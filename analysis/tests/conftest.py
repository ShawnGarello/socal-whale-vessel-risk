from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from whale_vessel_analysis.ais_processing import (
    AIS_PROCESSING_CONTRACT,
    CLEANED_FILENAME,
    QUALITY_REPORT_FILENAME,
    RUN_METADATA_FILENAME,
)

CLEANED_SCHEMA = pa.schema(
    [
        pa.field("mmsi", pa.string()),
        pa.field("observed_at_utc", pa.timestamp("us", tz="UTC")),
        pa.field("latitude", pa.float64()),
        pa.field("longitude", pa.float64()),
        pa.field("sog_knots", pa.float64()),
        pa.field("cog_degrees", pa.float64()),
        pa.field("heading_degrees", pa.float64()),
        pa.field("vessel_type_code", pa.int16()),
        pa.field("vessel_type_group", pa.string()),
        pa.field("length_m", pa.float64()),
    ]
)

_GROUP_CODES = {"passenger": 60, "cargo": 70, "tanker": 80}

SyntheticRow = tuple[str, datetime, float, float, str]
BundleFactory = Callable[..., Path]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def synthetic_rows(
    utc_date: str,
    *,
    mmsi: str = "123456789",
    seconds: Sequence[int] = (0,),
    group: str = "cargo",
    longitude: float = -118.0,
) -> list[SyntheticRow]:
    """Build simple observation tuples for one UTC date."""
    day = datetime.fromisoformat(utc_date).replace(tzinfo=UTC)
    return [
        (
            mmsi,
            day.replace(
                hour=second // 3600, minute=(second // 60) % 60, second=second % 60
            ),
            34.0,
            longitude,
            group,
        )
        for second in seconds
    ]


def build_cleaned_bundle(
    directory: Path,
    rows: Sequence[SyntheticRow],
    *,
    observed_utc_date: str | None = None,
    run_id: str = "ais-synthetic0000000000000",
    metadata_run_id: str | None = None,
    cleaning_step_version: str = "2.0.0",
    quality_contract: str = AIS_PROCESSING_CONTRACT,
    reported_rows: int | None = None,
    completeness_status: str = "unverified",
    started_at: str = "2026-08-28T00:00:00Z",
    completed_at: str = "2026-08-28T00:00:01Z",
) -> Path:
    """Write one synthetic three-file cleaner bundle with consistent checksums."""
    directory.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "mmsi": [row[0] for row in rows],
            "observed_at_utc": [row[1] for row in rows],
            "latitude": [row[2] for row in rows],
            "longitude": [row[3] for row in rows],
            "sog_knots": [10.0 for _ in rows],
            "cog_degrees": [90.0 for _ in rows],
            "heading_degrees": [90.0 for _ in rows],
            "vessel_type_code": [_GROUP_CODES[row[4]] for row in rows],
            "vessel_type_group": [row[4] for row in rows],
            "length_m": [200.0 for _ in rows],
        },
        schema=CLEANED_SCHEMA,
    )
    cleaned_path = directory / CLEANED_FILENAME
    pq.write_table(table, cleaned_path, compression="zstd")
    cleaned_sha256 = _sha256(cleaned_path)
    observed = observed_utc_date or rows[0][1].date().isoformat()
    timestamps = sorted(row[1] for row in rows)
    quality: dict[str, Any] = {
        "contract": quality_contract,
        "run_id": run_id,
        "status": "success",
        "output": {
            "path": str(cleaned_path),
            "sha256": cleaned_sha256,
            "rows": len(rows) if reported_rows is None else reported_rows,
        },
        "temporal_coverage": {
            "observed_utc_date": observed,
            "earliest_valid_observed_at_utc": timestamps[0]
            .isoformat()
            .replace("+00:00", "Z"),
            "latest_valid_observed_at_utc": timestamps[-1]
            .isoformat()
            .replace("+00:00", "Z"),
            "completeness": {
                "status": completeness_status,
                "reason": "synthetic bundle",
            },
        },
    }
    quality_path = directory / QUALITY_REPORT_FILENAME
    _write_json(quality_path, quality)
    quality_sha256 = _sha256(quality_path)
    metadata = {
        "contract": AIS_PROCESSING_CONTRACT,
        "run": {
            "run_id": metadata_run_id or run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "steps": [
                {"name": "validate-noaa-flat-csv-header", "version": "1.0.0"},
                {
                    "name": "clean-and-scope-ais-extract",
                    "version": cleaning_step_version,
                },
                {"name": "write-deterministic-parquet", "version": "1.0.0"},
            ],
            "outputs": [
                {"artifact_id": "cleaned-ais-parquet", "sha256": cleaned_sha256},
                {"artifact_id": "ais-quality-report", "sha256": quality_sha256},
            ],
        },
    }
    _write_json(directory / RUN_METADATA_FILENAME, metadata)
    return directory


@pytest.fixture
def cleaned_bundle() -> BundleFactory:
    """Return the synthetic cleaner-bundle builder."""
    return build_cleaned_bundle


@pytest.fixture
def day_bundle(tmp_path: Path) -> Callable[..., Path]:
    """Return a builder for one simple single-date bundle."""

    def build(utc_date: str, *, name: str | None = None, **updates: Any) -> Path:
        directory = tmp_path / "bundles" / (name or utc_date)
        rows = updates.pop("rows", None) or synthetic_rows(utc_date)
        return build_cleaned_bundle(directory, rows, **updates)

    return build
