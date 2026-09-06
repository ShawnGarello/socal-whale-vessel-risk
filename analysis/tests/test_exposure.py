"""Known-answer tests for the authorized exploratory method, not real inputs."""

from dataclasses import replace
from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import box

from whale_vessel_analysis import exposure_run
from whale_vessel_analysis.exposure import (
    analyze_grid,
    coarsen_10km,
    compare_methods,
    intensities,
    normalized,
    prepare_cells,
    summarize,
    weighted_quantile,
)
from whale_vessel_analysis.exposure_geometry import ExposureBoundaries
from whale_vessel_analysis.exposure_inputs import (
    ExposureInputCell,
    join_inputs,
    load_exposure_inputs,
)
from whale_vessel_analysis.whale_grid import TargetGridCell, TargetGridInspection


def cell(name, x, width, density, distance):
    water = box(x, 0, x + width, 1000)
    area = water.area / 1e6
    return ExposureInputCell(name, x, 0, water, area, density, density * area, distance)


def prepared():
    inputs = (
        cell("a", 0, 1000, 2, 10),
        cell("b", 1000, 2000, 1, 20),
        cell("c", 4000, 1000, 999, 999),
    )
    boundaries = ExposureBoundaries(
        box(0, 0, 2000, 1000), box(0, 0, 500, 1000), "EPSG:3310"
    )
    return prepare_cells(inputs, boundaries)


def test_intensity_integrated_area_and_partial_domain_known_answer():
    cells = prepared()
    values = intensities(cells, "product")
    assert values[:2] == [20, 10]
    result = summarize(cells, values)
    assert result["integrated_qualified"] == 30  # 20*1 + 10*1, not 20*1 + 10*2
    assert result["integrated_inside"] == 10
    assert result["integrated_outside"] == 20
    assert result["share_exposure_inside"] == pytest.approx(1 / 3)
    maximum, indices = normalized(values, cells)
    assert maximum == 20  # excluded huge value cannot set maximum
    assert indices == [1, 0.5, None]


def test_weighted_quantile_ties_and_cell_count_difference():
    assert weighted_quantile([1, 2, 3], [90, 5, 5], 0.8) == 1
    assert weighted_quantile([1, 2, 3], [1, 1, 1], 0.8) == 3
    assert weighted_quantile([5, 1, 5], [30, 40, 30], 0.9) == 5
    assert weighted_quantile([999, 1, 2], [0, 1, 1], 0.8) == 2


@pytest.mark.parametrize(
    "values,weights,p",
    [
        ([1], [0], 0.9),
        ([1], [-1], 0.9),
        ([float("nan")], [1], 0.9),
        ([1], [1], 0),
        ([1], [1], 1),
        ([1], [], 0.9),
    ],
)
def test_invalid_quantile_inputs_fail(values, weights, p):
    with pytest.raises(ValueError):
        weighted_quantile(values, weights, p)


def test_threshold_is_area_weighted_and_all_ties_included():
    inputs = [cell(str(i), i * 1000, 1000, 1, v) for i, v in enumerate((1, 5, 5))]
    boundaries = ExposureBoundaries(
        box(0, 0, 3000, 1000), box(0, 0, 2000, 1000), "EPSG:3310"
    )
    cells = prepare_cells(inputs, boundaries)
    result = summarize(cells, intensities(cells, "product"))
    p90 = result["thresholds"][1]
    assert p90["selected_cell_ids"] == ["1", "2"]
    assert p90["high_area_km2"] == 2
    assert p90["share_high_area_inside"] == 0.5
    assert p90["threshold_tied_area_km2"] == 2
    assert p90["share_domain_area_high"] == pytest.approx(2 / 3)


def test_zero_and_positive_only_threshold_population():
    inputs = [cell(str(i), i * 1000, 1000, 1, 1 if i == 19 else 0) for i in range(20)]
    cells = prepare_cells(
        inputs,
        ExposureBoundaries(box(0, 0, 20000, 1000), box(0, 0, 20000, 1000), "EPSG:3310"),
    )
    result = analyze_grid(cells)["methods"]["product"]
    assert result["thresholds"][1]["threshold"] == 0
    assert result["thresholds"][1]["share_high_area_inside"] is None
    assert result["thresholds"][4]["threshold"] == 1
    assert result["thresholds"][4]["high_area_km2"] == 1


def test_all_zero_results_have_no_fabricated_shares_indices_or_high_class():
    source = cell("zero", 0, 1000, 1, 0)
    cells = prepare_cells(
        [source], ExposureBoundaries(source.water, source.water, "EPSG:3310")
    )
    result = analyze_grid(cells)
    for summary in result["methods"].values():
        assert summary["integrated_qualified"] == 0
        assert summary["share_exposure_inside"] is None
        assert all(
            row["share_high_area_inside"] is None for row in summary["thresholds"]
        )
    assert normalized([0], cells) == (0, [None])
    assert not result["normalization_controls"]["product_max"]["available"]


def test_log_compression_changes_question_and_rank_ties_are_handled():
    cells = prepared()
    primary = intensities(cells, "product")
    log = intensities(cells, "log_traffic")
    assert log[0] == pytest.approx(2 * __import__("math").log1p(10))
    assert compare_methods(cells, [1, 2, 0], [2, 1, 0])["spearman_cell_ranks"] == -1
    assert compare_methods(cells, [1, 1, 0], [1, 1, 0])["spearman_cell_ranks"] is None
    result = analyze_grid(cells)
    assert result["normalization_controls"]["product_max"][
        "all_threshold_memberships_equal"
    ]
    assert result["normalization_controls"]["separate_input_maxima"][
        "inside_share_difference"
    ] == pytest.approx(0)
    assert primary[0] > log[0]


def test_coarse_recomputes_product_not_sum_of_fine_products():
    inputs = [cell("a", 0, 5000, 1, 100), cell("b", 5000, 5000, 3, 0)]
    coarse = coarsen_10km(inputs)
    assert len(coarse) == 1
    assert coarse[0].water_km2 == 10
    assert coarse[0].whale_abundance == 20
    assert coarse[0].vessel_km == 100
    assert coarse[0].whale_density == 2
    boundaries = ExposureBoundaries(
        box(0, 0, 10000, 1000), box(0, 0, 5000, 1000), "EPSG:3310"
    )
    fine = prepare_cells(inputs, boundaries)
    large = prepare_cells(coarse, boundaries)
    fine_result = summarize(fine, intensities(fine, "product"))
    coarse_result = summarize(large, intensities(large, "product"))
    assert fine_result["integrated_qualified"] == 100
    assert coarse_result["integrated_qualified"] == 200
    assert fine_result["share_exposure_inside"] == 1
    assert coarse_result["share_exposure_inside"] == 0.5


def test_coarse_negative_origins_floor_and_overlapping_water_rejected():
    a = cell("a", -5000, 5000, 1, 1)
    assert coarsen_10km([a])[0].x_min_m == -10000
    with pytest.raises(ValueError, match="area conservation"):
        coarsen_10km([a, replace(a, cell_id="b")])


def test_empty_domain_missing_density_duplicate_ids_rejected():
    a = cell("a", 0, 1000, 1, 1)
    boundaries = ExposureBoundaries(box(5000, 0, 6000, 1000), a.water, "EPSG:3310")
    with pytest.raises(ValueError, match="empty qualified"):
        prepare_cells([a], boundaries)
    with pytest.raises(ValueError, match="duplicate"):
        prepare_cells([a, a], boundaries)
    with pytest.raises(ValueError, match="missing"):
        prepare_cells([replace(a, whale_density=None)], boundaries)


def tables(tmp_path):
    geometry = box(0, 0, 1000, 1000)
    cell = TargetGridCell("a", 0, 0, 0, 0, 5000, 5000, 1e6, 1, geometry, geometry.wkb)
    grid = TargetGridInspection((cell,), tmp_path / "grid", "a" * 64, {})
    row = {
        "cell_id": "a",
        "row_index": 0,
        "column_index": 0,
        "cell_x_min_m": 0,
        "cell_y_min_m": 0,
        "cell_x_max_m": 5000,
        "cell_y_max_m": 5000,
        "water_area_m2": 1e6,
        "water_area_km2": 1,
        "geometry": geometry.wkb,
    }
    whale = {
        **row,
        "coverage_status": "complete",
        "uncovered_water_area_m2": 0.0,
        "source_covered_water_area_m2": 1e6,
        "source_coverage_fraction": 1.0,
        "modeled_density_animals_per_km2": 2.0,
        "modeled_abundance_allocation_animals": 2.0,
    }
    vessel = {
        **row,
        "vessel_km_all_commercial": 10.0,
        "vessel_km_per_water_km2_all_commercial": 10.0,
        "vessel_km_passenger": 3.0,
        "vessel_km_cargo": 7.0,
        "vessel_km_tanker": 0.0,
    }
    return grid, whale, vessel


def test_join_known_answer(tmp_path):
    grid, w, v = tables(tmp_path)
    joined = join_inputs(grid, pa.Table.from_pylist([w]), pa.Table.from_pylist([v]))
    assert joined[0].whale_density == 2
    assert joined[0].vessel_km == 10


@pytest.mark.parametrize(
    "field,value",
    [
        ("geometry", box(0, 0, 2000, 1000).wkb),
        ("cell_id", "different"),
        ("coverage_status", "incomplete"),
        ("modeled_density_animals_per_km2", None),
        ("modeled_abundance_allocation_animals", 4.0),
        ("uncovered_water_area_m2", 1.0),
        ("source_coverage_fraction", 0.5),
    ],
)
def test_join_rejects_bad_support_identity_and_values(tmp_path, field, value):
    grid, w, v = tables(tmp_path)
    w[field] = value
    with pytest.raises(ValueError):
        join_inputs(grid, pa.Table.from_pylist([w]), pa.Table.from_pylist([v]))


def test_retained_loader_refuses_unverified_file(tmp_path):
    p = tmp_path / "unverified"
    p.write_bytes(b"bad")
    with pytest.raises(ValueError, match="checksum"):
        load_exposure_inputs(p, p, p)


def test_serialized_results_verify_and_have_no_vsr_geometry():
    cells = prepared()
    report = analyze_grid(cells)
    table = exposure_run.exposure_table(cells, report, {"run_id": "synthetic"})
    exposure_run.verify_table(table, report)
    assert table["geometry"].null_count == 1
    assert table["product_intensity"].null_count == 1
    assert [f for f in table.column_names if "geometry" in f] == ["geometry"]
    row = table.to_pylist()[0]
    row["product_integrated_inside"] += 1
    with pytest.raises(ValueError, match="integration"):
        exposure_run.verify_table(
            pa.Table.from_pylist([row, *table.to_pylist()[1:]], schema=table.schema),
            report,
        )


def test_bundle_repeats_bytes_and_preserves_existing_output(tmp_path, monkeypatch):
    monkeypatch.setattr(exposure_run, "ROOT", tmp_path)
    grids = {"5km": prepared()}
    identity = {"run_id": "synthetic", "input_sha256": {}}
    one = tmp_path / "data/derived/one"
    two = tmp_path / "data/derived/two"
    exposure_run.write_bundle(
        one, grids, identity, datetime(2026, 1, 1, tzinfo=UTC), {}
    )
    exposure_run.write_bundle(
        two, grids, identity, datetime(2026, 1, 2, tzinfo=UTC), {}
    )
    for filename in ("exposure-5km.parquet", "sensitivity-report.json"):
        assert (one / filename).read_bytes() == (two / filename).read_bytes()
    assert (one / "run-metadata.json").read_bytes() != (
        two / "run-metadata.json"
    ).read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        exposure_run.write_bundle(one, grids, identity, datetime.now(UTC), {})
    with pytest.raises(ValueError, match="ignored"):
        exposure_run.validate_destination(tmp_path / "data/raw/bad", [])


def test_partial_bundle_failure_retains_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(exposure_run, "ROOT", tmp_path)

    def fail(*args, **kwargs):
        raise OSError("synthetic write failure")

    monkeypatch.setattr(pq, "write_table", fail)
    target = tmp_path / "data/derived/failure"
    with pytest.raises(ValueError, match="retained evidence"):
        exposure_run.write_bundle(
            target,
            {"5km": prepared()},
            {"run_id": "s", "input_sha256": {}},
            datetime.now(UTC),
            {},
        )
    assert not target.exists()
    assert len(list(target.parent.glob(".failure.temporary-*"))) == 1
