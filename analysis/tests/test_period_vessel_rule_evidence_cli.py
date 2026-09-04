from __future__ import annotations

import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from whale_vessel_analysis import period_vessel_rule_evidence_cli
from whale_vessel_analysis.period_vessel_rule_evidence import (
    VESSEL_LENGTH_TREATMENT,
    PeriodVesselRuleEvidenceError,
)


def _arguments(tmp_path: Path) -> list[str]:
    return [
        "--manifest",
        str(tmp_path / "manifest.json"),
        "--output-dir",
        str(tmp_path / "data" / "interim" / "evidence"),
        "--maximum-gap-seconds",
        "300",
        "--maximum-gap-seconds",
        "1800",
        "--implied-speed-ceiling-knots",
        "30",
        "--implied-speed-ceiling-knots",
        "50",
        "--vessel-length-treatment",
        VESSEL_LENGTH_TREATMENT,
        "--memory-limit",
        "256MB",
        "--temp-directory",
        str(tmp_path / "data" / "interim" / "spill"),
    ]


def test_module_help_names_every_explicit_boundary() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "whale_vessel_analysis.period_vessel_rule_evidence_cli",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    for option in (
        "--manifest",
        "--output-dir",
        "--maximum-gap-seconds",
        "--implied-speed-ceiling-knots",
        "--vessel-length-treatment",
        "--allow-incomplete-non-production",
        "--memory-limit",
        "--temp-directory",
        "--batch-size",
        "--overwrite",
    ):
        assert option in completed.stdout
    assert completed.stderr == ""


def test_cli_has_no_hidden_candidate_or_length_defaults(tmp_path: Path) -> None:
    parser = period_vessel_rule_evidence_cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--manifest",
                str(tmp_path / "manifest.json"),
                "--output-dir",
                str(tmp_path / "output"),
                "--memory-limit",
                "256MB",
                "--temp-directory",
                str(tmp_path / "spill"),
            ]
        )


def test_cli_success_passes_ready_requirement_and_resources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    manifest = {
        "period_input_id": "multiday-ais-synthetic",
        "period_input_readiness": {"status": "ready"},
        "independent_transfer_completeness": {"status": "unverified"},
        "observational_completeness": {"status": "unverified"},
    }
    observed: dict[str, Any] = {}
    monkeypatch.setattr(
        period_vessel_rule_evidence_cli, "load_period_manifest", lambda _path: manifest
    )
    monkeypatch.setattr(
        period_vessel_rule_evidence_cli, "sha256_file", lambda _path: "a" * 64
    )
    monkeypatch.setattr(
        period_vessel_rule_evidence_cli, "period_partitions", lambda _manifest: ()
    )
    monkeypatch.setattr(
        period_vessel_rule_evidence_cli,
        "validate_evidence_output_target",
        lambda *args, **kwargs: observed.setdefault("preflight", (args, kwargs)),
    )
    monkeypatch.setattr(
        period_vessel_rule_evidence_cli,
        "RelationResources",
        lambda **kwargs: observed.setdefault("resources", SimpleNamespace(**kwargs)),
    )

    @contextmanager
    def relation_context(*args: object, **kwargs: object) -> Any:
        observed["relation"] = (args, kwargs)
        yield object()

    monkeypatch.setattr(
        period_vessel_rule_evidence_cli, "open_period_relation", relation_context
    )
    monkeypatch.setattr(
        period_vessel_rule_evidence_cli,
        "build_period_vessel_rule_evidence",
        lambda *args, **kwargs: observed.setdefault("build", (args, kwargs))
        and object(),
    )
    monkeypatch.setattr(
        period_vessel_rule_evidence_cli,
        "write_period_vessel_rule_evidence",
        lambda *args, **kwargs: SimpleNamespace(to_dict=lambda: {"status": "ok"}),
    )

    assert period_vessel_rule_evidence_cli.main(_arguments(tmp_path)) == 0
    assert observed["relation"][1]["require_ready"] is True
    assert observed["resources"].memory_limit == "256MB"
    parameters = observed["build"][0][2]
    assert parameters.maximum_gap_seconds == (300.0, 1800.0)
    assert parameters.implied_speed_ceiling_knots == (30.0, 50.0)
    assert parameters.allow_incomplete_non_production is False
    assert '"status": "ok"' in capsys.readouterr().out


def test_cli_failure_returns_two_without_success_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        period_vessel_rule_evidence_cli,
        "load_period_manifest",
        lambda _path: (_ for _ in ()).throw(
            PeriodVesselRuleEvidenceError("synthetic refusal")
        ),
    )
    assert period_vessel_rule_evidence_cli.main(_arguments(tmp_path)) == 2
    captured = capsys.readouterr()
    assert "synthetic refusal" in captured.err
    assert captured.out == ""
