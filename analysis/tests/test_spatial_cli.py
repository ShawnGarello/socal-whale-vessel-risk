from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from whale_vessel_analysis import spatial_cli


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


def test_execution_start_is_captured_before_loading_and_processing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    events: list[str] = []
    started_at = datetime(2026, 8, 27, 12, tzinfo=UTC)
    config = object()
    mask = object()
    dataset = object()

    def capture_start() -> datetime:
        events.append("start")
        return started_at

    def load_config() -> object:
        events.append("load-config")
        return config

    def load_mask(*_args: object, **_kwargs: object) -> object:
        events.append("load-mask")
        return mask

    def build_grid(*_args: object, **_kwargs: object) -> object:
        events.append("build-grid")
        return dataset

    def write_grid(*_args: object, **kwargs: object) -> SimpleNamespace:
        events.append("write-grid")
        assert kwargs["started_at"] == started_at
        return SimpleNamespace(to_dict=lambda: {"status": "ok"})

    monkeypatch.setattr(spatial_cli, "_utc_now", capture_start)
    monkeypatch.setattr(spatial_cli, "load_default_config", load_config)
    monkeypatch.setattr(spatial_cli, "load_water_mask", load_mask)
    monkeypatch.setattr(spatial_cli, "build_water_grid", build_grid)
    monkeypatch.setattr(spatial_cli, "write_water_grid", write_grid)

    exit_code = spatial_cli.main(
        [
            "--input",
            str(tmp_path / "mask.geojson"),
            "--source-crs",
            "EPSG:4326",
            "--output",
            str(tmp_path / "grid.parquet"),
        ]
    )

    assert exit_code == 0
    assert events == ["start", "load-config", "load-mask", "build-grid", "write-grid"]
    assert '"status": "ok"' in capsys.readouterr().out
