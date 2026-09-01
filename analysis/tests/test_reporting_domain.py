from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.reporting_domain import (
    ReportingDomainError,
    load_default_reporting_domain,
    reporting_domain_from_mapping,
)

_UPSTREAM_CONFIG_SHA256 = (
    "df60aa03796ca979eff5bdca4c620fbac809a797d40d320ea649276d6c889c06"
)


def _document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "spatial_roles": {
            "map_context": {
                "id": "southern_california_map_context_v1",
                "purpose": "map_and_context",
            },
            "modeled_whale_support": {
                "id": "noaa_swfsc_blue_whale_summer_fall_2020b_support_v1",
                "purpose": "modeled_whale_support_water_geometry",
                "basis": "union_of_selected_model_polygons",
            },
        },
        "analytical_domain": {
            "id": "receivers_50_nautical_miles",
            "status": "accepted",
            "scope": "scope_reduced",
            "qualification": "system_performance_qualified",
            "distance_nautical_miles": 50,
            "distance_m": 92600,
            "measured_from": "relevant_nais_reception_stations",
            "geometry_basis": (
                "union_of_station_buffers_intersected_with_modeled_whale_support"
            ),
            "boundary_cell_treatment": "exact_fractional_geometry",
            "distance_from_coast": False,
            "empirical_2024_coverage": False,
            "outside_cell_treatment": (
                "exclude_from_headline_statistics_not_low_traffic"
            ),
            "limitations": {
                "receiver_uptime_2024": "unknown",
                "station_completeness": "unknown",
                "feed_interruptions": "unknown",
                "antenna_and_terrain_effects": "not_empirically_modeled",
                "observational_completeness": "unverified",
            },
        },
    }


def test_default_reporting_domain_validates_independently() -> None:
    contract = load_default_reporting_domain()

    assert contract.to_dict() == _document()


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("schema_version",), 2, "schema_version must be 1"),
        (
            ("spatial_roles", "map_context", "id"),
            "generic_context",
            "map context id",
        ),
        (
            ("spatial_roles", "map_context", "purpose"),
            "reporting_domain",
            "map context purpose",
        ),
        (
            ("spatial_roles", "modeled_whale_support", "id"),
            "generic_water",
            "modeled whale support id",
        ),
        (
            ("spatial_roles", "modeled_whale_support", "purpose"),
            "map_extent",
            "modeled whale support purpose",
        ),
        (
            ("spatial_roles", "modeled_whale_support", "basis"),
            "shoreline",
            "modeled whale support basis",
        ),
        (("analytical_domain", "id"), "coast_buffer", "analytical domain id"),
        (("analytical_domain", "status"), "proposed", "status must be 'accepted'"),
        (("analytical_domain", "scope"), "complete", "scope must be scope-reduced"),
        (
            ("analytical_domain", "qualification"),
            "observed_coverage",
            "system-performance-qualified",
        ),
        (
            ("analytical_domain", "distance_nautical_miles"),
            40,
            "50 nautical miles",
        ),
        (("analytical_domain", "distance_m"), 92500, "92,600 metres"),
        (
            ("analytical_domain", "measured_from"),
            "coast",
            "relevant NAIS reception stations",
        ),
        (
            ("analytical_domain", "geometry_basis"),
            "full_map_extent",
            "receiver buffers",
        ),
        (
            ("analytical_domain", "boundary_cell_treatment"),
            "centroid",
            "exact fractional geometry",
        ),
        (
            ("analytical_domain", "distance_from_coast"),
            True,
            "not be measured from the coast",
        ),
        (
            ("analytical_domain", "empirical_2024_coverage"),
            True,
            "not claim empirical 2024",
        ),
        (
            ("analytical_domain", "outside_cell_treatment"),
            "low_traffic",
            "not classified as low traffic",
        ),
        (
            ("analytical_domain", "limitations", "receiver_uptime_2024"),
            "verified",
            "preserve the accepted unknowns",
        ),
        (
            ("analytical_domain", "limitations", "station_completeness"),
            "complete",
            "preserve the accepted unknowns",
        ),
        (
            ("analytical_domain", "limitations", "feed_interruptions"),
            "none",
            "preserve the accepted unknowns",
        ),
        (
            ("analytical_domain", "limitations", "antenna_and_terrain_effects"),
            "modeled",
            "preserve the accepted unknowns",
        ),
        (
            (
                "analytical_domain",
                "limitations",
                "observational_completeness",
            ),
            "verified",
            "preserve the accepted unknowns",
        ),
    ],
)
def test_rejects_changed_reporting_domain_semantics(
    path: tuple[str, ...], value: object, message: str
) -> None:
    document = deepcopy(_document())
    target: dict[str, Any] = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ReportingDomainError, match=message):
        reporting_domain_from_mapping(document)


def test_reporting_domain_changes_cannot_change_upstream_config_digest() -> None:
    processing = load_default_config()
    changed_domain = _document()
    changed_domain["analytical_domain"]["status"] = "proposed"

    with pytest.raises(ReportingDomainError, match="status must be 'accepted'"):
        reporting_domain_from_mapping(changed_domain)

    assert processing.schema_version == 1
    assert processing.digest() == _UPSTREAM_CONFIG_SHA256
