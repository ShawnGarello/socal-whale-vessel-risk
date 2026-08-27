"""Selected blue-whale model contract and read-only validation."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import pyarrow as pa
import pyogrio
from pyogrio.errors import DataLayerError, DataSourceError, FieldError

WHALE_LAYER_NAME: Final = "Blue_whale_summer_fall"
WHALE_SOURCE_CRS: Final = "EPSG:4326"
WHALE_GEOMETRY_TYPE: Final = "MultiPolygon"
WHALE_DENSITY_UNIT: Final = "animals/km²"
WHALE_UNCERTAINTY_MEANING: Final = "coefficient of variation"
WHALE_SEASON: Final = "Summer-Fall"
ABUNDANCE_ABSOLUTE_TOLERANCE: Final = 1e-6
ABUNDANCE_RELATIVE_TOLERANCE: Final = 1e-6

WHALE_PUBLISHED_FIELDS: Final = (
    "UID",
    "SPECIES",
    "SPECIES_2",
    "MONTH_NUMB",
    "MONTH_NAME",
    "STUDY",
    "STRATUM",
    "MODEL_TYPE",
    "DENSITY",
    "UNCERTAINTY",
    "UNCER_QUAL",
    "MODEL_VERS",
    "NAEMO_VERS",
    "SEASON",
    "AREA_SQKM",
    "ABUNDANCE",
    "Shape_Length",
    "Shape_Area",
)

WHALE_VALIDATION_FIELDS: Final = (
    "MONTH_NUMB",
    "MONTH_NAME",
    "DENSITY",
    "UNCERTAINTY",
    "SEASON",
    "AREA_SQKM",
    "ABUNDANCE",
)


class WhaleValidationError(ValueError):
    """Raised when the selected whale source cannot satisfy its contract."""


class WhaleSchemaError(WhaleValidationError):
    """Raised when layer, fields, geometry type, or CRS do not match."""


@dataclass(frozen=True, slots=True)
class WhaleValidationResult:
    """Auditable value checks for the selected multi-year whale surface."""

    path: str
    layer: str
    feature_count: int
    attribute_row_count: int
    missing_required_value_rows: int
    invalid_density_rows: int
    invalid_area_rows: int
    invalid_abundance_rows: int
    inconsistent_abundance_rows: int
    invalid_uncertainty_rows: int
    wrong_season_rows: int
    populated_month_rows: int

    @property
    def passed(self) -> bool:
        return (
            self.feature_count > 0
            and self.feature_count == self.attribute_row_count
            and not any(
                (
                    self.missing_required_value_rows,
                    self.invalid_density_rows,
                    self.invalid_area_rows,
                    self.invalid_abundance_rows,
                    self.inconsistent_abundance_rows,
                    self.invalid_uncertainty_rows,
                    self.wrong_season_rows,
                    self.populated_month_rows,
                )
            )
        )

    def messages(self) -> list[str]:
        messages: list[str] = []
        if self.feature_count == 0:
            messages.append("selected whale layer contains no features")
        if self.feature_count != self.attribute_row_count:
            messages.append(
                "geometry feature count does not match the validated attribute rows"
            )
        checks = (
            (self.missing_required_value_rows, "missing required numeric values"),
            (self.invalid_density_rows, "invalid DENSITY values"),
            (self.invalid_area_rows, "invalid AREA_SQKM values"),
            (self.invalid_abundance_rows, "invalid ABUNDANCE values"),
            (
                self.inconsistent_abundance_rows,
                "ABUNDANCE values inconsistent with DENSITY * AREA_SQKM",
            ),
            (self.invalid_uncertainty_rows, "invalid coefficient-of-variation values"),
            (self.wrong_season_rows, "values outside the Summer-Fall surface"),
            (self.populated_month_rows, "month values in a non-time-series surface"),
        )
        for count, label in checks:
            if count:
                messages.append(f"{count} row(s) have {label}")
        return messages

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "noaa_swfsc_blue_whale_2020b_v1",
            "path": self.path,
            "layer": self.layer,
            "source_crs": WHALE_SOURCE_CRS,
            "geometry_type": WHALE_GEOMETRY_TYPE,
            "density_unit": WHALE_DENSITY_UNIT,
            "uncertainty_meaning": WHALE_UNCERTAINTY_MEANING,
            "temporal_meaning": "single multi-year Summer-Fall surface",
            "passed": self.passed,
            "counts": {
                "feature_count": self.feature_count,
                "attribute_row_count": self.attribute_row_count,
                "missing_required_value_rows": self.missing_required_value_rows,
                "invalid_density_rows": self.invalid_density_rows,
                "invalid_area_rows": self.invalid_area_rows,
                "invalid_abundance_rows": self.invalid_abundance_rows,
                "inconsistent_abundance_rows": self.inconsistent_abundance_rows,
                "invalid_uncertainty_rows": self.invalid_uncertainty_rows,
                "wrong_season_rows": self.wrong_season_rows,
                "populated_month_rows": self.populated_month_rows,
            },
            "messages": self.messages(),
        }


def validate_whale_schema(fields: Sequence[str], geometry_type: str, crs: str) -> None:
    """Require the exact inspected fields, polygon type, and WGS 84 source CRS."""
    received = tuple(fields)
    if received != WHALE_PUBLISHED_FIELDS:
        missing = [field for field in WHALE_PUBLISHED_FIELDS if field not in received]
        unexpected = [
            field for field in received if field not in WHALE_PUBLISHED_FIELDS
        ]
        details: list[str] = []
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected fields: {', '.join(unexpected)}")
        if not details:
            details.append("fields are not in the inspected order")
        raise WhaleSchemaError(
            "whale layer fields do not match the inspected 2020b product; "
            + "; ".join(details)
        )
    if geometry_type != WHALE_GEOMETRY_TYPE:
        raise WhaleSchemaError(
            f"whale geometry must be {WHALE_GEOMETRY_TYPE}, received {geometry_type}"
        )
    if crs != WHALE_SOURCE_CRS:
        raise WhaleSchemaError(
            f"whale source CRS must be {WHALE_SOURCE_CRS}, received {crs}"
        )


def _float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(cast(int | float | str, value))
    except (TypeError, ValueError):
        return math.nan


def _validate_records(records: list[dict[str, object]]) -> tuple[int, ...]:
    missing_required = 0
    invalid_density = 0
    invalid_area = 0
    invalid_abundance = 0
    inconsistent_abundance = 0
    invalid_uncertainty = 0
    wrong_season = 0
    populated_month = 0
    for record in records:
        density = _float(record["DENSITY"])
        area = _float(record["AREA_SQKM"])
        abundance = _float(record["ABUNDANCE"])
        uncertainty = _float(record["UNCERTAINTY"])
        required = (density, area, abundance, uncertainty)
        if any(value is None for value in required):
            missing_required += 1
        if density is not None and (not math.isfinite(density) or density < 0):
            invalid_density += 1
        if area is not None and (not math.isfinite(area) or area <= 0):
            invalid_area += 1
        if abundance is not None and (not math.isfinite(abundance) or abundance < 0):
            invalid_abundance += 1
        if uncertainty is not None and (
            not math.isfinite(uncertainty) or uncertainty <= 0
        ):
            invalid_uncertainty += 1
        if density is not None and area is not None and abundance is not None:
            expected = density * area
            if not math.isclose(
                abundance,
                expected,
                rel_tol=ABUNDANCE_RELATIVE_TOLERANCE,
                abs_tol=ABUNDANCE_ABSOLUTE_TOLERANCE,
            ):
                inconsistent_abundance += 1
        if record["SEASON"] != WHALE_SEASON:
            wrong_season += 1
        if record["MONTH_NUMB"] is not None or record["MONTH_NAME"] is not None:
            populated_month += 1
    return (
        missing_required,
        invalid_density,
        invalid_area,
        invalid_abundance,
        inconsistent_abundance,
        invalid_uncertainty,
        wrong_season,
        populated_month,
    )


def validate_whale_input(
    path: Path, layer: str = WHALE_LAYER_NAME
) -> WhaleValidationResult:
    """Validate the selected 2020b layer without producing an analytical output."""
    if not path.exists():
        raise WhaleValidationError(f"whale input does not exist: {path}")
    if layer != WHALE_LAYER_NAME:
        raise WhaleSchemaError(
            f"selected whale layer must be {WHALE_LAYER_NAME}, received {layer}"
        )
    try:
        info = cast(dict[str, object], pyogrio.read_info(path, layer=layer))
        fields = tuple(str(field) for field in cast(Sequence[object], info["fields"]))
        geometry_type = str(info["geometry_type"])
        crs = str(info["crs"])
        validate_whale_schema(fields, geometry_type, crs)
        _metadata, raw_table = pyogrio.read_arrow(
            path,
            layer=layer,
            columns=list(WHALE_VALIDATION_FIELDS),
            read_geometry=False,
        )
    except (DataLayerError, DataSourceError, FieldError) as exc:
        raise WhaleValidationError(f"could not read whale input {path}: {exc}") from exc
    table = cast(pa.Table, raw_table)
    records = cast(list[dict[str, object]], table.to_pylist())
    counts = _validate_records(records)
    return WhaleValidationResult(
        path=str(path),
        layer=layer,
        feature_count=int(cast(int, info["features"])),
        attribute_row_count=table.num_rows,
        missing_required_value_rows=counts[0],
        invalid_density_rows=counts[1],
        invalid_area_rows=counts[2],
        invalid_abundance_rows=counts[3],
        inconsistent_abundance_rows=counts[4],
        invalid_uncertainty_rows=counts[5],
        wrong_season_rows=counts[6],
        populated_month_rows=counts[7],
    )
