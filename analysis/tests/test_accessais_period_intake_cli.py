from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from whale_vessel_analysis import accessais_period_intake, multiday_ais
from whale_vessel_analysis.accessais_period_intake_cli import main
from whale_vessel_analysis.ais import AIS_PUBLISHED_HEADER
from whale_vessel_analysis.multiday_ais import load_period_manifest


def _roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
    return interim


def _write_csv(path: Path, timestamp: str, *, mmsi: str = "123456789") -> None:
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
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(AIS_PUBLISHED_HEADER)
        writer.writerow([values[field] for field in AIS_PUBLISHED_HEADER])


def _delivery_args(source: Path, intake: Path) -> list[str]:
    return [
        "--input",
        str(source),
        "--intake-dir",
        str(intake),
        "--requested-start",
        "2024-07-01",
        "--requested-end",
        "2024-07-03",
    ]


def test_module_help_lists_prepare_run_and_status() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "whale_vessel_analysis.accessais_period_intake_cli",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "prepare" in completed.stdout
    assert "run" in completed.stdout
    assert "status" in completed.stdout
    assert "No network action" in completed.stdout


def test_prepare_status_and_run_cli_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interim = _roots(tmp_path, monkeypatch)
    source = tmp_path / "delivery.csv"
    intake = interim / "intake"
    _write_csv(source, "2024-07-01T00:00:00")

    assert main(["prepare", *_delivery_args(source, intake)]) == 0
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["outcome"] == "prepared"
    assert prepared["row_accounting"]["source_data_rows"] == 1

    assert main(["status", "--intake-dir", str(intake)]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["delivery_id"] == prepared["delivery_id"]
    assert status["observational_completeness"]["status"] == "unverified"

    assert (
        main(
            [
                "run",
                *_delivery_args(source, intake),
                "--cleaned-root",
                str(interim / "cleaned"),
                "--period-manifest",
                str(interim / "period.json"),
            ]
        )
        == 3
    )
    run = json.loads(capsys.readouterr().out)
    assert run["cleaned_dates"] == ["2024-07-01"]
    assert run["period_status"]["period_input_readiness"]["status"] == "not_ready"


def test_cli_conflict_has_distinct_exit_and_preserves_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interim = _roots(tmp_path, monkeypatch)
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    intake = interim / "intake"
    _write_csv(first, "2024-07-01T00:00:00")
    _write_csv(second, "2024-07-02T00:00:00")
    assert main(["prepare", *_delivery_args(first, intake)]) == 0
    capsys.readouterr()

    assert main(["prepare", *_delivery_args(second, intake)]) == 4
    captured = capsys.readouterr()
    assert "conflict recorded" in captured.err
    assert (intake / "daily" / "2024-07-01.csv").is_file()
    assert not (intake / "daily" / "2024-07-02.csv").exists()


def test_shared_cleaned_root_refuses_conflicting_overlap_without_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interim = _roots(tmp_path, monkeypatch)
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write_csv(first, "2024-07-01T00:00:00", mmsi="100000001")
    _write_csv(second, "2024-07-01T00:00:00", mmsi="199999999")
    manifest = interim / "period.json"
    cleaned_root = interim / "cleaned"

    def run_args(source: Path, name: str) -> list[str]:
        return [
            "run",
            "--input",
            str(source),
            "--intake-dir",
            str(interim / "intake" / name),
            "--requested-start",
            "2024-07-01",
            "--requested-end",
            "2024-07-01",
            "--cleaned-root",
            str(cleaned_root),
            "--period-manifest",
            str(manifest),
        ]

    assert main(run_args(first, "first")) == 3
    capsys.readouterr()
    established_bundle = cleaned_root / "2024-07-01"
    established_bytes = {
        path.name: path.read_bytes() for path in established_bundle.iterdir()
    }

    assert main(run_args(second, "second")) == 2
    captured = capsys.readouterr()
    assert "does not belong to the established daily slice" in captured.err
    assert established_bytes == {
        path.name: path.read_bytes() for path in established_bundle.iterdir()
    }

    stored = load_period_manifest(manifest)
    entry = next(item for item in stored["dates"] if item["utc_date"] == "2024-07-01")
    assert entry["status"] == "compatible"
    assert [attempt["outcome"] for attempt in entry["attempt_history"]] == ["recorded"]
    assert stored["period_input_readiness"]["compatible_date_count"] == 1
    assert stored["period_input_readiness"]["conflicting_date_count"] == 0


def test_run_records_independently_produced_cleaner_conflict_with_exit_four(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interim = _roots(tmp_path, monkeypatch)
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write_csv(first, "2024-07-01T00:00:00", mmsi="100000001")
    _write_csv(second, "2024-07-01T00:00:00", mmsi="199999999")
    manifest = interim / "period.json"

    def run_args(source: Path, name: str) -> list[str]:
        return [
            "run",
            "--input",
            str(source),
            "--intake-dir",
            str(interim / "intake" / name),
            "--requested-start",
            "2024-07-01",
            "--requested-end",
            "2024-07-01",
            "--cleaned-root",
            str(interim / "cleaned" / name),
            "--period-manifest",
            str(manifest),
        ]

    assert main(run_args(first, "first")) == 3
    capsys.readouterr()
    assert main(run_args(second, "second")) == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["conflicting_dates"] == ["2024-07-01"]

    stored = load_period_manifest(manifest)
    entry = next(item for item in stored["dates"] if item["utc_date"] == "2024-07-01")
    assert entry["status"] == "conflict"
    assert [attempt["outcome"] for attempt in entry["attempt_history"]] == [
        "recorded",
        "conflict",
    ]
