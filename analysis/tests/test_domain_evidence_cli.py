from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from whale_vessel_analysis import domain_evidence_cli


def test_module_help_exposes_paired_outputs_and_overwrite_policy() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "whale_vessel_analysis.domain_evidence_cli",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--report" in completed.stdout
    assert "--masks" in completed.stdout
    assert "--overwrite" in completed.stdout
    assert completed.stderr == ""


def test_cli_passes_explicit_paths_and_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed: dict[str, object] = {}

    def run(**kwargs: object) -> dict[str, object]:
        observed.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(domain_evidence_cli, "run_domain_evidence", run)
    arguments = {
        name: tmp_path / name
        for name in (
            "config",
            "grid",
            "shoreline-archive",
            "station-archive",
            "vsr",
            "report",
            "masks",
        )
    }
    argv: list[str] = []
    for name, path in arguments.items():
        argv.extend((f"--{name}", str(path)))
    argv.append("--overwrite")

    assert domain_evidence_cli.main(argv) == 0
    assert observed == {
        "config_path": arguments["config"],
        "grid_path": arguments["grid"],
        "shoreline_archive": arguments["shoreline-archive"],
        "station_archive": arguments["station-archive"],
        "vsr_path": arguments["vsr"],
        "report_path": arguments["report"],
        "masks_path": arguments["masks"],
        "overwrite": True,
    }
    captured = capsys.readouterr()
    assert '"status": "ok"' in captured.out
    assert captured.err == ""
