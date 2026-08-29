from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest

from conftest import build_cleaned_bundle
from whale_vessel_analysis import multiday_ais, multiday_ais_relation
from whale_vessel_analysis.ais_processing import CLEANED_FILENAME
from whale_vessel_analysis.multiday_ais import record_cleaned_days
from whale_vessel_analysis.multiday_ais_relation import (
    GLOBAL_ORDER_COLUMNS,
    MultiDayRelationError,
    RelationResources,
    open_period_relation,
    period_partitions,
)

FIXED_CLOCK = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def _clock() -> datetime:
    return FIXED_CLOCK


def _roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    interim = tmp_path / "data" / "interim"
    raw = tmp_path / "data" / "raw"
    interim.mkdir(parents=True)
    raw.mkdir(parents=True)
    monkeypatch.setattr(multiday_ais, "_PROJECT_INTERIM_ROOT", interim.resolve())
    monkeypatch.setattr(multiday_ais, "_PROJECT_RAW_ROOT", raw.resolve())
    return interim, raw


def _rows(batches: list[pa.RecordBatch]) -> list[tuple[str, int]]:
    """Read streamed batches without depending on a local tz database."""
    rows: list[tuple[str, int]] = []
    for batch in batches:
        mmsis = batch.column("mmsi").to_pylist()
        stamps = batch.column("observed_at_utc").cast(pa.int64()).to_pylist()
        rows.extend(zip(mmsis, stamps, strict=True))
    return rows


def _at(utc_date: str, hour: int, minute: int) -> datetime:
    day = datetime.fromisoformat(utc_date)
    return day.replace(hour=hour, minute=minute, tzinfo=UTC)


def _midnight_bundles(tmp_path: Path) -> list[Path]:
    """Two adjacent dates whose shared MMSI reports either side of midnight."""
    first = build_cleaned_bundle(
        tmp_path / "bundles" / "2024-07-01",
        [
            ("123456789", _at("2024-07-01", 23, 58), 34.0, -118.0, "cargo"),
            ("123456789", _at("2024-07-01", 23, 59), 34.0, -117.99, "cargo"),
            ("555555555", _at("2024-07-01", 12, 0), 33.0, -119.0, "tanker"),
        ],
        run_id="ais-day1000000000000000000",
    )
    second = build_cleaned_bundle(
        tmp_path / "bundles" / "2024-07-02",
        [
            ("123456789", _at("2024-07-02", 0, 1), 34.0, -117.98, "cargo"),
            ("123456789", _at("2024-07-02", 0, 2), 34.0, -117.97, "cargo"),
            ("999999999", _at("2024-07-02", 6, 0), 32.5, -120.0, "passenger"),
        ],
        run_id="ais-day2000000000000000000",
    )
    return [first, second]


def _manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundles: list[Path],
    *,
    name: str = "manifest.json",
) -> tuple[dict[str, Any], Path]:
    interim, _ = _roots(tmp_path, monkeypatch)
    update = record_cleaned_days(interim / name, bundles, clock=_clock)
    return dict(update.manifest), interim


def _resources(interim: Path) -> RelationResources:
    return RelationResources(
        memory_limit="512MB", temporary_directory=interim / "duckdb-temp", threads=2
    )


def test_relation_scans_partitions_and_orders_globally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, interim = _manifest(tmp_path, monkeypatch, _midnight_bundles(tmp_path))
    with open_period_relation(manifest, _resources(interim)) as relation:
        assert relation.count_observations() == 6
        assert relation.partition_row_counts() == {
            "2024-07-01": 3,
            "2024-07-02": 3,
        }
        reader = relation.ordered_batches(batch_size=2)
        assert isinstance(reader, pa.RecordBatchReader)
        batches = list(reader)
        assert len(batches) >= 3
        rows = _rows(batches)
        assert [mmsi for mmsi, _ in rows] == [
            "123456789",
            "123456789",
            "123456789",
            "123456789",
            "555555555",
            "999999999",
        ]
        timestamps = [timestamp for mmsi, timestamp in rows if mmsi == "123456789"]
        assert timestamps == sorted(timestamps)
        assert relation.ordered_query().endswith(", ".join(GLOBAL_ORDER_COLUMNS))


def test_cross_midnight_continuity_is_preserved_for_one_mmsi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, interim = _manifest(tmp_path, monkeypatch, _midnight_bundles(tmp_path))
    with open_period_relation(manifest, _resources(interim)) as relation:
        pairs = relation.cross_date_adjacency()
        assert len(pairs) == 1
        pair = pairs[0]
        assert pair.mmsi == "123456789"
        assert pair.from_utc_date == "2024-07-01"
        assert pair.to_utc_date == "2024-07-02"
        assert pair.from_observed_at_utc == "2024-07-01T23:59:00Z"
        assert pair.to_observed_at_utc == "2024-07-02T00:01:00Z"
        assert pair.elapsed_seconds == 120.0


def test_no_artificial_daily_partition_break(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, interim = _manifest(tmp_path, monkeypatch, _midnight_bundles(tmp_path))
    with open_period_relation(manifest, _resources(interim)) as relation:
        summary = relation.continuity_summary()
    assert summary["whole_period_consecutive_pairs"] == 3
    assert summary["date_partitioned_consecutive_pairs"] == 2
    assert summary["pairs_lost_to_date_partitioning"] == 1
    assert summary["cross_utc_date_pairs"] == 1
    assert summary["mmsi_with_cross_utc_date_pairs"] == 1


def test_ordering_is_stable_regardless_of_manifest_input_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundles = _midnight_bundles(tmp_path)
    interim, _ = _roots(tmp_path, monkeypatch)
    forward = record_cleaned_days(interim / "forward.json", bundles, clock=_clock)
    reverse = record_cleaned_days(
        interim / "reverse.json", list(reversed(bundles)), clock=_clock
    )
    resources = _resources(interim)

    def streamed(manifest: dict[str, Any]) -> list[tuple[str, int]]:
        with open_period_relation(manifest, resources) as relation:
            return _rows(list(relation.ordered_batches(batch_size=2)))

    assert streamed(dict(forward.manifest)) == streamed(dict(reverse.manifest))
    ordered = [partition.utc_date for partition in period_partitions(forward.manifest)]
    assert ordered == ["2024-07-01", "2024-07-02"]
    assert period_partitions(forward.manifest) == period_partitions(reverse.manifest)


def test_scanning_is_streamed_and_never_materialized_in_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, interim = _manifest(tmp_path, monkeypatch, _midnight_bundles(tmp_path))
    with open_period_relation(manifest, _resources(interim)) as relation:
        assert relation.count_observations() == 6
        batches = list(relation.ordered_batches(batch_size=1))
    assert len(batches) == 6
    assert all(batch.num_rows == 1 for batch in batches)

    source = Path(multiday_ais_relation.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "import pandas",
        "import polars",
        "fetchdf",
        "fetch_df",
        ".df()",
        ".pl()",
        "fetch_arrow_table",
        "to_pandas",
        "arrow()",
    ):
        assert forbidden not in source
    assert "to_arrow_reader" in source


def test_relation_settings_apply_the_explicit_memory_and_spill_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, interim = _manifest(tmp_path, monkeypatch, _midnight_bundles(tmp_path))
    resources = _resources(interim)
    with open_period_relation(manifest, resources) as relation:
        settings = relation.effective_settings()
        assert settings["threads"] == 2
        assert str(relation.spill_directory) == str(settings["temp_directory"])
        assert relation.spill_directory.is_dir()
        assert relation.spill_directory.is_relative_to(resources.temporary_directory)
        assert settings["memory_limit"] != ""
        payload = relation.to_dict()
        spill = relation.spill_directory
    assert payload["partition_count"] == 2
    assert not spill.exists()


def test_memory_limit_and_thread_configuration_are_validated(tmp_path: Path) -> None:
    interim = tmp_path / "data" / "interim"
    interim.mkdir(parents=True)
    with pytest.raises(MultiDayRelationError, match="explicit size with a unit"):
        RelationResources(memory_limit="lots", temporary_directory=interim)
    with pytest.raises(MultiDayRelationError, match="explicit size with a unit"):
        RelationResources(memory_limit="2048", temporary_directory=interim)
    with pytest.raises(MultiDayRelationError, match="greater than zero"):
        RelationResources(memory_limit="0GB", temporary_directory=interim)
    with pytest.raises(MultiDayRelationError, match="at least one"):
        RelationResources(memory_limit="1GB", temporary_directory=interim, threads=0)


def test_spill_directory_must_be_ignored_local_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, raw = _roots(tmp_path, monkeypatch)
    with pytest.raises(multiday_ais.MultiDayAISInputError, match="under raw data"):
        RelationResources(memory_limit="1GB", temporary_directory=raw / "spill")
    with pytest.raises(multiday_ais.MultiDayAISInputError, match="data/interim"):
        RelationResources(memory_limit="1GB", temporary_directory=tmp_path / "spill")
    file_path = interim / "not-a-directory"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(multiday_ais.MultiDayAISInputError, match="not a directory"):
        RelationResources(memory_limit="1GB", temporary_directory=file_path)


def test_partition_checksum_change_after_recording_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, interim = _manifest(tmp_path, monkeypatch, _midnight_bundles(tmp_path))
    cleaned = tmp_path / "bundles" / "2024-07-02" / CLEANED_FILENAME
    cleaned.write_bytes(cleaned.read_bytes() + b"\x00")
    with (
        pytest.raises(MultiDayRelationError, match="no longer matches its recorded"),
        open_period_relation(manifest, _resources(interim)),
    ):
        pass


def test_missing_partition_file_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, interim = _manifest(tmp_path, monkeypatch, _midnight_bundles(tmp_path))
    (tmp_path / "bundles" / "2024-07-02" / CLEANED_FILENAME).unlink()
    with (
        pytest.raises(MultiDayRelationError, match="recorded cleaned Parquet is"),
        open_period_relation(manifest, _resources(interim)),
    ):
        pass


def test_incomplete_period_is_refused_when_readiness_is_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, interim = _manifest(tmp_path, monkeypatch, _midnight_bundles(tmp_path))
    with (
        pytest.raises(MultiDayRelationError, match="not ready"),
        open_period_relation(manifest, _resources(interim), require_ready=True),
    ):
        pass


def test_manifest_without_any_compatible_date_cannot_be_scanned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim, _ = _roots(tmp_path, monkeypatch)
    empty = multiday_ais.empty_period_manifest()
    with (
        pytest.raises(MultiDayRelationError, match="no compatible date"),
        open_period_relation(empty, _resources(interim)),
    ):
        pass
