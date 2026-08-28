"""Safe local inspection and manifesting for one NOAA AIS delivery."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import IO, Final, Literal, cast
from urllib.parse import urlsplit, urlunsplit

from whale_vessel_analysis.ais import (
    AIS_PUBLISHED_HEADER,
    AISSchemaError,
    validate_header,
)
from whale_vessel_analysis.config import ANALYTICAL_PERIOD_END, ANALYTICAL_PERIOD_START

RETRIEVAL_MANIFEST_CONTRACT: Final = "noaa_ais_retrieval_manifest_v1"
RETRIEVAL_MANIFEST_SCHEMA_VERSION: Final = 1
CSV_BUNDLE_CONTRACT: Final = "noaa_ais_retrieval_csv_bundle_v1"
CSV_BUNDLE_FILENAME: Final = "source.csv"
CSV_BUNDLE_METADATA_FILENAME: Final = "bundle-metadata.json"
OBSERVATIONAL_COMPLETENESS_REASON: Final = (
    "retrieval integrity cannot establish land-receiver coverage, collection "
    "continuity, or records that were never observed"
)

RetrievalRoute = Literal["accessais", "bulk_daily"]

_ZIP_SIGNATURES: Final = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_EMAIL_PATTERN: Final = re.compile(
    r"(?i)\b[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+\b"
)
_SECRET_PAIR_PATTERN: Final = re.compile(
    r"(?i)\b(token|access_token|signature|sig|key|api_key|code|expires)"
    r"\s*[=:]\s*[^&\s]+"
)
_WINDOWS_DRIVE_PATTERN: Final = re.compile(r"^[a-zA-Z]:")
_TIMESTAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%S"


class AISRetrievalError(ValueError):
    """Raised when a retrieval artifact or manifest is unsafe or incompatible."""


class AISRetrievalConflictError(AISRetrievalError):
    """Raised when new bytes conflict with a verified current date entry."""


@dataclass(frozen=True, slots=True)
class RequestBounds:
    """Inclusive requested dates and WGS 84 longitude/latitude bounds."""

    from_date: date
    through_date: date
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float

    def __post_init__(self) -> None:
        if self.from_date > self.through_date:
            raise AISRetrievalError("requested from-date cannot follow through-date")
        coordinates = (self.lon_min, self.lat_min, self.lon_max, self.lat_max)
        if not all(math.isfinite(value) for value in coordinates):
            raise AISRetrievalError("requested WGS 84 bounds must be finite")
        if not -180.0 <= self.lon_min < self.lon_max <= 180.0:
            raise AISRetrievalError("requested longitude bounds are invalid")
        if not -90.0 <= self.lat_min < self.lat_max <= 90.0:
            raise AISRetrievalError("requested latitude bounds are invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "from_date": self.from_date.isoformat(),
            "through_date": self.through_date.isoformat(),
            "bounds_wgs84": {
                "coordinate_order": "longitude_latitude",
                "lon_min": self.lon_min,
                "lat_min": self.lat_min,
                "lon_max": self.lon_max,
                "lat_max": self.lat_max,
            },
        }


@dataclass(frozen=True, slots=True)
class SourceHttpMetadata:
    """Optional author-supplied HTTP metadata, never a checksum substitute."""

    content_length: int | None = None
    etag: str | None = None
    last_modified: str | None = None

    def __post_init__(self) -> None:
        if self.content_length is not None and self.content_length < 0:
            raise AISRetrievalError("HTTP Content-Length cannot be negative")
        for value, name in (
            (self.etag, "ETag"),
            (self.last_modified, "Last-Modified"),
        ):
            if value is not None and not value.strip():
                raise AISRetrievalError(f"HTTP {name} cannot be blank")
            if value is not None and (
                _EMAIL_PATTERN.search(value) or _SECRET_PAIR_PATTERN.search(value)
            ):
                raise AISRetrievalError(f"HTTP {name} contains sensitive text")

    def to_dict(self) -> dict[str, object]:
        return {
            "content_length": self.content_length,
            "etag": self.etag,
            "last_modified": self.last_modified,
        }


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Token-free local provenance supplied for one retained delivery."""

    expected_utc_date: date
    route: RetrievalRoute
    request_id: str
    source_reference: str
    request_parameters: RequestBounds
    source_filename: str
    retrieved_at_utc: datetime
    source_http_metadata: SourceHttpMetadata = SourceHttpMetadata()

    def __post_init__(self) -> None:
        if self.route not in ("accessais", "bulk_daily"):
            raise AISRetrievalError(f"unsupported retrieval route: {self.route}")
        if not self.request_id.strip():
            raise AISRetrievalError("request_id cannot be blank")
        if _EMAIL_PATTERN.search(self.request_id) or _SECRET_PAIR_PATTERN.search(
            self.request_id
        ):
            raise AISRetrievalError("request_id must be a token-free local identifier")
        if not self.source_reference.strip():
            raise AISRetrievalError("source_reference cannot be blank")
        if not self.source_filename.strip():
            raise AISRetrievalError("source_filename cannot be blank")
        if Path(self.source_filename).name != self.source_filename or any(
            separator in self.source_filename for separator in ("/", "\\")
        ):
            raise AISRetrievalError(
                "source_filename must be the NOAA-supplied basename"
            )
        if _EMAIL_PATTERN.search(self.source_filename) or _SECRET_PAIR_PATTERN.search(
            self.source_filename
        ):
            raise AISRetrievalError("source_filename cannot contain sensitive text")
        if self.retrieved_at_utc.utcoffset() != UTC.utcoffset(self.retrieved_at_utc):
            raise AISRetrievalError("retrieved_at_utc must be timezone-aware UTC")
        if not (
            self.request_parameters.from_date
            <= self.expected_utc_date
            <= self.request_parameters.through_date
        ):
            raise AISRetrievalError(
                "expected UTC date must fall inside the exact requested dates"
            )
        if not (
            ANALYTICAL_PERIOD_START <= self.expected_utc_date <= ANALYTICAL_PERIOD_END
        ):
            raise AISRetrievalError(
                "expected UTC date must fall inside the accepted analytical period"
            )
        if self.route == "bulk_daily" and (
            self.request_parameters.from_date != self.expected_utc_date
            or self.request_parameters.through_date != self.expected_utc_date
        ):
            raise AISRetrievalError(
                "bulk_daily requests must describe exactly one date"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "utc_date": self.expected_utc_date.isoformat(),
            "route": self.route,
            "request_id": self.request_id,
            "source_reference": redact_source_reference(
                self.source_reference, self.route
            ),
            "request_parameters": self.request_parameters.to_dict(),
            "source_filename": self.source_filename,
            "retrieved_at_utc": _utc_timestamp(self.retrieved_at_utc),
            "source_http_metadata": self.source_http_metadata.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class CSVDateInspection:
    """Header and UTC-date findings from one selected CSV stream."""

    row_count: int
    valid_timestamp_rows: int
    invalid_timestamp_rows: int
    observed_utc_dates: tuple[str, ...]
    earliest_valid_observed_at_utc: str
    latest_valid_observed_at_utc: str

    def to_dict(self) -> dict[str, object]:
        return {
            "header_contract": "noaa_marine_cadastre_ais_flat_csv_v1",
            "header_valid": True,
            "row_count": self.row_count,
            "valid_timestamp_rows": self.valid_timestamp_rows,
            "invalid_timestamp_rows": self.invalid_timestamp_rows,
            "observed_utc_dates": list(self.observed_utc_dates),
            "earliest_valid_observed_at_utc": self.earliest_valid_observed_at_utc,
            "latest_valid_observed_at_utc": self.latest_valid_observed_at_utc,
            "expected_date_match": True,
        }


@dataclass(frozen=True, slots=True)
class ArtifactInspection:
    """Identity, container, CRC, header, and date evidence for retained bytes."""

    byte_size: int
    sha256: str
    container: Literal["csv", "zip"]
    archive_members: tuple[str, ...]
    selected_csv_member: str | None
    crc_valid: bool | None
    source_content_length_match: bool | None
    date_inspection: CSVDateInspection

    @property
    def byte_complete(self) -> bool:
        """Whether retained bytes have independent transfer/container completeness."""
        return self.source_content_length_match is True or (
            self.container == "zip" and self.crc_valid is True
        )

    def identity_dict(self) -> dict[str, object]:
        return {"byte_size": self.byte_size, "sha256": self.sha256}

    def archive_dict(self) -> dict[str, object]:
        return {
            "container_detected_by_content": self.container,
            "archive_valid": True if self.container == "zip" else None,
            "crc_valid": self.crc_valid,
            "members": list(self.archive_members),
            "selected_csv_member": self.selected_csv_member,
            "csv_member_selection": "unambiguous",
        }


@dataclass(frozen=True, slots=True)
class ManifestUpdate:
    """Outcome from an atomic manifest update."""

    outcome: Literal["verified", "identical_retry", "conflict", "failed"]
    entry_status: str
    manifest: dict[str, object]


@dataclass(frozen=True, slots=True)
class CSVBundleResult:
    """A published or safely reused interim CSV bundle."""

    directory: Path
    csv_path: Path
    metadata_path: Path
    csv_byte_size: int
    csv_sha256: str
    reused: bool


def _utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_utc_timestamp(value: str) -> datetime:
    """Parse a supplied retrieval timestamp and require an explicit UTC offset."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AISRetrievalError(f"invalid UTC timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise AISRetrievalError("retrieval timestamp must carry an explicit UTC offset")
    return parsed.astimezone(UTC)


def redact_source_reference(reference: str, route: RetrievalRoute) -> str:
    """Remove email addresses, credentials, queries, fragments, and delivery paths."""
    stripped = reference.strip()
    parsed = urlsplit(stripped)
    if parsed.scheme.lower() in ("http", "https") and parsed.netloc:
        hostname = parsed.hostname or "[redacted-host]"
        port = f":{parsed.port}" if parsed.port is not None else ""
        if route == "accessais":
            return urlunsplit(
                (parsed.scheme.lower(), hostname + port, "/[redacted-delivery]", "", "")
            )
        query_marker = "redacted" if parsed.query else ""
        fragment = "redacted" if parsed.fragment else ""
        return urlunsplit(
            (
                parsed.scheme.lower(),
                hostname + port,
                parsed.path,
                query_marker,
                fragment,
            )
        )
    redacted = _EMAIL_PATTERN.sub("[redacted-email]", stripped)
    redacted = _SECRET_PAIR_PATTERN.sub(r"\1=[redacted]", redacted)
    return redacted


def _redact_free_text(value: str) -> str:
    redacted = _EMAIL_PATTERN.sub("[redacted-email]", value)
    return _SECRET_PAIR_PATTERN.sub(r"\1=[redacted]", redacted)


def _fingerprint_regular_file(path: Path) -> tuple[int, str, int]:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise AISRetrievalError(f"source artifact does not exist: {path}") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise AISRetrievalError(f"source artifact is not a regular file: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise AISRetrievalError(f"could not read source artifact: {path}") from exc
    return metadata.st_size, digest.hexdigest(), metadata.st_mtime_ns


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not name
        or "\x00" in name
        or normalized.startswith("/")
        or _WINDOWS_DRIVE_PATTERN.match(normalized)
        or ".." in path.parts
    ):
        raise AISRetrievalError(f"unsafe archive member path: {name!r}")
    if _EMAIL_PATTERN.search(name) or _SECRET_PAIR_PATTERN.search(name):
        raise AISRetrievalError("archive member name contains sensitive text")
    return normalized


def _inspect_csv_stream(source: IO[bytes], expected_date: date) -> CSVDateInspection:
    import io

    text_source = io.TextIOWrapper(source, encoding="utf-8", newline="")
    try:
        reader = csv.reader(text_source, strict=True)
        header = next(reader, None)
        if header is None:
            raise AISRetrievalError("selected CSV is empty")
        try:
            validate_header(header)
        except AISSchemaError as exc:
            raise AISRetrievalError(str(exc)) from exc
        row_count = 0
        valid_timestamp_rows = 0
        invalid_timestamp_rows = 0
        observed_date_values: set[str] = set()
        earliest: datetime | None = None
        latest: datetime | None = None
        timestamp_index = AIS_PUBLISHED_HEADER.index("BaseDateTime")
        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            if len(row) != len(AIS_PUBLISHED_HEADER):
                raise AISRetrievalError(
                    f"CSV row {row_number} has {len(row)} fields; "
                    f"expected {len(AIS_PUBLISHED_HEADER)}"
                )
            try:
                observed = datetime.strptime(
                    row[timestamp_index], _TIMESTAMP_FORMAT
                ).replace(tzinfo=UTC)
            except ValueError:
                invalid_timestamp_rows += 1
                continue
            valid_timestamp_rows += 1
            observed_date_values.add(observed.date().isoformat())
            earliest = observed if earliest is None else min(earliest, observed)
            latest = observed if latest is None else max(latest, observed)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise AISRetrievalError(
            f"selected member is not compatible UTF-8 CSV: {exc}"
        ) from exc
    finally:
        text_source.detach()
    if row_count == 0:
        raise AISRetrievalError("selected CSV contains zero data rows")
    if valid_timestamp_rows == 0 or earliest is None or latest is None:
        raise AISRetrievalError("selected CSV contains zero valid UTC timestamps")
    observed_dates = tuple(sorted(observed_date_values))
    expected = expected_date.isoformat()
    if observed_dates != (expected,):
        raise AISRetrievalError(
            "valid timestamps do not belong exclusively to expected UTC date "
            f"{expected}; found {', '.join(observed_dates)}"
        )
    return CSVDateInspection(
        row_count=row_count,
        valid_timestamp_rows=valid_timestamp_rows,
        invalid_timestamp_rows=invalid_timestamp_rows,
        observed_utc_dates=observed_dates,
        earliest_valid_observed_at_utc=_utc_timestamp(earliest),
        latest_valid_observed_at_utc=_utc_timestamp(latest),
    )


def inspect_ais_artifact(
    path: Path,
    expected_utc_date: date,
    *,
    source_content_length: int | None = None,
) -> ArtifactInspection:
    """Inspect a local artifact without modifying or extracting it."""
    path = path.resolve()
    byte_size, sha256, initial_mtime_ns = _fingerprint_regular_file(path)
    if source_content_length is not None and source_content_length != byte_size:
        raise AISRetrievalError(
            f"source Content-Length {source_content_length} does not match "
            f"local byte size {byte_size}"
        )
    with path.open("rb") as source:
        signature = source.read(4)
    if signature in _ZIP_SIGNATURES:
        try:
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
                normalized_names = tuple(
                    _safe_member_name(info.filename) for info in infos
                )
                csv_infos = [
                    info
                    for info, normalized in zip(infos, normalized_names, strict=True)
                    if not info.is_dir() and normalized.lower().endswith(".csv")
                ]
                if not csv_infos:
                    raise AISRetrievalError("archive contains no CSV member")
                if len(csv_infos) > 1:
                    names = ", ".join(info.filename for info in csv_infos)
                    raise AISRetrievalError(
                        f"archive contains multiple ambiguous CSV members: {names}"
                    )
                selected = csv_infos[0]
                date_inspection: CSVDateInspection | None = None
                for info in infos:
                    if info.is_dir():
                        continue
                    with archive.open(info, "r") as member:
                        if info is selected:
                            date_inspection = _inspect_csv_stream(
                                member, expected_utc_date
                            )
                        else:
                            for _chunk in iter(lambda: member.read(1024 * 1024), b""):
                                pass
                if date_inspection is None:
                    raise AISRetrievalError("selected CSV member could not be read")
        except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
            raise AISRetrievalError(
                f"ZIP archive or member CRC validation failed: {exc}"
            ) from exc
        container: Literal["csv", "zip"] = "zip"
        members = normalized_names
        selected_member: str | None = _safe_member_name(selected.filename)
        crc_valid: bool | None = True
    else:
        try:
            with path.open("rb") as source:
                date_inspection = _inspect_csv_stream(source, expected_utc_date)
        except OSError as exc:
            raise AISRetrievalError(f"could not read source CSV: {path}") from exc
        container = "csv"
        members = ()
        selected_member = None
        crc_valid = None
    final_metadata = path.stat()
    if (
        final_metadata.st_size != byte_size
        or final_metadata.st_mtime_ns != initial_mtime_ns
    ):
        raise AISRetrievalError("source artifact changed during read-only inspection")
    return ArtifactInspection(
        byte_size=byte_size,
        sha256=sha256,
        container=container,
        archive_members=members,
        selected_csv_member=selected_member,
        crc_valid=crc_valid,
        source_content_length_match=(None if source_content_length is None else True),
        date_inspection=date_inspection,
    )


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _accepted_utc_dates() -> list[str]:
    day_count = (ANALYTICAL_PERIOD_END - ANALYTICAL_PERIOD_START).days + 1
    return [
        date.fromordinal(ANALYTICAL_PERIOD_START.toordinal() + offset).isoformat()
        for offset in range(day_count)
    ]


def _period_retrieval_summary(
    entries: list[dict[str, object]], expected_dates: list[str]
) -> dict[str, object]:
    expected_set = set(expected_dates)
    entry_dates = {cast(str, entry["utc_date"]) for entry in entries}
    if not entry_dates <= expected_set:
        raise AISRetrievalError(
            "manifest current entries must belong to the accepted analytical period"
        )
    verified_dates = {
        cast(str, entry["utc_date"])
        for entry in entries
        if entry.get("status") == "verified"
    }
    missing = sorted(expected_set - verified_dates)
    return {
        "status": "verified" if not missing else "not_verified",
        "missing_expected_utc_dates": missing,
    }


def _empty_manifest() -> dict[str, object]:
    expected_dates = _accepted_utc_dates()
    return {
        "contract": RETRIEVAL_MANIFEST_CONTRACT,
        "schema_version": RETRIEVAL_MANIFEST_SCHEMA_VERSION,
        "expected_utc_dates": expected_dates,
        "entries": [],
        "period_retrieval": {
            "status": "not_verified",
            "missing_expected_utc_dates": expected_dates.copy(),
        },
        "observational_completeness": {
            "status": "unverified",
            "reason": OBSERVATIONAL_COMPLETENESS_REASON,
        },
    }


def load_retrieval_manifest(path: Path) -> dict[str, object]:
    """Load and validate the current-entry uniqueness of a retrieval manifest."""
    if not path.exists():
        return _empty_manifest()
    if not path.is_file():
        raise AISRetrievalError(f"manifest path is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AISRetrievalError(
            f"retrieval manifest is not readable JSON: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise AISRetrievalError("retrieval manifest root must be an object")
    if payload.get("contract") != RETRIEVAL_MANIFEST_CONTRACT:
        raise AISRetrievalError("existing manifest has an incompatible contract")
    if payload.get("schema_version") != RETRIEVAL_MANIFEST_SCHEMA_VERSION:
        raise AISRetrievalError("existing manifest has an incompatible schema version")
    entries = payload.get("entries")
    expected = payload.get("expected_utc_dates")
    if not isinstance(entries, list) or not isinstance(expected, list):
        raise AISRetrievalError("manifest entries and expected_utc_dates must be lists")
    dates: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("utc_date"), str):
            raise AISRetrievalError("every current manifest entry must have a UTC date")
        dates.append(cast(str, entry["utc_date"]))
        attempts = entry.get("attempt_history")
        if not isinstance(attempts, list):
            raise AISRetrievalError("every current entry must carry attempt history")
    if len(dates) != len(set(dates)):
        raise AISRetrievalError("manifest contains a duplicate current UTC-date entry")
    if expected != _accepted_utc_dates():
        raise AISRetrievalError(
            "expected_utc_dates must equal the complete accepted analytical period"
        )
    expected_set = set(cast(list[str], expected))
    if not set(dates) <= expected_set:
        raise AISRetrievalError(
            "manifest current entries must belong to the accepted analytical period"
        )
    if payload.get("period_retrieval") != _period_retrieval_summary(
        cast(list[dict[str, object]], entries), cast(list[str], expected)
    ):
        raise AISRetrievalError(
            "period_retrieval must match the current entries and accepted period"
        )
    return cast(dict[str, object], payload)


def _write_manifest_atomic(path: Path, manifest: Mapping[str, object]) -> None:
    if _is_under_data_raw(path.resolve()):
        raise AISRetrievalError(
            f"retrieval manifest cannot be written under data/raw: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.temporary-", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(_canonical_json(manifest) + "\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        if temporary.exists():
            temporary.unlink()
        raise AISRetrievalError(
            f"could not publish retrieval manifest atomically: {exc}"
        ) from exc


def _attempt(
    request: RetrievalRequest,
    number: int,
    outcome: str,
    inspection: ArtifactInspection | None,
    reason: str | None = None,
) -> dict[str, object]:
    return {
        "attempt_number": number,
        "outcome": outcome,
        "reason": reason,
        "request": request.to_dict(),
        "artifact_identity": (
            None if inspection is None else inspection.identity_dict()
        ),
        "archive_verification": (
            None if inspection is None else inspection.archive_dict()
        ),
        "date_verification": (
            None if inspection is None else inspection.date_inspection.to_dict()
        ),
    }


def _verified_entry(
    request: RetrievalRequest,
    inspection: ArtifactInspection,
    attempts: list[dict[str, object]],
) -> dict[str, object]:
    status = "verified" if inspection.byte_complete else "retrieved"
    byte_completeness = {
        "status": "verified" if inspection.byte_complete else "unverified",
        "evidence": (
            "matching source Content-Length"
            if inspection.source_content_length_match is True
            else (
                "complete ZIP structure and CRC validation"
                if inspection.container == "zip"
                else "no independent source byte count or archive integrity boundary"
            )
        ),
    }
    return {
        "utc_date": request.expected_utc_date.isoformat(),
        "status": status,
        "status_reason": (
            "retained bytes, byte completeness, container, header, and UTC "
            "date verified"
            if inspection.byte_complete
            else (
                "retained byte identity, header, and UTC date verified; independent "
                "byte completeness remains unverified"
            )
        ),
        "source_availability": {
            "status": "available",
            "evidence": "author_supplied_local_artifact",
        },
        "request": request.to_dict(),
        "retrieval_verification": {
            "status": "verified" if inspection.byte_complete else "identity_verified",
            "byte_identity": {"status": "verified", **inspection.identity_dict()},
            "identity": inspection.identity_dict(),
            "byte_completeness": byte_completeness,
            "source_content_length_match": inspection.source_content_length_match,
            "archive": inspection.archive_dict(),
        },
        "date_verification": {
            "status": "verified",
            **inspection.date_inspection.to_dict(),
        },
        "cleaning_compatibility": {
            "status": "header_compatible_not_exercised",
            "exact_header_compatible": True,
            "cleaner_exercised": False,
            "cleaning_reference": None,
        },
        "observational_completeness": {
            "status": "unverified",
            "reason": OBSERVATIONAL_COMPLETENESS_REASON,
        },
        "attempt_history": attempts,
    }


def _refresh_manifest_summary(manifest: dict[str, object]) -> None:
    entries = cast(list[dict[str, object]], manifest["entries"])
    entries.sort(key=lambda entry: cast(str, entry["utc_date"]))
    expected = cast(list[str], manifest["expected_utc_dates"])
    manifest["period_retrieval"] = _period_retrieval_summary(entries, expected)


def record_verified_attempt(
    manifest_path: Path,
    request: RetrievalRequest,
    inspection: ArtifactInspection,
) -> ManifestUpdate:
    """Atomically add, reuse, or conflict-review one verified date attempt."""
    manifest_path = manifest_path.resolve()
    manifest = load_retrieval_manifest(manifest_path)
    entries = cast(list[dict[str, object]], manifest["entries"])
    utc_date = request.expected_utc_date.isoformat()
    current = next(
        (entry for entry in entries if entry.get("utc_date") == utc_date), None
    )
    if current is None:
        attempt = _attempt(request, 1, "verified", inspection)
        current = _verified_entry(request, inspection, [attempt])
        entries.append(current)
        outcome: Literal["verified", "identical_retry", "conflict"] = "verified"
    else:
        attempts = cast(list[dict[str, object]], current["attempt_history"])
        if current.get("status") == "conflict":
            reason = "current date entry remains in conflict pending explicit review"
            attempts.append(
                _attempt(request, len(attempts) + 1, "conflict", inspection, reason)
            )
            current["status_reason"] = reason
            outcome = "conflict"
            _refresh_manifest_summary(manifest)
            _write_manifest_atomic(manifest_path, manifest)
            return ManifestUpdate(outcome, "conflict", manifest)
        existing_verification = current.get("retrieval_verification")
        existing_sha: str | None = None
        if isinstance(existing_verification, dict):
            identity = existing_verification.get("identity")
            if isinstance(identity, dict) and isinstance(identity.get("sha256"), str):
                existing_sha = cast(str, identity["sha256"])
        if existing_sha is None:
            attempts.append(
                _attempt(request, len(attempts) + 1, "verified", inspection)
            )
            replacement = _verified_entry(request, inspection, attempts)
            entries[entries.index(current)] = replacement
            current = replacement
            outcome = "verified"
        elif existing_sha == inspection.sha256:
            attempts.append(
                _attempt(request, len(attempts) + 1, "identical_reuse", inspection)
            )
            if current.get("status") == "retrieved" and inspection.byte_complete:
                replacement = _verified_entry(request, inspection, attempts)
                entries[entries.index(current)] = replacement
                current = replacement
            outcome = "identical_retry"
        else:
            reason = (
                "retry bytes differ from the verified current artifact; immutable "
                "evidence was not replaced"
            )
            attempts.append(
                _attempt(request, len(attempts) + 1, "conflict", inspection, reason)
            )
            current["status"] = "conflict"
            current["status_reason"] = reason
            outcome = "conflict"
    _refresh_manifest_summary(manifest)
    _write_manifest_atomic(manifest_path, manifest)
    return ManifestUpdate(outcome, cast(str, current["status"]), manifest)


def record_failed_attempt(
    manifest_path: Path,
    request: RetrievalRequest,
    reason: str,
) -> ManifestUpdate:
    """Preserve failure history without replacing any verified artifact evidence."""
    reason = _redact_free_text(reason)
    manifest_path = manifest_path.resolve()
    manifest = load_retrieval_manifest(manifest_path)
    entries = cast(list[dict[str, object]], manifest["entries"])
    utc_date = request.expected_utc_date.isoformat()
    current = next(
        (entry for entry in entries if entry.get("utc_date") == utc_date), None
    )
    if current is None:
        current = {
            "utc_date": utc_date,
            "status": "failed",
            "status_reason": reason,
            "source_availability": {"status": "unverified", "evidence": None},
            "request": request.to_dict(),
            "retrieval_verification": None,
            "date_verification": None,
            "cleaning_compatibility": {
                "status": "not_verified",
                "exact_header_compatible": False,
                "cleaner_exercised": False,
                "cleaning_reference": None,
            },
            "observational_completeness": {
                "status": "unverified",
                "reason": OBSERVATIONAL_COMPLETENESS_REASON,
            },
            "attempt_history": [],
        }
        entries.append(current)
    attempts = cast(list[dict[str, object]], current["attempt_history"])
    attempts.append(_attempt(request, len(attempts) + 1, "failed", None, reason))
    if current.get("status") not in ("verified", "retrieved", "conflict"):
        current["status"] = "failed"
        current["status_reason"] = reason
    _refresh_manifest_summary(manifest)
    _write_manifest_atomic(manifest_path, manifest)
    return ManifestUpdate("failed", cast(str, current["status"]), manifest)


def _is_under_data_raw(path: Path) -> bool:
    parts = [part.casefold() for part in path.parts]
    return any(
        parts[index] == "data" and parts[index + 1] == "raw"
        for index in range(len(parts) - 1)
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_inspected_source_identity(
    source_path: Path, inspection: ArtifactInspection
) -> None:
    byte_size, sha256, _mtime_ns = _fingerprint_regular_file(source_path)
    if byte_size != inspection.byte_size or sha256 != inspection.sha256:
        raise AISRetrievalError(
            "source artifact no longer matches the inspected byte size and SHA-256"
        )


def _require_open_source_identity(
    source: IO[bytes], inspection: ArtifactInspection
) -> None:
    source.seek(0)
    digest = hashlib.sha256()
    byte_size = 0
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        byte_size += len(chunk)
        digest.update(chunk)
    source.seek(0)
    if byte_size != inspection.byte_size or digest.hexdigest() != inspection.sha256:
        raise AISRetrievalError(
            "source artifact no longer matches the inspected byte size and SHA-256"
        )


def _existing_csv_bundle(
    output_directory: Path,
    inspection: ArtifactInspection,
    expected_date: date,
) -> CSVBundleResult:
    entries = {entry.name for entry in output_directory.iterdir()}
    expected_entries = {CSV_BUNDLE_FILENAME, CSV_BUNDLE_METADATA_FILENAME}
    if entries != expected_entries:
        raise AISRetrievalError(
            "existing extraction destination is not a complete compatible CSV bundle"
        )
    metadata_path = output_directory / CSV_BUNDLE_METADATA_FILENAME
    csv_path = output_directory / CSV_BUNDLE_FILENAME
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AISRetrievalError("existing CSV bundle metadata is unreadable") from exc
    if (
        metadata.get("contract") != CSV_BUNDLE_CONTRACT
        or metadata.get("source_sha256") != inspection.sha256
        or metadata.get("selected_csv_member") != inspection.selected_csv_member
        or metadata.get("expected_utc_date") != expected_date.isoformat()
    ):
        raise AISRetrievalError(
            "existing extraction destination does not match the verified source"
        )
    if not csv_path.is_file():
        raise AISRetrievalError("existing CSV bundle is missing source.csv")
    csv_size = csv_path.stat().st_size
    csv_sha = _sha256(csv_path)
    if (
        metadata.get("csv_byte_size") != csv_size
        or metadata.get("csv_sha256") != csv_sha
    ):
        raise AISRetrievalError("existing CSV bundle bytes do not match its metadata")
    return CSVBundleResult(
        output_directory,
        csv_path,
        metadata_path,
        csv_size,
        csv_sha,
        True,
    )


def materialize_verified_csv_bundle(
    source_path: Path,
    inspection: ArtifactInspection,
    expected_utc_date: date,
    output_directory: Path,
) -> CSVBundleResult:
    """Atomically extract one verified ZIP member to an explicit interim bundle."""
    source_path = source_path.resolve()
    output_directory = output_directory.resolve()
    if inspection.container != "zip" or inspection.selected_csv_member is None:
        raise AISRetrievalError("CSV materialization is only needed for a verified ZIP")
    _require_inspected_source_identity(source_path, inspection)
    if _is_under_data_raw(output_directory):
        raise AISRetrievalError(
            f"archive extraction cannot be written under data/raw: {output_directory}"
        )
    if output_directory.exists():
        if not output_directory.is_dir():
            raise AISRetrievalError(
                f"extraction destination is not a directory: {output_directory}"
            )
        return _existing_csv_bundle(output_directory, inspection, expected_utc_date)
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{output_directory.name}.temporary-", dir=output_directory.parent
        )
    )
    csv_path = temporary / CSV_BUNDLE_FILENAME
    metadata_path = temporary / CSV_BUNDLE_METADATA_FILENAME
    try:
        with source_path.open("rb") as source_file:
            _require_open_source_identity(source_file, inspection)
            with zipfile.ZipFile(source_file) as archive:
                matching = [
                    info
                    for info in archive.infolist()
                    if _safe_member_name(info.filename)
                    == inspection.selected_csv_member
                ]
                if len(matching) != 1:
                    raise AISRetrievalError(
                        "verified CSV member is no longer unique in the source archive"
                    )
                with (
                    archive.open(matching[0], "r") as member_source,
                    csv_path.open("xb") as output,
                ):
                    shutil.copyfileobj(member_source, output, length=1024 * 1024)
            _require_open_source_identity(source_file, inspection)
        csv_size = csv_path.stat().st_size
        csv_sha = _sha256(csv_path)
        metadata = {
            "contract": CSV_BUNDLE_CONTRACT,
            "source_sha256": inspection.sha256,
            "source_byte_size": inspection.byte_size,
            "selected_csv_member": inspection.selected_csv_member,
            "expected_utc_date": expected_utc_date.isoformat(),
            "csv_filename": CSV_BUNDLE_FILENAME,
            "csv_byte_size": csv_size,
            "csv_sha256": csv_sha,
        }
        metadata_path.write_text(
            _canonical_json(metadata) + "\n", encoding="utf-8", newline="\n"
        )
        temporary.rename(output_directory)
    except (AISRetrievalError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        if isinstance(exc, AISRetrievalError):
            raise
        raise AISRetrievalError(
            f"could not publish verified CSV bundle: {exc}"
        ) from exc
    return CSVBundleResult(
        output_directory,
        output_directory / CSV_BUNDLE_FILENAME,
        output_directory / CSV_BUNDLE_METADATA_FILENAME,
        csv_size,
        csv_sha,
        False,
    )


def attach_cleaning_reference(
    manifest_path: Path,
    expected_utc_date: date,
    reference: Mapping[str, object],
) -> dict[str, object]:
    """Attach cleaner evidence while preserving unverified observability."""
    manifest_path = manifest_path.resolve()
    manifest = load_retrieval_manifest(manifest_path)
    entries = cast(list[dict[str, object]], manifest["entries"])
    utc_date = expected_utc_date.isoformat()
    entry = next((item for item in entries if item.get("utc_date") == utc_date), None)
    if entry is None or entry.get("status") not in ("verified", "retrieved"):
        raise AISRetrievalError(
            "cleaning evidence requires one inspected, non-conflicting date entry"
        )
    if cast(dict[str, object], entry["observational_completeness"]).get("status") != (
        "unverified"
    ):
        raise AISRetrievalError("cleaning evidence cannot upgrade observability")
    if reference.get("cleaner_reported_completeness") != "unverified":
        raise AISRetrievalError(
            "cleaning evidence must preserve unverified observational completeness"
        )
    entry["cleaning_compatibility"] = {
        "status": "exercised_compatible",
        "exact_header_compatible": True,
        "cleaner_exercised": True,
        "cleaning_reference": dict(reference),
        "observational_completeness_preserved": True,
    }
    _write_manifest_atomic(manifest_path, manifest)
    return manifest
