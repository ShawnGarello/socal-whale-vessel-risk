from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from shapely import from_wkb
from shapely.geometry import Point, Polygon, box

from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.spatial_grid import (
    AREA_TOLERANCE_M2,
    MaskInspection,
    SpatialOutputError,
    WaterGridDataset,
    WaterMaskValidationError,
    construct_water_grid,
    load_water_mask,
    reproject_mask,
    write_water_grid,
)

_SOURCE_SHA256 = "a" * 64
_FIXED_RUN_AT = datetime(2026, 8, 26, 12, tzinfo=UTC)


def _dataset(geometry: Polygon) -> WaterGridDataset:
    return construct_water_grid(
        geometry,
        source_crs="EPSG:3310",
        source_sha256=_SOURCE_SHA256,
        mask_feature_count=1,
        config=load_default_config(),
    )


def _mask(path: Path, geometry: Polygon) -> MaskInspection:
    path.write_text("synthetic mask\n", encoding="utf-8")
    return MaskInspection(
        geometry=geometry,
        path=path,
        layer=None,
        source_crs="EPSG:3310",
        source_sha256=_SOURCE_SHA256,
        feature_count=1,
        null_geometry_count=0,
        empty_geometry_count=0,
        invalid_geometry_count=0,
        non_finite_geometry_count=0,
    )


@pytest.fixture(scope="module")
def full_grid() -> WaterGridDataset:
    return _dataset(box(-190_000, -670_000, 285_000, -330_000))


def test_exact_grid_structure_bounds_area_and_stable_ids(
    full_grid: WaterGridDataset,
) -> None:
    assert full_grid.grid.rows == 68
    assert full_grid.grid.columns == 95
    assert full_grid.nominal_cell_count == 6_460
    assert full_grid.retained_water_cell_count == 6_460
    assert full_grid.grid_bounds == (-190_000, -670_000, 285_000, -330_000)
    assert full_grid.cells[0].cell_id == "r000_c000"
    assert full_grid.cells[-1].cell_id == "r067_c094"
    assert len({cell.cell_id for cell in full_grid.cells}) == 6_460
    assert {cell.water_area_m2 for cell in full_grid.cells} == {25_000_000.0}


def test_rows_are_deterministically_south_to_north_then_west_to_east(
    full_grid: WaterGridDataset,
) -> None:
    ordering = [(cell.row_index, cell.column_index) for cell in full_grid.cells]

    assert ordering == sorted(ordering)
    assert full_grid.cells[94].cell_id == "r000_c094"
    assert full_grid.cells[95].cell_id == "r001_c000"


def test_full_cell_water_geometry_has_exact_area() -> None:
    dataset = _dataset(box(-190_000, -670_000, -185_000, -665_000))

    assert dataset.retained_water_cell_count == 1
    assert dataset.dry_cell_count == 6_459
    assert dataset.cells[0].water_area_m2 == 25_000_000.0
    assert dataset.cells[0].water_area_km2 == 25.0
    assert dataset.cells[0].geometry.equals(box(-190_000, -670_000, -185_000, -665_000))


def test_half_cell_water_geometry_has_exact_area() -> None:
    dataset = _dataset(box(-190_000, -670_000, -187_500, -665_000))

    assert dataset.retained_water_cell_count == 1
    assert dataset.cells[0].water_area_m2 == 12_500_000.0
    assert dataset.cells[0].water_area_km2 == 12.5


def test_coastline_like_partial_geometry_and_dry_cells() -> None:
    coastline = Polygon(
        [
            (-190_000, -670_000),
            (-185_000, -670_000),
            (-187_500, -667_500),
            (-185_000, -665_000),
            (-190_000, -665_000),
        ]
    )
    dataset = _dataset(coastline)

    assert dataset.retained_water_cell_count == 1
    assert dataset.dry_cell_count == 6_459
    assert dataset.cells[0].water_area_m2 == 18_750_000.0


@pytest.mark.parametrize(
    ("geometry", "message"),
    [
        (Polygon(), "empty"),
        (
            Polygon(
                [
                    (-190_000, -670_000),
                    (-185_000, -665_000),
                    (-185_000, -670_000),
                    (-190_000, -665_000),
                ]
            ),
            "invalid",
        ),
    ],
)
def test_empty_and_invalid_masks_are_rejected(geometry: Polygon, message: str) -> None:
    with pytest.raises(WaterMaskValidationError, match=message):
        _dataset(geometry)


def test_non_finite_mask_coordinates_are_rejected() -> None:
    with pytest.warns(RuntimeWarning, match="invalid value"):
        geometry = Polygon(
            [
                (-190_000, -670_000),
                (-185_000, -670_000),
                (math.nan, -665_000),
                (-190_000, -665_000),
            ]
        )

    with pytest.raises(WaterMaskValidationError, match="non-finite"):
        _dataset(geometry)


def test_declared_source_crs_must_match_embedded_crs(tmp_path: Path) -> None:
    path = tmp_path / "mask.geojson"
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [-118.1, 33.9],
                                    [-118.0, 33.9],
                                    [-118.0, 34.0],
                                    [-118.1, 34.0],
                                    [-118.1, 33.9],
                                ]
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(WaterMaskValidationError, match="does not match embedded"):
        load_water_mask(path, layer=None, declared_source_crs="EPSG:3857")


def test_missing_embedded_source_crs_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "mask.geojson"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "whale_vessel_analysis.spatial_grid.pyogrio.read_info",
        lambda *_args, **_kwargs: {"crs": None},
    )

    with pytest.raises(
        WaterMaskValidationError, match="embedded water-mask CRS is missing"
    ):
        load_water_mask(path, layer=None, declared_source_crs="EPSG:4326")


def test_known_longitude_latitude_transformation_uses_xy_order() -> None:
    source = box(-118.0, 34.0, -117.99, 34.01)

    projected, definition = reproject_mask(source, "EPSG:4326")

    expected_corner = (184_755.8686105011, -444_218.17569026817)
    assert projected.boundary.distance(Point(expected_corner)) < 0.001
    assert "proj=aea" in definition


def test_every_water_geometry_is_contained_and_area_is_conserved(
    full_grid: WaterGridDataset,
) -> None:
    for cell in full_grid.cells:
        parent = box(cell.x_min_m, cell.y_min_m, cell.x_max_m, cell.y_max_m)
        assert parent.covers(cell.geometry)
        assert 0 < cell.water_area_m2 <= 25_000_000.0 + AREA_TOLERANCE_M2
    assert full_grid.total_water_area_m2 == pytest.approx(
        full_grid.mask_intersection_area_m2, abs=AREA_TOLERANCE_M2
    )


def test_geometry_bytes_ids_and_metadata_are_deterministic() -> None:
    geometry = box(-190_000, -670_000, -187_500, -665_000)
    first = _dataset(geometry)
    second = _dataset(geometry)

    assert [cell.cell_id for cell in first.cells] == [
        cell.cell_id for cell in second.cells
    ]
    assert [cell.geometry_wkb for cell in first.cells] == [
        cell.geometry_wkb for cell in second.cells
    ]
    assert first.summary() == second.summary()


def test_deterministic_geoparquet_and_lineage_serialization(tmp_path: Path) -> None:
    geometry = box(-190_000, -670_000, -187_500, -665_000)
    dataset = _dataset(geometry)
    mask = _mask(tmp_path / "mask.txt", geometry)
    output = tmp_path / "water-grid.parquet"

    first = write_water_grid(dataset, mask, output, run_at=_FIXED_RUN_AT)
    output_bytes = output.read_bytes()
    lineage_bytes = first.lineage_path.read_bytes()
    second = write_water_grid(
        dataset,
        mask,
        output,
        overwrite=True,
        run_at=_FIXED_RUN_AT,
    )

    assert output.read_bytes() == output_bytes
    assert second.lineage_path.read_bytes() == lineage_bytes
    assert second.output_sha256 == first.output_sha256
    assert second.lineage_sha256 == first.lineage_sha256
    metadata = pq.read_schema(output).metadata
    assert metadata is not None
    geo = json.loads(metadata[b"geo"])
    contract = json.loads(metadata[b"whale_vessel_analysis"])
    assert geo["version"] == "1.1.0"
    assert geo["primary_column"] == "geometry"
    assert geo["columns"]["geometry"]["encoding"] == "WKB"
    assert contract["analysis_crs"] == "EPSG:3310"
    assert contract["source"]["sha256"] == _SOURCE_SHA256
    table = pq.read_table(output)
    stored = from_wkb(table["geometry"][0].as_py())
    assert stored.equals(dataset.cells[0].geometry)


def test_existing_output_is_refused_without_authorization(tmp_path: Path) -> None:
    geometry = box(-190_000, -670_000, -185_000, -665_000)
    dataset = _dataset(geometry)
    mask = _mask(tmp_path / "mask.txt", geometry)
    output = tmp_path / "water-grid.parquet"
    write_water_grid(dataset, mask, output, run_at=_FIXED_RUN_AT)

    with pytest.raises(SpatialOutputError, match="explicit overwrite"):
        write_water_grid(dataset, mask, output, run_at=_FIXED_RUN_AT)


def test_failed_write_leaves_no_final_or_temporary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    geometry = box(-190_000, -670_000, -185_000, -665_000)
    dataset = _dataset(geometry)
    mask = _mask(tmp_path / "mask.txt", geometry)
    output = tmp_path / "water-grid.parquet"

    def fail_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic lineage failure")

    monkeypatch.setattr("whale_vessel_analysis.spatial_grid._write_json", fail_write)

    with pytest.raises(SpatialOutputError, match="synthetic lineage failure"):
        write_water_grid(dataset, mask, output, run_at=_FIXED_RUN_AT)

    assert not output.exists()
    assert not output.with_suffix(".parquet.lineage.json").exists()
    assert list(tmp_path.glob(".*.tmp")) == []
