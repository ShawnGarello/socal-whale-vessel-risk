from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from whale_vessel_analysis import whale_grid_cli
from whale_vessel_analysis.whale_grid import WhaleGridInputError


def test_whale_grid_module_help_exposes_explicit_inputs_and_output() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "whale_vessel_analysis.whale_grid_cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--whale-input" in completed.stdout
    assert "--whale-layer" in completed.stdout
    assert "--grid-input" in completed.stdout
    assert "--expected-grid-sha256" in completed.stdout
    assert "--output" in completed.stdout
    assert "--overwrite" in completed.stdout
    assert completed.stderr == ""


def test_whale_grid_cli_success_path_preserves_processing_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    events: list[str] = []
    started_at = datetime(2026, 8, 27, 12, tzinfo=UTC)
    config = object()
    source = object()
    target = object()
    dataset = object()

    def start() -> datetime:
        events.append("start")
        return started_at

    def load_config() -> object:
        events.append("config")
        return config

    def load_source(*_args: object, **_kwargs: object) -> object:
        events.append("source")
        return source

    def load_grid(*_args: object, **kwargs: object) -> object:
        events.append("grid")
        assert kwargs["expected_sha256"] == "a" * 64
        return target

    def transfer(*_args: object) -> object:
        events.append("transfer")
        return dataset

    def write(*_args: object, **kwargs: object) -> SimpleNamespace:
        events.append("write")
        assert kwargs["started_at"] == started_at
        assert kwargs["expected_grid_sha256"] == "a" * 64
        return SimpleNamespace(to_dict=lambda: {"status": "ok"})

    monkeypatch.setattr(whale_grid_cli, "_utc_now", start)
    monkeypatch.setattr(whale_grid_cli, "load_default_config", load_config)
    monkeypatch.setattr(whale_grid_cli, "load_whale_source", load_source)
    monkeypatch.setattr(whale_grid_cli, "load_target_grid", load_grid)
    monkeypatch.setattr(whale_grid_cli, "transfer_whale_density", transfer)
    monkeypatch.setattr(whale_grid_cli, "write_whale_grid", write)

    exit_code = whale_grid_cli.main(
        [
            "--whale-input",
            str(tmp_path / "source.gdb"),
            "--grid-input",
            str(tmp_path / "grid.parquet"),
            "--expected-grid-sha256",
            "a" * 64,
            "--output",
            str(tmp_path / "output.parquet"),
        ]
    )

    assert exit_code == 0
    assert events == ["start", "config", "grid", "source", "transfer", "write"]
    assert '"status": "ok"' in capsys.readouterr().out


def test_grid_checksum_failure_precedes_whale_source_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(whale_grid_cli, "load_default_config", lambda: object())

    def fail_grid(*_args: object, **_kwargs: object) -> object:
        raise WhaleGridInputError("synthetic invalid grid checksum")

    def unexpected_source(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("whale source must not load before grid validation")

    monkeypatch.setattr(whale_grid_cli, "load_target_grid", fail_grid)
    monkeypatch.setattr(whale_grid_cli, "load_whale_source", unexpected_source)

    exit_code = whale_grid_cli.main(
        [
            "--whale-input",
            str(tmp_path / "source.gdb"),
            "--grid-input",
            str(tmp_path / "grid.parquet"),
            "--output",
            str(tmp_path / "output.parquet"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "synthetic invalid grid checksum" in captured.err
    assert captured.out == ""
