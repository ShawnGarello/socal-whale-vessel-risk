from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from whale_vessel_analysis.ais import AIS_PUBLISHED_HEADER
from whale_vessel_analysis.ais_retrieval_cli import main


def _write_csv(path: Path, timestamp: str = "2024-07-15T00:00:00") -> None:
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


def _args(artifact: Path, manifest: Path) -> list[str]:
    return [
        "--input",
        str(artifact),
        "--manifest",
        str(manifest),
        "--expected-utc-date",
        "2024-07-15",
        "--route",
        "accessais",
        "--request-id",
        "accessais-2024-07-15-bbox-v1",
        "--source-reference",
        "author-supplied AccessAIS delivery",
        "--requested-from",
        "2024-07-15",
        "--requested-through",
        "2024-07-15",
        "--lon-min",
        "-122",
        "--lat-min",
        "32",
        "--lon-max",
        "-117",
        "--lat-max",
        "35",
        "--source-filename",
        artifact.name,
        "--retrieved-at-utc",
        "2026-08-27T20:00:00Z",
        "--http-content-length",
        str(artifact.stat().st_size),
    ]


def test_retrieval_module_help_works() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "whale_vessel_analysis.ais_retrieval_cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--expected-utc-date" in completed.stdout
    assert "--csv-bundle-dir" in completed.stdout
    assert completed.stderr == ""


def test_cli_success_exit_code_and_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact = tmp_path / "delivery.bin"
    manifest = tmp_path / "data" / "interim" / "manifest.json"
    _write_csv(artifact)

    assert main(_args(artifact, manifest)) == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    stored = json.loads(manifest.read_text(encoding="utf-8"))

    assert captured.err == ""
    assert output["status"] == "success"
    assert output["artifact"]["container"] == "csv"
    assert stored["entries"][0]["status"] == "verified"
    assert stored["entries"][0]["observational_completeness"]["status"] == (
        "unverified"
    )


def test_cli_failure_exit_code_records_attempt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact = tmp_path / "wrong-date.csv"
    manifest = tmp_path / "data" / "interim" / "manifest.json"
    _write_csv(artifact, "2024-07-16T00:00:00")

    assert main(_args(artifact, manifest)) == 2
    captured = capsys.readouterr()
    stored = json.loads(manifest.read_text(encoding="utf-8"))

    assert captured.out == ""
    assert "expected UTC date 2024-07-15" in captured.err
    assert stored["entries"][0]["status"] == "failed"
    assert stored["entries"][0]["attempt_history"][0]["outcome"] == "failed"


def test_cli_exercises_cleaner_without_upgrading_completeness(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact = tmp_path / "delivery.csv"
    manifest = tmp_path / "data" / "interim" / "manifest.json"
    cleaned = tmp_path / "data" / "interim" / "cleaned"
    _write_csv(artifact)
    args = [*_args(artifact, manifest), "--clean-output-dir", str(cleaned)]

    assert main(args) == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    stored = json.loads(manifest.read_text(encoding="utf-8"))
    quality = json.loads((cleaned / "quality-report.json").read_text(encoding="utf-8"))

    assert output["cleaning"]["output_rows"] == 1
    assert quality["temporal_coverage"]["completeness"]["status"] == "unverified"
    compatibility = stored["entries"][0]["cleaning_compatibility"]
    assert compatibility["status"] == "exercised_compatible"
    assert compatibility["observational_completeness_preserved"] is True
    assert stored["entries"][0]["observational_completeness"]["status"] == (
        "unverified"
    )
