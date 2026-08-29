from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from conftest import build_cleaned_bundle, synthetic_rows
from whale_vessel_analysis import multiday_ais
from whale_vessel_analysis.multiday_ais_cli import build_parser, main


def _roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    interim = tmp_path / "data" / "interim"
    raw = tmp_path / "data" / "raw"
    interim.mkdir(parents=True)
    raw.mkdir(parents=True)
    monkeypatch.setattr(multiday_ais, "_PROJECT_INTERIM_ROOT", interim.resolve())
    monkeypatch.setattr(multiday_ais, "_PROJECT_RAW_ROOT", raw.resolve())
    return interim, raw


def _at(utc_date: str, hour: int, minute: int) -> datetime:
    return datetime.fromisoformat(utc_date).replace(
        hour=hour, minute=minute, tzinfo=UTC
    )


def _bundles(tmp_path: Path) -> list[Path]:
    first = build_cleaned_bundle(
        tmp_path / "bundles" / "2024-07-01",
        [("123456789", _at("2024-07-01", 23, 59), 34.0, -118.0, "cargo")],
        run_id="ais-day1000000000000000000",
    )
    second = build_cleaned_bundle(
        tmp_path / "bundles" / "2024-07-02",
        [("123456789", _at("2024-07-02", 0, 1), 34.0, -117.99, "cargo")],
        run_id="ais-day2000000000000000000",
    )
    return [first, second]


def test_help_boundary_lists_every_subcommand(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["--help"])
    assert excinfo.value.code == 0
    printed = capsys.readouterr().out
    assert "record" in printed
    assert "status" in printed
    assert "scan" in printed


def test_record_status_and_scan_success_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "period" / "manifest.json"
    bundles = _bundles(tmp_path)

    exit_code = main(
        [
            "record",
            "--manifest",
            str(manifest_path),
            "--cleaned-bundle",
            str(bundles[0]),
            "--cleaned-bundle",
            str(bundles[1]),
        ]
    )
    recorded: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert [item["outcome"] for item in recorded["recorded_dates"]] == [
        "recorded",
        "recorded",
    ]
    assert recorded["period_input_readiness"]["missing_date_count"] == 151
    assert recorded["observational_completeness"]["status"] == "unverified"

    assert main(["status", "--manifest", str(manifest_path)]) == 3
    status: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert status["period_input_readiness"]["status"] == "not_ready"
    assert status["compatible_utc_dates"] == ["2024-07-01", "2024-07-02"]

    assert (
        main(
            [
                "scan",
                "--manifest",
                str(manifest_path),
                "--memory-limit",
                "512MB",
                "--temp-directory",
                str(interim / "duckdb-temp"),
                "--batch-size",
                "1",
            ]
        )
        == 3
    )
    scanned: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert scanned["observations"] == 2
    assert scanned["streamed"] == {"record_batches": 2, "rows": 2}
    assert scanned["continuity"]["cross_utc_date_pairs"] == 1
    assert scanned["continuity"]["pairs_lost_to_date_partitioning"] == 1
    assert scanned["relation"]["resources"]["memory_limit"] == "512MB"


def test_scan_requires_readiness_when_asked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"
    main(
        [
            "record",
            "--manifest",
            str(manifest_path),
            "--cleaned-bundle",
            str(_bundles(tmp_path)[0]),
        ]
    )
    capsys.readouterr()
    exit_code = main(
        [
            "scan",
            "--manifest",
            str(manifest_path),
            "--memory-limit",
            "512MB",
            "--temp-directory",
            str(interim / "duckdb-temp"),
            "--require-ready",
        ]
    )
    assert exit_code == 2
    assert "not ready" in capsys.readouterr().err


def test_record_reports_a_conflict_with_its_own_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"
    original = build_cleaned_bundle(
        tmp_path / "a", synthetic_rows("2024-08-15", seconds=(0,))
    )
    different = build_cleaned_bundle(
        tmp_path / "b",
        synthetic_rows("2024-08-15", seconds=(0, 60)),
        run_id="ais-other00000000000000000",
    )
    assert (
        main(
            [
                "record",
                "--manifest",
                str(manifest_path),
                "--cleaned-bundle",
                str(original),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "record",
                "--manifest",
                str(manifest_path),
                "--cleaned-bundle",
                str(different),
            ]
        )
        == 4
    )
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert payload["recorded_dates"][0]["outcome"] == "conflict"


def test_error_paths_return_exit_code_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interim, raw = _roots(tmp_path, monkeypatch)
    bundle = _bundles(tmp_path)[0]

    assert (
        main(
            [
                "record",
                "--manifest",
                str(raw / "m.json"),
                "--cleaned-bundle",
                str(bundle),
            ]
        )
        == 2
    )
    assert "under raw data" in capsys.readouterr().err

    assert (
        main(
            [
                "record",
                "--manifest",
                str(interim / "m.json"),
                "--cleaned-bundle",
                str(tmp_path / "does-not-exist"),
            ]
        )
        == 2
    )
    assert "does not exist" in capsys.readouterr().err

    assert main(["status", "--manifest", str(interim / "absent.json")]) == 2
    assert "does not exist" in capsys.readouterr().err

    main(
        [
            "record",
            "--manifest",
            str(interim / "m.json"),
            "--cleaned-bundle",
            str(bundle),
        ]
    )
    capsys.readouterr()
    assert (
        main(
            [
                "scan",
                "--manifest",
                str(interim / "m.json"),
                "--memory-limit",
                "plenty",
                "--temp-directory",
                str(interim / "duckdb-temp"),
            ]
        )
        == 2
    )
    assert "explicit size with a unit" in capsys.readouterr().err


def test_status_returns_zero_only_for_a_ready_period(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    manifest_path = interim / "manifest.json"
    arguments = ["record", "--manifest", str(manifest_path)]
    for index, utc_date in enumerate(multiday_ais.accepted_utc_dates()):
        bundle = build_cleaned_bundle(
            tmp_path / "all" / utc_date,
            synthetic_rows(utc_date),
            run_id=f"ais-{index:024d}",
        )
        arguments.extend(["--cleaned-bundle", str(bundle)])
    assert main(arguments) == 0
    capsys.readouterr()
    assert main(["status", "--manifest", str(manifest_path)]) == 0
    status: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert status["period_input_readiness"]["status"] == "ready"
    assert status["observational_completeness"]["status"] == "unverified"
    assert status["independent_transfer_completeness"]["status"] == "unverified"
