"""Method-independent, local-only fractional accounting (ADRs 0002/0004/0019).

No exposure formula, production result writer, or public geometry export lives
here. Supplied totals must already be integrated over the FULL cell water area.
Splitting them assumes uniform exposure within that water geometry.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pyarrow.parquet as pq
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.reporting_domain import load_default_reporting_domain
from whale_vessel_analysis.vsr import validate_vsr_input

DOMAIN_SHA256 = "4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77"
VSR_SHA256 = "2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783"
# Numerical conservation checks only: never use these to drop positive slivers.
AREA_ABS_TOLERANCE_M2 = 1e-6
AREA_REL_TOLERANCE = 1e-10


def _nonnegative(value: float, label: str) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{label} must be finite and nonnegative")


def _polygon(geometry: BaseGeometry, label: str, *, empty: bool = False) -> None:
    if not isinstance(geometry, (Polygon, MultiPolygon)):
        raise ValueError(f"{label} must be Polygon or MultiPolygon")
    if geometry.is_empty:
        if empty:
            return
        raise ValueError(f"{label} must not be empty")
    if geometry.has_z or shapely.has_m(geometry):
        raise ValueError(f"{label} must be two-dimensional")
    if not all(
        math.isfinite(float(v)) for xy in shapely.get_coordinates(geometry) for v in xy
    ):
        raise ValueError(f"{label} has non-finite coordinates")
    if not geometry.is_valid or not math.isfinite(geometry.area) or geometry.area <= 0:
        raise ValueError(f"{label} must be valid with finite positive area")


def _conserves(total: float, parts: tuple[float, ...]) -> bool:
    return math.isclose(
        total,
        math.fsum(parts),
        rel_tol=AREA_REL_TOLERANCE,
        abs_tol=AREA_ABS_TOLERANCE_M2,
    )


@dataclass(frozen=True)
class SplitTotal:
    """Same units as the supplied integrated total; excluded is not low traffic."""

    inside_vsr: float
    outside_vsr: float
    excluded_domain: float


@dataclass(frozen=True)
class CellAreas:
    """Exact overlay areas, all in m²; no VSR-derived geometry is exposed."""

    water_m2: float
    qualified_m2: float
    inside_vsr_m2: float
    outside_vsr_m2: float
    excluded_domain_m2: float

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _nonnegative(getattr(self, name), name)
        if self.water_m2 <= 0:
            raise ValueError("dry cells must be skipped")
        if not _conserves(self.qualified_m2, (self.inside_vsr_m2, self.outside_vsr_m2)):
            raise ValueError("inside/outside areas do not conserve qualified area")
        if not _conserves(self.water_m2, (self.qualified_m2, self.excluded_domain_m2)):
            raise ValueError("qualified/excluded areas do not conserve water area")
        for part, whole in (
            (self.qualified_m2, self.water_m2),
            (self.inside_vsr_m2, self.qualified_m2),
            (self.outside_vsr_m2, self.qualified_m2),
            (self.excluded_domain_m2, self.water_m2),
        ):
            if part > whole and not _conserves(whole, (part,)):
                raise ValueError("nested areas exceed their support")

    @property
    def inside_fraction_of_qualified(self) -> float | None:
        """Undefined for wholly excluded water; never fabricate an outside zero."""
        if self.qualified_m2 == 0:
            return None
        return self.inside_vsr_m2 / self.qualified_m2

    def split_water_total(self, total: float) -> SplitTotal:
        """Split a FULL-water integrated total, not density or a qualified total.

        Missing input is an error, not zero. Callers must handle missing support
        before invoking this primitive. No whale/vessel product is computed.
        """
        _nonnegative(total, "full-water integrated total")
        return SplitTotal(
            total * (self.inside_vsr_m2 / self.water_m2),
            total * (self.outside_vsr_m2 / self.water_m2),
            total * (self.excluded_domain_m2 / self.water_m2),
        )


@dataclass(frozen=True)
class ExposureBoundaries:
    """In-memory analytical boundaries. CRS declarations are checked, not guessed.

    Use load_local_boundaries for real inputs. Direct construction is useful for
    synthetic known-answer cases. This object must never be publicly serialized.
    """

    domain: BaseGeometry
    vsr: BaseGeometry
    crs: str

    def __post_init__(self) -> None:
        if CRS.from_user_input(self.crs) != CRS.from_epsg(3310):
            raise ValueError("boundaries must use EPSG:3310")
        _polygon(self.domain, "qualified domain")
        _polygon(self.vsr, "local VSR snapshot")
        shapely.prepare(self.domain)
        shapely.prepare(self.vsr)

    def cell_areas(self, water: BaseGeometry, *, water_crs: str) -> CellAreas | None:
        """Intersect water ∩ domain ∩ VSR; never multiply independent fractions."""
        if CRS.from_user_input(water_crs) != CRS.from_epsg(3310):
            raise ValueError("cell water must use EPSG:3310")
        _polygon(water, "cell water", empty=True)
        if water.is_empty:
            return None
        qualified = (
            water if self.domain.covers(water) else water.intersection(self.domain)
        )
        inside = (
            qualified
            if self.vsr.covers(qualified)
            else qualified.intersection(self.vsr)
        )
        outside = qualified.difference(self.vsr)
        excluded = water.difference(self.domain)
        return CellAreas(
            float(water.area),
            float(qualified.area),
            float(inside.area),
            float(outside.area),
            float(excluded.area),
        )


def load_local_boundaries(domain_path: Path, vsr_path: Path) -> ExposureBoundaries:
    """Load only the retained accepted-domain bytes and immutable local snapshot.

    Both paths are local files, read only. Geographic VSR edges are densified to
    0.01 degrees before always-xy projection, matching retained domain evidence.
    No live service, repair, simplification, output file, or alternate scenario.
    """
    for path, expected in ((domain_path, DOMAIN_SHA256), (vsr_path, VSR_SHA256)):
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"retained analytical input checksum mismatch: {path}")
    table = pq.read_table(domain_path)
    metadata = table.schema.metadata or {}
    geo = json.loads(metadata[b"geo"])
    column = geo["columns"]["geometry"]
    if geo["primary_column"] != "geometry" or column["encoding"] != "WKB":
        raise ValueError("domain must carry explicit WKB GeoParquet metadata")
    if CRS.from_user_input(column["crs"]) != CRS.from_epsg(3310):
        raise ValueError("domain must use EPSG:3310")
    accepted = load_default_reporting_domain().analytical_domain
    selected = [
        row for row in table.to_pylist() if row["scenario_id"] == accepted.domain_id
    ]
    if len(selected) != 1:
        raise ValueError("expected exactly one accepted receiver domain")
    row = selected[0]
    if row["basis"] != "receivers" or row["distance_m"] != accepted.distance_m:
        raise ValueError("domain must be 92,600 metres from reception stations")
    domain = shapely.from_wkb(row["geometry"])
    validation = validate_vsr_input(vsr_path)
    if not validation.passed:
        raise ValueError("local VSR source contract failed")
    document = json.loads(vsr_path.read_text(encoding="utf-8"))
    feature = document["features"][0]
    if feature["properties"]["FID"] != 126:
        raise ValueError("local VSR snapshot must select FID 126")
    source = shape(feature["geometry"])
    _polygon(source, "geographic VSR snapshot")
    projected = transform(
        Transformer.from_crs(4326, 3310, always_xy=True).transform,
        shapely.segmentize(source, 0.01),
    )
    return ExposureBoundaries(cast(BaseGeometry, domain), projected, "EPSG:3310")
