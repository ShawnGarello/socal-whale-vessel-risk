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

CONFIG_SCHEMA_VERSION: Final = 2
ANALYTICAL_PERIOD_START: Final = date(2024, 7, 1)
ANALYTICAL_PERIOD_END: Final = date(2024, 11, 30)
MAP_EXTENT_CRS: Final = "EPSG:4326"
PROJECTED_CRS: Final = "EPSG:3310"
GRID_CELL_SIZE_M: Final = 5_000
GRID_BOUNDS_M: Final = (-190_000, -670_000, 285_000, -330_000)
MAP_EXTENT_BOUNDS: Final = (-122.0, 32.0, -117.0, 35.0)
MAP_EXTENT_ID: Final = "southern_california_map_context_v1"
MODELED_WHALE_SUPPORT_ID: Final = "noaa_swfsc_blue_whale_summer_fall_2020b_support_v1"
ANALYTICAL_DOMAIN_ID: Final = "receivers_50_nautical_miles"
ANALYTICAL_DOMAIN_DISTANCE_NAUTICAL_MILES: Final = 50
ANALYTICAL_DOMAIN_DISTANCE_M: Final = 92_600


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

    extent_id: Literal["southern_california_map_context_v1"]
    purpose: Literal["map_and_context"]
    crs: str
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float

    def __post_init__(self) -> None:
        if self.extent_id != MAP_EXTENT_ID:
            raise ConfigurationError(f"map extent id must be {MAP_EXTENT_ID}")
        if self.purpose != "map_and_context":
            raise ConfigurationError("map extent purpose must be 'map_and_context'")
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
            "id": self.extent_id,
            "purpose": self.purpose,
            "crs": self.crs,
            "lon_min": self.lon_min,
            "lat_min": self.lat_min,
            "lon_max": self.lon_max,
            "lat_max": self.lat_max,
        }


@dataclass(frozen=True, slots=True)
class ModeledWhaleSupport:
    """The biological-support water geometry accepted in ADR 0014."""

    support_id: Literal["noaa_swfsc_blue_whale_summer_fall_2020b_support_v1"]
    purpose: Literal["modeled_whale_support_water_geometry"]
    basis: Literal["union_of_selected_model_polygons"]

    def __post_init__(self) -> None:
        if self.support_id != MODELED_WHALE_SUPPORT_ID:
            raise ConfigurationError(
                f"modeled whale support id must be {MODELED_WHALE_SUPPORT_ID}"
            )
        if self.purpose != "modeled_whale_support_water_geometry":
            raise ConfigurationError(
                "modeled whale support purpose must be "
                "'modeled_whale_support_water_geometry'"
            )
        if self.basis != "union_of_selected_model_polygons":
            raise ConfigurationError(
                "modeled whale support basis must be 'union_of_selected_model_polygons'"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.support_id,
            "purpose": self.purpose,
            "basis": self.basis,
        }


@dataclass(frozen=True, slots=True)
class AnalyticalDomainLimitations:
    """Unknowns that acceptance does not convert into observed completeness."""

    receiver_uptime_2024: Literal["unknown"]
    station_completeness: Literal["unknown"]
    feed_interruptions: Literal["unknown"]
    antenna_and_terrain_effects: Literal["not_empirically_modeled"]
    observational_completeness: Literal["unverified"]

    def __post_init__(self) -> None:
        expected = {
            "receiver_uptime_2024": "unknown",
            "station_completeness": "unknown",
            "feed_interruptions": "unknown",
            "antenna_and_terrain_effects": "not_empirically_modeled",
            "observational_completeness": "unverified",
        }
        if self.to_dict() != expected:
            raise ConfigurationError(
                "analytical domain limitations must preserve the accepted unknowns"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "receiver_uptime_2024": self.receiver_uptime_2024,
            "station_completeness": self.station_completeness,
            "feed_interruptions": self.feed_interruptions,
            "antenna_and_terrain_effects": self.antenna_and_terrain_effects,
            "observational_completeness": self.observational_completeness,
        }


@dataclass(frozen=True, slots=True)
class AnalyticalDomain:
    """The scope-reduced AIS reporting domain accepted in ADR 0002."""

    domain_id: Literal["receivers_50_nautical_miles"]
    status: Literal["accepted"]
    qualification: Literal["system_performance_qualified"]
    distance_nautical_miles: int
    distance_m: int
    measured_from: Literal["relevant_nais_reception_stations"]
    geometry_basis: Literal[
        "union_of_station_buffers_intersected_with_modeled_whale_support"
    ]
    boundary_cell_treatment: Literal["exact_fractional_geometry"]
    distance_from_coast: Literal[False]
    empirical_2024_coverage: Literal[False]
    outside_cell_treatment: Literal["exclude_from_headline_statistics_not_low_traffic"]
    limitations: AnalyticalDomainLimitations

    def __post_init__(self) -> None:
        if self.domain_id != ANALYTICAL_DOMAIN_ID:
            raise ConfigurationError(
                f"analytical domain id must be {ANALYTICAL_DOMAIN_ID}"
            )
        if self.status != "accepted":
            raise ConfigurationError("analytical domain status must be 'accepted'")
        if self.qualification != "system_performance_qualified":
            raise ConfigurationError(
                "analytical domain qualification must be 'system_performance_qualified'"
            )
        if self.distance_nautical_miles != ANALYTICAL_DOMAIN_DISTANCE_NAUTICAL_MILES:
            raise ConfigurationError(
                "analytical domain distance must be 50 nautical miles"
            )
        if self.distance_m != ANALYTICAL_DOMAIN_DISTANCE_M:
            raise ConfigurationError("analytical domain distance must be 92600 metres")
        if self.measured_from != "relevant_nais_reception_stations":
            raise ConfigurationError(
                "analytical domain distance must be measured from the relevant "
                "NAIS reception stations"
            )
        if (
            self.geometry_basis
            != "union_of_station_buffers_intersected_with_modeled_whale_support"
        ):
            raise ConfigurationError(
                "analytical domain geometry must intersect the receiver-buffer "
                "union with modeled whale support"
            )
        if self.boundary_cell_treatment != "exact_fractional_geometry":
            raise ConfigurationError(
                "analytical domain boundary cells must retain exact fractional geometry"
            )
        if self.distance_from_coast is not False:
            raise ConfigurationError(
                "analytical domain distance must not be measured from the coast"
            )
        if self.empirical_2024_coverage is not False:
            raise ConfigurationError(
                "analytical domain must not claim empirical 2024 coverage"
            )
        if (
            self.outside_cell_treatment
            != "exclude_from_headline_statistics_not_low_traffic"
        ):
            raise ConfigurationError(
                "outside cells must be excluded from headline statistics and must "
                "not be classified as low traffic"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.domain_id,
            "status": self.status,
            "qualification": self.qualification,
            "distance_nautical_miles": self.distance_nautical_miles,
            "distance_m": self.distance_m,
            "measured_from": self.measured_from,
            "geometry_basis": self.geometry_basis,
            "boundary_cell_treatment": self.boundary_cell_treatment,
            "distance_from_coast": self.distance_from_coast,
            "empirical_2024_coverage": self.empirical_2024_coverage,
            "outside_cell_treatment": self.outside_cell_treatment,
            "limitations": self.limitations.to_dict(),
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
    modeled_whale_support: ModeledWhaleSupport
    analytical_domain: AnalyticalDomain
    grid: AnalysisGrid

    def __post_init__(self) -> None:
        extent_bounds = (
            self.map_extent.lon_min,
            self.map_extent.lat_min,
            self.map_extent.lon_max,
            self.map_extent.lat_max,
        )
        if extent_bounds != MAP_EXTENT_BOUNDS:
            raise ConfigurationError(
                "map extent must match the context extent accepted in ADR 0002: "
                f"{MAP_EXTENT_BOUNDS}, received {extent_bounds}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "map_extent": self.map_extent.to_dict(),
            "modeled_whale_support": self.modeled_whale_support.to_dict(),
            "analytical_domain": self.analytical_domain.to_dict(),
            "grid": self.grid.to_dict(),
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


def _boolean(table: Mapping[str, object], key: str, table_name: str) -> bool:
    value = _required(table, key, table_name)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{table_name}.{key} must be a boolean")
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
            "map_extent",
            "modeled_whale_support",
            "analytical_domain",
        },
        "spatial",
    )
    extent_table = _mapping(
        _required(spatial_table, "map_extent", "spatial"), "spatial.map_extent"
    )
    _reject_unknown(
        extent_table,
        {"id", "purpose", "crs", "lon_min", "lat_min", "lon_max", "lat_max"},
        "spatial.map_extent",
    )
    map_extent = GeographicExtent(
        extent_id=cast(
            Literal["southern_california_map_context_v1"],
            _string(extent_table, "id", "spatial.map_extent"),
        ),
        purpose=cast(
            Literal["map_and_context"],
            _string(extent_table, "purpose", "spatial.map_extent"),
        ),
        crs=_string(extent_table, "crs", "spatial.map_extent"),
        lon_min=_number(extent_table, "lon_min", "spatial.map_extent"),
        lat_min=_number(extent_table, "lat_min", "spatial.map_extent"),
        lon_max=_number(extent_table, "lon_max", "spatial.map_extent"),
        lat_max=_number(extent_table, "lat_max", "spatial.map_extent"),
    )
    support_table = _mapping(
        _required(spatial_table, "modeled_whale_support", "spatial"),
        "spatial.modeled_whale_support",
    )
    _reject_unknown(
        support_table,
        {"id", "purpose", "basis"},
        "spatial.modeled_whale_support",
    )
    modeled_whale_support = ModeledWhaleSupport(
        support_id=cast(
            Literal["noaa_swfsc_blue_whale_summer_fall_2020b_support_v1"],
            _string(support_table, "id", "spatial.modeled_whale_support"),
        ),
        purpose=cast(
            Literal["modeled_whale_support_water_geometry"],
            _string(support_table, "purpose", "spatial.modeled_whale_support"),
        ),
        basis=cast(
            Literal["union_of_selected_model_polygons"],
            _string(support_table, "basis", "spatial.modeled_whale_support"),
        ),
    )
    domain_table = _mapping(
        _required(spatial_table, "analytical_domain", "spatial"),
        "spatial.analytical_domain",
    )
    _reject_unknown(
        domain_table,
        {
            "id",
            "status",
            "qualification",
            "distance_nautical_miles",
            "distance_m",
            "measured_from",
            "geometry_basis",
            "boundary_cell_treatment",
            "distance_from_coast",
            "empirical_2024_coverage",
            "outside_cell_treatment",
            "limitations",
        },
        "spatial.analytical_domain",
    )
    limitations_table = _mapping(
        _required(domain_table, "limitations", "spatial.analytical_domain"),
        "spatial.analytical_domain.limitations",
    )
    _reject_unknown(
        limitations_table,
        {
            "receiver_uptime_2024",
            "station_completeness",
            "feed_interruptions",
            "antenna_and_terrain_effects",
            "observational_completeness",
        },
        "spatial.analytical_domain.limitations",
    )
    limitations = AnalyticalDomainLimitations(
        receiver_uptime_2024=cast(
            Literal["unknown"],
            _string(
                limitations_table,
                "receiver_uptime_2024",
                "spatial.analytical_domain.limitations",
            ),
        ),
        station_completeness=cast(
            Literal["unknown"],
            _string(
                limitations_table,
                "station_completeness",
                "spatial.analytical_domain.limitations",
            ),
        ),
        feed_interruptions=cast(
            Literal["unknown"],
            _string(
                limitations_table,
                "feed_interruptions",
                "spatial.analytical_domain.limitations",
            ),
        ),
        antenna_and_terrain_effects=cast(
            Literal["not_empirically_modeled"],
            _string(
                limitations_table,
                "antenna_and_terrain_effects",
                "spatial.analytical_domain.limitations",
            ),
        ),
        observational_completeness=cast(
            Literal["unverified"],
            _string(
                limitations_table,
                "observational_completeness",
                "spatial.analytical_domain.limitations",
            ),
        ),
    )
    analytical_domain = AnalyticalDomain(
        domain_id=cast(
            Literal["receivers_50_nautical_miles"],
            _string(domain_table, "id", "spatial.analytical_domain"),
        ),
        status=cast(
            Literal["accepted"],
            _string(domain_table, "status", "spatial.analytical_domain"),
        ),
        qualification=cast(
            Literal["system_performance_qualified"],
            _string(domain_table, "qualification", "spatial.analytical_domain"),
        ),
        distance_nautical_miles=_integer(
            domain_table, "distance_nautical_miles", "spatial.analytical_domain"
        ),
        distance_m=_integer(domain_table, "distance_m", "spatial.analytical_domain"),
        measured_from=cast(
            Literal["relevant_nais_reception_stations"],
            _string(domain_table, "measured_from", "spatial.analytical_domain"),
        ),
        geometry_basis=cast(
            Literal["union_of_station_buffers_intersected_with_modeled_whale_support"],
            _string(domain_table, "geometry_basis", "spatial.analytical_domain"),
        ),
        boundary_cell_treatment=cast(
            Literal["exact_fractional_geometry"],
            _string(
                domain_table,
                "boundary_cell_treatment",
                "spatial.analytical_domain",
            ),
        ),
        distance_from_coast=cast(
            Literal[False],
            _boolean(domain_table, "distance_from_coast", "spatial.analytical_domain"),
        ),
        empirical_2024_coverage=cast(
            Literal[False],
            _boolean(
                domain_table,
                "empirical_2024_coverage",
                "spatial.analytical_domain",
            ),
        ),
        outside_cell_treatment=cast(
            Literal["exclude_from_headline_statistics_not_low_traffic"],
            _string(
                domain_table,
                "outside_cell_treatment",
                "spatial.analytical_domain",
            ),
        ),
        limitations=limitations,
    )
    grid = AnalysisGrid(
        projected_crs=_string(spatial_table, "projected_crs", "spatial"),
        cell_size_m=_integer(spatial_table, "grid_cell_size_m", "spatial"),
        x_min_m=_integer(spatial_table, "grid_x_min_m", "spatial"),
        y_min_m=_integer(spatial_table, "grid_y_min_m", "spatial"),
        x_max_m=_integer(spatial_table, "grid_x_max_m", "spatial"),
        y_max_m=_integer(spatial_table, "grid_y_max_m", "spatial"),
    )
    return ProcessingConfig(
        schema_version=_integer(document, "schema_version", "root"),
        analytical_period=analytical_period,
        spatial=SpatialConfig(
            map_extent=map_extent,
            modeled_whale_support=modeled_whale_support,
            analytical_domain=analytical_domain,
            grid=grid,
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
