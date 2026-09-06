"""Shared source fixtures for the whale display-export tests.

The fixtures here build a `blue_whale_grid_transfer_v1` artifact from scratch so
every expected answer is known by construction. Nothing reads a generated
project artifact or the ignored local data root.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from pyproj import CRS
from shapely.geometry import MultiPolygon, Polygon, box

from whale_vessel_analysis.spatial_grid import CELL_ID_PATTERN, GEOMETRY_COLUMN
from whale_vessel_analysis.whale_display_export import SOURCE_CRS, SOURCE_SCHEMA
from whale_vessel_analysis.whale_grid import (
    LINEAGE_SUFFIX,
    WHALE_GRID_CONTRACT,
    WHALE_GRID_DATASET_SCHEMA_VERSION,
    WHALE_GRID_LINEAGE_CONTRACT,
)

# EPSG:3310 places its central meridian at 120 degrees west, so any easting of
# exactly zero must come back as longitude -120 whatever the implementation
# does internally. The cells below straddle that meridian for that reason, and
# they sit inside the configured map extent (-122, 32, -117, 35).
#: Sentinel meaning "delete this metadata key" in `metadata_overrides`.
REMOVE = object()

CENTRAL_MERIDIAN_LONGITUDE = -120.0
CELL_SIZE_M = 5_000
BASE_X = 0
BASE_Y = -500_000


def _cell_geometry(row: int, column: int) -> Polygon:
    x_min = BASE_X + column * CELL_SIZE_M
    y_min = BASE_Y + row * CELL_SIZE_M
    return box(x_min, y_min, x_min + CELL_SIZE_M, y_min + CELL_SIZE_M)


def _cell(
    row: int,
    column: int,
    *,
    geometry: Polygon | MultiPolygon | None = None,
    density: float = 0.0025,
    water_area_km2: float = 25.0,
    coverage: float = 1.0,
    status: str = "complete",
) -> dict[str, object]:
    shape = _cell_geometry(row, column) if geometry is None else geometry
    return {
        "cell_id": CELL_ID_PATTERN.format(row=row, column=column),
        "row_index": row,
        "column_index": column,
        "cell_x_min_m": BASE_X + column * CELL_SIZE_M,
        "cell_y_min_m": BASE_Y + row * CELL_SIZE_M,
        "cell_x_max_m": BASE_X + (column + 1) * CELL_SIZE_M,
        "cell_y_max_m": BASE_Y + (row + 1) * CELL_SIZE_M,
        "water_area_m2": water_area_km2 * 1e6,
        "water_area_km2": water_area_km2,
        "modeled_abundance_allocation_animals": density * water_area_km2,
        "modeled_density_animals_per_km2": density,
        "source_covered_water_area_m2": water_area_km2 * 1e6 * coverage,
        "source_covered_water_area_km2": water_area_km2 * coverage,
        "uncovered_water_area_m2": water_area_km2 * 1e6 * (1.0 - coverage),
        "uncovered_water_area_km2": water_area_km2 * (1.0 - coverage),
        "source_coverage_fraction": coverage,
        "coverage_status": status,
        "source_polygon_count": 1,
        GEOMETRY_COLUMN: shapely.to_wkb(shape),
    }


def _table(
    cells: Sequence[dict[str, object]],
    *,
    contract: str = WHALE_GRID_CONTRACT,
    schema_version: int = WHALE_GRID_DATASET_SCHEMA_VERSION,
    analysis_crs: str = SOURCE_CRS,
    geometry_crs: str = SOURCE_CRS,
    encoding: str = "WKB",
    nullable: bool = False,
    drop_column: str | None = None,
    retype: tuple[str, pa.DataType] | None = None,
    omit_geo_metadata: bool = False,
    metadata_overrides: dict[str, object] | None = None,
) -> pa.Table:
    fields = []
    for name, kind in SOURCE_SCHEMA:
        if name == drop_column:
            continue
        if retype is not None and retype[0] == name:
            kind = retype[1]
        fields.append(pa.field(name, kind, nullable=nullable))
    dataset_metadata = {
        "contract": contract,
        "schema_version": schema_version,
        "analysis_crs": analysis_crs,
        # The complete method block the real `blue_whale_grid_transfer_v1`
        # writer emits, so the exporter's public-field validation is exercised
        # against the shape it will actually meet.
        "method": {
            "name": "abundance-conserving area-weighted polygon transfer",
            "contribution": (
                "source modeled density (animals/km²) multiplied by overlap area (km²)"
            ),
            "target_density": (
                "modeled abundance allocation (animals) / cell water area (km²)"
            ),
            "source_overlap_area_tolerance_m2": 1.0,
            "coverage_exact_tolerance_m2": 1e-06,
            "coverage_numerical_tolerance_m2": 0.1,
            "uncertainty_propagation": "not_performed",
            "resolution_limit": (
                "5 km reporting grid; biological precision remains limited to the "
                "approximately 0.1-degree source model"
            ),
        },
        "units": {"modeled_density_animals_per_km2": "animals/km\u00b2"},
        "inputs": {
            "whale_source_sha256": "0" * 64,
            "target_grid_sha256": "1" * 64,
            "configuration_sha256": "2" * 64,
        },
    }
    if metadata_overrides is not None:
        for path, value in metadata_overrides.items():
            section, _, key = path.partition(".")
            block = dataset_metadata.get(section)
            if key and isinstance(block, dict):
                if value is REMOVE:
                    block.pop(key, None)
                else:
                    block[key] = value
            elif value is REMOVE:
                dataset_metadata.pop(section, None)
            else:
                dataset_metadata[section] = value
    metadata = {
        b"whale_vessel_analysis": json.dumps(
            dataset_metadata, sort_keys=True, separators=(",", ":")
        ).encode("utf-8"),
    }
    if not omit_geo_metadata:
        metadata[b"geo"] = json.dumps(
            {
                "version": "1.1.0",
                "primary_column": GEOMETRY_COLUMN,
                "columns": {
                    GEOMETRY_COLUMN: {
                        "encoding": encoding,
                        "geometry_types": ["Polygon"],
                        "crs": CRS.from_user_input(geometry_crs).to_json_dict(),
                    }
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    schema = pa.schema(fields, metadata=metadata)
    arrays = [
        pa.array([cell[field.name] for cell in cells], type=field.type)
        for field in schema
    ]
    return pa.Table.from_arrays(arrays, schema=schema)


def _write_source(path: Path, table: pa.Table, *, lineage: bool = True) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", use_dictionary=False)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if lineage:
        sidecar = path.with_suffix(path.suffix + LINEAGE_SUFFIX)
        sidecar.write_text(
            json.dumps(
                {
                    "contract": WHALE_GRID_LINEAGE_CONTRACT,
                    "run": {"run_id": "whale-grid-testfixture0000000000"},
                    "output": {"path": "ignored", "sha256": digest},
                    "inputs": {"whale_source": {"path": r"C:\private\raw\model.gdb"}},
                    "visual_inspection_status": "not_completed",
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    return digest


def _prepare(tmp_path: Path, cells: Sequence[dict[str, object]], **kwargs: object):
    source_path = tmp_path / "source" / "whale-grid.parquet"
    digest = _write_source(source_path, _table(cells, **kwargs))  # type: ignore[arg-type]
    return source_path, digest
