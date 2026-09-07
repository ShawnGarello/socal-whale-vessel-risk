"""Validated public-display and application-results exports for M6 exposure.

This module crosses the publication boundary; it does not recompute the M6
analysis.  It accepts one checksum-identified ``exploratory_relative_exposure_v1``
bundle, re-verifies both serialized analytical grids against their sensitivity
report, and emits two deliberately separate downstream contracts:

* WGS 84 GeoJSON containing qualified 5 km water geometry and display fields;
* a small JSON result carrying exact statistics, denominators, sensitivity,
  provenance, null rules, and presentation strings for a future M7 consumer.

No local path, credential, generation lineage, raw record, VSR geometry, or
VSR-derived geometry enters either public contract.  Execution timestamps and
locators remain in the private upstream ``run-metadata.json``, which this module
does not read.  A caller-supplied UTC delivery timestamp records when an export
was prepared but is excluded from the deterministic analytical result identity.
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
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Final, Literal, TypedDict, cast

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from numpy.typing import NDArray
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError
from shapely.errors import GEOSException
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.exposure import (
    METHODS,
    PERCENTILES,
    ExposureCell,
    analyze_grid,
)
from whale_vessel_analysis.exposure_geometry import (
    DOMAIN_SHA256,
    VSR_SHA256,
    CellAreas,
)
from whale_vessel_analysis.exposure_inputs import (
    VESSEL_QUALITY_SHA256,
    VESSEL_SHA256,
    WATER_SHA256,
    WHALE_SHA256,
    ExposureInputCell,
)
from whale_vessel_analysis.exposure_run import (
    CONTRACT as ANALYTICAL_CONTRACT,
)
from whale_vessel_analysis.exposure_run import (
    json_text,
    method_contract,
    verify_table,
)
from whale_vessel_analysis.vessel_input import selected_method

DISPLAY_CONTRACT: Final = "relative_exposure_display_v1"
DISPLAY_MANIFEST_CONTRACT: Final = "relative_exposure_display_manifest_v1"
RESULTS_CONTRACT: Final = "relative_exposure_application_results_v1"
DELIVERY_VERSION: Final = "1.0.0"
RESULTS_SCHEMA_VERSION: Final = 1
SOURCE_CRS: Final = "EPSG:3310"
DISPLAY_CRS: Final = "EPSG:4326"
MANIFEST_SUFFIX: Final = ".manifest.json"
GEOJSON_SUFFIX: Final = ".geojson"
JSON_SUFFIX: Final = ".json"
MAP_EXTENT_DISPLAY_TOLERANCE_DEGREES: Final = 1e-6

_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
DISPLAY_OUTPUT_ROOTS: Final = (
    (_PROJECT_ROOT / "data" / "derived").resolve(),
    (_PROJECT_ROOT / "data" / "interim").resolve(),
    (_PROJECT_ROOT / "web" / "public" / "layers").resolve(),
)
RESULTS_OUTPUT_ROOTS: Final = (
    (_PROJECT_ROOT / "results").resolve(),
    (_PROJECT_ROOT / "data" / "derived").resolve(),
    (_PROJECT_ROOT / "data" / "interim").resolve(),
)

SOURCE_FILES: Final = {
    "5km": "exposure-5km.parquet",
    "10km": "exposure-10km.parquet",
    "report": "sensitivity-report.json",
}
EXPECTED_INPUT_SHA256: Final = {
    "water": WATER_SHA256,
    "whale": WHALE_SHA256,
    "vessel": VESSEL_SHA256,
    "vessel_quality": VESSEL_QUALITY_SHA256,
    "domain": DOMAIN_SHA256,
    "vsr": VSR_SHA256,
}

SOURCE_SCHEMA: Final[tuple[tuple[str, pa.DataType], ...]] = (
    ("cell_id", pa.string()),
    ("x_min_m", pa.int64()),
    ("y_min_m", pa.int64()),
    ("analysis_status", pa.string()),
    ("water_area_km2", pa.float64()),
    ("qualified_area_km2", pa.float64()),
    ("inside_vsr_area_km2", pa.float64()),
    ("outside_vsr_area_km2", pa.float64()),
    ("excluded_domain_area_km2", pa.float64()),
    ("whale_density_animals_per_km2", pa.float64()),
    ("whale_abundance_animals", pa.float64()),
    ("vessel_km", pa.float64()),
    ("geometry", pa.binary()),
    ("product_intensity", pa.float64()),
    ("product_index", pa.float64()),
    ("product_integrated_qualified", pa.float64()),
    ("product_integrated_inside", pa.float64()),
    ("product_integrated_outside", pa.float64()),
    ("product_high_p80", pa.bool_()),
    ("product_high_p90", pa.bool_()),
    ("product_high_p95", pa.bool_()),
    ("log_traffic_intensity", pa.float64()),
    ("log_traffic_index", pa.float64()),
    ("log_traffic_integrated_qualified", pa.float64()),
    ("log_traffic_integrated_inside", pa.float64()),
    ("log_traffic_integrated_outside", pa.float64()),
    ("log_traffic_high_p80", pa.bool_()),
    ("log_traffic_high_p90", pa.bool_()),
    ("log_traffic_high_p95", pa.bool_()),
)

DISPLAY_FIELDS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "object_id",
        "unitless integer",
        "Display-only 1-based feature identifier in qualified source-row order.",
    ),
    ("cell_id", "unitless identifier", "Stable 5 km analysis-grid identity."),
    (
        "water_area_km2",
        "km^2",
        "Full modeled-support water area used in both intensity denominators.",
    ),
    (
        "qualified_area_km2",
        "km^2",
        "Exact receiver-domain-qualified water area used for integration.",
    ),
    (
        "product_intensity",
        "modeled animals * vessel-km / km^4, period total",
        "Primary proportional overlap intensity W * (L / full water km^2).",
    ),
    (
        "product_index",
        "unitless [0,1] or null",
        "Primary intensity divided by the qualified-domain maximum; null when "
        "the maximum is zero.",
    ),
    (
        "product_high_p90",
        "boolean or null",
        "Primary all-valid qualified-area-weighted p90 classification; null when "
        "the threshold is unavailable.",
    ),
    (
        "log_traffic_intensity",
        "dimensionless",
        "Sensitivity intensity (W / 1 animal per km^2) * log1p(T / 1 period "
        "vessel-km per km^2).",
    ),
    (
        "log_traffic_index",
        "unitless [0,1] or null",
        "Log-traffic intensity divided by its qualified-domain maximum; null "
        "when the maximum is zero.",
    ),
    (
        "log_traffic_high_p90",
        "boolean or null",
        "Log-traffic all-valid qualified-area-weighted p90 classification; null "
        "when the threshold is unavailable.",
    ),
)

DISPLAY_STATEMENTS: Final = (
    "The proportional product is the primary exploratory overlap measure; the "
    "log-traffic alternative must accompany it because the inside share changes "
    "materially under traffic compression.",
    "Intensity uses each cell's full modeled-support water area. Integration "
    "uses only exact receiver-qualified water and its fractional inside/outside "
    "VSR split, assuming uniform exposure within each cell's water geometry.",
    "Outside-domain water is excluded, not classified as low traffic. Zero "
    "movement means no retained movement under the accepted AIS rules, not "
    "verified vessel absence.",
    "The index is relative to this artifact's qualified-domain maximum and is "
    "not comparable across releases without that reference.",
    "This is a spatial co-occurrence proxy, not collision probability, predicted "
    "strikes, VSR effectiveness, causation, or a policy recommendation.",
)

SOURCE_REFERENCES: Final[dict[str, dict[str, object]]] = {
    "whales": {
        "publisher": (
            "NMFS Office of Science and Technology; models produced by NOAA "
            "Fisheries Southwest Fisheries Science Center"
        ),
        "product": (
            "Predictive Models of Cetacean Densities in the California Current "
            "Ecosystem, 2020b"
        ),
        "layer": "Blue_whale_summer_fall",
        "survey_basis": "nine survey years during 1991-2018",
        "metadata": "https://www.fisheries.noaa.gov/inport/item/64349",
    },
    "traffic": {
        "publisher": "NOAA Office for Coastal Management / Marine Cadastre",
        "source": "U.S. Coast Guard Nationwide AIS",
        "period": "2024-07-01 through 2024-11-30 UTC",
        "population": "AIS type codes 60-69, 70-79, and 80-89; no length filter",
        "terms": "https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf",
    },
    "vsr": {
        "publisher": (
            "Danielle Alvarez, California Marine Sanctuary Foundation, and "
            "Protecting Blue Whales and Blue Skies"
        ),
        "feature": "California Voluntary Vessel Speed Reduction Zone, FID 126",
        "boundary_year": 2026,
        "snapshot_retrieved": "2026-08-25",
        "public_service": (
            "https://services5.arcgis.com/4biRnCjZju47bNvA/arcgis/rest/services/"
            "WhaleAtlas_2026/FeatureServer/0"
        ),
        "display_rule": (
            "The application references the publisher service directly; no VSR "
            "geometry or derivative is included in these artifacts."
        ),
    },
}

_RUN_ID_PATTERN: Final = re.compile(r"^exposure-[0-9a-f]{24}$")
_SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")


class AvailableNormalizationControl(TypedDict):
    """Allowlisted public shape for an available scaling control."""

    available: Literal[True]
    normalizer: float
    inside_share_difference: float
    all_threshold_memberships_equal: bool


class UnavailableNormalizationControl(TypedDict):
    """Allowlisted public shape for an unavailable scaling control."""

    available: Literal[False]
    reason: str


type PublicNormalizationControl = (
    AvailableNormalizationControl | UnavailableNormalizationControl
)


class PublicNormalizationControls(TypedDict):
    """Only the two predeclared global-scaling checks cross publication."""

    product_max: PublicNormalizationControl
    separate_input_maxima: PublicNormalizationControl


class PublicDisplayDiagnostics(TypedDict):
    """Allowlisted geometry/value diagnostics written to the public manifest."""

    feature_count: int
    unique_cell_count: int
    polygon_part_count: int
    interior_ring_count: int
    coordinate_count: int
    geometry_types: list[str]
    bounds_lon_lat: list[float]
    max_vertex_roundtrip_metres: float
    transformation_definition: str
    transformation_accuracy_metres: float
    configured_map_extent_lon_lat: list[float]
    map_extent_display_tolerance_degrees: float
    qualified_area_km2_total: float
    non_null_index_min: float | None
    non_null_index_max: float | None


class ExposureDeliveryError(ValueError):
    """Base error for a rejected delivery input or output."""


class ExposureDeliveryInputError(ExposureDeliveryError):
    """The supplied M6 bundle violates the accepted delivery input contract."""


class ExposureDeliveryOutputError(ExposureDeliveryError):
    """A public artifact cannot be constructed or safely written."""


@dataclass(frozen=True, slots=True)
class BundleInspection:
    """A fully re-verified analytical bundle; private run metadata is absent."""

    tables: Mapping[str, pa.Table]
    report: Mapping[str, Any]
    source_sha256: Mapping[str, str]
    identity: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DisplayExport:
    """Deterministic GeoJSON bytes plus diagnostics derived during transform."""

    geojson: bytes
    diagnostics: Mapping[str, object]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.geojson).hexdigest()


@dataclass(frozen=True, slots=True)
class ResultsExport:
    """Deterministic application-results bytes for a supplied UTC timestamp."""

    payload: bytes
    document: Mapping[str, object]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()


@dataclass(frozen=True, slots=True)
class DeliveryExport:
    """All three public files prepared before any destination is touched."""

    display: DisplayExport
    display_manifest: bytes
    results: ResultsExport


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Local destinations and identities reported by the command, not published."""

    display_path: Path
    display_manifest_path: Path
    results_path: Path
    display_sha256: str
    display_manifest_sha256: str
    results_sha256: str
    results_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "display_contract": DISPLAY_CONTRACT,
            "results_contract": RESULTS_CONTRACT,
            "display": {
                "path": self.display_path.as_posix(),
                "sha256": self.display_sha256,
            },
            "display_manifest": {
                "path": self.display_manifest_path.as_posix(),
                "sha256": self.display_manifest_sha256,
            },
            "results": {
                "path": self.results_path.as_posix(),
                "sha256": self.results_sha256,
                "results_id": self.results_id,
            },
        }


def canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    """Return strict, stable UTF-8 JSON with no non-finite extension values."""
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def parse_utc_timestamp(value: str) -> datetime:
    """Parse one explicit timezone-aware UTC timestamp for delivery provenance."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExposureDeliveryOutputError(
            "generated-at timestamp must be ISO 8601"
        ) from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ExposureDeliveryOutputError("generated-at timestamp must be UTC")
    return parsed


def _utc_text(value: datetime) -> str:
    if value.utcoffset() != UTC.utcoffset(value):
        raise ExposureDeliveryOutputError("generated_at must be timezone-aware UTC")
    return value.isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExposureDeliveryInputError(f"could not read {path.name}: {exc}") from exc
    if not isinstance(document, dict):
        raise ExposureDeliveryInputError(f"{path.name} must contain a JSON object")
    return cast(Mapping[str, Any], document)


def _compare_verified_value(actual: Any, expected: Any, path: str) -> None:
    """Require an exact typed shape and numerically equivalent verified value."""
    if isinstance(expected, Mapping):
        if not isinstance(actual, dict):
            raise ExposureDeliveryInputError(f"{path} must be an object")
        actual_keys = set(actual)
        expected_keys = set(expected)
        if actual_keys != expected_keys:
            missing = sorted(expected_keys - actual_keys)
            unexpected = sorted(actual_keys - expected_keys)
            raise ExposureDeliveryInputError(
                f"{path} fields differ; missing={missing}, unexpected={unexpected}"
            )
        for key, value in expected.items():
            _compare_verified_value(actual[key], value, f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ExposureDeliveryInputError(f"{path} list shape differs")
        for index, (actual_item, expected_item) in enumerate(
            zip(actual, expected, strict=True)
        ):
            _compare_verified_value(actual_item, expected_item, f"{path}[{index}]")
        return
    if expected is None:
        if actual is not None:
            raise ExposureDeliveryInputError(f"{path} must be null")
        return
    if isinstance(expected, bool):
        if not isinstance(actual, bool) or actual is not expected:
            raise ExposureDeliveryInputError(f"{path} boolean differs")
        return
    if isinstance(expected, int):
        if (
            isinstance(actual, bool)
            or not isinstance(actual, int)
            or actual != expected
        ):
            raise ExposureDeliveryInputError(f"{path} integer differs")
        return
    if isinstance(expected, float):
        absolute_tolerance = (
            1e-6
            if "maximum_" in path and "_residual_m2" in path
            else 1e-9
            if "_km2" in path or "integrated_" in path
            else 1e-12
        )
        if (
            isinstance(actual, bool)
            or not isinstance(actual, (int, float))
            or not math.isfinite(float(actual))
            or not math.isclose(
                float(actual),
                expected,
                rel_tol=1e-12,
                abs_tol=absolute_tolerance,
            )
        ):
            raise ExposureDeliveryInputError(
                f"{path} differs from the value recomputed from verified rows"
            )
        return
    if isinstance(expected, str):
        if not isinstance(actual, str) or actual != expected:
            raise ExposureDeliveryInputError(
                f"{path} text/enumeration differs from the accepted calculation"
            )
        return
    raise AssertionError(f"unsupported verified value at {path}: {type(expected)}")


def _reconstruct_verified_cells(table: pa.Table) -> tuple[ExposureCell, ...]:
    """Reconstruct summary inputs from serialized rows without private lineage.

    ``analyze_grid`` needs only the stored scalar sufficient statistics, exact
    area partitions, identifiers and qualified geometry. The placeholder full-
    water geometry is deliberately never used by that calculation.
    """
    cells: list[ExposureCell] = []
    for row in cast(list[dict[str, Any]], table.to_pylist()):
        water_km2 = float(row["water_area_km2"])
        density = float(row["whale_density_animals_per_km2"])
        abundance = float(row["whale_abundance_animals"])
        vessel_km = float(row["vessel_km"])
        if (
            not all(
                math.isfinite(value) and value >= 0
                for value in (water_km2, density, abundance, vessel_km)
            )
            or water_km2 <= 0
        ):
            raise ExposureDeliveryInputError(
                "analytical sufficient statistics are nonfinite or negative"
            )
        if not math.isclose(
            abundance, density * water_km2, rel_tol=1e-10, abs_tol=1e-9
        ):
            raise ExposureDeliveryInputError(
                "stored whale abundance differs from density times full water area"
            )
        qualified_km2 = float(row["qualified_area_km2"])
        expected_status = "qualified" if qualified_km2 > 0 else "excluded_domain"
        if row["analysis_status"] != expected_status:
            raise ExposureDeliveryInputError(
                "analysis status differs from receiver-qualified area"
            )
        qualified_geometry = (
            _decode_qualified_geometry(row) if qualified_km2 > 0 else Polygon()
        )
        try:
            areas = CellAreas(
                water_m2=water_km2 * 1e6,
                qualified_m2=qualified_km2 * 1e6,
                inside_vsr_m2=float(row["inside_vsr_area_km2"]) * 1e6,
                outside_vsr_m2=float(row["outside_vsr_area_km2"]) * 1e6,
                excluded_domain_m2=float(row["excluded_domain_area_km2"]) * 1e6,
            )
        except ValueError as exc:
            raise ExposureDeliveryInputError(
                f"stored water partitions are invalid: {exc}"
            ) from exc
        source = ExposureInputCell(
            cell_id=row["cell_id"],
            x_min_m=row["x_min_m"],
            y_min_m=row["y_min_m"],
            water=Polygon(),
            water_km2=water_km2,
            whale_density=density,
            whale_abundance=abundance,
            vessel_km=vessel_km,
        )
        cells.append(ExposureCell(source, areas, qualified_geometry))
    return tuple(cells)


def _validate_geo_metadata(table: pa.Table, label: str) -> Mapping[str, Any]:
    metadata = table.schema.metadata or {}
    try:
        geo = json.loads(metadata[b"geo"])
        column = geo["columns"]["geometry"]
        identity = json.loads(metadata[b"whale_vessel_analysis"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ExposureDeliveryInputError(
            f"{label} source metadata is missing or malformed"
        ) from exc
    if not isinstance(column, dict):
        raise ExposureDeliveryInputError(
            f"{label} source geometry metadata is malformed"
        )
    try:
        source_crs = CRS.from_user_input(column.get("crs"))
    except CRSError as exc:
        raise ExposureDeliveryInputError(
            f"{label} source CRS is missing or malformed"
        ) from exc
    if (
        geo.get("primary_column") != "geometry"
        or column.get("encoding") != "WKB"
        or source_crs != CRS.from_epsg(3310)
    ):
        raise ExposureDeliveryInputError(
            f"{label} source must declare WKB geometry in {SOURCE_CRS}"
        )
    if not isinstance(identity, dict):
        raise ExposureDeliveryInputError(f"{label} analytical identity is malformed")
    return cast(Mapping[str, Any], identity)


def _validate_source_schema(table: pa.Table, label: str) -> None:
    actual = [(field.name, field.type) for field in table.schema]
    expected = list(SOURCE_SCHEMA)
    if actual != expected:
        raise ExposureDeliveryInputError(
            f"{label} source schema differs from {ANALYTICAL_CONTRACT}"
        )


def _validate_identity(identity: Mapping[str, Any]) -> None:
    if set(identity) != {"method", "input_sha256", "software", "run_id"}:
        raise ExposureDeliveryInputError("analytical identity fields differ")
    serialized_method = json.loads(json_text(method_contract()))
    if identity.get("method") != serialized_method:
        raise ExposureDeliveryInputError("analytical method contract differs")
    if identity.get("input_sha256") != EXPECTED_INPUT_SHA256:
        raise ExposureDeliveryInputError("analytical input provenance differs")
    software = identity.get("software")
    if not isinstance(software, dict) or set(software) != {
        "python",
        "pyarrow",
        "shapely",
        "pyproj",
    }:
        raise ExposureDeliveryInputError("analytical software identity differs")
    if not all(isinstance(value, str) and value for value in software.values()):
        raise ExposureDeliveryInputError("analytical software versions are malformed")
    run_id = identity.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
        raise ExposureDeliveryInputError("analytical run identity is malformed")
    basis = dict(identity)
    basis.pop("run_id")
    expected = "exposure-" + hashlib.sha256(json_text(basis).encode()).hexdigest()[:24]
    if run_id != expected:
        raise ExposureDeliveryInputError("analytical run identity does not verify")


def _threshold_rows(summary: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = summary.get("thresholds")
    if (
        not isinstance(rows, list)
        or len(rows) != 2 * len(PERCENTILES)
        or not all(isinstance(row, dict) for row in rows)
    ):
        raise ExposureDeliveryInputError("threshold family differs")
    expected = [
        (reference, percentile)
        for reference in ("all_valid", "positive_only")
        for percentile in PERCENTILES
    ]
    actual = [(row.get("reference"), row.get("percentile")) for row in rows]
    if actual != expected:
        raise ExposureDeliveryInputError("threshold ordering/reference differs")
    return cast(list[Mapping[str, Any]], rows)


def _validate_report(report: Mapping[str, Any], identity: Mapping[str, Any]) -> None:
    if set(report) != {"identity", "grids", "output_sha256"}:
        raise ExposureDeliveryInputError("sensitivity report fields differ")
    if report.get("identity") != identity:
        raise ExposureDeliveryInputError(
            "report and layer analytical identities differ"
        )
    outputs = report.get("output_sha256")
    if not isinstance(outputs, dict) or set(outputs) != {
        SOURCE_FILES["5km"],
        SOURCE_FILES["10km"],
    }:
        raise ExposureDeliveryInputError("report output inventory differs")
    grids = report.get("grids")
    if not isinstance(grids, dict) or set(grids) != {"5km", "10km"}:
        raise ExposureDeliveryInputError("report grid inventory differs")
    for grid_name, grid in grids.items():
        if not isinstance(grid, dict):
            raise ExposureDeliveryInputError(f"{grid_name} report is malformed")
        methods = grid.get("methods")
        if not isinstance(methods, dict) or tuple(sorted(methods)) != tuple(
            sorted(METHODS)
        ):
            raise ExposureDeliveryInputError(f"{grid_name} method inventory differs")
        for summary in methods.values():
            if not isinstance(summary, dict):
                raise ExposureDeliveryInputError("method summary is malformed")
            _threshold_rows(summary)


def _validate_report_statistics(
    report: Mapping[str, Any], tables: Mapping[str, pa.Table]
) -> None:
    """Recompute every report grid field from the verified serialized rows."""
    grids = cast(Mapping[str, Any], report["grids"])
    for grid_name in ("5km", "10km"):
        expected = analyze_grid(_reconstruct_verified_cells(tables[grid_name]))
        _compare_verified_value(
            grids[grid_name], expected, f"sensitivity report.grids.{grid_name}"
        )


def load_bundle(
    bundle: Path,
    *,
    expected_5km_sha256: str,
    expected_10km_sha256: str,
    expected_report_sha256: str,
) -> BundleInspection:
    """Load and independently verify an exact M6 analytical bundle.

    ``run-metadata.json`` is intentionally neither required nor read: it holds
    private paths, clocks, and upstream lineage hashes and must not influence a
    deterministic analytical or delivery identity.
    """
    expected = {
        "5km": expected_5km_sha256.lower(),
        "10km": expected_10km_sha256.lower(),
        "report": expected_report_sha256.lower(),
    }
    if not bundle.is_dir():
        raise ExposureDeliveryInputError(f"analytical bundle does not exist: {bundle}")
    for label, digest in expected.items():
        if not _SHA256_PATTERN.fullmatch(digest):
            raise ExposureDeliveryInputError(
                f"expected {label} checksum must be 64 lowercase hexadecimal characters"
            )
        path = bundle / SOURCE_FILES[label]
        if not path.is_file():
            raise ExposureDeliveryInputError(
                f"analytical source is absent: {path.name}"
            )
        actual = sha256_file(path)
        if actual != digest:
            raise ExposureDeliveryInputError(
                f"{label} checksum mismatch: expected {digest}, found {actual}"
            )

    report = _read_json(bundle / SOURCE_FILES["report"])
    tables: dict[str, pa.Table] = {}
    identities: list[Mapping[str, Any]] = []
    for label in ("5km", "10km"):
        try:
            table = pq.read_table(bundle / SOURCE_FILES[label], use_threads=False)
        except Exception as exc:  # pragma: no cover - third-party read boundary
            raise ExposureDeliveryInputError(
                f"could not read {label} analytical Parquet: {exc}"
            ) from exc
        _validate_source_schema(table, label)
        identities.append(_validate_geo_metadata(table, label))
        tables[label] = table
    if identities[0] != identities[1]:
        raise ExposureDeliveryInputError("5 km and 10 km identities differ")
    identity = identities[0]
    try:
        _validate_identity(identity)
        _validate_report(report, identity)
    except ExposureDeliveryInputError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ExposureDeliveryInputError(
            f"analytical identity or sensitivity report is malformed: {exc}"
        ) from exc

    output_sha256 = cast(Mapping[str, str], report["output_sha256"])
    for label in ("5km", "10km"):
        if output_sha256[SOURCE_FILES[label]] != expected[label]:
            raise ExposureDeliveryInputError(
                f"report records a different {label} artifact checksum"
            )
        try:
            verify_table(tables[label], report["grids"][label])
        except (ValueError, KeyError, TypeError) as exc:
            raise ExposureDeliveryInputError(
                f"{label} analytical read-back verification failed: {exc}"
            ) from exc
    try:
        _validate_report_statistics(report, tables)
    except ExposureDeliveryInputError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ExposureDeliveryInputError(
            f"sensitivity report statistics are malformed: {exc}"
        ) from exc

    return BundleInspection(
        tables=tables,
        report=report,
        source_sha256={
            "exposure_5km": expected["5km"],
            "exposure_10km": expected["10km"],
            "sensitivity_report": expected["report"],
        },
        identity=identity,
    )


def _polygon_rings(geometry: BaseGeometry) -> list[list[list[float]]]:
    polygon = cast(Polygon, geometry)
    return [
        [[float(x), float(y)] for x, y in ring.coords]
        for ring in (polygon.exterior, *polygon.interiors)
    ]


def _geometry_mapping(geometry: BaseGeometry) -> dict[str, object]:
    if geometry.geom_type == "Polygon":
        return {"type": "Polygon", "coordinates": _polygon_rings(geometry)}
    return {
        "type": "MultiPolygon",
        "coordinates": [
            _polygon_rings(part) for part in shapely.get_parts(geometry).tolist()
        ],
    }


def _decode_qualified_geometry(row: Mapping[str, Any]) -> BaseGeometry:
    if row["analysis_status"] != "qualified" or row["qualified_area_km2"] <= 0:
        raise ExposureDeliveryInputError("display row is not receiver-domain qualified")
    try:
        geometry = shapely.from_wkb(row["geometry"])
    except (GEOSException, TypeError, ValueError) as exc:
        raise ExposureDeliveryInputError("qualified geometry is not valid WKB") from exc
    if (
        geometry is None
        or geometry.is_empty
        or not geometry.is_valid
        or geometry.geom_type not in {"Polygon", "MultiPolygon"}
    ):
        raise ExposureDeliveryInputError("qualified geometry is empty or invalid")
    if not math.isclose(
        float(geometry.area) / 1e6,
        float(row["qualified_area_km2"]),
        rel_tol=1e-10,
        abs_tol=1e-12,
    ):
        raise ExposureDeliveryInputError(
            "qualified geometry area differs from its field"
        )
    return cast(BaseGeometry, geometry)


def build_display_export(inspection: BundleInspection) -> DisplayExport:
    """Transform exact qualified 5 km water to WGS 84 without altering values."""
    rows = cast(list[dict[str, Any]], inspection.tables["5km"].to_pylist())
    qualified = [row for row in rows if row["analysis_status"] == "qualified"]
    expected_count = inspection.report["grids"]["5km"]["qualified_cell_count"]
    if not qualified or len(qualified) != expected_count:
        raise ExposureDeliveryInputError("qualified display population differs")

    to_display = Transformer.from_crs(SOURCE_CRS, DISPLAY_CRS, always_xy=True)
    to_source = Transformer.from_crs(DISPLAY_CRS, SOURCE_CRS, always_xy=True)

    def transform_positions(
        coordinates: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        longitude, latitude = to_display.transform(coordinates[:, 0], coordinates[:, 1])
        return cast("NDArray[np.float64]", np.column_stack([longitude, latitude]))

    features: list[dict[str, object]] = []
    parts = rings = coordinates = 0
    geometry_types: set[str] = set()
    min_lon = min_lat = math.inf
    max_lon = max_lat = -math.inf
    max_roundtrip = 0.0
    for object_id, row in enumerate(qualified, start=1):
        source = _decode_qualified_geometry(row)
        transformed = shapely.transform(source, transform_positions)
        displayed = shapely.orient_polygons(transformed)
        if (
            displayed.is_empty
            or not displayed.is_valid
            or displayed.geom_type != source.geom_type
        ):
            raise ExposureDeliveryOutputError(
                f"transformed geometry is invalid for {row['cell_id']}"
            )
        source_coordinates = shapely.get_coordinates(source)
        transformed_coordinates = shapely.get_coordinates(transformed)
        displayed_coordinates = shapely.get_coordinates(displayed)
        if source_coordinates.shape != displayed_coordinates.shape:
            raise ExposureDeliveryOutputError("display transformation changed vertices")
        back_x, back_y = to_source.transform(
            transformed_coordinates[:, 0], transformed_coordinates[:, 1]
        )
        roundtrip = float(
            np.hypot(
                back_x - source_coordinates[:, 0],
                back_y - source_coordinates[:, 1],
            ).max()
        )
        max_roundtrip = max(max_roundtrip, roundtrip)
        longitudes = displayed_coordinates[:, 0]
        latitudes = displayed_coordinates[:, 1]
        if (
            longitudes.min() < -180
            or longitudes.max() > 180
            or latitudes.min() < -90
            or latitudes.max() > 90
        ):
            raise ExposureDeliveryOutputError(
                "display coordinates fall outside longitude/latitude bounds"
            )
        min_lon = min(min_lon, float(longitudes.min()))
        max_lon = max(max_lon, float(longitudes.max()))
        min_lat = min(min_lat, float(latitudes.min()))
        max_lat = max(max_lat, float(latitudes.max()))
        displayed_parts = shapely.get_parts(displayed)
        source_parts = shapely.get_parts(source)
        if len(displayed_parts) != len(source_parts):
            raise ExposureDeliveryOutputError("display transformation changed parts")
        displayed_rings = int(sum(shapely.get_num_interior_rings(displayed_parts)))
        source_rings = int(sum(shapely.get_num_interior_rings(source_parts)))
        if displayed_rings != source_rings:
            raise ExposureDeliveryOutputError("display transformation changed holes")
        parts += len(displayed_parts)
        rings += displayed_rings
        coordinates += int(displayed_coordinates.shape[0])
        geometry_types.add(displayed.geom_type)
        properties = {
            "object_id": object_id,
            "cell_id": row["cell_id"],
            "water_area_km2": row["water_area_km2"],
            "qualified_area_km2": row["qualified_area_km2"],
            "product_intensity": row["product_intensity"],
            "product_index": row["product_index"],
            "product_high_p90": row["product_high_p90"],
            "log_traffic_intensity": row["log_traffic_intensity"],
            "log_traffic_index": row["log_traffic_index"],
            "log_traffic_high_p90": row["log_traffic_high_p90"],
        }
        features.append(
            {
                "type": "Feature",
                "id": row["cell_id"],
                "geometry": _geometry_mapping(displayed),
                "properties": properties,
            }
        )

    extent = load_default_config().spatial.map_extent
    tolerance = MAP_EXTENT_DISPLAY_TOLERANCE_DEGREES
    if not (
        extent.lon_min - tolerance <= min_lon
        and max_lon <= extent.lon_max + tolerance
        and extent.lat_min - tolerance <= min_lat
        and max_lat <= extent.lat_max + tolerance
    ):
        raise ExposureDeliveryOutputError(
            "display geometry falls outside the accepted map/context extent"
        )
    collection: dict[str, object] = {
        "type": "FeatureCollection",
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "features": features,
    }
    indices = [
        float(row[field])
        for row in qualified
        for field in ("product_index", "log_traffic_index")
        if row[field] is not None
    ]
    diagnostics: dict[str, object] = {
        "feature_count": len(features),
        "unique_cell_count": len({row["cell_id"] for row in qualified}),
        "polygon_part_count": parts,
        "interior_ring_count": rings,
        "coordinate_count": coordinates,
        "geometry_types": sorted(geometry_types),
        "bounds_lon_lat": [min_lon, min_lat, max_lon, max_lat],
        "max_vertex_roundtrip_metres": max_roundtrip,
        "transformation_definition": to_display.definition,
        "transformation_accuracy_metres": to_display.accuracy,
        "configured_map_extent_lon_lat": [
            extent.lon_min,
            extent.lat_min,
            extent.lon_max,
            extent.lat_max,
        ],
        "map_extent_display_tolerance_degrees": (MAP_EXTENT_DISPLAY_TOLERANCE_DEGREES),
        "qualified_area_km2_total": math.fsum(
            row["qualified_area_km2"] for row in qualified
        ),
        "non_null_index_min": min(indices) if indices else None,
        "non_null_index_max": max(indices) if indices else None,
    }
    return DisplayExport(canonical_json_bytes(collection), diagnostics)


def _decimal_text(value: float, places: int) -> str:
    quantum = Decimal(1).scaleb(-places)
    rounded = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
    if rounded == 0:
        rounded = abs(rounded)
    return f"{rounded:.{places}f}"


def _percent_text(value: float | None, places: int = 1) -> str | None:
    if value is None:
        return None
    return _decimal_text(value * 100, places) + "%"


def _area_text(value: float | None) -> str | None:
    return None if value is None else _decimal_text(value, 1) + " km^2"


def _threshold_text(value: float | None) -> str | None:
    return None if value is None else _decimal_text(value, 4)


def _share_delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _relative_change(left: float, right: float) -> float | None:
    return None if right == 0 else (left - right) / right


def _require_fields(value: object, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ExposureDeliveryInputError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise ExposureDeliveryInputError(
            f"{label} fields differ; missing={sorted(expected - actual)}, "
            f"unexpected={sorted(actual - expected)}"
        )
    return cast(Mapping[str, Any], value)


def _public_normalization_control(
    value: object, label: str
) -> PublicNormalizationControl:
    control = _require_fields(
        value,
        (
            {
                "available",
                "normalizer",
                "inside_share_difference",
                "all_threshold_memberships_equal",
            }
            if isinstance(value, dict) and value.get("available") is True
            else {"available", "reason"}
        ),
        label,
    )
    available = control["available"]
    if available is True:
        normalizer = control["normalizer"]
        difference = control["inside_share_difference"]
        memberships_equal = control["all_threshold_memberships_equal"]
        if (
            isinstance(normalizer, bool)
            or not isinstance(normalizer, (int, float))
            or not math.isfinite(float(normalizer))
            or float(normalizer) <= 0
            or isinstance(difference, bool)
            or not isinstance(difference, (int, float))
            or not math.isfinite(float(difference))
            or abs(float(difference)) > 1e-12
            or memberships_equal is not True
        ):
            raise ExposureDeliveryInputError(f"{label} values are malformed")
        return AvailableNormalizationControl(
            available=True,
            normalizer=float(normalizer),
            inside_share_difference=float(difference),
            all_threshold_memberships_equal=True,
        )
    if available is False and control["reason"] == "zero normalizer":
        return UnavailableNormalizationControl(
            available=False, reason="zero normalizer"
        )
    raise ExposureDeliveryInputError(f"{label} availability/reason enumeration differs")


def _public_normalization_controls(
    value: object, label: str
) -> PublicNormalizationControls:
    controls = _require_fields(value, {"product_max", "separate_input_maxima"}, label)
    return PublicNormalizationControls(
        product_max=_public_normalization_control(
            controls["product_max"], f"{label}.product_max"
        ),
        separate_input_maxima=_public_normalization_control(
            controls["separate_input_maxima"], f"{label}.separate_input_maxima"
        ),
    )


def _public_sha256_map(
    value: object, keys: tuple[str, ...], label: str
) -> dict[str, str]:
    source = _require_fields(value, set(keys), label)
    result: dict[str, str] = {}
    for key in keys:
        digest = source[key]
        if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
            raise ExposureDeliveryInputError(f"{label}.{key} is not a SHA-256")
        result[key] = digest
    return result


def _public_domain_limitations(value: object) -> dict[str, str]:
    keys = (
        "receiver_uptime_2024",
        "station_completeness",
        "feed_interruptions",
        "antenna_and_terrain_effects",
        "observational_completeness",
    )
    limitations = _require_fields(value, set(keys), "analytical domain limitations")
    result: dict[str, str] = {}
    for key in keys:
        text = limitations[key]
        if not isinstance(text, str) or not text:
            raise ExposureDeliveryInputError(
                f"analytical domain limitation {key} must be nonempty text"
            )
        result[key] = text
    return result


def _public_length_filter(value: object) -> dict[str, object]:
    length_filter = _require_fields(
        value, {"minimum_length_m", "reason", "status"}, "vessel length filter"
    )
    if length_filter["minimum_length_m"] is not None:
        raise ExposureDeliveryInputError("vessel length-filter minimum must be null")
    if (
        length_filter["status"] != "type-only-no-length-filter"
        or not isinstance(length_filter["reason"], str)
        or not length_filter["reason"]
    ):
        raise ExposureDeliveryInputError(
            "vessel length-filter text/enumeration differs"
        )
    return {
        "minimum_length_m": None,
        "reason": length_filter["reason"],
        "status": "type-only-no-length-filter",
    }


def _public_source_references() -> dict[str, dict[str, object]]:
    """Project the authored source register text through fixed field lists."""
    return {
        "whales": {
            "publisher": SOURCE_REFERENCES["whales"]["publisher"],
            "product": SOURCE_REFERENCES["whales"]["product"],
            "layer": SOURCE_REFERENCES["whales"]["layer"],
            "survey_basis": SOURCE_REFERENCES["whales"]["survey_basis"],
            "metadata": SOURCE_REFERENCES["whales"]["metadata"],
        },
        "traffic": {
            "publisher": SOURCE_REFERENCES["traffic"]["publisher"],
            "source": SOURCE_REFERENCES["traffic"]["source"],
            "period": SOURCE_REFERENCES["traffic"]["period"],
            "population": SOURCE_REFERENCES["traffic"]["population"],
            "terms": SOURCE_REFERENCES["traffic"]["terms"],
        },
        "vsr": {
            "publisher": SOURCE_REFERENCES["vsr"]["publisher"],
            "feature": SOURCE_REFERENCES["vsr"]["feature"],
            "boundary_year": SOURCE_REFERENCES["vsr"]["boundary_year"],
            "snapshot_retrieved": SOURCE_REFERENCES["vsr"]["snapshot_retrieved"],
            "public_service": SOURCE_REFERENCES["vsr"]["public_service"],
            "display_rule": SOURCE_REFERENCES["vsr"]["display_rule"],
        },
    }


def _public_number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ExposureDeliveryOutputError(f"{label} must be a finite number")
    return float(value)


def _public_nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExposureDeliveryOutputError(f"{label} must be a nonnegative integer")
    return value


def _public_number_list(value: object, size: int, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != size:
        raise ExposureDeliveryOutputError(f"{label} shape differs")
    return [
        _public_number(item, f"{label}[{index}]") for index, item in enumerate(value)
    ]


def _public_optional_number(value: object, label: str) -> float | None:
    return None if value is None else _public_number(value, label)


def _public_display_diagnostics(value: object) -> PublicDisplayDiagnostics:
    keys = {
        "feature_count",
        "unique_cell_count",
        "polygon_part_count",
        "interior_ring_count",
        "coordinate_count",
        "geometry_types",
        "bounds_lon_lat",
        "max_vertex_roundtrip_metres",
        "transformation_definition",
        "transformation_accuracy_metres",
        "configured_map_extent_lon_lat",
        "map_extent_display_tolerance_degrees",
        "qualified_area_km2_total",
        "non_null_index_min",
        "non_null_index_max",
    }
    try:
        diagnostics = _require_fields(value, keys, "display diagnostics")
    except ExposureDeliveryInputError as exc:
        raise ExposureDeliveryOutputError(str(exc)) from exc
    geometry_types = diagnostics["geometry_types"]
    if (
        not isinstance(geometry_types, list)
        or not geometry_types
        or any(item not in {"Polygon", "MultiPolygon"} for item in geometry_types)
        or geometry_types != sorted(set(geometry_types))
    ):
        raise ExposureDeliveryOutputError("display diagnostics geometry types differ")
    definition = diagnostics["transformation_definition"]
    if not isinstance(definition, str) or not definition:
        raise ExposureDeliveryOutputError(
            "display transformation definition must be nonempty text"
        )
    return PublicDisplayDiagnostics(
        feature_count=_public_nonnegative_int(
            diagnostics["feature_count"], "display feature count"
        ),
        unique_cell_count=_public_nonnegative_int(
            diagnostics["unique_cell_count"], "display unique cell count"
        ),
        polygon_part_count=_public_nonnegative_int(
            diagnostics["polygon_part_count"], "display polygon part count"
        ),
        interior_ring_count=_public_nonnegative_int(
            diagnostics["interior_ring_count"], "display interior ring count"
        ),
        coordinate_count=_public_nonnegative_int(
            diagnostics["coordinate_count"], "display coordinate count"
        ),
        geometry_types=list(geometry_types),
        bounds_lon_lat=_public_number_list(
            diagnostics["bounds_lon_lat"], 4, "display bounds"
        ),
        max_vertex_roundtrip_metres=_public_number(
            diagnostics["max_vertex_roundtrip_metres"],
            "display maximum vertex roundtrip",
        ),
        transformation_definition=definition,
        transformation_accuracy_metres=_public_number(
            diagnostics["transformation_accuracy_metres"],
            "display transformation accuracy",
        ),
        configured_map_extent_lon_lat=_public_number_list(
            diagnostics["configured_map_extent_lon_lat"],
            4,
            "configured map extent",
        ),
        map_extent_display_tolerance_degrees=_public_number(
            diagnostics["map_extent_display_tolerance_degrees"],
            "map extent display tolerance",
        ),
        qualified_area_km2_total=_public_number(
            diagnostics["qualified_area_km2_total"],
            "display qualified area total",
        ),
        non_null_index_min=_public_optional_number(
            diagnostics["non_null_index_min"], "display non-null index minimum"
        ),
        non_null_index_max=_public_optional_number(
            diagnostics["non_null_index_max"], "display non-null index maximum"
        ),
    )


def _high_result(row: Mapping[str, Any], units: str) -> dict[str, object]:
    return {
        "percentile": row["percentile"],
        "threshold": row["threshold"],
        "threshold_units": units,
        "available": row["available"],
        "unavailable_reason": row["unavailable_reason"],
        "selected_water_area_km2": row["high_area_km2"],
        "inside_water_area_km2": row["high_inside_km2"],
        "outside_water_area_km2": row["high_outside_km2"],
        "inside_share_of_selected_water": row["share_high_area_inside"],
        "outside_share_of_selected_water": row["share_high_area_outside"],
        "selected_share_of_qualified_domain_water": row["share_domain_area_high"],
        "threshold_tied_water_area_km2": row["threshold_tied_area_km2"],
        "presentation": {
            "threshold_4dp": _threshold_text(row["threshold"]),
            "selected_water_area_1dp": _area_text(row["high_area_km2"]),
            "inside_share_percent_1dp": _percent_text(row["share_high_area_inside"]),
            "outside_share_percent_1dp": _percent_text(row["share_high_area_outside"]),
        },
    }


def _scenario(
    inspection: BundleInspection, grid_name: str, method: str
) -> dict[str, object]:
    grid = inspection.report["grids"][grid_name]
    summary = grid["methods"][method]
    method_definition = inspection.identity["method"]
    intensity_units = method_definition[f"{method}_intensity_units"]
    integrated_units = method_definition[f"{method}_integrated_units"]
    thresholds = _threshold_rows(summary)
    references = {
        reference: [
            _high_result(row, intensity_units)
            for row in thresholds
            if row["reference"] == reference
        ]
        for reference in ("all_valid", "positive_only")
    }
    result: dict[str, object] = {
        "grid_resolution_m": 5000 if grid_name == "5km" else 10000,
        "method": method,
        "role": "primary" if method == "product" else "sensitivity",
        "intensity_units": intensity_units,
        "integrated_units": integrated_units,
        "water_cell_count": grid["water_cell_count"],
        "qualified_cell_count": grid["qualified_cell_count"],
        "excluded_cell_count": grid["excluded_cell_count"],
        "zero_product_qualified_cell_count": grid["zero_product_qualified_cells"],
        "qualified_water_area_km2": summary["qualified_area_km2"],
        "integrated_exposure": {
            "total_qualified": summary["integrated_qualified"],
            "inside_vsr": summary["integrated_inside"],
            "outside_vsr": summary["integrated_outside"],
            "inside_share": summary["share_exposure_inside"],
            "outside_share": summary["share_exposure_outside"],
            "share_denominator": (
                "integrated inside plus integrated outside exposure over exact "
                "receiver-qualified water"
            ),
            "presentation": {
                "inside_share_percent_1dp": _percent_text(
                    summary["share_exposure_inside"]
                ),
                "outside_share_percent_1dp": _percent_text(
                    summary["share_exposure_outside"]
                ),
            },
        },
        "normalization": {
            "maximum_intensity": summary["normalization_maximum"],
            "reference_population": "positive-qualified-area cells",
            "null_when_maximum_zero": True,
        },
        "high_exposure": {
            "definition": (
                "smallest observed intensity reaching the stated cumulative "
                "qualified-water-area percentile; select intensity >= threshold "
                "and include all ties"
            ),
            "area_share_denominator": (
                "selected high-exposure qualified water area, partitioned by "
                "exact inside/outside VSR water area"
            ),
            "all_valid": references["all_valid"],
            "positive_only_sensitivity": references["positive_only"],
        },
    }
    if grid_name == "5km":
        result["outside_concentrations"] = {
            "definition": inspection.identity["method"]["outside_concentrations"],
            "top_ten_share_of_outside_exposure": summary["top_ten_share_outside"],
            "cells": [
                {
                    "cell_id": row["cell_id"],
                    "outside_integrated": row["outside_integrated"],
                    "share_of_outside_total": row["share_outside_total"],
                }
                for row in summary["top_outside_cells"]
            ],
        }
    return result


def _threshold_lookup(
    inspection: BundleInspection, grid: str, method: str, percentile: float
) -> Mapping[str, Any]:
    rows = _threshold_rows(inspection.report["grids"][grid]["methods"][method])
    return next(
        row
        for row in rows
        if row["reference"] == "all_valid" and row["percentile"] == percentile
    )


def _comparisons(inspection: BundleInspection) -> dict[str, object]:
    grids = inspection.report["grids"]
    fine_product = grids["5km"]["methods"]["product"]
    fine_log = grids["5km"]["methods"]["log_traffic"]
    formula_delta = _share_delta(
        fine_log["share_exposure_inside"], fine_product["share_exposure_inside"]
    )
    resolution: dict[str, object] = {}
    for method in METHODS:
        fine = grids["5km"]["methods"][method]
        coarse = grids["10km"]["methods"][method]
        inside_delta = _share_delta(
            coarse["share_exposure_inside"], fine["share_exposure_inside"]
        )
        high_deltas = []
        for percentile in PERCENTILES:
            left = _threshold_lookup(inspection, "10km", method, percentile)
            right = _threshold_lookup(inspection, "5km", method, percentile)
            delta = _share_delta(
                left["share_high_area_inside"], right["share_high_area_inside"]
            )
            high_deltas.append(
                {
                    "percentile": percentile,
                    "inside_high_area_share_change": delta,
                    "presentation_change_percentage_points_4dp": None
                    if delta is None
                    else _decimal_text(delta * 100, 4),
                }
            )
        total_change = _relative_change(
            coarse["integrated_qualified"], fine["integrated_qualified"]
        )
        resolution[method] = {
            "from_resolution_m": 5000,
            "to_resolution_m": 10000,
            "integrated_total_relative_change": total_change,
            "presentation_integrated_total_percent_change_6dp": None
            if total_change is None
            else _decimal_text(total_change * 100, 6),
            "inside_share_change": inside_delta,
            "presentation_inside_change_percentage_points_4dp": None
            if inside_delta is None
            else _decimal_text(inside_delta * 100, 4),
            "high_area_inside_share_changes": high_deltas,
        }
    return {
        "formula_sensitivity_at_5km": {
            "comparison": "log_traffic minus primary product",
            "inside_share_change": formula_delta,
            "presentation_change_percentage_points_4dp": None
            if formula_delta is None
            else _decimal_text(formula_delta * 100, 4),
            "spearman_cell_ranks": grids["5km"]["product_vs_log"][
                "spearman_cell_ranks"
            ],
            "maximum_absolute_rank_change": grids["5km"]["product_vs_log"][
                "maximum_absolute_rank_change"
            ],
        },
        "grid_resolution_sensitivity": resolution,
        "global_scaling_controls": {
            grid: _public_normalization_controls(
                grids[grid]["normalization_controls"],
                f"sensitivity report.grids.{grid}.normalization_controls",
            )
            for grid in ("5km", "10km")
        },
    }


def _build_results_base(inspection: BundleInspection) -> dict[str, object]:
    """Project verified inputs into an explicitly allowlisted public result."""
    method = inspection.identity["method"]
    domain = method["reporting_domain"]["analytical_domain"]
    vessel_method = selected_method()
    base: dict[str, object] = {
        "contract": RESULTS_CONTRACT,
        "schema_version": RESULTS_SCHEMA_VERSION,
        "producer": {
            "module": "whale_vessel_analysis.exposure_delivery",
            "delivery_version": DELIVERY_VERSION,
        },
        "analysis": {
            "contract": ANALYTICAL_CONTRACT,
            "method_version": method["method_version"],
            "decision": method["decision"],
            "run_id": inspection.identity["run_id"],
            "source_artifact_sha256": _public_sha256_map(
                inspection.source_sha256,
                ("exposure_5km", "exposure_10km", "sensitivity_report"),
                "analytical source artifacts",
            ),
            "analytical_input_sha256": _public_sha256_map(
                inspection.identity["input_sha256"],
                ("water", "whale", "vessel", "vessel_quality", "domain", "vsr"),
                "analytical input provenance",
            ),
            "execution_lineage": "excluded from this public contract and identity",
        },
        "scope": {
            "traffic_period_start_utc": method["period_start_utc"],
            "traffic_period_end_exclusive_utc": method["period_end_exclusive_utc"],
            "whale_vintage": method["whale_vintage"],
            "vsr_boundary_year": SOURCE_REFERENCES["vsr"]["boundary_year"],
            "vsr_snapshot_retrieved": method["vsr_snapshot_retrieved"],
            "vsr_fid": method["vsr_fid"],
            "analytical_domain": {
                "id": domain["id"],
                "qualification": domain["qualification"],
                "geometry_basis": domain["geometry_basis"],
                "measured_from": domain["measured_from"],
                "distance_m": domain["distance_m"],
                "distance_nautical_miles": domain["distance_nautical_miles"],
                "empirical_2024_coverage": domain["empirical_2024_coverage"],
                "boundary_cell_treatment": domain["boundary_cell_treatment"],
                "outside_cell_treatment": domain["outside_cell_treatment"],
                "limitations": _public_domain_limitations(domain["limitations"]),
            },
            "vessel_parameters": {
                "commercial_type_codes": ["60-69", "70-79", "80-89"],
                "maximum_gap_seconds": vessel_method["maximum_gap_seconds"],
                "maximum_implied_speed_knots": vessel_method[
                    "implied_speed_ceiling_knots"
                ],
                "length_filter": _public_length_filter(
                    vessel_method["vessel_length_filter"]
                ),
                "edge_treatment": vessel_method["edge_treatment"],
                "water_support_treatment": vessel_method["support_treatment"],
                "threshold_status": vessel_method["threshold_status"],
                "speed_weight": method["speed_weight"],
            },
        },
        "methods": {
            "primary": {
                "id": "product",
                "formula": method["product"],
                "intensity_area_basis": "full cell water area",
                "integration_area_basis": (
                    "exact qualified water and its inside/outside VSR partition"
                ),
                "assumption": method["assumption"],
            },
            "sensitivity": {
                "id": "log_traffic",
                "formula": method["log_traffic"],
                "purpose": "compress high traffic values; changes the question",
                "scientific_status": "sensitivity alternative, not preferred evidence",
            },
            "normalization": method["normalization"],
            "speed_separation": "speed is descriptive and not an exposure weight",
        },
        "scenarios": {
            f"{grid}_{method_name}": _scenario(inspection, grid, method_name)
            for grid in ("5km", "10km")
            for method_name in METHODS
        },
        "comparisons": _comparisons(inspection),
        "nulls_and_exclusions": {
            "outside_domain": method["outside_domain"],
            "zero_movement": method["zero_movement"],
            "missing_speed": "does not make exposure missing",
            "all_zero": (
                "integrated totals are zero; exposure shares, normalized indices, "
                "and discriminating high-exposure statistics are null"
            ),
            "empty_qualified_domain": "invalid input; no result is produced",
            "observational_completeness": method["observational_completeness"],
            "publisher_transfer_completeness": method[
                "publisher_transfer_completeness"
            ],
        },
        "source_references": _public_source_references(),
        "limitations": [
            "The inputs mix a multi-year modeled summer-fall whale surface, "
            "July-November 2024 traffic, and the 2026 VSR boundary; they do not "
            "represent contemporaneous whale-vessel encounters.",
            "Receiver qualification is a system-performance domain, not empirical "
            "2024 coverage; receiver uptime, station completeness, feed losses, "
            "antenna and terrain effects, and observational completeness remain "
            "unknown or unverified.",
            "Native whale-model uncertainty is not propagated, and the 5 km grid "
            "does not add biological resolution to the roughly 0.1-degree model.",
            "Inside-zone overlap does not establish avoided collisions, protection "
            "effectiveness, program compliance, causation, or a policy recommendation.",
        ],
        "presentation_rules": {
            "shares": "percent with 1 decimal place, round half up",
            "areas": "km^2 with 1 decimal place, round half up",
            "thresholds": "4 decimal places, round half up; retain exact value",
            "sensitivity_share_changes": (
                "percentage points with 4 decimal places, round half up"
            ),
            "integrated_total_changes": (
                "percent with 6 decimal places, round half up"
            ),
            "exact_values": "unrounded numeric fields remain authoritative",
        },
    }
    return base


def build_results_export(
    inspection: BundleInspection, *, generated_at: datetime
) -> ResultsExport:
    """Build the small M7-ready results contract entirely from verified M6 data."""
    base = _build_results_base(inspection)
    results_id = (
        "exposure-results-"
        + hashlib.sha256(canonical_json_bytes(base)).hexdigest()[:24]
    )
    document = {
        **base,
        "results_id": results_id,
        "generated_at_utc": _utc_text(generated_at),
    }
    payload = canonical_json_bytes(document)
    result = ResultsExport(payload, document)
    verify_results_document(json.loads(payload), inspection)
    return result


def build_display_manifest(
    inspection: BundleInspection,
    display: DisplayExport,
    results: ResultsExport,
    *,
    output_name: str,
    generated_at: datetime,
) -> bytes:
    """Build a sanitized public manifest binding display bytes to M6 and results."""
    method = inspection.identity["method"]
    public_diagnostics = _public_display_diagnostics(display.diagnostics)
    classifications: dict[str, object] = {}
    for method_name in METHODS:
        threshold = _threshold_lookup(inspection, "5km", method_name, 0.9)
        classifications[method_name] = {
            "field": f"{method_name}_high_p90",
            "threshold": threshold["threshold"],
            "threshold_units": method[f"{method_name}_intensity_units"],
            "reference": "all_valid",
            "percentile": 0.9,
            "available": threshold["available"],
            "definition": method["quantile"],
        }
    manifest: dict[str, object] = {
        "contract": DISPLAY_MANIFEST_CONTRACT,
        "dataset_contract": DISPLAY_CONTRACT,
        "processing_version": DELIVERY_VERSION,
        "generated_at_utc": _utc_text(generated_at),
        "source": {
            "analytical_contract": ANALYTICAL_CONTRACT,
            "method_version": method["method_version"],
            "analysis_run_id": inspection.identity["run_id"],
            "artifact_sha256": _public_sha256_map(
                inspection.source_sha256,
                ("exposure_5km", "exposure_10km", "sensitivity_report"),
                "analytical source artifacts",
            ),
            "analytical_input_sha256": _public_sha256_map(
                inspection.identity["input_sha256"],
                ("water", "whale", "vessel", "vessel_quality", "domain", "vsr"),
                "analytical input provenance",
            ),
            "execution_lineage": "excluded; no private run metadata was read",
        },
        "results": {
            "contract": RESULTS_CONTRACT,
            "results_id": results.document["results_id"],
            "sha256": results.sha256,
        },
        "geometry": {
            "meaning": "exact receiver-domain-qualified 5 km water geometry",
            "source_crs": SOURCE_CRS,
            "display_crs": DISPLAY_CRS,
            "always_xy": True,
            "ring_orientation": (
                "RFC 7946: exterior counterclockwise, interior clockwise"
            ),
            "simplification": "not_performed",
            "coordinate_rounding": "not_performed",
            "densification": "not_performed",
            "vsr_geometry": "not_included",
        },
        "fields": [
            {"name": name, "unit": unit, "meaning": meaning}
            for name, unit, meaning in DISPLAY_FIELDS
        ],
        "classification": classifications,
        "display_statements": list(DISPLAY_STATEMENTS),
        "source_references": _public_source_references(),
        "output": {
            "name": output_name,
            "format": "GeoJSON (RFC 7946)",
            "media_type": "application/geo+json",
            "bytes": len(display.geojson),
            "sha256": display.sha256,
            **public_diagnostics,
        },
    }
    payload = canonical_json_bytes(manifest)
    verify_display_manifest(json.loads(payload), inspection, display, results)
    return payload


def build_delivery_export(
    inspection: BundleInspection,
    *,
    display_name: str,
    generated_at: datetime,
) -> DeliveryExport:
    """Prepare and serialize every public artifact before any write begins."""
    results = build_results_export(inspection, generated_at=generated_at)
    display = build_display_export(inspection)
    verify_display_document(json.loads(display.geojson), inspection)
    manifest = build_display_manifest(
        inspection,
        display,
        results,
        output_name=display_name,
        generated_at=generated_at,
    )
    return DeliveryExport(display, manifest, results)


def verify_display_document(
    document: Mapping[str, Any], inspection: BundleInspection
) -> None:
    """Compare every serialized public display value with the analytical table."""
    features = document.get("features")
    if document.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise ExposureDeliveryOutputError(
            "serialized display is not a FeatureCollection"
        )
    source_rows = [
        row
        for row in inspection.tables["5km"].to_pylist()
        if row["analysis_status"] == "qualified"
    ]
    if len(features) != len(source_rows):
        raise ExposureDeliveryOutputError("serialized display feature count differs")
    fields = [name for name, _unit, _meaning in DISPLAY_FIELDS]
    for object_id, (feature, row) in enumerate(
        zip(features, source_rows, strict=True), start=1
    ):
        if not isinstance(feature, dict) or feature.get("id") != row["cell_id"]:
            raise ExposureDeliveryOutputError("serialized display identity differs")
        properties = feature.get("properties")
        if not isinstance(properties, dict) or set(properties) != set(fields):
            raise ExposureDeliveryOutputError("serialized display fields differ")
        expected = {
            "object_id": object_id,
            "cell_id": row["cell_id"],
            "water_area_km2": row["water_area_km2"],
            "qualified_area_km2": row["qualified_area_km2"],
            "product_intensity": row["product_intensity"],
            "product_index": row["product_index"],
            "product_high_p90": row["product_high_p90"],
            "log_traffic_intensity": row["log_traffic_intensity"],
            "log_traffic_index": row["log_traffic_index"],
            "log_traffic_high_p90": row["log_traffic_high_p90"],
        }
        if properties != expected:
            raise ExposureDeliveryOutputError(
                f"serialized display values differ for {row['cell_id']}"
            )


def verify_results_document(
    document: Mapping[str, Any], inspection: BundleInspection
) -> None:
    """Compare every public result field with report values and contract rules."""
    if document.get("contract") != RESULTS_CONTRACT:
        raise ExposureDeliveryOutputError("serialized results contract differs")
    expected_basis = _build_results_base(inspection)
    expected_fields = {*expected_basis, "results_id", "generated_at_utc"}
    if set(document) != expected_fields:
        raise ExposureDeliveryOutputError("serialized results fields differ")
    generated_at = document["generated_at_utc"]
    if not isinstance(generated_at, str):
        raise ExposureDeliveryOutputError("serialized generation time is malformed")
    try:
        if _utc_text(parse_utc_timestamp(generated_at)) != generated_at:
            raise ExposureDeliveryOutputError(
                "serialized generation time is not canonical UTC"
            )
    except ExposureDeliveryOutputError:
        raise
    basis = {key: document[key] for key in expected_basis}
    results_id = document["results_id"]
    expected_id = (
        "exposure-results-"
        + hashlib.sha256(canonical_json_bytes(basis)).hexdigest()[:24]
    )
    if results_id != expected_id:
        raise ExposureDeliveryOutputError("serialized results identity differs")
    if basis != expected_basis:
        raise ExposureDeliveryOutputError(
            "serialized results differ from the typed verified projection"
        )


def verify_display_manifest(
    manifest: Mapping[str, Any],
    inspection: BundleInspection,
    display: DisplayExport,
    results: ResultsExport,
) -> None:
    """Verify manifest numerical bindings without consulting private lineage."""
    if (
        manifest.get("contract") != DISPLAY_MANIFEST_CONTRACT
        or manifest.get("dataset_contract") != DISPLAY_CONTRACT
    ):
        raise ExposureDeliveryOutputError("display manifest contract differs")
    if manifest["source"]["analysis_run_id"] != inspection.identity["run_id"]:
        raise ExposureDeliveryOutputError("display manifest run identity differs")
    if manifest["results"]["sha256"] != results.sha256:
        raise ExposureDeliveryOutputError("display/results binding differs")
    output = manifest["output"]
    if output["sha256"] != display.sha256 or output["bytes"] != len(display.geojson):
        raise ExposureDeliveryOutputError("display manifest output identity differs")
    for key, value in _public_display_diagnostics(display.diagnostics).items():
        if output[key] != value:
            raise ExposureDeliveryOutputError("display manifest diagnostics differ")
    for method in METHODS:
        threshold = _threshold_lookup(inspection, "5km", method, 0.9)
        if manifest["classification"][method]["threshold"] != threshold["threshold"]:
            raise ExposureDeliveryOutputError("display threshold binding differs")


def _reject_protected_location(path: Path) -> None:
    parts = path.resolve().parts
    if ".git" in parts:
        raise ExposureDeliveryOutputError(
            f"delivery output cannot be written under Git metadata: {path}"
        )
    for index in range(1, len(parts)):
        if parts[index] == "raw" and parts[index - 1] == "data":
            raise ExposureDeliveryOutputError(
                f"delivery output cannot be written under raw data: {path}"
            )


def _validate_output_path(
    path: Path,
    *,
    suffix: str,
    roots: Sequence[Path],
) -> None:
    if path.suffix.lower() != suffix:
        raise ExposureDeliveryOutputError(f"output path must end in {suffix}")
    resolved = path.resolve()
    _reject_protected_location(resolved)
    if not any(resolved.is_relative_to(root.resolve()) for root in roots):
        approved = ", ".join(root.as_posix() for root in roots)
        raise ExposureDeliveryOutputError(
            f"output must be under an approved root ({approved}); refused {resolved}"
        )


def _write_new(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _publish_files(files: Sequence[tuple[Path, bytes]], *, overwrite: bool) -> None:
    temporary: list[tuple[Path, Path]] = []
    backups: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    token = uuid.uuid4().hex
    try:
        for final, payload in files:
            final.parent.mkdir(parents=True, exist_ok=True)
            temp = final.with_name(f".{final.name}.{token}.tmp")
            _write_new(temp, payload)
            temporary.append((temp, final))
        if not overwrite and any(final.exists() for _temp, final in temporary):
            raise ExposureDeliveryOutputError(
                "an output already exists; use explicit overwrite authorization"
            )
        if overwrite:
            for _temp, final in temporary:
                if final.exists():
                    backup = final.with_name(f".{final.name}.{token}.backup")
                    os.replace(final, backup)
                    backups.append((backup, final))
        for temp, final in temporary:
            os.replace(temp, final)
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
    finally:
        for temp, _final in temporary:
            temp.unlink(missing_ok=True)


def write_delivery(
    inspection: BundleInspection,
    display_path: Path,
    results_path: Path,
    *,
    generated_at: datetime,
    overwrite: bool = False,
    display_roots: Sequence[Path] | None = None,
    results_roots: Sequence[Path] | None = None,
) -> DeliveryResult:
    """Validate destinations, build all bytes, then publish the three-file set."""
    _validate_output_path(
        display_path,
        suffix=GEOJSON_SUFFIX,
        roots=DISPLAY_OUTPUT_ROOTS if display_roots is None else display_roots,
    )
    _validate_output_path(
        results_path,
        suffix=JSON_SUFFIX,
        roots=RESULTS_OUTPUT_ROOTS if results_roots is None else results_roots,
    )
    manifest_path = display_path.with_name(display_path.name + MANIFEST_SUFFIX)
    resolved = {path.resolve() for path in (display_path, manifest_path, results_path)}
    if len(resolved) != 3:
        raise ExposureDeliveryOutputError("delivery output paths overlap")
    export = build_delivery_export(
        inspection,
        display_name=display_path.name,
        generated_at=generated_at,
    )
    try:
        _publish_files(
            (
                (display_path, export.display.geojson),
                (manifest_path, export.display_manifest),
                (results_path, export.results.payload),
            ),
            overwrite=overwrite,
        )
    except ExposureDeliveryError:
        raise
    except Exception as exc:
        raise ExposureDeliveryOutputError(
            f"could not publish exposure delivery artifacts: {exc}"
        ) from exc
    return DeliveryResult(
        display_path=display_path,
        display_manifest_path=manifest_path,
        results_path=results_path,
        display_sha256=export.display.sha256,
        display_manifest_sha256=hashlib.sha256(export.display_manifest).hexdigest(),
        results_sha256=export.results.sha256,
        results_id=cast(str, export.results.document["results_id"]),
    )
