from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from shapely import from_wkb
from shapely.geometry import Point, Polygon, box
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis import spatial_grid
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.spatial_grid import (
    AREA_TOLERANCE_M2,
    MAP_EXTENT_AREA_TOLERANCE_M2,
    MAP_EXTENT_EDGE_MAX_SEGMENT_DEGREES,
    MaskInspection,
    SpatialOutputError,
    WaterGridDataset,
    WaterMaskValidationError,
    construct_water_grid,
    load_water_mask,
    project_map_extent,
    reproject_mask,
    write_water_grid,
)

_SOURCE_SHA256 = "a" * 64
_STARTED_AT = datetime(2026, 8, 26, 12, tzinfo=UTC)
_COMPLETED_AT = datetime(2026, 8, 26, 12, 0, 1, tzinfo=UTC)
_SECOND_STARTED_AT = datetime(2026, 8, 26, 13, tzinfo=UTC)
_SECOND_COMPLETED_AT = datetime(2026, 8, 26, 13, 0, 1, tzinfo=UTC)
_INTERIOR_CELL = box(0, -500_000, 5_000, -495_000)


def _dataset(geometry: BaseGeometry) -> WaterGridDataset:
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
    assert full_grid.grid_bounds == (-190_000, -670_000, 285_000, -330_000)
    nominal_ids = [
        f"r{row:03d}_c{column:03d}"
        for row in range(full_grid.grid.rows)
        for column in range(full_grid.grid.columns)
    ]
    assert len(nominal_ids) == 6_460
    assert nominal_ids[0] == "r000_c000"
    assert nominal_ids[-1] == "r067_c094"
    assert full_grid.cells[0].cell_id == "r000_c000"
    assert len({cell.cell_id for cell in full_grid.cells}) == len(full_grid.cells)
    assert all(cell.cell_id in nominal_ids for cell in full_grid.cells)
    assert all(
        cell.cell_id == f"r{cell.row_index:03d}_c{cell.column_index:03d}"
        for cell in full_grid.cells
    )


def test_rows_are_deterministically_south_to_north_then_west_to_east(
    full_grid: WaterGridDataset,
) -> None:
    ordering = [(cell.row_index, cell.column_index) for cell in full_grid.cells]

    assert ordering == sorted(ordering)
    assert [cell.cell_id for cell in full_grid.cells] == [
        f"r{row:03d}_c{column:03d}" for row, column in ordering
    ]


def test_full_cell_water_geometry_has_exact_area() -> None:
    dataset = _dataset(_INTERIOR_CELL)

    assert dataset.retained_water_cell_count == 1
    assert dataset.dry_cell_count == 6_459
    assert dataset.cells[0].water_area_m2 == 25_000_000.0
    assert dataset.cells[0].water_area_km2 == 25.0
    assert dataset.cells[0].cell_id == "r034_c038"
    assert dataset.cells[0].geometry.equals(_INTERIOR_CELL)


def test_half_cell_water_geometry_has_exact_area() -> None:
    dataset = _dataset(box(0, -500_000, 2_500, -495_000))

    assert dataset.retained_water_cell_count == 1
    assert dataset.cells[0].water_area_m2 == 12_500_000.0
    assert dataset.cells[0].water_area_km2 == 12.5


def test_coastline_like_partial_geometry_and_dry_cells() -> None:
    coastline = Polygon(
        [
            (0, -500_000),
            (5_000, -500_000),
            (2_500, -497_500),
            (5_000, -495_000),
            (0, -495_000),
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


def test_configured_map_extent_is_densified_before_projection() -> None:
    extent = load_default_config().spatial.map_extent

    projected, definition = project_map_extent(extent)

    assert len(projected.exterior.coords) == 1_601
    assert MAP_EXTENT_EDGE_MAX_SEGMENT_DEGREES == 0.01
    assert projected.bounds == pytest.approx(
        (-189_429.3723, -667_727.4114, 284_117.7156, -330_858.9956),
        abs=0.001,
    )
    assert "proj=aea" in definition


def test_no_output_geometry_lies_outside_projected_map_extent(
    full_grid: WaterGridDataset,
) -> None:
    assert all(
        cell.geometry.difference(full_grid.map_extent_geometry).area
        <= MAP_EXTENT_AREA_TOLERANCE_M2
        for cell in full_grid.cells
    )


def test_boundary_cells_are_clipped_to_projected_map_extent(
    full_grid: WaterGridDataset,
) -> None:
    boundary_cell = next(
        cell for cell in full_grid.cells if cell.water_area_m2 < 25_000_000.0
    )
    parent = box(
        boundary_cell.x_min_m,
        boundary_cell.y_min_m,
        boundary_cell.x_max_m,
        boundary_cell.y_max_m,
    )
    expected = parent.intersection(full_grid.map_extent_geometry)

    assert boundary_cell.geometry.equals(expected)
    assert boundary_cell.water_area_m2 == pytest.approx(expected.area, abs=1e-6)
    assert boundary_cell.water_area_m2 < parent.area


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
    geometry = box(-190_000, -670_000, 285_000, -330_000)
    first = _dataset(geometry)
    second = _dataset(geometry)

    assert [cell.cell_id for cell in first.cells] == [
        cell.cell_id for cell in second.cells
    ]
    assert [cell.geometry_wkb for cell in first.cells] == [
        cell.geometry_wkb for cell in second.cells
    ]
    assert [cell.water_area_m2 for cell in first.cells] == [
        cell.water_area_m2 for cell in second.cells
    ]
    assert first.summary() == second.summary()


def test_deterministic_geoparquet_and_content_identity_with_truthful_timestamps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    geometry = box(0, -500_000, 2_500, -495_000)
    dataset = _dataset(geometry)
    mask = _mask(tmp_path / "mask.txt", geometry)
    output = tmp_path / "water-grid.parquet"
    completion_times = iter((_COMPLETED_AT, _SECOND_COMPLETED_AT))
    monkeypatch.setattr(spatial_grid, "_utc_now", completion_times.__next__)

    first = write_water_grid(dataset, mask, output, started_at=_STARTED_AT)
    output_bytes = output.read_bytes()
    first_lineage = json.loads(first.lineage_path.read_text(encoding="utf-8"))
    second = write_water_grid(
        dataset,
        mask,
        output,
        overwrite=True,
        started_at=_SECOND_STARTED_AT,
    )
    second_lineage = json.loads(second.lineage_path.read_text(encoding="utf-8"))

    assert output.read_bytes() == output_bytes
    assert second.output_sha256 == first.output_sha256
    assert second.lineage_sha256 != first.lineage_sha256
    assert first_lineage["run"]["run_id"] == second_lineage["run"]["run_id"]
    assert first_lineage["run"]["started_at"] == "2026-08-26T12:00:00Z"
    assert first_lineage["run"]["completed_at"] == "2026-08-26T12:00:01Z"
    assert second_lineage["run"]["started_at"] == "2026-08-26T13:00:00Z"
    assert second_lineage["run"]["completed_at"] == "2026-08-26T13:00:01Z"
    assert first_lineage["dataset"] == second_lineage["dataset"]
    metadata = pq.read_schema(output).metadata
    assert metadata is not None
    geo = json.loads(metadata[b"geo"])
    contract = json.loads(metadata[b"whale_vessel_analysis"])
    assert geo["version"] == "1.1.0"
    assert geo["primary_column"] == "geometry"
    assert geo["columns"]["geometry"]["encoding"] == "WKB"
    assert contract["analysis_crs"] == "EPSG:3310"
    assert contract["source"]["sha256"] == _SOURCE_SHA256
    assert contract["processing_extent"]["bounds_wgs84"] == [
        -122.0,
        32.0,
        -117.0,
        35.0,
    ]
    table = pq.read_table(output)
    stored = from_wkb(table["geometry"][0].as_py())
    assert stored.equals(dataset.cells[0].geometry)


def test_completion_timestamp_is_captured_after_parquet_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = _dataset(_INTERIOR_CELL)
    mask = _mask(tmp_path / "mask.txt", _INTERIOR_CELL)
    output = tmp_path / "water-grid.parquet"
    parquet_write_succeeded = False
    original_write_table = pq.write_table

    def tracking_write_table(*args: object, **kwargs: object) -> None:
        nonlocal parquet_write_succeeded
        original_write_table(*args, **kwargs)
        parquet_write_succeeded = True

    def completion_time() -> datetime:
        assert parquet_write_succeeded
        return _COMPLETED_AT

    monkeypatch.setattr(pq, "write_table", tracking_write_table)
    monkeypatch.setattr(spatial_grid, "_utc_now", completion_time)

    result = write_water_grid(dataset, mask, output, started_at=_STARTED_AT)
    lineage = json.loads(result.lineage_path.read_text(encoding="utf-8"))

    assert lineage["run"]["started_at"] != lineage["run"]["completed_at"]


def test_existing_output_is_refused_without_authorization(tmp_path: Path) -> None:
    geometry = _INTERIOR_CELL
    dataset = _dataset(geometry)
    mask = _mask(tmp_path / "mask.txt", geometry)
    output = tmp_path / "water-grid.parquet"
    write_water_grid(dataset, mask, output, started_at=_STARTED_AT)

    with pytest.raises(SpatialOutputError, match="explicit overwrite"):
        write_water_grid(dataset, mask, output, started_at=_STARTED_AT)


def test_output_under_raw_data_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    geometry = _INTERIOR_CELL
    dataset = _dataset(geometry)
    mask = _mask(tmp_path / "mask.txt", geometry)
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    monkeypatch.setattr(spatial_grid, "_PROJECT_RAW_ROOT", raw_root.resolve())
    output = raw_root / "forbidden.parquet"

    with pytest.raises(SpatialOutputError, match="cannot be written under raw data"):
        write_water_grid(dataset, mask, output, started_at=_STARTED_AT)

    assert not output.exists()


def test_failed_write_leaves_no_final_or_temporary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    geometry = _INTERIOR_CELL
    dataset = _dataset(geometry)
    mask = _mask(tmp_path / "mask.txt", geometry)
    output = tmp_path / "water-grid.parquet"

    def fail_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic lineage failure")

    monkeypatch.setattr("whale_vessel_analysis.spatial_grid._write_json", fail_write)

    with pytest.raises(SpatialOutputError, match="synthetic lineage failure"):
        write_water_grid(dataset, mask, output, started_at=_STARTED_AT)

    assert not output.exists()
    assert not output.with_suffix(".parquet.lineage.json").exists()
    assert list(tmp_path.glob(".*.tmp")) == []
