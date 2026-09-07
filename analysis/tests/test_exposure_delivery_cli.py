"""CLI boundary tests for exposure display and application results."""

from __future__ import annotations

import json
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from test_exposure_delivery import _make_bundle
from whale_vessel_analysis.exposure_delivery_cli import build_parser, main


@pytest.fixture
def approved_output_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parents[2] / "data" / "interim"
    output = root / f"pytest-exposure-delivery-cli-{uuid.uuid4().hex}"
    try:
        yield output
    finally:
        shutil.rmtree(output, ignore_errors=True)


def _argv(bundle: Path, hashes: dict[str, str], output: Path) -> list[str]:
    return [
        "--bundle",
        str(bundle),
        "--expected-5km-sha256",
        hashes["5km"],
        "--expected-10km-sha256",
        hashes["10km"],
        "--expected-report-sha256",
        hashes["report"],
        "--display-output",
        str(output / "relative-exposure.geojson"),
        "--results-output",
        str(output / "exposure-results.v1.json"),
        "--generated-at-utc",
        "2026-09-06T22:00:00Z",
    ]


def test_parser_requires_all_sources_destinations_and_timestamp() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--bundle", "bundle"])


def test_cli_writes_all_contracts_and_prints_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approved_output_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    assert main(_argv(bundle, hashes, approved_output_dir)) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["display_contract"] == "relative_exposure_display_v1"
    assert output["results_contract"] == "relative_exposure_application_results_v1"
    assert output["results"]["results_id"].startswith("exposure-results-")
    assert (approved_output_dir / "relative-exposure.geojson").is_file()
    assert (approved_output_dir / "relative-exposure.geojson.manifest.json").is_file()
    assert (approved_output_dir / "exposure-results.v1.json").is_file()


def test_cli_rejects_wrong_checksum_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approved_output_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    hashes["report"] = "f" * 64
    assert main(_argv(bundle, hashes, approved_output_dir)) == 2
    assert "checksum mismatch" in capsys.readouterr().err
    assert not approved_output_dir.exists()


def test_cli_rejects_non_utc_delivery_timestamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approved_output_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    argv = _argv(bundle, hashes, approved_output_dir)
    argv[-1] = "2026-09-06T22:00:00-07:00"
    assert main(argv) == 2
    assert "must be UTC" in capsys.readouterr().err
    assert not approved_output_dir.exists()
