from __future__ import annotations

from dataclasses import dataclass

import pytest

from whale_vessel_analysis.whale import (
    WHALE_GEOMETRY_TYPE,
    WHALE_PUBLISHED_FIELDS,
    WHALE_SOURCE_CRS,
    WhaleSchemaError,
    WhaleValidationResult,
    _geometry_from_wkb,
    validate_whale_attributes,
    validate_whale_geometries,
    validate_whale_schema,
)


@dataclass(frozen=True)
class _Geometry:
    is_empty: bool
    is_valid: bool


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


def test_geometry_validation_counts_null_empty_and_invalid_values() -> None:
    result = validate_whale_geometries(
        [None, _Geometry(is_empty=True, is_valid=True), _Geometry(False, False)]
    )

    assert not result.passed
    assert result.null_geometry_rows == 1
    assert result.empty_geometry_rows == 1
    assert result.invalid_geometry_rows == 1


def test_wkb_geometry_values_are_classified_before_layer_validation() -> None:
    empty_polygon_wkb = bytes.fromhex("010300000000000000")
    result = validate_whale_geometries(
        [
            _geometry_from_wkb(None),
            _geometry_from_wkb(empty_polygon_wkb),
            _geometry_from_wkb(b"not-wkb"),
        ]
    )

    assert result.null_geometry_rows == 1
    assert result.empty_geometry_rows == 1
    assert result.invalid_geometry_rows == 1


def test_whale_result_reports_geometry_failures_in_messages_and_json() -> None:
    result = WhaleValidationResult(
        path="synthetic.gdb",
        layer="Blue_whale_summer_fall",
        feature_count=1,
        attribute_row_count=1,
        null_geometry_rows=1,
        empty_geometry_rows=0,
        invalid_geometry_rows=0,
        missing_required_value_rows=0,
        invalid_density_rows=0,
        invalid_area_rows=0,
        invalid_abundance_rows=0,
        inconsistent_abundance_rows=0,
        invalid_uncertainty_rows=0,
        wrong_season_rows=0,
        populated_month_rows=0,
    )

    assert not result.passed
    assert result.messages() == ["1 row(s) have null geometries"]
    assert result.to_dict()["counts"]["null_geometry_rows"] == 1
