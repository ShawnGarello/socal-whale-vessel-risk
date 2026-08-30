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


def _write_csv(path: Path, timestamp: str) -> None:
    values = {
        "MMSI": "123456789",
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
