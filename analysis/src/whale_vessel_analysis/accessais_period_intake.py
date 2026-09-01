"""Bounded local intake for one author-supplied multi-date AccessAIS delivery.

The intake partitions valid in-request timestamp rows into deterministic
one-date CSV artifacts for the existing cleaner. It performs no network work,
stores no delivery URL or email address, and makes no completeness inference
from filenames, row counts, timestamp bounds, or requested-date presence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import IO, Final, Literal, TextIO, cast

import duckdb

from whale_vessel_analysis.ais import (
    AIS_PUBLISHED_HEADER,
    AISSchemaError,
    validate_header,
)
from whale_vessel_analysis.ais_processing import AISProcessingResult, process_ais_csv
from whale_vessel_analysis.ais_retrieval import (
    AISRetrievalError,
    fingerprint_regular_file,
    inspect_ais_container,
    redact_source_reference,
)
from whale_vessel_analysis.cleaned_ais_bundle import canonical_json, sha256_file
from whale_vessel_analysis.config import (
    ANALYTICAL_PERIOD_END,
    ANALYTICAL_PERIOD_START,
    ProcessingConfig,
)
from whale_vessel_analysis.multiday_ais import (
    MultiDayAISInputError,
    inspect_cleaned_day,
    load_period_manifest,
    period_status,
    record_cleaned_days,
    validate_manifest_destination,
)

ACCESSAIS_PERIOD_DELIVERY_V1_CONTRACT: Final = "accessais_period_delivery_v1"
ACCESSAIS_PERIOD_DELIVERY_CONTRACT: Final = "accessais_period_delivery_v2"
ACCESSAIS_PERIOD_DELIVERY_SCHEMA_VERSION: Final = 2
ACCESSAIS_PERIOD_DELIVERY_PROCESSING_VERSION: Final = "2.0.1"
DELIVERY_MANIFEST_FILENAME: Final = "delivery-manifest.json"
DAILY_DIRECTORY_NAME: Final = "daily"
MAX_OPEN_DAILY_FILES: Final = 8
STAGING_DIRECTORY_NAME: Final = "staging"
_TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%S"
_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
_PROJECT_RAW_ROOT: Final = (_PROJECT_ROOT / "data" / "raw").resolve()
_PROJECT_INTERIM_ROOT: Final = (_PROJECT_ROOT / "data" / "interim").resolve()

PreparationOutcome = Literal["prepared", "identical_retry", "conflict"]


class AccessAISPeriodIntakeError(ValueError):
    """Raised when a supplied period delivery or destination is unsafe."""


class AccessAISPeriodConflictError(AccessAISPeriodIntakeError):
    """Raised after a non-replacing conflict attempt has been recorded."""


@dataclass(frozen=True, slots=True)
class RequestedPeriod:
    """Exact inclusive dates author-supplied for the AccessAIS order."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise AccessAISPeriodIntakeError(
                "requested start date cannot follow requested end date"
            )
        if not (
            ANALYTICAL_PERIOD_START <= self.start_date <= ANALYTICAL_PERIOD_END
            and ANALYTICAL_PERIOD_START <= self.end_date <= ANALYTICAL_PERIOD_END
        ):
            raise AccessAISPeriodIntakeError(
                "requested dates must fall inside the accepted analytical period"
            )

    def dates(self) -> tuple[str, ...]:
        count = (self.end_date - self.start_date).days + 1
        return tuple(
            date.fromordinal(self.start_date.toordinal() + offset).isoformat()
            for offset in range(count)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "start_utc_date": self.start_date.isoformat(),
            "end_utc_date": self.end_date.isoformat(),
            "inclusive": True,
            "expected_utc_dates": list(self.dates()),
        }


@dataclass(frozen=True, slots=True)
class CanonicalizationResources:
    """Explicit bounded DuckDB resources for canonical daily sorting."""

    memory_limit: str
    temporary_directory: Path

    def validate(self) -> CanonicalizationResources:
        import re

        if (
            re.fullmatch(r"[1-9][0-9]*(?:\.[0-9]+)?(?:KB|MB|GB|TB)", self.memory_limit)
            is None
        ):
            raise AccessAISPeriodIntakeError(
                "canonicalization memory limit must be a positive size with a "
                "KB, MB, GB, or TB unit"
            )
        temporary = validate_intake_directory(
            self.temporary_directory, "canonicalization temporary directory"
        )
        return CanonicalizationResources(self.memory_limit, temporary)


@dataclass(frozen=True, slots=True)
class DailySlice:
    """Stable identity and lineage for one generated one-date CSV."""

    utc_date: str
    relative_path: str
    row_count: int
    byte_size: int
    sha256: str
    artifact_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "utc_date": self.utc_date,
            "relative_path": self.relative_path,
            "row_count": self.row_count,
            "canonical_content_identity": self.artifact_id,
            "canonical_artifact": {
                "byte_size": self.byte_size,
                "sha256": self.sha256,
                "encoding": "UTF-8",
                "record_line_ending": "LF",
                "serialization": "all parsed fields CSV-quoted with RFC 4180 escaping",
            },
            "header": list(AIS_PUBLISHED_HEADER),
            "observed_valid_utc_date_count": 1,
        }


@dataclass(frozen=True, slots=True)
class PartitionCounts:
    """Delivery-level row accounting from one streaming CSV scan."""

    source_rows: int
    valid_timestamp_rows: int
    malformed_timestamp_rows: int
    in_request_rows: int
    out_of_request_rows: int
    rows_by_date: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class PreparationResult:
    """One prepared, reused, or conflicted intake destination."""

    output_directory: Path
    manifest_path: Path
    delivery_id: str
    outcome: PreparationOutcome
    manifest: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "output_directory": str(self.output_directory),
            "manifest_path": str(self.manifest_path),
            "delivery_id": self.delivery_id,
            "outcome": self.outcome,
            "preparation_status": self.manifest["preparation_status"],
            "row_accounting": self.manifest["row_accounting"],
            "requested_date_coverage": self.manifest["requested_date_coverage"],
            "independent_transfer_completeness": self.manifest[
                "independent_transfer_completeness"
            ],
            "observational_completeness": self.manifest["observational_completeness"],
        }


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    """Outcome from sequential cleaning and period-manifest recording."""

    preparation: PreparationResult
    cleaned_dates: tuple[str, ...]
    recorded_existing_dates: tuple[str, ...]
    skipped_successful_dates: tuple[str, ...]
    conflicting_dates: tuple[str, ...]
    period_status: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "preparation": self.preparation.to_dict(),
            "cleaned_dates": list(self.cleaned_dates),
            "recorded_existing_dates": list(self.recorded_existing_dates),
            "skipped_successful_dates": list(self.skipped_successful_dates),
            "conflicting_dates": list(self.conflicting_dates),
            "period_status": dict(self.period_status),
            "execution_note": (
                "daily slices are cleaned sequentially and each successful bundle "
                "is recorded immediately; interruption recovery skips dates whose "
                "compatible bundle is already recorded"
            ),
        }


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime) -> str:
    if value.utcoffset() != UTC.utcoffset(value):
        raise AccessAISPeriodIntakeError("intake timestamps must be timezone-aware UTC")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _delivery_id(source_sha256: str, requested: RequestedPeriod) -> str:
    material = {
        "contract": ACCESSAIS_PERIOD_DELIVERY_CONTRACT,
        "processing_version": ACCESSAIS_PERIOD_DELIVERY_PROCESSING_VERSION,
        "source_sha256": source_sha256,
        "requested_period": requested.to_dict(),
    }
    digest = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return "accessais-period-" + digest[:24]


def _v1_delivery_id(source_sha256: str, requested: RequestedPeriod) -> str:
    material = {
        "contract": ACCESSAIS_PERIOD_DELIVERY_V1_CONTRACT,
        "processing_version": "1.0.0",
        "source_sha256": source_sha256,
        "requested_period": requested.to_dict(),
    }
    digest = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return "accessais-period-" + digest[:24]


def _v1_slice_id(delivery_id: str, utc_date: str, sha256: str, row_count: int) -> str:
    material = {
        "delivery_id": delivery_id,
        "utc_date": utc_date,
        "sha256": sha256,
        "row_count": row_count,
    }
    digest = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return "accessais-day-" + digest[:24]


def _slice_id(utc_date: str, sha256: str, row_count: int) -> str:
    material = {
        "contract": "accessais_canonical_daily_content_v1",
        "utc_date": utc_date,
        "canonical_artifact_sha256": sha256,
        "row_count": row_count,
    }
    digest = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return "accessais-day-content-" + digest[:24]


def _is_under_data_raw(path: Path) -> bool:
    return path == _PROJECT_RAW_ROOT or path.is_relative_to(_PROJECT_RAW_ROOT)


def validate_intake_directory(path: Path, label: str) -> Path:
    """Require one explicit ignored data/interim directory."""
    resolved = path.resolve()
    if _is_under_data_raw(resolved):
        raise AccessAISPeriodIntakeError(f"{label} cannot be placed under data/raw")
    if not (
        resolved == _PROJECT_INTERIM_ROOT
        or resolved.is_relative_to(_PROJECT_INTERIM_ROOT)
    ):
        raise AccessAISPeriodIntakeError(
            f"{label} must be an explicit path under ignored data/interim"
        )
    if resolved.exists() and not resolved.is_dir():
        raise AccessAISPeriodIntakeError(f"{label} is not a directory: {resolved}")
    return resolved


def _paths_overlap(first: Path, second: Path) -> bool:
    return (
        first == second or first.is_relative_to(second) or second.is_relative_to(first)
    )


def _validated_canonicalization_resources(
    resources: CanonicalizationResources | None,
    intake_directory: Path,
    *other_managed_destinations: tuple[str, Path],
) -> CanonicalizationResources:
    """Resolve resources and reject spill overlap before creating any output."""
    candidate = resources or CanonicalizationResources(
        "512MB", intake_directory.parent / ".accessais-canonical-duckdb"
    )
    validated = candidate.validate()
    managed_destinations = (
        ("intake directory", intake_directory),
        *other_managed_destinations,
    )
    for label, destination in managed_destinations:
        if _paths_overlap(validated.temporary_directory, destination):
            raise AccessAISPeriodIntakeError(
                f"canonicalization temporary directory and {label} must be disjoint"
            )
    return validated


def _validate_orchestration_destinations(
    intake_directory: Path, cleaned_root: Path, period_manifest_path: Path
) -> tuple[Path, Path, Path]:
    """Resolve and reject overlapping managed paths before any output is written."""
    intake = validate_intake_directory(intake_directory, "intake directory")
    cleaned = validate_intake_directory(cleaned_root, "cleaned bundle root")
    if _paths_overlap(intake, cleaned):
        raise AccessAISPeriodIntakeError(
            "intake directory and cleaned bundle root must be disjoint"
        )
    manifest = period_manifest_path.resolve()
    if manifest == intake or manifest.is_relative_to(intake):
        raise AccessAISPeriodIntakeError(
            "period manifest cannot be placed inside the intake directory"
        )
    if manifest == cleaned or manifest.is_relative_to(cleaned):
        raise AccessAISPeriodIntakeError(
            "period manifest cannot be placed inside the cleaned bundle root"
        )
    try:
        manifest = validate_manifest_destination(manifest)
    except MultiDayAISInputError as exc:
        raise AccessAISPeriodIntakeError(str(exc)) from exc
    return intake, cleaned, manifest


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8", newline="\n")


class _DailyWriters:
    """Small LRU of append-only daily CSV writers for a streaming source scan."""

    def __init__(self, daily_directory: Path) -> None:
        self._directory = daily_directory
        self._open: OrderedDict[
            str, tuple[TextIO, Callable[[Sequence[str]], object]]
        ] = OrderedDict()
        self._started: set[str] = set()

    def write(self, utc_date: str, row: Sequence[str]) -> None:
        current = self._open.pop(utc_date, None)
        if current is None:
            path = self._directory / f"{utc_date}.csv"
            first = utc_date not in self._started
            stream = path.open("w" if first else "a", encoding="utf-8", newline="")
            csv_writer = csv.writer(stream, lineterminator="\n")
            writer = csv_writer.writerow
            if first:
                writer(AIS_PUBLISHED_HEADER)
                self._started.add(utc_date)
            current = (stream, writer)
        current_stream, current_writer = current
        current_writer(row)
        self._open[utc_date] = (current_stream, current_writer)
        if len(self._open) > MAX_OPEN_DAILY_FILES:
            _old_date, (old_stream, _old_writer) = self._open.popitem(last=False)
            old_stream.close()

    def close(self) -> None:
        for stream, _writer in self._open.values():
            stream.close()
        self._open.clear()


def _partition_csv_stream(
    source: IO[bytes], requested: RequestedPeriod, daily_directory: Path
) -> PartitionCounts:
    import io

    text_source = io.TextIOWrapper(source, encoding="utf-8", newline="")
    writers = _DailyWriters(daily_directory)
    source_rows = 0
    valid_rows = 0
    malformed_rows = 0
    in_request_rows = 0
    out_of_request_rows = 0
    rows_by_date: dict[str, int] = {}
    requested_dates = set(requested.dates())
    try:
        reader = csv.reader(text_source, strict=True)
        header = next(reader, None)
        if header is None:
            raise AccessAISPeriodIntakeError("selected CSV is empty")
        try:
            validate_header(header)
        except AISSchemaError as exc:
            raise AccessAISPeriodIntakeError(str(exc)) from exc
        timestamp_index = AIS_PUBLISHED_HEADER.index("BaseDateTime")
        for row_number, row in enumerate(reader, start=2):
            source_rows += 1
            if len(row) != len(AIS_PUBLISHED_HEADER):
                raise AccessAISPeriodIntakeError(
                    f"CSV row {row_number} has {len(row)} fields; "
                    f"expected {len(AIS_PUBLISHED_HEADER)}"
                )
            try:
                observed = datetime.strptime(
                    row[timestamp_index], _TIMESTAMP_FORMAT
                ).replace(tzinfo=UTC)
            except ValueError:
                malformed_rows += 1
                continue
            valid_rows += 1
            utc_date = observed.date().isoformat()
            rows_by_date[utc_date] = rows_by_date.get(utc_date, 0) + 1
            if utc_date not in requested_dates:
                out_of_request_rows += 1
                continue
            writers.write(utc_date, row)
            in_request_rows += 1
    except (UnicodeDecodeError, csv.Error) as exc:
        raise AccessAISPeriodIntakeError(
            f"selected member is not compatible UTF-8 CSV: {exc}"
        ) from exc
    finally:
        writers.close()
        text_source.detach()
    if source_rows == 0:
        raise AccessAISPeriodIntakeError("selected CSV contains zero data rows")
    if source_rows != malformed_rows + in_request_rows + out_of_request_rows:
        raise AccessAISPeriodIntakeError("delivery row accounting did not reconcile")
    return PartitionCounts(
        source_rows=source_rows,
        valid_timestamp_rows=valid_rows,
        malformed_timestamp_rows=malformed_rows,
        in_request_rows=in_request_rows,
        out_of_request_rows=out_of_request_rows,
        rows_by_date=dict(sorted(rows_by_date.items())),
    )


def _daily_slices(
    temporary: Path,
    counts: PartitionCounts,
) -> list[DailySlice]:
    slices: list[DailySlice] = []
    daily_directory = temporary / DAILY_DIRECTORY_NAME
    for utc_date, row_count in counts.rows_by_date.items():
        path = daily_directory / f"{utc_date}.csv"
        if not path.exists():
            continue
        sha256 = sha256_file(path)
        slices.append(
            DailySlice(
                utc_date=utc_date,
                relative_path=f"{DAILY_DIRECTORY_NAME}/{utc_date}.csv",
                row_count=row_count,
                byte_size=path.stat().st_size,
                sha256=sha256,
                artifact_id=_slice_id(utc_date, sha256, row_count),
            )
        )
    return slices


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _canonicalize_daily_files(
    temporary: Path,
    counts: PartitionCounts,
    resources: CanonicalizationResources,
) -> dict[str, object]:
    """Sort parsed fields out of core and serialize stable canonical daily CSVs."""
    validated = resources.validate()
    validated.temporary_directory.mkdir(parents=True, exist_ok=True)
    spill_directory = Path(
        tempfile.mkdtemp(
            prefix=".accessais-canonical-spill-",
            dir=validated.temporary_directory,
        )
    )
    staging_directory = temporary / STAGING_DIRECTORY_NAME
    daily_directory = temporary / DAILY_DIRECTORY_NAME
    columns = ", ".join(
        f"{_sql_string(name)}: 'VARCHAR'" for name in AIS_PUBLISHED_HEADER
    )
    normalized_columns = ", ".join(
        f"COALESCE({_quoted_identifier(name)}, '') AS {_quoted_identifier(name)}"
        for name in AIS_PUBLISHED_HEADER
    )
    order = ", ".join(
        f"COALESCE({_quoted_identifier(name)}, '')" for name in AIS_PUBLISHED_HEADER
    )
    try:
        with duckdb.connect() as connection:
            connection.execute(
                f"SET memory_limit = {_sql_string(validated.memory_limit)}"
            )
            connection.execute(
                f"SET temp_directory = {_sql_string(str(spill_directory))}"
            )
            connection.execute("SET threads = 1")
            for utc_date in sorted(counts.rows_by_date):
                staged = staging_directory / f"{utc_date}.csv"
                if not staged.is_file():
                    continue
                data_output = temporary / f".{utc_date}.canonical-data.csv"
                connection.execute(
                    "CREATE OR REPLACE TEMP TABLE canonical_rows AS "
                    f"SELECT {normalized_columns} FROM "
                    f"read_csv({_sql_string(str(staged))}, "
                    f"header = true, auto_detect = false, columns = {{{columns}}}, "
                    "strict_mode = true)"
                )
                connection.execute(
                    f"COPY (SELECT * FROM canonical_rows ORDER BY {order}) "
                    f"TO {_sql_string(str(data_output))} "
                    "(FORMAT CSV, HEADER false, FORCE_QUOTE *)"
                )
                destination = daily_directory / f"{utc_date}.csv"
                with destination.open("wb") as output:
                    output.write(
                        (",".join(AIS_PUBLISHED_HEADER) + "\n").encode("utf-8")
                    )
                    with data_output.open("rb") as source:
                        shutil.copyfileobj(source, output)
                    output.flush()
                    os.fsync(output.fileno())
                data_output.unlink()
    except duckdb.Error as exc:
        raise AccessAISPeriodIntakeError(
            f"could not canonicalize daily AccessAIS content with DuckDB: {exc}"
        ) from exc
    finally:
        shutil.rmtree(spill_directory, ignore_errors=True)
    shutil.rmtree(staging_directory)
    return {
        "engine": "DuckDB",
        "memory_limit": validated.memory_limit,
        "threads": 1,
        "isolated_spill_directory": True,
        "spill_directory_removed_after_run": not spill_directory.exists(),
        "sort_fields": list(AIS_PUBLISHED_HEADER),
        "duplicate_multiplicity": "preserved",
    }


def _transfer_state(
    container: str, crc_valid: bool | None, content_length_match: bool | None
) -> dict[str, object]:
    verified = content_length_match is True or (
        container == "zip" and crc_valid is True
    )
    return {
        "status": "verified" if verified else "unverified",
        "evidence": (
            "matching independently supplied source Content-Length"
            if content_length_match is True
            else (
                "complete ZIP structure and CRC validation"
                if container == "zip" and crc_valid is True
                else "no independent source byte count or archive integrity boundary"
            )
        ),
        "note": (
            "transfer integrity is separate from requested-date presence and from "
            "observational completeness"
        ),
    }


def _attempt(
    number: int,
    outcome: PreparationOutcome,
    source_sha256: str,
    source_byte_size: int,
    requested: RequestedPeriod,
    attempted_at: datetime,
) -> dict[str, object]:
    return {
        "attempt_number": number,
        "outcome": outcome,
        "attempted_at_utc": _timestamp(attempted_at),
        "source_identity": {
            "byte_size": source_byte_size,
            "sha256": source_sha256,
        },
        "requested_period": requested.to_dict(),
        "candidate_delivery_id": _delivery_id(source_sha256, requested),
    }


def _build_manifest(
    *,
    source_path: Path,
    source_byte_size: int,
    source_sha256: str,
    source_content_length: int | None,
    requested: RequestedPeriod,
    container: str,
    archive_members: Sequence[str],
    selected_csv_member: str | None,
    crc_valid: bool | None,
    counts: PartitionCounts,
    slices: Sequence[DailySlice],
    canonicalization: Mapping[str, object],
    attempted_at: datetime,
) -> dict[str, object]:
    delivery_id = _delivery_id(source_sha256, requested)
    expected = set(requested.dates())
    observed = set(counts.rows_by_date)
    present = sorted(expected & observed)
    missing = sorted(expected - observed)
    outside = sorted(observed - expected)
    exception_count = counts.malformed_timestamp_rows + counts.out_of_request_rows
    preparation_status = (
        "prepared_with_exceptions" if exception_count or missing else "prepared"
    )
    content_length_match = (
        None
        if source_content_length is None
        else source_content_length == source_byte_size
    )
    return {
        "contract": ACCESSAIS_PERIOD_DELIVERY_CONTRACT,
        "schema_version": ACCESSAIS_PERIOD_DELIVERY_SCHEMA_VERSION,
        "processing_version": ACCESSAIS_PERIOD_DELIVERY_PROCESSING_VERSION,
        "delivery_id": delivery_id,
        "route": "accessais_author_supplied_local_delivery",
        "requested_period": requested.to_dict(),
        "source": {
            "byte_size": source_byte_size,
            "sha256": source_sha256,
            "source_filename": redact_source_reference(source_path.name, "accessais"),
            "content_type_detected_from_bytes": container,
            "source_content_length": source_content_length,
            "source_content_length_match": content_length_match,
            "archive_verification": {
                "archive_valid": True if container == "zip" else None,
                "crc_valid": crc_valid,
                "members": list(archive_members),
                "selected_csv_member": selected_csv_member,
                "csv_member_selection": "unambiguous",
            },
            "header": {
                "contract": "noaa_marine_cadastre_ais_flat_csv_v1",
                "exact_published_header": list(AIS_PUBLISHED_HEADER),
                "valid": True,
            },
        },
        "row_accounting": {
            "status": "reconciled",
            "source_data_rows": counts.source_rows,
            "valid_timestamp_rows": counts.valid_timestamp_rows,
            "malformed_or_unassignable_timestamp_rows": (
                counts.malformed_timestamp_rows
            ),
            "valid_in_request_rows_assigned_to_daily_slices": counts.in_request_rows,
            "valid_out_of_request_rows": counts.out_of_request_rows,
            "conservation_equation": (
                "source_data_rows = malformed_or_unassignable_timestamp_rows + "
                "valid_in_request_rows_assigned_to_daily_slices + "
                "valid_out_of_request_rows"
            ),
        },
        "observed_valid_utc_dates": sorted(observed),
        "rows_by_utc_date": dict(counts.rows_by_date),
        "requested_date_coverage": {
            "status": "has_exceptions" if missing or outside else "dates_present",
            "present_requested_utc_dates": present,
            "missing_requested_utc_dates": missing,
            "out_of_request_utc_dates": outside,
            "note": (
                "date presence is inventory evidence only and does not establish "
                "transfer or observational completeness"
            ),
        },
        "daily_slices": [item.to_dict() for item in slices],
        "generated_artifact_lineage": {
            "source_delivery_identity": {
                "byte_size": source_byte_size,
                "sha256": source_sha256,
                "delivery_id": delivery_id,
            },
            "processing_version": ACCESSAIS_PERIOD_DELIVERY_PROCESSING_VERSION,
            "partition_rule": "strict parsed UTC date within requested inclusive dates",
            "canonical_content_rule": (
                "parsed 17-field rows sorted lexicographically by every field; "
                "duplicate multiplicity preserved"
            ),
            "header_rule": "exact published header written to every daily slice",
            "canonicalization": dict(canonicalization),
        },
        "preparation_status": preparation_status,
        "independent_transfer_completeness": _transfer_state(
            container, crc_valid, content_length_match
        ),
        "observational_completeness": {
            "status": "unverified",
            "reason": (
                "delivery integrity and row accounting cannot establish receiver "
                "coverage, collection continuity, or records never observed"
            ),
        },
        "period_availability": {
            "status": "not_claimed",
            "reason": (
                "this delivery covers only its explicit requested dates; analytical-"
                "period availability is owned by the 153-date cleaned-input manifest"
            ),
        },
        "attempt_history": [
            _attempt(
                1,
                "prepared",
                source_sha256,
                source_byte_size,
                requested,
                attempted_at,
            )
        ],
        "latest_attempt_outcome": "prepared",
        "local_provenance": {
            "source_path": redact_source_reference(str(source_path), "accessais"),
            "note": "local paths are execution provenance and not delivery identity",
        },
    }


def _manifest_path(directory: Path) -> Path:
    return directory / DELIVERY_MANIFEST_FILENAME


def _validate_slice_content(
    path: Path, utc_date: str, expected_rows: int, *, canonical: bool
) -> None:
    row_count = 0
    previous_row: tuple[str, ...] | None = None
    timestamp_index = AIS_PUBLISHED_HEADER.index("BaseDateTime")
    try:
        with path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.reader(source, strict=True)
            header = next(reader, None)
            if header is None:
                raise AccessAISPeriodIntakeError(f"daily slice {utc_date} is empty")
            validate_header(header)
            if canonical:
                expected_header = (",".join(AIS_PUBLISHED_HEADER) + "\n").encode(
                    "utf-8"
                )
                with path.open("rb") as binary_source:
                    if binary_source.read(len(expected_header)) != expected_header:
                        raise AccessAISPeriodIntakeError(
                            f"daily slice {utc_date} does not use the exact canonical "
                            "UTF-8/LF header bytes"
                        )
            for row_number, row in enumerate(reader, start=2):
                row_count += 1
                if len(row) != len(AIS_PUBLISHED_HEADER):
                    raise AccessAISPeriodIntakeError(
                        f"daily slice {utc_date} row {row_number} has an invalid "
                        "field count"
                    )
                try:
                    observed = datetime.strptime(
                        row[timestamp_index], _TIMESTAMP_FORMAT
                    ).replace(tzinfo=UTC)
                except ValueError as exc:
                    raise AccessAISPeriodIntakeError(
                        f"daily slice {utc_date} contains an unassignable timestamp"
                    ) from exc
                if observed.date().isoformat() != utc_date:
                    raise AccessAISPeriodIntakeError(
                        f"daily slice {utc_date} contains another valid UTC date"
                    )
                row_key = tuple(row)
                if canonical and previous_row is not None and row_key < previous_row:
                    raise AccessAISPeriodIntakeError(
                        f"daily slice {utc_date} is not sorted by all published fields"
                    )
                previous_row = row_key
    except (OSError, UnicodeDecodeError, csv.Error, AISSchemaError) as exc:
        raise AccessAISPeriodIntakeError(
            f"daily slice {utc_date} is not compatible exact-header UTF-8 CSV"
        ) from exc
    if row_count != expected_rows:
        raise AccessAISPeriodIntakeError(
            f"daily slice {utc_date} row count does not match its manifest"
        )


def _strict_nonnegative_count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AccessAISPeriodIntakeError(f"{label} must be a non-boolean integer count")
    if value < 0:
        raise AccessAISPeriodIntakeError(f"{label} cannot be negative")
    return value


def _validate_manifest_accounting(
    payload: Mapping[str, object], requested: RequestedPeriod
) -> tuple[dict[str, int], frozenset[str]]:
    row_accounting = payload.get("row_accounting")
    rows_by_date = payload.get("rows_by_utc_date")
    coverage = payload.get("requested_date_coverage")
    if not (
        isinstance(row_accounting, dict)
        and isinstance(rows_by_date, dict)
        and isinstance(coverage, dict)
    ):
        raise AccessAISPeriodIntakeError(
            "delivery row accounting and date coverage must be objects"
        )
    source_rows = _strict_nonnegative_count(
        row_accounting.get("source_data_rows"), "source_data_rows"
    )
    valid_rows = _strict_nonnegative_count(
        row_accounting.get("valid_timestamp_rows"), "valid_timestamp_rows"
    )
    malformed_rows = _strict_nonnegative_count(
        row_accounting.get("malformed_or_unassignable_timestamp_rows"),
        "malformed_or_unassignable_timestamp_rows",
    )
    assigned_rows = _strict_nonnegative_count(
        row_accounting.get("valid_in_request_rows_assigned_to_daily_slices"),
        "valid_in_request_rows_assigned_to_daily_slices",
    )
    outside_rows = _strict_nonnegative_count(
        row_accounting.get("valid_out_of_request_rows"),
        "valid_out_of_request_rows",
    )
    normalized_rows_by_date: dict[str, int] = {}
    for raw_date, raw_count in rows_by_date.items():
        if not isinstance(raw_date, str):
            raise AccessAISPeriodIntakeError(
                "rows_by_utc_date keys must be UTC-date strings"
            )
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise AccessAISPeriodIntakeError(
                f"rows_by_utc_date key is not a valid UTC date: {raw_date}"
            ) from exc
        if parsed_date.isoformat() != raw_date:
            raise AccessAISPeriodIntakeError(
                f"rows_by_utc_date key is not canonical ISO format: {raw_date}"
            )
        count = _strict_nonnegative_count(raw_count, f"rows_by_utc_date[{raw_date}]")
        if count == 0:
            raise AccessAISPeriodIntakeError(
                f"rows_by_utc_date[{raw_date}] must be positive"
            )
        normalized_rows_by_date[raw_date] = count
    requested_dates = set(requested.dates())
    observed_dates = set(normalized_rows_by_date)
    expected_assigned = sum(
        count
        for utc_date, count in normalized_rows_by_date.items()
        if utc_date in requested_dates
    )
    expected_outside = sum(
        count
        for utc_date, count in normalized_rows_by_date.items()
        if utc_date not in requested_dates
    )
    if not (
        row_accounting.get("status") == "reconciled"
        and valid_rows == assigned_rows + outside_rows
        and source_rows == valid_rows + malformed_rows
        and assigned_rows == expected_assigned
        and outside_rows == expected_outside
    ):
        raise AccessAISPeriodIntakeError(
            "delivery row accounting does not reconcile with rows_by_utc_date"
        )
    if (
        coverage.get("present_requested_utc_dates")
        != sorted(requested_dates & observed_dates)
        or coverage.get("missing_requested_utc_dates")
        != sorted(requested_dates - observed_dates)
        or coverage.get("out_of_request_utc_dates")
        != sorted(observed_dates - requested_dates)
        or payload.get("observed_valid_utc_dates") != sorted(observed_dates)
    ):
        raise AccessAISPeriodIntakeError(
            "delivery date coverage does not match rows_by_utc_date"
        )
    return normalized_rows_by_date, frozenset(requested_dates & observed_dates)


def _validate_completeness_states(payload: Mapping[str, object]) -> None:
    source = payload.get("source")
    transfer = payload.get("independent_transfer_completeness")
    observational = payload.get("observational_completeness")
    availability = payload.get("period_availability")
    if not all(
        isinstance(value, dict)
        for value in (source, transfer, observational, availability)
    ):
        raise AccessAISPeriodIntakeError(
            "delivery completeness states must be separate objects"
        )
    source = cast(dict[str, object], source)
    transfer = cast(dict[str, object], transfer)
    archive = source.get("archive_verification")
    independently_verified = source.get("source_content_length_match") is True or (
        source.get("content_type_detected_from_bytes") == "zip"
        and isinstance(archive, dict)
        and archive.get("crc_valid") is True
    )
    expected_transfer = "verified" if independently_verified else "unverified"
    if transfer.get("status") != expected_transfer:
        raise AccessAISPeriodIntakeError(
            "independent transfer completeness is unsupported by source evidence"
        )
    if cast(dict[str, object], observational).get("status") != "unverified":
        raise AccessAISPeriodIntakeError(
            "observational completeness must remain unverified"
        )
    if cast(dict[str, object], availability).get("status") != "not_claimed":
        raise AccessAISPeriodIntakeError(
            "delivery intake cannot claim analytical-period availability"
        )


def load_delivery_manifest(directory: Path) -> dict[str, object]:
    """Load and validate one established delivery bundle and every slice checksum."""
    resolved = directory.resolve()
    if not resolved.is_dir():
        raise AccessAISPeriodIntakeError(f"intake directory does not exist: {resolved}")
    if {entry.name for entry in resolved.iterdir()} != {
        DELIVERY_MANIFEST_FILENAME,
        DAILY_DIRECTORY_NAME,
    }:
        raise AccessAISPeriodIntakeError(
            "existing intake destination is not a complete AccessAIS period bundle"
        )
    try:
        payload = json.loads(_manifest_path(resolved).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AccessAISPeriodIntakeError(
            "delivery manifest is not readable JSON"
        ) from exc
    if not isinstance(payload, dict) or payload.get("contract") not in {
        ACCESSAIS_PERIOD_DELIVERY_V1_CONTRACT,
        ACCESSAIS_PERIOD_DELIVERY_CONTRACT,
    }:
        raise AccessAISPeriodIntakeError(
            "existing intake destination has an incompatible contract"
        )
    contract = cast(str, payload["contract"])
    expected_schema = (
        1
        if contract == ACCESSAIS_PERIOD_DELIVERY_V1_CONTRACT
        else ACCESSAIS_PERIOD_DELIVERY_SCHEMA_VERSION
    )
    if payload.get("schema_version") != expected_schema:
        raise AccessAISPeriodIntakeError("delivery manifest schema version is invalid")
    source = payload.get("source")
    request = payload.get("requested_period")
    if not isinstance(source, dict) or not isinstance(request, dict):
        raise AccessAISPeriodIntakeError("delivery source/request records are invalid")
    try:
        requested = RequestedPeriod(
            date.fromisoformat(cast(str, request["start_utc_date"])),
            date.fromisoformat(cast(str, request["end_utc_date"])),
        )
        expected_id = (
            _v1_delivery_id(cast(str, source["sha256"]), requested)
            if contract == ACCESSAIS_PERIOD_DELIVERY_V1_CONTRACT
            else _delivery_id(cast(str, source["sha256"]), requested)
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AccessAISPeriodIntakeError(
            "delivery identity fields are invalid"
        ) from exc
    if payload.get("delivery_id") != expected_id:
        raise AccessAISPeriodIntakeError("delivery_id does not match manifest content")
    rows_by_date, present_requested_dates = _validate_manifest_accounting(
        payload, requested
    )
    _validate_completeness_states(payload)
    if contract == ACCESSAIS_PERIOD_DELIVERY_CONTRACT:
        if payload.get("processing_version") != (
            ACCESSAIS_PERIOD_DELIVERY_PROCESSING_VERSION
        ):
            raise AccessAISPeriodIntakeError(
                "Version 2 delivery processing version is invalid"
            )
        lineage = payload.get("generated_artifact_lineage")
        if not isinstance(lineage, dict):
            raise AccessAISPeriodIntakeError(
                "Version 2 generated-artifact lineage is invalid"
            )
        source_identity = lineage.get("source_delivery_identity")
        canonicalization = lineage.get("canonicalization")
        if not (
            isinstance(source_identity, dict)
            and source_identity
            == {
                "byte_size": source.get("byte_size"),
                "sha256": source.get("sha256"),
                "delivery_id": expected_id,
            }
            and isinstance(canonicalization, dict)
            and canonicalization.get("engine") == "DuckDB"
            and canonicalization.get("threads") == 1
            and canonicalization.get("isolated_spill_directory") is True
            and canonicalization.get("spill_directory_removed_after_run") is True
            and canonicalization.get("sort_fields") == list(AIS_PUBLISHED_HEADER)
            and canonicalization.get("duplicate_multiplicity") == "preserved"
        ):
            raise AccessAISPeriodIntakeError(
                "Version 2 canonical lineage is inconsistent with its source"
            )
    daily_directory = resolved / DAILY_DIRECTORY_NAME
    if not daily_directory.is_dir():
        raise AccessAISPeriodIntakeError("delivery daily slice directory is missing")
    if not daily_directory.resolve().is_relative_to(resolved):
        raise AccessAISPeriodIntakeError(
            "delivery daily slice directory escapes the intake directory"
        )
    slices = payload.get("daily_slices")
    if not isinstance(slices, list):
        raise AccessAISPeriodIntakeError("delivery daily_slices must be a list")
    expected_names: set[str] = set()
    observed_slice_dates: set[str] = set()
    assigned_slice_rows = 0
    validated_slices: list[tuple[dict[str, object], str]] = []
    for raw_slice in slices:
        if not isinstance(raw_slice, dict):
            raise AccessAISPeriodIntakeError("every daily slice must be an object")
        utc_date_value = raw_slice.get("utc_date")
        if not isinstance(utc_date_value, str):
            raise AccessAISPeriodIntakeError("daily slice utc_date must be a string")
        utc_date = utc_date_value
        if utc_date in observed_slice_dates or utc_date not in requested.dates():
            raise AccessAISPeriodIntakeError(
                "daily slices must have unique in-request UTC dates"
            )
        observed_slice_dates.add(utc_date)
        validated_slices.append((raw_slice, utc_date))
    if observed_slice_dates != present_requested_dates:
        raise AccessAISPeriodIntakeError(
            "daily slice dates must exactly match present_requested_utc_dates"
        )
    for raw_slice, utc_date in validated_slices:
        expected_names.add(f"{utc_date}.csv")
        expected_relative_path = f"{DAILY_DIRECTORY_NAME}/{utc_date}.csv"
        relative_path = raw_slice.get("relative_path")
        if not isinstance(relative_path, str) or relative_path != (
            expected_relative_path
        ):
            raise AccessAISPeriodIntakeError(
                f"daily slice {utc_date} relative_path must be exactly "
                f"{expected_relative_path}"
            )
        path = daily_directory / f"{utc_date}.csv"
        if not path.resolve().is_relative_to(resolved):
            raise AccessAISPeriodIntakeError(
                f"daily slice {utc_date} escapes the intake directory"
            )
        canonical_artifact = raw_slice.get("canonical_artifact")
        if contract == ACCESSAIS_PERIOD_DELIVERY_V1_CONTRACT:
            recorded_sha256 = raw_slice.get("sha256")
            recorded_byte_size = raw_slice.get("byte_size")
            recorded_artifact_id = raw_slice.get("artifact_id")
        elif isinstance(canonical_artifact, dict):
            recorded_sha256 = canonical_artifact.get("sha256")
            recorded_byte_size = canonical_artifact.get("byte_size")
            recorded_artifact_id = raw_slice.get("canonical_content_identity")
            if canonical_artifact.get("encoding") != "UTF-8" or (
                canonical_artifact.get("record_line_ending") != "LF"
            ):
                raise AccessAISPeriodIntakeError(
                    f"daily slice {utc_date} canonical serialization is invalid"
                )
        else:
            raise AccessAISPeriodIntakeError(
                f"daily slice {utc_date} canonical_artifact is invalid"
            )
        if not isinstance(recorded_sha256, str):
            raise AccessAISPeriodIntakeError(
                f"daily slice {utc_date} artifact SHA-256 is invalid"
            )
        if not path.is_file() or sha256_file(path) != recorded_sha256:
            raise AccessAISPeriodIntakeError(
                f"daily slice {utc_date} is missing or does not match its checksum"
            )
        row_count = _strict_nonnegative_count(
            raw_slice.get("row_count"), f"daily slice {utc_date} row_count"
        )
        if row_count != rows_by_date[utc_date]:
            raise AccessAISPeriodIntakeError(
                f"daily slice {utc_date} row_count does not match rows_by_utc_date"
            )
        byte_size_value = recorded_byte_size
        if isinstance(byte_size_value, bool) or not isinstance(byte_size_value, int):
            raise AccessAISPeriodIntakeError(
                f"daily slice {utc_date} byte_size must be a non-boolean integer"
            )
        byte_size = byte_size_value
        if byte_size != path.stat().st_size:
            raise AccessAISPeriodIntakeError(
                f"daily slice {utc_date} byte size does not match its manifest"
            )
        expected_artifact_id = (
            _v1_slice_id(expected_id, utc_date, recorded_sha256, row_count)
            if contract == ACCESSAIS_PERIOD_DELIVERY_V1_CONTRACT
            else _slice_id(utc_date, recorded_sha256, row_count)
        )
        if recorded_artifact_id != expected_artifact_id:
            raise AccessAISPeriodIntakeError(
                f"daily slice {utc_date} artifact_id does not match its identity"
            )
        _validate_slice_content(
            path,
            utc_date,
            row_count,
            canonical=contract == ACCESSAIS_PERIOD_DELIVERY_CONTRACT,
        )
        assigned_slice_rows += row_count
    actual_names = {path.name for path in daily_directory.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise AccessAISPeriodIntakeError(
            "daily slice directory contains files not owned by the delivery manifest"
        )
    row_accounting = cast(dict[str, object], payload["row_accounting"])
    if assigned_slice_rows != row_accounting.get(
        "valid_in_request_rows_assigned_to_daily_slices"
    ):
        raise AccessAISPeriodIntakeError(
            "daily slice rows do not match reconciled delivery accounting"
        )
    attempts = payload.get("attempt_history")
    if not isinstance(attempts, list):
        raise AccessAISPeriodIntakeError("delivery attempt_history must be a list")
    return cast(dict[str, object], payload)


def _replace_file(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def _write_existing_manifest_atomic(
    directory: Path, manifest: Mapping[str, object]
) -> None:
    path = _manifest_path(directory)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.temporary-", dir=directory
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(canonical_json(manifest) + "\n")
            output.flush()
            os.fsync(output.fileno())
        _replace_file(temporary, path)
    except OSError as exc:
        raise AccessAISPeriodIntakeError(
            f"could not update delivery attempt history atomically: {exc}"
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def _existing_attempt(
    directory: Path,
    source_sha256: str,
    source_byte_size: int,
    requested: RequestedPeriod,
    attempted_at: datetime,
) -> PreparationResult:
    manifest = load_delivery_manifest(directory)
    if manifest.get("contract") == ACCESSAIS_PERIOD_DELIVERY_V1_CONTRACT:
        raise AccessAISPeriodIntakeError(
            "existing intake directory uses read-only "
            "accessais_period_delivery_v1; Version 2 output requires a fresh "
            "intake directory"
        )
    existing_id = cast(str, manifest["delivery_id"])
    candidate_id = _delivery_id(source_sha256, requested)
    attempts = cast(list[dict[str, object]], manifest["attempt_history"])
    outcome: PreparationOutcome = (
        "identical_retry" if existing_id == candidate_id else "conflict"
    )
    attempts.append(
        _attempt(
            len(attempts) + 1,
            outcome,
            source_sha256,
            source_byte_size,
            requested,
            attempted_at,
        )
    )
    manifest["latest_attempt_outcome"] = outcome
    _write_existing_manifest_atomic(directory, manifest)
    result = PreparationResult(
        directory,
        _manifest_path(directory),
        existing_id,
        outcome,
        manifest,
    )
    if outcome == "conflict":
        raise AccessAISPeriodConflictError(
            "delivery conflict recorded; established identity and daily slices "
            "were not replaced"
        )
    return result


def _publish_directory(temporary: Path, destination: Path) -> None:
    temporary.rename(destination)


def prepare_accessais_delivery(
    source_path: Path,
    output_directory: Path,
    requested: RequestedPeriod,
    resources: CanonicalizationResources | None = None,
    *,
    source_content_length: int | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> PreparationResult:
    """Partition one immutable AccessAIS CSV/ZIP into atomic one-date slices."""
    source_path = source_path.resolve()
    output_directory = validate_intake_directory(output_directory, "intake directory")
    resources = _validated_canonicalization_resources(resources, output_directory)
    source_byte_size, source_sha256, source_mtime_ns = fingerprint_regular_file(
        source_path
    )
    if source_content_length is not None and source_content_length != source_byte_size:
        raise AccessAISPeriodIntakeError(
            f"source Content-Length {source_content_length} does not match local "
            f"byte size {source_byte_size}"
        )
    attempted_at = clock()
    if output_directory.exists():
        return _existing_attempt(
            output_directory,
            source_sha256,
            source_byte_size,
            requested,
            attempted_at,
        )
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{output_directory.name}.temporary-", dir=output_directory.parent
        )
    )
    staging_directory = temporary / STAGING_DIRECTORY_NAME
    daily_directory = temporary / DAILY_DIRECTORY_NAME
    staging_directory.mkdir()
    daily_directory.mkdir()
    try:
        try:
            container, counts = inspect_ais_container(
                source_path,
                lambda stream: _partition_csv_stream(
                    stream, requested, staging_directory
                ),
            )
        except AISRetrievalError as exc:
            raise AccessAISPeriodIntakeError(str(exc)) from exc
        final_size, final_sha256, final_mtime_ns = fingerprint_regular_file(source_path)
        if (
            final_size != source_byte_size
            or final_sha256 != source_sha256
            or final_mtime_ns != source_mtime_ns
        ):
            raise AccessAISPeriodIntakeError(
                "supplied delivery changed during read-only preparation"
            )
        canonicalization = _canonicalize_daily_files(temporary, counts, resources)
        slices = _daily_slices(temporary, counts)
        if sum(item.row_count for item in slices) != counts.in_request_rows:
            raise AccessAISPeriodIntakeError(
                "daily slice row counts do not conserve assigned delivery rows"
            )
        manifest = _build_manifest(
            source_path=source_path,
            source_byte_size=source_byte_size,
            source_sha256=source_sha256,
            source_content_length=source_content_length,
            requested=requested,
            container=container.container,
            archive_members=container.archive_members,
            selected_csv_member=container.selected_csv_member,
            crc_valid=container.crc_valid,
            counts=counts,
            slices=slices,
            canonicalization=canonicalization,
            attempted_at=attempted_at,
        )
        _write_json(temporary / DELIVERY_MANIFEST_FILENAME, manifest)
        _publish_directory(temporary, output_directory)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return PreparationResult(
        output_directory,
        _manifest_path(output_directory),
        cast(str, manifest["delivery_id"]),
        "prepared",
        manifest,
    )


def _daily_slice_records(
    directory: Path, manifest: Mapping[str, object]
) -> tuple[tuple[str, Path, str], ...]:
    slices = cast(list[dict[str, object]], manifest["daily_slices"])
    return tuple(
        (
            cast(str, item["utc_date"]),
            directory / DAILY_DIRECTORY_NAME / f"{cast(str, item['utc_date'])}.csv",
            cast(
                str,
                cast(dict[str, object], item["canonical_artifact"])["sha256"],
            ),
        )
        for item in sorted(slices, key=lambda item: cast(str, item["utc_date"]))
    )


def _cleaner_input_sha256(bundle: Path) -> str | None:
    try:
        quality = json.loads(
            (bundle / "quality-report.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(quality, dict) or not isinstance(quality.get("input"), dict):
        return None
    value = cast(dict[str, object], quality["input"]).get("sha256")
    return value if isinstance(value, str) else None


def _already_recorded_for_bundle(
    period_manifest: Mapping[str, object], utc_date: str, bundle: Path, slice_sha: str
) -> bool:
    dates = period_manifest.get("dates")
    if not isinstance(dates, list):
        return False
    entry = next(
        (
            item
            for item in dates
            if isinstance(item, dict) and item.get("utc_date") == utc_date
        ),
        None,
    )
    if not isinstance(entry, dict) or entry.get("status") != "compatible":
        return False
    if _cleaner_input_sha256(bundle) != slice_sha:
        return False
    try:
        inspection = inspect_cleaned_day(bundle)
    except MultiDayAISInputError:
        return False
    compatibility = entry.get("cleaner_bundle_compatibility")
    return isinstance(compatibility, dict) and all(
        compatibility.get(field) == value
        for field, value in inspection.identity_dict().items()
    )


def orchestrate_accessais_delivery(
    source_path: Path,
    intake_directory: Path,
    cleaned_root: Path,
    period_manifest_path: Path,
    requested: RequestedPeriod,
    config: ProcessingConfig,
    resources: CanonicalizationResources | None = None,
    *,
    source_content_length: int | None = None,
    clock: Callable[[], datetime] = _utc_now,
    cleaner: Callable[[Path, Path, ProcessingConfig], AISProcessingResult] = (
        process_ais_csv
    ),
) -> OrchestrationResult:
    """Prepare, sequentially clean, and immediately record each available date."""
    intake_directory, cleaned_root, period_manifest_path = (
        _validate_orchestration_destinations(
            intake_directory, cleaned_root, period_manifest_path
        )
    )
    resources = _validated_canonicalization_resources(
        resources,
        intake_directory,
        ("cleaned bundle root", cleaned_root),
        ("period manifest", period_manifest_path),
    )
    preparation = prepare_accessais_delivery(
        source_path,
        intake_directory,
        requested,
        resources,
        source_content_length=source_content_length,
        clock=clock,
    )
    cleaned_root.mkdir(parents=True, exist_ok=True)
    cleaned_dates: list[str] = []
    recorded_existing_dates: list[str] = []
    skipped_dates: list[str] = []
    conflicting_dates: list[str] = []
    for utc_date, slice_path, slice_sha in _daily_slice_records(
        preparation.output_directory, preparation.manifest
    ):
        bundle = cleaned_root / utc_date
        current_manifest = (
            load_period_manifest(period_manifest_path.resolve())
            if period_manifest_path.is_file()
            else None
        )
        if current_manifest is not None and _already_recorded_for_bundle(
            current_manifest, utc_date, bundle, slice_sha
        ):
            skipped_dates.append(utc_date)
            continue
        if bundle.exists():
            inspection = inspect_cleaned_day(bundle)
            if (
                inspection.utc_date != utc_date
                or _cleaner_input_sha256(bundle) != slice_sha
            ):
                raise AccessAISPeriodIntakeError(
                    f"existing cleaner bundle for {utc_date} does not belong to the "
                    "established daily slice"
                )
            update = record_cleaned_days(period_manifest_path, [bundle], clock=clock)
            if any(outcome.entry_status == "conflict" for outcome in update.outcomes):
                conflicting_dates.append(utc_date)
            recorded_existing_dates.append(utc_date)
            continue
        cleaner(slice_path, bundle, config)
        if _cleaner_input_sha256(bundle) != slice_sha:
            raise AccessAISPeriodIntakeError(
                f"new cleaner bundle for {utc_date} does not record the "
                "established daily-slice SHA-256"
            )
        update = record_cleaned_days(period_manifest_path, [bundle], clock=clock)
        if any(outcome.entry_status == "conflict" for outcome in update.outcomes):
            conflicting_dates.append(utc_date)
        cleaned_dates.append(utc_date)
    if not period_manifest_path.is_file():
        raise AccessAISPeriodIntakeError(
            "delivery produced no compatible daily slice to record"
        )
    final_period = load_period_manifest(period_manifest_path.resolve())
    return OrchestrationResult(
        preparation,
        tuple(cleaned_dates),
        tuple(recorded_existing_dates),
        tuple(skipped_dates),
        tuple(conflicting_dates),
        period_status(final_period),
    )
