"""Evidence benchmark for selecting the large-tabular AIS engine.

This module is development evidence, not an analytical processing step. It
reads an explicitly supplied AIS CSV and emits measurements to standard output;
it never writes data or benchmark results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

MAP_LON_MIN = -122.0
MAP_LON_MAX = -117.0
MAP_LAT_MIN = 32.0
MAP_LAT_MAX = 35.0
SOG_MISSING_SENTINEL = 102.3

EngineName = Literal["duckdb", "polars"]


class GroupResult(TypedDict):
    """Normalized result for one vessel-type code."""

    vessel_type: int | None
    row_count: int
    distinct_mmsi: int
    valid_speed_rows: int
    mean_sog_knots: float | None
    mean_length_m: float | None


class WorkerResult(TypedDict):
    """One isolated engine measurement."""

    engine: EngineName
    elapsed_seconds: float
    initial_rss_mib: float
    peak_rss_mib: float
    rss_increase_mib: float
    filtered_rows: int
    groups: list[GroupResult]


class RunMeasurement(TypedDict):
    """Reported timing and memory measurement without repeated group detail."""

    elapsed_seconds: float
    initial_rss_mib: float
    peak_rss_mib: float
    rss_increase_mib: float
    filtered_rows: int


class EngineSummary(TypedDict):
    """Measurements summarized across repeated isolated runs."""

    runs: list[RunMeasurement]
    median_elapsed_seconds: float
    median_peak_rss_mib: float
    median_rss_increase_mib: float


class _MemorySample(TypedDict):
    initial_rss_mib: float
    peak_rss_mib: float
    rss_increase_mib: float


@contextmanager
def _sample_memory() -> Iterator[Callable[[], _MemorySample]]:
    """Sample process RSS at short intervals during one operation."""
    import psutil

    process = psutil.Process()
    initial_rss = process.memory_info().rss
    peak_rss = initial_rss
    stop = threading.Event()

    def monitor() -> None:
        nonlocal peak_rss
        while not stop.wait(0.005):
            peak_rss = max(peak_rss, process.memory_info().rss)

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()

    def measurement() -> _MemorySample:
        current_rss = process.memory_info().rss
        observed_peak = max(peak_rss, current_rss)
        mib = 1024 * 1024
        return {
            "initial_rss_mib": initial_rss / mib,
            "peak_rss_mib": observed_peak / mib,
            "rss_increase_mib": (observed_peak - initial_rss) / mib,
        }

    try:
        yield measurement
    finally:
        stop.set()
        thread.join()


def _group_result(
    vessel_type: object,
    row_count: object,
    distinct_mmsi: object,
    valid_speed_rows: object,
    mean_sog_knots: object,
    mean_length_m: object,
) -> GroupResult:
    return {
        "vessel_type": None if vessel_type is None else int(cast(int, vessel_type)),
        "row_count": int(cast(int, row_count)),
        "distinct_mmsi": int(cast(int, distinct_mmsi)),
        "valid_speed_rows": int(cast(int, valid_speed_rows)),
        "mean_sog_knots": (
            None if mean_sog_knots is None else float(cast(float, mean_sog_knots))
        ),
        "mean_length_m": (
            None if mean_length_m is None else float(cast(float, mean_length_m))
        ),
    }


def _run_duckdb(input_path: Path) -> list[GroupResult]:
    import duckdb

    query = """
        WITH parsed AS (
            SELECT
                MMSI,
                try_strptime(BaseDateTime, '%Y-%m-%dT%H:%M:%S') AS observed_at,
                try_cast(LAT AS DOUBLE) AS latitude,
                try_cast(LON AS DOUBLE) AS longitude,
                try_cast(SOG AS DOUBLE) AS sog_knots,
                try_cast(VesselType AS INTEGER) AS vessel_type,
                try_cast(Length AS DOUBLE) AS length_m
            FROM read_csv(?, header = true, all_varchar = true)
        ),
        filtered AS (
            SELECT
                MMSI,
                vessel_type,
                CASE WHEN sog_knots = 102.3 THEN NULL ELSE sog_knots END
                    AS valid_sog_knots,
                length_m
            FROM parsed
            WHERE observed_at IS NOT NULL
              AND longitude BETWEEN -122.0 AND -117.0
              AND latitude BETWEEN 32.0 AND 35.0
        )
        SELECT
            vessel_type,
            count(*) AS row_count,
            count(DISTINCT MMSI) AS distinct_mmsi,
            count(valid_sog_knots) AS valid_speed_rows,
            avg(valid_sog_knots) AS mean_sog_knots,
            avg(length_m) AS mean_length_m
        FROM filtered
        GROUP BY vessel_type
        ORDER BY vessel_type NULLS LAST
    """
    connection = duckdb.connect()
    try:
        rows = connection.execute(query, [str(input_path)]).fetchall()
    finally:
        connection.close()
    return [_group_result(*row) for row in rows]


def _run_polars(input_path: Path) -> list[GroupResult]:
    import polars as pl

    columns = [
        "MMSI",
        "BaseDateTime",
        "LAT",
        "LON",
        "SOG",
        "VesselType",
        "Length",
    ]
    strings = {column: pl.String for column in columns}
    parsed = (
        pl.scan_csv(input_path, schema_overrides=strings)
        .select(columns)
        .with_columns(
            pl.col("BaseDateTime")
            .str.to_datetime(format="%Y-%m-%dT%H:%M:%S", strict=False)
            .alias("observed_at"),
            pl.col("LAT").cast(pl.Float64, strict=False).alias("latitude"),
            pl.col("LON").cast(pl.Float64, strict=False).alias("longitude"),
            pl.col("SOG").cast(pl.Float64, strict=False).alias("sog_knots"),
            pl.col("VesselType").cast(pl.Int32, strict=False).alias("vessel_type"),
            pl.col("Length").cast(pl.Float64, strict=False).alias("length_m"),
        )
        .filter(
            pl.col("observed_at").is_not_null()
            & pl.col("longitude").is_between(MAP_LON_MIN, MAP_LON_MAX)
            & pl.col("latitude").is_between(MAP_LAT_MIN, MAP_LAT_MAX)
        )
        .with_columns(
            pl.when(pl.col("sog_knots") == SOG_MISSING_SENTINEL)
            .then(None)
            .otherwise(pl.col("sog_knots"))
            .alias("valid_sog_knots")
        )
    )
    grouped = (
        parsed.group_by("vessel_type")
        .agg(
            pl.len().alias("row_count"),
            pl.col("MMSI").n_unique().alias("distinct_mmsi"),
            pl.col("valid_sog_knots").count().alias("valid_speed_rows"),
            pl.col("valid_sog_knots").mean().alias("mean_sog_knots"),
            pl.col("length_m").mean().alias("mean_length_m"),
        )
        .sort("vessel_type", nulls_last=True)
        .collect(engine="streaming")
    )
    return [
        _group_result(
            row["vessel_type"],
            row["row_count"],
            row["distinct_mmsi"],
            row["valid_speed_rows"],
            row["mean_sog_knots"],
            row["mean_length_m"],
        )
        for row in grouped.iter_rows(named=True)
    ]


def _run_worker(engine: EngineName, input_path: Path) -> WorkerResult:
    operation = _run_duckdb if engine == "duckdb" else _run_polars
    with _sample_memory() as memory:
        started = time.perf_counter()
        groups = operation(input_path)
        elapsed = time.perf_counter() - started
        memory_result = memory()
    return {
        "engine": engine,
        "elapsed_seconds": elapsed,
        **memory_result,
        "filtered_rows": sum(group["row_count"] for group in groups),
        "groups": groups,
    }


def _parse_worker_result(raw: str) -> WorkerResult:
    return cast(WorkerResult, json.loads(raw))


def _invoke_worker(engine: EngineName, input_path: Path) -> WorkerResult:
    command = [
        sys.executable,
        "-m",
        "whale_vessel_analysis.benchmark",
        "--worker",
        engine,
        "--input",
        str(input_path),
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return _parse_worker_result(completed.stdout)


def _same_optional_float(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-9)


def _equivalent(left: list[GroupResult], right: list[GroupResult]) -> bool:
    if len(left) != len(right):
        return False
    for left_group, right_group in zip(left, right, strict=True):
        if (
            left_group["vessel_type"] != right_group["vessel_type"]
            or left_group["row_count"] != right_group["row_count"]
            or left_group["distinct_mmsi"] != right_group["distinct_mmsi"]
            or left_group["valid_speed_rows"] != right_group["valid_speed_rows"]
            or not _same_optional_float(
                left_group["mean_sog_knots"], right_group["mean_sog_knots"]
            )
            or not _same_optional_float(
                left_group["mean_length_m"], right_group["mean_length_m"]
            )
        ):
            return False
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_count(path: Path) -> int:
    with path.open("rb") as source:
        lines = sum(1 for _ in source)
    return max(0, lines - 1)


def _summary(runs: list[WorkerResult]) -> EngineSummary:
    return {
        "runs": [
            {
                "elapsed_seconds": run["elapsed_seconds"],
                "initial_rss_mib": run["initial_rss_mib"],
                "peak_rss_mib": run["peak_rss_mib"],
                "rss_increase_mib": run["rss_increase_mib"],
                "filtered_rows": run["filtered_rows"],
            }
            for run in runs
        ],
        "median_elapsed_seconds": statistics.median(
            run["elapsed_seconds"] for run in runs
        ),
        "median_peak_rss_mib": statistics.median(run["peak_rss_mib"] for run in runs),
        "median_rss_increase_mib": statistics.median(
            run["rss_increase_mib"] for run in runs
        ),
    }


def _benchmark(input_path: Path, runs: int, warmups: int) -> dict[str, Any]:
    if not input_path.is_file():
        raise FileNotFoundError(f"AIS benchmark input does not exist: {input_path}")
    if runs < 1 or warmups < 0:
        raise ValueError("runs must be at least 1 and warmups cannot be negative")

    for _ in range(warmups):
        _invoke_worker("duckdb", input_path)
        _invoke_worker("polars", input_path)

    measurements: dict[EngineName, list[WorkerResult]] = {
        "duckdb": [],
        "polars": [],
    }
    for run_number in range(runs):
        order: tuple[EngineName, EngineName] = (
            ("duckdb", "polars") if run_number % 2 == 0 else ("polars", "duckdb")
        )
        for engine in order:
            measurements[engine].append(_invoke_worker(engine, input_path))

    duckdb_groups = measurements["duckdb"][0]["groups"]
    polars_groups = measurements["polars"][0]["groups"]
    equivalent = _equivalent(duckdb_groups, polars_groups)
    if not equivalent:
        raise RuntimeError("DuckDB and Polars produced different grouped results")

    return {
        "input": {
            "path": str(input_path.resolve()),
            "bytes": input_path.stat().st_size,
            "sha256": _sha256(input_path),
            "records": _record_count(input_path),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "duckdb": version("duckdb"),
            "polars": version("polars"),
            "psutil": version("psutil"),
        },
        "operation": {
            "columns": [
                "MMSI",
                "BaseDateTime",
                "LAT",
                "LON",
                "SOG",
                "VesselType",
                "Length",
            ],
            "timestamp_format": "%Y-%m-%dT%H:%M:%S UTC",
            "map_extent_wgs84": {
                "lon_min": MAP_LON_MIN,
                "lon_max": MAP_LON_MAX,
                "lat_min": MAP_LAT_MIN,
                "lat_max": MAP_LAT_MAX,
            },
            "speed_missing_sentinel": SOG_MISSING_SENTINEL,
            "group_by": "VesselType",
            "aggregates": [
                "row count",
                "distinct MMSI",
                "valid SOG count",
                "mean valid SOG",
                "mean available Length",
            ],
            "warmups": warmups,
            "measured_runs": runs,
        },
        "results": {
            "duckdb": _summary(measurements["duckdb"]),
            "polars": _summary(measurements["polars"]),
        },
        "tested_result": {
            "filtered_rows": measurements["duckdb"][0]["filtered_rows"],
            "vessel_type_groups": len(duckdb_groups),
        },
        "equivalent": equivalent,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare DuckDB and Polars on one supplied AIS CSV sample."
    )
    parser.add_argument("--input", type=Path, required=True, help="AIS CSV path")
    parser.add_argument(
        "--runs", type=int, default=5, help="measured isolated runs per engine"
    )
    parser.add_argument(
        "--warmups", type=int, default=1, help="unreported warm-up runs per engine"
    )
    parser.add_argument(
        "--worker", choices=("duckdb", "polars"), help=argparse.SUPPRESS
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    input_path = cast(Path, args.input)
    worker = cast(EngineName | None, args.worker)
    if worker is not None:
        print(json.dumps(_run_worker(worker, input_path), sort_keys=True))
        return 0
    report = _benchmark(input_path, cast(int, args.runs), cast(int, args.warmups))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
