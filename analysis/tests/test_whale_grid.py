from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely import from_wkb, to_wkb
from shapely.geometry import Point, Polygon, box
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis import whale_grid
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.spatial_grid import (
    MaskInspection,
    construct_water_grid,
    write_water_grid,
)
from whale_vessel_analysis.whale import WhaleValidationResult
from whale_vessel_analysis.whale_grid import (
    COVERAGE_NUMERICAL_TOLERANCE_M2,
    TargetGridCell,
    TargetGridInspection,
    WhaleGridConservationError,
    WhaleGridInputError,
    WhaleGridOutputError,
    WhaleGridOverlapError,
    WhaleSourceFeature,
    WhaleSourceInspection,
    load_target_grid,
    reproject_source_geometry,
    transfer_whale_density,
    write_whale_grid,
)

_SOURCE_SHA256 = "a" * 64
_GRID_SHA256 = "b" * 64
_STARTED_AT = datetime(2026, 8, 27, 12, tzinfo=UTC)
_COMPLETED_AT = datetime(2026, 8, 27, 12, 0, 1, tzinfo=UTC)
_SECOND_STARTED_AT = datetime(2026, 8, 27, 13, tzinfo=UTC)
_SECOND_COMPLETED_AT = datetime(2026, 8, 27, 13, 0, 1, tzinfo=UTC)


def _validation(feature_count: int) -> WhaleValidationResult:
    return WhaleValidationResult(
        path="synthetic.gdb",
        layer="Blue_whale_summer_fall",
        feature_count=feature_count,
        attribute_row_count=feature_count,
        null_geometry_rows=0,
        empty_geometry_rows=0,
        invalid_geometry_rows=0,
        missing_required_value_rows=0,
        invalid_density_rows=0,
        invalid_area_rows=0,
        invalid_abundance_rows=0,
        inconsistent_abundance_rows=0,
        invalid_uncertainty_rows=0,
        wrong_season_rows=0,
        populated_month_rows=0,
    )


def _source(
    tmp_path: Path, features: list[tuple[object, BaseGeometry]]
) -> WhaleSourceInspection:
    source_path = tmp_path / "synthetic-source.gdb"
    source_path.mkdir(exist_ok=True)
    (source_path / "table.bin").write_bytes(b"synthetic source")
    source_features = tuple(
        WhaleSourceFeature(index, cast(float, density), geometry)
        for index, (density, geometry) in enumerate(features)
    )
    return WhaleSourceInspection(
        features=source_features,
        path=source_path,
        layer="Blue_whale_summer_fall",
        source_crs="EPSG:4326",
        source_sha256=_SOURCE_SHA256,
        transformation="synthetic always_xy transformation",
        validation=_validation(len(features)),
    )


def _geometry_wkb(geometry: BaseGeometry) -> bytes:
    return cast(
        bytes,
        to_wkb(
            geometry,
            hex=False,
            output_dimension=2,
            byte_order=1,
            include_srid=False,
            flavor="iso",
        ),
    )


def _target_cell(
    row_index: int, column_index: int, geometry: BaseGeometry
) -> TargetGridCell:
    config = load_default_config()
    grid = config.spatial.grid
    x_min = grid.x_min_m + column_index * grid.cell_size_m
    y_min = grid.y_min_m + row_index * grid.cell_size_m
    area_m2 = float(geometry.area)
    return TargetGridCell(
        cell_id=f"r{row_index:03d}_c{column_index:03d}",
        row_index=row_index,
        column_index=column_index,
        x_min_m=x_min,
        y_min_m=y_min,
        x_max_m=x_min + grid.cell_size_m,
        y_max_m=y_min + grid.cell_size_m,
        water_area_m2=area_m2,
        water_area_km2=area_m2 / 1_000_000.0,
        geometry=geometry,
        geometry_wkb=_geometry_wkb(geometry),
    )


def _target(tmp_path: Path, cells: list[TargetGridCell]) -> TargetGridInspection:
    path = tmp_path / "target-grid.parquet"
    path.write_bytes(b"synthetic target grid")
    return TargetGridInspection(
        cells=tuple(cells),
        path=path,
        sha256=_GRID_SHA256,
        metadata={"contract": "projected_water_grid_v1"},
    )


def _cell_geometry(row_index: int, column_index: int) -> Polygon:
    grid = load_default_config().spatial.grid
    x_min = grid.x_min_m + column_index * grid.cell_size_m
    y_min = grid.y_min_m + row_index * grid.cell_size_m
    return box(x_min, y_min, x_min + 5_000, y_min + 5_000)


def _transfer(
    tmp_path: Path,
    source_features: list[tuple[object, BaseGeometry]],
    target_cells: list[TargetGridCell],
):
    config = load_default_config()
    source = _source(tmp_path, source_features)
    target = _target(tmp_path, target_cells)
    return transfer_whale_density(source, target, config), source, target


def _valid_grid_path(tmp_path: Path) -> Path:
    config = load_default_config()
    geometry = _cell_geometry(34, 38)
    mask_path = tmp_path / "mask.txt"
    mask_path.write_text("synthetic mask\n", encoding="utf-8")
    mask = MaskInspection(
        geometry=geometry,
        path=mask_path,
        layer=None,
        source_crs="EPSG:3310",
        source_sha256="c" * 64,
        feature_count=1,
        null_geometry_count=0,
        empty_geometry_count=0,
        invalid_geometry_count=0,
        non_finite_geometry_count=0,
    )
    dataset = construct_water_grid(
        geometry,
        source_crs="EPSG:3310",
        source_sha256=mask.source_sha256,
        mask_feature_count=1,
        config=config,
    )
    output = tmp_path / "valid-water-grid.parquet"
    write_water_grid(dataset, mask, output, started_at=datetime.now(UTC))
    return output


def test_one_source_polygon_fully_covering_one_cell(tmp_path: Path) -> None:
    geometry = _cell_geometry(34, 38)
    dataset, _source_input, _target_input = _transfer(
        tmp_path, [(2.0, geometry)], [_target_cell(34, 38, geometry)]
    )

    cell = dataset.cells[0]
    assert cell.modeled_abundance_allocation_animals == pytest.approx(50.0)
    assert cell.modeled_density_animals_per_km2 == pytest.approx(2.0)
    assert cell.source_coverage_fraction == pytest.approx(1.0)
    assert cell.coverage_status == "complete"
    assert dataset.diagnostics.conservation_passed


def test_fractional_half_cell_overlap_is_not_renormalized(tmp_path: Path) -> None:
    water = _cell_geometry(34, 38)
    min_x, min_y, _max_x, max_y = water.bounds
    source_geometry = box(min_x, min_y, min_x + 2_500, max_y)
    dataset, _source_input, _target_input = _transfer(
        tmp_path, [(2.0, source_geometry)], [_target_cell(34, 38, water)]
    )

    cell = dataset.cells[0]
    assert cell.modeled_abundance_allocation_animals == pytest.approx(25.0)
    assert cell.modeled_density_animals_per_km2 == pytest.approx(1.0)
    assert cell.source_covered_water_area_m2 == pytest.approx(12_500_000.0)
    assert cell.uncovered_water_area_m2 == pytest.approx(12_500_000.0)
    assert cell.coverage_status == "incomplete"


def test_multiple_source_polygons_contribute_to_one_target_cell(tmp_path: Path) -> None:
    water = _cell_geometry(34, 38)
    min_x, min_y, max_x, max_y = water.bounds
    west = box(min_x, min_y, min_x + 2_500, max_y)
    east = box(min_x + 2_500, min_y, max_x, max_y)
    dataset, _source_input, _target_input = _transfer(
        tmp_path,
        [(2.0, west), (4.0, east)],
        [_target_cell(34, 38, water)],
    )

    cell = dataset.cells[0]
    assert cell.source_polygon_count == 2
    assert cell.modeled_abundance_allocation_animals == pytest.approx(75.0)
    assert cell.modeled_density_animals_per_km2 == pytest.approx(3.0)
    assert cell.coverage_status == "complete"


def test_one_source_polygon_contributes_to_multiple_target_cells(
    tmp_path: Path,
) -> None:
    west = _cell_geometry(34, 38)
    east = _cell_geometry(34, 39)
    source_geometry = box(*west.bounds[:2], east.bounds[2], east.bounds[3])
    target_cells = [_target_cell(34, 38, west), _target_cell(34, 39, east)]
    dataset, _source_input, _target_input = _transfer(
        tmp_path, [(2.0, source_geometry)], target_cells
    )

    assert [cell.target.cell_id for cell in dataset.cells] == [
        "r034_c038",
        "r034_c039",
    ]
    assert [cell.modeled_abundance_allocation_animals for cell in dataset.cells] == [
        pytest.approx(50.0),
        pytest.approx(50.0),
    ]
    assert dataset.diagnostics.source_contribution_animals == pytest.approx(100.0)
    assert dataset.diagnostics.allocated_abundance_animals == pytest.approx(100.0)


def test_independent_conservation_rejects_omitted_cell_intersections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    geometry = _cell_geometry(34, 38)

    class _OmittingTree:
        def __init__(self, _geometries: object) -> None:
            pass

        def query(self, _geometry: object) -> tuple[int, ...]:
            return ()

    monkeypatch.setattr(whale_grid, "STRtree", _OmittingTree)

    with pytest.raises(
        WhaleGridConservationError,
        match="did not conserve source contribution",
    ):
        _transfer(
            tmp_path,
            [(2.0, geometry)],
            [_target_cell(34, 38, geometry)],
        )


def test_coastal_partial_water_uses_actual_water_area(tmp_path: Path) -> None:
    parent = _cell_geometry(34, 38)
    min_x, min_y, max_x, max_y = parent.bounds
    water = Polygon([(min_x, min_y), (max_x, min_y), (min_x, max_y)])
    dataset, _source_input, _target_input = _transfer(
        tmp_path, [(2.0, parent)], [_target_cell(34, 38, water)]
    )

    cell = dataset.cells[0]
    assert cell.target.water_area_km2 == pytest.approx(12.5)
    assert cell.modeled_abundance_allocation_animals == pytest.approx(25.0)
    assert cell.modeled_density_animals_per_km2 == pytest.approx(2.0)
    assert cell.coverage_status == "complete"


def test_small_coverage_residual_is_distinguished_from_complete_support(
    tmp_path: Path,
) -> None:
    water = _cell_geometry(34, 38)
    min_x, min_y, max_x, max_y = water.bounds
    omitted_width = (COVERAGE_NUMERICAL_TOLERANCE_M2 / 2) / (max_y - min_y)
    source_geometry = box(min_x + omitted_width, min_y, max_x, max_y)
    dataset, _source_input, _target_input = _transfer(
        tmp_path, [(1.0, source_geometry)], [_target_cell(34, 38, water)]
    )

    cell = dataset.cells[0]
    assert cell.uncovered_water_area_m2 == pytest.approx(0.05, abs=1e-6)
    assert cell.coverage_status == "within_numerical_tolerance"
    assert dataset.diagnostics.numerical_tolerance_cell_count == 1


def test_stable_cell_identity_geometry_and_order_are_preserved(tmp_path: Path) -> None:
    first_geometry = _cell_geometry(34, 38)
    second_geometry = _cell_geometry(34, 39)
    targets = [
        _target_cell(34, 38, first_geometry),
        _target_cell(34, 39, second_geometry),
    ]
    dataset, _source_input, _target_input = _transfer(
        tmp_path,
        [(1.0, first_geometry), (2.0, second_geometry)],
        targets,
    )

    assert [cell.target.cell_id for cell in dataset.cells] == [
        "r034_c038",
        "r034_c039",
    ]
    assert [cell.target.geometry_wkb for cell in dataset.cells] == [
        target.geometry_wkb for target in targets
    ]


def test_known_longitude_latitude_transformation_uses_xy_order() -> None:
    source = box(-118.0, 34.0, -117.99, 34.01)

    projected, definition = reproject_source_geometry(source, "EPSG:4326")

    expected_corner = (184_755.8686105011, -444_218.17569026817)
    assert projected.boundary.distance(Point(expected_corner)) < 0.001
    assert "proj=aea" in definition


@pytest.mark.parametrize("crs", ["EPSG:3857", "not-a-crs"])
def test_unsupported_or_invalid_source_crs_is_rejected(crs: str) -> None:
    with pytest.raises(WhaleGridInputError, match="CRS"):
        reproject_source_geometry(box(-118.0, 34.0, -117.99, 34.01), crs)


@pytest.mark.parametrize(
    ("density", "message"),
    [
        (None, "missing"),
        (-1.0, "negative"),
        (float("nan"), "finite"),
        (float("inf"), "finite"),
    ],
)
def test_invalid_modeled_density_is_rejected(
    tmp_path: Path, density: object, message: str
) -> None:
    geometry = _cell_geometry(34, 38)
    with pytest.raises(WhaleGridInputError, match=message):
        _transfer(
            tmp_path,
            [(density, geometry)],
            [_target_cell(34, 38, geometry)],
        )


def test_source_polygon_interior_overlap_is_rejected(tmp_path: Path) -> None:
    water = _cell_geometry(34, 38)
    min_x, min_y, max_x, max_y = water.bounds
    first = box(min_x, min_y, min_x + 3_000, max_y)
    second = box(min_x + 2_000, min_y, max_x, max_y)

    with pytest.raises(WhaleGridOverlapError, match="overlap beyond tolerance"):
        _transfer(
            tmp_path,
            [(1.0, first), (1.0, second)],
            [_target_cell(34, 38, water)],
        )


def test_sub_square_metre_source_overlap_is_reported_as_numerical(
    tmp_path: Path,
) -> None:
    water = _cell_geometry(34, 38)
    min_x, min_y, max_x, max_y = water.bounds
    overlap_width = 0.5 / (max_y - min_y)
    west = box(min_x, min_y, min_x + 2_500 + overlap_width, max_y)
    east = box(min_x + 2_500, min_y, max_x, max_y)

    dataset, _source_input, _target_input = _transfer(
        tmp_path,
        [(1.0, west), (1.0, east)],
        [_target_cell(34, 38, water)],
    )

    assert dataset.diagnostics.source_overlap_pair_count_within_tolerance == 1
    assert dataset.diagnostics.source_overlap_area_m2_within_tolerance == pytest.approx(
        0.5, abs=1e-6
    )


def test_target_grid_checksum_and_contract_are_validated(tmp_path: Path) -> None:
    config = load_default_config()
    path = _valid_grid_path(tmp_path)
    checksum = whale_grid._sha256_file(path)

    loaded = load_target_grid(path, config, expected_sha256=checksum)

    assert len(loaded.cells) == 1
    assert loaded.sha256 == checksum
    with pytest.raises(WhaleGridInputError, match="checksum does not match"):
        load_target_grid(path, config, expected_sha256="0" * 64)


def test_existing_schema_v1_grid_metadata_remains_accepted(tmp_path: Path) -> None:
    config = load_default_config()
    path = _valid_grid_path(tmp_path)
    table = pq.read_table(path)
    metadata = table.schema.metadata

    assert metadata is not None
    contract = json.loads(metadata[b"whale_vessel_analysis"])
    assert contract["configuration"] == {
        "version": 1,
        "sha256": ("df60aa03796ca979eff5bdca4c620fbac809a797d40d320ea649276d6c889c06"),
    }
    assert load_target_grid(path, config).metadata["configuration"] == {
        "version": 1,
        "sha256": config.digest(),
    }


def test_invalid_target_grid_contract_is_rejected(tmp_path: Path) -> None:
    config = load_default_config()
    valid_path = _valid_grid_path(tmp_path)
    table = pq.read_table(valid_path)
    metadata = dict(table.schema.metadata or {})
    contract = json.loads(metadata[b"whale_vessel_analysis"])
    contract["contract"] = "wrong_contract"
    metadata[b"whale_vessel_analysis"] = json.dumps(contract).encode("utf-8")
    invalid_path = tmp_path / "invalid-grid.parquet"
    pq.write_table(table.replace_schema_metadata(metadata), invalid_path)

    with pytest.raises(WhaleGridInputError, match="contract must be"):
        load_target_grid(invalid_path, config)


def test_output_readback_lineage_checksums_and_determinism(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    geometry = _cell_geometry(34, 38)
    dataset, source, target = _transfer(
        tmp_path, [(2.0, geometry)], [_target_cell(34, 38, geometry)]
    )
    output = tmp_path / "whale-grid.parquet"
    completion_times = iter((_COMPLETED_AT, _SECOND_COMPLETED_AT))
    monkeypatch.setattr(whale_grid, "_utc_now", completion_times.__next__)

    first = write_whale_grid(
        dataset,
        source,
        target,
        output,
        started_at=_STARTED_AT,
        expected_grid_sha256=_GRID_SHA256,
    )
    first_bytes = output.read_bytes()
    first_lineage = json.loads(first.lineage_path.read_text(encoding="utf-8"))
    second = write_whale_grid(
        dataset,
        source,
        target,
        output,
        started_at=_SECOND_STARTED_AT,
        expected_grid_sha256=_GRID_SHA256,
        overwrite=True,
    )
    second_lineage = json.loads(second.lineage_path.read_text(encoding="utf-8"))

    assert output.read_bytes() == first_bytes
    assert first.output_sha256 == second.output_sha256
    assert first.lineage_sha256 != second.lineage_sha256
    assert first_lineage["run"]["run_id"] == second_lineage["run"]["run_id"]
    assert first_lineage["inputs"]["target_grid"]["checksum_verified"] is True
    assert first_lineage["parameters"]["uncertainty_propagation"] == "not_performed"
    assert first_lineage["software"]["pyarrow"] == pa.__version__
    table = pq.read_table(output)
    assert table.column_names == [
        "cell_id",
        "row_index",
        "column_index",
        "cell_x_min_m",
        "cell_y_min_m",
        "cell_x_max_m",
        "cell_y_max_m",
        "water_area_m2",
        "water_area_km2",
        "modeled_abundance_allocation_animals",
        "modeled_density_animals_per_km2",
        "source_covered_water_area_m2",
        "source_covered_water_area_km2",
        "uncovered_water_area_m2",
        "uncovered_water_area_km2",
        "source_coverage_fraction",
        "coverage_status",
        "source_polygon_count",
        "geometry",
    ]
    assert from_wkb(table["geometry"][0].as_py()).equals(geometry)
    metadata = table.schema.metadata
    assert metadata is not None
    contract = json.loads(metadata[b"whale_vessel_analysis"])
    assert contract["contract"] == "blue_whale_grid_transfer_v1"
    assert contract["units"]["modeled_density_animals_per_km2"] == "animals/km²"


def test_refusal_to_overwrite_and_atomic_failure_behavior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    geometry = _cell_geometry(34, 38)
    dataset, source, target = _transfer(
        tmp_path, [(2.0, geometry)], [_target_cell(34, 38, geometry)]
    )
    existing_output = tmp_path / "existing.parquet"
    monkeypatch.setattr(whale_grid, "_utc_now", lambda: _COMPLETED_AT)
    write_whale_grid(dataset, source, target, existing_output, started_at=_STARTED_AT)
    with pytest.raises(WhaleGridOutputError, match="explicit overwrite"):
        write_whale_grid(
            dataset, source, target, existing_output, started_at=_STARTED_AT
        )

    failed_output = tmp_path / "failed.parquet"

    def fail_write(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic lineage failure")

    monkeypatch.setattr(whale_grid, "_write_json", fail_write)
    with pytest.raises(WhaleGridOutputError, match="synthetic lineage failure"):
        write_whale_grid(dataset, source, target, failed_output, started_at=_STARTED_AT)
    assert not failed_output.exists()
    assert not failed_output.with_suffix(".parquet.lineage.json").exists()
    assert list(tmp_path.glob(".*.tmp")) == []
