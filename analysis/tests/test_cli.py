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

    assert payload["configuration"]["spatial"]["analytical_domain"] == {
        "id": "receivers_50_nautical_miles",
        "status": "accepted",
        "qualification": "system_performance_qualified",
        "distance_nautical_miles": 50,
        "distance_m": 92600,
        "measured_from": "relevant_nais_reception_stations",
        "geometry_basis": (
            "union_of_station_buffers_intersected_with_modeled_whale_support"
        ),
        "boundary_cell_treatment": "exact_fractional_geometry",
        "distance_from_coast": False,
        "empirical_2024_coverage": False,
        "outside_cell_treatment": ("exclude_from_headline_statistics_not_low_traffic"),
        "limitations": {
            "receiver_uptime_2024": "unknown",
            "station_completeness": "unknown",
            "feed_interruptions": "unknown",
            "antenna_and_terrain_effects": "not_empirically_modeled",
            "observational_completeness": "unverified",
        },
    }
    assert payload["configuration"]["analytical_period"] == {
        "start_date": "2024-07-01",
        "end_date": "2024-11-30",
    }
    assert payload["sha256"] == (
        "897f538854370c8f8ae2ff4f0e20ccad591f4ab8987152040d260567fd7d4caf"
    )
