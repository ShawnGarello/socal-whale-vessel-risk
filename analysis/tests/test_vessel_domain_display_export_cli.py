"""CLI checks for the vessel/domain display boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vessel_domain_display_fixtures import prepare_sources
from whale_vessel_analysis.vessel_domain_display_export_cli import main


def _arguments(tmp_path: Path) -> tuple[list[str], Path]:
    (
        vessel,
        vessel_sha,
        quality,
        quality_sha,
        domain,
        domain_sha,
        report,
        report_sha,
    ) = prepare_sources(tmp_path)
    output = Path(__file__).resolve().parents[2] / "data/interim/test-vessel-domain-cli"
    return (
        [
            "--vessel-source",
            str(vessel),
            "--expected-vessel-sha256",
            vessel_sha,
            "--vessel-quality-report",
            str(quality),
            "--expected-vessel-quality-report-sha256",
            quality_sha,
            "--domain-source",
            str(domain),
            "--expected-domain-sha256",
            domain_sha,
            "--domain-report",
            str(report),
            "--expected-domain-report-sha256",
            report_sha,
            "--output-directory",
            str(output),
        ],
        output,
    )


def test_cli_exports_bundle_and_prints_only_output_identities(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args, output = _arguments(tmp_path)
    try:
        assert main(args) == 0
        summary = json.loads(capsys.readouterr().out)
        assert summary["contract"] == "vessel_domain_display_export_bundle_v1"
        assert len(summary["outputs"]) == 2
        assert str(tmp_path) not in json.dumps(summary)
    finally:
        if output.exists():
            for child in output.iterdir():
                child.unlink()
            output.rmdir()


def test_cli_rejects_checksum_mismatch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args, _output = _arguments(tmp_path)
    checksum_index = args.index("--expected-vessel-sha256") + 1
    args[checksum_index] = "0" * 64
    assert main(args) == 2
    assert "checksum mismatch" in capsys.readouterr().err
