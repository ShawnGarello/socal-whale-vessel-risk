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
        "schema_version": 1,
        "spatial": {
            "projected_crs": "EPSG:3310",
            "grid_cell_size_m": 5000,
            "grid_x_min_m": -190000,
            "grid_y_min_m": -670000,
            "grid_x_max_m": 285000,
            "grid_y_max_m": -330000,
            "analytical_domain_status": "unresolved",
            "map_extent": {
                "crs": "EPSG:4326",
                "lon_min": -122.0,
                "lat_min": 32.0,
                "lon_max": -117.0,
                "lat_max": 35.0,
            },
        },
    }


def test_default_configuration_records_settled_spatial_invariants() -> None:
    config = load_default_config()

    assert config.schema_version == 1
    assert config.spatial.map_extent.to_dict() == {
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
    assert config.spatial.analytical_domain_status == "unresolved"
    assert config.digest() == (
        "617f1b3b513d15b1c7bc3a6f8bf4a13f4ad60687c9342332473c0a40051939ff"
    )


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("projected_crs", "EPSG:3857", "analysis CRS must be EPSG:3310"),
        ("grid_cell_size_m", 10000, "grid cell size must be 5000"),
        (
            "analytical_domain_status",
            "accepted",
            "analytical_domain_status must be 'unresolved'",
        ),
    ],
)
def test_rejects_unsettled_or_changed_spatial_choices(
    key: str, value: object, message: str
) -> None:
    document = _document()
    document["spatial"][key] = value

    with pytest.raises(ConfigurationError, match=message):
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
