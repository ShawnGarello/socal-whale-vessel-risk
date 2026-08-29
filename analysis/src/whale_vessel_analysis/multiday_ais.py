"""Versioned multi-day cleaned AIS input contract for the analytical period.

This module assembles independently verified one-date cleaner bundles into one
explicit period-input manifest. It records what has been verified and what has
not, and it refuses to imply that the analytical period is ready until every
expected UTC date carries a compatible verified current entry.

It selects no plausibility threshold, constructs no segment, and emits no
vessel-activity grid.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Final, Literal, cast

import duckdb
import pyarrow.parquet as pq

from whale_vessel_analysis.ais_processing import (
    AIS_PROCESSING_CONTRACT,
    AIS_PROCESSING_VERSION,
    CLEANED_FILENAME,
    QUALITY_REPORT_FILENAME,
    RUN_METADATA_FILENAME,
)
from whale_vessel_analysis.ais_retrieval import (
    OBSERVATIONAL_COMPLETENESS_REASON,
    RETRIEVAL_MANIFEST_CONTRACT,
    AISRetrievalError,
    load_retrieval_manifest,
)
from whale_vessel_analysis.cleaned_ais_bundle import (
    CleanedAISBundleError,
    canonical_json,
    read_json_object,
    require_mapping,
    sha256_file,
    validate_bundle_layout,
    validate_bundle_sidecars,
    validate_cleaned_schema,
)
from whale_vessel_analysis.config import ANALYTICAL_PERIOD_END, ANALYTICAL_PERIOD_START

MULTIDAY_INPUT_CONTRACT: Final = "multiday_cleaned_ais_input_v1"
MULTIDAY_INPUT_SCHEMA_VERSION: Final = 1
MULTIDAY_INPUT_PROCESSING_VERSION: Final = "1.0.0"
PERIOD_INPUT_ID_PREFIX: Final = "multiday-ais-"
SUPPORTED_CLEANER_CONTRACT: Final = AIS_PROCESSING_CONTRACT
SUPPORTED_CLEANER_PROCESSING_VERSION: Final = AIS_PROCESSING_VERSION

READINESS_REQUIREMENT: Final = (
    "every expected UTC date must carry a compatible, checksum-verified current "
    "cleaner-bundle entry"
)
INSUFFICIENT_READINESS_EVIDENCE: Final = (
    "observed timestamp bounds do not establish complete UTC-day coverage",
    "a filename or directory name is not evidence that a date was delivered",
    "a plausible row count is not evidence that a date is complete",
    "independent retrieval transfer completeness is a separate, unverified state",
    "observational completeness remains unverified for every date",
)
TRANSFER_COMPLETENESS_REASON: Final = (
    "independent byte or archive completeness is established by the retrieval "
    "boundary, not by cleaned-input assembly"
)
IDENTITY_NOTE: Final = (
    "period_input_id is derived from contracts, expected dates, the deterministic "
    "cleaned-Parquet checksums and the deterministic cleaner run identities; the "
    "quality-report and run-metadata checksums are recorded and validated for "
    "integrity but excluded from it, because those sidecars embed local paths and "
    "real execution timestamps"
)
SIDECAR_IDENTITY_NOTE: Final = (
    "quality_report_sha256 and run_metadata_sha256 verify the bundle that was "
    "inspected; they are not part of period_input_id because the cleaner records "
    "local paths and real execution timestamps inside those sidecars"
)
SCOPE_NOTE: Final = (
    "This manifest is a cleaned-input assembly boundary. It selects no maximum "
    "gap, implied-speed, length or edge-support rule, constructs no segment, and "
    "is not a vessel-activity grid or an exposure result."
)

_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
_PROJECT_RAW_ROOT: Final = (_PROJECT_ROOT / "data" / "raw").resolve()
_PROJECT_INTERIM_ROOT: Final = (_PROJECT_ROOT / "data" / "interim").resolve()

DateEntryStatus = Literal["missing", "compatible", "conflict"]
RecordOutcome = Literal[
    "recorded", "identical_retry", "conflict", "conflict_pending_review"
]


class MultiDayAISInputError(ValueError):
    """Raised when a supplied bundle, manifest, or destination is unusable."""


@dataclass(frozen=True, slots=True)
class CleanedDayInspection:
    """One validated cleaner bundle bound to exactly one accepted UTC date."""

    bundle_path: Path
    cleaned_path: Path
    utc_date: str
    cleaner_contract: str
    cleaner_processing_version: str
    cleaner_run_id: str
    cleaned_sha256: str
    quality_report_sha256: str
    run_metadata_sha256: str
    cleaned_rows: int
    observed_utc_dates: tuple[str, ...]
    temporal_coverage: Mapping[str, object]

    def identity_dict(self) -> dict[str, object]:
        """Return the path-free identity recorded in manifest history."""
        return {
            "cleaner_contract": self.cleaner_contract,
            "cleaner_processing_version": self.cleaner_processing_version,
            "cleaner_run_id": self.cleaner_run_id,
            "cleaned_parquet_sha256": self.cleaned_sha256,
            "quality_report_sha256": self.quality_report_sha256,
            "run_metadata_sha256": self.run_metadata_sha256,
            "cleaned_rows": self.cleaned_rows,
            "observed_utc_date": self.utc_date,
        }


@dataclass(frozen=True, slots=True)
class DayOutcome:
    """What one supplied bundle did to the period manifest."""

    utc_date: str
    outcome: RecordOutcome
    entry_status: DateEntryStatus
    cleaned_sha256: str
    bundle_path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "utc_date": self.utc_date,
            "outcome": self.outcome,
            "entry_status": self.entry_status,
            "cleaned_parquet_sha256": self.cleaned_sha256,
            "bundle_path": str(self.bundle_path),
        }


@dataclass(frozen=True, slots=True)
class PeriodManifestUpdate:
    """One completed atomic manifest publication plus execution facts."""

    manifest_path: Path
    manifest: Mapping[str, object]
    outcomes: tuple[DayOutcome, ...]
    started_at: datetime
    completed_at: datetime

    @property
    def period_input_id(self) -> str:
        return cast(str, self.manifest["period_input_id"])

    @property
    def ready(self) -> bool:
        readiness = require_mapping(
            self.manifest["period_input_readiness"], "period_input_readiness"
        )
        return readiness.get("status") == "ready"

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest": {
                "path": str(self.manifest_path),
                "contract": MULTIDAY_INPUT_CONTRACT,
                "period_input_id": self.period_input_id,
            },
            "recorded_dates": [outcome.to_dict() for outcome in self.outcomes],
            "period_input_readiness": self.manifest["period_input_readiness"],
            "observational_completeness": self.manifest["observational_completeness"],
            "execution": {
                "started_at": _timestamp(self.started_at),
                "completed_at": _timestamp(self.completed_at),
                "elapsed_seconds": round(
                    (self.completed_at - self.started_at).total_seconds(), 6
                ),
                "identity_note": IDENTITY_NOTE,
            },
        }


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def accepted_utc_dates() -> tuple[str, ...]:
    """Return every accepted analytical-period UTC date in calendar order."""
    day_count = (ANALYTICAL_PERIOD_END - ANALYTICAL_PERIOD_START).days + 1
    return tuple(
        date.fromordinal(ANALYTICAL_PERIOD_START.toordinal() + offset).isoformat()
        for offset in range(day_count)
    )


def _analytical_period() -> dict[str, object]:
    return {
        "start_utc_date": ANALYTICAL_PERIOD_START.isoformat(),
        "end_utc_date": ANALYTICAL_PERIOD_END.isoformat(),
        "expected_utc_date_count": len(accepted_utc_dates()),
        "decision": "ADR 0005",
    }


def _cleaner_compatibility() -> dict[str, object]:
    return {
        "contract": SUPPORTED_CLEANER_CONTRACT,
        "processing_version": SUPPORTED_CLEANER_PROCESSING_VERSION,
        "required_files": sorted(
            (CLEANED_FILENAME, QUALITY_REPORT_FILENAME, RUN_METADATA_FILENAME)
        ),
    }


def _observational_completeness() -> dict[str, object]:
    return {"status": "unverified", "reason": OBSERVATIONAL_COMPLETENESS_REASON}


def _unsupplied_retrieval_state() -> dict[str, object]:
    return {
        "status": "not_supplied",
        "manifest_contract": None,
        "entry_status": None,
        "source_availability_status": None,
        "date_verification_status": None,
        "attempt_count": None,
    }


def _unverified_retention_state() -> dict[str, object]:
    return {
        "retained_byte_identity": "unverified",
        "source_byte_size": None,
        "source_sha256": None,
        "independent_byte_completeness": "unverified",
        "byte_completeness_evidence": None,
        "archive_verification": None,
        "basis": "no retrieval manifest entry was supplied for this UTC date",
    }


LINKAGE_FIELDS: Final = (
    "cleaned_parquet_sha256",
    "quality_report_sha256",
    "run_metadata_sha256",
)


@dataclass(frozen=True, slots=True)
class RetrievalDateState:
    """One retrieval-manifest date as this contract records it."""

    manifest_state: dict[str, object]
    retention_state: dict[str, object]
    cleaning_reference: Mapping[str, object] | None


def _linkage(
    status: str, reason: str, reference: Mapping[str, object] | None = None
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "reason": reason,
        "reference_contract": (
            None if reference is None else reference.get("contract")
        ),
    }
    for field in LINKAGE_FIELDS:
        payload[f"reference_{field}"] = (
            None if reference is None else reference.get(field)
        )
    return payload


def _unsupplied_linkage() -> dict[str, object]:
    return _linkage(
        "not_supplied", "no retrieval manifest was supplied for this period input"
    )


def _cleaner_linkage(
    utc_date: str,
    entry: Mapping[str, object],
    reference: Mapping[str, object] | None,
) -> dict[str, object]:
    """Bind one retrieval cleaning_reference to the recorded cleaner bundle."""
    if reference is None:
        return _linkage(
            "unverified",
            "the supplied retrieval manifest records no cleaning_reference for "
            "this UTC date",
        )
    compatibility = entry.get("cleaner_bundle_compatibility")
    if compatibility is None:
        return _linkage(
            "unverified",
            "no compatible cleaner bundle is recorded for this UTC date, so the "
            "retrieval cleaning_reference cannot be bound to one",
            reference,
        )
    recorded = require_mapping(compatibility, "cleaner_bundle_compatibility")
    present = [field for field in LINKAGE_FIELDS if reference.get(field) is not None]
    mismatched = [
        field for field in present if reference.get(field) != recorded.get(field)
    ]
    if mismatched:
        raise MultiDayAISInputError(
            f"retrieval cleaning_reference for {utc_date} identifies a different "
            f"cleaner bundle than the recorded one ({', '.join(sorted(mismatched))} "
            "differ)"
        )
    if not present:
        return _linkage(
            "unverified",
            "the retrieval cleaning_reference carries no cleaner checksum to bind",
            reference,
        )
    missing = [field for field in LINKAGE_FIELDS if field not in present]
    if missing:
        return _linkage(
            "unverified",
            "the retrieval cleaning_reference matches the recorded bundle but omits "
            f"{', '.join(sorted(missing))}",
            reference,
        )
    return _linkage(
        "verified",
        "cleaned-Parquet, quality-report and run-metadata checksums match the "
        "retrieval manifest's cleaning_reference",
        reference,
    )


def _missing_entry(utc_date: str) -> dict[str, object]:
    return {
        "utc_date": utc_date,
        "status": "missing",
        "status_reason": "no compatible verified cleaner bundle has been recorded",
        "retrieval_manifest_state": _unsupplied_retrieval_state(),
        "independent_retention_state": _unverified_retention_state(),
        "retrieval_to_cleaner_linkage": _unsupplied_linkage(),
        "cleaner_bundle_compatibility": None,
        "observational_completeness": _observational_completeness(),
        "attempt_history": [],
        "local_provenance": None,
    }


def empty_period_manifest() -> dict[str, object]:
    """Return a manifest that expects all accepted dates and has none of them."""
    expected = accepted_utc_dates()
    manifest: dict[str, object] = {
        "contract": MULTIDAY_INPUT_CONTRACT,
        "schema_version": MULTIDAY_INPUT_SCHEMA_VERSION,
        "processing_version": MULTIDAY_INPUT_PROCESSING_VERSION,
        "analytical_period": _analytical_period(),
        "cleaner_compatibility": _cleaner_compatibility(),
        "expected_utc_dates": list(expected),
        "dates": [_missing_entry(utc_date) for utc_date in expected],
        "observational_completeness": _observational_completeness(),
        "scope_note": SCOPE_NOTE,
        "local_provenance": None,
    }
    refresh_period_manifest(manifest)
    return manifest


def _entries(manifest: Mapping[str, object]) -> list[dict[str, object]]:
    dates = manifest.get("dates")
    if not isinstance(dates, list):
        raise MultiDayAISInputError("period manifest dates must be a list")
    for entry in dates:
        if not isinstance(entry, dict):
            raise MultiDayAISInputError("every period manifest date must be an object")
    return cast(list[dict[str, object]], dates)


def _readiness(entries: Sequence[Mapping[str, object]]) -> dict[str, object]:
    expected = accepted_utc_dates()
    compatible = [
        cast(str, entry["utc_date"])
        for entry in entries
        if entry.get("status") == "compatible"
    ]
    conflicting = [
        cast(str, entry["utc_date"])
        for entry in entries
        if entry.get("status") == "conflict"
    ]
    missing = sorted(set(expected) - set(compatible))
    return {
        "status": "ready" if not missing else "not_ready",
        "requirement": READINESS_REQUIREMENT,
        "expected_date_count": len(expected),
        "compatible_date_count": len(compatible),
        "missing_date_count": len(missing),
        "conflicting_date_count": len(conflicting),
        "missing_expected_utc_dates": missing,
        "conflicting_utc_dates": sorted(conflicting),
        "insufficient_evidence": list(INSUFFICIENT_READINESS_EVIDENCE),
    }


def _retrieval_reference(
    entries: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    supplied = [
        entry
        for entry in entries
        if require_mapping(
            entry["retrieval_manifest_state"], "retrieval_manifest_state"
        ).get("status")
        != "not_supplied"
    ]
    verified = [
        entry
        for entry in entries
        if require_mapping(
            entry["retrieval_manifest_state"], "retrieval_manifest_state"
        ).get("entry_status")
        == "verified"
    ]
    linked = [
        entry
        for entry in entries
        if require_mapping(
            entry["retrieval_to_cleaner_linkage"], "retrieval_to_cleaner_linkage"
        ).get("status")
        == "verified"
    ]
    return {
        "status": "supplied" if supplied else "not_supplied",
        "manifest_contract": RETRIEVAL_MANIFEST_CONTRACT if supplied else None,
        "verified_retrieval_date_count": len(verified),
        "verified_cleaner_linkage_date_count": len(linked),
        "note": (
            "retrieval-manifest state is recorded separately; it neither gates nor "
            "satisfies cleaned-input readiness"
        ),
        "linkage_note": (
            "a date is linkage-verified only when the retrieval manifest's "
            "cleaning_reference checksums match the recorded cleaner bundle; a "
            "mismatched reference is refused rather than recorded"
        ),
    }


def _transfer_completeness(
    entries: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    complete = [
        entry
        for entry in entries
        if require_mapping(
            entry["independent_retention_state"], "independent_retention_state"
        ).get("independent_byte_completeness")
        == "verified"
    ]
    return {
        "status": "verified"
        if len(complete) == len(accepted_utc_dates())
        else ("unverified"),
        "independently_complete_date_count": len(complete),
        "expected_date_count": len(accepted_utc_dates()),
        "reason": TRANSFER_COMPLETENESS_REASON,
    }


def period_input_identity_material(manifest: Mapping[str, object]) -> dict[str, object]:
    """Return only the content that determines the deterministic period identity."""
    entries = _entries(manifest)
    dates: list[dict[str, object]] = []
    for entry in entries:
        compatibility = entry.get("cleaner_bundle_compatibility")
        identity: dict[str, object] | None = None
        if compatibility is not None:
            mapping = require_mapping(compatibility, "cleaner_bundle_compatibility")
            identity = {
                "cleaner_contract": mapping.get("cleaner_contract"),
                "cleaner_processing_version": mapping.get("cleaner_processing_version"),
                "cleaner_run_id": mapping.get("cleaner_run_id"),
                "cleaned_parquet_sha256": mapping.get("cleaned_parquet_sha256"),
                "cleaned_rows": mapping.get("cleaned_rows"),
                "observed_utc_date": mapping.get("observed_utc_date"),
            }
        dates.append(
            {
                "utc_date": entry.get("utc_date"),
                "status": entry.get("status"),
                "cleaner_bundle_identity": identity,
            }
        )
    return {
        "contract": manifest.get("contract"),
        "schema_version": manifest.get("schema_version"),
        "processing_version": manifest.get("processing_version"),
        "analytical_period": manifest.get("analytical_period"),
        "cleaner_compatibility": manifest.get("cleaner_compatibility"),
        "expected_utc_dates": manifest.get("expected_utc_dates"),
        "dates": dates,
    }


def compute_period_input_id(manifest: Mapping[str, object]) -> str:
    """Derive the path- and clock-independent period-input identifier."""
    material = period_input_identity_material(manifest)
    digest = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return PERIOD_INPUT_ID_PREFIX + digest[:24]


def refresh_period_manifest(manifest: dict[str, object]) -> None:
    """Recompute ordering, summaries, and the deterministic period identity."""
    entries = _entries(manifest)
    entries.sort(key=lambda entry: cast(str, entry["utc_date"]))
    manifest["period_input_readiness"] = _readiness(entries)
    manifest["retrieval_manifest_reference"] = _retrieval_reference(entries)
    manifest["independent_transfer_completeness"] = _transfer_completeness(entries)
    manifest["observational_completeness"] = _observational_completeness()
    manifest["period_input_id"] = compute_period_input_id(manifest)


def load_period_manifest(path: Path) -> dict[str, object]:
    """Load, validate, and self-check an existing period manifest."""
    if not path.exists():
        return empty_period_manifest()
    if not path.is_file():
        raise MultiDayAISInputError(f"manifest path is not a regular file: {path}")
    try:
        payload = read_json_object(path, "period manifest")
    except CleanedAISBundleError as exc:
        raise MultiDayAISInputError(str(exc)) from exc
    manifest = dict(payload)
    if manifest.get("contract") != MULTIDAY_INPUT_CONTRACT:
        raise MultiDayAISInputError(
            "existing manifest has an incompatible multi-day input contract"
        )
    if manifest.get("schema_version") != MULTIDAY_INPUT_SCHEMA_VERSION:
        raise MultiDayAISInputError("existing manifest has an incompatible schema")
    expected = manifest.get("expected_utc_dates")
    if expected != list(accepted_utc_dates()):
        raise MultiDayAISInputError(
            "expected_utc_dates must equal the complete accepted analytical period"
        )
    entries = _entries(manifest)
    observed: list[str] = []
    for entry in entries:
        utc_date = entry.get("utc_date")
        if not isinstance(utc_date, str):
            raise MultiDayAISInputError("every period manifest date needs a UTC date")
        if entry.get("status") not in ("missing", "compatible", "conflict"):
            raise MultiDayAISInputError(f"invalid manifest date status for {utc_date}")
        if not isinstance(entry.get("attempt_history"), list):
            raise MultiDayAISInputError(
                f"date {utc_date} must carry an attempt history"
            )
        require_mapping(
            entry.get("retrieval_manifest_state"), "retrieval_manifest_state"
        )
        require_mapping(
            entry.get("independent_retention_state"), "independent_retention_state"
        )
        require_mapping(
            entry.get("retrieval_to_cleaner_linkage"), "retrieval_to_cleaner_linkage"
        )
        observed.append(utc_date)
    if len(set(observed)) != len(observed):
        raise MultiDayAISInputError(
            "period manifest contains a duplicate current UTC-date entry"
        )
    if sorted(observed) != list(accepted_utc_dates()):
        raise MultiDayAISInputError(
            "period manifest dates must be exactly the accepted analytical period"
        )
    recorded_readiness = manifest.get("period_input_readiness")
    recorded_id = manifest.get("period_input_id")
    refresh_period_manifest(manifest)
    if recorded_readiness != manifest["period_input_readiness"]:
        raise MultiDayAISInputError(
            "period_input_readiness does not match the recorded date entries"
        )
    if recorded_id != manifest["period_input_id"]:
        raise MultiDayAISInputError(
            "period_input_id does not match deterministic manifest content"
        )
    return manifest


def _is_under_data_raw(path: Path) -> bool:
    parts = [part.casefold() for part in path.parts]
    return any(
        parts[index] == "data" and parts[index + 1] == "raw"
        for index in range(len(parts) - 1)
    )


def validate_ignored_local_directory(path: Path, label: str) -> Path:
    """Require an explicit working directory under ignored, non-raw local storage."""
    resolved = path.resolve()
    if (
        _is_under_data_raw(resolved)
        or resolved == _PROJECT_RAW_ROOT
        or resolved.is_relative_to(_PROJECT_RAW_ROOT)
    ):
        raise MultiDayAISInputError(
            f"{label} cannot be placed under raw data: {resolved}"
        )
    if not (
        resolved == _PROJECT_INTERIM_ROOT
        or resolved.is_relative_to(_PROJECT_INTERIM_ROOT)
    ):
        raise MultiDayAISInputError(
            f"{label} must be an explicit path under ignored data/interim"
        )
    if resolved.exists() and not resolved.is_dir():
        raise MultiDayAISInputError(f"{label} is not a directory: {resolved}")
    return resolved


def validate_manifest_destination(path: Path) -> Path:
    """Require an explicit, ignored, non-raw JSON destination for the manifest."""
    resolved = path.resolve()
    if (
        _is_under_data_raw(resolved)
        or resolved == _PROJECT_RAW_ROOT
        or resolved.is_relative_to(_PROJECT_RAW_ROOT)
    ):
        raise MultiDayAISInputError(
            f"period manifest cannot be written under raw data: {resolved}"
        )
    if not (
        resolved == _PROJECT_INTERIM_ROOT
        or resolved.is_relative_to(_PROJECT_INTERIM_ROOT)
    ):
        raise MultiDayAISInputError(
            "period manifest must be an explicit path under ignored data/interim"
        )
    if resolved.suffix.lower() != ".json":
        raise MultiDayAISInputError("period manifest path must end in .json")
    if resolved.exists() and not resolved.is_file():
        raise MultiDayAISInputError(f"period manifest is not a file: {resolved}")
    if resolved.exists():
        try:
            existing = read_json_object(resolved, "existing period manifest")
        except CleanedAISBundleError as exc:
            raise MultiDayAISInputError(str(exc)) from exc
        if existing.get("contract") != MULTIDAY_INPUT_CONTRACT:
            raise MultiDayAISInputError(
                "refusing to overwrite a file that is not a "
                f"{MULTIDAY_INPUT_CONTRACT} manifest"
            )
    return resolved


def write_period_manifest_atomic(
    path: Path, manifest: Mapping[str, object]
) -> tuple[Path, str]:
    """Publish one manifest atomically and return its path and checksum."""
    resolved = validate_manifest_destination(path)
    if manifest.get("contract") != MULTIDAY_INPUT_CONTRACT:
        raise MultiDayAISInputError("manifest contract is invalid")
    if manifest.get("period_input_id") != compute_period_input_id(manifest):
        raise MultiDayAISInputError(
            "period_input_id does not match deterministic manifest content"
        )
    payload = (canonical_json(dict(manifest)) + "\n").encode("utf-8")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{resolved.name}.temporary-", dir=resolved.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        _replace_file(temporary, resolved)
    except Exception as exc:
        raise MultiDayAISInputError(
            f"could not publish period manifest atomically: {exc}"
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)
    return resolved, hashlib.sha256(payload).hexdigest()


def _replace_file(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def _observed_dates_and_rows(cleaned_path: Path) -> tuple[tuple[str, ...], int]:
    query = f"""
        SELECT CAST(observed_at_utc AS DATE) AS utc_date, count(*) AS rows
        FROM read_parquet({_sql_string(cleaned_path)})
        GROUP BY 1
        ORDER BY 1
    """
    try:
        with duckdb.connect(":memory:") as connection:
            connection.execute("SET TimeZone = 'UTC'")
            rows = connection.execute(query).fetchall()
    except duckdb.Error as exc:
        raise MultiDayAISInputError(
            f"could not read cleaned Parquet {cleaned_path}: {exc}"
        ) from exc
    dates = tuple(cast(date, row[0]).isoformat() for row in rows)
    total = sum(int(cast(int, row[1])) for row in rows)
    return dates, total


def _sql_string(value: Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def inspect_cleaned_day(bundle_path: Path) -> CleanedDayInspection:
    """Validate one supplied cleaner bundle as exactly one accepted UTC date."""
    try:
        resolved = validate_bundle_layout(bundle_path)
        cleaned_path = resolved / CLEANED_FILENAME
        cleaned_sha256 = sha256_file(cleaned_path)
        sidecars = validate_bundle_sidecars(resolved, cleaned_sha256)
        validate_cleaned_schema(pq.read_schema(cleaned_path))
    except CleanedAISBundleError as exc:
        raise MultiDayAISInputError(str(exc)) from exc
    except OSError as exc:
        raise MultiDayAISInputError(
            f"could not read cleaned Parquet in {bundle_path}: {exc}"
        ) from exc
    if sidecars.cleaner_contract != SUPPORTED_CLEANER_CONTRACT:
        raise MultiDayAISInputError(
            f"cleaner bundle contract must be {SUPPORTED_CLEANER_CONTRACT}"
        )
    if sidecars.cleaning_step_version != SUPPORTED_CLEANER_PROCESSING_VERSION:
        raise MultiDayAISInputError(
            "cleaner bundle processing version must be "
            f"{SUPPORTED_CLEANER_PROCESSING_VERSION}"
        )
    observed_dates, cleaned_rows = _observed_dates_and_rows(cleaned_path)
    if len(observed_dates) != 1:
        raise MultiDayAISInputError(
            "cleaned Parquet must contain exactly one UTC date, found "
            f"{len(observed_dates)}"
        )
    utc_date = observed_dates[0]
    reported_date = sidecars.temporal_coverage.get("observed_utc_date")
    if reported_date != utc_date:
        raise MultiDayAISInputError(
            "quality-report observed UTC date does not match the cleaned Parquet"
        )
    completeness = require_mapping(
        sidecars.temporal_coverage.get("completeness"), "temporal completeness"
    )
    if completeness.get("status") != "unverified":
        raise MultiDayAISInputError(
            "cleaner temporal completeness must remain unverified; an upgraded "
            "completeness claim is refused"
        )
    quality_output = require_mapping(
        sidecars.quality_report.get("output"), "quality report output"
    )
    if quality_output.get("rows") != cleaned_rows:
        raise MultiDayAISInputError(
            "quality-report row count does not match the cleaned Parquet"
        )
    if utc_date not in accepted_utc_dates():
        raise MultiDayAISInputError(
            f"cleaned bundle UTC date {utc_date} is outside the accepted "
            "analytical period"
        )
    return CleanedDayInspection(
        bundle_path=resolved,
        cleaned_path=cleaned_path,
        utc_date=utc_date,
        cleaner_contract=sidecars.cleaner_contract,
        cleaner_processing_version=SUPPORTED_CLEANER_PROCESSING_VERSION,
        cleaner_run_id=sidecars.cleaner_run_id,
        cleaned_sha256=cleaned_sha256,
        quality_report_sha256=sidecars.quality_report_sha256,
        run_metadata_sha256=sidecars.run_metadata_sha256,
        cleaned_rows=cleaned_rows,
        observed_utc_dates=observed_dates,
        temporal_coverage=sidecars.temporal_coverage,
    )


def _compatibility_payload(inspection: CleanedDayInspection) -> dict[str, object]:
    return {
        "status": "compatible",
        **inspection.identity_dict(),
        "temporal_coverage": dict(inspection.temporal_coverage),
        "sidecar_identity_note": SIDECAR_IDENTITY_NOTE,
        "completeness_note": (
            "observed timestamp bounds do not establish complete UTC-day coverage"
        ),
    }


def _attempt(
    number: int,
    outcome: RecordOutcome,
    reason: str | None,
    inspection: CleanedDayInspection,
    recorded_at: datetime,
) -> dict[str, object]:
    return {
        "attempt_number": number,
        "outcome": outcome,
        "reason": reason,
        "recorded_at_utc": _timestamp(recorded_at),
        "bundle_identity": inspection.identity_dict(),
        "local_provenance": {"bundle_path": str(inspection.bundle_path)},
    }


def _apply_inspection(
    manifest: dict[str, object],
    inspection: CleanedDayInspection,
    recorded_at: datetime,
) -> DayOutcome:
    entries = _entries(manifest)
    entry = next(entry for entry in entries if entry["utc_date"] == inspection.utc_date)
    history = cast(list[dict[str, object]], entry["attempt_history"])
    status = entry["status"]
    if status == "conflict":
        reason = "current date entry remains in conflict pending explicit review"
        history.append(
            _attempt(
                len(history) + 1,
                "conflict_pending_review",
                reason,
                inspection,
                recorded_at,
            )
        )
        entry["status_reason"] = reason
        return DayOutcome(
            inspection.utc_date,
            "conflict_pending_review",
            "conflict",
            inspection.cleaned_sha256,
            inspection.bundle_path,
        )
    if status == "missing":
        history.append(
            _attempt(len(history) + 1, "recorded", None, inspection, recorded_at)
        )
        entry["status"] = "compatible"
        entry["status_reason"] = (
            "three-file bundle, cleaner contract and processing version, run "
            "identity, checksums, and exclusive accepted UTC date verified"
        )
        entry["cleaner_bundle_compatibility"] = _compatibility_payload(inspection)
        entry["local_provenance"] = {
            "bundle_path": str(inspection.bundle_path),
            "cleaned_parquet_path": str(inspection.cleaned_path),
        }
        return DayOutcome(
            inspection.utc_date,
            "recorded",
            "compatible",
            inspection.cleaned_sha256,
            inspection.bundle_path,
        )
    existing = require_mapping(
        entry["cleaner_bundle_compatibility"], "cleaner_bundle_compatibility"
    )
    identical = all(
        existing.get(field) == value
        for field, value in inspection.identity_dict().items()
    )
    if identical:
        history.append(
            _attempt(len(history) + 1, "identical_retry", None, inspection, recorded_at)
        )
        entry["local_provenance"] = {
            "bundle_path": str(inspection.bundle_path),
            "cleaned_parquet_path": str(inspection.cleaned_path),
        }
        return DayOutcome(
            inspection.utc_date,
            "identical_retry",
            "compatible",
            inspection.cleaned_sha256,
            inspection.bundle_path,
        )
    reason = (
        "supplied bundle differs from the recorded current entry for this date; "
        "verified identity was not replaced"
    )
    history.append(
        _attempt(len(history) + 1, "conflict", reason, inspection, recorded_at)
    )
    entry["status"] = "conflict"
    entry["status_reason"] = reason
    return DayOutcome(
        inspection.utc_date,
        "conflict",
        "conflict",
        inspection.cleaned_sha256,
        inspection.bundle_path,
    )


def _retrieval_states(
    retrieval_manifest_path: Path,
) -> dict[str, RetrievalDateState]:
    if not retrieval_manifest_path.is_file():
        raise MultiDayAISInputError(
            f"retrieval manifest does not exist: {retrieval_manifest_path}"
        )
    try:
        retrieval = load_retrieval_manifest(retrieval_manifest_path.resolve())
    except AISRetrievalError as exc:
        raise MultiDayAISInputError(str(exc)) from exc
    states: dict[str, RetrievalDateState] = {}
    for raw_entry in cast(list[object], retrieval["entries"]):
        entry = require_mapping(raw_entry, "retrieval manifest entry")
        utc_date = cast(str, entry["utc_date"])
        verification = entry.get("retrieval_verification")
        identity: Mapping[str, object] = {}
        completeness: Mapping[str, object] = {}
        archive: object = None
        if isinstance(verification, Mapping):
            raw_identity = verification.get("identity")
            if isinstance(raw_identity, Mapping):
                identity = raw_identity
            raw_completeness = verification.get("byte_completeness")
            if isinstance(raw_completeness, Mapping):
                completeness = raw_completeness
            archive = verification.get("archive")
        date_verification = entry.get("date_verification")
        availability = entry.get("source_availability")
        attempts = entry.get("attempt_history")
        manifest_state: dict[str, object] = {
            "status": "recorded",
            "manifest_contract": RETRIEVAL_MANIFEST_CONTRACT,
            "entry_status": entry.get("status"),
            "source_availability_status": (
                availability.get("status")
                if isinstance(availability, Mapping)
                else None
            ),
            "date_verification_status": (
                date_verification.get("status")
                if isinstance(date_verification, Mapping)
                else None
            ),
            "attempt_count": len(attempts) if isinstance(attempts, list) else None,
        }
        retention_state: dict[str, object] = {
            "retained_byte_identity": (
                "verified" if identity.get("sha256") else "unverified"
            ),
            "source_byte_size": identity.get("byte_size"),
            "source_sha256": identity.get("sha256"),
            "independent_byte_completeness": completeness.get("status", "unverified"),
            "byte_completeness_evidence": completeness.get("evidence"),
            "archive_verification": archive,
            "basis": (
                "recorded by the noaa_ais_retrieval_manifest_v1 boundary; retained "
                "byte identity and independent completeness are distinct states"
            ),
        }
        compatibility = entry.get("cleaning_compatibility")
        reference: Mapping[str, object] | None = None
        if isinstance(compatibility, Mapping):
            raw_reference = compatibility.get("cleaning_reference")
            if isinstance(raw_reference, Mapping):
                reference = raw_reference
        manifest_state["cleaning_reference_present"] = reference is not None
        states[utc_date] = RetrievalDateState(
            manifest_state=manifest_state,
            retention_state=retention_state,
            cleaning_reference=reference,
        )
    return states


def _apply_retrieval_states(
    manifest: dict[str, object],
    states: Mapping[str, RetrievalDateState],
) -> None:
    for entry in _entries(manifest):
        utc_date = cast(str, entry["utc_date"])
        state = states.get(utc_date)
        if state is None:
            entry["retrieval_manifest_state"] = {
                "status": "absent",
                "manifest_contract": RETRIEVAL_MANIFEST_CONTRACT,
                "entry_status": None,
                "source_availability_status": None,
                "date_verification_status": None,
                "attempt_count": 0,
                "cleaning_reference_present": False,
            }
            entry["independent_retention_state"] = _unverified_retention_state()
            entry["retrieval_to_cleaner_linkage"] = _linkage(
                "unverified",
                "the supplied retrieval manifest has no entry for this UTC date",
            )
            continue
        entry["retrieval_manifest_state"] = state.manifest_state
        entry["independent_retention_state"] = state.retention_state
        entry["retrieval_to_cleaner_linkage"] = _cleaner_linkage(
            utc_date, entry, state.cleaning_reference
        )


def record_cleaned_days(
    manifest_path: Path,
    bundle_paths: Iterable[Path],
    *,
    retrieval_manifest_path: Path | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> PeriodManifestUpdate:
    """Validate every supplied bundle and publish one updated period manifest."""
    started_at = clock()
    supplied = [Path(path) for path in bundle_paths]
    if not supplied:
        raise MultiDayAISInputError("at least one cleaned bundle must be supplied")
    destination = validate_manifest_destination(manifest_path)
    inspections = [inspect_cleaned_day(path) for path in supplied]
    manifest = load_period_manifest(destination)
    outcomes = tuple(
        _apply_inspection(manifest, inspection, clock()) for inspection in inspections
    )
    if retrieval_manifest_path is not None:
        _apply_retrieval_states(manifest, _retrieval_states(retrieval_manifest_path))
    manifest["local_provenance"] = {
        "manifest_path": str(destination),
        "retrieval_manifest_path": (
            None
            if retrieval_manifest_path is None
            else str(retrieval_manifest_path.resolve())
        ),
        "last_recorded_at_utc": _timestamp(started_at),
        "identity_note": IDENTITY_NOTE,
    }
    refresh_period_manifest(manifest)
    write_period_manifest_atomic(destination, manifest)
    completed_at = clock()
    return PeriodManifestUpdate(
        manifest_path=destination,
        manifest=manifest,
        outcomes=outcomes,
        started_at=started_at,
        completed_at=completed_at,
    )


def period_status(manifest: Mapping[str, object]) -> dict[str, object]:
    """Summarize one loaded manifest without writing anything."""
    entries = _entries(manifest)
    return {
        "contract": manifest["contract"],
        "schema_version": manifest["schema_version"],
        "processing_version": manifest["processing_version"],
        "period_input_id": manifest["period_input_id"],
        "analytical_period": manifest["analytical_period"],
        "cleaner_compatibility": manifest["cleaner_compatibility"],
        "period_input_readiness": manifest["period_input_readiness"],
        "retrieval_manifest_reference": manifest["retrieval_manifest_reference"],
        "independent_transfer_completeness": manifest[
            "independent_transfer_completeness"
        ],
        "observational_completeness": manifest["observational_completeness"],
        "compatible_utc_dates": [
            entry["utc_date"] for entry in entries if entry["status"] == "compatible"
        ],
        "scope_note": manifest["scope_note"],
    }
