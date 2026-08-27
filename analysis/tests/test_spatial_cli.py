from __future__ import annotations

import subprocess
import sys


def test_spatial_module_help_exposes_explicit_input_output_boundary() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "whale_vessel_analysis.spatial_cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--input" in completed.stdout
    assert "--layer" in completed.stdout
    assert "--source-crs" in completed.stdout
    assert "--output" in completed.stdout
    assert "--config" in completed.stdout
    assert "--overwrite" in completed.stdout
    assert completed.stderr == ""
