"""AIS source contract and read-only DuckDB validation."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import duckdb

from whale_vessel_analysis.config import GeographicExtent

AIS_SOURCE_CRS: Final = "EPSG:4326"
AIS_TIMESTAMP_ZONE: Final = "UTC"
AIS_SPEED_UNIT: Final = "knots"
SOG_MISSING_SENTINEL: Final = 102.3
COG_MISSING_SENTINEL: Final = 360.0
HEADING_MISSING_SENTINEL: Final = 511.0

AIS_PUBLISHED_HEADER: Final = (
    "MMSI",
    "BaseDateTime",
    "LAT",
    "LON",
    "SOG",
    "COG",
    "Heading",
    "VesselName",
    "IMO",
    "CallSign",
    "VesselType",
    "Status",
    "Length",
    "Width",
    "Draft",
    "Cargo",
    "TransceiverClass",
)

AIS_PROCESSING_COLUMNS: Final = (
    "MMSI",
    "BaseDateTime",
    "LAT",
    "LON",
    "SOG",
    "VesselType",
    "Length",
)

STABLE_IDENTIFIER_FIELDS: Final = ("MMSI", "IMO", "CallSign")
MARINER_ENTERED_IDENTIFIER_FIELDS: Final = ("VesselName",)
VESSEL_TYPE_CODE_MIN: Final = 0
VESSEL_TYPE_CODE_MAX: Final = 99

_SENTINELS: Final = {
    "SOG": SOG_MISSING_SENTINEL,
    "COG": COG_MISSING_SENTINEL,
    "Heading": HEADING_MISSING_SENTINEL,
}


class AISValidationError(ValueError):
    """Raised when an AIS artifact cannot satisfy the input contract."""


class AISSchemaError(AISValidationError):
    """Raised when an AIS CSV header differs from the published schema."""


@dataclass(frozen=True, slots=True)
class AISValidationResult:
    """Auditable source-quality counts from one AIS CSV scan."""

    path: str
    total_rows: int
    rows_in_map_extent: int
    invalid_timestamp_rows: int
    invalid_coordinate_rows: int
    invalid_mmsi_rows: int
    unavailable_sog_rows: int
    invalid_sog_rows: int
    unavailable_cog_rows: int
    invalid_cog_rows: int
    unavailable_heading_rows: int
    invalid_heading_rows: int
    missing_vessel_type_rows: int
    invalid_vessel_type_rows: int

    @property
    def passed(self) -> bool:
        return self.total_rows > 0 and not any(
            (
                self.invalid_timestamp_rows,
                self.invalid_coordinate_rows,
                self.invalid_mmsi_rows,
                self.invalid_sog_rows,
                self.invalid_cog_rows,
                self.invalid_heading_rows,
                self.missing_vessel_type_rows,
                self.invalid_vessel_type_rows,
            )
        )

    def messages(self) -> list[str]:
        messages: list[str] = []
        if self.total_rows == 0:
            messages.append("AIS input contains no data rows")
        checks = (
            (self.invalid_timestamp_rows, "invalid UTC timestamps"),
            (self.invalid_coordinate_rows, "missing or invalid WGS 84 coordinates"),
            (self.invalid_mmsi_rows, "missing or malformed stable MMSI values"),
            (self.invalid_sog_rows, "missing or invalid SOG values"),
            (self.invalid_cog_rows, "missing or invalid COG values"),
            (self.invalid_heading_rows, "missing or invalid Heading values"),
            (self.missing_vessel_type_rows, "missing vessel-type codes"),
            (self.invalid_vessel_type_rows, "invalid vessel-type codes"),
        )
        for count, label in checks:
            if count:
                messages.append(f"{count} row(s) have {label}")
        return messages

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "noaa_marine_cadastre_ais_flat_csv_v1",
            "path": self.path,
            "source_crs": AIS_SOURCE_CRS,
            "timestamp_zone": AIS_TIMESTAMP_ZONE,
            "speed_unit": AIS_SPEED_UNIT,
            "passed": self.passed,
            "counts": {
                "total_rows": self.total_rows,
                "rows_in_map_extent": self.rows_in_map_extent,
                "invalid_timestamp_rows": self.invalid_timestamp_rows,
                "invalid_coordinate_rows": self.invalid_coordinate_rows,
                "invalid_mmsi_rows": self.invalid_mmsi_rows,
                "unavailable_sog_rows": self.unavailable_sog_rows,
                "invalid_sog_rows": self.invalid_sog_rows,
                "unavailable_cog_rows": self.unavailable_cog_rows,
                "invalid_cog_rows": self.invalid_cog_rows,
                "unavailable_heading_rows": self.unavailable_heading_rows,
                "invalid_heading_rows": self.invalid_heading_rows,
                "missing_vessel_type_rows": self.missing_vessel_type_rows,
                "invalid_vessel_type_rows": self.invalid_vessel_type_rows,
            },
            "messages": self.messages(),
        }


def validate_header(header: Sequence[str]) -> None:
    """Require the exact published flat-CSV header and order."""
    received = tuple(header)
    if received == AIS_PUBLISHED_HEADER:
        return
    missing = [name for name in AIS_PUBLISHED_HEADER if name not in received]
    unexpected = [name for name in received if name not in AIS_PUBLISHED_HEADER]
    details: list[str] = []
    if missing:
        details.append(f"missing columns: {', '.join(missing)}")
    if unexpected:
        details.append(f"unexpected columns: {', '.join(unexpected)}")
    if not missing and not unexpected:
        details.append("columns are not in the published order")
    raise AISSchemaError(
        "AIS header does not match the published schema; " + "; ".join(details)
    )


def read_header(path: Path) -> tuple[str, ...]:
    """Read and validate the first CSV record without loading the input."""
    if not path.is_file():
        raise AISValidationError(f"AIS input does not exist: {path}")
    try:
        with path.open("r", encoding="utf-8", newline="") as source:
            header = next(csv.reader(source), None)
    except UnicodeDecodeError as exc:
        raise AISValidationError(f"AIS input is not UTF-8 CSV: {path}") from exc
    if header is None:
        raise AISSchemaError(f"AIS input is empty: {path}")
    validate_header(header)
    return tuple(header)


def normalize_documented_measurement(
    field: str, value: str | float | None
) -> float | None:
    """Parse one retained measurement and convert its documented sentinel to null."""
    try:
        sentinel = _SENTINELS[field]
    except KeyError as exc:
        raise AISValidationError(
            f"no documented sentinel contract for field {field}"
        ) from exc
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise AISValidationError(f"{field} value is not numeric: {value!r}") from exc
    return None if parsed == sentinel else parsed


def validate_ais_csv(path: Path, extent: GeographicExtent) -> AISValidationResult:
    """Scan one AIS CSV and return schema, parsing, sentinel, and range checks."""
    read_header(path)
    query = """
        WITH source AS (
            SELECT * FROM read_csv(?, header = true, all_varchar = true)
        ),
        parsed AS (
            SELECT
                MMSI,
                BaseDateTime,
                LAT,
                LON,
                SOG,
                COG,
                Heading,
                VesselType,
                try_strptime(BaseDateTime, '%Y-%m-%dT%H:%M:%S') AS observed_at,
                try_cast(LAT AS DOUBLE) AS latitude,
                try_cast(LON AS DOUBLE) AS longitude,
                try_cast(SOG AS DOUBLE) AS sog_knots,
                try_cast(COG AS DOUBLE) AS cog_degrees,
                try_cast(Heading AS DOUBLE) AS heading_degrees,
                try_cast(VesselType AS INTEGER) AS vessel_type_code
            FROM source
        )
        SELECT
            count(*) AS total_rows,
            count(*) FILTER (
                WHERE observed_at IS NOT NULL
                  AND longitude BETWEEN ? AND ?
                  AND latitude BETWEEN ? AND ?
            ) AS rows_in_map_extent,
            count(*) FILTER (WHERE observed_at IS NULL) AS invalid_timestamp_rows,
            count(*) FILTER (
                WHERE latitude IS NULL OR longitude IS NULL
                   OR NOT isfinite(latitude) OR NOT isfinite(longitude)
                   OR latitude NOT BETWEEN -90.0 AND 90.0
                   OR longitude NOT BETWEEN -180.0 AND 180.0
            ) AS invalid_coordinate_rows,
            count(*) FILTER (
                WHERE NOT coalesce(regexp_full_match(MMSI, '[1-9][0-9]{8}'), false)
            ) AS invalid_mmsi_rows,
            count(*) FILTER (WHERE sog_knots = 102.3) AS unavailable_sog_rows,
            count(*) FILTER (
                WHERE sog_knots IS NULL OR NOT isfinite(sog_knots) OR sog_knots < 0.0
            ) AS invalid_sog_rows,
            count(*) FILTER (WHERE cog_degrees = 360.0) AS unavailable_cog_rows,
            count(*) FILTER (
                WHERE cog_degrees IS NULL
                   OR NOT isfinite(cog_degrees)
                   OR cog_degrees < 0.0
                   OR cog_degrees > 360.0
            ) AS invalid_cog_rows,
            count(*) FILTER (WHERE heading_degrees = 511.0)
                AS unavailable_heading_rows,
            count(*) FILTER (
                WHERE heading_degrees IS NULL
                   OR NOT isfinite(heading_degrees)
                   OR heading_degrees < 0.0
                   OR heading_degrees > 511.0
            ) AS invalid_heading_rows,
            count(*) FILTER (
                WHERE VesselType IS NULL OR trim(VesselType) = ''
            ) AS missing_vessel_type_rows,
            count(*) FILTER (
                WHERE VesselType IS NOT NULL AND trim(VesselType) != ''
                  AND (
                    vessel_type_code IS NULL
                    OR vessel_type_code NOT BETWEEN 0 AND 99
                  )
            ) AS invalid_vessel_type_rows
        FROM parsed
    """
    parameters: list[str | float] = [
        str(path),
        extent.lon_min,
        extent.lon_max,
        extent.lat_min,
        extent.lat_max,
    ]
    try:
        with duckdb.connect() as connection:
            row = connection.execute(query, parameters).fetchone()
    except duckdb.Error as exc:
        raise AISValidationError(f"could not read AIS CSV {path}: {exc}") from exc
    if row is None:
        raise AISValidationError(f"AIS validation returned no result for {path}")
    counts = cast(tuple[int, ...], row)
    return AISValidationResult(str(path), *(int(value) for value in counts))
