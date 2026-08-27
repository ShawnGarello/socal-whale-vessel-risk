"""VSR source-geometry contract and read-only validation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, cast

import pyarrow as pa
import pyogrio
from pyogrio.errors import DataSourceError, FieldError, GeometryError
from shapely import from_wkb
from shapely.errors import GEOSException

VSR_SOURCE_CRS: Final = "EPSG:4326"
VSR_GEOMETRY_TYPE: Final = "Polygon"
VSR_ZONE_NAME: Final = "California Voluntary Vessel Speed Reduction Zone"
VSR_SEASON: Final = "April 22 - December 31, 2026"
VSR_SOURCE_NAME: Final = "Protecting Blue Whales & Blue Skies Coalition"

VSR_PUBLISHED_FIELDS: Final = (
    "FID",
    "Shape_Leng",
    "Shape_Area",
    "Location",
    "Name",
    "Type",
    "Species",
    "Season",
    "ShipReq",
    "Source",
    "Region",
    "Shape__Area",
    "Shape__Length",
)


class VSRValidationError(ValueError):
    """Raised when the supplied VSR geometry cannot satisfy its source contract."""


class _Geometry(Protocol):
    @property
    def is_empty(self) -> bool: ...

    @property
    def is_valid(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class VSRValidationResult:
    """Validation result for the single published 2026 California zone feature."""

    path: str
    feature_count: int
    valid_geometry: bool
    expected_name: bool
    expected_season: bool
    expected_source: bool

    @property
    def passed(self) -> bool:
        return (
            self.feature_count == 1
            and self.valid_geometry
            and self.expected_name
            and self.expected_season
            and self.expected_source
        )

    def messages(self) -> list[str]:
        messages: list[str] = []
        if self.feature_count != 1:
            messages.append("VSR source must contain exactly one selected zone feature")
        if not self.valid_geometry:
            messages.append("VSR geometry is empty or invalid")
        if not self.expected_name:
            messages.append("VSR feature name differs from the inspected source")
        if not self.expected_season:
            messages.append("VSR season differs from the inspected 2026 source")
        if not self.expected_source:
            messages.append(
                "VSR publisher attribution differs from the inspected source"
            )
        return messages

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "bwbs_california_vsr_2026_v1",
            "path": self.path,
            "source_crs": VSR_SOURCE_CRS,
            "geometry_type": VSR_GEOMETRY_TYPE,
            "passed": self.passed,
            "checks": {
                "feature_count": self.feature_count,
                "valid_geometry": self.valid_geometry,
                "expected_name": self.expected_name,
                "expected_season": self.expected_season,
                "expected_source": self.expected_source,
            },
            "messages": self.messages(),
        }


def validate_vsr_schema(fields: Sequence[str], geometry_type: str, crs: str) -> None:
    """Require the exact inspected GeoJSON fields, polygon type, and WGS 84 CRS."""
    received = tuple(fields)
    if received != VSR_PUBLISHED_FIELDS:
        missing = [field for field in VSR_PUBLISHED_FIELDS if field not in received]
        unexpected = [field for field in received if field not in VSR_PUBLISHED_FIELDS]
        details: list[str] = []
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected fields: {', '.join(unexpected)}")
        if not details:
            details.append("fields are not in the inspected order")
        raise VSRValidationError(
            "VSR fields do not match the inspected 2026 GeoJSON; " + "; ".join(details)
        )
    if geometry_type != VSR_GEOMETRY_TYPE:
        raise VSRValidationError(
            f"VSR geometry must be {VSR_GEOMETRY_TYPE}, received {geometry_type}"
        )
    if crs != VSR_SOURCE_CRS:
        raise VSRValidationError(
            f"VSR source CRS must be {VSR_SOURCE_CRS}, received {crs}"
        )


def validate_vsr_input(path: Path) -> VSRValidationResult:
    """Validate the published source geometry without copying or transforming it."""
    if not path.is_file():
        raise VSRValidationError(f"VSR input does not exist: {path}")
    try:
        info = cast(dict[str, object], pyogrio.read_info(path))
        fields = tuple(str(field) for field in cast(Sequence[object], info["fields"]))
        validate_vsr_schema(fields, str(info["geometry_type"]), str(info["crs"]))
        _metadata, raw_table = pyogrio.read_arrow(
            path,
            columns=["Name", "Season", "Source"],
            read_geometry=True,
        )
    except (DataSourceError, FieldError, GeometryError) as exc:
        raise VSRValidationError(f"could not read VSR input {path}: {exc}") from exc
    table = cast(pa.Table, raw_table)
    if table.num_rows != 1 or "wkb_geometry" not in table.column_names:
        return VSRValidationResult(
            str(path), table.num_rows, False, False, False, False
        )
    record = cast(dict[str, object], table.slice(0, 1).to_pylist()[0])
    wkb = cast(bytes | None, record["wkb_geometry"])
    try:
        geometry = cast(_Geometry | None, None if wkb is None else from_wkb(wkb))
    except GEOSException as exc:
        raise VSRValidationError(
            f"could not parse VSR geometry in {path}: {exc}"
        ) from exc
    return VSRValidationResult(
        path=str(path),
        feature_count=int(cast(int, info["features"])),
        valid_geometry=(
            geometry is not None and not geometry.is_empty and geometry.is_valid
        ),
        expected_name=record["Name"] == VSR_ZONE_NAME,
        expected_season=record["Season"] == VSR_SEASON,
        expected_source=record["Source"] == VSR_SOURCE_NAME,
    )
