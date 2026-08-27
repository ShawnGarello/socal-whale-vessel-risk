from __future__ import annotations

from pathlib import Path

import pytest

from whale_vessel_analysis.benchmark import (
    GroupResult,
    _benchmark,
    _equivalent,
)


def _group(**updates: object) -> GroupResult:
    group: GroupResult = {
        "vessel_type": 70,
        "row_count": 3,
        "distinct_mmsi": 2,
        "valid_speed_rows": 2,
        "mean_sog_knots": 12.5,
        "mean_length_m": 100.0,
    }
    group.update(updates)  # type: ignore[typeddict-item]
    return group


def test_benchmark_results_are_equivalent_when_all_measures_match() -> None:
    assert _equivalent([_group()], [_group(mean_sog_knots=12.5000000000001)])


def test_benchmark_detects_group_mismatch() -> None:
    assert not _equivalent([_group()], [_group(row_count=4)])


def test_benchmark_rejects_missing_input(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        _benchmark(tmp_path / "missing.csv", runs=1, warmups=0)


@pytest.mark.parametrize(
    ("runs", "warmups"),
    [(0, 0), (1, -1)],
)
def test_benchmark_rejects_invalid_run_counts(
    tmp_path: Path, runs: int, warmups: int
) -> None:
    path = tmp_path / "sample.csv"
    path.write_text("header\n", encoding="utf-8")

    with pytest.raises(ValueError, match="runs must be at least 1"):
        _benchmark(path, runs=runs, warmups=warmups)
