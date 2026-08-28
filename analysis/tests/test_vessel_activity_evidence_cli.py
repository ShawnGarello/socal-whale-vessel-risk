from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from whale_vessel_analysis import vessel_activity_evidence_cli
from whale_vessel_analysis.vessel_activity_evidence import (
    VesselActivityEvidenceError,
)


def test_module_help_exposes_explicit_inputs_candidates_and_output() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "whale_vessel_analysis.vessel_activity_evidence_cli",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--cleaned-bundle" in completed.stdout
    assert "--output" in completed.stdout
    assert "--candidate-maximum-gap-seconds" in completed.stdout
    assert "--candidate-implied-speed-ceiling-knots" in completed.stdout
    assert "--candidate-minimum-vessel-length-m" in completed.stdout
    assert "--grid-input" in completed.stdout
    assert "--expected-grid-sha256" in completed.stdout
    assert "--overwrite" in completed.stdout
    assert completed.stderr == ""


def test_cli_success_passes_only_explicit_candidate_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = object()
    observed: dict[str, object] = {}
    monkeypatch.setattr(
        vessel_activity_evidence_cli, "load_default_config", lambda: config
    )

    def run(*args: object, **kwargs: object) -> SimpleNamespace:
        observed["args"] = args
        observed["kwargs"] = kwargs
        return SimpleNamespace(to_dict=lambda: {"status": "ok"})

    monkeypatch.setattr(vessel_activity_evidence_cli, "run_evidence", run)
    exit_code = vessel_activity_evidence_cli.main(
        [
            "--cleaned-bundle",
            str(tmp_path / "bundle"),
            "--output",
            str(tmp_path / "data" / "interim" / "report.json"),
            "--candidate-maximum-gap-seconds",
            "120",
            "--candidate-implied-speed-ceiling-knots",
            "30",
            "--candidate-minimum-vessel-length-m",
            "100",
            "--grid-input",
            str(tmp_path / "grid.parquet"),
            "--expected-grid-sha256",
            "a" * 64,
            "--overwrite",
        ]
    )

    assert exit_code == 0
    assert observed["args"] == (
        tmp_path / "bundle",
        tmp_path / "data" / "interim" / "report.json",
        config,
    )
    assert observed["kwargs"] == {
        "candidate_maximum_gap_seconds": [120.0],
        "candidate_implied_speed_ceiling_knots": [30.0],
        "candidate_minimum_vessel_length_m": [100.0],
        "grid_input": tmp_path / "grid.parquet",
        "expected_grid_sha256": "a" * 64,
        "overwrite": True,
    }
    captured = capsys.readouterr()
    assert '"status": "ok"' in captured.out
    assert captured.err == ""


def test_cli_has_no_hidden_candidate_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        vessel_activity_evidence_cli, "load_default_config", lambda: object()
    )

    def run(*_args: object, **kwargs: object) -> SimpleNamespace:
        assert kwargs["candidate_maximum_gap_seconds"] == []
        assert kwargs["candidate_implied_speed_ceiling_knots"] == []
        assert kwargs["candidate_minimum_vessel_length_m"] == []
        return SimpleNamespace(to_dict=lambda: {})

    monkeypatch.setattr(vessel_activity_evidence_cli, "run_evidence", run)

    assert (
        vessel_activity_evidence_cli.main(
            [
                "--cleaned-bundle",
                str(tmp_path / "bundle"),
                "--output",
                str(tmp_path / "data" / "interim" / "report.json"),
            ]
        )
        == 0
    )


def test_cli_returns_documented_error_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        vessel_activity_evidence_cli, "load_default_config", lambda: object()
    )

    def fail(*_args: object, **_kwargs: object) -> object:
        raise VesselActivityEvidenceError("synthetic evidence failure")

    monkeypatch.setattr(vessel_activity_evidence_cli, "run_evidence", fail)
    exit_code = vessel_activity_evidence_cli.main(
        [
            "--cleaned-bundle",
            str(tmp_path / "bundle"),
            "--output",
            str(tmp_path / "data" / "interim" / "report.json"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "synthetic evidence failure" in captured.err
    assert captured.out == ""
