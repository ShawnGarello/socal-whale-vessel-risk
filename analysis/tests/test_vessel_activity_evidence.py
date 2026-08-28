from __future__ import annotations

import csv
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest
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
    allocate_segments_to_grid,
    build_evidence_report,
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
) -> CandidateSegment:
    distance = math.dist(start_xy, end_xy)
    start = _observation("123456789", 0, -118.0, group=group)
    end = _observation("123456789", 10, -117.99, group=group)
    return CandidateSegment(
        sequence=0,
        start=start,
        end=end,
        elapsed_seconds=10.0,
        projected_distance_m=distance,
        geodesic_distance_m=distance,
        implied_speed_knots=distance / 10 * evidence.KNOTS_PER_METRE_PER_SECOND,
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


def test_bundle_is_read_only_and_observations_are_deterministically_ordered(
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
    assert len(scenarios) == 1
    assert scenarios[0]["candidate_maximum_gap_seconds"] is None
    assert scenarios[0]["candidate_implied_speed_ceiling_knots"] is None
    assert scenarios[0]["candidate_minimum_vessel_length_m"] is None
    assert scenarios[0]["retained_segment_count"] == 2
    assert scenarios[0]["retained_projected_distance_m"] == pytest.approx(
        923.84786, abs=1
    )
    assert scenarios[0]["primary_exclusion_counts"] == {
        "gap": 0,
        "implied_speed": 0,
        "length": 0,
    }
    assert scenarios[0]["by_group"]["cargo"]["retained_segment_count"] == 2


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
