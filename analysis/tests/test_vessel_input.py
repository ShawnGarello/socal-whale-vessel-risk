import json
from dataclasses import replace
from datetime import timedelta

import pyarrow.parquet as pq
import pytest
from shapely.geometry import box

from conftest import build_cleaned_bundle
from test_vessel_grid import (
    FIXED_TIME,
    _at,
    _cell,
    _grid,
    _manifest_and_reference,
    _roots,
    _two_cell_grid,
)
from whale_vessel_analysis import vessel_grid, vessel_input
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.multiday_ais_relation import (
    RelationResources,
    open_period_relation,
)
from whale_vessel_analysis.vessel_input_cli import main


def test_speed_observes_exact_pieces_without_changing_distance():
    grid = _grid(
        _cell("left", 0, box(0, -1, 500, 1)), _cell("right", 1, box(500, -1, 1000, 1))
    )
    accumulator = vessel_input._ProductionAccumulator(grid)
    # Known projected metres, isolating allocation from CRS arithmetic.
    accumulator._xy = lambda longitude, latitude: (longitude, latitude)
    base = {
        "vessel_type_group": "cargo",
        "next_vessel_type_group": "cargo",
        "observed_at_utc": FIXED_TIME,
        "next_observed_at_utc": FIXED_TIME + timedelta(seconds=100),
        "longitude": 0,
        "latitude": 0,
        "next_longitude": 1000,
        "next_latitude": 0,
        "sog_knots": 20,
        "next_sog_knots": 20,
    }
    accumulator.add_candidate_segment(base)
    accumulator.add_candidate_segment({**base, "sog_knots": None})
    accumulator.add_candidate_segment({**base, "sog_knots": 50, "next_sog_knots": 50})
    # Retained zero movement and rejected fast jump have no piece speed weight.
    accumulator.add_candidate_segment({**base, "next_longitude": 0})
    accumulator.add_candidate_segment(
        {**base, "next_observed_at_utc": FIXED_TIME + timedelta(seconds=1)}
    )
    for order, cell in enumerate(accumulator.speed_cells()):
        values = cell["cargo"].to_dict()
        assert values["sog_available_km"] == 0.5
        assert values["sog_unavailable_km"] == 0.5
        assert values["sog_inconsistent_km"] == 0.5
        assert values["reported_sog_mean_knots"] == 20
        assert values["implied_speed_mean_knots"] == pytest.approx(19.438444924406)
        assert accumulator.cell_distance_m["cargo"][order] == 1500


def test_outside_and_ambiguous_pieces_receive_no_speed():
    grid = _grid(
        _cell("left", 0, box(0, 0, 1000, 1000)),
        _cell("right", 1, box(0, -1000, 1000, 0)),
    )
    accumulator = vessel_input._ProductionAccumulator(grid)
    accumulator._xy = lambda longitude, latitude: (longitude, latitude)
    for latitude in (0, 2000):
        accumulator.add_candidate_segment(
            {
                "vessel_type_group": "cargo",
                "next_vessel_type_group": "cargo",
                "observed_at_utc": FIXED_TIME,
                "next_observed_at_utc": FIXED_TIME + timedelta(seconds=100),
                "longitude": 0,
                "latitude": latitude,
                "next_longitude": 1000,
                "next_latitude": latitude,
                "sog_knots": 20,
                "next_sog_knots": 20,
            }
        )
    assert accumulator.distance_by_group["cargo"]["ambiguous_boundary_m"].total == 1000
    assert accumulator.distance_by_group["cargo"]["outside_support_m"].total == 1000
    assert all(cell["cargo"].total_km == 0 for cell in accumulator.speed_cells())


def test_production_requires_ready_exact_dates_and_preserves_candidate_values(
    tmp_path, monkeypatch
):
    interim, derived, raw = _roots(tmp_path, monkeypatch)
    bundle = build_cleaned_bundle(
        tmp_path / "bundle",
        [
            ("123456789", _at("2024-07-01", 0, 0), 34.0, -118.01, "cargo"),
            ("123456789", _at("2024-07-01", 0, 3), 34.0, -117.99, "cargo"),
        ],
    )
    manifest, reference = _manifest_and_reference(tmp_path, interim, [bundle])
    grid = _two_cell_grid()
    config = load_default_config()
    resources = RelationResources("256MB", interim / "spill", 1)
    with open_period_relation(manifest, resources) as relation:
        with pytest.raises(ValueError, match="ready period"):
            vessel_input.build_vessel_input(
                relation, grid, reference, config, batch_size=2
            )
        ready = replace(reference, period_input_readiness={"status": "ready"})
        with pytest.raises(ValueError, match="all exact accepted dates"):
            vessel_input.build_vessel_input(relation, grid, ready, config, batch_size=2)
        # Only this fixture reduces the period: the production API has no override.
        monkeypatch.setattr(vessel_input, "accepted_utc_dates", lambda: ("2024-07-01",))
        with pytest.raises(ValueError, match="remain unverified"):
            vessel_input.build_vessel_input(
                relation,
                grid,
                replace(ready, observational_completeness={"status": "complete"}),
                config,
                batch_size=2,
            )
        result = vessel_input.build_vessel_input(
            relation, grid, ready, config, batch_size=1
        )
        candidate = vessel_grid.aggregate_vessel_grid(
            relation,
            grid,
            ready,
            vessel_input.selected_parameters(),
            config,
            batch_size=2,
        )
        assert result.aggregation.cells == candidate.cells
        for cell, speed in zip(candidate.cells, result.speeds, strict=True):
            assert speed["cargo"].total_km == pytest.approx(cell.vessel_km["cargo"])
            assert speed["passenger"].to_dict()["reported_sog_mean_knots"] is None
        first = vessel_input.write_vessel_input(
            result, derived / "first", relation=relation, started_at=FIXED_TIME
        )
        repeat = vessel_input.build_vessel_input(
            relation,
            grid,
            replace(ready, manifest_sha256="b" * 64),
            config,
            batch_size=2,
        )
        second = vessel_input.write_vessel_input(
            repeat,
            derived / "second",
            relation=relation,
            started_at=FIXED_TIME + timedelta(seconds=1),
        )
        assert first["input_id"] == second["input_id"]
        assert first["grid_sha256"] == second["grid_sha256"]
        assert first["quality_sha256"] == second["quality_sha256"]
        assert first["lineage_sha256"] != second["lineage_sha256"]
        table = pq.read_table(derived / "first/vessel-grid.parquet")
        metadata = json.loads(table.schema.metadata[b"whale_vessel_analysis"])
        assert metadata["contract"] == vessel_input.CONTRACT
        assert (
            metadata["parameters"]["vessel_length_filter"]["status"]
            == "type-only-no-length-filter"
        )
        lineage = json.loads((derived / "first/run-metadata.json").read_text())
        assert lineage["contract"] == vessel_input.LINEAGE_CONTRACT
        assert lineage["run"]["run_id"] == first["input_id"]
        assert lineage["visual_inspection_status"] == "not_completed"
        with pytest.raises(ValueError, match="already exists"):
            vessel_input.write_vessel_input(
                result, derived / "first", relation=relation, started_at=FIXED_TIME
            )
        with pytest.raises(ValueError, match="raw data"):
            vessel_input.write_vessel_input(
                result, raw / "bad", relation=relation, started_at=FIXED_TIME
            )

        def fail(*args):
            raise OSError("test rename failure")

        monkeypatch.setattr(vessel_grid, "_publish_bundle", fail)
        with pytest.raises(ValueError, match="retained evidence"):
            vessel_input.write_vessel_input(
                result, derived / "failed", relation=relation, started_at=FIXED_TIME
            )
        assert not (derived / "failed").exists()
        assert len(list(derived.glob(".failed.temporary-*"))) == 1


def test_cli_has_no_rule_or_overwrite_override_and_fails_before_scan(
    tmp_path, monkeypatch
):
    _, derived, _ = _roots(tmp_path, monkeypatch)
    target = derived / "existing"
    target.mkdir()
    args = [
        "--manifest",
        "missing.json",
        "--grid-input",
        "missing.parquet",
        "--expected-grid-sha256",
        "a" * 64,
        "--output-dir",
        str(target),
        "--memory-limit",
        "1GB",
        "--threads",
        "1",
        "--batch-size",
        "50000",
        "--temp-directory",
        str(tmp_path / "spill"),
    ]
    assert main(args) == 2
    with pytest.raises(SystemExit):
        main([*args, "--overwrite"])
    with pytest.raises(SystemExit):
        main([*args, "--maximum-gap-seconds", "1800"])
