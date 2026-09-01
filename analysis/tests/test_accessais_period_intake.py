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
    CanonicalizationResources,
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


def test_same_row_multiset_in_different_orders_is_canonical_and_reusable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    rows = [
        _row("2024-07-01T00:02:00", mmsi="100000003"),
        _row("2024-07-01T00:00:00", mmsi="100000001"),
        _row("2024-07-01T00:01:00", mmsi="100000002"),
    ]
    first_source = tmp_path / "first.csv"
    second_source = tmp_path / "second.csv"
    _write_csv(first_source, rows)
    _write_csv(second_source, list(reversed(rows)))

    first = prepare_accessais_delivery(first_source, interim / "first", REQUESTED)
    second = prepare_accessais_delivery(second_source, interim / "second", REQUESTED)
    first_slice = first.manifest["daily_slices"][0]
    second_slice = second.manifest["daily_slices"][0]

    assert first.delivery_id != second.delivery_id
    assert (
        first_slice["canonical_content_identity"]
        == second_slice["canonical_content_identity"]
    )
    assert first_slice["canonical_artifact"] == second_slice["canonical_artifact"]
    assert (first.output_directory / "daily" / "2024-07-01.csv").read_bytes() == (
        second.output_directory / "daily" / "2024-07-01.csv"
    ).read_bytes()

    period_manifest = interim / "period.json"
    cleaned_root = interim / "cleaned"
    config = load_default_config()
    orchestrate_accessais_delivery(
        first_source,
        interim / "run-first",
        cleaned_root,
        period_manifest,
        REQUESTED,
        config,
    )
    reused = orchestrate_accessais_delivery(
        second_source,
        interim / "run-second",
        cleaned_root,
        period_manifest,
        REQUESTED,
        config,
    )
    assert reused.skipped_successful_dates == ("2024-07-01",)


def test_duplicate_multiplicity_and_csv_source_format_normalize_deterministically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    duplicate = _row("2024-07-01T00:00:00", mmsi="100000001")
    other = _row("2024-07-01T00:01:00", mmsi="100000002")
    first = tmp_path / "first.csv"
    _write_csv(first, [duplicate, other, duplicate])

    second = tmp_path / "second.csv"
    with second.open("w", encoding="utf-8", newline="") as output:
        output.write(",".join(AIS_PUBLISHED_HEADER) + "\r\n")
        for row in [other, duplicate, duplicate]:
            output.write(
                ",".join(f'"{value.replace(chr(34), chr(34) * 2)}"' for value in row)
                + "\r\n"
            )

    prepared_a = prepare_accessais_delivery(first, interim / "a", REQUESTED)
    prepared_b = prepare_accessais_delivery(second, interim / "b", REQUESTED)
    bytes_a = (prepared_a.output_directory / "daily" / "2024-07-01.csv").read_bytes()
    bytes_b = (prepared_b.output_directory / "daily" / "2024-07-01.csv").read_bytes()

    assert bytes_a == bytes_b
    assert b"\r\n" not in bytes_a
    assert _daily_rows(prepared_a.output_directory, "2024-07-01").count(duplicate) == 2


def test_blank_later_field_sorts_and_serializes_as_empty_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    populated = _row("2024-07-01T00:00:00", mmsi="100000001")
    blank = populated.copy()
    blank[AIS_PUBLISHED_HEADER.index("IMO")] = ""
    source = tmp_path / "blank-first-source.csv"
    reversed_source = tmp_path / "blank-reversed-source.csv"
    _write_csv(source, [populated, blank, blank])
    _write_csv(reversed_source, [blank, blank, populated])

    first = prepare_accessais_delivery(source, interim / "first", REQUESTED)
    loaded = load_delivery_manifest(first.output_directory)
    retry = prepare_accessais_delivery(source, interim / "first", REQUESTED)
    reversed_result = prepare_accessais_delivery(
        reversed_source, interim / "reversed", REQUESTED
    )

    first_slice = loaded["daily_slices"][0]
    reversed_slice = reversed_result.manifest["daily_slices"][0]
    assert retry.outcome == "identical_retry"
    assert (
        first_slice["canonical_content_identity"]
        == (reversed_slice["canonical_content_identity"])
    )
    first_bytes = (first.output_directory / "daily" / "2024-07-01.csv").read_bytes()
    reversed_bytes = (
        reversed_result.output_directory / "daily" / "2024-07-01.csv"
    ).read_bytes()
    assert first_bytes == reversed_bytes
    assert _daily_rows(first.output_directory, "2024-07-01") == [
        blank,
        blank,
        populated,
    ]
    data_lines = first_bytes.splitlines()[1:]
    assert all(
        line.startswith(b'"') and line.count(b'","') == 16 for line in data_lines
    )
    assert all(b',"",' in line for line in data_lines[:2])


@pytest.mark.parametrize(
    "changed_rows",
    [
        [_row("2024-07-01T00:00:00", mmsi="100000001")],
        [
            _row("2024-07-01T00:00:00", mmsi="100000001"),
            _row("2024-07-01T00:01:00", mmsi="100000002"),
            _row("2024-07-01T00:02:00", mmsi="100000003"),
        ],
        [
            _row("2024-07-01T00:00:00", mmsi="100000001"),
            _row("2024-07-01T00:01:00", mmsi="100000002"),
            _row("2024-07-01T00:01:00", mmsi="100000002"),
        ],
    ],
    ids=["removed-row", "added-row", "changed-duplicate-count"],
)
def test_changed_row_population_is_not_canonically_equivalent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_rows: list[list[str]],
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    baseline_rows = [
        _row("2024-07-01T00:00:00", mmsi="100000001"),
        _row("2024-07-01T00:01:00", mmsi="100000002"),
    ]
    baseline = tmp_path / "baseline.csv"
    changed = tmp_path / "changed.csv"
    _write_csv(baseline, baseline_rows)
    _write_csv(changed, changed_rows)
    first = prepare_accessais_delivery(baseline, interim / "baseline", REQUESTED)
    second = prepare_accessais_delivery(changed, interim / "changed", REQUESTED)
    assert (
        first.manifest["daily_slices"][0]["canonical_content_identity"]
        != (second.manifest["daily_slices"][0]["canonical_content_identity"])
    )


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


@pytest.mark.parametrize(
    "relative_path",
    [
        pytest.param(None, id="missing"),
        pytest.param(7, id="non-string"),
        pytest.param("../outside.csv", id="parent-traversal"),
        pytest.param("/outside.csv", id="posix-absolute"),
        pytest.param("C:/outside.csv", id="windows-absolute"),
        pytest.param(r"daily\2024-07-01.csv", id="backslashes"),
        pytest.param("daily/./2024-07-01.csv", id="alternate-spelling"),
        pytest.param("daily/2024-07-02.csv", id="different-date"),
    ],
)
def test_tampered_manifest_rejects_noncanonical_daily_slice_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: object,
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "intake"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    prepare_accessais_delivery(source, intake, REQUESTED, clock=_clock)
    manifest_path = intake / "delivery-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    daily_slice = payload["daily_slices"][0]
    if relative_path is None:
        daily_slice.pop("relative_path")
    else:
        daily_slice["relative_path"] = relative_path
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        AccessAISPeriodIntakeError,
        match=r"relative_path must be exactly daily/2024-07-01\.csv",
    ):
        load_delivery_manifest(intake)


def test_manifest_rejects_redistributed_per_date_row_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "intake"
    _write_csv(
        source,
        [
            _row("2024-07-01T00:00:00", mmsi="100000001"),
            _row("2024-07-01T00:01:00", mmsi="100000002"),
            _row("2024-07-02T00:00:00", mmsi="200000001"),
        ],
    )
    prepare_accessais_delivery(source, intake, REQUESTED, clock=_clock)
    manifest_path = intake / "delivery-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["rows_by_utc_date"] = {"2024-07-01": 1, "2024-07-02": 2}
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        AccessAISPeriodIntakeError,
        match="row_count does not match rows_by_utc_date",
    ):
        load_delivery_manifest(intake)


@pytest.mark.parametrize(
    ("location", "value"),
    [
        pytest.param("row-accounting", "1", id="row-accounting-string"),
        pytest.param("row-accounting", True, id="row-accounting-boolean"),
        pytest.param("rows-by-date", "1", id="rows-by-date-string"),
        pytest.param("rows-by-date", True, id="rows-by-date-boolean"),
        pytest.param("daily-slice", "1", id="daily-slice-string"),
        pytest.param("daily-slice", True, id="daily-slice-boolean"),
    ],
)
def test_manifest_rejects_string_and_boolean_row_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
    value: object,
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "intake"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    prepare_accessais_delivery(source, intake, REQUESTED, clock=_clock)
    manifest_path = intake / "delivery-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if location == "row-accounting":
        payload["row_accounting"]["source_data_rows"] = value
    elif location == "rows-by-date":
        payload["rows_by_utc_date"]["2024-07-01"] = value
    elif location == "daily-slice":
        payload["daily_slices"][0]["row_count"] = value
    else:
        raise AssertionError(f"unhandled count location: {location}")
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AccessAISPeriodIntakeError, match="non-boolean integer count"):
        load_delivery_manifest(intake)


def test_manifest_rejects_missing_daily_slice_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "intake"
    _write_csv(
        source,
        [
            _row("2024-07-01T00:00:00", mmsi="100000001"),
            _row("2024-07-02T00:00:00", mmsi="200000001"),
        ],
    )
    prepare_accessais_delivery(source, intake, REQUESTED, clock=_clock)
    manifest_path = intake / "delivery-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["daily_slices"] = [
        item for item in payload["daily_slices"] if item["utc_date"] == "2024-07-01"
    ]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        AccessAISPeriodIntakeError,
        match="slice dates must exactly match present_requested_utc_dates",
    ):
        load_delivery_manifest(intake)


def test_manifest_rejects_unexpected_daily_slice_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "intake"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    prepare_accessais_delivery(source, intake, REQUESTED, clock=_clock)
    manifest_path = intake / "delivery-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    unexpected = dict(payload["daily_slices"][0])
    unexpected["utc_date"] = "2024-07-02"
    payload["daily_slices"].append(unexpected)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        AccessAISPeriodIntakeError,
        match="slice dates must exactly match present_requested_utc_dates",
    ):
        load_delivery_manifest(intake)


def test_orchestration_refuses_tampered_slice_traversal_before_cleaning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "intake"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    outside = tmp_path / "data" / "outside.csv"
    _write_csv(outside, [_row("2024-07-01T00:00:00", mmsi="900000009")])
    prepare_accessais_delivery(source, intake, REQUESTED, clock=_clock)
    manifest_path = intake / "delivery-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["daily_slices"][0]["relative_path"] = "../../outside.csv"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    cleaner_called = False

    def cleaner(input_path: Path, output: Path, config: Any) -> Any:
        nonlocal cleaner_called
        cleaner_called = True
        return process_ais_csv(input_path, output, config)

    with pytest.raises(AccessAISPeriodIntakeError, match="relative_path"):
        orchestrate_accessais_delivery(
            source,
            intake,
            interim / "cleaned",
            interim / "period.json",
            REQUESTED,
            load_default_config(),
            clock=_clock,
            cleaner=cleaner,
        )

    assert cleaner_called is False
    assert outside.is_file()
    assert not (interim / "cleaned").exists()
    assert not (interim / "period.json").exists()


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


def test_prepare_refuses_intake_as_spill_parent_without_residual_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "intake"
    _write_csv(source, [_row("2024-07-01T00:00:00")])

    with pytest.raises(
        AccessAISPeriodIntakeError,
        match=r"canonicalization temporary directory.*must be disjoint",
    ):
        prepare_accessais_delivery(
            source,
            intake,
            REQUESTED,
            CanonicalizationResources("64MB", intake),
            clock=_clock,
        )

    assert not intake.exists()


@pytest.mark.parametrize("spill_destination", ["cleaned", "manifest"])
def test_spill_parent_must_be_disjoint_before_any_destination_is_created(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    spill_destination: str,
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "intake"
    cleaned = interim / "cleaned"
    manifest = interim / "period.json"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    spill = {"intake": intake, "cleaned": cleaned, "manifest": manifest}[
        spill_destination
    ]

    with pytest.raises(
        AccessAISPeriodIntakeError,
        match=r"canonicalization temporary directory.*must be disjoint",
    ):
        orchestrate_accessais_delivery(
            source,
            intake,
            cleaned,
            manifest,
            REQUESTED,
            load_default_config(),
            CanonicalizationResources("64MB", spill),
            clock=_clock,
        )

    assert not intake.exists()
    assert not cleaned.exists()
    assert not manifest.exists()


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


def test_disjoint_deliveries_accumulate_in_one_period_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    first_source = tmp_path / "first-delivery.csv"
    second_source = tmp_path / "second-delivery.csv"
    _write_csv(
        first_source,
        [
            _row("2024-07-01T00:01:00", mmsi="100000001"),
            _row("2024-07-01T00:02:00", mmsi="100000002"),
        ],
    )
    _write_csv(
        second_source,
        [_row("2024-07-03T00:01:00", mmsi="300000003")],
    )
    period_manifest = interim / "period" / "manifest.json"

    first = orchestrate_accessais_delivery(
        first_source,
        interim / "intake" / "first",
        interim / "cleaned" / "first",
        period_manifest,
        RequestedPeriod(date(2024, 7, 1), date(2024, 7, 1)),
        load_default_config(),
        clock=_clock,
    )
    second = orchestrate_accessais_delivery(
        second_source,
        interim / "intake" / "second",
        interim / "cleaned" / "second",
        period_manifest,
        RequestedPeriod(date(2024, 7, 3), date(2024, 7, 3)),
        load_default_config(),
        clock=_clock,
    )

    stored = load_period_manifest(period_manifest)
    assert first.cleaned_dates == ("2024-07-01",)
    assert second.cleaned_dates == ("2024-07-03",)
    assert first.conflicting_dates == second.conflicting_dates == ()
    assert _entry(stored, "2024-07-01")["status"] == "compatible"
    assert _entry(stored, "2024-07-03")["status"] == "compatible"
    readiness = stored["period_input_readiness"]
    assert readiness["status"] == "not_ready"
    assert readiness["expected_date_count"] == 153
    assert readiness["compatible_date_count"] == 2
    assert readiness["missing_date_count"] == 151
    assert readiness["conflicting_date_count"] == 0
    assert readiness["missing_expected_utc_dates"] == [
        utc_date
        for utc_date in multiday_ais.accepted_utc_dates()
        if utc_date not in {"2024-07-01", "2024-07-03"}
    ]
    assert readiness["conflicting_utc_dates"] == []
    assert readiness["insufficient_evidence"] == list(
        multiday_ais.INSUFFICIENT_READINESS_EVIDENCE
    )
    assert first.preparation.manifest["row_accounting"]["source_data_rows"] == 2
    assert first.preparation.manifest["rows_by_utc_date"] == {"2024-07-01": 2}
    assert second.preparation.manifest["row_accounting"]["source_data_rows"] == 1
    assert second.preparation.manifest["rows_by_utc_date"] == {"2024-07-03": 1}
    assert stored["independent_transfer_completeness"]["status"] == "unverified"
    assert stored["observational_completeness"]["status"] == "unverified"


def test_overlapping_delivery_reuses_identical_established_date_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    first_source = tmp_path / "first-delivery.csv"
    overlapping_source = tmp_path / "overlapping-delivery.csv"
    shared_row = _row("2024-07-02T00:01:00", mmsi="200000002")
    _write_csv(
        first_source,
        [
            _row("2024-07-01T00:01:00", mmsi="100000001"),
            shared_row,
        ],
    )
    _write_csv(
        overlapping_source,
        [
            shared_row,
            _row("2024-07-03T00:01:00", mmsi="300000003"),
        ],
    )
    period_manifest = interim / "period.json"
    cleaned_root = interim / "cleaned"

    first = orchestrate_accessais_delivery(
        first_source,
        interim / "intake" / "first",
        cleaned_root,
        period_manifest,
        RequestedPeriod(date(2024, 7, 1), date(2024, 7, 2)),
        load_default_config(),
        clock=_clock,
    )
    retry = orchestrate_accessais_delivery(
        overlapping_source,
        interim / "intake" / "overlap",
        cleaned_root,
        period_manifest,
        RequestedPeriod(date(2024, 7, 2), date(2024, 7, 3)),
        load_default_config(),
        clock=_clock,
    )

    stored = load_period_manifest(period_manifest)
    entry = _entry(stored, "2024-07-02")
    assert first.preparation.delivery_id != retry.preparation.delivery_id
    assert retry.conflicting_dates == ()
    assert retry.skipped_successful_dates == ("2024-07-02",)
    assert retry.cleaned_dates == ("2024-07-03",)
    assert entry["status"] == "compatible"
    assert [attempt["outcome"] for attempt in entry["attempt_history"]] == ["recorded"]
    assert stored["period_input_readiness"]["compatible_date_count"] == 3
    assert stored["period_input_readiness"]["missing_date_count"] == 150


def test_overlapping_conflict_preserves_prior_successful_dates_and_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    first_source = tmp_path / "first-delivery.csv"
    conflicting_source = tmp_path / "conflicting-delivery.csv"
    _write_csv(
        first_source,
        [
            _row("2024-07-01T00:01:00", mmsi="100000001"),
            _row("2024-07-02T00:01:00", mmsi="200000002"),
        ],
    )
    _write_csv(
        conflicting_source,
        [_row("2024-07-02T00:01:00", mmsi="299999999")],
    )
    period_manifest = interim / "period.json"

    orchestrate_accessais_delivery(
        first_source,
        interim / "intake" / "first",
        interim / "cleaned" / "first",
        period_manifest,
        RequestedPeriod(date(2024, 7, 1), date(2024, 7, 2)),
        load_default_config(),
        clock=_clock,
    )
    before = load_period_manifest(period_manifest)
    established_identity = dict(
        _entry(before, "2024-07-02")["cleaner_bundle_compatibility"]
    )

    conflict = orchestrate_accessais_delivery(
        conflicting_source,
        interim / "intake" / "conflict",
        interim / "cleaned" / "conflict",
        period_manifest,
        RequestedPeriod(date(2024, 7, 2), date(2024, 7, 2)),
        load_default_config(),
        clock=_clock,
    )

    stored = load_period_manifest(period_manifest)
    conflicted_entry = _entry(stored, "2024-07-02")
    assert conflict.conflicting_dates == ("2024-07-02",)
    assert _entry(stored, "2024-07-01")["status"] == "compatible"
    assert conflicted_entry["status"] == "conflict"
    assert conflicted_entry["cleaner_bundle_compatibility"] == established_identity
    assert [attempt["outcome"] for attempt in conflicted_entry["attempt_history"]] == [
        "recorded",
        "conflict",
    ]
    assert stored["period_input_readiness"]["status"] == "not_ready"
    assert stored["period_input_readiness"]["conflicting_utc_dates"] == ["2024-07-02"]
    assert stored["observational_completeness"]["status"] == "unverified"


def test_new_cleaner_bundle_must_record_the_daily_slice_sha_before_period_recording(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    different_input = tmp_path / "different.csv"
    _write_csv(source, [_row("2024-07-01T00:00:00", mmsi="100000001")])
    _write_csv(different_input, [_row("2024-07-01T00:00:00", mmsi="200000002")])
    period_manifest = interim / "period.json"

    def wrong_input_cleaner(input_path: Path, output: Path, config: Any) -> Any:
        assert input_path.name == "2024-07-01.csv"
        return process_ais_csv(different_input, output, config)

    with pytest.raises(
        AccessAISPeriodIntakeError,
        match="does not record the established daily-slice SHA-256",
    ):
        orchestrate_accessais_delivery(
            source,
            interim / "intake",
            interim / "cleaned",
            period_manifest,
            REQUESTED,
            load_default_config(),
            clock=_clock,
            cleaner=wrong_input_cleaner,
        )

    assert (interim / "cleaned" / "2024-07-01").is_dir()
    assert not period_manifest.exists()


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("same-managed-root", "must be disjoint"),
        ("cleaned-inside-intake", "must be disjoint"),
        ("intake-inside-cleaned", "must be disjoint"),
        ("manifest-inside-intake", "inside the intake directory"),
        ("manifest-inside-cleaned", "inside the cleaned bundle root"),
    ],
)
def test_orchestration_rejects_overlapping_managed_paths_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    message: str,
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    intake = interim / "intake"
    cleaned = interim / "cleaned"
    manifest = interim / "period.json"
    if case == "same-managed-root":
        cleaned = intake
    elif case == "cleaned-inside-intake":
        cleaned = intake / "cleaned"
    elif case == "intake-inside-cleaned":
        intake = cleaned / "intake"
    elif case == "manifest-inside-intake":
        manifest = intake / "period.json"
    elif case == "manifest-inside-cleaned":
        manifest = cleaned / "period.json"
    else:
        raise AssertionError(f"unhandled test case: {case}")

    with pytest.raises(AccessAISPeriodIntakeError, match=message):
        orchestrate_accessais_delivery(
            source,
            intake,
            cleaned,
            manifest,
            REQUESTED,
            load_default_config(),
            clock=_clock,
        )

    assert list(interim.iterdir()) == []


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


def test_v1_manifest_remains_read_only_valid_and_cannot_be_reused_for_v2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "legacy-v1"
    _write_csv(source, [_row("2024-07-01T00:00:00")])
    prepare_accessais_delivery(source, intake, REQUESTED, clock=_clock)

    manifest_path = intake / "delivery-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["contract"] = "accessais_period_delivery_v1"
    payload["schema_version"] = 1
    payload["processing_version"] = "1.0.0"
    payload["delivery_id"] = accessais_period_intake._v1_delivery_id(
        payload["source"]["sha256"], REQUESTED
    )
    for daily_slice in payload["daily_slices"]:
        artifact = daily_slice.pop("canonical_artifact")
        content_id = daily_slice.pop("canonical_content_identity")
        assert content_id
        daily_slice["byte_size"] = artifact["byte_size"]
        daily_slice["sha256"] = artifact["sha256"]
        daily_slice["artifact_id"] = accessais_period_intake._v1_slice_id(
            payload["delivery_id"],
            daily_slice["utc_date"],
            artifact["sha256"],
            daily_slice["row_count"],
        )
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_delivery_manifest(intake)["contract"] == (
        "accessais_period_delivery_v1"
    )
    with pytest.raises(AccessAISPeriodIntakeError, match=r"read-only.*Version 2"):
        prepare_accessais_delivery(source, intake, REQUESTED, clock=_clock)
