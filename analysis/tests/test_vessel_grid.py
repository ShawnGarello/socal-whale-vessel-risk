from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pyarrow.parquet as pq
import pytest
from pyproj import Transformer
from shapely import to_wkb
from shapely.geometry import LineString, box

from conftest import build_cleaned_bundle
from whale_vessel_analysis import multiday_ais, vessel_grid
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.multiday_ais import record_cleaned_days
from whale_vessel_analysis.multiday_ais_relation import (
    RelationResources,
    open_period_relation,
)
from whale_vessel_analysis.vessel_grid import (
    ALLOW_INCOMPLETE_PERIOD,
    EDGE_TREATMENT,
    SUPPORT_TREATMENT,
    PeriodInputReference,
    VesselGridError,
    VesselGridParameters,
    aggregate_vessel_grid,
    validate_input_output_separation,
    write_vessel_grid,
)
from whale_vessel_analysis.whale_grid import TargetGridCell, TargetGridInspection

FIXED_TIME = datetime(2026, 8, 30, 12, tzinfo=UTC)


def _roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    interim = tmp_path / "data" / "interim"
    derived = tmp_path / "data" / "derived"
    raw = tmp_path / "data" / "raw"
    interim.mkdir(parents=True)
    derived.mkdir(parents=True)
    raw.mkdir(parents=True)
    monkeypatch.setattr(multiday_ais, "_PROJECT_INTERIM_ROOT", interim.resolve())
    monkeypatch.setattr(multiday_ais, "_PROJECT_RAW_ROOT", raw.resolve())
    monkeypatch.setattr(vessel_grid, "_PROJECT_DERIVED_ROOT", derived.resolve())
    monkeypatch.setattr(vessel_grid, "_PROJECT_RAW_ROOT", raw.resolve())
    return interim, derived, raw


def _at(utc_date: str, hour: int, minute: int, second: int = 0) -> datetime:
    return datetime.fromisoformat(utc_date).replace(
        hour=hour, minute=minute, second=second, tzinfo=UTC
    )


def _cell(cell_id: str, order: int, geometry: Any) -> TargetGridCell:
    x_min, y_min, x_max, y_max = geometry.bounds
    return TargetGridCell(
        cell_id=cell_id,
        row_index=0,
        column_index=order,
        x_min_m=math.floor(x_min),
        y_min_m=math.floor(y_min),
        x_max_m=math.ceil(x_max),
        y_max_m=math.ceil(y_max),
        water_area_m2=float(geometry.area),
        water_area_km2=float(geometry.area) / 1_000_000.0,
        geometry=geometry,
        geometry_wkb=to_wkb(geometry),
    )


def _grid(*cells: TargetGridCell, path: Path | None = None) -> TargetGridInspection:
    return TargetGridInspection(
        cells=tuple(cells),
        path=path or Path("synthetic-grid.parquet"),
        sha256="a" * 64,
        metadata={},
    )


def _two_cell_grid(
    start_lon: float = -118.01,
    end_lon: float = -117.99,
    path: Path | None = None,
) -> TargetGridInspection:
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True)
    start_x, start_y = transformer.transform(start_lon, 34.0)
    end_x, end_y = transformer.transform(end_lon, 34.0)
    boundary = (start_x + end_x) / 2.0
    y_min = min(start_y, end_y) - 1_000
    y_max = max(start_y, end_y) + 1_000
    return _grid(
        _cell("left", 0, box(start_x - 100, y_min, boundary, y_max)),
        _cell("right", 1, box(boundary, y_min, end_x + 100, y_max)),
        path=path,
    )


def _parameters(*, gap: float = 300.0, speed: float = 100.0) -> VesselGridParameters:
    return VesselGridParameters(
        maximum_gap_seconds=gap,
        implied_speed_ceiling_knots=speed,
        period_readiness_treatment=ALLOW_INCOMPLETE_PERIOD,
        edge_treatment=EDGE_TREATMENT,
        support_treatment=SUPPORT_TREATMENT,
    )


def _manifest_and_reference(
    tmp_path: Path,
    interim: Path,
    bundles: list[Path],
) -> tuple[dict[str, Any], PeriodInputReference]:
    manifest_path = interim / "period-manifest.json"
    update = record_cleaned_days(manifest_path, bundles, clock=lambda: FIXED_TIME)
    return dict(update.manifest), PeriodInputReference(
        manifest_path=manifest_path,
        manifest_sha256=vessel_grid.sha256_file(manifest_path),
        period_input_id=update.period_input_id,
        period_input_readiness=update.manifest["period_input_readiness"],
        observational_completeness=update.manifest["observational_completeness"],
    )


def _aggregate(
    manifest: dict[str, Any],
    reference: PeriodInputReference,
    grid: TargetGridInspection,
    interim: Path,
    parameters: VesselGridParameters,
) -> tuple[vessel_grid.VesselGridDataset, Any]:
    resources = RelationResources(
        memory_limit="256MB", temporary_directory=interim / "spill", threads=1
    )
    context = open_period_relation(manifest, resources)
    relation = context.__enter__()
    try:
        dataset = aggregate_vessel_grid(
            relation,
            grid,
            reference,
            parameters,
            load_default_config(),
            batch_size=2,
        )
    except Exception:
        context.__exit__(*__import__("sys").exc_info())
        raise
    return dataset, (context, relation)


def _close_relation(handle: Any) -> None:
    context, _relation = handle
    context.__exit__(None, None, None)


def test_cross_midnight_segment_crosses_cells_and_conserves_distance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _derived, _raw = _roots(tmp_path, monkeypatch)
    first = build_cleaned_bundle(
        tmp_path / "bundles" / "day-1",
        [("123456789", _at("2024-07-01", 23, 59), 34.0, -118.01, "cargo")],
        run_id="ais-midnight-day-1",
    )
    second = build_cleaned_bundle(
        tmp_path / "bundles" / "day-2",
        [("123456789", _at("2024-07-02", 0, 1), 34.0, -117.99, "cargo")],
        run_id="ais-midnight-day-2",
    )
    manifest, reference = _manifest_and_reference(tmp_path, interim, [second, first])

    dataset, handle = _aggregate(
        manifest, reference, _two_cell_grid(), interim, _parameters()
    )
    try:
        left, right = dataset.cells
        quality = dataset.quality
        candidate = quality["counts"]["candidate_segments"]
        conservation = quality["distance_conservation"]
        assert candidate["cross_midnight_candidates"] == 1
        assert candidate["cross_midnight_retained"] == 1
        assert left.vessel_km["cargo"] > 0
        assert right.vessel_km["cargo"] > 0
        assert left.vessel_km["all_commercial"] == left.vessel_km["cargo"]
        assert conservation["passed"] is True
        assert conservation["by_group"]["all_commercial"]["difference_m"] == 0.0
        assert conservation["per_cell_output_total_m"] == pytest.approx(
            conservation["by_group"]["all_commercial"]["retained_parent_m"],
            abs=1e-6,
        )
    finally:
        _close_relation(handle)


@pytest.mark.parametrize(
    ("elapsed_seconds", "parameters", "reason"),
    [
        (600, _parameters(gap=300, speed=1_000), "maximum_gap"),
        (30, _parameters(gap=300, speed=30), "implied_speed"),
    ],
)
def test_explicit_gap_and_speed_rules_exclude_primary_segment_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    elapsed_seconds: int,
    parameters: VesselGridParameters,
    reason: str,
) -> None:
    interim, _derived, _raw = _roots(tmp_path, monkeypatch)
    rows = [
        ("123456789", _at("2024-07-01", 0, 0), 34.0, -118.01, "cargo"),
        (
            "123456789",
            _at("2024-07-01", 0, elapsed_seconds // 60, elapsed_seconds % 60),
            34.0,
            -117.99,
            "cargo",
        ),
    ]
    bundle = build_cleaned_bundle(tmp_path / "bundle", rows)
    manifest, reference = _manifest_and_reference(tmp_path, interim, [bundle])
    dataset, handle = _aggregate(
        manifest, reference, _two_cell_grid(), interim, parameters
    )
    try:
        exclusions = dataset.quality["counts"]["primary_exclusions"]
        assert exclusions[reason] == 1
        assert sum(cell.vessel_km["all_commercial"] for cell in dataset.cells) == 0
    finally:
        _close_relation(handle)


def test_zero_length_and_outside_support_are_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _derived, _raw = _roots(tmp_path, monkeypatch)
    rows = [
        ("111111111", _at("2024-07-01", 0, 0), 34.0, -118.0, "cargo"),
        ("111111111", _at("2024-07-01", 0, 1), 34.0, -118.0, "cargo"),
        ("222222222", _at("2024-07-01", 0, 0), 34.0, -117.0, "tanker"),
        ("222222222", _at("2024-07-01", 0, 1), 34.0, -116.999, "tanker"),
    ]
    bundle = build_cleaned_bundle(tmp_path / "bundle", rows)
    manifest, reference = _manifest_and_reference(tmp_path, interim, [bundle])
    dataset, handle = _aggregate(
        manifest, reference, _two_cell_grid(), interim, _parameters(speed=1_000)
    )
    try:
        statuses = dataset.quality["counts"]["allocation_status"]
        assert statuses["zero_length_in_support"] == 1
        assert statuses["positive_length_outside_support"] == 1
        distance = dataset.quality["distance_conservation"]["by_group"]
        assert distance["tanker"]["outside_support_m"] > 0
        assert distance["all_commercial"]["difference_m"] == 0.0
    finally:
        _close_relation(handle)


def test_boundary_ambiguity_is_excluded_and_distinct_union_is_recomputed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _derived, _raw = _roots(tmp_path, monkeypatch)
    forward = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True)
    inverse = Transformer.from_crs("EPSG:3310", "EPSG:4326", always_xy=True)
    x0, y0 = forward.transform(-118.0, 34.0)
    first_lon, first_lat = inverse.transform(x0, y0 - 100)
    second_lon, second_lat = inverse.transform(x0, y0 + 100)
    first_xy = forward.transform(first_lon, first_lat)
    second_xy = forward.transform(second_lon, second_lat)
    boundary = LineString([first_xy, second_xy])
    parts = [
        boundary.buffer(500, single_sided=True, cap_style="flat"),
        boundary.buffer(-500, single_sided=True, cap_style="flat"),
    ]
    grid = _grid(_cell("side-a", 0, parts[0]), _cell("side-b", 1, parts[1]))
    inside_lon, inside_lat = inverse.transform(x0 - 250, y0)
    rows = [
        (
            "111111111",
            _at("2024-07-01", 0, 0),
            first_lat,
            first_lon,
            "cargo",
        ),
        (
            "111111111",
            _at("2024-07-01", 0, 1),
            second_lat,
            second_lon,
            "cargo",
        ),
        (
            "222222222",
            _at("2024-07-01", 0, 0),
            inside_lat,
            inside_lon,
            "passenger",
        ),
        (
            "222222222",
            _at("2024-07-01", 0, 1),
            inside_lat,
            inside_lon,
            "cargo",
        ),
    ]
    assert boundary.length == pytest.approx(200, abs=1e-5)
    bundle = build_cleaned_bundle(tmp_path / "bundle", rows)
    manifest, reference = _manifest_and_reference(tmp_path, interim, [bundle])
    dataset, handle = _aggregate(
        manifest, reference, grid, interim, _parameters(speed=1_000)
    )
    try:
        quality = dataset.quality
        assert (
            quality["counts"]["allocation_status"]["positive_length_ambiguous_boundary"]
            == 1
        )
        assert (
            quality["distance_conservation"]["by_group"]["cargo"][
                "ambiguous_boundary_m"
            ]
            > 0
        )
        inside_cell = next(
            cell for cell in dataset.cells if cell.distinct_mmsi["passenger"] == 1
        )
        assert inside_cell.distinct_mmsi["cargo"] == 1
        assert inside_cell.distinct_mmsi["all_commercial"] == 1
        assert (
            inside_cell.distinct_mmsi["passenger"] + inside_cell.distinct_mmsi["cargo"]
            > inside_cell.distinct_mmsi["all_commercial"]
        )
    finally:
        _close_relation(handle)


def test_deterministic_serialization_overwrite_and_output_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, derived, raw = _roots(tmp_path, monkeypatch)
    rows = [
        ("123456789", _at("2024-07-01", 0, 0), 34.0, -118.01, "cargo"),
        ("123456789", _at("2024-07-01", 0, 1), 34.0, -117.99, "cargo"),
    ]
    bundle = build_cleaned_bundle(tmp_path / "bundle", rows)
    manifest, reference = _manifest_and_reference(tmp_path, interim, [bundle])
    dataset, handle = _aggregate(
        manifest,
        reference,
        _two_cell_grid(path=tmp_path / "grid.parquet"),
        interim,
        _parameters(speed=1_000),
    )
    context, relation = handle
    try:
        first = write_vessel_grid(
            dataset, derived / "first", started_at=FIXED_TIME, relation=relation
        )
        second = write_vessel_grid(
            dataset, derived / "second", started_at=FIXED_TIME, relation=relation
        )
        assert first.grid_path.read_bytes() == second.grid_path.read_bytes()
        assert first.quality_path.read_bytes() == second.quality_path.read_bytes()
        assert first.grid_sha256 == second.grid_sha256
        assert first.quality_sha256 == second.quality_sha256
        table = pq.read_table(first.grid_path)
        metadata = json.loads(table.schema.metadata[b"whale_vessel_analysis"])
        assert metadata["contract"] == vessel_grid.VESSEL_GRID_CONTRACT
        assert metadata["grid_id"] == dataset.grid_id
        with pytest.raises(VesselGridError, match="explicit overwrite"):
            write_vessel_grid(
                dataset, derived / "first", started_at=FIXED_TIME, relation=relation
            )
        repeated = write_vessel_grid(
            dataset,
            derived / "first",
            started_at=FIXED_TIME,
            relation=relation,
            overwrite=True,
        )
        assert repeated.grid_sha256 == first.grid_sha256
        arbitrary = derived / "arbitrary"
        arbitrary.mkdir()
        (arbitrary / "notes.txt").write_text("not a bundle", encoding="utf-8")
        with pytest.raises(VesselGridError, match="complete candidate"):
            write_vessel_grid(
                dataset,
                arbitrary,
                started_at=FIXED_TIME,
                relation=relation,
                overwrite=True,
            )
        with pytest.raises(VesselGridError, match="under raw"):
            write_vessel_grid(
                dataset, raw / "output", started_at=FIXED_TIME, relation=relation
            )
        with pytest.raises(VesselGridError, match="data/derived"):
            write_vessel_grid(
                dataset,
                tmp_path / "elsewhere" / "output",
                started_at=FIXED_TIME,
                relation=relation,
            )
    finally:
        context.__exit__(None, None, None)


def test_invalid_parameters_relation_batch_and_input_output_overlap_are_refused(
    tmp_path: Path,
) -> None:
    with pytest.raises(VesselGridError, match="finite and positive"):
        _parameters(gap=0)
    with pytest.raises(VesselGridError, match="finite and positive"):
        _parameters(speed=float("nan"))
    output = tmp_path / "data" / "derived" / "bundle"
    with pytest.raises(VesselGridError, match="must be separate"):
        validate_input_output_separation(output, [output / "manifest.json"])
    reference = PeriodInputReference(
        manifest_path=tmp_path / "manifest.json",
        manifest_sha256="m" * 64,
        period_input_id="multiday-ais-synthetic",
        period_input_readiness={"status": "not_ready"},
        observational_completeness={"status": "unverified"},
    )
    with pytest.raises(VesselGridError, match="batch size"):
        aggregate_vessel_grid(
            cast(Any, object()),
            _two_cell_grid(),
            reference,
            _parameters(),
            load_default_config(),
            batch_size=0,
        )
    with pytest.raises(VesselGridError, match="no cells"):
        aggregate_vessel_grid(
            cast(Any, object()),
            _grid(),
            reference,
            _parameters(),
            load_default_config(),
            batch_size=1,
        )


def test_failed_publication_leaves_no_output_or_temporary_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, derived, _raw = _roots(tmp_path, monkeypatch)
    rows = [
        ("123456789", _at("2024-07-01", 0, 0), 34.0, -118.01, "cargo"),
        ("123456789", _at("2024-07-01", 0, 1), 34.0, -117.99, "cargo"),
    ]
    bundle = build_cleaned_bundle(tmp_path / "bundle", rows)
    manifest, reference = _manifest_and_reference(tmp_path, interim, [bundle])
    dataset, handle = _aggregate(
        manifest, reference, _two_cell_grid(), interim, _parameters(speed=1_000)
    )
    context, relation = handle

    def fail_publish(_temporary: Path, _target: Path, _overwrite: bool) -> None:
        raise OSError("synthetic atomic publication failure")

    monkeypatch.setattr(vessel_grid, "_publish_bundle", fail_publish)
    output = derived / "failed"
    try:
        with pytest.raises(VesselGridError, match="synthetic atomic"):
            write_vessel_grid(dataset, output, started_at=FIXED_TIME, relation=relation)
        assert not output.exists()
        assert list(derived.glob(".failed.temporary-*")) == []
    finally:
        context.__exit__(None, None, None)
