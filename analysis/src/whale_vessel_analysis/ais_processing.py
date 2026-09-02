"""Deterministic processing for one supplied NOAA Marine Cadastre AIS CSV."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import tempfile
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from typing import Final

import duckdb

from whale_vessel_analysis.ais import AISValidationError, read_header
from whale_vessel_analysis.config import ProcessingConfig
from whale_vessel_analysis.duckdb_resources import memory_settings_match
from whale_vessel_analysis.lineage import (
    ArtifactReference,
    ProcessingStep,
    RunMetadata,
    ValidationRecord,
)

AIS_PROCESSING_CONTRACT: Final = "noaa_marine_cadastre_ais_extract_v2"
AIS_PROCESSING_VERSION: Final = "2.0.0"
CLEANED_FILENAME: Final = "cleaned.parquet"
QUALITY_REPORT_FILENAME: Final = "quality-report.json"
RUN_METADATA_FILENAME: Final = "run-metadata.json"
_BUNDLE_FILENAMES: Final = (
    CLEANED_FILENAME,
    QUALITY_REPORT_FILENAME,
    RUN_METADATA_FILENAME,
)
_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
_PROJECT_RAW_ROOT: Final = (_PROJECT_ROOT / "data" / "raw").resolve()
_LEGACY_OVERWRITE_CONTRACTS: Final = frozenset({"noaa_marine_cadastre_ais_day_v1"})
_MEMORY_LIMIT_PATTERN: Final = re.compile(r"^[1-9][0-9]*(?:\.[0-9]+)?(?:KB|MB|GB|TB)$")

_OUTPUT_SCHEMA: Final = (
    ("mmsi", "VARCHAR", True),
    ("observed_at_utc", "TIMESTAMP WITH TIME ZONE", True),
    ("latitude", "DOUBLE", True),
    ("longitude", "DOUBLE", True),
    ("sog_knots", "DOUBLE", False),
    ("cog_degrees", "DOUBLE", False),
    ("heading_degrees", "DOUBLE", False),
    ("vessel_type_code", "SMALLINT", True),
    ("vessel_type_group", "VARCHAR", True),
    ("length_m", "DOUBLE", False),
)


class AISProcessingError(ValueError):
    """Raised when a supplied AIS extract cannot be processed safely."""


@dataclass(frozen=True, slots=True)
class AISProcessingResources:
    """Explicit DuckDB resources for one-date AIS cleaning."""

    memory_limit: str
    temporary_directory: Path
    threads: int = 1

    def validate(self) -> AISProcessingResources:
        if _MEMORY_LIMIT_PATTERN.fullmatch(self.memory_limit) is None:
            raise AISProcessingError(
                "AIS processing memory limit must be a positive size with a "
                "KB, MB, GB, or TB unit"
            )
        if self.threads < 1:
            raise AISProcessingError("AIS processing thread count must be at least one")
        temporary = self.temporary_directory.resolve()
        if temporary.exists() and not temporary.is_dir():
            raise AISProcessingError(
                f"AIS processing temporary directory is not a directory: {temporary}"
            )
        return AISProcessingResources(self.memory_limit, temporary, self.threads)


@dataclass(frozen=True, slots=True)
class AISTemporalCoverage:
    """Observed timestamp bounds without an unsupported completeness claim."""

    observed_utc_date: str
    earliest_valid_observed_at_utc: str
    latest_valid_observed_at_utc: str

    def to_dict(self) -> dict[str, object]:
        return {
            "observed_utc_date": self.observed_utc_date,
            "earliest_valid_observed_at_utc": self.earliest_valid_observed_at_utc,
            "latest_valid_observed_at_utc": self.latest_valid_observed_at_utc,
            "completeness": {
                "status": "unverified",
                "reason": (
                    "the supplied CSV carries no retained retrieval metadata that "
                    "proves complete UTC-day coverage"
                ),
            },
        }


@dataclass(frozen=True, slots=True)
class AISProcessingResult:
    """Locations and stable identifiers for one completed output bundle."""

    run_id: str
    output_directory: Path
    cleaned_parquet: Path
    quality_report: Path
    run_metadata: Path
    input_rows: int
    output_rows: int
    output_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "output_directory": str(self.output_directory),
            "cleaned_parquet": str(self.cleaned_parquet),
            "quality_report": str(self.quality_report),
            "run_metadata": str(self.run_metadata),
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "output_sha256": self.output_sha256,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _write_json(path: Path, payload: object) -> None:
    path.write_text(_canonical_json(payload) + "\n", encoding="utf-8", newline="\n")


def _sql_string(value: Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _processing_parameters(config: ProcessingConfig) -> dict[str, object]:
    extent = config.spatial.map_extent
    return {
        "input_scope": "one explicitly supplied flat CSV extract",
        "timestamp": {
            "source_format": "%Y-%m-%dT%H:%M:%S",
            "timezone": "UTC",
            "required_valid_utc_dates": 1,
            "complete_day_required": False,
            "completeness_default": "unverified",
        },
        "map_extent": extent.to_dict(),
        "commercial_vessel_types": {
            "selected_codes": "60-89",
            "groups": {
                "passenger": "60-69",
                "cargo": "70-79",
                "tanker": "80-89",
            },
        },
        "length_filter": {
            "enabled": False,
            "minimum_length_m": None,
            "status": "unresolved project assumption",
            "reason": (
                "AIS has no gross tonnage, and no length threshold has an accepted "
                "decision record and sensitivity plan"
            ),
        },
        "behavioral_plausibility": {
            "enabled": False,
            "implied_speed_threshold_knots": None,
            "status": "unresolved project assumption",
            "reason": (
                "no authoritative or accepted provisional implied-speed threshold "
                "has been selected"
            ),
        },
        "duplicate_policy": {
            "exact_rows": "retain one row; all copies are identical",
            "repeated_mmsi_timestamp_conflicts": "remove every conflicting row",
            "decision": "ADR 0013",
        },
        "reported_sog_validity": {
            "unavailable_sentinel": 102.3,
            "invalid_rule": "missing, non-numeric, non-finite, or negative",
            "universal_maximum_enabled": False,
        },
        "optional_navigation_fields": {
            "cog_unavailable_sentinel": 360.0,
            "heading_unavailable_sentinel": 511,
            "invalid_values": "normalize to null and count",
        },
        "parquet": {
            "compression": "zstd",
            "row_group_size": 122_880,
            "ordering": [
                "observed_at_utc",
                "mmsi",
                "latitude",
                "longitude",
                "vessel_type_code",
            ],
            "schema": [
                {
                    "name": name,
                    "type": data_type,
                    "physical_nullable": True,
                    "required_by_cleaning_contract": required,
                }
                for name, data_type, required in _OUTPUT_SCHEMA
            ],
        },
    }


def _pipeline_ctes(config: ProcessingConfig, input_path: Path) -> str:
    extent = config.spatial.map_extent
    raw_columns = (
        "MMSI, BaseDateTime, LAT, LON, SOG, COG, Heading, VesselName, IMO, "
        "CallSign, VesselType, Status, Length, Width, Draft, Cargo, "
        "TransceiverClass"
    )
    return f"""
        source AS (
            SELECT row_number() OVER () AS source_row_number, *
            FROM read_csv({_sql_string(input_path)}, header = true, all_varchar = true)
        ),
        parsed AS (
            SELECT
                *,
                CASE
                    WHEN regexp_full_match(
                        BaseDateTime, '[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}T'
                                      '[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}'
                    )
                    THEN try_strptime(BaseDateTime, '%Y-%m-%dT%H:%M:%S')
                    ELSE NULL
                END AS observed_at_naive,
                try_cast(LAT AS DOUBLE) AS latitude,
                try_cast(LON AS DOUBLE) AS longitude,
                try_cast(SOG AS DOUBLE) AS parsed_sog,
                try_cast(COG AS DOUBLE) AS parsed_cog,
                try_cast(Heading AS DOUBLE) AS parsed_heading,
                try_cast(trim(VesselType) AS INTEGER) AS parsed_vessel_type,
                try_cast(Length AS DOUBLE) AS parsed_length
            FROM source
        ),
        timestamp_valid AS (
            SELECT *, timezone('UTC', observed_at_naive) AS observed_at_utc
            FROM parsed
            WHERE observed_at_naive IS NOT NULL
        ),
        coordinate_valid AS (
            SELECT *
            FROM timestamp_valid
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
              AND isfinite(latitude) AND isfinite(longitude)
              AND latitude BETWEEN -90.0 AND 90.0
              AND longitude BETWEEN -180.0 AND 180.0
        ),
        map_scoped AS (
            SELECT *
            FROM coordinate_valid
            WHERE longitude BETWEEN {extent.lon_min!r} AND {extent.lon_max!r}
              AND latitude BETWEEN {extent.lat_min!r} AND {extent.lat_max!r}
        ),
        mmsi_valid AS (
            SELECT *
            FROM map_scoped
            WHERE coalesce(regexp_full_match(MMSI, '[1-9][0-9]{{8}}'), false)
        ),
        sog_valid AS (
            SELECT *
            FROM mmsi_valid
            WHERE parsed_sog = 102.3
               OR (parsed_sog IS NOT NULL AND isfinite(parsed_sog) AND parsed_sog >= 0)
        ),
        vessel_type_valid AS (
            SELECT *
            FROM sog_valid
            WHERE VesselType IS NOT NULL AND trim(VesselType) != ''
              AND regexp_full_match(trim(VesselType), '[0-9]+')
              AND parsed_vessel_type BETWEEN 1 AND 99
        ),
        commercial AS (
            SELECT *
            FROM vessel_type_valid
            WHERE parsed_vessel_type BETWEEN 60 AND 89
        ),
        exact_ranked AS (
            SELECT *, row_number() OVER (
                PARTITION BY {raw_columns}
                ORDER BY source_row_number
            ) AS exact_rank
            FROM commercial
        ),
        exact_deduplicated AS (
            SELECT *
            FROM exact_ranked
            WHERE exact_rank = 1
        ),
        conflict_ranked AS (
            SELECT *, count(*) OVER (
                PARTITION BY MMSI, observed_at_utc
            ) AS key_occurrences
            FROM exact_deduplicated
        ),
        retained AS (
            SELECT *
            FROM conflict_ranked
            WHERE key_occurrences = 1
        )
    """


def _collect_counts(
    connection: duckdb.DuckDBPyConnection,
    config: ProcessingConfig,
    input_path: Path,
) -> tuple[dict[str, int], dict[str, int], dict[str, int], AISTemporalCoverage]:
    ctes = _pipeline_ctes(config, input_path)
    query = f"""
        WITH {ctes}
        SELECT
            (SELECT count(*) FROM source) AS source_rows,
            (SELECT count(*) FROM timestamp_valid) AS after_valid_timestamp,
            (SELECT count(*) FROM coordinate_valid) AS after_valid_coordinates,
            (SELECT count(*) FROM map_scoped) AS after_map_extent,
            (SELECT count(*) FROM mmsi_valid) AS after_valid_mmsi,
            (SELECT count(*) FROM sog_valid) AS after_valid_reported_sog,
            (SELECT count(*) FROM vessel_type_valid) AS after_valid_vessel_type,
            (SELECT count(*) FROM commercial) AS after_commercial_type,
            (SELECT count(*) FROM exact_deduplicated) AS after_exact_duplicates,
            (SELECT count(*) FROM retained) AS final_rows,
            (SELECT count(DISTINCT cast(observed_at_utc AS DATE))
                FROM timestamp_valid) AS distinct_utc_days,
            (SELECT min(cast(observed_at_utc AS DATE)) FROM timestamp_valid)
                AS first_utc_day,
            (SELECT max(cast(observed_at_utc AS DATE)) FROM timestamp_valid)
                AS last_utc_day,
            (SELECT strftime(min(observed_at_utc), '%Y-%m-%dT%H:%M:%SZ')
                FROM timestamp_valid) AS earliest_valid_observed_at_utc,
            (SELECT strftime(max(observed_at_utc), '%Y-%m-%dT%H:%M:%SZ')
                FROM timestamp_valid) AS latest_valid_observed_at_utc,
            (SELECT count(*) FROM sog_valid
                WHERE VesselType IS NULL OR trim(VesselType) = '')
                AS missing_vessel_type_removed,
            (SELECT count(*) FROM sog_valid
                WHERE VesselType IS NOT NULL AND trim(VesselType) != '' AND (
                    NOT regexp_full_match(trim(VesselType), '[0-9]+')
                    OR parsed_vessel_type IS NULL
                    OR parsed_vessel_type NOT BETWEEN 0 AND 99
                )) AS malformed_vessel_type_removed,
            (SELECT count(*) FROM sog_valid
                WHERE regexp_full_match(trim(VesselType), '[0-9]+')
                  AND parsed_vessel_type = 0) AS unavailable_vessel_type_removed,
            (SELECT count(*) FROM retained WHERE parsed_sog = 102.3)
                AS sog_sentinel_normalized,
            (SELECT count(*) FROM retained WHERE parsed_cog = 360.0)
                AS cog_sentinel_normalized,
            (SELECT count(*) FROM retained WHERE parsed_heading = 511.0)
                AS heading_sentinel_normalized,
            (SELECT count(*) FROM retained WHERE COG IS NULL OR trim(COG) = ''
                OR parsed_cog IS NULL OR NOT isfinite(parsed_cog)
                OR parsed_cog < 0 OR parsed_cog > 360) AS invalid_cog_normalized,
            (SELECT count(*) FROM retained WHERE Heading IS NULL OR trim(Heading) = ''
                OR parsed_heading IS NULL OR NOT isfinite(parsed_heading)
                OR parsed_heading < 0
                OR (parsed_heading > 359 AND parsed_heading != 511))
                AS invalid_heading_normalized,
            (SELECT count(*) FROM retained WHERE Length IS NULL OR trim(Length) = ''
                OR parsed_length IS NULL OR NOT isfinite(parsed_length)
                OR parsed_length < 0) AS unavailable_length_normalized
    """
    row = connection.execute(query).fetchone()
    if row is None:
        raise AISProcessingError("AIS cleaning count query returned no result")
    values = list(row)
    stages = {
        "source_rows": int(values[0]),
        "after_valid_timestamp": int(values[1]),
        "after_valid_coordinates": int(values[2]),
        "after_map_extent": int(values[3]),
        "after_valid_mmsi": int(values[4]),
        "after_valid_reported_sog": int(values[5]),
        "after_valid_vessel_type": int(values[6]),
        "after_commercial_type": int(values[7]),
        "after_exact_duplicates": int(values[8]),
        "final_rows": int(values[9]),
    }
    distinct_days = int(values[10])
    first_day = None if values[11] is None else str(values[11])
    last_day = None if values[12] is None else str(values[12])
    earliest_observed = None if values[13] is None else str(values[13])
    latest_observed = None if values[14] is None else str(values[14])
    if stages["source_rows"] == 0:
        raise AISProcessingError("AIS input contains no data rows")
    if stages["after_valid_timestamp"] == 0:
        raise AISProcessingError("AIS input contains zero valid UTC timestamps")
    if distinct_days > 1:
        raise AISProcessingError(
            "AIS input contains multiple UTC dates; supply one UTC-date extract "
            f"(found {first_day} through {last_day})"
        )
    if first_day is None or earliest_observed is None or latest_observed is None:
        raise AISProcessingError("AIS timestamp coverage query returned no bounds")
    start = config.analytical_period.start_date.isoformat()
    end = config.analytical_period.end_date.isoformat()
    if not start <= first_day <= end:
        raise AISProcessingError(
            f"AIS UTC date {first_day} is outside configured period {start} to {end}"
        )
    removals = {
        "invalid_timestamp_rows": stages["source_rows"]
        - stages["after_valid_timestamp"],
        "invalid_coordinate_rows": stages["after_valid_timestamp"]
        - stages["after_valid_coordinates"],
        "outside_map_extent_rows": stages["after_valid_coordinates"]
        - stages["after_map_extent"],
        "invalid_mmsi_rows": stages["after_map_extent"] - stages["after_valid_mmsi"],
        "invalid_reported_sog_rows": stages["after_valid_mmsi"]
        - stages["after_valid_reported_sog"],
        "missing_vessel_type_rows": int(values[15]),
        "malformed_vessel_type_rows": int(values[16]),
        "unavailable_vessel_type_rows": int(values[17]),
        "noncommercial_vessel_type_rows": stages["after_valid_vessel_type"]
        - stages["after_commercial_type"],
        "exact_duplicate_rows": stages["after_commercial_type"]
        - stages["after_exact_duplicates"],
        "conflicting_mmsi_timestamp_rows": stages["after_exact_duplicates"]
        - stages["final_rows"],
    }
    normalizations = {
        "sog_sentinel_to_null_rows": int(values[18]),
        "cog_sentinel_to_null_rows": int(values[19]),
        "heading_sentinel_to_null_rows": int(values[20]),
        "invalid_cog_to_null_rows": int(values[21]),
        "invalid_heading_to_null_rows": int(values[22]),
        "unavailable_or_invalid_length_to_null_rows": int(values[23]),
    }
    if sum(removals.values()) != stages["source_rows"] - stages["final_rows"]:
        raise AISProcessingError("AIS cleaning counts do not conserve input rows")
    return (
        stages,
        removals,
        normalizations,
        AISTemporalCoverage(
            observed_utc_date=first_day,
            earliest_valid_observed_at_utc=earliest_observed,
            latest_valid_observed_at_utc=latest_observed,
        ),
    )


def _write_cleaned_parquet(
    connection: duckdb.DuckDBPyConnection,
    config: ProcessingConfig,
    input_path: Path,
    output_path: Path,
) -> None:
    ctes = _pipeline_ctes(config, input_path)
    query = f"""
        COPY (
            WITH {ctes}
            SELECT
                MMSI AS mmsi,
                observed_at_utc,
                latitude,
                longitude,
                CASE WHEN parsed_sog = 102.3 THEN NULL ELSE parsed_sog END
                    AS sog_knots,
                CASE
                    WHEN parsed_cog = 360.0 OR parsed_cog IS NULL
                      OR NOT isfinite(parsed_cog)
                      OR parsed_cog < 0 OR parsed_cog > 360
                    THEN NULL
                    ELSE parsed_cog
                END AS cog_degrees,
                CASE
                    WHEN parsed_heading = 511.0 OR parsed_heading IS NULL
                      OR NOT isfinite(parsed_heading)
                      OR parsed_heading < 0 OR parsed_heading > 359
                    THEN NULL
                    ELSE parsed_heading
                END AS heading_degrees,
                cast(parsed_vessel_type AS SMALLINT) AS vessel_type_code,
                CASE
                    WHEN parsed_vessel_type BETWEEN 60 AND 69 THEN 'passenger'
                    WHEN parsed_vessel_type BETWEEN 70 AND 79 THEN 'cargo'
                    WHEN parsed_vessel_type BETWEEN 80 AND 89 THEN 'tanker'
                END AS vessel_type_group,
                CASE
                    WHEN parsed_length IS NULL OR NOT isfinite(parsed_length)
                      OR parsed_length < 0
                    THEN NULL
                    ELSE parsed_length
                END AS length_m
            FROM retained
            ORDER BY observed_at_utc, MMSI, latitude, longitude, parsed_vessel_type
        ) TO {_sql_string(output_path)} (
            FORMAT PARQUET,
            COMPRESSION ZSTD,
            ROW_GROUP_SIZE 122880
        )
    """
    connection.execute(query)


def _runtime() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "duckdb": version("duckdb"),
        "package": version("socal-whale-vessel-analysis"),
    }


def _duckdb_settings(
    connection: duckdb.DuckDBPyConnection,
    requested: AISProcessingResources,
    spill_directory: Path,
) -> dict[str, object]:
    row = connection.execute(
        "SELECT current_setting('memory_limit'), "
        "current_setting('temp_directory'), current_setting('threads')"
    ).fetchone()
    if row is None:
        raise AISProcessingError("DuckDB resource settings query returned no result")
    effective_temp = Path(str(row[1])).resolve()
    return {
        "requested_memory_limit": requested.memory_limit,
        "effective_memory_limit": str(row[0]),
        "requested_threads": requested.threads,
        "effective_threads": int(row[2]),
        "isolated_spill_directory": True,
        "effective_temp_directory_matches_isolated_spill": (
            effective_temp == spill_directory.resolve()
        ),
        "local_spill_path_recorded": False,
    }


def _configure_duckdb_resources(
    connection: duckdb.DuckDBPyConnection,
    resources: AISProcessingResources,
    spill_directory: Path,
) -> dict[str, object]:
    connection.execute(f"SET memory_limit = '{resources.memory_limit}'")
    escaped_spill = str(spill_directory).replace("'", "''")
    connection.execute(f"SET temp_directory = '{escaped_spill}'")
    connection.execute(f"SET threads = {resources.threads}")
    settings = _duckdb_settings(connection, resources, spill_directory)
    try:
        memory_matches = memory_settings_match(
            resources.memory_limit, str(settings["effective_memory_limit"])
        )
    except ValueError as exc:
        raise AISProcessingError(
            "DuckDB returned an unreadable effective AIS memory limit: "
            f"{settings['effective_memory_limit']!r}"
        ) from exc
    if not memory_matches:
        raise AISProcessingError(
            "DuckDB did not apply the requested AIS processing memory limit: "
            f"requested {resources.memory_limit!r}, effective "
            f"{settings['effective_memory_limit']!r}"
        )
    if (
        settings["effective_threads"] != resources.threads
        or settings["effective_temp_directory_matches_isolated_spill"] is not True
    ):
        raise AISProcessingError(
            "DuckDB did not apply the requested AIS processing resources"
        )
    return settings


def _validate_output_target(output_directory: Path, overwrite: bool) -> None:
    resolved = output_directory.resolve()
    if resolved == _PROJECT_RAW_ROOT or resolved.is_relative_to(_PROJECT_RAW_ROOT):
        raise AISProcessingError(
            f"AIS processing output cannot be written under raw data: {resolved}"
        )
    if output_directory.exists() and not output_directory.is_dir():
        raise AISProcessingError(f"output path is not a directory: {output_directory}")
    if output_directory.exists() and not overwrite:
        raise AISProcessingError(
            "output directory already exists; pass --overwrite to replace only an "
            "existing AIS processing bundle"
        )
    if not output_directory.exists():
        return
    entries = {entry.name for entry in output_directory.iterdir()}
    if entries != set(_BUNDLE_FILENAMES):
        raise AISProcessingError(
            "--overwrite only replaces a complete AIS processing bundle with the "
            f"expected files: {', '.join(_BUNDLE_FILENAMES)}"
        )
    try:
        metadata = json.loads(
            (output_directory / RUN_METADATA_FILENAME).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise AISProcessingError(
            "existing run-metadata.json is not a readable AIS bundle marker"
        ) from exc
    accepted_contracts = {AIS_PROCESSING_CONTRACT, *_LEGACY_OVERWRITE_CONTRACTS}
    if metadata.get("contract") not in accepted_contracts:
        raise AISProcessingError(
            "existing output is not marked as this AIS processing contract"
        )


def _paths_overlap(first: Path, second: Path) -> bool:
    return (
        first == second or first.is_relative_to(second) or second.is_relative_to(first)
    )


def _validate_resource_paths(
    resources: AISProcessingResources,
    input_path: Path,
    output_directory: Path,
) -> None:
    temporary = resources.temporary_directory
    if temporary == _PROJECT_RAW_ROOT or temporary.is_relative_to(_PROJECT_RAW_ROOT):
        raise AISProcessingError(
            "AIS processing temporary directory cannot be inside data/raw"
        )
    if _paths_overlap(temporary, input_path) or _paths_overlap(
        temporary, output_directory
    ):
        raise AISProcessingError(
            "AIS processing temporary directory must be disjoint from the input "
            "and output"
        )


def _cleanup_bundle_directory(path: Path) -> None:
    if not path.exists():
        return
    for filename in (*_BUNDLE_FILENAMES, "work.duckdb"):
        candidate = path / filename
        if candidate.is_file():
            candidate.unlink()
    with suppress(OSError):
        path.rmdir()


def _publish_bundle(temporary: Path, target: Path, overwrite: bool) -> None:
    if not target.exists():
        temporary.rename(target)
        return
    if not overwrite:
        raise AISProcessingError(f"output directory already exists: {target}")
    backup = target.with_name(f".{target.name}.previous-{os.getpid()}")
    if backup.exists():
        raise AISProcessingError(f"narrow overwrite backup already exists: {backup}")
    target.rename(backup)
    try:
        temporary.rename(target)
    except OSError:
        backup.rename(target)
        raise
    _cleanup_bundle_directory(backup)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _clock_timestamp(clock: Callable[[], datetime], name: str) -> datetime:
    value = clock()
    if value.utcoffset() != timedelta(0):
        raise AISProcessingError(f"{name} execution timestamp must be UTC")
    return value.astimezone(UTC)


def process_ais_csv(
    input_path: Path,
    output_directory: Path,
    config: ProcessingConfig,
    *,
    overwrite: bool = False,
    clock: Callable[[], datetime] = _utc_now,
    resources: AISProcessingResources | None = None,
) -> AISProcessingResult:
    """Clean one single-UTC-date AIS extract into an atomic output bundle."""
    started_at = _clock_timestamp(clock, "start")
    input_path = input_path.resolve()
    output_directory = output_directory.resolve()
    read_header(input_path)
    if input_path.is_relative_to(output_directory):
        raise AISProcessingError("output directory cannot contain the supplied input")
    _validate_output_target(output_directory, overwrite)
    validated_resources = None if resources is None else resources.validate()
    if validated_resources is not None:
        _validate_resource_paths(validated_resources, input_path, output_directory)
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{output_directory.name}.temporary-",
            dir=output_directory.parent,
        )
    )
    cleaned_temporary = temporary / CLEANED_FILENAME
    quality_temporary = temporary / QUALITY_REPORT_FILENAME
    metadata_temporary = temporary / RUN_METADATA_FILENAME
    input_sha256 = _sha256(input_path)
    parameters = _processing_parameters(config)
    spill_directory: Path | None = None
    execution_resources: dict[str, object] | None = None
    try:
        try:
            if validated_resources is not None:
                validated_resources.temporary_directory.mkdir(
                    parents=True, exist_ok=True
                )
                spill_directory = Path(
                    tempfile.mkdtemp(
                        prefix=".ais-cleaner-spill-",
                        dir=validated_resources.temporary_directory,
                    )
                )
            with duckdb.connect(str(temporary / "work.duckdb")) as connection:
                connection.execute("SET TimeZone = 'UTC'")
                if validated_resources is not None and spill_directory is not None:
                    execution_resources = _configure_duckdb_resources(
                        connection, validated_resources, spill_directory
                    )
                stages, removals, normalizations, temporal_coverage = _collect_counts(
                    connection, config, input_path
                )
                _write_cleaned_parquet(
                    connection, config, input_path, cleaned_temporary
                )
        except duckdb.Error as exc:
            raise AISProcessingError(
                f"could not process AIS CSV {input_path}: {exc}"
            ) from exc
        finally:
            if spill_directory is not None:
                shutil.rmtree(spill_directory)
                if execution_resources is not None:
                    execution_resources[
                        "spill_directory_removed_after_run"
                    ] = not spill_directory.exists()
        work_database = temporary / "work.duckdb"
        if work_database.exists():
            work_database.unlink()
        cleaned_sha256 = _sha256(cleaned_temporary)
        run_material = {
            "contract": AIS_PROCESSING_CONTRACT,
            "processing_version": AIS_PROCESSING_VERSION,
            "input_sha256": input_sha256,
            "configuration_sha256": config.digest(),
            "parameters": parameters,
            "output_sha256": cleaned_sha256,
        }
        run_id = (
            "ais-"
            + hashlib.sha256(_canonical_json(run_material).encode("utf-8")).hexdigest()[
                :24
            ]
        )
        final_cleaned = output_directory / CLEANED_FILENAME
        final_quality = output_directory / QUALITY_REPORT_FILENAME
        quality_payload: dict[str, object] = {
            "contract": AIS_PROCESSING_CONTRACT,
            "run_id": run_id,
            "status": "success",
            "input": {
                "path": str(input_path),
                "bytes": input_path.stat().st_size,
                "sha256": input_sha256,
            },
            "configuration": {
                "version": config.schema_version,
                "sha256": config.digest(),
                "analytical_period": config.analytical_period.to_dict(),
                "analytical_domain_status": (config.spatial.analytical_domain_status),
            },
            "temporal_coverage": temporal_coverage.to_dict(),
            "processing_parameters": parameters,
            "counts": {
                "stage_rows": stages,
                "removals": removals,
                "normalizations": normalizations,
            },
            "output": {
                "path": str(final_cleaned),
                "bytes": cleaned_temporary.stat().st_size,
                "sha256": cleaned_sha256,
                "rows": stages["final_rows"],
                "parquet": parameters["parquet"],
            },
            "scope_note": (
                "Rows are scoped to the accepted map/context extent, not clipped "
                "to the separately configured accepted analytical domain. This "
                "output is not a reporting-domain result."
            ),
        }
        _write_json(quality_temporary, quality_payload)
        quality_sha256 = _sha256(quality_temporary)
        completed_at = _clock_timestamp(clock, "completion")
        foundation_metadata = RunMetadata(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            configuration_version=config.schema_version,
            configuration_sha256=config.digest(),
            steps=(
                ProcessingStep("validate-noaa-flat-csv-header", "1.0.0"),
                ProcessingStep("clean-and-scope-ais-extract", AIS_PROCESSING_VERSION),
                ProcessingStep("write-deterministic-parquet", "1.0.0"),
            ),
            inputs=(
                ArtifactReference(
                    artifact_id="supplied-ais-csv",
                    locator=str(input_path),
                    sha256=input_sha256,
                ),
            ),
            outputs=(
                ArtifactReference(
                    artifact_id="cleaned-ais-parquet",
                    locator=str(final_cleaned),
                    sha256=cleaned_sha256,
                ),
                ArtifactReference(
                    artifact_id="ais-quality-report",
                    locator=str(final_quality),
                    sha256=quality_sha256,
                ),
            ),
            validations=(
                ValidationRecord.from_counts(
                    "ais-row-accounting",
                    True,
                    {**stages, **removals, **normalizations},
                    (
                        "all source rows are retained or assigned a counted removal "
                        "reason",
                    ),
                ),
            ),
        )
        metadata_payload = {
            "contract": AIS_PROCESSING_CONTRACT,
            "run": foundation_metadata.to_dict(),
            "analytical_period": config.analytical_period.to_dict(),
            "processing_parameters": parameters,
            "runtime": _runtime(),
            "execution_timestamp_semantics": (
                "started_at and completed_at are real UTC execution timestamps; "
                "they are separate from the configured analytical period and are "
                "excluded from the deterministic run identifier"
            ),
        }
        if execution_resources is not None:
            metadata_payload["execution_resources"] = execution_resources
        _write_json(metadata_temporary, metadata_payload)
        _publish_bundle(temporary, output_directory, overwrite)
    except (AISProcessingError, AISValidationError, OSError, ValueError):
        _cleanup_bundle_directory(temporary)
        raise
    return AISProcessingResult(
        run_id=run_id,
        output_directory=output_directory,
        cleaned_parquet=output_directory / CLEANED_FILENAME,
        quality_report=output_directory / QUALITY_REPORT_FILENAME,
        run_metadata=output_directory / RUN_METADATA_FILENAME,
        input_rows=stages["source_rows"],
        output_rows=stages["final_rows"],
        output_sha256=cleaned_sha256,
    )
