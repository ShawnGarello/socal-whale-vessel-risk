from __future__ import annotations

import pytest

from whale_vessel_analysis.whale import (
    WHALE_GEOMETRY_TYPE,
    WHALE_PUBLISHED_FIELDS,
    WHALE_SOURCE_CRS,
    WhaleSchemaError,
    validate_whale_attributes,
    validate_whale_schema,
)


def _record(**updates: object) -> dict[str, object]:
    record: dict[str, object] = {
        "MONTH_NUMB": None,
        "MONTH_NAME": None,
        "DENSITY": 0.02,
        "UNCERTAINTY": 0.4,
        "SEASON": "Summer-Fall",
        "AREA_SQKM": 50.0,
        "ABUNDANCE": 1.0,
    }
    record.update(updates)
    return record


def test_inspected_whale_schema_is_accepted() -> None:
    validate_whale_schema(WHALE_PUBLISHED_FIELDS, WHALE_GEOMETRY_TYPE, WHALE_SOURCE_CRS)


def test_missing_whale_field_is_rejected() -> None:
    fields = tuple(field for field in WHALE_PUBLISHED_FIELDS if field != "DENSITY")

    with pytest.raises(WhaleSchemaError, match="missing fields: DENSITY"):
        validate_whale_schema(fields, WHALE_GEOMETRY_TYPE, WHALE_SOURCE_CRS)


@pytest.mark.parametrize(
    ("geometry_type", "crs", "message"),
    [
        ("Point", WHALE_SOURCE_CRS, "geometry must be MultiPolygon"),
        (WHALE_GEOMETRY_TYPE, "EPSG:3857", "source CRS must be EPSG:4326"),
    ],
)
def test_wrong_whale_spatial_contract_is_rejected(
    geometry_type: str, crs: str, message: str
) -> None:
    with pytest.raises(WhaleSchemaError, match=message):
        validate_whale_schema(WHALE_PUBLISHED_FIELDS, geometry_type, crs)


def test_consistent_single_surface_attributes_are_accepted() -> None:
    result = validate_whale_attributes([_record()])

    assert result.passed


def test_abundance_must_equal_density_times_area() -> None:
    result = validate_whale_attributes([_record(ABUNDANCE=1.5)])

    assert not result.passed
    assert result.inconsistent_abundance_rows == 1


def test_uncertainty_is_positive_coefficient_of_variation() -> None:
    result = validate_whale_attributes([_record(UNCERTAINTY=-99999)])

    assert not result.passed
    assert result.invalid_uncertainty_rows == 1


def test_whale_surface_is_not_a_time_series() -> None:
    result = validate_whale_attributes(
        [_record(SEASON="Winter-Spring", MONTH_NUMB=7, MONTH_NAME="July")]
    )

    assert not result.passed
    assert result.wrong_season_rows == 1
    assert result.populated_month_rows == 1
