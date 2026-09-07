"""Deterministic public exports for vessel activity and the accepted domain.

This boundary consumes two already verified inputs: the production vessel grid
and the analytical-domain evidence mask.  It does not regenerate AIS, select a
different vessel rule, calculate speed, or calculate exposure.

The vessel display is clipped in EPSG:3310 to the accepted
``receivers_50_nautical_miles`` geometry before reprojection.  Values remain
the unchanged values of their source cells; partial cells explicitly carry the
fraction and area displayed.  The companion domain export contains the exact
accepted qualified geometry so excluded map water cannot be mistaken for
observed low activity.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from numpy.typing import NDArray
from pyproj import CRS, Transformer
from shapely import from_wkb, get_coordinates
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis.config import ProcessingConfig, load_default_config
from whale_vessel_analysis.reporting_domain import (
    ANALYTICAL_DOMAIN_ID,
    ReportingDomainContract,
    load_default_reporting_domain,
)
from whale_vessel_analysis.spatial_grid import (
    CELL_ID_PATTERN,
    GEOMETRY_COLUMN,
    ROW_ORDER,
)
from whale_vessel_analysis.vessel_input import (
    CONTRACT as VESSEL_INPUT_CONTRACT,
)
from whale_vessel_analysis.vessel_input import (
    PROCESSING_VERSION as VESSEL_INPUT_PROCESSING_VERSION,
)
from whale_vessel_analysis.vessel_input import (
    QUALITY_CONTRACT as VESSEL_INPUT_QUALITY_CONTRACT,
)
from whale_vessel_analysis.whale_display_export import (
    DISPLAY_CRS,
    MANIFEST_SUFFIX,
    MAP_EXTENT_DISPLAY_TOLERANCE_DEGREES,
    SOURCE_CRS,
    _canonical_json,
    _geometry_mapping,
    _sha256_file,
    _software_versions,
    validate_output_target,
)

VESSEL_DISPLAY_EXPORT_CONTRACT: Final = "commercial_vessel_display_export_v1"
DOMAIN_DISPLAY_EXPORT_CONTRACT: Final = "analytical_domain_display_export_v1"
VESSEL_MANIFEST_CONTRACT: Final = "commercial_vessel_display_manifest_v1"
DOMAIN_MANIFEST_CONTRACT: Final = "analytical_domain_display_manifest_v1"
PROCESSING_VERSION: Final = "1.0.0"

VESSEL_OUTPUT_NAME: Final = "commercial-vessel-activity.geojson"
DOMAIN_OUTPUT_NAME: Final = "accepted-analytical-domain.geojson"
DOMAIN_EVIDENCE_CONTRACT: Final = "analytical_domain_evidence_v1"
DOMAIN_EVIDENCE_SCHEMA_VERSION: Final = 1
DOMAIN_MASK_SCHEMA: Final = (
    ("scenario_id", pa.string()),
    ("basis", pa.string()),
    ("distance_m", pa.float64()),
    (GEOMETRY_COLUMN, pa.binary()),
)
DOMAIN_AREA_TOLERANCE_M2: Final = 1e-4
GEOMETRY_AREA_TOLERANCE_M2: Final = 1e-4
DOMAIN_SOURCE_CHECKSUM_FIELDS: Final = (
    "grid",
    "grid_path_sha256",
    "shoreline_archive",
    "station_archive",
    "vsr",
)

GROUPS: Final = ("passenger", "cargo", "tanker", "all_commercial")
SPEED_PREFIXES: Final = (
    "sog_available_km",
    "sog_unavailable_km",
    "sog_inconsistent_km",
    "reported_sog_mean_knots",
    "implied_speed_mean_knots",
)

VESSEL_SOURCE_SCHEMA: Final[tuple[tuple[str, pa.DataType, bool], ...]] = (
    ("cell_id", pa.string(), False),
    ("row_index", pa.int16(), False),
    ("column_index", pa.int16(), False),
    ("cell_x_min_m", pa.int32(), False),
    ("cell_y_min_m", pa.int32(), False),
    ("cell_x_max_m", pa.int32(), False),
    ("cell_y_max_m", pa.int32(), False),
    ("water_area_m2", pa.float64(), False),
    ("water_area_km2", pa.float64(), False),
    *((f"vessel_km_{group}", pa.float64(), False) for group in GROUPS),
    *((f"vessel_km_per_water_km2_{group}", pa.float64(), False) for group in GROUPS),
    *((f"distinct_mmsi_{group}", pa.int32(), False) for group in GROUPS),
    *((f"distinct_mmsi_dates_{group}", pa.int32(), False) for group in GROUPS),
    (GEOMETRY_COLUMN, pa.binary(), False),
    *(
        (f"{prefix}_{group}", pa.float64(), "mean" in prefix)
        for prefix in SPEED_PREFIXES
        for group in GROUPS
    ),
)

VESSEL_PUBLIC_FIELDS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "object_id",
        "unitless integer",
        "Display-only 1-based identifier in retained source row order.",
    ),
    ("cell_id", "unitless identifier", "Stable 5 km analysis-grid cell id."),
    (
        "vessel_km_per_water_km2_all_commercial",
        "km travelled / km² modeled-whale-support water",
        "Retained commercial movement per source cell water area during "
        "1 July through 30 November 2024.",
    ),
    (
        "vessel_km_all_commercial",
        "km travelled in the source cell",
        "Retained passenger, cargo and tanker movement in the complete source "
        "cell; partial display geometry does not rescale it.",
    ),
    *(
        (
            f"vessel_km_{group}",
            "km travelled in the source cell",
            f"Retained {group} movement in the complete source cell.",
        )
        for group in ("passenger", "cargo", "tanker")
    ),
    (
        "water_area_km2",
        "km²",
        "Modeled-whale-support water area of the complete source cell.",
    ),
    (
        "analytical_domain_area_km2",
        "km²",
        "Exact source-cell water area inside the accepted analytical domain.",
    ),
    (
        "analytical_domain_fraction",
        "unitless [0,1]",
        "Exact fraction of source-cell water inside the accepted domain.",
    ),
    (
        "analytical_domain_overlap",
        "classification",
        "Whether the exported geometry is a full or partial source cell.",
    ),
)

DOMAIN_PUBLIC_FIELDS: Final[tuple[tuple[str, str, str], ...]] = (
    ("object_id", "unitless integer", "Display-only object identifier."),
    ("domain_id", "unitless identifier", "Accepted analytical-domain id."),
    (
        "qualification",
        "classification",
        "System-performance-qualified, not empirical coverage.",
    ),
    ("distance_nautical_miles", "nautical miles", "Receiver buffer distance."),
    ("distance_m", "metres", "Exact receiver buffer distance."),
    (
        "measured_from",
        "classification",
        "Relevant NAIS reception stations, not the coast.",
    ),
    (
        "included_water_area_km2",
        "km²",
        "Modeled-whale-support water inside the accepted qualified geometry.",
    ),
    ("fully_inside_cell_count", "cells", "Source cells fully inside."),
    ("partly_inside_cell_count", "cells", "Source cells partly inside."),
    ("wholly_outside_cell_count", "cells", "Source cells wholly outside."),
)

VESSEL_WITHHELD_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    (
        "row_index, column_index and cell bounds",
        "Redundant grid internals; cell_id and WGS 84 geometry are published.",
    ),
    ("water_area_m2", "Redundant with water_area_km2."),
    (
        "distinct MMSI and MMSI-date fields",
        "Descriptors are not the selected activity measure and could invite "
        "an observational-completeness interpretation.",
    ),
    (
        "all reported and implied speed fields",
        "Speed remains a separate output under ADR 0006 and is not displayed "
        "or used to symbolize vessel activity in this slice.",
    ),
    (
        "production quality and lineage internals",
        "Private paths, per-partition identities, clocks and execution details "
        "remain outside the public artifact.",
    ),
)

AIS_SOURCE_REFERENCE: Final[dict[str, str]] = {
    "publisher": "NOAA Office for Coastal Management / Marine Cadastre",
    "product": "U.S. Coast Guard National AIS broadcast points",
    "analytical_period": "2024-07-01 through 2024-11-30 UTC (153 dates)",
    "metadata_record": "https://www.fisheries.noaa.gov/inport/item/39963",
    "data_page": "https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html",
    "source_credit": "NOAA Office for Coastal Management and U.S. Coast Guard",
    "use_constraint": (
        "Derived product for coastal and ocean planning; not for navigation, "
        "regulatory, or enforcement use."
    ),
}

DOMAIN_SOURCE_REFERENCE: Final[dict[str, str]] = {
    "station_publisher": "NOAA Office for Coastal Management",
    "station_product": "AIS Base Stations, 2024-08-01",
    "station_metadata": "https://www.fisheries.noaa.gov/inport/item/73206",
    "qualification_publisher": "U.S. Coast Guard NAVCEN",
    "qualification_source": "Work Instruction 2022-01",
    "qualification_url": (
        "https://www.navcen.uscg.gov/sites/default/files/pdf/waterways/nsra/"
        "NAVCEN%20Work%20Instruction%202022-01%20v2.pdf"
    ),
}

VESSEL_DISPLAY_STATEMENTS: Final[tuple[str, ...]] = (
    "Activity is retained passenger, cargo and tanker movement, measured as "
    "vessel-kilometres; it is not vessel presence, transit count, or speed.",
    "The population is type-only and is not program participation, eligibility, "
    "or a 300-gross-ton proxy.",
    "The 300-second gap and 30-knot implied-speed ceiling are project quality "
    "choices, not universal scientific thresholds.",
    "The upstream cleaner censors the map edge; omitted entry and exit distance "
    "is unknown and is not extrapolated.",
    "Source transfer completeness and AIS observational completeness remain "
    "unverified. Zero retained movement is not verified vessel absence.",
    "The geometry is limited to the accepted analytical domain before display. "
    "A partial boundary-cell value still describes its complete source cell and "
    "is not proportionally rescaled.",
    "This layer states no exposure, collision probability, strike prediction, "
    "or policy recommendation.",
)

DOMAIN_DISPLAY_STATEMENTS: Final[tuple[str, ...]] = (
    "The domain is 50 nautical miles (exactly 92,600 metres) from relevant NAIS "
    "reception stations, not from the coast.",
    "It is a system-performance-qualified scope reduction, not empirical 2024 "
    "coverage and not a guarantee that every transmission was received.",
    "Receiver uptime, station completeness, feed interruptions, antenna and "
    "terrain effects, and observational completeness remain unknown or unverified.",
    "Water outside this geometry is excluded from headline statistics and is "
    "not classified as low vessel activity.",
    "The broader map/context extent and modeled-whale-support water geometry have "
    "different roles and are not this analytical domain.",
)

_INPUT_ID_PATTERN: Final = re.compile(r"^vessel-input-[0-9a-f]{24}$")
_PERIOD_INPUT_ID_PATTERN: Final = re.compile(r"^multiday-ais-[0-9a-f]{24}$")
_EVIDENCE_ID_PATTERN: Final = re.compile(r"^domain-evidence-[0-9a-f]{24}$")
_PRIMARY_EXCLUSION_REASONS: Final = (
    "invalid_coordinate_transform",
    "non_increasing_time",
    "vessel_group_change",
    "maximum_gap",
    "implied_speed",
)
_ALLOCATION_STATUSES: Final = (
    "positive_length_in_support",
    "positive_length_outside_support",
    "positive_length_partially_outside_support",
    "zero_length_in_support",
    "zero_length_outside_support",
)


class VesselDomainDisplayExportError(ValueError):
    """Base error for rejected inputs, transformations, and destinations."""


class VesselDomainDisplayInputError(VesselDomainDisplayExportError):
    """Raised when a supplied artifact violates its accepted contract."""


class VesselDomainDisplayGeometryError(VesselDomainDisplayExportError):
    """Raised when clipping or reprojection yields invalid display geometry."""


class VesselDomainDisplayOutputError(VesselDomainDisplayExportError):
    """Raised when an export bundle cannot be written safely."""


@dataclass(frozen=True, slots=True)
class VesselSource:
    path: Path
    sha256: str
    table: pa.Table
    geometries: tuple[BaseGeometry, ...]
    input_id: str
    period_input_id: str
    target_grid_sha256: str
    configuration_sha256: str
    embedded_quality: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class VesselQualitySource:
    """Sanitized accounting from the accepted production quality sidecar."""

    path: Path
    sha256: str
    input_id: str
    period_input_id: str
    candidate_segment_count: int
    retained_segment_count: int
    excluded_segment_count: int
    primary_exclusions: Mapping[str, int]
    projected_excluded_distance_m: Mapping[str, float]
    allocation_status_counts: Mapping[str, int]
    all_commercial_distance_conservation: Mapping[str, float | bool]


@dataclass(frozen=True, slots=True)
class DomainSource:
    path: Path
    sha256: str
    report_path: Path
    report_sha256: str
    evidence_id: str
    configuration_sha256: str
    geometry: BaseGeometry
    measurement: Mapping[str, object]
    source_checksums: Mapping[str, str]
    contract: ReportingDomainContract


@dataclass(frozen=True, slots=True)
class GeometryDiagnostics:
    feature_count: int
    polygon_part_count: int
    interior_ring_count: int
    coordinate_count: int
    geometry_types: tuple[str, ...]
    bounds: tuple[float, float, float, float]
    max_vertex_roundtrip_metres: float

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_count": self.feature_count,
            "polygon_part_count": self.polygon_part_count,
            "interior_ring_count": self.interior_ring_count,
            "coordinate_count": self.coordinate_count,
            "geometry_types": list(self.geometry_types),
            "bounds_lon_lat": list(self.bounds),
            "max_vertex_roundtrip_metres": self.max_vertex_roundtrip_metres,
        }


@dataclass(frozen=True, slots=True)
class DisplayArtifact:
    name: str
    contract: str
    geojson: bytes
    diagnostics: GeometryDiagnostics
    value_diagnostics: Mapping[str, object]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.geojson).hexdigest()


@dataclass(frozen=True, slots=True)
class ExportBundle:
    vessel: DisplayArtifact
    domain: DisplayArtifact
    vessel_source: VesselSource
    vessel_quality_source: VesselQualitySource
    domain_source: DomainSource
    transformation_definition: str
    transformation_accuracy_metres: float | None


@dataclass(frozen=True, slots=True)
class ExportBundleResult:
    outputs: tuple[tuple[Path, str, int, Path, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": "vessel_domain_display_export_bundle_v1",
            "outputs": [
                {
                    "path": output.as_posix(),
                    "sha256": output_sha,
                    "bytes": size,
                    "manifest_path": manifest.as_posix(),
                    "manifest_sha256": manifest_sha,
                }
                for output, output_sha, size, manifest, manifest_sha in self.outputs
            ],
        }


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VesselDomainDisplayInputError(f"{name} must be an object")
    return cast(Mapping[str, object], value)


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VesselDomainDisplayInputError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise VesselDomainDisplayInputError(f"{name} must be finite")
    return number


def _nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VesselDomainDisplayInputError(f"{name} must be a non-negative integer")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise VesselDomainDisplayInputError(
            f"{name} must be 64 lowercase hexadecimal characters"
        )
    return value


def _read_parquet(path: Path, expected_sha256: str, label: str) -> tuple[str, pa.Table]:
    if not path.is_file():
        raise VesselDomainDisplayInputError(f"{label} does not exist: {path}")
    if path.suffix.lower() != ".parquet":
        raise VesselDomainDisplayInputError(f"{label} must be a .parquet file")
    actual = _sha256_file(path)
    if actual != expected_sha256.lower():
        raise VesselDomainDisplayInputError(
            f"{label} checksum mismatch: expected {expected_sha256.lower()}, "
            f"found {actual}"
        )
    try:
        return actual, pq.read_table(path, use_threads=False)
    except Exception as exc:  # pragma: no cover - third-party parser detail
        raise VesselDomainDisplayInputError(
            f"{label} could not be read as Parquet: {exc}"
        ) from exc


def _validate_geo_metadata(table: pa.Table, label: str) -> None:
    raw = (table.schema.metadata or {}).get(b"geo")
    if raw is None:
        raise VesselDomainDisplayInputError(f"{label} is missing GeoParquet metadata")
    try:
        geo = json.loads(raw)
        column = geo["columns"][GEOMETRY_COLUMN]
        crs = CRS.from_json_dict(column["crs"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VesselDomainDisplayInputError(
            f"{label} GeoParquet metadata is malformed: {exc}"
        ) from exc
    if geo.get("primary_column") != GEOMETRY_COLUMN:
        raise VesselDomainDisplayInputError(
            f"{label} primary geometry column must be {GEOMETRY_COLUMN}"
        )
    if column.get("encoding") != "WKB":
        raise VesselDomainDisplayInputError(f"{label} geometry encoding must be WKB")
    if crs.to_epsg() != CRS.from_user_input(SOURCE_CRS).to_epsg():
        raise VesselDomainDisplayInputError(
            f"{label} geometry CRS must be {SOURCE_CRS}; found {crs.to_string()}"
        )


def _decode_geometries(table: pa.Table, label: str) -> tuple[BaseGeometry, ...]:
    try:
        decoded = tuple(from_wkb(table[GEOMETRY_COLUMN].to_pylist()))
    except (GEOSException, TypeError, ValueError) as exc:
        raise VesselDomainDisplayInputError(
            f"{label} geometry could not be decoded from WKB: {exc}"
        ) from exc
    for index, geometry in enumerate(decoded):
        if geometry is None or geometry.is_empty:
            raise VesselDomainDisplayInputError(
                f"{label} geometry is empty at row {index}"
            )
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            raise VesselDomainDisplayInputError(
                f"{label} geometry at row {index} is {geometry.geom_type}"
            )
        if not geometry.is_valid:
            raise VesselDomainDisplayInputError(
                f"{label} geometry is invalid at row {index}"
            )
    return decoded


def _validate_vessel_schema(table: pa.Table) -> None:
    actual = [(field.name, field.type, field.nullable) for field in table.schema]
    expected = list(VESSEL_SOURCE_SCHEMA)
    if actual != expected:
        raise VesselDomainDisplayInputError(
            "vessel source schema does not match production_vessel_input_v1"
        )
    for name, _kind, nullable in VESSEL_SOURCE_SCHEMA:
        nulls = table[name].null_count
        if not nullable and nulls:
            raise VesselDomainDisplayInputError(
                f"non-nullable vessel source column {name} contains nulls"
            )


def _validate_vessel_metadata(
    table: pa.Table,
) -> tuple[str, str, str, str, Mapping[str, object]]:
    raw = (table.schema.metadata or {}).get(b"whale_vessel_analysis")
    if raw is None:
        raise VesselDomainDisplayInputError(
            "vessel source is missing whale_vessel_analysis metadata"
        )
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VesselDomainDisplayInputError(
            f"vessel source metadata is malformed: {exc}"
        ) from exc
    metadata = _mapping(document, "vessel source metadata")
    if metadata.get("contract") != VESSEL_INPUT_CONTRACT:
        raise VesselDomainDisplayInputError(
            f"vessel source contract must be {VESSEL_INPUT_CONTRACT}"
        )
    if metadata.get("schema_version") != 1:
        raise VesselDomainDisplayInputError("vessel source schema_version must be 1")
    if metadata.get("processing_version") != VESSEL_INPUT_PROCESSING_VERSION:
        raise VesselDomainDisplayInputError(
            "vessel source processing version does not match the accepted contract"
        )
    if metadata.get("analysis_crs") != SOURCE_CRS:
        raise VesselDomainDisplayInputError(
            f"vessel source analysis CRS must be {SOURCE_CRS}"
        )
    input_id = metadata.get("grid_id")
    if not isinstance(input_id, str) or not _INPUT_ID_PATTERN.fullmatch(input_id):
        raise VesselDomainDisplayInputError("vessel source input id is malformed")
    parameters = _mapping(metadata.get("parameters"), "vessel source parameters")
    expected_parameters: dict[str, object] = {
        "maximum_gap_seconds": 300.0,
        "implied_speed_ceiling_knots": 30.0,
        "period_readiness_treatment": "require-ready",
        "edge_treatment": "censor-at-cleaned-extent",
        "support_treatment": "exact-water-geometry-exclude-and-report",
    }
    for name, expected in expected_parameters.items():
        if parameters.get(name) != expected:
            raise VesselDomainDisplayInputError(
                f"vessel source parameter {name} must be {expected!r}"
            )
    length_filter = _mapping(
        parameters.get("vessel_length_filter"), "vessel length filter"
    )
    if length_filter.get("status") != "type-only-no-length-filter":
        raise VesselDomainDisplayInputError(
            "vessel source must use the accepted type-only population"
        )
    source_input = _mapping(metadata.get("input"), "vessel source input")
    completeness = _mapping(
        source_input.get("observational_completeness"),
        "vessel observational completeness",
    )
    if completeness.get("status") != "unverified":
        raise VesselDomainDisplayInputError(
            "vessel observational completeness must remain unverified"
        )
    readiness = _mapping(
        source_input.get("period_input_readiness"), "vessel period readiness"
    )
    if (
        readiness.get("status") != "ready"
        or readiness.get("expected_date_count") != 153
    ):
        raise VesselDomainDisplayInputError(
            "vessel source must use the ready 153-date analytical period"
        )
    period_input_id = source_input.get("period_input_id")
    if not isinstance(period_input_id, str) or not _PERIOD_INPUT_ID_PATTERN.fullmatch(
        period_input_id
    ):
        raise VesselDomainDisplayInputError("vessel period input id is malformed")
    target_grid_sha256 = _sha256(
        source_input.get("target_grid_sha256"), "target grid sha256"
    )
    configuration_sha256 = _sha256(
        source_input.get("configuration_sha256"), "configuration sha256"
    )
    embedded_quality = _mapping(
        metadata.get("quality"), "vessel embedded quality metadata"
    )
    return (
        input_id,
        period_input_id,
        target_grid_sha256,
        configuration_sha256,
        embedded_quality,
    )


def _validate_vessel_values(
    table: pa.Table, geometries: Sequence[BaseGeometry]
) -> None:
    if table.num_rows == 0:
        raise VesselDomainDisplayInputError("vessel source contains no rows")
    cell_ids = cast(list[str], table["cell_id"].to_pylist())
    rows = cast(list[int], table["row_index"].to_pylist())
    columns = cast(list[int], table["column_index"].to_pylist())
    if len(set(cell_ids)) != len(cell_ids):
        raise VesselDomainDisplayInputError("vessel source cell ids are not unique")
    if list(zip(rows, columns, strict=True)) != sorted(zip(rows, columns, strict=True)):
        raise VesselDomainDisplayInputError(
            f"vessel source rows are not in contract order ({ROW_ORDER})"
        )
    for index, (cell_id, row, column) in enumerate(
        zip(cell_ids, rows, columns, strict=True)
    ):
        if cell_id != CELL_ID_PATTERN.format(row=row, column=column):
            raise VesselDomainDisplayInputError(
                f"vessel cell id disagrees with row and column at row {index}"
            )
    water_m2 = cast(list[float], table["water_area_m2"].to_pylist())
    water_km2 = cast(list[float], table["water_area_km2"].to_pylist())
    numeric_names = [
        name
        for name, kind, _nullable in VESSEL_SOURCE_SCHEMA
        if pa.types.is_floating(kind) and name != GEOMETRY_COLUMN
    ]
    for name in numeric_names:
        for index, value in enumerate(table[name].to_pylist()):
            if value is None:
                continue
            number = float(value)
            if not math.isfinite(number) or number < 0:
                raise VesselDomainDisplayInputError(
                    f"vessel source {name} is invalid at row {index}"
                )
    for index, (area_m2, area_km2, geometry) in enumerate(
        zip(water_m2, water_km2, geometries, strict=True)
    ):
        if area_m2 <= 0 or not math.isclose(
            area_m2, area_km2 * 1_000_000, rel_tol=0, abs_tol=1e-6
        ):
            raise VesselDomainDisplayInputError(
                f"vessel source water-area units disagree at row {index}"
            )
        if not math.isclose(
            geometry.area,
            area_m2,
            rel_tol=1e-12,
            abs_tol=GEOMETRY_AREA_TOLERANCE_M2,
        ):
            raise VesselDomainDisplayInputError(
                f"vessel source geometry area disagrees at row {index}"
            )
    for index in range(table.num_rows):
        group_total = math.fsum(
            float(table[f"vessel_km_{group}"][index].as_py())
            for group in ("passenger", "cargo", "tanker")
        )
        all_total = float(table["vessel_km_all_commercial"][index].as_py())
        if not math.isclose(group_total, all_total, rel_tol=1e-12, abs_tol=1e-9):
            raise VesselDomainDisplayInputError(
                f"vessel group activity does not sum at row {index}"
            )
        density = float(table["vessel_km_per_water_km2_all_commercial"][index].as_py())
        if not math.isclose(
            density,
            all_total / water_km2[index],
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise VesselDomainDisplayInputError(
                f"vessel activity density disagrees at row {index}"
            )


def load_vessel_source(path: Path, *, expected_sha256: str) -> VesselSource:
    """Checksum-gate and validate one accepted production vessel artifact."""
    sha256, table = _read_parquet(path, expected_sha256, "vessel source")
    _validate_geo_metadata(table, "vessel source")
    _validate_vessel_schema(table)
    (
        input_id,
        period_input_id,
        target_grid_sha256,
        configuration_sha256,
        embedded_quality,
    ) = _validate_vessel_metadata(table)
    geometries = _decode_geometries(table, "vessel source")
    _validate_vessel_values(table, geometries)
    return VesselSource(
        path=path,
        sha256=sha256,
        table=table,
        geometries=geometries,
        input_id=input_id,
        period_input_id=period_input_id,
        target_grid_sha256=target_grid_sha256,
        configuration_sha256=configuration_sha256,
        embedded_quality=embedded_quality,
    )


def _read_json(path: Path, expected_sha256: str, label: str) -> tuple[str, object]:
    if not path.is_file():
        raise VesselDomainDisplayInputError(f"{label} does not exist: {path}")
    if path.suffix.lower() != ".json":
        raise VesselDomainDisplayInputError(f"{label} must be a .json file")
    actual = _sha256_file(path)
    if actual != expected_sha256.lower():
        raise VesselDomainDisplayInputError(
            f"{label} checksum mismatch: expected {expected_sha256.lower()}, "
            f"found {actual}"
        )
    try:
        return actual, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VesselDomainDisplayInputError(
            f"{label} could not be read: {exc}"
        ) from exc


def load_vessel_quality_source(
    path: Path,
    *,
    expected_sha256: str,
    vessel: VesselSource,
) -> VesselQualitySource:
    """Validate the production sidecar and retain only public-safe accounting."""
    quality_sha256, document = _read_json(
        path, expected_sha256, "vessel quality report"
    )
    quality = _mapping(document, "vessel quality report")
    if quality.get("contract") != VESSEL_INPUT_QUALITY_CONTRACT:
        raise VesselDomainDisplayInputError(
            f"vessel quality contract must be {VESSEL_INPUT_QUALITY_CONTRACT}"
        )
    if quality.get("processing_version") != VESSEL_INPUT_PROCESSING_VERSION:
        raise VesselDomainDisplayInputError(
            "vessel quality processing version does not match the accepted contract"
        )
    if quality.get("input_id") != vessel.input_id:
        raise VesselDomainDisplayInputError(
            "vessel quality input id does not match the vessel artifact"
        )
    embedded_candidate = {
        key: value for key, value in quality.items() if key != "output"
    }
    if embedded_candidate != dict(vessel.embedded_quality):
        raise VesselDomainDisplayInputError(
            "vessel quality report disagrees with embedded source quality metadata"
        )

    output = _mapping(quality.get("output"), "vessel quality output")
    if (
        output.get("contract") != VESSEL_INPUT_CONTRACT
        or output.get("input_id") != vessel.input_id
        or output.get("rows") != vessel.table.num_rows
        or output.get("sha256") != vessel.sha256
    ):
        raise VesselDomainDisplayInputError(
            "vessel quality output does not bind the supplied vessel artifact"
        )

    parameters = _mapping(quality.get("parameters"), "vessel quality parameters")
    expected_parameters: dict[str, object] = {
        "maximum_gap_seconds": 300.0,
        "implied_speed_ceiling_knots": 30.0,
        "period_readiness_treatment": "require-ready",
        "edge_treatment": "censor-at-cleaned-extent",
        "support_treatment": "exact-water-geometry-exclude-and-report",
    }
    for name, expected in expected_parameters.items():
        if parameters.get(name) != expected:
            raise VesselDomainDisplayInputError(
                f"vessel quality parameter {name} must be {expected!r}"
            )
    length_filter = _mapping(
        parameters.get("vessel_length_filter"), "vessel quality length filter"
    )
    if length_filter.get("status") != "type-only-no-length-filter":
        raise VesselDomainDisplayInputError(
            "vessel quality report must preserve the type-only population"
        )

    quality_input = _mapping(quality.get("input"), "vessel quality input")
    period_input_id = quality_input.get("period_input_id")
    if period_input_id != vessel.period_input_id:
        raise VesselDomainDisplayInputError(
            "vessel quality period input id does not match the vessel artifact"
        )
    readiness = _mapping(
        quality_input.get("period_input_readiness"),
        "vessel quality period readiness",
    )
    if (
        readiness.get("status") != "ready"
        or readiness.get("expected_date_count") != 153
        or quality_input.get("partition_count") != 153
    ):
        raise VesselDomainDisplayInputError(
            "vessel quality report must preserve the ready 153-date period"
        )
    completeness = _mapping(
        quality_input.get("observational_completeness"),
        "vessel quality observational completeness",
    )
    if completeness.get("status") != "unverified":
        raise VesselDomainDisplayInputError(
            "vessel quality observational completeness must remain unverified"
        )
    target_grid = _mapping(
        quality_input.get("target_grid"), "vessel quality target grid"
    )
    if (
        target_grid.get("sha256") != vessel.target_grid_sha256
        or target_grid.get("cell_count") != vessel.table.num_rows
        or target_grid.get("analysis_crs") != SOURCE_CRS
    ):
        raise VesselDomainDisplayInputError(
            "vessel quality target grid does not match the vessel artifact"
        )

    counts = _mapping(quality.get("counts"), "vessel quality counts")
    candidates = _mapping(
        counts.get("candidate_segments"), "vessel candidate segment counts"
    )
    group_counts = {
        group: _nonnegative_integer(candidates.get(group), f"candidate {group}")
        for group in GROUPS
    }
    candidate_count = group_counts["all_commercial"]
    if candidate_count != sum(group_counts[group] for group in GROUPS[:3]):
        raise VesselDomainDisplayInputError(
            "vessel candidate group counts do not reconcile"
        )
    retained_count = _nonnegative_integer(candidates.get("retained"), "retained")
    excluded_count = _nonnegative_integer(candidates.get("excluded"), "excluded")
    if retained_count + excluded_count != candidate_count:
        raise VesselDomainDisplayInputError(
            "retained and excluded vessel segments do not reconcile"
        )
    primary = _mapping(counts.get("primary_exclusions"), "primary exclusions")
    if set(primary) != set(_PRIMARY_EXCLUSION_REASONS):
        raise VesselDomainDisplayInputError(
            "primary exclusion reasons do not match the accepted contract"
        )
    primary_exclusions = {
        reason: _nonnegative_integer(primary.get(reason), f"exclusion {reason}")
        for reason in _PRIMARY_EXCLUSION_REASONS
    }
    if sum(primary_exclusions.values()) != excluded_count:
        raise VesselDomainDisplayInputError(
            "primary exclusion counts do not reconcile with excluded segments"
        )
    allocation = _mapping(counts.get("allocation_status"), "allocation status")
    if set(allocation) != set(_ALLOCATION_STATUSES):
        raise VesselDomainDisplayInputError(
            "allocation statuses do not match the accepted contract"
        )
    allocation_status_counts = {
        status: _nonnegative_integer(allocation.get(status), f"allocation {status}")
        for status in _ALLOCATION_STATUSES
    }

    exclusions = _mapping(quality.get("exclusions"), "vessel exclusions")
    if exclusions.get("precedence") != list(_PRIMARY_EXCLUSION_REASONS):
        raise VesselDomainDisplayInputError(
            "vessel exclusion precedence does not match the accepted contract"
        )
    projected = _mapping(
        exclusions.get("projected_distance_m_by_reason"),
        "projected excluded distance",
    )
    if set(projected) != {"maximum_gap", "implied_speed"}:
        raise VesselDomainDisplayInputError(
            "projected excluded-distance reasons do not match the accepted contract"
        )
    projected_excluded_distance_m = {
        reason: _finite_number(projected.get(reason), f"projected distance {reason}")
        for reason in ("maximum_gap", "implied_speed")
    }
    if any(value < 0 for value in projected_excluded_distance_m.values()):
        raise VesselDomainDisplayInputError(
            "projected excluded distances must be non-negative"
        )

    conservation = _mapping(
        quality.get("distance_conservation"), "vessel distance conservation"
    )
    if conservation.get("passed") is not True:
        raise VesselDomainDisplayInputError("vessel distance conservation must pass")
    by_group = _mapping(conservation.get("by_group"), "distance conservation groups")
    all_commercial = _mapping(
        by_group.get("all_commercial"), "all-commercial distance conservation"
    )
    distance_names = (
        "retained_parent_m",
        "allocated_to_cells_m",
        "outside_support_m",
        "ambiguous_boundary_m",
        "invalid_geometry_m",
        "difference_m",
    )
    distance_conservation = {
        name: _finite_number(all_commercial.get(name), f"distance conservation {name}")
        for name in distance_names
    }
    for name in distance_names[:-1]:
        if distance_conservation[name] < 0:
            raise VesselDomainDisplayInputError(
                f"distance conservation {name} must be non-negative"
            )
    if not math.isclose(
        distance_conservation["retained_parent_m"],
        math.fsum(
            distance_conservation[name]
            for name in (
                "allocated_to_cells_m",
                "outside_support_m",
                "ambiguous_boundary_m",
                "invalid_geometry_m",
            )
        ),
        rel_tol=1e-12,
        abs_tol=1e-6,
    ) or not math.isclose(
        distance_conservation["difference_m"], 0.0, rel_tol=0, abs_tol=1e-6
    ):
        raise VesselDomainDisplayInputError(
            "all-commercial retained distance does not conserve"
        )
    public_conservation: dict[str, float | bool] = {
        **distance_conservation,
        "passed": True,
    }
    return VesselQualitySource(
        path=path,
        sha256=quality_sha256,
        input_id=vessel.input_id,
        period_input_id=vessel.period_input_id,
        candidate_segment_count=candidate_count,
        retained_segment_count=retained_count,
        excluded_segment_count=excluded_count,
        primary_exclusions=primary_exclusions,
        projected_excluded_distance_m=projected_excluded_distance_m,
        allocation_status_counts=allocation_status_counts,
        all_commercial_distance_conservation=public_conservation,
    )


def _read_domain_report(
    path: Path, expected_sha256: str, mask_sha256: str
) -> tuple[str, Mapping[str, object]]:
    if not path.is_file():
        raise VesselDomainDisplayInputError(f"domain report does not exist: {path}")
    report_sha256 = _sha256_file(path)
    if report_sha256 != expected_sha256.lower():
        raise VesselDomainDisplayInputError(
            f"domain report checksum mismatch: expected {expected_sha256.lower()}, "
            f"found {report_sha256}"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VesselDomainDisplayInputError(
            f"domain report could not be read: {exc}"
        ) from exc
    report = _mapping(document, "domain report")
    if report.get("contract") != DOMAIN_EVIDENCE_CONTRACT:
        raise VesselDomainDisplayInputError(
            f"domain report contract must be {DOMAIN_EVIDENCE_CONTRACT}"
        )
    if report.get("schema_version") != DOMAIN_EVIDENCE_SCHEMA_VERSION:
        raise VesselDomainDisplayInputError("domain report schema_version must be 1")
    mask_output = _mapping(report.get("mask_output"), "domain report mask output")
    if (
        mask_output.get("sha256") != mask_sha256
        or mask_output.get("feature_count") != 8
    ):
        raise VesselDomainDisplayInputError(
            "domain report does not bind the supplied eight-feature mask"
        )
    return report_sha256, report


def _selected_measurement(report: Mapping[str, object]) -> Mapping[str, object]:
    candidates = report.get("candidates")
    if not isinstance(candidates, list):
        raise VesselDomainDisplayInputError("domain report candidates must be a list")
    selected = [
        _mapping(candidate, "domain candidate")
        for candidate in candidates
        if isinstance(candidate, Mapping)
        and candidate.get("id") == ANALYTICAL_DOMAIN_ID
    ]
    if len(selected) != 1:
        raise VesselDomainDisplayInputError(
            f"domain report must contain exactly one {ANALYTICAL_DOMAIN_ID} candidate"
        )
    measurement = selected[0]
    distance = _finite_number(measurement.get("distance"), "domain distance")
    distance_m = _finite_number(measurement.get("distance_m"), "domain distance_m")
    if (
        measurement.get("basis") != "receivers"
        or measurement.get("unit") != "nautical_mile"
        or distance != 50
        or distance_m != 92_600
    ):
        raise VesselDomainDisplayInputError(
            "domain report selected candidate does not match the accepted receiver rule"
        )
    included_water_area_km2 = _finite_number(
        measurement.get("included_water_area_km2"), "included water area"
    )
    if included_water_area_km2 <= 0:
        raise VesselDomainDisplayInputError("included water area must be positive")
    cells = _mapping(measurement.get("cells"), "domain cell counts")
    expected_cell_fields = {
        "fully_inside",
        "partly_inside",
        "wholly_outside",
    }
    if set(cells) != expected_cell_fields:
        raise VesselDomainDisplayInputError(
            "domain cell counts must contain only full, partial, and outside counts"
        )
    sanitized_cells = {
        name: _nonnegative_integer(cells.get(name), f"domain cells {name}")
        for name in sorted(expected_cell_fields)
    }
    return {
        "id": ANALYTICAL_DOMAIN_ID,
        "basis": "receivers",
        "unit": "nautical_mile",
        "distance": distance,
        "distance_m": distance_m,
        "included_water_area_km2": included_water_area_km2,
        "cells": sanitized_cells,
    }


def load_domain_source(
    path: Path,
    *,
    expected_sha256: str,
    report_path: Path,
    expected_report_sha256: str,
) -> DomainSource:
    """Validate and select the one accepted analytical-domain geometry."""
    sha256, table = _read_parquet(path, expected_sha256, "domain mask")
    _validate_geo_metadata(table, "domain mask")
    actual_schema = [(field.name, field.type) for field in table.schema]
    if actual_schema != list(DOMAIN_MASK_SCHEMA):
        raise VesselDomainDisplayInputError(
            "domain mask schema does not match analytical_domain_evidence_v1"
        )
    if table.num_rows != 8 or any(
        table[name].null_count for name in table.column_names
    ):
        raise VesselDomainDisplayInputError(
            "domain mask must contain eight complete candidate features"
        )
    geometries = _decode_geometries(table, "domain mask")
    scenario_ids = cast(list[str], table["scenario_id"].to_pylist())
    if len(set(scenario_ids)) != 8 or ANALYTICAL_DOMAIN_ID not in scenario_ids:
        raise VesselDomainDisplayInputError(
            "domain mask scenario identities are incomplete or duplicated"
        )
    selected_index = scenario_ids.index(ANALYTICAL_DOMAIN_ID)
    if table["basis"][selected_index].as_py() != "receivers":
        raise VesselDomainDisplayInputError("accepted domain basis must be receivers")
    if float(table["distance_m"][selected_index].as_py()) != 92_600:
        raise VesselDomainDisplayInputError("accepted domain distance must be 92,600 m")
    report_sha256, report = _read_domain_report(
        report_path, expected_report_sha256, sha256
    )
    measurement = _selected_measurement(report)
    geometry = geometries[selected_index]
    measured_area = _finite_number(
        measurement.get("included_water_area_km2"), "included water area"
    )
    if not math.isclose(
        geometry.area / 1_000_000,
        measured_area,
        rel_tol=1e-12,
        abs_tol=DOMAIN_AREA_TOLERANCE_M2 / 1_000_000,
    ):
        raise VesselDomainDisplayInputError(
            "accepted domain geometry area disagrees with the evidence report"
        )
    evidence_id = report.get("evidence_id")
    if not isinstance(evidence_id, str) or not _EVIDENCE_ID_PATTERN.fullmatch(
        evidence_id
    ):
        raise VesselDomainDisplayInputError("domain evidence id is malformed")
    sources = _mapping(report.get("sources"), "domain report sources")
    if set(sources) != set(DOMAIN_SOURCE_CHECKSUM_FIELDS):
        raise VesselDomainDisplayInputError(
            "domain report sources do not match the accepted checksum fields"
        )
    source_checksums = {
        name: _sha256(sources.get(name), f"domain source {name}")
        for name in DOMAIN_SOURCE_CHECKSUM_FIELDS
    }
    if source_checksums["grid_path_sha256"] != source_checksums["grid"]:
        raise VesselDomainDisplayInputError(
            "domain report grid checksum fields disagree"
        )
    configuration_sha256 = _sha256(
        report.get("configuration_sha256"), "domain configuration sha256"
    )
    return DomainSource(
        path=path,
        sha256=sha256,
        report_path=report_path,
        report_sha256=report_sha256,
        evidence_id=evidence_id,
        configuration_sha256=configuration_sha256,
        geometry=geometry,
        measurement=measurement,
        source_checksums=source_checksums,
        contract=load_default_reporting_domain(),
    )


def _transform_geometry(
    geometry: BaseGeometry,
    to_wgs84: Transformer,
    to_source: Transformer,
    *,
    label: str,
) -> tuple[BaseGeometry, float]:
    source_positions = get_coordinates(geometry)

    def positions(coordinates: NDArray[np.float64]) -> NDArray[np.float64]:
        longitude, latitude = to_wgs84.transform(coordinates[:, 0], coordinates[:, 1])
        return cast("NDArray[np.float64]", np.column_stack([longitude, latitude]))

    projected = shapely.transform(geometry, positions)
    oriented = shapely.orient_polygons(projected)
    if oriented.is_empty or not oriented.is_valid:
        raise VesselDomainDisplayGeometryError(
            f"{label} became empty or invalid after reprojection"
        )
    if oriented.geom_type not in {"Polygon", "MultiPolygon"}:
        raise VesselDomainDisplayGeometryError(
            f"{label} became unsupported geometry {oriented.geom_type}"
        )
    displayed = get_coordinates(oriented)
    projected_positions = get_coordinates(projected)
    longitude = displayed[:, 0]
    latitude = displayed[:, 1]
    if (
        longitude.min() < -180
        or longitude.max() > 180
        or latitude.min() < -90
        or latitude.max() > 90
    ):
        raise VesselDomainDisplayGeometryError(
            f"{label} has invalid longitude/latitude coordinates"
        )
    back_x, back_y = to_source.transform(
        projected_positions[:, 0], projected_positions[:, 1]
    )
    roundtrip = float(
        np.hypot(back_x - source_positions[:, 0], back_y - source_positions[:, 1]).max()
    )
    return oriented, roundtrip


def _geometry_diagnostics(
    geometries: Sequence[BaseGeometry], roundtrips: Sequence[float]
) -> GeometryDiagnostics:
    if not geometries:
        raise VesselDomainDisplayGeometryError("display export contains no geometry")
    parts = [part for geometry in geometries for part in shapely.get_parts(geometry)]
    positions = np.vstack([get_coordinates(geometry) for geometry in geometries])
    return GeometryDiagnostics(
        feature_count=len(geometries),
        polygon_part_count=len(parts),
        interior_ring_count=int(sum(shapely.get_num_interior_rings(parts))),
        coordinate_count=int(positions.shape[0]),
        geometry_types=tuple(sorted({geometry.geom_type for geometry in geometries})),
        bounds=(
            float(positions[:, 0].min()),
            float(positions[:, 1].min()),
            float(positions[:, 0].max()),
            float(positions[:, 1].max()),
        ),
        max_vertex_roundtrip_metres=max(roundtrips),
    )


def _validate_display_extent(
    diagnostics: GeometryDiagnostics, config: ProcessingConfig
) -> None:
    extent = config.spatial.map_extent
    min_lon, min_lat, max_lon, max_lat = diagnostics.bounds
    tolerance = MAP_EXTENT_DISPLAY_TOLERANCE_DEGREES
    if not (
        extent.lon_min - tolerance <= min_lon
        and max_lon <= extent.lon_max + tolerance
        and extent.lat_min - tolerance <= min_lat
        and max_lat <= extent.lat_max + tolerance
    ):
        raise VesselDomainDisplayGeometryError(
            "display geometry falls outside the configured map/context extent"
        )


def _feature_collection(features: Sequence[Mapping[str, object]]) -> bytes:
    geometries = [
        cast(Mapping[str, object], feature["geometry"]) for feature in features
    ]
    coordinates: list[tuple[float, float]] = []

    def collect(value: object) -> None:
        if (
            isinstance(value, list)
            and len(value) == 2
            and all(isinstance(item, (int, float)) for item in value)
        ):
            coordinates.append((float(value[0]), float(value[1])))
        elif isinstance(value, list):
            for item in value:
                collect(item)

    for geometry in geometries:
        collect(geometry["coordinates"])
    bbox = [
        min(item[0] for item in coordinates),
        min(item[1] for item in coordinates),
        max(item[0] for item in coordinates),
        max(item[1] for item in coordinates),
    ]
    collection: dict[str, object] = {
        "type": "FeatureCollection",
        "bbox": bbox,
        "features": list(features),
    }
    return (_canonical_json(collection) + "\n").encode("utf-8")


def build_exports(
    vessel: VesselSource,
    vessel_quality: VesselQualitySource,
    domain: DomainSource,
    config: ProcessingConfig | None = None,
) -> ExportBundle:
    """Clip vessel display geometry to the accepted domain and export both."""
    if vessel_quality.input_id != vessel.input_id:
        raise VesselDomainDisplayInputError(
            "vessel quality input id does not match the vessel artifact"
        )
    if vessel.target_grid_sha256 != domain.source_checksums.get("grid"):
        raise VesselDomainDisplayInputError(
            "vessel and analytical-domain artifacts use different water grids"
        )
    reporting = domain.contract.analytical_domain
    if reporting.domain_id != ANALYTICAL_DOMAIN_ID:
        raise VesselDomainDisplayInputError("default reporting domain is not accepted")

    to_wgs84 = Transformer.from_crs(SOURCE_CRS, DISPLAY_CRS, always_xy=True)
    to_source = Transformer.from_crs(DISPLAY_CRS, SOURCE_CRS, always_xy=True)
    table = vessel.table
    cell_ids = cast(list[str], table["cell_id"].to_pylist())
    values = {
        name: table[name].to_pylist()
        for name in (
            "vessel_km_per_water_km2_all_commercial",
            "vessel_km_all_commercial",
            "vessel_km_passenger",
            "vessel_km_cargo",
            "vessel_km_tanker",
            "water_area_km2",
        )
    }
    features: list[Mapping[str, object]] = []
    displayed_geometries: list[BaseGeometry] = []
    roundtrips: list[float] = []
    full_count = partial_count = 0
    activity_values: list[float] = []
    zero_count = 0
    displayed_area_total = 0.0

    for source_index, geometry in enumerate(vessel.geometries):
        try:
            clipped = geometry.intersection(domain.geometry)
        except GEOSException as exc:
            raise VesselDomainDisplayGeometryError(
                f"domain intersection failed for source row {source_index}: {exc}"
            ) from exc
        if clipped.is_empty or clipped.area <= DOMAIN_AREA_TOLERANCE_M2:
            continue
        if clipped.geom_type not in {"Polygon", "MultiPolygon"} or not clipped.is_valid:
            raise VesselDomainDisplayGeometryError(
                f"domain intersection is invalid at source row {source_index}"
            )
        fraction = clipped.area / geometry.area
        if fraction > 1 + 1e-12:
            raise VesselDomainDisplayGeometryError(
                f"domain fraction exceeds one at source row {source_index}"
            )
        overlap = "full" if math.isclose(fraction, 1.0, abs_tol=1e-12) else "partial"
        if overlap == "full":
            full_count += 1
        else:
            partial_count += 1
        displayed, roundtrip = _transform_geometry(
            clipped,
            to_wgs84,
            to_source,
            label=f"vessel source row {source_index}",
        )
        displayed_geometries.append(displayed)
        roundtrips.append(roundtrip)
        density = float(values["vessel_km_per_water_km2_all_commercial"][source_index])
        activity_values.append(density)
        if density == 0:
            zero_count += 1
        displayed_area_total += clipped.area
        properties: dict[str, object] = {
            "object_id": len(features) + 1,
            "cell_id": cell_ids[source_index],
            **{
                name: values[name][source_index]
                for name in (
                    "vessel_km_per_water_km2_all_commercial",
                    "vessel_km_all_commercial",
                    "vessel_km_passenger",
                    "vessel_km_cargo",
                    "vessel_km_tanker",
                    "water_area_km2",
                )
            },
            "analytical_domain_area_km2": clipped.area / 1_000_000,
            "analytical_domain_fraction": min(fraction, 1.0),
            "analytical_domain_overlap": overlap,
        }
        features.append(
            {
                "type": "Feature",
                "id": cell_ids[source_index],
                "geometry": _geometry_mapping(displayed),
                "properties": properties,
            }
        )

    vessel_diagnostics = _geometry_diagnostics(displayed_geometries, roundtrips)
    selected_cells = _mapping(domain.measurement.get("cells"), "domain cell counts")
    expected_full = selected_cells.get("fully_inside")
    expected_partial = selected_cells.get("partly_inside")
    if full_count != expected_full or partial_count != expected_partial:
        raise VesselDomainDisplayGeometryError(
            "vessel/domain intersection cell counts disagree with domain evidence"
        )
    expected_area = _finite_number(
        domain.measurement.get("included_water_area_km2"), "domain included water"
    )
    if not math.isclose(
        displayed_area_total / 1_000_000,
        expected_area,
        rel_tol=1e-12,
        abs_tol=DOMAIN_AREA_TOLERANCE_M2 / 1_000_000,
    ):
        raise VesselDomainDisplayGeometryError(
            "vessel display area does not conserve the accepted domain area"
        )

    displayed_domain, domain_roundtrip = _transform_geometry(
        domain.geometry,
        to_wgs84,
        to_source,
        label="accepted analytical domain",
    )
    domain_diagnostics = _geometry_diagnostics([displayed_domain], [domain_roundtrip])
    active_config = config if config is not None else load_default_config()
    _validate_display_extent(vessel_diagnostics, active_config)
    _validate_display_extent(domain_diagnostics, active_config)

    domain_cells = _mapping(domain.measurement["cells"], "domain cell counts")
    if sum(cast(int, value) for value in domain_cells.values()) != table.num_rows:
        raise VesselDomainDisplayGeometryError(
            "analytical-domain cell counts do not reconcile with the vessel grid"
        )
    domain_properties: dict[str, object] = {
        "object_id": 1,
        "domain_id": reporting.domain_id,
        "qualification": reporting.qualification,
        "distance_nautical_miles": reporting.distance_nautical_miles,
        "distance_m": reporting.distance_m,
        "measured_from": reporting.measured_from,
        "included_water_area_km2": expected_area,
        "fully_inside_cell_count": domain_cells["fully_inside"],
        "partly_inside_cell_count": domain_cells["partly_inside"],
        "wholly_outside_cell_count": domain_cells["wholly_outside"],
    }
    domain_features: list[Mapping[str, object]] = [
        {
            "type": "Feature",
            "id": reporting.domain_id,
            "geometry": _geometry_mapping(displayed_domain),
            "properties": domain_properties,
        }
    ]

    return ExportBundle(
        vessel=DisplayArtifact(
            name=VESSEL_OUTPUT_NAME,
            contract=VESSEL_DISPLAY_EXPORT_CONTRACT,
            geojson=_feature_collection(features),
            diagnostics=vessel_diagnostics,
            value_diagnostics={
                "unique_cell_count": len({feature["id"] for feature in features}),
                "fully_inside_cell_count": full_count,
                "partly_inside_cell_count": partial_count,
                "wholly_outside_cell_count": domain_cells["wholly_outside"],
                "zero_activity_cell_count": zero_count,
                "positive_activity_cell_count": len(activity_values) - zero_count,
                "activity_density_min": min(activity_values),
                "activity_density_max": max(activity_values),
                "displayed_domain_area_km2": displayed_area_total / 1_000_000,
            },
        ),
        domain=DisplayArtifact(
            name=DOMAIN_OUTPUT_NAME,
            contract=DOMAIN_DISPLAY_EXPORT_CONTRACT,
            geojson=_feature_collection(domain_features),
            diagnostics=domain_diagnostics,
            value_diagnostics={
                "included_water_area_km2": expected_area,
                "fully_inside_cell_count": domain_cells["fully_inside"],
                "partly_inside_cell_count": domain_cells["partly_inside"],
                "wholly_outside_cell_count": domain_cells["wholly_outside"],
            },
        ),
        vessel_source=vessel,
        vessel_quality_source=vessel_quality,
        domain_source=domain,
        transformation_definition=to_wgs84.definition,
        transformation_accuracy_metres=to_wgs84.accuracy,
    )


def _base_manifest(
    bundle: ExportBundle, artifact: DisplayArtifact, exported_at: datetime
) -> dict[str, object]:
    if exported_at.utcoffset() != UTC.utcoffset(exported_at):
        raise VesselDomainDisplayOutputError("exported_at must be timezone-aware UTC")
    return {
        "dataset_contract": artifact.contract,
        "processing_version": PROCESSING_VERSION,
        "exported_at": exported_at.isoformat().replace("+00:00", "Z"),
        "transformation": {
            "source_crs": SOURCE_CRS,
            "display_crs": DISPLAY_CRS,
            "always_xy": True,
            "definition": bundle.transformation_definition,
            "operation_accuracy_metres": bundle.transformation_accuracy_metres,
            "ring_orientation": (
                "RFC 7946: exterior rings counterclockwise, interior rings clockwise"
            ),
            "geometry_simplification": "not_performed",
            "coordinate_rounding": "not_performed",
            "densification": "not_performed",
        },
        "output": {
            "name": artifact.name,
            "format": "GeoJSON (RFC 7946)",
            "media_type": "application/geo+json",
            "bytes": len(artifact.geojson),
            "sha256": artifact.sha256,
            **artifact.diagnostics.to_dict(),
            **artifact.value_diagnostics,
        },
        "software": _software_versions(),
    }


def build_vessel_manifest(
    bundle: ExportBundle, *, exported_at: datetime
) -> dict[str, object]:
    manifest = _base_manifest(bundle, bundle.vessel, exported_at)
    manifest.update(
        {
            "contract": VESSEL_MANIFEST_CONTRACT,
            "source": {
                "artifact_id": "production-vessel-input",
                "contract": VESSEL_INPUT_CONTRACT,
                "processing_version": VESSEL_INPUT_PROCESSING_VERSION,
                "input_id": bundle.vessel_source.input_id,
                "period_input_id": bundle.vessel_source.period_input_id,
                "sha256": bundle.vessel_source.sha256,
                "quality_report_contract": VESSEL_INPUT_QUALITY_CONTRACT,
                "quality_report_sha256": bundle.vessel_quality_source.sha256,
                "target_grid_sha256": bundle.vessel_source.target_grid_sha256,
                "configuration_sha256": bundle.vessel_source.configuration_sha256,
                "analysis_crs": SOURCE_CRS,
                "row_order": ROW_ORDER,
                "visual_verification": {
                    "status": "recorded_separately",
                    "bound_to_sha256": bundle.vessel_source.sha256,
                    "reference": "analysis/README.md",
                },
            },
            "source_data": dict(AIS_SOURCE_REFERENCE),
            "accepted_method": {
                "activity_measure": "vessel-kilometres",
                "display_measure": (
                    "vessel-kilometres per km² modeled-whale-support water"
                ),
                "maximum_gap_seconds": 300,
                "implied_speed_ceiling_knots": 30,
                "vessel_groups": ["passenger", "cargo", "tanker"],
                "vessel_population": "type-only-no-length-filter",
                "edge_treatment": "censor-at-cleaned-extent",
                "support_treatment": "exact-water-geometry-exclude-and-report",
                "speed_role": "withheld; separate under ADR 0006",
            },
            "processing_accounting": {
                "candidate_segment_count": (
                    bundle.vessel_quality_source.candidate_segment_count
                ),
                "retained_segment_count": (
                    bundle.vessel_quality_source.retained_segment_count
                ),
                "excluded_segment_count": (
                    bundle.vessel_quality_source.excluded_segment_count
                ),
                "primary_exclusion_counts": dict(
                    bundle.vessel_quality_source.primary_exclusions
                ),
                "projected_excluded_distance_m": dict(
                    bundle.vessel_quality_source.projected_excluded_distance_m
                ),
                "allocation_status_counts": dict(
                    bundle.vessel_quality_source.allocation_status_counts
                ),
                "all_commercial_distance_conservation": dict(
                    bundle.vessel_quality_source.all_commercial_distance_conservation
                ),
                "source_point_removals": (
                    "owned by the upstream one-date cleaner and not counted again"
                ),
            },
            "analytical_domain": {
                "id": ANALYTICAL_DOMAIN_ID,
                "mask_sha256": bundle.domain_source.sha256,
                "report_sha256": bundle.domain_source.report_sha256,
                "reporting_contract": bundle.domain_source.contract.to_dict(),
                "geometry_operation": (
                    "source-cell water geometry intersected with the exact accepted "
                    "domain in EPSG:3310 before reprojection"
                ),
                "value_recomputation": "not_performed",
                "partial_cell_values": (
                    "unchanged complete-source-cell values; not multiplied by the "
                    "displayed domain fraction"
                ),
            },
            "fields": {
                "published": [
                    {"name": name, "unit": unit, "meaning": meaning}
                    for name, unit, meaning in VESSEL_PUBLIC_FIELDS
                ],
                "withheld": [
                    {"name": name, "reason": reason}
                    for name, reason in VESSEL_WITHHELD_FIELDS
                ],
                "feature_id": "cell_id",
                "display_object_id": "object_id",
            },
            "display_statements": list(VESSEL_DISPLAY_STATEMENTS),
        }
    )
    return manifest


def build_domain_manifest(
    bundle: ExportBundle, *, exported_at: datetime
) -> dict[str, object]:
    manifest = _base_manifest(bundle, bundle.domain, exported_at)
    manifest.update(
        {
            "contract": DOMAIN_MANIFEST_CONTRACT,
            "source": {
                "artifact_id": "analytical-domain-candidate-masks",
                "contract": DOMAIN_EVIDENCE_CONTRACT,
                "schema_version": DOMAIN_EVIDENCE_SCHEMA_VERSION,
                "evidence_id": bundle.domain_source.evidence_id,
                "mask_sha256": bundle.domain_source.sha256,
                "report_sha256": bundle.domain_source.report_sha256,
                "configuration_sha256": bundle.domain_source.configuration_sha256,
                "input_checksums": dict(bundle.domain_source.source_checksums),
                "analysis_crs": SOURCE_CRS,
                "visual_verification": {
                    "status": "recorded_separately",
                    "bound_to_sha256": bundle.domain_source.sha256,
                    "reference": "docs/analytical-domain-evidence.md",
                },
            },
            "source_data": dict(DOMAIN_SOURCE_REFERENCE),
            "reporting_contract": bundle.domain_source.contract.to_dict(),
            "geometry": {
                "selected_feature": ANALYTICAL_DOMAIN_ID,
                "selection_only": True,
                "value_recomputation": "not_performed",
            },
            "fields": {
                "published": [
                    {"name": name, "unit": unit, "meaning": meaning}
                    for name, unit, meaning in DOMAIN_PUBLIC_FIELDS
                ],
                "feature_id": "domain_id",
                "display_object_id": "object_id",
            },
            "display_statements": list(DOMAIN_DISPLAY_STATEMENTS),
        }
    )
    return manifest


def _write_bytes(path: Path, payload: bytes) -> None:
    with path.open("xb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())


def _commit_files(
    temporary_to_final: Sequence[tuple[Path, Path]], *, overwrite: bool
) -> None:
    backups: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    try:
        if overwrite:
            for _temporary, final in temporary_to_final:
                if final.exists():
                    backup = final.with_name(f".{final.name}.{uuid.uuid4().hex}.backup")
                    os.replace(final, backup)
                    backups.append((backup, final))
        elif any(final.exists() for _temporary, final in temporary_to_final):
            raise VesselDomainDisplayOutputError(
                "an output or manifest already exists; explicit overwrite is required"
            )
        for temporary, final in temporary_to_final:
            os.replace(temporary, final)
            committed.append(final)
    except Exception:
        for final in reversed(committed):
            final.unlink(missing_ok=True)
        for backup, final in reversed(backups):
            os.replace(backup, final)
        raise
    else:
        for backup, _final in backups:
            backup.unlink(missing_ok=True)


def write_export_bundle(
    bundle: ExportBundle,
    output_directory: Path,
    *,
    exported_at: datetime | None = None,
    overwrite: bool = False,
    approved_roots: Sequence[Path] | None = None,
) -> ExportBundleResult:
    """Atomically publish both GeoJSON files and their public manifests."""
    outputs = [
        output_directory / VESSEL_OUTPUT_NAME,
        output_directory / DOMAIN_OUTPUT_NAME,
    ]
    for output in outputs:
        try:
            validate_output_target(output, approved_roots)
        except ValueError as exc:
            raise VesselDomainDisplayOutputError(str(exc)) from exc
    resolved_parents = {output.resolve().parent for output in outputs}
    if len(resolved_parents) != 1:
        raise VesselDomainDisplayOutputError("bundle outputs must share one directory")
    output_directory.mkdir(parents=True, exist_ok=True)
    timestamp = exported_at if exported_at is not None else datetime.now(UTC)
    manifests = [
        build_vessel_manifest(bundle, exported_at=timestamp),
        build_domain_manifest(bundle, exported_at=timestamp),
    ]
    artifacts = [bundle.vessel, bundle.domain]
    payloads: list[tuple[Path, bytes]] = []
    for output, artifact, manifest in zip(outputs, artifacts, manifests, strict=True):
        payloads.extend(
            [
                (output, artifact.geojson),
                (
                    output.with_name(output.name + MANIFEST_SUFFIX),
                    (_canonical_json(manifest) + "\n").encode("utf-8"),
                ),
            ]
        )
    if not overwrite and any(path.exists() for path, _payload in payloads):
        raise VesselDomainDisplayOutputError(
            "an output or manifest already exists; explicit overwrite is required"
        )
    token = uuid.uuid4().hex
    temporary_to_final: list[tuple[Path, Path]] = []
    try:
        for final, payload in payloads:
            temporary = final.with_name(f".{final.name}.{token}.tmp")
            _write_bytes(temporary, payload)
            temporary_to_final.append((temporary, final))
        _commit_files(temporary_to_final, overwrite=overwrite)
    except VesselDomainDisplayExportError:
        raise
    except Exception as exc:
        raise VesselDomainDisplayOutputError(
            f"could not write vessel/domain display bundle: {exc}"
        ) from exc
    finally:
        for temporary, _final in temporary_to_final:
            temporary.unlink(missing_ok=True)
    results: list[tuple[Path, str, int, Path, str]] = []
    for output, artifact, manifest in zip(outputs, artifacts, manifests, strict=True):
        manifest_path = output.with_name(output.name + MANIFEST_SUFFIX)
        manifest_payload = (_canonical_json(manifest) + "\n").encode("utf-8")
        results.append(
            (
                output,
                artifact.sha256,
                len(artifact.geojson),
                manifest_path,
                hashlib.sha256(manifest_payload).hexdigest(),
            )
        )
    return ExportBundleResult(outputs=tuple(results))
