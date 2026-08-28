from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from conftest import build_cleaned_bundle, synthetic_rows
from whale_vessel_analysis import multiday_ais
from whale_vessel_analysis.ais import AIS_PUBLISHED_HEADER
from whale_vessel_analysis.ais_processing import (
    CLEANED_FILENAME,
    QUALITY_REPORT_FILENAME,
    process_ais_csv,
)
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.multiday_ais import (
    MULTIDAY_INPUT_CONTRACT,
    MultiDayAISInputError,
    accepted_utc_dates,
    compute_period_input_id,
    inspect_cleaned_day,
    load_period_manifest,
    period_status,
    record_cleaned_days,
)

FIXED_CLOCK = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def _clock() -> datetime:
    return FIXED_CLOCK


def _roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    interim = tmp_path / "data" / "interim"
    raw = tmp_path / "data" / "raw"
    interim.mkdir(parents=True)
    raw.mkdir(parents=True)
    monkeypatch.setattr(multiday_ais, "_PROJECT_INTERIM_ROOT", interim.resolve())
    monkeypatch.setattr(multiday_ais, "_PROJECT_RAW_ROOT", raw.resolve())
    return interim, raw


def _entry(manifest: dict[str, Any], utc_date: str) -> dict[str, Any]:
    dates: list[dict[str, Any]] = manifest["dates"]
    return next(entry for entry in dates if entry["utc_date"] == utc_date)


def test_accepted_period_has_all_153_expected_dates() -> None:
    dates = accepted_utc_dates()
    assert len(dates) == 153
    assert dates[0] == "2024-07-01"
    assert dates[-1] == "2024-11-30"
    assert len(set(dates)) == 153


def test_one_valid_date_leaves_152_missing_and_never_implies_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "period" / "manifest.json"
    update = record_cleaned_days(
        manifest_path, [day_bundle("2024-07-15")], clock=_clock
    )
    manifest = update.manifest
    readiness: dict[str, Any] = manifest["period_input_readiness"]

    assert manifest["contract"] == MULTIDAY_INPUT_CONTRACT
    assert len(manifest["expected_utc_dates"]) == 153
    assert len(manifest["dates"]) == 153
    assert readiness["status"] == "not_ready"
    assert readiness["compatible_date_count"] == 1
    assert readiness["missing_date_count"] == 152
    assert len(readiness["missing_expected_utc_dates"]) == 152
    assert "2024-07-15" not in readiness["missing_expected_utc_dates"]
    assert manifest["observational_completeness"]["status"] == "unverified"
    assert update.ready is False

    entry = _entry(dict(manifest), "2024-07-15")
    assert entry["status"] == "compatible"
    assert entry["observational_completeness"]["status"] == "unverified"
    assert entry["retrieval_manifest_state"]["status"] == "not_supplied"
    assert (
        entry["independent_retention_state"]["independent_byte_completeness"]
        == "unverified"
    )
    assert manifest_path.is_file()


def test_all_153_dates_become_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    bundles = [
        build_cleaned_bundle(
            tmp_path / "bundles" / utc_date,
            synthetic_rows(utc_date),
            run_id=f"ais-{index:024d}",
        )
        for index, utc_date in enumerate(accepted_utc_dates())
    ]
    manifest_path = interim / "manifest.json"
    update = record_cleaned_days(manifest_path, bundles, clock=_clock)
    readiness: dict[str, Any] = update.manifest["period_input_readiness"]

    assert readiness["status"] == "ready"
    assert readiness["compatible_date_count"] == 153
    assert readiness["missing_expected_utc_dates"] == []
    assert update.ready is True
    assert update.manifest["observational_completeness"]["status"] == "unverified"
    assert (
        update.manifest["independent_transfer_completeness"]["status"] == "unverified"
    )
    reloaded = load_period_manifest(manifest_path)
    assert reloaded["period_input_id"] == update.period_input_id


def test_missing_date_is_explicit_before_any_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _roots(tmp_path, monkeypatch)
    manifest = multiday_ais.empty_period_manifest()
    readiness: dict[str, Any] = manifest["period_input_readiness"]
    assert readiness["status"] == "not_ready"
    assert readiness["missing_date_count"] == 153
    assert all(entry["status"] == "missing" for entry in manifest["dates"])


def test_duplicate_identical_bundle_is_a_reusable_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"
    bundle = day_bundle("2024-08-01")
    first = record_cleaned_days(manifest_path, [bundle], clock=_clock)
    second = record_cleaned_days(manifest_path, [bundle], clock=_clock)

    assert first.outcomes[0].outcome == "recorded"
    assert second.outcomes[0].outcome == "identical_retry"
    entry = _entry(dict(second.manifest), "2024-08-01")
    assert entry["status"] == "compatible"
    assert len(entry["attempt_history"]) == 2
    assert first.period_input_id == second.period_input_id


def test_conflicting_bytes_are_recorded_without_silent_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"
    original = build_cleaned_bundle(
        tmp_path / "a", synthetic_rows("2024-09-10", seconds=(0,))
    )
    different = build_cleaned_bundle(
        tmp_path / "b",
        synthetic_rows("2024-09-10", seconds=(0, 60)),
        run_id="ais-different0000000000000",
    )
    first = record_cleaned_days(manifest_path, [original], clock=_clock)
    recorded_identity = _entry(dict(first.manifest), "2024-09-10")[
        "cleaner_bundle_compatibility"
    ]

    second = record_cleaned_days(manifest_path, [different], clock=_clock)
    entry = _entry(dict(second.manifest), "2024-09-10")

    assert second.outcomes[0].outcome == "conflict"
    assert entry["status"] == "conflict"
    assert entry["cleaner_bundle_compatibility"] == recorded_identity
    assert len(entry["attempt_history"]) == 2
    readiness: dict[str, Any] = second.manifest["period_input_readiness"]
    assert readiness["conflicting_utc_dates"] == ["2024-09-10"]
    assert "2024-09-10" in readiness["missing_expected_utc_dates"]

    third = record_cleaned_days(manifest_path, [original], clock=_clock)
    third_entry = _entry(dict(third.manifest), "2024-09-10")
    assert third.outcomes[0].outcome == "conflict_pending_review"
    assert third_entry["status"] == "conflict"
    assert len(third_entry["attempt_history"]) == 3


def test_out_of_period_date_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    with pytest.raises(MultiDayAISInputError, match="outside the accepted"):
        record_cleaned_days(
            interim / "manifest.json", [day_bundle("2024-06-30")], clock=_clock
        )
    assert not (interim / "manifest.json").exists()


def test_multiple_utc_dates_in_one_bundle_are_refused(tmp_path: Path) -> None:
    rows = synthetic_rows("2024-07-01") + synthetic_rows("2024-07-02")
    bundle = build_cleaned_bundle(
        tmp_path / "mixed", rows, observed_utc_date="2024-07-01"
    )
    with pytest.raises(MultiDayAISInputError, match="exactly one UTC date"):
        inspect_cleaned_day(bundle)


def test_incomplete_bundle_layout_is_refused(
    tmp_path: Path, day_bundle: Callable[..., Path]
) -> None:
    bundle = day_bundle("2024-07-02")
    (bundle / QUALITY_REPORT_FILENAME).unlink()
    with pytest.raises(MultiDayAISInputError, match="must contain exactly"):
        inspect_cleaned_day(bundle)


def test_tampered_cleaned_parquet_is_refused(
    tmp_path: Path, day_bundle: Callable[..., Path]
) -> None:
    bundle = day_bundle("2024-07-03")
    cleaned = bundle / CLEANED_FILENAME
    cleaned.write_bytes(cleaned.read_bytes() + b"\x00")
    with pytest.raises(
        MultiDayAISInputError, match="does not match the quality report"
    ):
        inspect_cleaned_day(bundle)


def test_tampered_quality_report_sidecar_is_refused(
    tmp_path: Path, day_bundle: Callable[..., Path]
) -> None:
    bundle = day_bundle("2024-07-04")
    quality_path = bundle / QUALITY_REPORT_FILENAME
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    payload["status"] = "tampered"
    quality_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(
        MultiDayAISInputError, match="quality report checksum does not match"
    ):
        inspect_cleaned_day(bundle)


def test_mismatched_quality_and_run_metadata_identities_are_refused(
    tmp_path: Path,
) -> None:
    bundle = build_cleaned_bundle(
        tmp_path / "mismatched",
        synthetic_rows("2024-07-05"),
        run_id="ais-quality00000000000000",
        metadata_run_id="ais-metadata0000000000000",
    )
    with pytest.raises(MultiDayAISInputError, match="same cleaner run_id"):
        inspect_cleaned_day(bundle)


def test_unsupported_cleaner_processing_version_is_refused(tmp_path: Path) -> None:
    bundle = build_cleaned_bundle(
        tmp_path / "old-version",
        synthetic_rows("2024-07-06"),
        cleaning_step_version="1.0.0",
    )
    with pytest.raises(MultiDayAISInputError, match="processing version must be"):
        inspect_cleaned_day(bundle)


def test_upgraded_completeness_claim_is_refused(tmp_path: Path) -> None:
    bundle = build_cleaned_bundle(
        tmp_path / "upgraded",
        synthetic_rows("2024-07-07"),
        completeness_status="verified",
    )
    with pytest.raises(MultiDayAISInputError, match="must remain unverified"):
        inspect_cleaned_day(bundle)


def test_row_count_disagreement_is_refused(tmp_path: Path) -> None:
    bundle = build_cleaned_bundle(
        tmp_path / "rows", synthetic_rows("2024-07-08"), reported_rows=99
    )
    with pytest.raises(MultiDayAISInputError, match="row count does not match"):
        inspect_cleaned_day(bundle)


def test_identical_bytes_at_different_paths_keep_one_period_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    first_bundle = day_bundle("2024-10-05")
    second_bundle = tmp_path / "relocated" / "2024-10-05"
    second_bundle.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(first_bundle, second_bundle)

    first = record_cleaned_days(
        interim / "one" / "manifest.json", [first_bundle], clock=_clock
    )
    second = record_cleaned_days(
        interim / "two" / "manifest.json", [second_bundle], clock=_clock
    )

    assert first.period_input_id == second.period_input_id
    assert first.manifest["local_provenance"] != second.manifest["local_provenance"]
    first_entry = _entry(dict(first.manifest), "2024-10-05")
    second_entry = _entry(dict(second.manifest), "2024-10-05")
    assert first_entry["local_provenance"] != second_entry["local_provenance"]
    material = multiday_ais.period_input_identity_material(first.manifest)
    assert "path" not in json.dumps(material)


def test_period_identity_is_independent_of_supplied_bundle_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    first = build_cleaned_bundle(tmp_path / "d1", synthetic_rows("2024-07-01"))
    second = build_cleaned_bundle(tmp_path / "d2", synthetic_rows("2024-07-02"))
    forward = record_cleaned_days(
        interim / "forward.json", [first, second], clock=_clock
    )
    reverse = record_cleaned_days(
        interim / "reverse.json", [second, first], clock=_clock
    )
    assert forward.period_input_id == reverse.period_input_id
    assert [entry["utc_date"] for entry in forward.manifest["dates"]] == list(
        accepted_utc_dates()
    )


def test_retrieval_manifest_state_stays_separate_from_bundle_compatibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    from whale_vessel_analysis import ais_retrieval

    retrieval_path = interim / "retrieval.json"
    retrieval = ais_retrieval._empty_manifest()
    retrieval["entries"] = [
        {
            "utc_date": "2024-07-20",
            "status": "retrieved",
            "status_reason": "identity verified",
            "source_availability": {"status": "available", "evidence": "local"},
            "retrieval_verification": {
                "status": "identity_verified",
                "identity": {"byte_size": 10, "sha256": "b" * 64},
                "byte_completeness": {
                    "status": "unverified",
                    "evidence": "no independent source byte count",
                },
                "archive": {"container_detected_by_content": "csv"},
            },
            "date_verification": {"status": "verified"},
            "attempt_history": [{"attempt_number": 1}],
        }
    ]
    ais_retrieval._refresh_manifest_summary(retrieval)
    retrieval_path.write_text(json.dumps(retrieval), encoding="utf-8")

    update = record_cleaned_days(
        interim / "manifest.json",
        [day_bundle("2024-07-20")],
        retrieval_manifest_path=retrieval_path,
        clock=_clock,
    )
    entry = _entry(dict(update.manifest), "2024-07-20")
    assert entry["status"] == "compatible"
    assert entry["retrieval_manifest_state"]["entry_status"] == "retrieved"
    assert entry["independent_retention_state"]["retained_byte_identity"] == "verified"
    assert (
        entry["independent_retention_state"]["independent_byte_completeness"]
        == "unverified"
    )
    other = _entry(dict(update.manifest), "2024-07-21")
    assert other["retrieval_manifest_state"]["status"] == "absent"
    reference: dict[str, Any] = update.manifest["retrieval_manifest_reference"]
    assert reference["status"] == "supplied"
    assert reference["verified_retrieval_date_count"] == 0
    assert (
        update.manifest["independent_transfer_completeness"]["status"] == "unverified"
    )


def test_raw_and_non_interim_destinations_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, raw = _roots(tmp_path, monkeypatch)
    bundle = day_bundle("2024-07-09")
    with pytest.raises(MultiDayAISInputError, match="under raw data"):
        record_cleaned_days(raw / "manifest.json", [bundle], clock=_clock)
    with pytest.raises(MultiDayAISInputError, match="data/interim"):
        record_cleaned_days(tmp_path / "elsewhere.json", [bundle], clock=_clock)
    with pytest.raises(MultiDayAISInputError, match=r"must end in \.json"):
        record_cleaned_days(interim / "manifest.txt", [bundle], clock=_clock)


def test_arbitrary_existing_file_is_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    unrelated = interim / "manifest.json"
    unrelated.write_text('{"contract": "something-else"}', encoding="utf-8")
    with pytest.raises(MultiDayAISInputError, match="refusing to overwrite"):
        record_cleaned_days(unrelated, [day_bundle("2024-07-10")], clock=_clock)
    assert json.loads(unrelated.read_text(encoding="utf-8")) == {
        "contract": "something-else"
    }


def test_failed_publication_leaves_no_temporary_file_and_no_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"

    def explode(source: Path, destination: Path) -> None:
        raise OSError("synthetic atomic failure")

    monkeypatch.setattr(multiday_ais, "_replace_file", explode)
    with pytest.raises(MultiDayAISInputError, match="synthetic atomic failure"):
        record_cleaned_days(manifest_path, [day_bundle("2024-07-11")], clock=_clock)
    assert not manifest_path.exists()
    assert list(interim.glob(".*temporary-*")) == []


def test_failed_publication_preserves_the_previous_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"
    record_cleaned_days(manifest_path, [day_bundle("2024-07-12")], clock=_clock)
    before = manifest_path.read_bytes()

    def explode(source: Path, destination: Path) -> None:
        raise OSError("synthetic atomic failure")

    monkeypatch.setattr(multiday_ais, "_replace_file", explode)
    with pytest.raises(MultiDayAISInputError):
        record_cleaned_days(manifest_path, [day_bundle("2024-07-13")], clock=_clock)
    assert manifest_path.read_bytes() == before
    assert list(interim.glob(".*temporary-*")) == []


def test_tampered_manifest_identity_is_detected_on_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"
    record_cleaned_days(manifest_path, [day_bundle("2024-07-14")], clock=_clock)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(item for item in payload["dates"] if item["utc_date"] == "2024-07-14")
    entry["cleaner_bundle_compatibility"]["cleaned_parquet_sha256"] = "c" * 64
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(MultiDayAISInputError, match="period_input_id"):
        load_period_manifest(manifest_path)


def test_manifest_readiness_tampering_is_detected_on_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"
    record_cleaned_days(manifest_path, [day_bundle("2024-07-16")], clock=_clock)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["period_input_readiness"]["status"] = "ready"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(MultiDayAISInputError, match="period_input_readiness"):
        load_period_manifest(manifest_path)


def test_period_status_reports_the_unfinished_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day_bundle: Callable[..., Path]
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"
    record_cleaned_days(manifest_path, [day_bundle("2024-07-17")], clock=_clock)
    status = period_status(load_period_manifest(manifest_path))
    assert status["compatible_utc_dates"] == ["2024-07-17"]
    assert status["period_input_readiness"]["status"] == "not_ready"
    assert status["observational_completeness"]["status"] == "unverified"
    assert status["independent_transfer_completeness"]["status"] == "unverified"
    assert status["period_input_id"].startswith("multiday-ais-")


def test_real_cleaner_bundle_is_accepted_by_the_period_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "synthetic.csv"
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
    with source.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination, lineterminator="\n")
        writer.writerow(AIS_PUBLISHED_HEADER)
        writer.writerow([values[field] for field in AIS_PUBLISHED_HEADER])
    bundle = tmp_path / "real-bundle"
    result = process_ais_csv(source, bundle, load_default_config())

    inspection = inspect_cleaned_day(bundle)
    assert inspection.utc_date == "2024-07-15"
    assert inspection.cleaner_run_id == result.run_id
    assert inspection.cleaned_sha256 == result.output_sha256
    assert inspection.cleaned_rows == 1

    update = record_cleaned_days(interim / "manifest.json", [bundle], clock=_clock)
    assert update.outcomes[0].entry_status == "compatible"
    assert update.period_input_id == compute_period_input_id(update.manifest)
