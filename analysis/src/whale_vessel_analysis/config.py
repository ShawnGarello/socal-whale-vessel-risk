"""Versioned processing and spatial configuration contracts."""

from __future__ import annotations

import hashlib
import json
import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Final, Literal, cast

CONFIG_SCHEMA_VERSION: Final = 1
ANALYTICAL_PERIOD_START: Final = date(2024, 7, 1)
ANALYTICAL_PERIOD_END: Final = date(2024, 11, 30)
MAP_EXTENT_CRS: Final = "EPSG:4326"
PROJECTED_CRS: Final = "EPSG:3310"
GRID_CELL_SIZE_M: Final = 5_000
GRID_BOUNDS_M: Final = (-190_000, -670_000, 285_000, -330_000)
MAP_EXTENT_BOUNDS: Final = (-122.0, 32.0, -117.0, 35.0)


class ConfigurationError(ValueError):
    """Raised when processing configuration violates a settled invariant."""


@dataclass(frozen=True, slots=True)
class AnalyticalPeriod:
    """The accepted Version 1 AIS analytical period from ADR 0005."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if (self.start_date, self.end_date) != (
            ANALYTICAL_PERIOD_START,
            ANALYTICAL_PERIOD_END,
        ):
            raise ConfigurationError(
                "analytical period must be 2024-07-01 through 2024-11-30 "
                "as accepted in ADR 0005"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class GeographicExtent:
    """A WGS 84 map/context extent, separate from the analytical domain."""

    crs: str
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float

    def __post_init__(self) -> None:
        coordinates = (self.lon_min, self.lat_min, self.lon_max, self.lat_max)
        if not all(math.isfinite(value) for value in coordinates):
            raise ConfigurationError("map extent coordinates must be finite")
        if self.crs != MAP_EXTENT_CRS:
            raise ConfigurationError(f"map extent CRS must be {MAP_EXTENT_CRS}")
        if not (-180 <= self.lon_min < self.lon_max <= 180):
            raise ConfigurationError("map extent longitudes are invalid")
        if not (-90 <= self.lat_min < self.lat_max <= 90):
            raise ConfigurationError("map extent latitudes are invalid")

    def to_dict(self) -> dict[str, str | float]:
        return {
            "crs": self.crs,
            "lon_min": self.lon_min,
            "lat_min": self.lat_min,
            "lon_max": self.lon_max,
            "lat_max": self.lat_max,
        }


@dataclass(frozen=True, slots=True)
class AnalysisGrid:
    """The accepted projected grid specification from ADRs 0003 and 0004."""

    projected_crs: str
    cell_size_m: int
    x_min_m: int
    y_min_m: int
    x_max_m: int
    y_max_m: int

    def __post_init__(self) -> None:
        if self.projected_crs != PROJECTED_CRS:
            raise ConfigurationError(f"analysis CRS must be {PROJECTED_CRS}")
        if self.cell_size_m != GRID_CELL_SIZE_M:
            raise ConfigurationError(
                f"analysis grid cell size must be {GRID_CELL_SIZE_M} metres"
            )
        bounds = (self.x_min_m, self.y_min_m, self.x_max_m, self.y_max_m)
        if bounds != GRID_BOUNDS_M:
            raise ConfigurationError(
                "analysis grid bounds must match ADR 0004: "
                f"{GRID_BOUNDS_M}, received {bounds}"
            )
        if any(value % self.cell_size_m for value in bounds):
            raise ConfigurationError("analysis grid bounds must align to cell size")

    @property
    def columns(self) -> int:
        return (self.x_max_m - self.x_min_m) // self.cell_size_m

    @property
    def rows(self) -> int:
        return (self.y_max_m - self.y_min_m) // self.cell_size_m

    def to_dict(self) -> dict[str, str | int]:
        return {
            "projected_crs": self.projected_crs,
            "cell_size_m": self.cell_size_m,
            "x_min_m": self.x_min_m,
            "y_min_m": self.y_min_m,
            "x_max_m": self.x_max_m,
            "y_max_m": self.y_max_m,
            "columns": self.columns,
            "rows": self.rows,
        }


@dataclass(frozen=True, slots=True)
class SpatialConfig:
    """Spatial configuration that keeps context and reporting domains distinct."""

    map_extent: GeographicExtent
    grid: AnalysisGrid
    analytical_domain_status: Literal["unresolved"]

    def __post_init__(self) -> None:
        extent_bounds = (
            self.map_extent.lon_min,
            self.map_extent.lat_min,
            self.map_extent.lon_max,
            self.map_extent.lat_max,
        )
        if extent_bounds != MAP_EXTENT_BOUNDS:
            raise ConfigurationError(
                "map extent must match the context extent in proposed ADR 0002: "
                f"{MAP_EXTENT_BOUNDS}, received {extent_bounds}"
            )
        if self.analytical_domain_status != "unresolved":
            raise ConfigurationError(
                "analytical domain must remain 'unresolved' until ADR 0002 is accepted"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "map_extent": self.map_extent.to_dict(),
            "grid": self.grid.to_dict(),
            "analytical_domain_status": self.analytical_domain_status,
        }


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    """Versioned foundation configuration with deterministic serialization."""

    schema_version: int
    analytical_period: AnalyticalPeriod
    spatial: SpatialConfig

    def __post_init__(self) -> None:
        if self.schema_version != CONFIG_SCHEMA_VERSION:
            raise ConfigurationError(
                f"configuration schema_version must be {CONFIG_SCHEMA_VERSION}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "analytical_period": self.analytical_period.to_dict(),
            "spatial": self.spatial.to_dict(),
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be a TOML table")
    return cast(Mapping[str, object], value)


def _required(table: Mapping[str, object], key: str, table_name: str) -> object:
    try:
        return table[key]
    except KeyError as exc:
        raise ConfigurationError(
            f"missing required setting {table_name}.{key}"
        ) from exc


def _reject_unknown(
    table: Mapping[str, object], allowed: set[str], table_name: str
) -> None:
    unexpected = sorted(set(table) - allowed)
    if unexpected:
        raise ConfigurationError(
            f"unexpected setting(s) in {table_name}: {', '.join(unexpected)}"
        )


def _string(table: Mapping[str, object], key: str, table_name: str) -> str:
    value = _required(table, key, table_name)
    if not isinstance(value, str):
        raise ConfigurationError(f"{table_name}.{key} must be a string")
    return value


def _integer(table: Mapping[str, object], key: str, table_name: str) -> int:
    value = _required(table, key, table_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigurationError(f"{table_name}.{key} must be an integer")
    return value


def _number(table: Mapping[str, object], key: str, table_name: str) -> float:
    value = _required(table, key, table_name)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ConfigurationError(f"{table_name}.{key} must be a number")
    return float(value)


def _date(table: Mapping[str, object], key: str, table_name: str) -> date:
    value = _required(table, key, table_name)
    if not isinstance(value, str):
        raise ConfigurationError(f"{table_name}.{key} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigurationError(
            f"{table_name}.{key} must be an ISO date (YYYY-MM-DD)"
        ) from exc
    if parsed.isoformat() != value:
        raise ConfigurationError(f"{table_name}.{key} must be an ISO date (YYYY-MM-DD)")
    return parsed


def config_from_mapping(document: Mapping[str, object]) -> ProcessingConfig:
    """Construct and validate configuration from a parsed TOML mapping."""
    _reject_unknown(
        document, {"schema_version", "analytical_period", "spatial"}, "root"
    )
    period_table = _mapping(
        _required(document, "analytical_period", "root"), "analytical_period"
    )
    _reject_unknown(period_table, {"start_date", "end_date"}, "analytical_period")
    analytical_period = AnalyticalPeriod(
        start_date=_date(period_table, "start_date", "analytical_period"),
        end_date=_date(period_table, "end_date", "analytical_period"),
    )
    spatial_table = _mapping(_required(document, "spatial", "root"), "spatial")
    _reject_unknown(
        spatial_table,
        {
            "projected_crs",
            "grid_cell_size_m",
            "grid_x_min_m",
            "grid_y_min_m",
            "grid_x_max_m",
            "grid_y_max_m",
            "analytical_domain_status",
            "map_extent",
        },
        "spatial",
    )
    extent_table = _mapping(
        _required(spatial_table, "map_extent", "spatial"), "spatial.map_extent"
    )
    _reject_unknown(
        extent_table,
        {"crs", "lon_min", "lat_min", "lon_max", "lat_max"},
        "spatial.map_extent",
    )
    map_extent = GeographicExtent(
        crs=_string(extent_table, "crs", "spatial.map_extent"),
        lon_min=_number(extent_table, "lon_min", "spatial.map_extent"),
        lat_min=_number(extent_table, "lat_min", "spatial.map_extent"),
        lon_max=_number(extent_table, "lon_max", "spatial.map_extent"),
        lat_max=_number(extent_table, "lat_max", "spatial.map_extent"),
    )
    grid = AnalysisGrid(
        projected_crs=_string(spatial_table, "projected_crs", "spatial"),
        cell_size_m=_integer(spatial_table, "grid_cell_size_m", "spatial"),
        x_min_m=_integer(spatial_table, "grid_x_min_m", "spatial"),
        y_min_m=_integer(spatial_table, "grid_y_min_m", "spatial"),
        x_max_m=_integer(spatial_table, "grid_x_max_m", "spatial"),
        y_max_m=_integer(spatial_table, "grid_y_max_m", "spatial"),
    )
    analytical_status = _string(spatial_table, "analytical_domain_status", "spatial")
    if analytical_status != "unresolved":
        raise ConfigurationError(
            "spatial.analytical_domain_status must be 'unresolved'"
        )
    return ProcessingConfig(
        schema_version=_integer(document, "schema_version", "root"),
        analytical_period=analytical_period,
        spatial=SpatialConfig(
            map_extent=map_extent,
            grid=grid,
            analytical_domain_status="unresolved",
        ),
    )


def load_config(path: Path) -> ProcessingConfig:
    """Load a TOML configuration file supplied at runtime."""
    if not path.is_file():
        raise ConfigurationError(f"configuration file does not exist: {path}")
    try:
        with path.open("rb") as source:
            document = tomllib.load(source)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"invalid TOML in {path}: {exc}") from exc
    return config_from_mapping(document)


def load_default_config() -> ProcessingConfig:
    """Load the version-controlled configuration packaged with the project."""
    resource = resources.files("whale_vessel_analysis").joinpath("default_config.toml")
    with resource.open("rb") as source:
        document = tomllib.load(source)
    return config_from_mapping(document)
