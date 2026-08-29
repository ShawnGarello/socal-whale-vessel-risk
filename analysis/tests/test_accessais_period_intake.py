from __future__ import annotations

import csv
import inspect
import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from whale_vessel_analysis import accessais_period_intake, multiday_ais
from whale_vessel_analysis.accessais_period_intake import (
    AccessAISPeriodConflictError,
    AccessAISPeriodIntakeError,
    RequestedPeriod,
    load_delivery_manifest,
    orchestrate_accessais_delivery,
    prepare_accessais_delivery,
)
from whale_vessel_analysis.ais import AIS_PUBLISHED_HEADER
from whale_vessel_analysis.ais_processing import process_ais_csv
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.multiday_ais import load_period_manifest

REQUESTED = RequestedPeriod(date(2024, 7, 1), date(2024, 7, 3))
FIXED_CLOCK = datetime(2026, 8, 28, 18, 0, tzinfo=UTC)


def _clock() -> datetime:
    return FIXED_CLOCK


def _roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    interim = tmp_path / "data" / "interim"
    raw = tmp_path / "data" / "raw"
    interim.mkdir(parents=True)
    raw.mkdir(parents=True)
    monkeypatch.setattr(
        accessais_period_intake, "_PROJECT_INTERIM_ROOT", interim.resolve()
    )
    monkeypatch.setattr(accessais_period_intake, "_PROJECT_RAW_ROOT", raw.resolve())
    monkeypatch.setattr(multiday_ais, "_PROJECT_INTERIM_ROOT", interim.resolve())
    monkeypatch.setattr(multiday_ais, "_PROJECT_RAW_ROOT", raw.resolve())
    return interim, raw


def _row(timestamp: str, *, mmsi: str = "123456789") -> list[str]:
    values = {
        "MMSI": mmsi,
        "BaseDateTime": timestamp,
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
    return [values[field] for field in AIS_PUBLISHED_HEADER]


def _csv_bytes(rows: list[list[str]]) -> bytes:
    import io

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(AIS_PUBLISHED_HEADER)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    path.write_bytes(_csv_bytes(rows))


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def _daily_rows(directory: Path, utc_date: str) -> list[list[str]]:
    with (directory / "daily" / f"{utc_date}.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        rows = list(csv.reader(source))
    assert rows[0] == list(AIS_PUBLISHED_HEADER)
    return rows[1:]


def _entry(manifest: dict[str, Any], utc_date: str) -> dict[str, Any]:
    return next(item for item in manifest["dates"] if item["utc_date"] == utc_date)


def test_unsorted_delivery_partitions_exact_dates_and_conserves_every_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "unsorted.csv"
    _write_csv(
        source,
        [
            _row("2024-07-03T12:00:00", mmsi="300000003"),
            _row("malformed", mmsi="900000009"),
            _row("2024-07-01T23:00:00", mmsi="100000001"),
            _row("2024-07-04T00:00:00", mmsi="400000004"),
            _row("2024-07-01T01:00:00", mmsi="100000002"),
        ],
    )

    result = prepare_accessais_delivery(
        source, interim / "intake", REQUESTED, clock=_clock
    )
    manifest = result.manifest

    assert _daily_rows(result.output_directory, "2024-07-01") == [
        _row("2024-07-01T23:00:00", mmsi="100000001"),
        _row("2024-07-01T01:00:00", mmsi="100000002"),
    ]
    assert _daily_rows(result.output_directory, "2024-07-03") == [
        _row("2024-07-03T12:00:00", mmsi="300000003")
    ]
    assert not (result.output_directory / "daily" / "2024-07-04.csv").exists()
    assert manifest["rows_by_utc_date"] == {
        "2024-07-01": 2,
        "2024-07-03": 1,
        "2024-07-04": 1,
    }
    assert manifest["row_accounting"] == {
        "status": "reconciled",
        "source_data_rows": 5,
        "valid_timestamp_rows": 4,
        "malformed_or_unassignable_timestamp_rows": 1,
        "valid_in_request_rows_assigned_to_daily_slices": 3,
        "valid_out_of_request_rows": 1,
        "conservation_equation": (
            "source_data_rows = malformed_or_unassignable_timestamp_rows + "
            "valid_in_request_rows_assigned_to_daily_slices + "
            "valid_out_of_request_rows"
        ),
    }
    coverage = manifest["requested_date_coverage"]
    assert coverage["missing_requested_utc_dates"] == ["2024-07-02"]
    assert coverage["out_of_request_utc_dates"] == ["2024-07-04"]
    assert manifest["preparation_status"] == "prepared_with_exceptions"


@pytest.mark.parametrize("container", ["csv", "zip"])
def test_direct_csv_and_safe_zip_use_content_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, container: str
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.unknown"
    content = _csv_bytes([_row("2024-07-01T00:00:00")])
    if container == "csv":
        source.write_bytes(content)
    else:
        _write_zip(
            source,
            {"delivery/readme.txt": b"metadata\n", "delivery/points.csv": content},
        )

    result = prepare_accessais_delivery(
        source,
        interim / f"intake-{container}",
        RequestedPeriod(date(2024, 7, 1), date(2024, 7, 1)),
        clock=_clock,
    )

    assert result.manifest["source"]["content_type_detected_from_bytes"] == container
    transfer = result.manifest["independent_transfer_completeness"]
    assert transfer["status"] == ("verified" if container == "zip" else "unverified")


@pytest.mark.parametrize(
    ("members", "message"),
    [
        ({"../points.csv": _csv_bytes([_row("2024-07-01T00:00:00")])}, "unsafe"),
        (
            {
                "one.csv": _csv_bytes([_row("2024-07-01T00:00:00")]),
                "two.csv": _csv_bytes([_row("2024-07-01T00:01:00")]),
            },
            "multiple ambiguous",
        ),
        ({"readme.txt": b"not csv"}, "no CSV member"),
    ],
)
def test_unsafe_or_ambiguous_zip_is_refused_without_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    members: dict[str, bytes],
    message: str,
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "bad.zip"
    _write_zip(source, members)
    output = interim / "intake"

    with pytest.raises(AccessAISPeriodIntakeError, match=message):
        prepare_accessais_delivery(source, output, REQUESTED, clock=_clock)

    assert not output.exists()
    assert list(interim.glob(".intake.temporary-*")) == []


def test_corrupt_zip_crc_is_refused_without_partial_slices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "corrupt.zip"
    content = _csv_bytes([_row("2024-07-01T00:00:00")])
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("points.csv", content)
    damaged = bytearray(source.read_bytes())
    damaged[damaged.index(content) + len(content) - 2] ^= 1
    source.write_bytes(damaged)

    with pytest.raises(AccessAISPeriodIntakeError, match="CRC validation failed"):
        prepare_accessais_delivery(source, interim / "intake", REQUESTED, clock=_clock)

    assert not (interim / "intake").exists()
    assert list(interim.glob(".intake.temporary-*")) == []


def test_daily_identity_and_bytes_do_not_depend_on_input_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    rows = [
        _row("2024-07-02T00:00:00", mmsi="200000002"),
        _row("2024-07-01T00:00:00", mmsi="100000001"),
    ]
    first_source = tmp_path / "first" / "delivery.csv"
    second_source = tmp_path / "second" / "renamed.bin"
    first_source.parent.mkdir()
    second_source.parent.mkdir()
    _write_csv(first_source, rows)
    _write_csv(second_source, rows)

    first = prepare_accessais_delivery(
        first_source, interim / "one", REQUESTED, clock=_clock
    )
    second = prepare_accessais_delivery(
        second_source, interim / "two", REQUESTED, clock=_clock
    )

    assert first.delivery_id == second.delivery_id
    first_slices = first.manifest["daily_slices"]
    second_slices = second.manifest["daily_slices"]
    assert first_slices == second_slices
    for utc_date in ("2024-07-01", "2024-07-02"):
        assert (first.output_directory / "daily" / f"{utc_date}.csv").read_bytes() == (
            second.output_directory / "daily" / f"{utc_date}.csv"
        ).read_bytes()


def test_retry_reuses_and_conflict_preserves_established_slices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    output = interim / "intake"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    first = prepare_accessais_delivery(source, output, REQUESTED, clock=_clock)
    daily_before = (output / "daily" / "2024-07-01.csv").read_bytes()

    retry = prepare_accessais_delivery(source, output, REQUESTED, clock=_clock)
    assert retry.outcome == "identical_retry"
    assert retry.delivery_id == first.delivery_id
    assert len(retry.manifest["attempt_history"]) == 2

    different = tmp_path / "different.csv"
    _write_csv(different, [_row("2024-07-02T00:00:00")])
    with pytest.raises(AccessAISPeriodConflictError, match="conflict recorded"):
        prepare_accessais_delivery(different, output, REQUESTED, clock=_clock)

    stored = load_delivery_manifest(output)
    assert stored["delivery_id"] == first.delivery_id
    assert stored["latest_attempt_outcome"] == "conflict"
    assert len(stored["attempt_history"]) == 3
    assert (output / "daily" / "2024-07-01.csv").read_bytes() == daily_before


def test_atomic_publication_failure_cleans_temporary_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    output = interim / "intake"
    _write_csv(source, [_row("2024-07-01T00:00:00")])

    def explode(temporary: Path, destination: Path) -> None:
        raise OSError("synthetic atomic publication failure")

    monkeypatch.setattr(accessais_period_intake, "_publish_directory", explode)
    with pytest.raises(OSError, match="synthetic atomic publication failure"):
        prepare_accessais_delivery(source, output, REQUESTED, clock=_clock)

    assert not output.exists()
    assert list(interim.glob(".intake.temporary-*")) == []


def test_raw_output_and_arbitrary_existing_destination_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, raw = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    with pytest.raises(AccessAISPeriodIntakeError, match="under data/raw"):
        prepare_accessais_delivery(source, raw / "intake", REQUESTED, clock=_clock)

    existing = interim / "existing"
    existing.mkdir()
    marker = existing / "preserve.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(AccessAISPeriodIntakeError, match="not a complete"):
        prepare_accessais_delivery(source, existing, REQUESTED, clock=_clock)
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_daily_slices_are_cleaner_compatible_and_populate_period_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    _write_csv(
        source,
        [
            _row("2024-07-02T00:01:00", mmsi="200000002"),
            _row("2024-07-01T00:01:00", mmsi="100000001"),
        ],
    )
    period_manifest = interim / "period" / "manifest.json"
    result = orchestrate_accessais_delivery(
        source,
        interim / "intake",
        interim / "cleaned",
        period_manifest,
        REQUESTED,
        load_default_config(),
        clock=_clock,
    )

    assert result.cleaned_dates == ("2024-07-01", "2024-07-02")
    stored = load_period_manifest(period_manifest)
    assert _entry(stored, "2024-07-01")["status"] == "compatible"
    assert _entry(stored, "2024-07-02")["status"] == "compatible"
    assert stored["period_input_readiness"]["compatible_date_count"] == 2
    assert stored["period_input_readiness"]["missing_date_count"] == 151
    assert stored["period_input_readiness"]["status"] == "not_ready"
    assert stored["independent_transfer_completeness"]["status"] == "unverified"
    assert stored["observational_completeness"]["status"] == "unverified"
    assert result.preparation.manifest["period_availability"]["status"] == "not_claimed"


def test_interruption_then_resume_skips_successfully_recorded_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    _write_csv(
        source,
        [
            _row("2024-07-01T00:01:00", mmsi="100000001"),
            _row("2024-07-02T00:01:00", mmsi="200000002"),
        ],
    )
    period_manifest = interim / "period.json"
    calls: list[str] = []

    def interrupting_cleaner(input_path: Path, output: Path, config: Any) -> Any:
        calls.append(input_path.stem)
        if input_path.stem == "2024-07-02":
            raise RuntimeError("synthetic interruption")
        return process_ais_csv(input_path, output, config)

    with pytest.raises(RuntimeError, match="synthetic interruption"):
        orchestrate_accessais_delivery(
            source,
            interim / "intake",
            interim / "cleaned",
            period_manifest,
            REQUESTED,
            load_default_config(),
            clock=_clock,
            cleaner=interrupting_cleaner,
        )
    after_interrupt = load_period_manifest(period_manifest)
    assert _entry(after_interrupt, "2024-07-01")["status"] == "compatible"
    assert _entry(after_interrupt, "2024-07-02")["status"] == "missing"

    resumed_calls: list[str] = []

    def resumed_cleaner(input_path: Path, output: Path, config: Any) -> Any:
        resumed_calls.append(input_path.stem)
        return process_ais_csv(input_path, output, config)

    resumed = orchestrate_accessais_delivery(
        source,
        interim / "intake",
        interim / "cleaned",
        period_manifest,
        REQUESTED,
        load_default_config(),
        clock=_clock,
        cleaner=resumed_cleaner,
    )

    assert calls == ["2024-07-01", "2024-07-02"]
    assert resumed_calls == ["2024-07-02"]
    assert resumed.skipped_successful_dates == ("2024-07-01",)
    assert resumed.cleaned_dates == ("2024-07-02",)


def test_streaming_implementation_has_no_whole_delivery_materializer() -> None:
    source = inspect.getsource(accessais_period_intake._partition_csv_stream)
    for forbidden in (
        "import pandas",
        "import polars",
        "import pyarrow",
        ".read_bytes()",
        ".read_text()",
        "list(reader)",
    ):
        assert forbidden not in source
    assert "for row_number, row in enumerate(reader" in source
    writers_source = inspect.getsource(accessais_period_intake._DailyWriters)
    assert "MAX_OPEN_DAILY_FILES" in writers_source


def test_matching_source_content_length_is_independent_transfer_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    result = prepare_accessais_delivery(
        source,
        interim / "intake",
        REQUESTED,
        source_content_length=source.stat().st_size,
        clock=_clock,
    )
    assert result.manifest["independent_transfer_completeness"]["status"] == (
        "verified"
    )
    assert result.manifest["observational_completeness"]["status"] == "unverified"


@pytest.mark.parametrize(
    ("field", "status", "message"),
    [
        (
            "independent_transfer_completeness",
            "verified",
            "unsupported by source evidence",
        ),
        (
            "observational_completeness",
            "verified",
            "must remain unverified",
        ),
        ("period_availability", "available", "cannot claim analytical-period"),
    ],
)
def test_manifest_cannot_be_tampered_into_a_false_completeness_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    status: str,
    message: str,
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    output = interim / "intake"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    prepare_accessais_delivery(source, output, REQUESTED, clock=_clock)
    manifest_path = output / "delivery-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload[field]["status"] = status
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AccessAISPeriodIntakeError, match=message):
        load_delivery_manifest(output)
