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
    assert "process-ais" in completed.stdout
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
    assert payload["configuration"]["analytical_period"] == {
        "start_date": "2024-07-01",
        "end_date": "2024-11-30",
    }
    assert payload["sha256"] == (
        "df60aa03796ca979eff5bdca4c620fbac809a797d40d320ea649276d6c889c06"
    )
