"""Known-answer inputs for vessel/domain display-export tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from pyproj import CRS
from shapely.geometry import box

from whale_vessel_analysis.reporting_domain import ANALYTICAL_DOMAIN_ID
from whale_vessel_analysis.spatial_grid import CELL_ID_PATTERN, GEOMETRY_COLUMN
from whale_vessel_analysis.vessel_domain_display_export import (
    DOMAIN_MASK_SCHEMA,
    SOURCE_CRS,
    VESSEL_SOURCE_SCHEMA,
)

BASE_X = 0
BASE_Y = -500_000
CELL_SIZE_M = 5_000
GRID_SHA256 = "7" * 64
CONFIGURATION_SHA256 = "8" * 64
PERIOD_INPUT_ID = "multiday-ais-1234567890abcdef12345678"

SCENARIOS = (
    "coast_40_statute_miles",
    "coast_40_nautical_miles",
    "coast_50_statute_miles",
    "coast_50_nautical_miles",
    "receivers_40_statute_miles",
    "receivers_40_nautical_miles",
    "receivers_50_statute_miles",
    ANALYTICAL_DOMAIN_ID,
)


def _quality_document() -> dict[str, object]:
    """Small quality report whose accounting is known by construction."""
    return {
        "contract": "production_vessel_input_quality_v1",
        "processing_version": "1.0.0",
        "input_id": "vessel-input-1234567890abcdef12345678",
        "parameters": {
            "maximum_gap_seconds": 300.0,
            "implied_speed_ceiling_knots": 30.0,
            "period_readiness_treatment": "require-ready",
            "edge_treatment": "censor-at-cleaned-extent",
            "support_treatment": "exact-water-geometry-exclude-and-report",
            "vessel_length_filter": {"status": "type-only-no-length-filter"},
        },
        "input": {
            "period_input_id": PERIOD_INPUT_ID,
            "partition_count": 153,
            "period_input_readiness": {
                "status": "ready",
                "expected_date_count": 153,
            },
            "observational_completeness": {"status": "unverified"},
            "target_grid": {
                "sha256": GRID_SHA256,
                "cell_count": 4,
                "analysis_crs": "EPSG:3310",
            },
        },
        "counts": {
            "candidate_segments": {
                "passenger": 4,
                "cargo": 4,
                "tanker": 2,
                "all_commercial": 10,
                "retained": 8,
                "excluded": 2,
            },
            "primary_exclusions": {
                "invalid_coordinate_transform": 0,
                "non_increasing_time": 0,
                "vessel_group_change": 0,
                "maximum_gap": 1,
                "implied_speed": 1,
            },
            "allocation_status": {
                "positive_length_in_support": 5,
                "positive_length_outside_support": 2,
                "positive_length_partially_outside_support": 1,
                "zero_length_in_support": 0,
                "zero_length_outside_support": 0,
            },
        },
        "exclusions": {
            "precedence": [
                "invalid_coordinate_transform",
                "non_increasing_time",
                "vessel_group_change",
                "maximum_gap",
                "implied_speed",
            ],
            "projected_distance_m_by_reason": {
                "maximum_gap": 100.0,
                "implied_speed": 200.0,
            },
        },
        "distance_conservation": {
            "passed": True,
            "by_group": {
                "all_commercial": {
                    "retained_parent_m": 1_000.0,
                    "allocated_to_cells_m": 800.0,
                    "outside_support_m": 200.0,
                    "ambiguous_boundary_m": 0.0,
                    "invalid_geometry_m": 0.0,
                    "difference_m": 0.0,
                }
            },
        },
    }


def _geo_metadata() -> bytes:
    return json.dumps(
        {
            "version": "1.1.0",
            "primary_column": GEOMETRY_COLUMN,
            "columns": {
                GEOMETRY_COLUMN: {
                    "encoding": "WKB",
                    "geometry_types": ["Polygon"],
                    "crs": CRS.from_user_input(SOURCE_CRS).to_json_dict(),
                }
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _vessel_row(column: int, total_km: float) -> dict[str, object]:
    geometry = box(
        BASE_X + column * CELL_SIZE_M,
        BASE_Y,
        BASE_X + (column + 1) * CELL_SIZE_M,
        BASE_Y + CELL_SIZE_M,
    )
    row: dict[str, object] = {
        "cell_id": CELL_ID_PATTERN.format(row=0, column=column),
        "row_index": 0,
        "column_index": column,
        "cell_x_min_m": BASE_X + column * CELL_SIZE_M,
        "cell_y_min_m": BASE_Y,
        "cell_x_max_m": BASE_X + (column + 1) * CELL_SIZE_M,
        "cell_y_max_m": BASE_Y + CELL_SIZE_M,
        "water_area_m2": 25_000_000.0,
        "water_area_km2": 25.0,
        GEOMETRY_COLUMN: shapely.to_wkb(geometry),
    }
    group_values = {
        "passenger": total_km * 0.2,
        "cargo": total_km * 0.5,
        "tanker": total_km * 0.3,
        "all_commercial": total_km,
    }
    for group, value in group_values.items():
        row[f"vessel_km_{group}"] = value
        row[f"vessel_km_per_water_km2_{group}"] = value / 25.0
        row[f"distinct_mmsi_{group}"] = 0 if value == 0 else column + 1
        row[f"distinct_mmsi_dates_{group}"] = 0 if value == 0 else column + 2
        row[f"sog_available_km_{group}"] = value
        row[f"sog_unavailable_km_{group}"] = 0.0
        row[f"sog_inconsistent_km_{group}"] = 0.0
        row[f"reported_sog_mean_knots_{group}"] = None if value == 0 else 10.0
        row[f"implied_speed_mean_knots_{group}"] = None if value == 0 else 10.5
    return row


def vessel_table(*, metadata_override: tuple[str, object] | None = None) -> pa.Table:
    rows = [_vessel_row(index, value) for index, value in enumerate((0, 25, 100, 50))]
    document: dict[str, object] = {
        "contract": "production_vessel_input_v1",
        "schema_version": 1,
        "processing_version": "1.0.0",
        "analysis_crs": SOURCE_CRS,
        "grid_id": "vessel-input-1234567890abcdef12345678",
        "parameters": {
            "maximum_gap_seconds": 300.0,
            "implied_speed_ceiling_knots": 30.0,
            "period_readiness_treatment": "require-ready",
            "edge_treatment": "censor-at-cleaned-extent",
            "support_treatment": "exact-water-geometry-exclude-and-report",
            "vessel_length_filter": {"status": "type-only-no-length-filter"},
        },
        "input": {
            "period_input_id": PERIOD_INPUT_ID,
            "configuration_sha256": CONFIGURATION_SHA256,
            "target_grid_sha256": GRID_SHA256,
            "observational_completeness": {"status": "unverified"},
            "period_input_readiness": {"status": "ready", "expected_date_count": 153},
        },
        "quality": _quality_document(),
    }
    if metadata_override is not None:
        key, value = metadata_override
        document[key] = value
    schema = pa.schema(
        [
            pa.field(name, kind, nullable=nullable)
            for name, kind, nullable in VESSEL_SOURCE_SCHEMA
        ],
        metadata={
            b"geo": _geo_metadata(),
            b"whale_vessel_analysis": json.dumps(
                document, sort_keys=True, separators=(",", ":")
            ).encode(),
        },
    )
    return pa.Table.from_arrays(
        [
            pa.array([row[field.name] for row in rows], type=field.type)
            for field in schema
        ],
        schema=schema,
    )


def domain_table() -> pa.Table:
    accepted = box(BASE_X, BASE_Y, BASE_X + 7_500, BASE_Y + CELL_SIZE_M)
    rows = []
    for scenario in SCENARIOS:
        receivers = scenario.startswith("receivers")
        nautical = "nautical" in scenario
        distance = 50 if "_50_" in scenario else 40
        distance_m = distance * (1852.0 if nautical else 1609.344)
        rows.append(
            {
                "scenario_id": scenario,
                "basis": "receivers" if receivers else "coastline",
                "distance_m": distance_m,
                GEOMETRY_COLUMN: shapely.to_wkb(accepted),
            }
        )
    schema = pa.schema(
        [pa.field(name, kind, nullable=False) for name, kind in DOMAIN_MASK_SCHEMA],
        metadata={b"geo": _geo_metadata()},
    )
    return pa.Table.from_arrays(
        [
            pa.array([row[field.name] for row in rows], type=field.type)
            for field in schema
        ],
        schema=schema,
    )


def _write_table(path: Path, table: pa.Table) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", use_dictionary=False)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_sources(
    tmp_path: Path,
) -> tuple[Path, str, Path, str, Path, str, Path, str]:
    vessel_path = tmp_path / "inputs" / "vessel-grid.parquet"
    vessel_sha = _write_table(vessel_path, vessel_table())
    quality_path = tmp_path / "inputs" / "quality-report.json"
    quality = {
        **_quality_document(),
        "output": {
            "contract": "production_vessel_input_v1",
            "input_id": "vessel-input-1234567890abcdef12345678",
            "rows": 4,
            "sha256": vessel_sha,
        },
    }
    quality_path.write_text(
        json.dumps(quality, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    quality_sha = hashlib.sha256(quality_path.read_bytes()).hexdigest()
    domain_path = tmp_path / "inputs" / "domain-candidate-masks.parquet"
    domain_sha = _write_table(domain_path, domain_table())
    report = {
        "contract": "analytical_domain_evidence_v1",
        "schema_version": 1,
        "evidence_id": "domain-evidence-1234567890abcdef12345678",
        "configuration_sha256": CONFIGURATION_SHA256,
        "mask_output": {"sha256": domain_sha, "feature_count": 8},
        "sources": {
            "grid": GRID_SHA256,
            "grid_path_sha256": GRID_SHA256,
            "station_archive": "9" * 64,
            "shoreline_archive": "a" * 64,
            "vsr": "b" * 64,
        },
        "candidates": [
            {
                "id": ANALYTICAL_DOMAIN_ID,
                "basis": "receivers",
                "unit": "nautical_mile",
                "distance": 50,
                "distance_m": 92_600.0,
                "included_water_area_km2": 37.5,
                "cells": {
                    "fully_inside": 1,
                    "partly_inside": 1,
                    "wholly_outside": 2,
                },
            }
        ],
    }
    report_path = tmp_path / "inputs" / "domain-evidence-report.json"
    report_path.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    report_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()
    return (
        vessel_path,
        vessel_sha,
        quality_path,
        quality_sha,
        domain_path,
        domain_sha,
        report_path,
        report_sha,
    )
