"""Shared validation of the three-file cleaned AIS bundle written by the cleaner.

The one-bundle evidence harness and the multi-day cleaned-input foundation both
have to trust the same sidecar and checksum boundary. This module owns that
boundary so the two callers cannot drift apart. It validates structure,
contracts, checksums, and shared run identity; it does not read observations and
does not interpret them.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import pyarrow as pa

from whale_vessel_analysis.ais_processing import (
    AIS_PROCESSING_CONTRACT,
    CLEANED_FILENAME,
    QUALITY_REPORT_FILENAME,
    RUN_METADATA_FILENAME,
)

CLEANED_BUNDLE_FILENAMES: Final = frozenset(
    {CLEANED_FILENAME, QUALITY_REPORT_FILENAME, RUN_METADATA_FILENAME}
)
CLEANED_COLUMNS: Final = (
    "mmsi",
    "observed_at_utc",
    "latitude",
    "longitude",
    "sog_knots",
    "cog_degrees",
    "heading_degrees",
    "vessel_type_code",
    "vessel_type_group",
    "length_m",
)
CLEANING_STEP_NAME: Final = "clean-and-scope-ais-extract"
CLEANED_PARQUET_ARTIFACT_ID: Final = "cleaned-ais-parquet"
QUALITY_REPORT_ARTIFACT_ID: Final = "ais-quality-report"


class CleanedAISBundleError(ValueError):
    """Raised when a supplied cleaner bundle is incomplete or inconsistent."""


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of a file read in bounded chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    """Serialize a value as sorted, compact, deterministic JSON text."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def read_json_object(path: Path, label: str) -> Mapping[str, object]:
    """Read one JSON object, refusing unreadable text and non-object roots."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CleanedAISBundleError(f"{label} is not readable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CleanedAISBundleError(f"{label} must contain a JSON object")
    return cast(Mapping[str, object], value)


def require_mapping(value: object, label: str) -> Mapping[str, object]:
    """Return the value as a mapping or refuse it."""
    if not isinstance(value, Mapping):
        raise CleanedAISBundleError(f"{label} must be an object")
    return cast(Mapping[str, object], value)


@dataclass(frozen=True, slots=True)
class CleanedBundleSidecars:
    """Validated sidecar identity for one cleaner bundle."""

    cleaner_run_id: str
    cleaner_contract: str
    cleaning_step_version: str | None
    cleaned_sha256: str
    quality_report_sha256: str
    run_metadata_sha256: str
    temporal_coverage: Mapping[str, object]
    quality_report: Mapping[str, object]
    run_metadata: Mapping[str, object]


def validate_bundle_layout(bundle_path: Path) -> Path:
    """Resolve one bundle directory and require the exact three-file layout."""
    resolved = bundle_path.resolve()
    if not resolved.is_dir():
        raise CleanedAISBundleError(f"cleaned AIS bundle does not exist: {resolved}")
    entries = {entry.name for entry in resolved.iterdir()}
    if entries != CLEANED_BUNDLE_FILENAMES:
        raise CleanedAISBundleError(
            "cleaned AIS bundle must contain exactly cleaned.parquet, "
            "quality-report.json, and run-metadata.json"
        )
    return resolved


def _cleaning_step_version(run: Mapping[str, object]) -> str | None:
    steps = run.get("steps")
    if not isinstance(steps, list):
        raise CleanedAISBundleError("cleaner run metadata steps must be a list")
    for step in steps:
        if isinstance(step, Mapping) and step.get("name") == CLEANING_STEP_NAME:
            version = step.get("version")
            return version if isinstance(version, str) else None
    return None


def validate_bundle_sidecars(
    bundle_path: Path, cleaned_sha256: str
) -> CleanedBundleSidecars:
    """Validate contracts, checksums, and shared cleaner run identity."""
    quality_path = bundle_path / QUALITY_REPORT_FILENAME
    metadata_path = bundle_path / RUN_METADATA_FILENAME
    quality_sha256 = sha256_file(quality_path)
    metadata_sha256 = sha256_file(metadata_path)
    quality = read_json_object(quality_path, "quality report")
    metadata = read_json_object(metadata_path, "run metadata")
    if quality.get("contract") != AIS_PROCESSING_CONTRACT:
        raise CleanedAISBundleError(
            f"quality report contract must be {AIS_PROCESSING_CONTRACT}"
        )
    if metadata.get("contract") != AIS_PROCESSING_CONTRACT:
        raise CleanedAISBundleError(
            f"run metadata contract must be {AIS_PROCESSING_CONTRACT}"
        )
    quality_run_id = quality.get("run_id")
    if not isinstance(quality_run_id, str) or not quality_run_id.strip():
        raise CleanedAISBundleError("quality report has no valid run_id")
    quality_output = require_mapping(quality.get("output"), "quality report output")
    if quality_output.get("sha256") != cleaned_sha256:
        raise CleanedAISBundleError(
            "cleaned Parquet checksum does not match the quality report"
        )
    run = require_mapping(metadata.get("run"), "run metadata run")
    run_id = run.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise CleanedAISBundleError("cleaner run metadata has no valid run_id")
    if quality_run_id != run_id:
        raise CleanedAISBundleError(
            "quality report and run metadata do not share the same cleaner run_id"
        )
    outputs = run.get("outputs")
    if not isinstance(outputs, list):
        raise CleanedAISBundleError("cleaner run metadata outputs must be a list")
    cleaned_outputs = [
        item
        for item in outputs
        if isinstance(item, Mapping)
        and item.get("artifact_id") == CLEANED_PARQUET_ARTIFACT_ID
    ]
    if len(cleaned_outputs) != 1 or cleaned_outputs[0].get("sha256") != cleaned_sha256:
        raise CleanedAISBundleError(
            "cleaned Parquet checksum does not match cleaner run metadata"
        )
    quality_outputs = [
        item
        for item in outputs
        if isinstance(item, Mapping)
        and item.get("artifact_id") == QUALITY_REPORT_ARTIFACT_ID
    ]
    if len(quality_outputs) != 1 or quality_outputs[0].get("sha256") != quality_sha256:
        raise CleanedAISBundleError(
            "quality report checksum does not match cleaner run metadata"
        )
    temporal = require_mapping(quality.get("temporal_coverage"), "temporal coverage")
    return CleanedBundleSidecars(
        cleaner_run_id=run_id,
        cleaner_contract=AIS_PROCESSING_CONTRACT,
        cleaning_step_version=_cleaning_step_version(run),
        cleaned_sha256=cleaned_sha256,
        quality_report_sha256=quality_sha256,
        run_metadata_sha256=metadata_sha256,
        temporal_coverage=temporal,
        quality_report=quality,
        run_metadata=metadata,
    )


def validate_cleaned_schema(schema: pa.Schema) -> None:
    """Require the exact one-extract cleaner output schema."""
    if tuple(schema.names) != CLEANED_COLUMNS:
        raise CleanedAISBundleError(
            "cleaned Parquet columns do not match the one-extract cleaner contract"
        )
    expected_types = (
        pa.types.is_string,
        pa.types.is_timestamp,
        pa.types.is_floating,
        pa.types.is_floating,
        pa.types.is_floating,
        pa.types.is_floating,
        pa.types.is_floating,
        pa.types.is_integer,
        pa.types.is_string,
        pa.types.is_floating,
    )
    for field, predicate in zip(schema, expected_types, strict=True):
        if not predicate(field.type):
            raise CleanedAISBundleError(
                f"cleaned Parquet column {field.name} has invalid type {field.type}"
            )
    timestamp_type = schema.field("observed_at_utc").type
    if not isinstance(timestamp_type, pa.TimestampType) or timestamp_type.tz is None:
        raise CleanedAISBundleError(
            "cleaned Parquet observed_at_utc must be timezone-aware"
        )
