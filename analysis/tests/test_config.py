from __future__ import annotations

from typing import Any

import pytest

from whale_vessel_analysis.config import (
    ConfigurationError,
    config_from_mapping,
    load_default_config,
)


def _document() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "analytical_period": {
            "start_date": "2024-07-01",
            "end_date": "2024-11-30",
        },
        "spatial": {
            "projected_crs": "EPSG:3310",
            "grid_cell_size_m": 5000,
            "grid_x_min_m": -190000,
            "grid_y_min_m": -670000,
            "grid_x_max_m": 285000,
            "grid_y_max_m": -330000,
            "map_extent": {
                "id": "southern_california_map_context_v1",
                "purpose": "map_and_context",
                "crs": "EPSG:4326",
                "lon_min": -122.0,
                "lat_min": 32.0,
                "lon_max": -117.0,
                "lat_max": 35.0,
            },
            "modeled_whale_support": {
                "id": "noaa_swfsc_blue_whale_summer_fall_2020b_support_v1",
                "purpose": "modeled_whale_support_water_geometry",
                "basis": "union_of_selected_model_polygons",
            },
            "analytical_domain": {
                "id": "receivers_50_nautical_miles",
                "status": "accepted",
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
        },
    }


def test_default_configuration_records_settled_spatial_invariants() -> None:
    config = load_default_config()

    assert config.schema_version == 2
    assert config.analytical_period.to_dict() == {
        "start_date": "2024-07-01",
        "end_date": "2024-11-30",
    }
    assert config.spatial.map_extent.to_dict() == {
        "id": "southern_california_map_context_v1",
        "purpose": "map_and_context",
        "crs": "EPSG:4326",
        "lon_min": -122.0,
        "lat_min": 32.0,
        "lon_max": -117.0,
        "lat_max": 35.0,
    }
    assert config.spatial.grid.projected_crs == "EPSG:3310"
    assert config.spatial.grid.cell_size_m == 5000
    assert config.spatial.grid.columns == 95
    assert config.spatial.grid.rows == 68
    assert config.spatial.modeled_whale_support.to_dict() == {
        "id": "noaa_swfsc_blue_whale_summer_fall_2020b_support_v1",
        "purpose": "modeled_whale_support_water_geometry",
        "basis": "union_of_selected_model_polygons",
    }
    assert config.spatial.analytical_domain.to_dict() == {
        "id": "receivers_50_nautical_miles",
        "status": "accepted",
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
        "outside_cell_treatment": ("exclude_from_headline_statistics_not_low_traffic"),
        "limitations": {
            "receiver_uptime_2024": "unknown",
            "station_completeness": "unknown",
            "feed_interruptions": "unknown",
            "antenna_and_terrain_effects": "not_empirically_modeled",
            "observational_completeness": "unverified",
        },
    }
    assert config.digest() == (
        "897f538854370c8f8ae2ff4f0e20ccad591f4ab8987152040d260567fd7d4caf"
    )


@pytest.mark.parametrize("key", ["start_date", "end_date"])
def test_rejects_period_outside_accepted_analytical_window(key: str) -> None:
    document = _document()
    document["analytical_period"][key] = "2024-06-30"

    with pytest.raises(ConfigurationError, match="analytical period must be"):
        config_from_mapping(document)


def test_rejects_invalid_period_date() -> None:
    document = _document()
    document["analytical_period"]["start_date"] = "not-a-date"

    with pytest.raises(ConfigurationError, match="must be an ISO date"):
        config_from_mapping(document)


def test_rejects_noncanonical_iso_period_date() -> None:
    document = _document()
    document["analytical_period"]["start_date"] = "20240701"

    with pytest.raises(ConfigurationError, match="must be an ISO date"):
        config_from_mapping(document)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("projected_crs", "EPSG:3857", "analysis CRS must be EPSG:3310"),
        ("grid_cell_size_m", 10000, "grid cell size must be 5000"),
    ],
)
def test_rejects_changed_grid_choices(key: str, value: object, message: str) -> None:
    document = _document()
    document["spatial"][key] = value

    with pytest.raises(ConfigurationError, match=message):
        config_from_mapping(document)


def test_rejects_configuration_schema_v1_instead_of_reinterpreting_it() -> None:
    document = _document()
    document["schema_version"] = 1

    with pytest.raises(ConfigurationError, match="schema_version must be 2"):
        config_from_mapping(document)


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        (
            "map_extent",
            "id",
            "generic_extent",
            "map extent id must be southern_california_map_context_v1",
        ),
        (
            "map_extent",
            "purpose",
            "analysis",
            "map extent purpose must be 'map_and_context'",
        ),
        (
            "modeled_whale_support",
            "id",
            "generic_water",
            "modeled whale support id must be",
        ),
        (
            "modeled_whale_support",
            "purpose",
            "shoreline",
            "modeled whale support purpose must be",
        ),
        (
            "modeled_whale_support",
            "basis",
            "coastline",
            "modeled whale support basis must be",
        ),
        (
            "analytical_domain",
            "id",
            "coast_50_nautical_miles",
            "analytical domain id must be receivers_50_nautical_miles",
        ),
        (
            "analytical_domain",
            "status",
            "unresolved",
            "analytical domain status must be 'accepted'",
        ),
        (
            "analytical_domain",
            "qualification",
            "observed_coverage",
            "analytical domain qualification must be",
        ),
        (
            "analytical_domain",
            "distance_nautical_miles",
            40,
            "distance must be 50 nautical miles",
        ),
        (
            "analytical_domain",
            "distance_m",
            92500,
            "distance must be 92600 metres",
        ),
        (
            "analytical_domain",
            "measured_from",
            "coast",
            "measured from the relevant NAIS reception stations",
        ),
        (
            "analytical_domain",
            "geometry_basis",
            "full_map_extent",
            "geometry must intersect the receiver-buffer union",
        ),
        (
            "analytical_domain",
            "boundary_cell_treatment",
            "centroid",
            "boundary cells must retain exact fractional geometry",
        ),
        (
            "analytical_domain",
            "distance_from_coast",
            True,
            "must not be measured from the coast",
        ),
        (
            "analytical_domain",
            "empirical_2024_coverage",
            True,
            "must not claim empirical 2024 coverage",
        ),
        (
            "analytical_domain",
            "outside_cell_treatment",
            "low_traffic",
            "excluded from headline statistics",
        ),
    ],
)
def test_rejects_changed_spatial_domain_semantics(
    section: str, key: str, value: object, message: str
) -> None:
    document = _document()
    document["spatial"][section][key] = value

    with pytest.raises(ConfigurationError, match=message):
        config_from_mapping(document)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("receiver_uptime_2024", "verified"),
        ("station_completeness", "complete"),
        ("feed_interruptions", "none"),
        ("antenna_and_terrain_effects", "modeled"),
        ("observational_completeness", "verified"),
    ],
)
def test_rejects_upgrading_accepted_domain_limitations(key: str, value: object) -> None:
    document = _document()
    document["spatial"]["analytical_domain"]["limitations"][key] = value

    with pytest.raises(ConfigurationError, match="preserve the accepted unknowns"):
        config_from_mapping(document)


def test_rejects_changed_map_extent() -> None:
    document = _document()
    document["spatial"]["map_extent"]["lon_min"] = -121.0

    with pytest.raises(ConfigurationError, match="map extent must match"):
        config_from_mapping(document)


def test_rejects_unknown_setting_instead_of_ignoring_it() -> None:
    document = _document()
    document["spatial"]["exposure_weight"] = 2

    with pytest.raises(ConfigurationError, match="exposure_weight"):
        config_from_mapping(document)


def test_rejects_missing_required_setting() -> None:
    document = _document()
    del document["spatial"]["map_extent"]["lat_max"]

    with pytest.raises(ConfigurationError, match=r"spatial\.map_extent\.lat_max"):
        config_from_mapping(document)
