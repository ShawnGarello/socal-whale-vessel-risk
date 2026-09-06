"""Deterministic public-display export of the validated whale grid.

This is a presentation boundary, not an analytical one. It changes the
*representation* of an already validated `blue_whale_grid_transfer_v1` artifact
so a browser can draw it: EPSG:3310 WKB becomes RFC 7946 WGS 84 GeoJSON. It
never recomputes, rescales, normalizes, rounds, or simplifies an analytical
value, and it refuses a source that does not match its declared contract and
checksum.

Two files are produced together and both are safe to publish: the GeoJSON
itself, and a sanitized export manifest that records where the displayed
numbers came from. The manifest deliberately carries no filesystem path, no
account identifier, no credential, and nothing from the VSR snapshot.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import sys
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final, cast

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyproj
import shapely
from numpy.typing import NDArray
from pyproj import CRS, Transformer
from shapely import from_wkb, get_coordinates
from shapely.errors import GEOSException
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis.config import ProcessingConfig, load_default_config
from whale_vessel_analysis.spatial_grid import (
    CELL_ID_PATTERN,
    GEOMETRY_COLUMN,
    ROW_ORDER,
)
from whale_vessel_analysis.whale import (
    WHALE_DENSITY_UNIT,
    WHALE_LAYER_NAME,
    WHALE_SEASON,
)
from whale_vessel_analysis.whale_grid import (
    LINEAGE_SUFFIX,
    WHALE_GRID_CONTRACT,
    WHALE_GRID_DATASET_SCHEMA_VERSION,
    WHALE_GRID_LINEAGE_CONTRACT,
)

WHALE_DISPLAY_EXPORT_CONTRACT: Final = "blue_whale_display_export_v1"
WHALE_DISPLAY_EXPORT_MANIFEST_CONTRACT: Final = "blue_whale_display_export_manifest_v1"
WHALE_DISPLAY_EXPORT_PROCESSING_VERSION: Final = "1.0.0"
DISPLAY_CRS: Final = "EPSG:4326"
SOURCE_CRS: Final = "EPSG:3310"
MANIFEST_SUFFIX: Final = ".manifest.json"
GEOJSON_SUFFIX: Final = ".geojson"

# RFC 7946 fixes the axis order for `crs`-less GeoJSON as longitude, latitude,
# so every transformation below is built with `always_xy=True` and the result is
# checked against these bounds rather than trusting the flag.
LONGITUDE_BOUNDS: Final = (-180.0, 180.0)
LATITUDE_BOUNDS: Final = (-90.0, 90.0)

# How far outside the configured map/context extent an exported vertex may sit.
#
# The analysis grid is built by densifying the geographic extent to at most
# 0.01 degrees, projecting it, and clipping in EPSG:3310. A straight projected
# chord between two densified vertices on the 35 N parallel bulges roughly
# 1.08e-7 degrees (about 1.2 cm) north of it, so the exported boundary
# reproduces that bulge. This tolerance admits that known method artifact and
# nothing larger; clipping it away here would silently change the analytical
# geometry, which this boundary must never do.
MAP_EXTENT_DISPLAY_TOLERANCE_DEGREES: Final = 1e-6

_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]

#: The only destinations an export may be written to.
#:
#: This is an allowlist, not a denylist, and it is anchored to *this* checkout.
#: Sibling worktrees share the repository's directory layout, so a denylist
#: would have to enumerate every one of them; an allowlist rejects them all,
#: along with every other location on the machine, without knowing they exist.
#: Everything listed here is Git-ignored, so a generated layer cannot be staged
#: for a commit by accident, and `web/public/layers` is the local
#: static-serving location the application reads during development and during
#: `next build`.
#:
#: If `_PROJECT_ROOT` were ever wrong — an installed wheel rather than this
#: source tree — every destination fails closed rather than opening up.
APPROVED_OUTPUT_ROOTS: Final = (
    (_PROJECT_ROOT / "data" / "derived").resolve(),
    (_PROJECT_ROOT / "data" / "interim").resolve(),
    (_PROJECT_ROOT / "web" / "public" / "layers").resolve(),
)

#: Exact `blue_whale_grid_transfer_v1` schema this exporter accepts, in order.
SOURCE_SCHEMA: Final[tuple[tuple[str, pa.DataType], ...]] = (
    ("cell_id", pa.string()),
    ("row_index", pa.int16()),
    ("column_index", pa.int16()),
    ("cell_x_min_m", pa.int32()),
    ("cell_y_min_m", pa.int32()),
    ("cell_x_max_m", pa.int32()),
    ("cell_y_max_m", pa.int32()),
    ("water_area_m2", pa.float64()),
    ("water_area_km2", pa.float64()),
    ("modeled_abundance_allocation_animals", pa.float64()),
    ("modeled_density_animals_per_km2", pa.float64()),
    ("source_covered_water_area_m2", pa.float64()),
    ("source_covered_water_area_km2", pa.float64()),
    ("uncovered_water_area_m2", pa.float64()),
    ("uncovered_water_area_km2", pa.float64()),
    ("source_coverage_fraction", pa.float64()),
    ("coverage_status", pa.string()),
    ("source_polygon_count", pa.int32()),
    (GEOMETRY_COLUMN, pa.binary()),
)

#: Fields published in the GeoJSON, with the meaning and unit a reader needs.
#: `object_id` is display-only and is derived here; every other field is copied
#: from the validated source without recomputation.
PUBLIC_FIELDS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "object_id",
        "unitless integer",
        "Display-only identifier: the cell's 1-based position in the source "
        "row order. Derived deterministically here so a browser layer has a "
        "stable numeric object id; it is not an analytical value.",
    ),
    (
        "cell_id",
        "unitless identifier",
        f"Stable analysis-grid identity, formatted {CELL_ID_PATTERN!r}.",
    ),
    (
        "modeled_density_animals_per_km2",
        WHALE_DENSITY_UNIT,
        "Modeled blue-whale density for the cell: allocated modeled abundance "
        "divided by the cell's water area. Modeled, not observed.",
    ),
    (
        "modeled_abundance_allocation_animals",
        "animals",
        "Modeled animals allocated to this cell by abundance-conserving area "
        "weighting. Modeled, not counted.",
    ),
    (
        "water_area_km2",
        "km²",
        "Water area of the cell that supports the modeled value.",
    ),
    (
        "source_coverage_fraction",
        "unitless [0,1]",
        "Share of the cell's water area covered by contributing source "
        "polygons. Source-model support, not survey or AIS completeness.",
    ),
    (
        "coverage_status",
        "unitless classification",
        "Explicit source-support classification: complete, "
        "within_numerical_tolerance, or incomplete.",
    ),
)

#: Source columns deliberately withheld from the public layer, with the reason.
WITHHELD_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    (
        "row_index",
        "Redundant: cell_id already encodes the row index.",
    ),
    (
        "column_index",
        "Redundant: cell_id already encodes the column index.",
    ),
    (
        "cell_x_min_m",
        "EPSG:3310 grid internals; the published geometry is WGS 84.",
    ),
    (
        "cell_y_min_m",
        "EPSG:3310 grid internals; the published geometry is WGS 84.",
    ),
    (
        "cell_x_max_m",
        "EPSG:3310 grid internals; the published geometry is WGS 84.",
    ),
    (
        "cell_y_max_m",
        "EPSG:3310 grid internals; the published geometry is WGS 84.",
    ),
    ("water_area_m2", "Redundant with water_area_km2."),
    (
        "source_covered_water_area_m2",
        "Redundant with source_coverage_fraction and water_area_km2.",
    ),
    (
        "source_covered_water_area_km2",
        "Redundant with source_coverage_fraction and water_area_km2.",
    ),
    (
        "uncovered_water_area_m2",
        "Redundant with source_coverage_fraction and water_area_km2.",
    ),
    (
        "uncovered_water_area_km2",
        "Redundant with source_coverage_fraction and water_area_km2.",
    ),
    (
        "source_polygon_count",
        "Generation diagnostic with no display meaning.",
    ),
)

#: Provenance the public manifest must carry so a displayed number is traceable
#: to a citable source without exposing anything local.
SOURCE_MODEL_REFERENCE: Final[dict[str, str]] = {
    "publisher": (
        "NMFS Office of Science and Technology; models produced by NOAA "
        "Fisheries Southwest Fisheries Science Center (SWFSC)"
    ),
    "product": (
        "Predictive Models of Cetacean Densities in the California Current "
        "Ecosystem, 2020b"
    ),
    "layer": WHALE_LAYER_NAME,
    "season_label": WHALE_SEASON,
    "metadata_record": "https://www.fisheries.noaa.gov/inport/item/64349",
    "distribution_item": (
        "https://noaa.maps.arcgis.com/home/item.html"
        "?id=566b4ad31f1d40eeb65b8cf3a4f087ca"
    ),
    "retrieved_on": "2026-08-25",
    "study_citation": (
        "Becker EA, Forney KA, Miller DL, Fiedler PC, Barlow J, Moore JE. 2020. "
        "Habitat-based density estimates for cetaceans in the California "
        "Current Ecosystem based on 1991-2018 survey data. U.S. Department of "
        "Commerce, NOAA Technical Memorandum NMFS-SWFSC-638. "
        "https://doi.org/10.25923/3znq-yx13"
    ),
    "metadata_citation": (
        "NMFS Office of Science and Technology, 2026: Predictive Models of "
        "Cetacean Densities in the California Current Ecosystem, 2020b, "
        "https://www.fisheries.noaa.gov/inport/item/64349"
    ),
    "use_constraint": (
        "Distributed by NMFS with a no-warranty disclaimer; the user assumes "
        "the entire risk related to use of these data."
    ),
}

#: Statements that must accompany the layer wherever it is displayed. They are
#: the project brief's scientific-communication rules expressed as data, so the
#: exporter and the application cannot drift apart on what the layer claims.
DISPLAY_STATEMENTS: Final[tuple[str, ...]] = (
    "Modeled blue-whale density, not observed whales and not sightings.",
    "A single multi-year summer-fall average; it is not a time series and "
    "supports no monthly or seasonal claim.",
    "Values were transferred to a 5 km reporting grid. That grid does not "
    "improve the roughly 0.1-degree resolution of the source model.",
    "The source model's per-cell uncertainty (a coefficient of variation) is "
    "not propagated into this layer and is not displayed.",
    "This layer shows habitat only. It states no vessel exposure, no "
    "collision probability, and no strike risk.",
)


#: Source metadata copied into the public manifest.
#:
#: The source artifact's embedded metadata is producer-controlled, so nothing
#: from it reaches a public artifact unless it is named here and passes the
#: validation below. Unlisted keys are dropped rather than copied, and a listed
#: key that is missing or malformed fails the export.
PUBLIC_METHOD_TEXT_FIELDS: Final = (
    "name",
    "contribution",
    "target_density",
    "uncertainty_propagation",
    "resolution_limit",
)
PUBLIC_METHOD_NUMBER_FIELDS: Final = (
    "source_overlap_area_tolerance_m2",
    "coverage_exact_tolerance_m2",
    "coverage_numerical_tolerance_m2",
)
PUBLIC_INPUT_CHECKSUM_FIELDS: Final = (
    "whale_source_sha256",
    "target_grid_sha256",
    "configuration_sha256",
)

MAX_PUBLIC_TEXT_LENGTH: Final = 400

_SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class WhaleDisplayExportError(ValueError):
    """Raised when display-export input, transformation, or output is invalid."""


class WhaleDisplayExportInputError(WhaleDisplayExportError):
    """Raised when the source artifact violates the accepted input contract."""


class WhaleDisplayExportGeometryError(WhaleDisplayExportError):
    """Raised when transformed display geometry is unusable or implausible."""


class WhaleDisplayExportOutputError(WhaleDisplayExportError):
    """Raised when an export bundle cannot be published to a safe destination."""


@dataclass(frozen=True, slots=True)
class SourceInspection:
    """One validated `blue_whale_grid_transfer_v1` artifact and its identity."""

    path: Path
    sha256: str
    table: pa.Table
    geometries: tuple[BaseGeometry, ...]
    dataset_metadata: Mapping[str, object]
    lineage_sha256: str | None
    run_id: str | None

    @property
    def feature_count(self) -> int:
        return int(self.table.num_rows)


@dataclass(frozen=True, slots=True)
class TransformDiagnostics:
    """What the projected-to-geographic step actually did, for the manifest."""

    feature_count: int
    unique_cell_count: int
    polygon_part_count: int
    interior_ring_count: int
    coordinate_count: int
    geometry_types: tuple[str, ...]
    bounds: tuple[float, float, float, float]
    density_min: float
    density_max: float
    abundance_total: float
    water_area_km2_total: float
    max_vertex_roundtrip_metres: float
    transformation_definition: str
    transformation_accuracy_metres: float | None
    configured_map_extent: tuple[float, float, float, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_count": self.feature_count,
            "unique_cell_count": self.unique_cell_count,
            "polygon_part_count": self.polygon_part_count,
            "interior_ring_count": self.interior_ring_count,
            "coordinate_count": self.coordinate_count,
            "geometry_types": list(self.geometry_types),
            "bounds_lon_lat": list(self.bounds),
            "modeled_density_animals_per_km2_min": self.density_min,
            "modeled_density_animals_per_km2_max": self.density_max,
            "modeled_abundance_allocation_animals_total": self.abundance_total,
            "water_area_km2_total": self.water_area_km2_total,
            "max_vertex_roundtrip_metres": self.max_vertex_roundtrip_metres,
            "configured_map_extent_lon_lat": list(self.configured_map_extent),
            "map_extent_display_tolerance_degrees": (
                MAP_EXTENT_DISPLAY_TOLERANCE_DEGREES
            ),
        }


@dataclass(frozen=True, slots=True)
class DisplayExport:
    """The exact bytes of one deterministic export, before they are written."""

    geojson: bytes
    diagnostics: TransformDiagnostics
    source: SourceInspection

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.geojson).hexdigest()


@dataclass(frozen=True, slots=True)
class DisplayExportResult:
    """Identities of a published export bundle."""

    output_path: Path
    manifest_path: Path
    output_sha256: str
    output_bytes: int
    manifest_sha256: str
    diagnostics: TransformDiagnostics

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": WHALE_DISPLAY_EXPORT_CONTRACT,
            "output": {
                "path": self.output_path.as_posix(),
                "sha256": self.output_sha256,
                "bytes": self.output_bytes,
            },
            "manifest": {
                "path": self.manifest_path.as_posix(),
                "sha256": self.manifest_sha256,
            },
            "diagnostics": self.diagnostics.to_dict(),
        }


def _canonical_json(value: Mapping[str, object]) -> str:
    """Serialize deterministically, refusing NaN and Infinity.

    `allow_nan=False` matters here: JSON has no non-finite numbers, so emitting
    them would produce a public artifact that strict parsers reject.
    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version() -> str:
    try:
        return version("socal-whale-vessel-analysis")
    except PackageNotFoundError:
        return "uninstalled"


def _software_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "package": _package_version(),
        "pyarrow": pa.__version__,
        "pyproj": pyproj.__version__,
        "proj": pyproj.proj_version_str,
        "shapely": shapely.__version__,
        "geos": shapely.geos_version_string,
        "platform": sys.platform,
    }


def _require_finite(values: Sequence[float], column: str) -> None:
    for index, value in enumerate(values):
        if not math.isfinite(value):
            raise WhaleDisplayExportInputError(
                f"{column} is not finite at source row {index}"
            )


def _reject_location_like(value: str, field: str) -> None:
    """Reject text shaped like a filesystem path, UNC share, or URL.

    Public metadata describes a method; it never needs to name a location. A
    value that looks like one is either a mistake or an attempt to smuggle a
    local path into a published artifact, and both should stop the export.
    """
    if "\\" in value:
        raise WhaleDisplayExportInputError(
            f"source metadata {field} contains a backslash path separator"
        )
    if len(value) >= 2 and value[1] == ":" and value[0].isalpha():
        raise WhaleDisplayExportInputError(
            f"source metadata {field} looks like a drive-letter path"
        )
    if "://" in value or value.startswith(("/", "~/", "file:")):
        raise WhaleDisplayExportInputError(
            f"source metadata {field} looks like a URL or absolute path"
        )


def _public_text(value: object, field: str) -> str:
    """Validate one producer-supplied string before it becomes public."""
    if not isinstance(value, str):
        raise WhaleDisplayExportInputError(
            f"source metadata {field} must be a string; found {type(value).__name__}"
        )
    if not value.strip():
        raise WhaleDisplayExportInputError(f"source metadata {field} is blank")
    if len(value) > MAX_PUBLIC_TEXT_LENGTH:
        raise WhaleDisplayExportInputError(
            f"source metadata {field} exceeds {MAX_PUBLIC_TEXT_LENGTH} characters"
        )
    if any(character < " " or character == "" for character in value):
        raise WhaleDisplayExportInputError(
            f"source metadata {field} contains a control character"
        )
    _reject_location_like(value, field)
    return value


def _public_number(value: object, field: str) -> float:
    """Validate one producer-supplied number before it becomes public."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WhaleDisplayExportInputError(
            f"source metadata {field} must be a number; found {type(value).__name__}"
        )
    number = float(value)
    if not math.isfinite(number):
        raise WhaleDisplayExportInputError(f"source metadata {field} is not finite")
    return number


def _public_sha256(value: object, field: str) -> str:
    """Validate one producer-supplied checksum before it becomes public."""
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise WhaleDisplayExportInputError(
            f"source metadata {field} must be 64 lowercase hexadecimal characters"
        )
    return value


def _public_run_id(value: object) -> str:
    """Validate the generation run identifier before it becomes public."""
    if not isinstance(value, str) or not _RUN_ID_PATTERN.fullmatch(value):
        raise WhaleDisplayExportInputError(
            "source lineage run_id must be 1-64 characters of letters, digits, "
            "'.', '_' or '-', starting with a letter or digit"
        )
    return value


def _sanitized_source_metadata(dataset: Mapping[str, object]) -> dict[str, object]:
    """Rebuild the publishable subset of source metadata, field by field.

    Nothing is copied wholesale. Each field below is named, located, and
    validated, so an unlisted or malformed key cannot reach a public artifact
    however the source artifact was produced.
    """
    method = dataset.get("method")
    if not isinstance(method, dict):
        raise WhaleDisplayExportInputError("source metadata method must be an object")
    inputs = dataset.get("inputs")
    if not isinstance(inputs, dict):
        raise WhaleDisplayExportInputError("source metadata inputs must be an object")

    public_method: dict[str, object] = {}
    for name in PUBLIC_METHOD_TEXT_FIELDS:
        if name not in method:
            raise WhaleDisplayExportInputError(
                f"source metadata method.{name} is absent"
            )
        public_method[name] = _public_text(method[name], f"method.{name}")
    for name in PUBLIC_METHOD_NUMBER_FIELDS:
        if name not in method:
            raise WhaleDisplayExportInputError(
                f"source metadata method.{name} is absent"
            )
        public_method[name] = _public_number(method[name], f"method.{name}")

    public_inputs: dict[str, object] = {}
    for name in PUBLIC_INPUT_CHECKSUM_FIELDS:
        if name not in inputs:
            raise WhaleDisplayExportInputError(
                f"source metadata inputs.{name} is absent"
            )
        public_inputs[name] = _public_sha256(inputs[name], f"inputs.{name}")

    return {"method": public_method, "inputs": public_inputs}


def _read_source_lineage(
    lineage_path: Path, source_sha256: str
) -> tuple[str | None, str | None]:
    """Return the source run id and lineage checksum without reading its paths.

    The generation lineage records local filesystem locations, so only the two
    non-locational facts below are lifted out of it: which run produced the
    artifact, and whether that run's recorded output checksum agrees with the
    bytes actually being exported. Nothing else from the file reaches a public
    artifact.
    """
    if not lineage_path.is_file():
        return None, None
    try:
        document = json.loads(lineage_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WhaleDisplayExportInputError(
            f"source lineage sidecar could not be read: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise WhaleDisplayExportInputError("source lineage sidecar must be an object")
    if document.get("contract") != WHALE_GRID_LINEAGE_CONTRACT:
        raise WhaleDisplayExportInputError(
            f"source lineage sidecar contract must be {WHALE_GRID_LINEAGE_CONTRACT}"
        )
    output = document.get("output")
    recorded = output.get("sha256") if isinstance(output, dict) else None
    if recorded != source_sha256:
        raise WhaleDisplayExportInputError(
            "source lineage sidecar records a different output checksum than the "
            "supplied source artifact"
        )
    run = document.get("run")
    run_id = run.get("run_id") if isinstance(run, dict) else None
    return (
        None if run_id is None else _public_run_id(run_id),
        _sha256_file(lineage_path),
    )


def _validate_geo_metadata(table: pa.Table) -> None:
    metadata = table.schema.metadata or {}
    raw = metadata.get(b"geo")
    if raw is None:
        raise WhaleDisplayExportInputError("source is missing GeoParquet metadata")
    geo = json.loads(raw)
    if geo.get("primary_column") != GEOMETRY_COLUMN:
        raise WhaleDisplayExportInputError(
            f"source primary geometry column must be {GEOMETRY_COLUMN}"
        )
    column = geo.get("columns", {}).get(GEOMETRY_COLUMN)
    if not isinstance(column, dict):
        raise WhaleDisplayExportInputError(
            "source GeoParquet metadata has no geometry column entry"
        )
    if column.get("encoding") != "WKB":
        raise WhaleDisplayExportInputError("source geometry encoding must be WKB")
    try:
        crs = CRS.from_json_dict(column["crs"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WhaleDisplayExportInputError(
            f"source GeoParquet CRS could not be read: {exc}"
        ) from exc
    if crs.to_epsg() != CRS.from_user_input(SOURCE_CRS).to_epsg():
        raise WhaleDisplayExportInputError(
            f"source geometry CRS must be {SOURCE_CRS}; found {crs.to_string()}"
        )


def _validate_dataset_metadata(table: pa.Table) -> Mapping[str, object]:
    metadata = table.schema.metadata or {}
    raw = metadata.get(b"whale_vessel_analysis")
    if raw is None:
        raise WhaleDisplayExportInputError(
            "source is missing its whale_vessel_analysis dataset metadata"
        )
    dataset = json.loads(raw)
    if not isinstance(dataset, dict):
        raise WhaleDisplayExportInputError("source dataset metadata must be an object")
    if dataset.get("contract") != WHALE_GRID_CONTRACT:
        raise WhaleDisplayExportInputError(
            f"source contract must be {WHALE_GRID_CONTRACT}; "
            f"found {dataset.get('contract')!r}"
        )
    if dataset.get("schema_version") != WHALE_GRID_DATASET_SCHEMA_VERSION:
        raise WhaleDisplayExportInputError(
            "source schema version must be "
            f"{WHALE_GRID_DATASET_SCHEMA_VERSION}; "
            f"found {dataset.get('schema_version')!r}"
        )
    if dataset.get("analysis_crs") != SOURCE_CRS:
        raise WhaleDisplayExportInputError(
            f"source analysis CRS must be {SOURCE_CRS}; "
            f"found {dataset.get('analysis_crs')!r}"
        )
    # Only the sanitized subset leaves this function, so nothing downstream can
    # copy an unvalidated field into a public artifact.
    return _sanitized_source_metadata(cast(Mapping[str, object], dataset))


def _validate_schema(table: pa.Table) -> None:
    actual = [(field.name, field.type) for field in table.schema]
    expected = [(name, kind) for name, kind in SOURCE_SCHEMA]
    if actual != expected:
        actual_names = [name for name, _ in actual]
        expected_names = [name for name, _ in expected]
        if actual_names != expected_names:
            raise WhaleDisplayExportInputError(
                f"source columns must be exactly {expected_names}; found {actual_names}"
            )
        mismatched = [
            f"{name}: expected {kind}, found {found_kind}"
            for (name, kind), (_, found_kind) in zip(expected, actual, strict=True)
            if kind != found_kind
        ]
        raise WhaleDisplayExportInputError(
            f"source column types do not match the contract: {'; '.join(mismatched)}"
        )
    for field in table.schema:
        if field.nullable:
            raise WhaleDisplayExportInputError(
                f"source column {field.name} must be declared non-nullable"
            )
    for name in table.column_names:
        if table[name].null_count:
            raise WhaleDisplayExportInputError(f"source column {name} contains nulls")


def _validate_identity_and_values(table: pa.Table) -> None:
    if table.num_rows == 0:
        raise WhaleDisplayExportInputError("source contains no rows")
    cell_ids = cast(list[str], table["cell_id"].to_pylist())
    rows = cast(list[int], table["row_index"].to_pylist())
    columns = cast(list[int], table["column_index"].to_pylist())
    if len(set(cell_ids)) != len(cell_ids):
        raise WhaleDisplayExportInputError("source cell_id values are not unique")
    for index, (cell_id, row, column) in enumerate(
        zip(cell_ids, rows, columns, strict=True)
    ):
        if cell_id != CELL_ID_PATTERN.format(row=row, column=column):
            raise WhaleDisplayExportInputError(
                f"source cell_id {cell_id!r} does not match its row/column "
                f"index at source row {index}"
            )
    ordered = sorted(zip(rows, columns, strict=True))
    if list(zip(rows, columns, strict=True)) != ordered:
        raise WhaleDisplayExportInputError(
            f"source rows are not in the contract order ({ROW_ORDER})"
        )

    density = cast(list[float], table["modeled_density_animals_per_km2"].to_pylist())
    abundance = cast(
        list[float], table["modeled_abundance_allocation_animals"].to_pylist()
    )
    water = cast(list[float], table["water_area_km2"].to_pylist())
    coverage = cast(list[float], table["source_coverage_fraction"].to_pylist())
    _require_finite(density, "modeled_density_animals_per_km2")
    _require_finite(abundance, "modeled_abundance_allocation_animals")
    _require_finite(water, "water_area_km2")
    _require_finite(coverage, "source_coverage_fraction")
    for index, value in enumerate(density):
        if value < 0.0:
            raise WhaleDisplayExportInputError(
                f"modeled_density_animals_per_km2 is negative at source row {index}"
            )
    for index, value in enumerate(abundance):
        if value < 0.0:
            raise WhaleDisplayExportInputError(
                "modeled_abundance_allocation_animals is negative at source row "
                f"{index}"
            )
    for index, value in enumerate(water):
        if value <= 0.0:
            raise WhaleDisplayExportInputError(
                f"water_area_km2 must be positive at source row {index}"
            )
    for index, value in enumerate(coverage):
        if not 0.0 <= value <= 1.0:
            raise WhaleDisplayExportInputError(
                f"source_coverage_fraction is outside [0,1] at source row {index}"
            )


def load_source(path: Path, *, expected_sha256: str | None = None) -> SourceInspection:
    """Validate one whale-grid artifact against the exact accepted contract."""
    if not path.is_file():
        raise WhaleDisplayExportInputError(f"source artifact does not exist: {path}")
    if path.suffix.lower() != ".parquet":
        raise WhaleDisplayExportInputError("source artifact must be a .parquet file")
    sha256 = _sha256_file(path)
    if expected_sha256 is not None and expected_sha256.lower() != sha256:
        raise WhaleDisplayExportInputError(
            f"source checksum mismatch: expected {expected_sha256.lower()}, "
            f"found {sha256}"
        )
    try:
        table = pq.read_table(path, use_threads=False)
    except Exception as exc:  # pragma: no cover - surfaced as a contract failure
        raise WhaleDisplayExportInputError(
            f"source artifact could not be read as Parquet: {exc}"
        ) from exc
    dataset_metadata = _validate_dataset_metadata(table)
    _validate_geo_metadata(table)
    _validate_schema(table)
    _validate_identity_and_values(table)
    geometries = _decode_geometries(table)
    run_id, lineage_sha256 = _read_source_lineage(
        path.with_suffix(path.suffix + LINEAGE_SUFFIX), sha256
    )
    return SourceInspection(
        path=path,
        sha256=sha256,
        table=table,
        geometries=tuple(geometries),
        dataset_metadata=dataset_metadata,
        lineage_sha256=lineage_sha256,
        run_id=run_id,
    )


def _decode_geometries(table: pa.Table) -> list[BaseGeometry]:
    try:
        geometries: list[BaseGeometry] = list(
            from_wkb(table[GEOMETRY_COLUMN].to_pylist())
        )
    except (GEOSException, ValueError, TypeError) as exc:
        raise WhaleDisplayExportInputError(
            f"source geometry could not be decoded from WKB: {exc}"
        ) from exc
    for index, geometry in enumerate(geometries):
        if geometry is None or geometry.is_empty:
            raise WhaleDisplayExportInputError(
                f"source geometry is empty at source row {index}"
            )
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            raise WhaleDisplayExportInputError(
                f"source geometry at row {index} is {geometry.geom_type}; only "
                "Polygon and MultiPolygon can be displayed"
            )
        if not geometry.is_valid:
            raise WhaleDisplayExportInputError(
                f"source geometry is invalid at source row {index}"
            )
    return geometries


def _ring_coordinates(geometry: BaseGeometry) -> list[list[list[float]]]:
    """Return one polygon's rings as RFC 7946 position lists."""
    polygon = cast(Polygon, geometry)
    rings = [polygon.exterior, *polygon.interiors]
    return [[[float(x), float(y)] for x, y in ring.coords] for ring in rings]


def _geometry_mapping(geometry: BaseGeometry) -> dict[str, object]:
    if geometry.geom_type == "Polygon":
        return {"type": "Polygon", "coordinates": _ring_coordinates(geometry)}
    parts = [_ring_coordinates(part) for part in shapely.get_parts(geometry).tolist()]
    return {"type": "MultiPolygon", "coordinates": parts}


def build_export(
    source: SourceInspection, config: ProcessingConfig | None = None
) -> DisplayExport:
    """Transform the validated source into the exact public GeoJSON bytes.

    Nothing here changes an analytical number. Coordinates move from EPSG:3310
    to WGS 84 with an explicit x/y order, rings are oriented as RFC 7946
    requires, and every value is written at full double precision — no
    rounding, no simplification, no densification, no reprojection of areas.
    """
    extent = (
        config if config is not None else load_default_config()
    ).spatial.map_extent
    table = source.table
    geometries = source.geometries

    to_wgs84 = Transformer.from_crs(SOURCE_CRS, DISPLAY_CRS, always_xy=True)
    to_source = Transformer.from_crs(DISPLAY_CRS, SOURCE_CRS, always_xy=True)

    def to_display_positions(
        coordinates: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Move an (n, 2) coordinate block with an explicit x/y order."""
        longitude, latitude = to_wgs84.transform(coordinates[:, 0], coordinates[:, 1])
        return cast("NDArray[np.float64]", np.column_stack([longitude, latitude]))

    cell_ids = cast(list[str], table["cell_id"].to_pylist())
    density = cast(list[float], table["modeled_density_animals_per_km2"].to_pylist())
    abundance = cast(
        list[float], table["modeled_abundance_allocation_animals"].to_pylist()
    )
    water = cast(list[float], table["water_area_km2"].to_pylist())
    coverage = cast(list[float], table["source_coverage_fraction"].to_pylist())
    status = cast(list[str], table["coverage_status"].to_pylist())

    features: list[dict[str, object]] = []
    polygon_parts = 0
    interior_rings = 0
    coordinate_count = 0
    geometry_types: set[str] = set()
    max_roundtrip = 0.0
    min_lon = min_lat = math.inf
    max_lon = max_lat = -math.inf

    for index, geometry in enumerate(geometries):
        projected = shapely.transform(geometry, to_display_positions)
        oriented = shapely.orient_polygons(projected)
        if oriented.is_empty or not oriented.is_valid:
            raise WhaleDisplayExportGeometryError(
                f"transformed geometry is empty or invalid at source row {index}"
            )
        if oriented.geom_type != geometry.geom_type:
            raise WhaleDisplayExportGeometryError(
                f"transformed geometry type changed at source row {index}: "
                f"{geometry.geom_type} became {oriented.geom_type}"
            )
        source_positions = get_coordinates(geometry)
        # Ring orientation reverses vertex order, so the round-trip check reads
        # the projected geometry, whose positions still line up one-for-one with
        # the source. `oriented` supplies the published coordinates.
        projected_positions = get_coordinates(projected)
        display_positions = get_coordinates(oriented)
        if display_positions.shape != source_positions.shape:
            raise WhaleDisplayExportGeometryError(
                f"transformed geometry lost or gained vertices at source row {index}"
            )
        parts = shapely.get_parts(oriented)
        if len(parts) != len(shapely.get_parts(geometry)):
            raise WhaleDisplayExportGeometryError(
                f"transformed geometry changed part count at source row {index}"
            )
        source_rings = int(
            sum(shapely.get_num_interior_rings(shapely.get_parts(geometry)))
        )
        display_rings = int(sum(shapely.get_num_interior_rings(parts)))
        if display_rings != source_rings:
            raise WhaleDisplayExportGeometryError(
                f"transformed geometry changed hole count at source row {index}"
            )

        longitudes = display_positions[:, 0]
        latitudes = display_positions[:, 1]
        if (
            longitudes.min() < LONGITUDE_BOUNDS[0]
            or longitudes.max() > LONGITUDE_BOUNDS[1]
            or latitudes.min() < LATITUDE_BOUNDS[0]
            or latitudes.max() > LATITUDE_BOUNDS[1]
        ):
            raise WhaleDisplayExportGeometryError(
                "transformed coordinates fall outside valid longitude/latitude "
                f"ranges at source row {index}; check the x/y axis order"
            )
        back_x, back_y = to_source.transform(
            projected_positions[:, 0], projected_positions[:, 1]
        )
        roundtrip = float(
            np.hypot(
                back_x - source_positions[:, 0], back_y - source_positions[:, 1]
            ).max()
        )
        max_roundtrip = max(max_roundtrip, roundtrip)

        min_lon = min(min_lon, float(longitudes.min()))
        max_lon = max(max_lon, float(longitudes.max()))
        min_lat = min(min_lat, float(latitudes.min()))
        max_lat = max(max_lat, float(latitudes.max()))
        polygon_parts += len(parts)
        interior_rings += display_rings
        coordinate_count += int(display_positions.shape[0])
        geometry_types.add(oriented.geom_type)

        features.append(
            {
                "type": "Feature",
                "id": cell_ids[index],
                "geometry": _geometry_mapping(oriented),
                "properties": {
                    "object_id": index + 1,
                    "cell_id": cell_ids[index],
                    "modeled_density_animals_per_km2": density[index],
                    "modeled_abundance_allocation_animals": abundance[index],
                    "water_area_km2": water[index],
                    "source_coverage_fraction": coverage[index],
                    "coverage_status": status[index],
                },
            }
        )

    tolerance = MAP_EXTENT_DISPLAY_TOLERANCE_DEGREES
    if not (
        extent.lon_min - tolerance <= min_lon
        and max_lon <= extent.lon_max + tolerance
        and extent.lat_min - tolerance <= min_lat
        and max_lat <= extent.lat_max + tolerance
    ):
        raise WhaleDisplayExportGeometryError(
            f"transformed extent ({min_lon}, {min_lat}, {max_lon}, {max_lat}) "
            f"falls outside the configured map extent ({extent.lon_min}, "
            f"{extent.lat_min}, {extent.lon_max}, {extent.lat_max}) by more "
            f"than {tolerance} degrees"
        )

    collection: dict[str, object] = {
        "type": "FeatureCollection",
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "features": features,
    }
    payload = (_canonical_json(collection) + "\n").encode("utf-8")

    diagnostics = TransformDiagnostics(
        feature_count=len(features),
        unique_cell_count=len(set(cell_ids)),
        polygon_part_count=polygon_parts,
        interior_ring_count=interior_rings,
        coordinate_count=coordinate_count,
        geometry_types=tuple(sorted(geometry_types)),
        bounds=(min_lon, min_lat, max_lon, max_lat),
        density_min=min(density),
        density_max=max(density),
        abundance_total=math.fsum(abundance),
        water_area_km2_total=math.fsum(water),
        max_vertex_roundtrip_metres=max_roundtrip,
        transformation_definition=to_wgs84.definition,
        transformation_accuracy_metres=to_wgs84.accuracy,
        configured_map_extent=(
            extent.lon_min,
            extent.lat_min,
            extent.lon_max,
            extent.lat_max,
        ),
    )
    return DisplayExport(geojson=payload, diagnostics=diagnostics, source=source)


def build_manifest(
    export: DisplayExport,
    *,
    output_name: str,
    exported_at: datetime,
) -> dict[str, object]:
    """Build the sanitized, publishable export manifest.

    Every value here is either a checksum, a count, a unit, a public citation,
    or a declared parameter. No filesystem path, account identifier, credential,
    raw input, or VSR-derived value may appear.
    """
    if exported_at.utcoffset() != UTC.utcoffset(exported_at):
        raise WhaleDisplayExportOutputError("exported_at must be timezone-aware UTC")
    diagnostics = export.diagnostics
    return {
        "contract": WHALE_DISPLAY_EXPORT_MANIFEST_CONTRACT,
        "dataset_contract": WHALE_DISPLAY_EXPORT_CONTRACT,
        "processing_version": WHALE_DISPLAY_EXPORT_PROCESSING_VERSION,
        "exported_at": exported_at.isoformat().replace("+00:00", "Z"),
        "source": {
            "artifact_id": "blue-whale-grid-transfer",
            "contract": WHALE_GRID_CONTRACT,
            "schema_version": WHALE_GRID_DATASET_SCHEMA_VERSION,
            "sha256": export.source.sha256,
            "run_id": export.source.run_id,
            "generation_lineage_sha256": export.source.lineage_sha256,
            "analysis_crs": SOURCE_CRS,
            "row_order": ROW_ORDER,
            "method": export.source.dataset_metadata["method"],
            "inputs": export.source.dataset_metadata["inputs"],
            "visual_verification": {
                "status": "recorded_separately",
                "bound_to_sha256": export.source.sha256,
                "reference": "analysis/README.md",
            },
        },
        "source_model": dict(SOURCE_MODEL_REFERENCE),
        "transformation": {
            "source_crs": SOURCE_CRS,
            "display_crs": DISPLAY_CRS,
            "always_xy": True,
            "definition": diagnostics.transformation_definition,
            "operation_accuracy_metres": diagnostics.transformation_accuracy_metres,
            "ring_orientation": (
                "RFC 7946: exterior rings counterclockwise, interior rings clockwise"
            ),
            "geometry_simplification": "not_performed",
            "coordinate_rounding": "not_performed",
            "densification": "not_performed",
            "value_recomputation": "not_performed",
        },
        "fields": {
            "published": [
                {"name": name, "unit": unit, "meaning": meaning}
                for name, unit, meaning in PUBLIC_FIELDS
            ],
            "withheld": [
                {"name": name, "reason": reason} for name, reason in WITHHELD_FIELDS
            ],
            "feature_id": "cell_id",
            "display_object_id": "object_id",
        },
        "display_statements": list(DISPLAY_STATEMENTS),
        "output": {
            "name": output_name,
            "format": "GeoJSON (RFC 7946)",
            "media_type": "application/geo+json",
            "bytes": len(export.geojson),
            "sha256": export.sha256,
            **diagnostics.to_dict(),
        },
        "software": _software_versions(),
    }


def reject_protected_location(resolved: Path) -> None:
    """Refuse raw-source and version-control locations, in any checkout.

    The allowlist below already excludes these, so this is defence in depth: it
    keeps the most damaging destinations refused, with a message that names why,
    even if the allowlist is ever widened. It matches by directory shape rather
    than by absolute path, so a sibling worktree's `data/raw` is refused exactly
    like this one's.
    """
    parts = resolved.parts
    for index in range(1, len(parts)):
        if parts[index] == "raw" and parts[index - 1] == "data":
            raise WhaleDisplayExportOutputError(
                f"display-export output cannot be written under raw data: {resolved}"
            )
    if ".git" in parts:
        raise WhaleDisplayExportOutputError(
            f"display-export output cannot be written under Git metadata: {resolved}"
        )


def validate_output_target(
    output_path: Path, approved_roots: Sequence[Path] | None = None
) -> None:
    """Refuse every destination outside the approved output roots.

    `approved_roots` exists so tests can exercise publication against their own
    temporary directory. It is a widening seam, so `reject_protected_location`
    runs first and unconditionally: no supplied root can authorize a raw-data or
    Git-metadata destination. The CLI never passes it, so the shipped behaviour
    is always `APPROVED_OUTPUT_ROOTS`.
    """
    if output_path.suffix.lower() != GEOJSON_SUFFIX:
        raise WhaleDisplayExportOutputError(
            f"display-export output path must end in {GEOJSON_SUFFIX}"
        )
    resolved = output_path.resolve()
    reject_protected_location(resolved)
    roots = (
        APPROVED_OUTPUT_ROOTS
        if approved_roots is None
        else tuple(root.resolve() for root in approved_roots)
    )
    if any(resolved.is_relative_to(root) for root in roots):
        return
    approved = ", ".join(root.as_posix() for root in roots)
    raise WhaleDisplayExportOutputError(
        f"display-export output must be under one of the approved roots "
        f"({approved}); refused {resolved}"
    )


def _write_bytes(path: Path, payload: bytes) -> None:
    with path.open("xb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())


def _commit_pair(
    temporary_output: Path,
    output_path: Path,
    temporary_manifest: Path,
    manifest_path: Path,
    *,
    overwrite: bool,
) -> None:
    """Publish both files together, or leave the destination as it was."""
    backups: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    try:
        if overwrite:
            for final in (output_path, manifest_path):
                if final.exists():
                    backup = final.with_name(f".{final.name}.{uuid.uuid4().hex}.backup")
                    os.replace(final, backup)
                    backups.append((backup, final))
        elif output_path.exists() or manifest_path.exists():
            raise WhaleDisplayExportOutputError(
                "output or manifest already exists; pass overwrite=True to replace both"
            )
        os.replace(temporary_output, output_path)
        committed.append(output_path)
        os.replace(temporary_manifest, manifest_path)
        committed.append(manifest_path)
    except Exception:
        for final in reversed(committed):
            final.unlink(missing_ok=True)
        for backup, final in reversed(backups):
            os.replace(backup, final)
        raise
    else:
        for backup, _final in backups:
            backup.unlink(missing_ok=True)


def write_display_export(
    export: DisplayExport,
    output_path: Path,
    *,
    exported_at: datetime | None = None,
    overwrite: bool = False,
    approved_roots: Sequence[Path] | None = None,
) -> DisplayExportResult:
    """Atomically publish the GeoJSON and its sanitized export manifest."""
    validate_output_target(output_path, approved_roots)
    manifest_path = output_path.with_name(output_path.name + MANIFEST_SUFFIX)
    if not overwrite and (output_path.exists() or manifest_path.exists()):
        raise WhaleDisplayExportOutputError(
            "output or manifest already exists; use explicit overwrite authorization"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        export,
        output_name=output_path.name,
        exported_at=exported_at if exported_at is not None else datetime.now(UTC),
    )
    manifest_payload = (_canonical_json(manifest) + "\n").encode("utf-8")
    token = uuid.uuid4().hex
    temporary_output = output_path.with_name(f".{output_path.name}.{token}.tmp")
    temporary_manifest = manifest_path.with_name(f".{manifest_path.name}.{token}.tmp")
    try:
        _write_bytes(temporary_output, export.geojson)
        _write_bytes(temporary_manifest, manifest_payload)
        _commit_pair(
            temporary_output,
            output_path,
            temporary_manifest,
            manifest_path,
            overwrite=overwrite,
        )
    except WhaleDisplayExportError:
        raise
    except Exception as exc:
        raise WhaleDisplayExportOutputError(
            f"could not write display export {output_path}: {exc}"
        ) from exc
    finally:
        temporary_output.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)
    return DisplayExportResult(
        output_path=output_path,
        manifest_path=manifest_path,
        output_sha256=export.sha256,
        output_bytes=len(export.geojson),
        manifest_sha256=hashlib.sha256(manifest_payload).hexdigest(),
        diagnostics=export.diagnostics,
    )
