from __future__ import annotations

import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from whale_vessel_analysis import vessel_grid_cli
from whale_vessel_analysis.vessel_grid import (
    ALLOW_INCOMPLETE_PERIOD,
    EDGE_TREATMENT,
    SUPPORT_TREATMENT,
    VesselGridError,
)


def test_module_help_requires_every_methodological_choice() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "whale_vessel_analysis.vessel_grid_cli",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    for option in (
        "--manifest",
        "--grid-input",
        "--output-dir",
        "--maximum-gap-seconds",
        "--implied-speed-ceiling-knots",
        "--period-readiness-treatment",
        "--edge-treatment",
        "--support-treatment",
        "--memory-limit",
        "--temp-directory",
        "--overwrite",
    ):
        assert option in completed.stdout
    assert "--minimum-vessel-length" not in completed.stdout
    assert completed.stderr == ""


def test_cli_passes_explicit_parameters_and_bounded_resources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    manifest = {
        "period_input_id": "multiday-ais-synthetic",
        "period_input_readiness": {"status": "not_ready"},
        "observational_completeness": {"status": "unverified"},
    }
    config = SimpleNamespace(digest=lambda: "c" * 64)
    relation = object()
    grid = object()
    dataset = object()
    observed: dict[str, Any] = {}
    monkeypatch.setattr(vessel_grid_cli, "load_default_config", lambda: config)
    monkeypatch.setattr(vessel_grid_cli, "load_period_manifest", lambda _path: manifest)
    monkeypatch.setattr(vessel_grid_cli, "sha256_file", lambda _path: "m" * 64)
    monkeypatch.setattr(
        vessel_grid_cli,
        "RelationResources",
        lambda **kwargs: observed.setdefault("resources", kwargs),
    )
    monkeypatch.setattr(
        vessel_grid_cli,
        "load_target_grid",
        lambda *args, **kwargs: observed.setdefault("grid_load", (args, kwargs))
        and grid,
    )

    @contextmanager
    def relation_context(*args: object, **kwargs: object) -> Any:
        observed["relation_open"] = (args, kwargs)
        yield relation

    monkeypatch.setattr(vessel_grid_cli, "open_period_relation", relation_context)

    def aggregate(*args: object, **kwargs: object) -> object:
        observed["aggregate"] = (args, kwargs)
        return dataset

    monkeypatch.setattr(vessel_grid_cli, "aggregate_vessel_grid", aggregate)

    def write(*args: object, **kwargs: object) -> SimpleNamespace:
        observed["write"] = (args, kwargs)
        return SimpleNamespace(to_dict=lambda: {"status": "ok"})

    monkeypatch.setattr(vessel_grid_cli, "write_vessel_grid", write)
    output = tmp_path / "data" / "derived" / "candidate"
    exit_code = vessel_grid_cli.main(
        [
            "--manifest",
            str(manifest_path),
            "--grid-input",
            str(tmp_path / "grid.parquet"),
            "--expected-grid-sha256",
            "a" * 64,
            "--output-dir",
            str(output),
            "--maximum-gap-seconds",
            "300",
            "--implied-speed-ceiling-knots",
            "30",
            "--period-readiness-treatment",
            ALLOW_INCOMPLETE_PERIOD,
            "--edge-treatment",
            EDGE_TREATMENT,
            "--support-treatment",
            SUPPORT_TREATMENT,
            "--memory-limit",
            "512MB",
            "--temp-directory",
            str(tmp_path / "data" / "interim" / "spill"),
            "--threads",
            "2",
            "--batch-size",
            "7",
            "--overwrite",
        ]
    )

    assert exit_code == 0
    parameters = observed["aggregate"][0][3]
    assert parameters.maximum_gap_seconds == 300
    assert parameters.implied_speed_ceiling_knots == 30
    assert parameters.period_readiness_treatment == ALLOW_INCOMPLETE_PERIOD
    assert parameters.edge_treatment == EDGE_TREATMENT
    assert parameters.support_treatment == SUPPORT_TREATMENT
    assert observed["aggregate"][1]["batch_size"] == 7
    assert observed["relation_open"][1]["require_ready"] is False
    assert observed["resources"] == {
        "memory_limit": "512MB",
        "temporary_directory": tmp_path / "data" / "interim" / "spill",
        "threads": 2,
    }
    assert observed["write"][0][1] == output
    assert observed["write"][1]["overwrite"] is True
    captured = capsys.readouterr()
    assert '"status": "ok"' in captured.out
    assert captured.err == ""


def test_cli_has_no_hidden_methodological_defaults(tmp_path: Path) -> None:
    parser = vessel_grid_cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--manifest",
                str(tmp_path / "manifest.json"),
                "--grid-input",
                str(tmp_path / "grid.parquet"),
                "--output-dir",
                str(tmp_path / "output"),
                "--memory-limit",
                "1GB",
                "--temp-directory",
                str(tmp_path / "spill"),
            ]
        )


def test_cli_returns_error_exit_without_partial_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        vessel_grid_cli,
        "load_period_manifest",
        lambda _path: (_ for _ in ()).throw(VesselGridError("synthetic refusal")),
    )
    exit_code = vessel_grid_cli.main(
        [
            "--manifest",
            str(manifest_path),
            "--grid-input",
            str(tmp_path / "grid.parquet"),
            "--output-dir",
            str(tmp_path / "data" / "derived" / "candidate"),
            "--maximum-gap-seconds",
            "300",
            "--implied-speed-ceiling-knots",
            "30",
            "--period-readiness-treatment",
            ALLOW_INCOMPLETE_PERIOD,
            "--edge-treatment",
            EDGE_TREATMENT,
            "--support-treatment",
            SUPPORT_TREATMENT,
            "--memory-limit",
            "1GB",
            "--temp-directory",
            str(tmp_path / "data" / "interim" / "spill"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "synthetic refusal" in captured.err
    assert captured.out == ""
