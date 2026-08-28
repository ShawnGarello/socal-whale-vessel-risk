from __future__ import annotations

import csv
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from pyproj import Transformer
from shapely import to_wkb
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis import vessel_activity_evidence as evidence
from whale_vessel_analysis.ais import AIS_PUBLISHED_HEADER
from whale_vessel_analysis.ais_processing import process_ais_csv
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.spatial_grid import (
    MaskInspection,
    construct_water_grid,
    write_water_grid,
)
from whale_vessel_analysis.vessel_activity_evidence import (
    CandidateSegment,
    Observation,
    VesselActivityEvidenceError,
    aggregate_segment_piece_cache,
    allocate_segments_to_grid,
    build_evidence_report,
    build_segment_piece_cache,
    construct_candidate_segments,
    load_cleaned_bundle,
    run_evidence,
    write_evidence_report,
)
from whale_vessel_analysis.whale_grid import (
    TargetGridCell,
    TargetGridInspection,
    WhaleGridInputError,
)


def _row(**updates: str) -> list[str]:
    values = {
        "MMSI": "123456789",
        "BaseDateTime": "2024-07-15T00:00:00",
        "LAT": "34.0",
        "LON": "-118.0",
        "SOG": "12.5",
        "COG": "145.0",
        "Heading": "145",
        "VesselName": "SYNTHETIC VESSEL",
        "IMO": "IMO1234567",
        "CallSign": "TEST1",
        "VesselType": "70",
        "Status": "0",
        "Length": "200",
        "Width": "30",
        "Draft": "9.5",
        "Cargo": "70",
        "TransceiverClass": "A",
    }
    values.update(updates)
    return [values[field] for field in AIS_PUBLISHED_HEADER]


def _bundle(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "synthetic.csv"
    rows = [
        _row(BaseDateTime="2024-07-15T00:02:00", LON="-117.99"),
        _row(BaseDateTime="2024-07-15T00:00:00"),
        _row(BaseDateTime="2024-07-15T00:01:00", LON="-117.99"),
        _row(BaseDateTime="2024-07-15T00:03:00", LON="-117.99", VesselType="80"),
        _row(
            MMSI="223456789",
            BaseDateTime="2024-07-15T00:00:30",
            VesselType="60",
            SOG="102.3",
            Length="",
        ),
    ]
    with source.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination, lineterminator="\n")
        writer.writerow(AIS_PUBLISHED_HEADER)
        writer.writerows(rows)
    bundle = tmp_path / "bundle"
    process_ais_csv(source, bundle, load_default_config())
    return bundle


def _gap_bundle(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "synthetic-gaps.csv"
    rows = [
        _row(BaseDateTime="2024-07-15T00:00:00", LON="-118.000"),
        _row(BaseDateTime="2024-07-15T00:00:10", LON="-117.999"),
        _row(BaseDateTime="2024-07-15T00:00:50", LON="-117.998"),
    ]
    with source.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination, lineterminator="\n")
        writer.writerow(AIS_PUBLISHED_HEADER)
        writer.writerows(rows)
    bundle = tmp_path / "bundle"
    process_ais_csv(source, bundle, load_default_config())
    return bundle


def _observation(
    mmsi: str,
    second: int,
    longitude: float,
    *,
    group: evidence.VesselGroup = "cargo",
    length_m: float | None = 200.0,
) -> Observation:
    return Observation(
        mmsi=mmsi,
        observed_at_utc=datetime(2024, 7, 15, 0, 0, second, tzinfo=UTC),
        latitude=34.0,
        longitude=longitude,
        sog_knots=10.0,
        vessel_type_code={"passenger": 60, "cargo": 70, "tanker": 80}[group],
        vessel_type_group=group,
        length_m=length_m,
    )


def _segment(
    start_xy: tuple[float, float],
    end_xy: tuple[float, float],
    *,
    group: evidence.VesselGroup = "cargo",
    sequence: int = 0,
    mmsi: str = "123456789",
    elapsed_seconds: int = 10,
) -> CandidateSegment:
    distance = math.dist(start_xy, end_xy)
    start = _observation(mmsi, 0, -118.0, group=group)
    end = _observation(mmsi, elapsed_seconds, -117.99, group=group)
    return CandidateSegment(
        sequence=sequence,
        start=start,
        end=end,
        elapsed_seconds=float(elapsed_seconds),
        projected_distance_m=distance,
        geodesic_distance_m=distance,
        implied_speed_knots=(
            distance / elapsed_seconds * evidence.KNOTS_PER_METRE_PER_SECOND
        ),
        start_xy_m=start_xy,
        end_xy_m=end_xy,
    )


def _cell(
    cell_id: str, column: int, geometry: BaseGeometry | None = None
) -> TargetGridCell:
    shape = geometry or box(column * 5, 0, (column + 1) * 5, 10)
    return TargetGridCell(
        cell_id=cell_id,
        row_index=0,
        column_index=column,
        x_min_m=column * 5,
        y_min_m=0,
        x_max_m=(column + 1) * 5,
        y_max_m=10,
        water_area_m2=float(shape.area),
        water_area_km2=float(shape.area) / 1_000_000,
        geometry=shape,
        geometry_wkb=to_wkb(shape),
    )


def _grid(*cells: TargetGridCell) -> TargetGridInspection:
    return TargetGridInspection(
        cells=tuple(cells),
        path=Path("synthetic-grid.parquet"),
        sha256="a" * 64,
        metadata={},
    )


def _configure_output_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    interim = tmp_path / "data" / "interim"
    raw = tmp_path / "data" / "raw"
    interim.mkdir(parents=True)
    raw.mkdir(parents=True)
    monkeypatch.setattr(evidence, "_PROJECT_INTERIM_ROOT", interim.resolve())
    monkeypatch.setattr(evidence, "_PROJECT_RAW_ROOT", raw.resolve())
    return interim


def test_bundle_integrity_and_observations_are_deterministically_ordered(
    tmp_path: Path,
) -> None:
    bundle_path = _bundle(tmp_path)
    before = {path.name: path.read_bytes() for path in bundle_path.iterdir()}

    bundle = load_cleaned_bundle(bundle_path)

    assert [
        (item.mmsi, item.observed_at_utc.second) for item in bundle.observations
    ] == [
        ("123456789", 0),
        ("123456789", 0),
        ("123456789", 0),
        ("123456789", 0),
        ("223456789", 30),
    ]
    assert [item.observed_at_utc.minute for item in bundle.observations[:4]] == [
        0,
        1,
        2,
        3,
    ]
    assert before == {path.name: path.read_bytes() for path in bundle_path.iterdir()}

    tampered_quality_bundle = _bundle(tmp_path / "tampered-quality")
    quality_path = tampered_quality_bundle / "quality-report.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality["scope_note"] = "tampered after cleaner publication"
    quality_path.write_text(
        json.dumps(quality, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(VesselActivityEvidenceError, match="quality report checksum"):
        load_cleaned_bundle(tampered_quality_bundle)

    mismatched_run_bundle = _bundle(tmp_path / "mismatched-run")
    metadata_path = mismatched_run_bundle / "run-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["run"]["run_id"] = "ais-tampered-run-identity"
    metadata_path.write_text(
        json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(VesselActivityEvidenceError, match="same cleaner run_id"):
        load_cleaned_bundle(mismatched_run_bundle)


def test_pairing_covers_full_zero_and_non_increasing_time_gaps() -> None:
    observations = (
        _observation("223456789", 10, -118.0),
        _observation("123456789", 10, -117.99),
        _observation("123456789", 0, -118.0),
        _observation("123456789", 10, -117.98),
    )

    segments = construct_candidate_segments(observations)

    assert [segment.elapsed_seconds for segment in segments] == [10.0, 0.0]
    assert segments[0].projected_distance_m > 0
    assert segments[1].implied_speed_knots is None
    diagnostics = evidence._grouped_segment_diagnostics(segments)
    assert (
        diagnostics["by_group"]["all_commercial"]["non_increasing_timestamp_count"] == 1
    )


def test_known_distance_comparison_implied_speed_and_axis_order() -> None:
    start = _observation("123456789", 0, -118.0)
    end = _observation("123456789", 10, -117.99)

    segment = construct_candidate_segments((end, start))[0]

    assert segment.start_xy_m == pytest.approx(
        (184_755.8686105011, -444_218.17569026817), abs=0.001
    )
    assert segment.projected_distance_m > 0
    assert segment.geodesic_distance_m > 0
    difference = segment.projected_distance_m - segment.geodesic_distance_m
    assert 0 < abs(difference) < 1
    assert segment.implied_speed_knots == pytest.approx(
        segment.projected_distance_m / 10 * evidence.KNOTS_PER_METRE_PER_SECOND
    )


def test_report_exposes_group_changes_union_distincts_and_candidate_values(
    tmp_path: Path,
) -> None:
    bundle = load_cleaned_bundle(_bundle(tmp_path))

    report = build_evidence_report(
        bundle,
        candidate_maximum_gap_seconds=[60, 120],
        candidate_implied_speed_ceiling_knots=[20],
        candidate_minimum_vessel_length_m=[150],
    )

    observations = report["observations"]
    assert isinstance(observations, dict)
    all_commercial = observations["all_commercial"]
    assert all_commercial["observation_count"] == 5
    assert all_commercial["unique_mmsi_count"] == 2
    assert all_commercial["union_recomputation"]["observation_counts_are_additive"]
    assert all_commercial["union_recomputation"]["sum_of_group_unique_mmsi_counts"] == 3
    segments = report["candidate_segments"]
    assert segments["vessel_group_changes"]["count"] == 1
    assert segments["by_group"]["cargo"]["zero_length_consecutive_segment_count"] == 2
    sensitivity = report["candidate_rule_sensitivity"]
    assert sensitivity["implicit_defaults"] is False
    assert sensitivity["supplied_values"] == {
        "maximum_gap_seconds": [60.0, 120.0],
        "implied_speed_ceiling_knots": [20.0],
        "minimum_vessel_length_m": [150.0],
    }
    assert len(sensitivity["candidate_scenarios"]) == 2
    assert (
        observations["passenger"]["reported_sog"]["unavailable_observation_count"] == 1
    )
    limitations = report["censoring_and_support_limitations"]
    assert "cannot construct cross-day pairs" in limitations["period_censoring"]
    assert "does not assign a cause" in limitations["spatial_edge_support"]


def test_no_candidate_values_means_no_implicit_behavioral_defaults(
    tmp_path: Path,
) -> None:
    report = build_evidence_report(load_cleaned_bundle(_bundle(tmp_path)))
    sensitivity = report["candidate_rule_sensitivity"]

    assert sensitivity["supplied_values"] == {
        "maximum_gap_seconds": [],
        "implied_speed_ceiling_knots": [],
        "minimum_vessel_length_m": [],
    }
    scenarios = sensitivity["candidate_scenarios"]
    assert scenarios == []
    baseline = sensitivity["structural_baseline"]
    assert baseline["segment_count"] == 2
    assert baseline["projected_distance_m"] == pytest.approx(923.84786, abs=1)


def test_gap_candidate_and_grid_allocation_use_the_same_segment_population(
    tmp_path: Path,
) -> None:
    bundle = load_cleaned_bundle(_gap_bundle(tmp_path))
    support = _cell(
        "support",
        0,
        box(180_000, -450_000, 190_000, -440_000),
    )

    report = build_evidence_report(
        bundle,
        candidate_maximum_gap_seconds=[20],
        target_grid=_grid(support),
    )

    sensitivity_scenario = report["candidate_rule_sensitivity"]["candidate_scenarios"][
        0
    ]
    allocation_report = report["optional_grid_allocation"]
    baseline = allocation_report["baseline"]
    allocation_scenario = allocation_report["candidate_scenarios"][0]
    assert sensitivity_scenario["retained_segment_count"] == 1
    assert baseline["counts"]["allocated_segment_count"] == 2
    assert allocation_scenario["scenario_id"] == sensitivity_scenario["scenario_id"]
    assert allocation_scenario["retained_segment_count"] == 1
    assert allocation_scenario["allocation"]["counts"]["allocated_segment_count"] == 1
    assert (
        allocation_scenario["allocation"]["lengths"]["parent_projected_length_km"]
        < baseline["lengths"]["parent_projected_length_km"]
    )


def test_exact_full_partial_and_multi_cell_allocation_conserves_length() -> None:
    cells = _grid(_cell("left", 0), _cell("right", 1))

    full = allocate_segments_to_grid((_segment((1, 5), (9, 5)),), cells)
    partial = allocate_segments_to_grid(
        (_segment((-2, 5), (7, 5)),), _grid(_cell("left", 0))
    )

    assert full["counts"]["positive_length_piece_count"] == 2
    assert full["lengths"]["in_support_piece_length_m"] == 8.0
    assert full["lengths"]["outside_support_length_m"] == 0.0
    assert full["conservation"]["no_double_allocation"] is True
    assert partial["lengths"]["parent_projected_length_m"] == 9.0
    assert partial["lengths"]["in_support_piece_length_m"] == 5.0
    assert partial["lengths"]["outside_support_length_m"] == 4.0


def test_one_segment_splits_exact_distance_and_elapsed_time_across_two_cells() -> None:
    grid = _grid(_cell("left", 0), _cell("right", 1))
    segment = _segment((1, 5), (9, 5), elapsed_seconds=16)

    cache = build_segment_piece_cache((segment,), grid)
    allocation = cache.allocations[0]
    report = aggregate_segment_piece_cache(
        cache, (segment,), population_label="synthetic baseline"
    )

    assert [piece.cell_id for piece in allocation.pieces] == ["left", "right"]
    assert [piece.piece_order for piece in allocation.pieces] == [0, 1]
    assert [piece.piece_distance_m for piece in allocation.pieces] == [4.0, 4.0]
    assert [piece.piece_elapsed_seconds for piece in allocation.pieces] == [8.0, 8.0]
    assert report["per_cell"][0] == {
        "cell_id": "left",
        "segment_piece_count": 1,
        "vessel_kilometres": {
            "passenger": 0.0,
            "cargo": 0.004,
            "tanker": 0.0,
            "all_commercial": 0.004,
        },
        "vessel_hours": {
            "passenger": 0.0,
            "cargo": pytest.approx(8 / 3_600),
            "tanker": 0.0,
            "all_commercial": pytest.approx(8 / 3_600),
        },
    }
    assert report["per_cell"][1]["vessel_kilometres"]["cargo"] == 0.004
    assert report["conservation"]["passed"] is True
    assert report["conservation"]["parent_elapsed_minus_allocated_seconds"] == 0.0


def test_partial_outside_support_conserves_distance_and_elapsed_time() -> None:
    grid = _grid(_cell("support", 0))
    segment = _segment((-2, 5), (7, 5), elapsed_seconds=18)

    cache = build_segment_piece_cache((segment,), grid)
    allocation = cache.allocations[0]
    report = aggregate_segment_piece_cache(
        cache, (segment,), population_label="synthetic baseline"
    )

    assert allocation.status == "positive_length_partially_outside_support"
    assert allocation.inside_support_distance_m == 5.0
    assert allocation.outside_support_distance_m == 4.0
    assert allocation.inside_support_elapsed_seconds == 10.0
    assert allocation.outside_support_elapsed_seconds == 8.0
    hours = report["vessel_hours_comparison"]
    assert hours["parent_elapsed_seconds"] == 18.0
    assert hours["in_support_elapsed_seconds"] == 10.0
    assert hours["outside_support_elapsed_seconds"] == 8.0
    assert hours["unallocated_elapsed_seconds"] == 0.0


def test_zero_length_time_is_assigned_to_one_unambiguous_support_cell() -> None:
    segment = _segment((2, 5), (2, 5), elapsed_seconds=12)

    cache = build_segment_piece_cache((segment,), _grid(_cell("support", 0)))
    allocation = cache.allocations[0]
    report = aggregate_segment_piece_cache(
        cache, (segment,), population_label="synthetic baseline"
    )

    assert allocation.status == "zero_length_in_support"
    assert len(allocation.pieces) == 1
    assert allocation.pieces[0].piece_distance_m == 0.0
    assert allocation.pieces[0].piece_elapsed_seconds == 12.0
    assert report["per_cell"][0]["segment_piece_count"] == 1
    assert report["vessel_hours_comparison"]["in_support_elapsed_seconds"] == 12.0


def test_zero_length_time_outside_support_is_retained_separately() -> None:
    segment = _segment((-2, 5), (-2, 5), elapsed_seconds=12)

    cache = build_segment_piece_cache((segment,), _grid(_cell("support", 0)))
    allocation = cache.allocations[0]
    report = aggregate_segment_piece_cache(
        cache, (segment,), population_label="synthetic baseline"
    )

    assert allocation.status == "zero_length_outside_support"
    assert allocation.pieces == ()
    assert report["vessel_hours_comparison"]["outside_support_elapsed_seconds"] == 12.0
    assert report["vessel_hours_comparison"]["unallocated_elapsed_seconds"] == 0.0


def test_zero_length_boundary_ambiguity_is_never_silently_assigned() -> None:
    segment = _segment((5, 5), (5, 5), elapsed_seconds=12)

    cache = build_segment_piece_cache(
        (segment,), _grid(_cell("left", 0), _cell("right", 1))
    )
    allocation = cache.allocations[0]
    report = aggregate_segment_piece_cache(
        cache, (segment,), population_label="synthetic baseline"
    )

    assert allocation.status == "zero_length_ambiguous"
    assert allocation.pieces == ()
    assert [cell["segment_piece_count"] for cell in report["per_cell"]] == [0, 0]
    assert report["vessel_hours_comparison"]["unallocated_elapsed_seconds"] == 12.0
    assert report["conservation"]["parent_elapsed_minus_allocated_seconds"] == 0.0


def test_per_cell_group_totals_and_all_commercial_are_additive() -> None:
    grid = _grid(_cell("support", 0), _cell("zero", 1))
    segments = (
        _segment((1, 5), (4, 5), group="passenger", sequence=0, mmsi="111111111"),
        _segment((1, 4), (3, 4), group="cargo", sequence=1, mmsi="222222222"),
        _segment((1, 3), (2, 3), group="tanker", sequence=2, mmsi="333333333"),
    )

    cache = build_segment_piece_cache(segments, grid)
    report = aggregate_segment_piece_cache(
        cache, segments, population_label="synthetic baseline"
    )
    support = report["per_cell"][0]

    assert support["segment_piece_count"] == 3
    assert support["vessel_kilometres"] == {
        "passenger": 0.003,
        "cargo": 0.002,
        "tanker": 0.001,
        "all_commercial": 0.006,
    }
    assert support["vessel_hours"]["all_commercial"] == pytest.approx(30 / 3_600)
    assert report["per_cell"][1]["vessel_kilometres"]["all_commercial"] == 0.0


def test_point_context_recomputes_union_distincts_and_retains_spatial_ambiguity() -> (
    None
):
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True)
    boundary_x, boundary_y = transformer.transform(-118.0, 34.0)
    inside_longitude = -118.0005
    inside_x, inside_y = transformer.transform(inside_longitude, 34.0)
    assert inside_x < boundary_x
    grid = _grid(
        _cell(
            "left",
            0,
            box(boundary_x - 100, boundary_y - 100, boundary_x, boundary_y + 100),
        ),
        _cell(
            "right",
            1,
            box(boundary_x, boundary_y - 100, boundary_x + 100, boundary_y + 100),
        ),
    )
    observations = (
        _observation("123456789", 0, inside_longitude, group="passenger"),
        _observation("123456789", 1, inside_longitude, group="cargo"),
        _observation("223456789", 2, inside_longitude, group="tanker"),
        _observation("323456789", 3, -117.9, group="cargo"),
        _observation("423456789", 4, -118.0, group="tanker"),
    )
    context = evidence._point_context_diagnostics(observations, grid)
    left = context["per_cell"][0]

    assert inside_y == pytest.approx(boundary_y, abs=1)
    assert left["observation_count"] == {
        "passenger": 1,
        "cargo": 1,
        "tanker": 1,
        "all_commercial": 3,
    }
    assert left["distinct_mmsi"] == {
        "passenger": 1,
        "cargo": 1,
        "tanker": 1,
        "all_commercial": 2,
    }
    assert left["distinct_mmsi_date"]["all_commercial"] == 2
    assert context["counts"]["outside_support_observation_count"]["all_commercial"] == 1
    assert context["counts"]["ambiguous_observation_count"]["all_commercial"] == 1
    assert context["counts"]["conservation_passed"] is True


def test_candidate_scenarios_reuse_baseline_pieces_without_more_intersections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = load_cleaned_bundle(_gap_bundle(tmp_path))
    grid = _grid(_cell("support", 0, box(180_000, -450_000, 190_000, -440_000)))
    original_intersection = evidence._geometry_intersection
    call_count = 0

    def counted_intersection(left: BaseGeometry, right: BaseGeometry) -> BaseGeometry:
        nonlocal call_count
        call_count += 1
        return original_intersection(left, right)

    monkeypatch.setattr(evidence, "_geometry_intersection", counted_intersection)
    baseline_report = build_evidence_report(bundle, target_grid=grid)
    baseline_calls = call_count
    call_count = 0
    scenario_report = build_evidence_report(
        bundle,
        candidate_maximum_gap_seconds=[20, 100],
        target_grid=grid,
    )

    assert call_count == baseline_calls
    reuse = scenario_report["optional_grid_allocation"][
        "reusable_segment_piece_representation"
    ]
    assert reuse["geometry_intersection_pass_count"] == 1
    assert reuse["candidate_population_count"] == 2
    baseline = baseline_report["optional_grid_allocation"]["baseline"]
    unfiltered_scenario = scenario_report["optional_grid_allocation"][
        "candidate_scenarios"
    ][1]["allocation"]
    assert unfiltered_scenario["per_cell"] == baseline["per_cell"]


def test_report_is_deterministic_for_reordered_observations_and_candidates(
    tmp_path: Path,
) -> None:
    bundle = load_cleaned_bundle(_gap_bundle(tmp_path))
    reordered = evidence.CleanedBundleInspection(
        bundle_path=bundle.bundle_path,
        cleaned_path=bundle.cleaned_path,
        cleaned_sha256=bundle.cleaned_sha256,
        cleaner_run_id=bundle.cleaner_run_id,
        temporal_coverage=bundle.temporal_coverage,
        observations=tuple(reversed(bundle.observations)),
    )
    grid = _grid(_cell("support", 0, box(180_000, -450_000, 190_000, -440_000)))

    first = build_evidence_report(
        bundle,
        candidate_maximum_gap_seconds=[100, 20],
        candidate_implied_speed_ceiling_knots=[50, 20],
        target_grid=grid,
    )
    second = build_evidence_report(
        reordered,
        candidate_maximum_gap_seconds=[20, 100],
        candidate_implied_speed_ceiling_knots=[20, 50],
        target_grid=grid,
    )

    assert first == second
    assert first["report_id"] == second["report_id"]


def test_grid_checksum_and_contract_validation_are_delegated_to_exact_validator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim = _configure_output_roots(tmp_path, monkeypatch)
    bundle = _bundle(tmp_path)
    geometry = box(0, -500_000, 5_000, -495_000)
    source = tmp_path / "mask.txt"
    source.write_text("synthetic\n", encoding="utf-8")
    mask = MaskInspection(
        geometry=geometry,
        path=source,
        layer=None,
        source_crs="EPSG:3310",
        source_sha256="b" * 64,
        feature_count=1,
        null_geometry_count=0,
        empty_geometry_count=0,
        invalid_geometry_count=0,
        non_finite_geometry_count=0,
    )
    dataset = construct_water_grid(
        geometry,
        source_crs="EPSG:3310",
        source_sha256="b" * 64,
        mask_feature_count=1,
        config=load_default_config(),
    )
    grid_path = tmp_path / "grid.parquet"
    write_water_grid(
        dataset,
        mask,
        grid_path,
        started_at=datetime(2026, 8, 27, 12, tzinfo=UTC),
    )

    with pytest.raises(WhaleGridInputError, match="checksum"):
        run_evidence(
            bundle,
            interim / "report.json",
            load_default_config(),
            grid_input=grid_path,
            expected_grid_sha256="0" * 64,
        )

    table = pq.read_table(grid_path)
    metadata = dict(table.schema.metadata or {})
    contract = json.loads(metadata[b"whale_vessel_analysis"])
    contract["analysis_crs"] = "EPSG:3857"
    metadata[b"whale_vessel_analysis"] = json.dumps(
        contract, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    invalid_crs = tmp_path / "invalid-crs.parquet"
    pq.write_table(table.replace_schema_metadata(metadata), invalid_crs)
    with pytest.raises(WhaleGridInputError, match="analysis CRS"):
        run_evidence(
            bundle,
            interim / "report.json",
            load_default_config(),
            grid_input=invalid_crs,
        )

    invalid_grid = tmp_path / "invalid-grid.parquet"
    invalid_grid.write_bytes(b"not parquet")
    with pytest.raises(WhaleGridInputError, match="could not read target grid"):
        run_evidence(
            bundle,
            interim / "report.json",
            load_default_config(),
            grid_input=invalid_grid,
        )


def test_deterministic_identity_overwrite_and_atomic_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim = _configure_output_roots(tmp_path, monkeypatch)
    report = build_evidence_report(load_cleaned_bundle(_bundle(tmp_path)))
    output = interim / "report.json"

    first_id, first_checksum = write_evidence_report(report, output)
    first_bytes = output.read_bytes()
    with pytest.raises(VesselActivityEvidenceError, match="explicit overwrite"):
        write_evidence_report(report, output)
    second_id, second_checksum = write_evidence_report(report, output, overwrite=True)

    assert output.read_bytes() == first_bytes
    assert second_id == first_id
    assert second_checksum == first_checksum

    failed_output = interim / "failed.json"

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("synthetic atomic failure")

    monkeypatch.setattr(evidence, "_replace_file", fail_replace)
    with pytest.raises(VesselActivityEvidenceError, match="synthetic atomic failure"):
        write_evidence_report(report, failed_output)
    assert not failed_output.exists()
    assert list(interim.glob(".*.tmp")) == []


def test_report_identity_excludes_local_bundle_parquet_and_grid_paths(
    tmp_path: Path,
) -> None:
    first_bundle = load_cleaned_bundle(_bundle(tmp_path / "first-location"))
    second_bundle = load_cleaned_bundle(_bundle(tmp_path / "second-location"))
    first_grid = _grid(_cell("support", 0))
    second_grid = TargetGridInspection(
        cells=first_grid.cells,
        path=tmp_path / "another-worktree" / "same-grid.parquet",
        sha256=first_grid.sha256,
        metadata=first_grid.metadata,
    )

    first = build_evidence_report(first_bundle, target_grid=first_grid)
    second = build_evidence_report(second_bundle, target_grid=second_grid)

    assert first_bundle.cleaned_sha256 == second_bundle.cleaned_sha256
    assert first_bundle.cleaner_run_id == second_bundle.cleaner_run_id
    assert first["local_provenance"] != second["local_provenance"]
    assert first["report_id"] == second["report_id"]


def test_raw_and_non_interim_output_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim = _configure_output_roots(tmp_path, monkeypatch)
    report = build_evidence_report(load_cleaned_bundle(_bundle(tmp_path)))
    raw_output = tmp_path / "data" / "raw" / "report.json"

    with pytest.raises(VesselActivityEvidenceError, match="under raw data"):
        write_evidence_report(report, raw_output)
    with pytest.raises(VesselActivityEvidenceError, match="data/interim"):
        write_evidence_report(report, tmp_path / "elsewhere.json")
    assert not raw_output.exists()
    assert interim.exists()


def test_report_runtime_is_separate_from_deterministic_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim = _configure_output_roots(tmp_path, monkeypatch)
    bundle = _bundle(tmp_path)
    times = iter(
        (
            datetime(2026, 8, 27, 12, tzinfo=UTC),
            datetime(2026, 8, 27, 12, 0, 1, tzinfo=UTC),
            datetime(2026, 8, 27, 13, tzinfo=UTC),
            datetime(2026, 8, 27, 13, 0, 2, tzinfo=UTC),
        )
    )
    monkeypatch.setattr(evidence, "_utc_now", times.__next__)
    output = interim / "report.json"

    first = run_evidence(bundle, output, load_default_config())
    first_bytes = output.read_bytes()
    second = run_evidence(bundle, output, load_default_config(), overwrite=True)

    assert output.read_bytes() == first_bytes
    assert first.report_id == second.report_id
    assert first.report_sha256 == second.report_sha256
    assert first.started_at != second.started_at
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert "execution" not in stored
