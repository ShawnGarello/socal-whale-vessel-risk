from __future__ import annotations

import pytest

from whale_vessel_analysis.vsr import (
    VSR_GEOMETRY_TYPE,
    VSR_PUBLISHED_FIELDS,
    VSR_SOURCE_CRS,
    VSRValidationError,
    validate_vsr_schema,
)


def test_inspected_vsr_schema_is_accepted() -> None:
    validate_vsr_schema(VSR_PUBLISHED_FIELDS, VSR_GEOMETRY_TYPE, VSR_SOURCE_CRS)


def test_vsr_requires_polygon_geometry() -> None:
    with pytest.raises(VSRValidationError, match="geometry must be Polygon"):
        validate_vsr_schema(VSR_PUBLISHED_FIELDS, "LineString", VSR_SOURCE_CRS)


def test_vsr_requires_inspected_source_fields() -> None:
    fields = tuple(field for field in VSR_PUBLISHED_FIELDS if field != "Season")

    with pytest.raises(VSRValidationError, match="missing fields: Season"):
        validate_vsr_schema(fields, VSR_GEOMETRY_TYPE, VSR_SOURCE_CRS)
