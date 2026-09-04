from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from conftest import build_cleaned_bundle
from whale_vessel_analysis import multiday_ais, period_vessel_rule_evidence
from whale_vessel_analysis.multiday_ais import (
    MultiDayAISInputError,
    load_period_manifest,
    record_cleaned_days,
)
from whale_vessel_analysis.multiday_ais_relation import (
    MultiDayRelationError,
    PeriodRelation,
    RelationResources,
    open_period_relation,
)
from whale_vessel_analysis.period_vessel_rule_evidence import (
    EVIDENCE_CONTRACT,
    EVIDENCE_FILENAME,
    EVIDENCE_LINEAGE_CONTRACT,
    RUN_METADATA_FILENAME,
    VESSEL_LENGTH_TREATMENT,
    PeriodEvidenceInputReference,
    PeriodVesselRuleEvidenceError,
    PeriodVesselRuleParameters,
    build_period_vessel_rule_evidence,
    validate_evidence_document,
    validate_evidence_output_target,
    write_period_vessel_rule_evidence,
)

FIXED_TIME = datetime(2026, 9, 4, 12, tzinfo=UTC)


def _roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    interim = tmp_path / "data" / "interim"
    raw = tmp_path / "data" / "raw"
    interim.mkdir(parents=True)
    raw.mkdir(parents=True)
    monkeypatch.setattr(multiday_ais, "_PROJECT_INTERIM_ROOT", interim.resolve())
    monkeypatch.setattr(multiday_ais, "_PROJECT_RAW_ROOT", raw.resolve())
    monkeypatch.setattr(
        period_vessel_rule_evidence, "_PROJECT_INTERIM_ROOT", interim.resolve()
    )
    monkeypatch.setattr(period_vessel_rule_evidence, "_PROJECT_RAW_ROOT", raw.resolve())
    return interim, raw


def _at(date: str, hour: int, minute: int, second: int = 0) -> datetime:
    return datetime.fromisoformat(date).replace(
        hour=hour, minute=minute, second=second, tzinfo=UTC
    )


def _parameters(*, allow_incomplete: bool = True) -> PeriodVesselRuleParameters:
    return PeriodVesselRuleParameters(
        maximum_gap_seconds=(1_800.0, 300.0),
        implied_speed_ceiling_knots=(50.0, 30.0),
        vessel_length_treatment=VESSEL_LENGTH_TREATMENT,
        allow_incomplete_non_production=allow_incomplete,
    )


def _reference(
    manifest_path: Path, manifest: dict[str, Any]
) -> PeriodEvidenceInputReference:
    return PeriodEvidenceInputReference(
        manifest_path=manifest_path,
        manifest_sha256=period_vessel_rule_evidence.sha256_file(manifest_path),
        period_input_id=cast(str, manifest["period_input_id"]),
        period_input_readiness=cast(
            dict[str, object], manifest["period_input_readiness"]
        ),
        independent_transfer_completeness=cast(
            dict[str, object], manifest["independent_transfer_completeness"]
        ),
        observational_completeness=cast(
            dict[str, object], manifest["observational_completeness"]
        ),
    )


def _build_matrix_input(tmp_path: Path, interim: Path) -> tuple[dict[str, Any], Path]:
    day_one_rows = [
        ("111111111", _at("2024-07-01", 23, 59), 34.0, -118.000, "cargo"),
        ("222222222", _at("2024-07-01", 0, 0), 34.0, -118.000, "passenger"),
        ("222222222", _at("2024-07-01", 0, 10), 34.0, -117.999, "passenger"),
        ("333333333", _at("2024-07-01", 1, 0), 34.0, -118.000, "tanker"),
        ("333333333", _at("2024-07-01", 1, 1), 34.0, -117.980, "tanker"),
        ("444444444", _at("2024-07-01", 2, 0), 34.0, -118.000, "passenger"),
        ("444444444", _at("2024-07-01", 2, 1), 34.0, -118.000, "cargo"),
        ("555555555", _at("2024-07-01", 3, 0), 34.0, -118.000, "cargo"),
        ("555555555", _at("2024-07-01", 3, 0), 34.0, -117.999, "cargo"),
        ("666666666", _at("2024-07-01", 4, 0), 34.0, -118.000, "tanker"),
        ("666666666", _at("2024-07-01", 4, 1), 34.0, -117.986, "tanker"),
    ]
    day_two_rows = [
        ("111111111", _at("2024-07-02", 0, 1), 34.0, -117.999, "cargo"),
        ("111111111", _at("2024-07-02", 0, 3), 34.0, -117.999, "cargo"),
    ]
    day_one = build_cleaned_bundle(
        tmp_path / "bundles" / "day-one",
        list(reversed(day_one_rows)),
        run_id="ais-period-evidence-day-one",
        sog_knots=(10.0, None, 10.0, -1.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0),
        length_m=(
            200.0,
            None,
            200.0,
            -5.0,
            200.0,
            200.0,
            200.0,
            200.0,
            200.0,
            200.0,
            200.0,
        ),
    )
    day_two = build_cleaned_bundle(
        tmp_path / "bundles" / "day-two",
        day_two_rows,
        run_id="ais-period-evidence-day-two",
        sog_knots=(8.0, None),
        length_m=(210.0, 210.0),
    )
    manifest_path = interim / "period.json"
    update = record_cleaned_days(
        manifest_path, [day_two, day_one], clock=lambda: FIXED_TIME
    )
    return dict(update.manifest), manifest_path


def _build_dataset(
    manifest: dict[str, Any],
    manifest_path: Path,
    interim: Path,
    *,
    batch_size: int = 2,
) -> tuple[Any, Any]:
    resources = RelationResources(
        memory_limit="256MB", temporary_directory=interim / "spill", threads=1
    )
    context = open_period_relation(manifest, resources)
    relation = context.__enter__()
    try:
        dataset = build_period_vessel_rule_evidence(
            relation,
            _reference(manifest_path, manifest),
            _parameters(),
            batch_size=batch_size,
        )
    except Exception:
        context.__exit__(*__import__("sys").exc_info())
        raise
    return dataset, (context, relation)


def test_one_ordered_stream_covers_all_rules_and_daily_accounting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _raw = _roots(tmp_path, monkeypatch)
    original_batches = PeriodRelation.adjacent_observation_batches
    stream_calls = 0

    def counted_batches(self: PeriodRelation, batch_size: int = 100_000) -> Any:
        nonlocal stream_calls
        stream_calls += 1
        return original_batches(self, batch_size)

    monkeypatch.setattr(PeriodRelation, "adjacent_observation_batches", counted_batches)
    manifest, manifest_path = _build_matrix_input(tmp_path, interim)
    dataset, handle = _build_dataset(manifest, manifest_path, interim)
    context, _relation = handle
    try:
        document = dataset.document
        commercial = document["whole_period_by_vessel_group"]["all_commercial"]
        structural = commercial["structural_segments"]
        assert commercial["cleaned_observations"] == 13
        assert structural["candidate_segments"] == 7
        assert structural["non_increasing_timestamps"] == 1
        assert structural["vessel_group_changes"] == 1
        assert structural["zero_length_movement"] == 2
        assert structural["cross_midnight"] == 1
        assert structural["projected_endpoint_distance_m"]["count"] == 7
        assert structural["wgs84_geodesic_endpoint_distance_m"]["count"] == 7
        assert structural["projected_minus_geodesic_distance_m"]["count"] == 7
        assert structural["absolute_projected_minus_geodesic_distance_m"]["count"] == 7
        assert (
            structural["signed_relative_projected_minus_geodesic_difference_fraction"][
                "count"
            ]
            == 5
        )
        assert (
            structural[
                "absolute_relative_projected_minus_geodesic_difference_fraction"
            ]["count"]
            == 5
        )
        assert structural["relative_difference_undefined_geodesic_zero"] == 2
        assert structural["projected_endpoint_distance_m"]["sum"] - structural[
            "wgs84_geodesic_endpoint_distance_m"
        ]["sum"] == pytest.approx(
            structural["projected_minus_geodesic_distance_m"]["sum"], abs=1e-6
        )
        assert structural["projected_minus_geodesic_distance_m"]["sum"] != 0
        assert structural["absolute_projected_minus_geodesic_distance_m"]["sum"] > 0
        assert structural["implied_speed_knots"]["count"] == 6
        assert commercial["observation_quality"]["reported_sog"] == {
            **commercial["observation_quality"]["reported_sog"],
            "available": 10,
            "unavailable_null": 2,
            "invalid_retained_value": 1,
        }
        length = commercial["observation_quality"]["vessel_length"]
        assert (
            length["valid"],
            length["missing_or_upstream_invalid_null"],
            length["invalid_retained_value"],
        ) == (11, 1, 1)

        matrix = {
            (item["maximum_gap_seconds"], item["implied_speed_ceiling_knots"]): item
            for item in commercial["candidate_matrix"]
        }
        assert set(matrix) == {
            (300.0, 30.0),
            (300.0, 50.0),
            (1800.0, 30.0),
            (1800.0, 50.0),
        }
        assert [matrix[key]["retained_segments"] for key in sorted(matrix)] == [
            2,
            3,
            3,
            4,
        ]
        assert matrix[(300.0, 30.0)]["primary_exclusions"] == {
            "invalid_coordinate_transform": 0,
            "non_increasing_time": 1,
            "vessel_group_change": 1,
            "maximum_gap": 1,
            "implied_speed": 2,
        }

        july_one = document["daily_by_utc_date"][0]["by_vessel_group"]["all_commercial"]
        july_two = document["daily_by_utc_date"][1]["by_vessel_group"]["all_commercial"]
        assert july_one["structural_segments"]["cross_midnight"] == 1
        assert july_two["structural_segments"]["cross_midnight"] == 0
        assert (
            document["ordering_and_accounting"]["daily_segment_accounting"]
            == "starting-observation-utc-date"
        )
        assert dataset.execution_stats.arrow_record_batches > 1
        assert dataset.execution_stats.maximum_arrow_batch_rows <= 2
        assert dataset.execution_stats.streamed_observations == 13
        assert stream_calls == 1
    finally:
        context.__exit__(None, None, None)


def test_zero_geodesic_distance_is_explicit_and_fixed_bins_are_validated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _raw = _roots(tmp_path, monkeypatch)
    rows = [
        ("123456789", _at("2024-07-01", 0, 0), 34.0, -118.0, "cargo"),
        ("123456789", _at("2024-07-01", 0, 1), 34.0, -118.0, "cargo"),
        ("987654321", _at("2024-07-01", 1, 0), 34.0, -118.0, "tanker"),
        ("987654321", _at("2024-07-01", 1, 1), 34.0, -117.999, "tanker"),
    ]
    bundle = build_cleaned_bundle(tmp_path / "zero-geodesic", rows)
    manifest_path = interim / "zero-geodesic-period.json"
    manifest = dict(
        record_cleaned_days(manifest_path, [bundle], clock=lambda: FIXED_TIME).manifest
    )
    dataset, handle = _build_dataset(manifest, manifest_path, interim, batch_size=1)
    context, _relation = handle
    try:
        edges = dataset.document["distribution_contract"]["edges"]
        assert edges["absolute_projected_minus_geodesic_distance_m"] == [
            0.0,
            0.001,
            0.01,
            0.1,
            1.0,
            10.0,
            100.0,
            1_000.0,
        ]
        assert edges[
            "signed_relative_projected_minus_geodesic_difference_fraction"
        ] == [
            -0.1,
            -0.01,
            -0.001,
            -0.0001,
            -0.00001,
            0.0,
            0.00001,
            0.0001,
            0.001,
            0.01,
            0.1,
        ]
        assert edges[
            "absolute_relative_projected_minus_geodesic_difference_fraction"
        ] == [0.0, 0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.1, 1.0]
        structural = dataset.document["whole_period_by_vessel_group"]["all_commercial"][
            "structural_segments"
        ]
        projected = structural["projected_endpoint_distance_m"]["sum"]
        geodesic = structural["wgs84_geodesic_endpoint_distance_m"]["sum"]
        difference = projected - geodesic
        relative = difference / geodesic
        assert structural["projected_minus_geodesic_distance_m"]["count"] == 2
        assert structural["projected_minus_geodesic_distance_m"][
            "sum"
        ] == pytest.approx(difference, abs=1e-9)
        assert structural["absolute_projected_minus_geodesic_distance_m"][
            "sum"
        ] == pytest.approx(abs(difference), abs=1e-9)
        assert (
            structural["signed_relative_projected_minus_geodesic_difference_fraction"][
                "count"
            ]
            == 1
        )
        assert structural[
            "signed_relative_projected_minus_geodesic_difference_fraction"
        ]["sum"] == pytest.approx(relative, abs=1e-12)
        assert (
            structural[
                "absolute_relative_projected_minus_geodesic_difference_fraction"
            ]["count"]
            == 1
        )
        assert structural[
            "absolute_relative_projected_minus_geodesic_difference_fraction"
        ]["sum"] == pytest.approx(abs(relative), abs=1e-12)
        assert structural["relative_difference_undefined_geodesic_zero"] == 1

        tampered = json.loads(json.dumps(dataset.document))
        bins = tampered["whole_period_by_vessel_group"]["all_commercial"][
            "structural_segments"
        ]["absolute_projected_minus_geodesic_distance_m"]["bin_counts"]
        bins[0] += 1
        identity = dict(tampered)
        del identity["evidence_id"]
        tampered["evidence_id"] = (
            period_vessel_rule_evidence.EVIDENCE_ID_PREFIX
            + period_vessel_rule_evidence.hashlib.sha256(
                period_vessel_rule_evidence.canonical_json(identity).encode("utf-8")
            ).hexdigest()[:24]
        )
        with pytest.raises(PeriodVesselRuleEvidenceError, match="fixed-bin counts"):
            validate_evidence_document(tampered)
    finally:
        context.__exit__(None, None, None)


def test_group_and_commercial_union_counts_reconcile_without_summing_distincts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _raw = _roots(tmp_path, monkeypatch)
    manifest, manifest_path = _build_matrix_input(tmp_path, interim)
    dataset, handle = _build_dataset(manifest, manifest_path, interim, batch_size=20)
    context, _relation = handle
    try:
        groups = dataset.document["whole_period_by_vessel_group"]
        commercial = groups["all_commercial"]
        assert commercial["cleaned_observations"] == sum(
            groups[group]["cleaned_observations"]
            for group in ("passenger", "cargo", "tanker")
        )
        assert commercial["distinct_mmsi"] == 6
        assert (
            sum(
                groups[group]["distinct_mmsi"]
                for group in ("passenger", "cargo", "tanker")
            )
            == 7
        )
        assert commercial["distinct_mmsi_date_combinations"] < sum(
            groups[group]["distinct_mmsi_date_combinations"]
            for group in ("passenger", "cargo", "tanker")
        )
        for day in dataset.document["daily_by_utc_date"]:
            by_group = day["by_vessel_group"]
            assert by_group["all_commercial"]["cleaned_observations"] == sum(
                by_group[group]["cleaned_observations"]
                for group in ("passenger", "cargo", "tanker")
            )
    finally:
        context.__exit__(None, None, None)


def test_reordered_equivalent_manifest_produces_identical_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _raw = _roots(tmp_path, monkeypatch)
    manifest, manifest_path = _build_matrix_input(tmp_path, interim)
    reordered = dict(manifest)
    reordered["dates"] = list(reversed(cast(list[object], manifest["dates"])))

    first, first_handle = _build_dataset(manifest, manifest_path, interim, batch_size=2)
    first_context, _first_relation = first_handle
    try:
        first_document = first.document
    finally:
        first_context.__exit__(None, None, None)

    second, second_handle = _build_dataset(
        reordered, manifest_path, interim, batch_size=5
    )
    second_context, _second_relation = second_handle
    try:
        assert second.document == first_document
        assert second.evidence_id == first.evidence_id
    finally:
        second_context.__exit__(None, None, None)


def test_identity_is_independent_of_batching_paths_and_execution_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _raw = _roots(tmp_path, monkeypatch)
    rows = [
        ("123456789", _at("2024-07-01", 0, 0), 34.0, -118.0, "cargo"),
        ("123456789", _at("2024-07-01", 0, 1), 34.0, -117.999, "cargo"),
    ]
    bundle_a = build_cleaned_bundle(
        tmp_path / "place-a" / "bundle",
        rows,
        run_id="ais-equivalent-period-evidence",
        started_at="2026-09-01T00:00:00Z",
    )
    bundle_b = build_cleaned_bundle(
        tmp_path / "place-b" / "bundle",
        rows,
        run_id="ais-equivalent-period-evidence",
        started_at="2026-09-02T00:00:00Z",
    )
    manifest_a_path = interim / "manifest-a.json"
    manifest_b_path = interim / "manifest-b.json"
    manifest_a = dict(
        record_cleaned_days(
            manifest_a_path, [bundle_a], clock=lambda: FIXED_TIME
        ).manifest
    )
    manifest_b = dict(
        record_cleaned_days(
            manifest_b_path, [bundle_b], clock=lambda: datetime(2026, 9, 5, tzinfo=UTC)
        ).manifest
    )

    dataset_a, handle_a = _build_dataset(
        manifest_a, manifest_a_path, interim, batch_size=1
    )
    context_a, relation_a = handle_a
    try:
        first = write_period_vessel_rule_evidence(
            dataset_a,
            interim / "output-a",
            relation=relation_a,
            started_at=FIXED_TIME,
        )
    finally:
        context_a.__exit__(None, None, None)

    dataset_b, handle_b = _build_dataset(
        manifest_b, manifest_b_path, interim, batch_size=10
    )
    context_b, relation_b = handle_b
    try:
        second = write_period_vessel_rule_evidence(
            dataset_b,
            interim / "output-b",
            relation=relation_b,
            started_at=datetime(2026, 9, 4, 13, tzinfo=UTC),
        )
    finally:
        context_b.__exit__(None, None, None)

    assert dataset_a.evidence_id == dataset_b.evidence_id
    assert first.evidence_path.read_bytes() == second.evidence_path.read_bytes()
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.lineage_path.read_bytes() != second.lineage_path.read_bytes()
    evidence_text = first.evidence_path.read_text(encoding="utf-8")
    assert str(tmp_path) not in evidence_text
    assert "2026-09-04T12:00:00Z" not in evidence_text
    lineage = json.loads(first.lineage_path.read_text(encoding="utf-8"))
    assert lineage["contract"] == EVIDENCE_LINEAGE_CONTRACT
    manifest_input = next(
        item
        for item in lineage["run"]["inputs"]
        if item["artifact_id"] == "multi-day-cleaned-ais-manifest"
    )
    assert manifest_input["locator"] == str(manifest_a_path)
    assert lineage["execution"]["arrow_batch_size_rows"] == 1


def test_parameters_and_ready_period_are_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _raw = _roots(tmp_path, monkeypatch)
    with pytest.raises(PeriodVesselRuleEvidenceError, match="explicitly contain"):
        PeriodVesselRuleParameters(
            maximum_gap_seconds=(300.0,),
            implied_speed_ceiling_knots=(30.0, 50.0),
            vessel_length_treatment=VESSEL_LENGTH_TREATMENT,
        )
    with pytest.raises(PeriodVesselRuleEvidenceError, match="finite and positive"):
        PeriodVesselRuleParameters(
            maximum_gap_seconds=(300.0, math.nan),
            implied_speed_ceiling_knots=(30.0, 50.0),
            vessel_length_treatment=VESSEL_LENGTH_TREATMENT,
        )
    manifest, manifest_path = _build_matrix_input(tmp_path, interim)
    resources = RelationResources("256MB", interim / "spill", 1)
    with (
        open_period_relation(manifest, resources) as relation,
        pytest.raises(PeriodVesselRuleEvidenceError, match="requires a ready"),
    ):
        build_period_vessel_rule_evidence(
            relation,
            _reference(manifest_path, manifest),
            _parameters(allow_incomplete=False),
            batch_size=2,
        )
    with (
        pytest.raises(MultiDayRelationError, match="not ready"),
        open_period_relation(manifest, resources, require_ready=True),
    ):
        pass


def test_invalid_coordinate_values_remain_explicit_candidate_exclusions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _raw = _roots(tmp_path, monkeypatch)
    rows = [
        ("123456789", _at("2024-07-01", 0, 0), 34.0, -118.0, "cargo"),
        ("123456789", _at("2024-07-01", 0, 1), math.nan, -117.9, "cargo"),
    ]
    bundle = build_cleaned_bundle(tmp_path / "bundle-invalid", rows)
    manifest_path = interim / "invalid-period.json"
    manifest = dict(
        record_cleaned_days(manifest_path, [bundle], clock=lambda: FIXED_TIME).manifest
    )
    dataset, handle = _build_dataset(manifest, manifest_path, interim)
    context, _relation = handle
    try:
        commercial = dataset.document["whole_period_by_vessel_group"]["all_commercial"]
        assert commercial["observation_quality"]["invalid_coordinate_values"] == 1
        assert commercial["structural_segments"]["invalid_coordinate_transform"] == 1
        for candidate in commercial["candidate_matrix"]:
            assert candidate["retained_segments"] == 0
            assert candidate["primary_exclusions"]["invalid_coordinate_transform"] == 1
    finally:
        context.__exit__(None, None, None)


def test_checksum_contract_and_identity_rejections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _raw = _roots(tmp_path, monkeypatch)
    manifest, manifest_path = _build_matrix_input(tmp_path, interim)
    invalid_document = {
        "contract": EVIDENCE_CONTRACT,
        "schema_version": 1,
        "processing_version": "0",
        "evidence_id": "bad",
    }
    with pytest.raises(PeriodVesselRuleEvidenceError, match="processing version"):
        validate_evidence_document(invalid_document)

    bundle_path = Path(manifest["dates"][0]["local_provenance"]["cleaned_parquet_path"])
    bundle_path.write_bytes(bundle_path.read_bytes() + b"tamper")
    with (
        pytest.raises(MultiDayRelationError, match="recorded checksum"),
        open_period_relation(
            manifest, RelationResources("256MB", interim / "spill", 1)
        ),
    ):
        pass

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["contract"] = "unsupported"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(MultiDayAISInputError, match="contract"):
        load_period_manifest(manifest_path)


def test_period_manifest_missing_and_duplicate_dates_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _raw = _roots(tmp_path, monkeypatch)
    manifest, _manifest_path = _build_matrix_input(tmp_path, interim)

    missing = dict(manifest)
    missing["dates"] = cast(list[object], manifest["dates"])[:-1]
    missing_path = interim / "missing-date.json"
    missing_path.write_text(json.dumps(missing), encoding="utf-8")
    with pytest.raises(MultiDayAISInputError, match="exactly the accepted"):
        load_period_manifest(missing_path)

    duplicate = dict(manifest)
    duplicate_dates = list(cast(list[object], manifest["dates"]))
    duplicate_dates[-1] = duplicate_dates[0]
    duplicate["dates"] = duplicate_dates
    duplicate_path = interim / "duplicate-date.json"
    duplicate_path.write_text(json.dumps(duplicate), encoding="utf-8")
    with pytest.raises(MultiDayAISInputError, match="duplicate current"):
        load_period_manifest(duplicate_path)


def test_output_guards_overwrite_and_atomic_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, raw = _roots(tmp_path, monkeypatch)
    manifest, manifest_path = _build_matrix_input(tmp_path, interim)
    dataset, handle = _build_dataset(manifest, manifest_path, interim)
    context, relation = handle
    try:
        output = interim / "evidence-output"
        first = write_period_vessel_rule_evidence(
            dataset, output, relation=relation, started_at=FIXED_TIME
        )
        assert first.evidence_path.name == EVIDENCE_FILENAME
        assert first.lineage_path.name == RUN_METADATA_FILENAME
        with pytest.raises(PeriodVesselRuleEvidenceError, match="explicit overwrite"):
            write_period_vessel_rule_evidence(
                dataset, output, relation=relation, started_at=FIXED_TIME
            )
        repeated = write_period_vessel_rule_evidence(
            dataset,
            output,
            relation=relation,
            started_at=FIXED_TIME,
            overwrite=True,
        )
        assert repeated.evidence_sha256 == first.evidence_sha256

        arbitrary = interim / "arbitrary"
        arbitrary.mkdir()
        (arbitrary / "notes.txt").write_text("not evidence", encoding="utf-8")
        with pytest.raises(PeriodVesselRuleEvidenceError, match="complete period"):
            validate_evidence_output_target(arbitrary, (), overwrite=True)
        with pytest.raises(PeriodVesselRuleEvidenceError, match="under raw"):
            validate_evidence_output_target(raw / "output", ())
        with pytest.raises(PeriodVesselRuleEvidenceError, match="must be separate"):
            validate_evidence_output_target(
                interim / "contains-input",
                [interim / "contains-input" / "manifest.json"],
            )

        def fail_publish(_temporary: Path, _target: Path, _overwrite: bool) -> None:
            raise OSError("synthetic atomic publication failure")

        monkeypatch.setattr(
            period_vessel_rule_evidence, "_publish_bundle", fail_publish
        )
        failed = interim / "failed"
        with pytest.raises(PeriodVesselRuleEvidenceError, match="synthetic atomic"):
            write_period_vessel_rule_evidence(
                dataset, failed, relation=relation, started_at=FIXED_TIME
            )
        assert not failed.exists()
        assert list(interim.glob(".failed.temporary-*")) == []
    finally:
        context.__exit__(None, None, None)
