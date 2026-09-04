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
from whale_vessel_analysis.period_vessel_rule_evidence import (
    VESSEL_LENGTH_TREATMENT,
    PeriodEvidenceInputReference,
    PeriodVesselRuleParameters,
    build_period_vessel_rule_evidence,
)
from whale_vessel_analysis.vessel_activity_evidence import (
    build_evidence_report,
    load_cleaned_bundle,
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


def test_candidate_and_evidence_paths_match_for_shared_nonambiguous_logic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Protect the semantics shared by the diagnostic and candidate boundaries."""
    interim, _derived, _raw = _roots(tmp_path, monkeypatch)
    rows = [
        ("111111111", _at("2024-07-01", 0, 0), 34.0, -118.01, "cargo"),
        ("111111111", _at("2024-07-01", 0, 2), 34.0, -117.99, "cargo"),
        ("222222222", _at("2024-07-01", 0, 0), 34.0, -118.01, "passenger"),
        ("222222222", _at("2024-07-01", 0, 10), 34.0, -117.99, "passenger"),
        ("333333333", _at("2024-07-01", 0, 0), 34.0, -118.01, "tanker"),
        ("333333333", _at("2024-07-01", 0, 0, 30), 34.0, -117.99, "tanker"),
    ]
    bundle = build_cleaned_bundle(tmp_path / "bundle", rows)
    manifest, reference = _manifest_and_reference(tmp_path, interim, [bundle])
    grid = _two_cell_grid()
    parameters = _parameters(gap=300, speed=40)
    dataset, handle = _aggregate(manifest, reference, grid, interim, parameters)
    try:
        evidence = build_evidence_report(
            load_cleaned_bundle(bundle),
            candidate_maximum_gap_seconds=(300,),
            candidate_implied_speed_ceiling_knots=(40,),
            target_grid=grid,
        )
        sensitivity = evidence["candidate_rule_sensitivity"]
        scenario = sensitivity["candidate_scenarios"][0]
        allocation_wrapper = evidence["optional_grid_allocation"][
            "candidate_scenarios"
        ][0]
        allocation = allocation_wrapper["allocation"]
        candidate_counts = dataset.quality["counts"]["candidate_segments"]
        candidate_exclusions = dataset.quality["counts"]["primary_exclusions"]

        assert candidate_counts["retained"] == scenario["retained_segment_count"]
        assert candidate_counts["excluded"] == 2
        assert (
            candidate_exclusions["maximum_gap"]
            == scenario["primary_exclusion_counts"]["gap"]
        )
        assert (
            candidate_exclusions["implied_speed"]
            == scenario["primary_exclusion_counts"]["implied_speed"]
        )

        for evidence_cell, candidate_cell, target_cell in zip(
            allocation["per_cell"], dataset.cells, grid.cells, strict=True
        ):
            assert evidence_cell["cell_id"] == target_cell.cell_id
            for group in (*vessel_grid.VESSEL_GROUPS, vessel_grid.ALL_COMMERCIAL):
                assert candidate_cell.vessel_km[group] == pytest.approx(
                    evidence_cell["vessel_kilometres"][group], abs=1e-12
                )

        candidate_commercial_m = dataset.quality["distance_conservation"]["by_group"][
            "all_commercial"
        ]["allocated_to_cells_m"]
        evidence_commercial_km = allocation["by_group"]["all_commercial"][
            "in_support_length_km"
        ]
        assert candidate_commercial_m / 1_000 == pytest.approx(
            evidence_commercial_km, abs=1e-12
        )
    finally:
        _close_relation(handle)


def test_period_rule_evidence_matches_candidate_grid_for_all_four_rules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the non-spatial rule evidence aligned with candidate-grid filtering."""
    interim, _derived, _raw = _roots(tmp_path, monkeypatch)
    day_one = build_cleaned_bundle(
        tmp_path / "bundles" / "parity-day-1",
        [
            ("111111111", _at("2024-07-01", 23, 59), 34.0, -118.005, "cargo"),
            ("222222222", _at("2024-07-01", 0, 0), 34.0, -118.005, "passenger"),
            ("222222222", _at("2024-07-01", 0, 10), 34.0, -117.999, "passenger"),
            ("333333333", _at("2024-07-01", 1, 0), 34.0, -118.005, "tanker"),
            ("333333333", _at("2024-07-01", 1, 1), 34.0, -117.980, "tanker"),
            ("444444444", _at("2024-07-01", 2, 0), 34.0, -118.000, "cargo"),
            ("444444444", _at("2024-07-01", 2, 1), 34.0, -118.000, "passenger"),
            ("555555555", _at("2024-07-01", 3, 0), 34.0, -118.000, "cargo"),
            ("555555555", _at("2024-07-01", 3, 0), 34.0, -117.999, "cargo"),
            ("666666666", _at("2024-07-01", 4, 0), 34.0, -118.000, "cargo"),
            ("666666666", _at("2024-07-01", 4, 1), 34.0, -117.986, "cargo"),
        ],
        run_id="ais-period-grid-parity-day-1",
    )
    day_two = build_cleaned_bundle(
        tmp_path / "bundles" / "parity-day-2",
        [
            ("111111111", _at("2024-07-02", 0, 1), 34.0, -117.999, "cargo"),
            ("111111111", _at("2024-07-02", 0, 3), 34.0, -117.999, "cargo"),
        ],
        run_id="ais-period-grid-parity-day-2",
    )
    manifest, grid_reference = _manifest_and_reference(
        tmp_path, interim, [day_two, day_one]
    )
    evidence_reference = PeriodEvidenceInputReference(
        manifest_path=grid_reference.manifest_path,
        manifest_sha256=grid_reference.manifest_sha256,
        period_input_id=grid_reference.period_input_id,
        period_input_readiness=grid_reference.period_input_readiness,
        independent_transfer_completeness=manifest["independent_transfer_completeness"],
        observational_completeness=grid_reference.observational_completeness,
    )
    evidence_parameters = PeriodVesselRuleParameters(
        maximum_gap_seconds=(300.0, 1_800.0),
        implied_speed_ceiling_knots=(30.0, 50.0),
        vessel_length_treatment=VESSEL_LENGTH_TREATMENT,
        allow_incomplete_non_production=True,
    )
    resources = RelationResources(
        memory_limit="256MB", temporary_directory=interim / "parity-spill", threads=1
    )
    with open_period_relation(manifest, resources) as relation:
        evidence = build_period_vessel_rule_evidence(
            relation,
            evidence_reference,
            evidence_parameters,
            batch_size=2,
        )
        evidence_matrix = {
            (
                candidate["maximum_gap_seconds"],
                candidate["implied_speed_ceiling_knots"],
            ): candidate
            for candidate in evidence.document["whole_period_by_vessel_group"][
                "all_commercial"
            ]["candidate_matrix"]
        }
        grid = _two_cell_grid()
        for gap, speed in (
            (300.0, 30.0),
            (300.0, 50.0),
            (1_800.0, 30.0),
            (1_800.0, 50.0),
        ):
            candidate_grid = aggregate_vessel_grid(
                relation,
                grid,
                grid_reference,
                _parameters(gap=gap, speed=speed),
                load_default_config(),
                batch_size=3,
            )
            expected = evidence_matrix[(gap, speed)]
            counts = candidate_grid.quality["counts"]["candidate_segments"]
            assert counts["retained"] == expected["retained_segments"]
            assert counts["excluded"] == expected["excluded_segments"]
            assert (
                candidate_grid.quality["counts"]["primary_exclusions"]
                == expected["primary_exclusions"]
            )
            assert (
                counts["cross_midnight_retained"]
                == expected["cross_midnight_retained_segments"]
            )
            assert (
                counts["zero_length_retained"]
                == expected["zero_length_retained_segments"]
            )
            retained_parent = candidate_grid.quality["distance_conservation"][
                "by_group"
            ]["all_commercial"]["retained_parent_m"]
            assert retained_parent == pytest.approx(
                expected["retained_projected_endpoint_distance_m"], abs=1e-9
            )


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
        assert "manifest_sha256" not in metadata["input"]
        lineage = json.loads(first.lineage_path.read_text(encoding="utf-8"))
        settings = lineage["execution_settings"]
        assert settings["arrow_batch_size_rows"] == 2
        assert settings["duckdb"]["requested_memory_limit"] == "256MB"
        assert settings["duckdb"]["requested_threads"] == 1
        assert settings["spill_directory"] == {
            "configured": True,
            "run_isolated": True,
            "location_class": "ignored data/interim",
            "local_path_recorded": False,
        }
        assert str(interim) not in json.dumps(settings)
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


def test_manifest_path_timestamp_and_retry_history_do_not_change_output_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, derived, _raw = _roots(tmp_path, monkeypatch)
    rows = [
        ("123456789", _at("2024-07-01", 0, 0), 34.0, -118.01, "cargo"),
        ("123456789", _at("2024-07-01", 0, 1), 34.0, -117.99, "cargo"),
    ]
    bundle_a = build_cleaned_bundle(
        tmp_path / "worktree-a" / "bundle",
        rows,
        run_id="ais-equivalent-input",
        started_at="2026-08-30T00:00:00Z",
        completed_at="2026-08-30T00:00:01Z",
    )
    bundle_b = build_cleaned_bundle(
        tmp_path / "worktree-b" / "bundle",
        rows,
        run_id="ais-equivalent-input",
        started_at="2026-08-31T00:00:00Z",
        completed_at="2026-08-31T00:00:01Z",
    )
    manifest_path_a = interim / "worktree-a-manifest.json"
    manifest_path_b = interim / "worktree-b-manifest.json"
    update_a = record_cleaned_days(
        manifest_path_a, [bundle_a], clock=lambda: FIXED_TIME
    )
    record_cleaned_days(
        manifest_path_b,
        [bundle_b],
        clock=lambda: datetime(2026, 8, 31, 12, tzinfo=UTC),
    )
    update_b = record_cleaned_days(
        manifest_path_b,
        [bundle_b],
        clock=lambda: datetime(2026, 9, 1, 12, tzinfo=UTC),
    )
    assert update_a.period_input_id == update_b.period_input_id
    assert vessel_grid.sha256_file(manifest_path_a) != vessel_grid.sha256_file(
        manifest_path_b
    )
    reference_a = PeriodInputReference(
        manifest_path=manifest_path_a,
        manifest_sha256=vessel_grid.sha256_file(manifest_path_a),
        period_input_id=update_a.period_input_id,
        period_input_readiness=update_a.manifest["period_input_readiness"],
        observational_completeness=update_a.manifest["observational_completeness"],
    )
    reference_b = PeriodInputReference(
        manifest_path=manifest_path_b,
        manifest_sha256=vessel_grid.sha256_file(manifest_path_b),
        period_input_id=update_b.period_input_id,
        period_input_readiness=update_b.manifest["period_input_readiness"],
        observational_completeness=update_b.manifest["observational_completeness"],
    )
    grid = _two_cell_grid(path=tmp_path / "grid.parquet")

    dataset_a, handle_a = _aggregate(
        dict(update_a.manifest), reference_a, grid, interim, _parameters(speed=1_000)
    )
    context_a, relation_a = handle_a
    try:
        result_a = write_vessel_grid(
            dataset_a,
            derived / "manifest-a",
            started_at=FIXED_TIME,
            relation=relation_a,
        )
    finally:
        context_a.__exit__(None, None, None)

    dataset_b, handle_b = _aggregate(
        dict(update_b.manifest), reference_b, grid, interim, _parameters(speed=1_000)
    )
    context_b, relation_b = handle_b
    try:
        result_b = write_vessel_grid(
            dataset_b,
            derived / "manifest-b",
            started_at=FIXED_TIME,
            relation=relation_b,
        )
    finally:
        context_b.__exit__(None, None, None)

    assert dataset_a.grid_id == dataset_b.grid_id
    assert result_a.grid_path.read_bytes() == result_b.grid_path.read_bytes()
    assert result_a.quality_path.read_bytes() == result_b.quality_path.read_bytes()
    lineage_a = json.loads(result_a.lineage_path.read_text(encoding="utf-8"))
    lineage_b = json.loads(result_b.lineage_path.read_text(encoding="utf-8"))
    manifest_input_a = next(
        item
        for item in lineage_a["run"]["inputs"]
        if item["artifact_id"] == "multi-day-cleaned-ais-manifest"
    )
    manifest_input_b = next(
        item
        for item in lineage_b["run"]["inputs"]
        if item["artifact_id"] == "multi-day-cleaned-ais-manifest"
    )
    assert manifest_input_a["sha256"] == reference_a.manifest_sha256
    assert manifest_input_b["sha256"] == reference_b.manifest_sha256
    assert manifest_input_a["sha256"] != manifest_input_b["sha256"]


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
