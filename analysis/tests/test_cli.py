from __future__ import annotations

import json
import subprocess
import sys

import pytest

from whale_vessel_analysis.cli import main


def test_module_help_works() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "whale_vessel_analysis", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "validate-ais" in completed.stdout
    assert "validate-whale" in completed.stdout
    assert completed.stderr == ""


def test_validate_default_config_boundary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["validate-config"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["configuration"]["spatial"]["analytical_domain_status"] == (
        "unresolved"
    )
    assert payload["sha256"] == (
        "617f1b3b513d15b1c7bc3a6f8bf4a13f4ad60687c9342332473c0a40051939ff"
    )
