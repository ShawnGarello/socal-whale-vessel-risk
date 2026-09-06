"""Boundary tests for the whale display-export command."""

from __future__ import annotations

import json
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from whale_display_fixtures import _cell, _prepare
from whale_vessel_analysis.whale_display_export import (
    APPROVED_OUTPUT_ROOTS,
    MANIFEST_SUFFIX,
    WHALE_DISPLAY_EXPORT_CONTRACT,
)
from whale_vessel_analysis.whale_display_export_cli import build_parser, main


@pytest.fixture
def approved_output_dir() -> Iterator[Path]:
    """A fresh directory under a real approved root, removed afterwards.

    The command deliberately has no seam for widening the approved roots, so a
    CLI test that expects a successful write has to use one of them. These live
    under the ignored `data/interim` root.
    """
    root = next(root for root in APPROVED_OUTPUT_ROOTS if root.name == "interim")
    directory = root / f"pytest-display-export-{uuid.uuid4().hex}"
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_parser_requires_source_checksum_and_output() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--source", "whale.parquet"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--source", "whale.parquet", "--output", "whale.geojson"])

    args = parser.parse_args(
        [
            "--source",
            "whale.parquet",
            "--expected-source-sha256",
            "a" * 64,
            "--output",
            "whale.geojson",
        ]
    )
    assert args.source == Path("whale.parquet")
    assert args.output == Path("whale.geojson")
    assert args.overwrite is False


def test_exports_and_prints_the_output_identity(
    tmp_path: Path, approved_output_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0), _cell(0, 1)])
    output = approved_output_dir / "blue-whale-density.geojson"

    exit_code = main(
        [
            "--source",
            str(source_path),
            "--expected-source-sha256",
            digest,
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["contract"] == WHALE_DISPLAY_EXPORT_CONTRACT
    assert summary["diagnostics"]["feature_count"] == 2
    assert summary["output"]["bytes"] == output.stat().st_size
    assert output.with_name(output.name + MANIFEST_SUFFIX).is_file()


def test_reports_a_checksum_mismatch_without_writing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_path, _digest = _prepare(tmp_path, [_cell(0, 0)])
    output = tmp_path / "out" / "blue-whale-density.geojson"

    exit_code = main(
        [
            "--source",
            str(source_path),
            "--expected-source-sha256",
            "f" * 64,
            "--output",
            str(output),
        ]
    )

    assert exit_code == 2
    assert "checksum mismatch" in capsys.readouterr().err
    assert not output.exists()
    assert not output.parent.exists()


def test_refuses_an_existing_export_without_overwrite(
    tmp_path: Path, approved_output_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    output = approved_output_dir / "blue-whale-density.geojson"
    argv = [
        "--source",
        str(source_path),
        "--expected-source-sha256",
        digest,
        "--output",
        str(output),
    ]
    assert main(argv) == 0
    capsys.readouterr()

    assert main(argv) == 2
    assert "already exists" in capsys.readouterr().err
    assert main([*argv, "--overwrite"]) == 0


def test_refuses_a_non_geojson_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])

    exit_code = main(
        [
            "--source",
            str(source_path),
            "--expected-source-sha256",
            digest,
            "--output",
            str(tmp_path / "out" / "blue-whale-density.json"),
        ]
    )

    assert exit_code == 2
    assert ".geojson" in capsys.readouterr().err


def test_refuses_a_raw_data_destination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    project_root = Path(__file__).resolve().parents[2]

    exit_code = main(
        [
            "--source",
            str(source_path),
            "--expected-source-sha256",
            digest,
            "--output",
            str(project_root / "data" / "raw" / "blue-whale-density.geojson"),
        ]
    )

    assert exit_code == 2
    assert "raw data" in capsys.readouterr().err


def test_refuses_a_destination_outside_the_approved_roots(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The command has no seam for widening the approved roots."""
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    output = tmp_path / "out" / "blue-whale-density.geojson"

    exit_code = main(
        [
            "--source",
            str(source_path),
            "--expected-source-sha256",
            digest,
            "--output",
            str(output),
        ]
    )

    assert exit_code == 2
    assert "approved roots" in capsys.readouterr().err
    assert not output.exists()


def test_refuses_another_worktree_raw_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A sibling checkout's raw data is refused by shape, not by absolute path."""
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    sibling_raw = tmp_path / "another-worktree" / "data" / "raw" / "leak.geojson"

    exit_code = main(
        [
            "--source",
            str(source_path),
            "--expected-source-sha256",
            digest,
            "--output",
            str(sibling_raw),
        ]
    )

    assert exit_code == 2
    assert "raw data" in capsys.readouterr().err
    assert not sibling_raw.exists()
