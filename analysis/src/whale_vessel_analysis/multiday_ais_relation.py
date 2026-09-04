"""Bounded DuckDB relation over the verified multi-day cleaned AIS input.

The analytical period is scanned as daily Parquet partitions through DuckDB with
an explicit memory limit and an explicit spill directory under ignored local
storage. The full period is never concatenated in Python, Pandas, Polars, or
PyArrow: callers stream ordered record batches or read SQL aggregates.

Global ordering is deterministic and continuous across midnight, so a later
whole-period window operation will not split a vessel merely because the UTC
date changed. This module applies no maximum-gap or implied-speed rule and emits
no production segment or vessel-activity grid.
"""

from __future__ import annotations

import re
import shutil
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import duckdb
import pyarrow as pa

from whale_vessel_analysis.cleaned_ais_bundle import require_mapping, sha256_file
from whale_vessel_analysis.multiday_ais import (
    MultiDayAISInputError,
    validate_ignored_local_directory,
)

PERIOD_VIEW_NAME: Final = "cleaned_period_observations"
GLOBAL_ORDER_COLUMNS: Final = (
    "mmsi",
    "observed_at_utc",
    "latitude",
    "longitude",
    "vessel_type_code",
    "vessel_type_group",
)
DEFAULT_BATCH_SIZE: Final = 100_000
CONTINUITY_NOTE: Final = (
    "consecutive pairs are constructed across the whole period, so a vessel is "
    "not split solely because the UTC date changed; no maximum-gap, "
    "implied-speed, length or edge-support rule is applied and no segment is "
    "emitted"
)
_MEMORY_LIMIT_PATTERN: Final = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>KB|MB|GB|TB|KIB|MIB|GIB|TIB)\s*$",
    re.IGNORECASE,
)


class MultiDayRelationError(MultiDayAISInputError):
    """Raised when relation resources or partition inputs are unusable."""


@dataclass(frozen=True, slots=True)
class RelationResources:
    """Explicit bounded-execution settings for the period relation."""

    memory_limit: str
    temporary_directory: Path
    threads: int | None = None

    def __post_init__(self) -> None:
        match = _MEMORY_LIMIT_PATTERN.match(self.memory_limit)
        if match is None:
            raise MultiDayRelationError(
                "memory limit must be an explicit size with a unit, for example "
                "'2GB' or '512MiB'"
            )
        if float(match.group("value")) <= 0:
            raise MultiDayRelationError("memory limit must be greater than zero")
        if self.threads is not None and self.threads < 1:
            raise MultiDayRelationError("thread count must be at least one")
        object.__setattr__(
            self,
            "temporary_directory",
            validate_ignored_local_directory(
                self.temporary_directory, "temporary/spill directory"
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_limit": self.memory_limit,
            "temporary_directory": str(self.temporary_directory),
            "threads": self.threads,
        }


@dataclass(frozen=True, slots=True)
class DatePartition:
    """One verified daily Parquet partition of the period input."""

    utc_date: str
    cleaned_path: Path
    cleaned_sha256: str
    cleaner_run_id: str
    cleaned_rows: int

    def to_dict(self) -> dict[str, object]:
        return {
            "utc_date": self.utc_date,
            "cleaned_parquet_sha256": self.cleaned_sha256,
            "cleaner_run_id": self.cleaner_run_id,
            "cleaned_rows": self.cleaned_rows,
        }


@dataclass(frozen=True, slots=True)
class AdjacentObservationPair:
    """One diagnostic consecutive-observation adjacency for the same MMSI."""

    mmsi: str
    from_utc_date: str
    to_utc_date: str
    from_observed_at_utc: str
    to_observed_at_utc: str
    elapsed_seconds: float

    def to_dict(self) -> dict[str, object]:
        return {
            "mmsi": self.mmsi,
            "from_utc_date": self.from_utc_date,
            "to_utc_date": self.to_utc_date,
            "from_observed_at_utc": self.from_observed_at_utc,
            "to_observed_at_utc": self.to_observed_at_utc,
            "elapsed_seconds": self.elapsed_seconds,
        }


def _sql_string(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def period_partitions(manifest: Mapping[str, object]) -> tuple[DatePartition, ...]:
    """Return the compatible daily partitions recorded in one period manifest."""
    dates = manifest.get("dates")
    if not isinstance(dates, list):
        raise MultiDayRelationError("period manifest dates must be a list")
    partitions: list[DatePartition] = []
    for raw_entry in cast(list[object], dates):
        entry = require_mapping(raw_entry, "period manifest date")
        if entry.get("status") != "compatible":
            continue
        compatibility = require_mapping(
            entry.get("cleaner_bundle_compatibility"), "cleaner_bundle_compatibility"
        )
        provenance = require_mapping(
            entry.get("local_provenance"), "date local provenance"
        )
        cleaned_path = provenance.get("cleaned_parquet_path")
        if not isinstance(cleaned_path, str):
            raise MultiDayRelationError(
                f"date {entry.get('utc_date')} has no recorded cleaned Parquet path"
            )
        partitions.append(
            DatePartition(
                utc_date=cast(str, entry["utc_date"]),
                cleaned_path=Path(cleaned_path),
                cleaned_sha256=cast(str, compatibility["cleaned_parquet_sha256"]),
                cleaner_run_id=cast(str, compatibility["cleaner_run_id"]),
                cleaned_rows=cast(int, compatibility["cleaned_rows"]),
            )
        )
    return tuple(sorted(partitions, key=lambda partition: partition.utc_date))


def _verify_partitions(partitions: tuple[DatePartition, ...]) -> None:
    for partition in partitions:
        if not partition.cleaned_path.is_file():
            raise MultiDayRelationError(
                f"recorded cleaned Parquet is missing for {partition.utc_date}: "
                f"{partition.cleaned_path}"
            )
        actual = sha256_file(partition.cleaned_path)
        if actual != partition.cleaned_sha256:
            raise MultiDayRelationError(
                f"cleaned Parquet for {partition.utc_date} no longer matches its "
                "recorded checksum"
            )


def _ordered_select() -> str:
    columns = ", ".join(GLOBAL_ORDER_COLUMNS)
    return f"SELECT * FROM {PERIOD_VIEW_NAME} ORDER BY {columns}"


@dataclass(frozen=True, slots=True)
class PeriodRelation:
    """A bounded, deterministically ordered relation over the period input."""

    connection: duckdb.DuckDBPyConnection
    partitions: tuple[DatePartition, ...]
    resources: RelationResources
    spill_directory: Path
    view_name: str = PERIOD_VIEW_NAME

    def count_observations(self) -> int:
        """Count every observation in SQL without materializing any row."""
        result = self.connection.execute(
            f"SELECT count(*) FROM {self.view_name}"
        ).fetchone()
        return int(cast(int, cast(tuple[object, ...], result)[0]))

    def partition_row_counts(self) -> dict[str, int]:
        """Return SQL-side row counts by observed UTC date."""
        rows = self.connection.execute(
            f"SELECT observed_utc_date, count(*) FROM {self.view_name} "
            "GROUP BY 1 ORDER BY 1"
        ).fetchall()
        return {str(row[0]): int(cast(int, row[1])) for row in rows}

    def ordered_query(self) -> str:
        """Return the deterministic global-ordering query text."""
        return _ordered_select()

    def ordered_batches(
        self, batch_size: int = DEFAULT_BATCH_SIZE
    ) -> pa.RecordBatchReader:
        """Stream globally ordered observations as bounded Arrow record batches."""
        if batch_size < 1:
            raise MultiDayRelationError("batch size must be at least one")
        return self.connection.execute(self.ordered_query()).to_arrow_reader(batch_size)

    def adjacent_observation_query(self) -> str:
        """Return one deterministic whole-period observation/pair stream query."""
        order = ", ".join(GLOBAL_ORDER_COLUMNS)
        next_columns = (
            "observed_at_utc",
            "latitude",
            "longitude",
            "sog_knots",
            "vessel_type_code",
            "vessel_type_group",
            "length_m",
        )
        lead_expressions = ",\n".join(
            f"""                lead({column}) OVER (
                    PARTITION BY mmsi ORDER BY {order}
                ) AS next_{column}"""
            for column in next_columns
        )
        return f"""
            WITH ordered AS (
                SELECT
                    mmsi,
                    observed_at_utc,
                    observed_utc_date,
                    latitude,
                    longitude,
                    sog_knots,
                    vessel_type_code,
                    vessel_type_group,
                    length_m,
{lead_expressions}
                FROM {self.view_name}
            )
            SELECT
                mmsi,
                epoch_us(observed_at_utc) AS observed_at_utc,
                observed_utc_date,
                latitude,
                longitude,
                sog_knots,
                vessel_type_code,
                vessel_type_group,
                length_m,
                epoch_us(next_observed_at_utc) AS next_observed_at_utc,
                next_latitude,
                next_longitude,
                next_sog_knots,
                next_vessel_type_code,
                next_vessel_type_group,
                next_length_m
            FROM ordered
            ORDER BY {order}
        """

    def adjacent_observation_batches(
        self, batch_size: int = DEFAULT_BATCH_SIZE
    ) -> pa.RecordBatchReader:
        """Stream observations with the next same-MMSI observation attached."""
        if batch_size < 1:
            raise MultiDayRelationError("batch size must be at least one")
        return self.connection.execute(
            self.adjacent_observation_query()
        ).to_arrow_reader(batch_size)

    def continuity_summary(self) -> dict[str, object]:
        """Compare whole-period adjacency with artificial daily partitioning."""
        order = ", ".join(GLOBAL_ORDER_COLUMNS)
        query = f"""
            WITH ordered AS (
                SELECT
                    mmsi,
                    observed_utc_date,
                    lead(observed_at_utc) OVER (
                        PARTITION BY mmsi ORDER BY {order}
                    ) AS next_observed_at_utc,
                    lead(observed_utc_date) OVER (
                        PARTITION BY mmsi ORDER BY {order}
                    ) AS next_observed_utc_date,
                    lead(observed_at_utc) OVER (
                        PARTITION BY mmsi, observed_utc_date ORDER BY {order}
                    ) AS next_within_date
                FROM {self.view_name}
            )
            SELECT
                count(*) FILTER (WHERE next_observed_at_utc IS NOT NULL),
                count(*) FILTER (WHERE next_within_date IS NOT NULL),
                count(*) FILTER (
                    WHERE next_observed_utc_date IS NOT NULL
                    AND next_observed_utc_date <> observed_utc_date
                ),
                count(DISTINCT mmsi) FILTER (
                    WHERE next_observed_utc_date IS NOT NULL
                    AND next_observed_utc_date <> observed_utc_date
                )
            FROM ordered
        """
        row = cast(
            tuple[object, ...],
            cast(object, self.connection.execute(query).fetchone()),
        )
        whole_period = int(cast(int, row[0]))
        date_partitioned = int(cast(int, row[1]))
        cross_date = int(cast(int, row[2]))
        return {
            "whole_period_consecutive_pairs": whole_period,
            "date_partitioned_consecutive_pairs": date_partitioned,
            "pairs_lost_to_date_partitioning": whole_period - date_partitioned,
            "cross_utc_date_pairs": cross_date,
            "mmsi_with_cross_utc_date_pairs": int(cast(int, row[3])),
            "note": CONTINUITY_NOTE,
        }

    def cross_date_adjacency(self) -> tuple[AdjacentObservationPair, ...]:
        """List same-MMSI adjacencies whose two observations differ in UTC date."""
        order = ", ".join(GLOBAL_ORDER_COLUMNS)
        query = f"""
            WITH ordered AS (
                SELECT
                    mmsi,
                    observed_at_utc,
                    observed_utc_date,
                    lead(observed_at_utc) OVER (
                        PARTITION BY mmsi ORDER BY {order}
                    ) AS next_observed_at_utc,
                    lead(observed_utc_date) OVER (
                        PARTITION BY mmsi ORDER BY {order}
                    ) AS next_observed_utc_date
                FROM {self.view_name}
            )
            SELECT
                mmsi,
                observed_utc_date,
                next_observed_utc_date,
                strftime(observed_at_utc, '%Y-%m-%dT%H:%M:%SZ'),
                strftime(next_observed_at_utc, '%Y-%m-%dT%H:%M:%SZ'),
                date_diff('second', observed_at_utc, next_observed_at_utc)
            FROM ordered
            WHERE next_observed_utc_date IS NOT NULL
              AND next_observed_utc_date <> observed_utc_date
            ORDER BY mmsi, observed_at_utc
        """
        rows = self.connection.execute(query).fetchall()
        return tuple(
            AdjacentObservationPair(
                mmsi=str(row[0]),
                from_utc_date=str(row[1]),
                to_utc_date=str(row[2]),
                from_observed_at_utc=str(row[3]),
                to_observed_at_utc=str(row[4]),
                elapsed_seconds=float(cast(float, row[5])),
            )
            for row in rows
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "view_name": self.view_name,
            "resources": self.resources.to_dict(),
            "spill_directory": str(self.spill_directory),
            "duckdb_settings": self.effective_settings(),
            "partition_count": len(self.partitions),
            "partitions": [partition.to_dict() for partition in self.partitions],
            "global_order_columns": list(GLOBAL_ORDER_COLUMNS),
            "materialization_note": (
                "the period is scanned through DuckDB; ordered results are streamed "
                "as bounded Arrow record batches and are never concatenated in "
                "Python, Pandas, Polars, or PyArrow"
            ),
        }

    def effective_settings(self) -> dict[str, object]:
        """Return the DuckDB settings actually in force for this connection."""
        settings: dict[str, object] = {}
        for name in ("memory_limit", "temp_directory", "threads"):
            row = cast(
                tuple[object, ...],
                cast(
                    object,
                    self.connection.execute(
                        f"SELECT current_setting({_sql_string(name)})"
                    ).fetchone(),
                ),
            )
            settings[name] = row[0]
        return settings


@contextmanager
def open_period_relation(
    manifest: Mapping[str, object],
    resources: RelationResources,
    *,
    require_ready: bool = False,
    verify_checksums: bool = True,
) -> Iterator[PeriodRelation]:
    """Open a bounded DuckDB relation over the manifest's verified partitions."""
    readiness = require_mapping(
        manifest.get("period_input_readiness"), "period_input_readiness"
    )
    if require_ready and readiness.get("status") != "ready":
        raise MultiDayRelationError(
            "the analytical period is not ready; every expected UTC date needs a "
            "compatible verified cleaner bundle"
        )
    partitions = period_partitions(manifest)
    if not partitions:
        raise MultiDayRelationError(
            "the period manifest records no compatible date to scan"
        )
    if verify_checksums:
        _verify_partitions(partitions)
    spill_directory = resources.temporary_directory / f"duckdb-spill-{uuid.uuid4().hex}"
    spill_directory.mkdir(parents=True)
    connection: duckdb.DuckDBPyConnection | None = None
    try:
        connection = duckdb.connect(":memory:")
        connection.execute("SET TimeZone = 'UTC'")
        connection.execute(f"SET memory_limit = {_sql_string(resources.memory_limit)}")
        connection.execute(f"SET temp_directory = {_sql_string(spill_directory)}")
        if resources.threads is not None:
            connection.execute(f"SET threads = {resources.threads}")
        paths = ", ".join(_sql_string(item.cleaned_path) for item in partitions)
        connection.execute(
            f"""
            CREATE OR REPLACE VIEW {PERIOD_VIEW_NAME} AS
            SELECT
                CAST(observed_at_utc AS DATE) AS observed_utc_date,
                mmsi,
                observed_at_utc,
                latitude,
                longitude,
                sog_knots,
                cog_degrees,
                heading_degrees,
                vessel_type_code,
                vessel_type_group,
                length_m
            FROM read_parquet([{paths}])
            """
        )
        relation = PeriodRelation(
            connection=connection,
            partitions=partitions,
            resources=resources,
            spill_directory=spill_directory,
        )
        _verify_partition_alignment(relation)
        yield relation
    except duckdb.Error as exc:
        raise MultiDayRelationError(
            f"could not open the bounded period relation: {exc}"
        ) from exc
    finally:
        if connection is not None:
            connection.close()
        shutil.rmtree(spill_directory, ignore_errors=True)


def _verify_partition_alignment(relation: PeriodRelation) -> None:
    counts = relation.partition_row_counts()
    expected = {
        partition.utc_date: partition.cleaned_rows for partition in relation.partitions
    }
    if counts != expected:
        raise MultiDayRelationError(
            "scanned daily partitions do not match the manifest's recorded UTC "
            "dates and row counts"
        )
