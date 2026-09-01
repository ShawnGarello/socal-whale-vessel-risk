"""Versioned downstream reporting-domain contract, independent of processing."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Final, Literal, cast

REPORTING_DOMAIN_SCHEMA_VERSION: Final = 1
MAP_CONTEXT_ID: Final = "southern_california_map_context_v1"
MODELED_WHALE_SUPPORT_ID: Final = "noaa_swfsc_blue_whale_summer_fall_2020b_support_v1"
ANALYTICAL_DOMAIN_ID: Final = "receivers_50_nautical_miles"
ANALYTICAL_DOMAIN_DISTANCE_NAUTICAL_MILES: Final = 50
ANALYTICAL_DOMAIN_DISTANCE_M: Final = 92_600


class ReportingDomainError(ValueError):
    """Raised when the reporting-domain definition violates its contract."""


@dataclass(frozen=True, slots=True)
class SpatialRoles:
    """Stable identities for context and biological-support geometry."""

    map_context_id: Literal["southern_california_map_context_v1"]
    map_context_purpose: Literal["map_and_context"]
    modeled_whale_support_id: Literal[
        "noaa_swfsc_blue_whale_summer_fall_2020b_support_v1"
    ]
    modeled_whale_support_purpose: Literal["modeled_whale_support_water_geometry"]
    modeled_whale_support_basis: Literal["union_of_selected_model_polygons"]

    def __post_init__(self) -> None:
        if self.map_context_id != MAP_CONTEXT_ID:
            raise ReportingDomainError(f"map context id must be {MAP_CONTEXT_ID}")
        if self.map_context_purpose != "map_and_context":
            raise ReportingDomainError("map context purpose must be 'map_and_context'")
        if self.modeled_whale_support_id != MODELED_WHALE_SUPPORT_ID:
            raise ReportingDomainError(
                f"modeled whale support id must be {MODELED_WHALE_SUPPORT_ID}"
            )
        if self.modeled_whale_support_purpose != "modeled_whale_support_water_geometry":
            raise ReportingDomainError(
                "modeled whale support purpose must identify water geometry"
            )
        if self.modeled_whale_support_basis != "union_of_selected_model_polygons":
            raise ReportingDomainError(
                "modeled whale support basis must be the selected model polygons"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "map_context": {
                "id": self.map_context_id,
                "purpose": self.map_context_purpose,
            },
            "modeled_whale_support": {
                "id": self.modeled_whale_support_id,
                "purpose": self.modeled_whale_support_purpose,
                "basis": self.modeled_whale_support_basis,
            },
        }


@dataclass(frozen=True, slots=True)
class ReportingDomainLimitations:
    """Operational and completeness unknowns preserved by domain acceptance."""

    receiver_uptime_2024: Literal["unknown"]
    station_completeness: Literal["unknown"]
    feed_interruptions: Literal["unknown"]
    antenna_and_terrain_effects: Literal["not_empirically_modeled"]
    observational_completeness: Literal["unverified"]

    def __post_init__(self) -> None:
        if self.to_dict() != {
            "receiver_uptime_2024": "unknown",
            "station_completeness": "unknown",
            "feed_interruptions": "unknown",
            "antenna_and_terrain_effects": "not_empirically_modeled",
            "observational_completeness": "unverified",
        }:
            raise ReportingDomainError(
                "reporting-domain limitations must preserve the accepted unknowns"
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
    """Accepted scope-reduced, system-performance-qualified AIS domain."""

    domain_id: Literal["receivers_50_nautical_miles"]
    status: Literal["accepted"]
    scope: Literal["scope_reduced"]
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
    limitations: ReportingDomainLimitations

    def __post_init__(self) -> None:
        if self.domain_id != ANALYTICAL_DOMAIN_ID:
            raise ReportingDomainError(
                f"analytical domain id must be {ANALYTICAL_DOMAIN_ID}"
            )
        if self.status != "accepted":
            raise ReportingDomainError("analytical domain status must be 'accepted'")
        if self.scope != "scope_reduced":
            raise ReportingDomainError("analytical domain scope must be scope-reduced")
        if self.qualification != "system_performance_qualified":
            raise ReportingDomainError(
                "analytical domain must be system-performance-qualified"
            )
        if self.distance_nautical_miles != ANALYTICAL_DOMAIN_DISTANCE_NAUTICAL_MILES:
            raise ReportingDomainError(
                "analytical domain distance must be 50 nautical miles"
            )
        if self.distance_m != ANALYTICAL_DOMAIN_DISTANCE_M:
            raise ReportingDomainError(
                "analytical domain distance must be 92,600 metres"
            )
        if self.measured_from != "relevant_nais_reception_stations":
            raise ReportingDomainError(
                "distance must be measured from the relevant NAIS reception stations"
            )
        if (
            self.geometry_basis
            != "union_of_station_buffers_intersected_with_modeled_whale_support"
        ):
            raise ReportingDomainError(
                "analytical geometry must intersect receiver buffers with modeled "
                "whale support"
            )
        if self.boundary_cell_treatment != "exact_fractional_geometry":
            raise ReportingDomainError(
                "boundary cells must retain exact fractional geometry"
            )
        if self.distance_from_coast is not False:
            raise ReportingDomainError("distance must not be measured from the coast")
        if self.empirical_2024_coverage is not False:
            raise ReportingDomainError(
                "the domain must not claim empirical 2024 reception coverage"
            )
        if (
            self.outside_cell_treatment
            != "exclude_from_headline_statistics_not_low_traffic"
        ):
            raise ReportingDomainError(
                "outside cells must be excluded from headline statistics, not "
                "classified as low traffic"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.domain_id,
            "status": self.status,
            "scope": self.scope,
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
class ReportingDomainContract:
    """Versioned definition consumed only by downstream reporting analysis."""

    schema_version: int
    spatial_roles: SpatialRoles
    analytical_domain: AnalyticalDomain

    def __post_init__(self) -> None:
        if self.schema_version != REPORTING_DOMAIN_SCHEMA_VERSION:
            raise ReportingDomainError(
                "reporting-domain schema_version must be "
                f"{REPORTING_DOMAIN_SCHEMA_VERSION}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "spatial_roles": self.spatial_roles.to_dict(),
            "analytical_domain": self.analytical_domain.to_dict(),
        }


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ReportingDomainError(f"{name} must be a TOML table")
    return cast(Mapping[str, object], value)


def _required(table: Mapping[str, object], key: str, name: str) -> object:
    try:
        return table[key]
    except KeyError as exc:
        raise ReportingDomainError(f"missing required setting {name}.{key}") from exc


def _reject_unknown(table: Mapping[str, object], allowed: set[str], name: str) -> None:
    unexpected = sorted(set(table) - allowed)
    if unexpected:
        raise ReportingDomainError(
            f"unexpected setting(s) in {name}: {', '.join(unexpected)}"
        )


def _string(table: Mapping[str, object], key: str, name: str) -> str:
    value = _required(table, key, name)
    if not isinstance(value, str):
        raise ReportingDomainError(f"{name}.{key} must be a string")
    return value


def _integer(table: Mapping[str, object], key: str, name: str) -> int:
    value = _required(table, key, name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ReportingDomainError(f"{name}.{key} must be an integer")
    return value


def _boolean(table: Mapping[str, object], key: str, name: str) -> bool:
    value = _required(table, key, name)
    if not isinstance(value, bool):
        raise ReportingDomainError(f"{name}.{key} must be a boolean")
    return value


def reporting_domain_from_mapping(
    document: Mapping[str, object],
) -> ReportingDomainContract:
    """Construct and strictly validate a reporting-domain definition."""
    _reject_unknown(
        document, {"schema_version", "spatial_roles", "analytical_domain"}, "root"
    )
    roles = _mapping(_required(document, "spatial_roles", "root"), "spatial_roles")
    _reject_unknown(roles, {"map_context", "modeled_whale_support"}, "spatial_roles")
    context = _mapping(
        _required(roles, "map_context", "spatial_roles"),
        "spatial_roles.map_context",
    )
    _reject_unknown(context, {"id", "purpose"}, "spatial_roles.map_context")
    support = _mapping(
        _required(roles, "modeled_whale_support", "spatial_roles"),
        "spatial_roles.modeled_whale_support",
    )
    _reject_unknown(
        support, {"id", "purpose", "basis"}, "spatial_roles.modeled_whale_support"
    )
    domain = _mapping(
        _required(document, "analytical_domain", "root"), "analytical_domain"
    )
    _reject_unknown(
        domain,
        {
            "id",
            "status",
            "scope",
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
        "analytical_domain",
    )
    limitations = _mapping(
        _required(domain, "limitations", "analytical_domain"),
        "analytical_domain.limitations",
    )
    _reject_unknown(
        limitations,
        {
            "receiver_uptime_2024",
            "station_completeness",
            "feed_interruptions",
            "antenna_and_terrain_effects",
            "observational_completeness",
        },
        "analytical_domain.limitations",
    )
    return ReportingDomainContract(
        schema_version=_integer(document, "schema_version", "root"),
        spatial_roles=SpatialRoles(
            map_context_id=cast(
                Literal["southern_california_map_context_v1"],
                _string(context, "id", "spatial_roles.map_context"),
            ),
            map_context_purpose=cast(
                Literal["map_and_context"],
                _string(context, "purpose", "spatial_roles.map_context"),
            ),
            modeled_whale_support_id=cast(
                Literal["noaa_swfsc_blue_whale_summer_fall_2020b_support_v1"],
                _string(support, "id", "spatial_roles.modeled_whale_support"),
            ),
            modeled_whale_support_purpose=cast(
                Literal["modeled_whale_support_water_geometry"],
                _string(support, "purpose", "spatial_roles.modeled_whale_support"),
            ),
            modeled_whale_support_basis=cast(
                Literal["union_of_selected_model_polygons"],
                _string(support, "basis", "spatial_roles.modeled_whale_support"),
            ),
        ),
        analytical_domain=AnalyticalDomain(
            domain_id=cast(
                Literal["receivers_50_nautical_miles"],
                _string(domain, "id", "analytical_domain"),
            ),
            status=cast(
                Literal["accepted"], _string(domain, "status", "analytical_domain")
            ),
            scope=cast(
                Literal["scope_reduced"], _string(domain, "scope", "analytical_domain")
            ),
            qualification=cast(
                Literal["system_performance_qualified"],
                _string(domain, "qualification", "analytical_domain"),
            ),
            distance_nautical_miles=_integer(
                domain, "distance_nautical_miles", "analytical_domain"
            ),
            distance_m=_integer(domain, "distance_m", "analytical_domain"),
            measured_from=cast(
                Literal["relevant_nais_reception_stations"],
                _string(domain, "measured_from", "analytical_domain"),
            ),
            geometry_basis=cast(
                Literal[
                    "union_of_station_buffers_intersected_with_modeled_whale_support"
                ],
                _string(domain, "geometry_basis", "analytical_domain"),
            ),
            boundary_cell_treatment=cast(
                Literal["exact_fractional_geometry"],
                _string(domain, "boundary_cell_treatment", "analytical_domain"),
            ),
            distance_from_coast=cast(
                Literal[False],
                _boolean(domain, "distance_from_coast", "analytical_domain"),
            ),
            empirical_2024_coverage=cast(
                Literal[False],
                _boolean(domain, "empirical_2024_coverage", "analytical_domain"),
            ),
            outside_cell_treatment=cast(
                Literal["exclude_from_headline_statistics_not_low_traffic"],
                _string(domain, "outside_cell_treatment", "analytical_domain"),
            ),
            limitations=ReportingDomainLimitations(
                receiver_uptime_2024=cast(
                    Literal["unknown"],
                    _string(
                        limitations,
                        "receiver_uptime_2024",
                        "analytical_domain.limitations",
                    ),
                ),
                station_completeness=cast(
                    Literal["unknown"],
                    _string(
                        limitations,
                        "station_completeness",
                        "analytical_domain.limitations",
                    ),
                ),
                feed_interruptions=cast(
                    Literal["unknown"],
                    _string(
                        limitations,
                        "feed_interruptions",
                        "analytical_domain.limitations",
                    ),
                ),
                antenna_and_terrain_effects=cast(
                    Literal["not_empirically_modeled"],
                    _string(
                        limitations,
                        "antenna_and_terrain_effects",
                        "analytical_domain.limitations",
                    ),
                ),
                observational_completeness=cast(
                    Literal["unverified"],
                    _string(
                        limitations,
                        "observational_completeness",
                        "analytical_domain.limitations",
                    ),
                ),
            ),
        ),
    )


def load_reporting_domain(path: Path) -> ReportingDomainContract:
    """Load a reporting-domain TOML file supplied at runtime."""
    if not path.is_file():
        raise ReportingDomainError(f"reporting-domain file does not exist: {path}")
    try:
        with path.open("rb") as source:
            document = tomllib.load(source)
    except tomllib.TOMLDecodeError as exc:
        raise ReportingDomainError(f"invalid TOML in {path}: {exc}") from exc
    return reporting_domain_from_mapping(document)


def load_default_reporting_domain() -> ReportingDomainContract:
    """Load the version-controlled downstream reporting-domain definition."""
    resource = resources.files("whale_vessel_analysis").joinpath(
        "default_reporting_domain.toml"
    )
    with resource.open("rb") as source:
        document = tomllib.load(source)
    return reporting_domain_from_mapping(document)
