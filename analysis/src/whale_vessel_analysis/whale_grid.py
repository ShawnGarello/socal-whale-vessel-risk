"""Abundance-conserving transfer of modeled whale density to the water grid."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final, Literal, cast

import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import pyproj
import shapely
from pyogrio.errors import DataLayerError, DataSourceError, FieldError
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError
from shapely import (
    STRtree,
    from_wkb,
    get_coordinates,
    normalize,
    to_wkb,
    transform,
    unary_union,
)
from shapely.errors import GEOSException
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis.config import (
    CONFIG_SCHEMA_VERSION,
    PROJECTED_CRS,
    ProcessingConfig,
)
from whale_vessel_analysis.lineage import (
    ArtifactReference,
    ProcessingStep,
    RunMetadata,
    ValidationRecord,
)
from whale_vessel_analysis.spatial_grid import (
    AREA_TOLERANCE_M2,
    CELL_ID_PATTERN,
    GEOMETRY_COLUMN,
    GEOPARQUET_VERSION,
    GRID_DATASET_SCHEMA_VERSION,
    ROW_ORDER,
    sha256_path,
)
from whale_vessel_analysis.whale import (
    WHALE_DENSITY_UNIT,
    WHALE_LAYER_NAME,
    WHALE_SOURCE_CRS,
    WhaleValidationResult,
    validate_whale_input,
)

WHALE_GRID_DATASET_SCHEMA_VERSION: Final = 1
WHALE_GRID_PROCESSING_VERSION: Final = "1.0.0"
WHALE_GRID_CONTRACT: Final = "blue_whale_grid_transfer_v1"
WHALE_GRID_LINEAGE_CONTRACT: Final = "blue_whale_grid_transfer_lineage_v1"
GRID_INPUT_CONTRACT: Final = "projected_water_grid_v1"
CONSERVATION_ABSOLUTE_TOLERANCE_ANIMALS: Final = 1e-9
CONSERVATION_RELATIVE_TOLERANCE: Final = 1e-10
SOURCE_OVERLAP_AREA_TOLERANCE_M2: Final = 1.0
COVERAGE_EXACT_TOLERANCE_M2: Final = 1e-6
COVERAGE_NUMERICAL_TOLERANCE_M2: Final = 0.1
LINEAGE_SUFFIX: Final = ".lineage.json"
_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
_PROJECT_RAW_ROOT: Final = (_PROJECT_ROOT / "data" / "raw").resolve()

CoverageStatus = Literal["complete", "within_numerical_tolerance", "incomplete"]


class WhaleGridError(ValueError):
    """Raised when whale-grid transfer input, processing, or output is invalid."""


class WhaleGridInputError(WhaleGridError):
    """Raised when a whale or target-grid input violates its contract."""


class WhaleGridOverlapError(WhaleGridError):
    """Raised when source polygon interiors overlap enough to double count."""


class WhaleGridConservationError(WhaleGridError):
    """Raised when target allocation does not conserve source contribution."""


class WhaleGridOutputError(WhaleGridError):
    """Raised when an output bundle cannot be published atomically."""


@dataclass(frozen=True, slots=True)
class WhaleSourceFeature:
    """One validated source polygon and its modeled density."""

    source_index: int
    density_animals_per_km2: float
    geometry: BaseGeometry


@dataclass(frozen=True, slots=True)
class WhaleSourceInspection:
    """Validated and projected source features plus lineage facts."""

    features: tuple[WhaleSourceFeature, ...]
    path: Path
    layer: str
    source_crs: str
    source_sha256: str
    transformation: str
    validation: WhaleValidationResult


@dataclass(frozen=True, slots=True)
class TargetGridCell:
    """One validated target water-grid row."""

    cell_id: str
    row_index: int
    column_index: int
    x_min_m: int
    y_min_m: int
    x_max_m: int
    y_max_m: int
    water_area_m2: float
    water_area_km2: float
    geometry: BaseGeometry
    geometry_wkb: bytes


@dataclass(frozen=True, slots=True)
class TargetGridInspection:
    """Validated target grid and the metadata required for transfer lineage."""

    cells: tuple[TargetGridCell, ...]
    path: Path
    sha256: str
    metadata: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class WhaleGridCell:
    """One target cell carrying transferred modeled whale values."""

    target: TargetGridCell
    modeled_abundance_allocation_animals: float
    modeled_density_animals_per_km2: float
    source_covered_water_area_m2: float
    uncovered_water_area_m2: float
    source_coverage_fraction: float
    coverage_status: CoverageStatus
    source_polygon_count: int

    @property
    def source_covered_water_area_km2(self) -> float:
        return self.source_covered_water_area_m2 / 1_000_000.0

    @property
    def uncovered_water_area_km2(self) -> float:
        return self.uncovered_water_area_m2 / 1_000_000.0


@dataclass(frozen=True, slots=True)
class WhaleGridDiagnostics:
    """Counts and numerical checks from one deterministic transfer."""

    source_feature_count: int
    target_cell_count: int
    intersection_count: int
    source_overlap_pair_count_within_tolerance: int
    source_overlap_area_m2_within_tolerance: float
    complete_cell_count: int
    numerical_tolerance_cell_count: int
    incomplete_cell_count: int
    total_water_area_m2: float
    total_source_covered_water_area_m2: float
    total_uncovered_water_area_m2: float
    source_contribution_animals: float
    allocated_abundance_animals: float
    conservation_difference_animals: float
    conservation_absolute_tolerance_animals: float
    conservation_relative_tolerance: float

    @property
    def conservation_passed(self) -> bool:
        return math.isclose(
            self.allocated_abundance_animals,
            self.source_contribution_animals,
            rel_tol=self.conservation_relative_tolerance,
            abs_tol=self.conservation_absolute_tolerance_animals,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_feature_count": self.source_feature_count,
            "target_cell_count": self.target_cell_count,
            "intersection_count": self.intersection_count,
            "source_overlap_pair_count_within_tolerance": (
                self.source_overlap_pair_count_within_tolerance
            ),
            "source_overlap_area_m2_within_tolerance": (
                self.source_overlap_area_m2_within_tolerance
            ),
            "coverage": {
                "complete_cell_count": self.complete_cell_count,
                "numerical_tolerance_cell_count": (self.numerical_tolerance_cell_count),
                "incomplete_cell_count": self.incomplete_cell_count,
                "total_water_area_m2": self.total_water_area_m2,
                "total_source_covered_water_area_m2": (
                    self.total_source_covered_water_area_m2
                ),
                "total_uncovered_water_area_m2": self.total_uncovered_water_area_m2,
            },
            "conservation": {
                "passed": self.conservation_passed,
                "source_contribution_animals": self.source_contribution_animals,
                "allocated_abundance_animals": self.allocated_abundance_animals,
                "difference_animals": self.conservation_difference_animals,
                "absolute_tolerance_animals": (
                    self.conservation_absolute_tolerance_animals
                ),
                "relative_tolerance": self.conservation_relative_tolerance,
            },
        }


@dataclass(frozen=True, slots=True)
class WhaleGridDataset:
    """Transferred grid cells and all deterministic processing diagnostics."""

    cells: tuple[WhaleGridCell, ...]
    diagnostics: WhaleGridDiagnostics
    source_sha256: str
    target_grid_sha256: str
    configuration_sha256: str
    transformation: str

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        if not self.cells:
            raise WhaleGridError("whale-grid dataset contains no cells")
        return (
            min(cell.target.geometry.bounds[0] for cell in self.cells),
            min(cell.target.geometry.bounds[1] for cell in self.cells),
            max(cell.target.geometry.bounds[2] for cell in self.cells),
            max(cell.target.geometry.bounds[3] for cell in self.cells),
        )

    def summary(self) -> dict[str, object]:
        return {
            "contract": WHALE_GRID_CONTRACT,
            "schema_version": WHALE_GRID_DATASET_SCHEMA_VERSION,
            "analysis_crs": PROJECTED_CRS,
            "row_order": ROW_ORDER,
            "cell_count": len(self.cells),
            "density_unit": WHALE_DENSITY_UNIT,
            "abundance_allocation_unit": "animals",
            "coverage_area_unit": "m² (with km² companion columns)",
            "diagnostics": self.diagnostics.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class WhaleGridWriteResult:
    """Published output paths, checksums, and transfer summary."""

    output_path: Path
    lineage_path: Path
    output_sha256: str
    output_bytes: int
    lineage_sha256: str
    dataset: WhaleGridDataset

    def to_dict(self) -> dict[str, object]:
        return {
            "output": {
                "path": str(self.output_path),
                "bytes": self.output_bytes,
                "sha256": self.output_sha256,
                "format": "GeoParquet 1.1.0 with WKB geometry",
            },
            "lineage": {
                "path": str(self.lineage_path),
                "sha256": self.lineage_sha256,
            },
            "dataset": self.dataset.summary(),
        }


def _canonical_json(value: Mapping[str, object]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _geometry_is_finite(geometry: BaseGeometry) -> bool:
    coordinates = get_coordinates(geometry, include_z=False)
    return bool(
        coordinates.size
        and all(math.isfinite(float(value)) for value in coordinates.flat)
    )


def _validate_polygon(geometry: BaseGeometry, label: str) -> None:
    if geometry.is_empty:
        raise WhaleGridInputError(f"{label} geometry is empty")
    if not _geometry_is_finite(geometry):
        raise WhaleGridInputError(f"{label} geometry has non-finite coordinates")
    if not geometry.is_valid:
        raise WhaleGridInputError(f"{label} geometry is invalid")
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise WhaleGridInputError(
            f"{label} geometry must be Polygon or MultiPolygon, "
            f"received {geometry.geom_type}"
        )


def _polygonal_parts(geometry: BaseGeometry) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon | GeometryCollection):
        parts: list[Polygon] = []
        for part in geometry.geoms:
            parts.extend(_polygonal_parts(cast(BaseGeometry, part)))
        return parts
    return []


def _polygonal_only(geometry: BaseGeometry) -> BaseGeometry:
    parts = _polygonal_parts(geometry)
    if not parts:
        return Polygon()
    combined = parts[0] if len(parts) == 1 else unary_union(parts)
    return cast(BaseGeometry, normalize(combined))


def _parse_crs(value: object, label: str) -> CRS:
    if value is None or not str(value).strip():
        raise WhaleGridInputError(f"{label} CRS is missing")
    try:
        return CRS.from_user_input(value)
    except CRSError as exc:
        raise WhaleGridInputError(f"{label} CRS is invalid: {value}") from exc


def reproject_source_geometry(
    geometry: BaseGeometry, source_crs: str
) -> tuple[BaseGeometry, str]:
    """Project source geometry to EPSG:3310 with explicit x/y axis ordering."""
    _validate_polygon(geometry, "source whale")
    source = _parse_crs(source_crs, "source whale")
    expected = CRS.from_user_input(WHALE_SOURCE_CRS)
    if not source.equals(expected):
        raise WhaleGridInputError(
            f"source whale CRS must be {WHALE_SOURCE_CRS}, "
            f"received {source.to_string()}"
        )
    transformer = Transformer.from_crs(source, PROJECTED_CRS, always_xy=True)
    try:
        projected = cast(
            BaseGeometry,
            transform(
                geometry,
                transformer.transform,
                include_z=False,
                interleaved=False,
            ),
        )
    except (GEOSException, ValueError) as exc:
        raise WhaleGridInputError(
            f"could not transform whale geometry to {PROJECTED_CRS}"
        ) from exc
    _validate_polygon(projected, "projected whale")
    definition = transformer.definition
    if not definition or definition == "unavailable until proj_trans is called":
        definition = transformer.to_json()
    return cast(BaseGeometry, normalize(projected)), definition


def _validate_density(value: object, label: str) -> float:
    if value is None:
        raise WhaleGridInputError(f"{label} modeled density is missing")
    try:
        density = float(cast(int | float | str, value))
    except (TypeError, ValueError) as exc:
        raise WhaleGridInputError(f"{label} modeled density is invalid") from exc
    if not math.isfinite(density):
        raise WhaleGridInputError(f"{label} modeled density must be finite")
    if density < 0:
        raise WhaleGridInputError(f"{label} modeled density cannot be negative")
    return density


def load_whale_source(
    path: Path, *, layer: str = WHALE_LAYER_NAME
) -> WhaleSourceInspection:
    """Validate and load the selected source layer, then project it to EPSG:3310."""
    validation = validate_whale_input(path, layer=layer)
    if not validation.passed:
        detail = "; ".join(validation.messages()) or "validation failed"
        raise WhaleGridInputError(
            f"whale input does not satisfy its contract: {detail}"
        )
    try:
        metadata, raw_table = pyogrio.read_arrow(
            path,
            layer=layer,
            columns=["DENSITY"],
            read_geometry=True,
        )
    except (DataLayerError, DataSourceError, FieldError) as exc:
        raise WhaleGridInputError(f"could not read whale input {path}: {exc}") from exc
    table = cast(pa.Table, raw_table)
    geometry_name = str(metadata.get("geometry_name", ""))
    if not geometry_name or geometry_name not in table.column_names:
        raise WhaleGridInputError(
            f"whale input {path} did not provide a WKB geometry column"
        )
    rows = cast(list[dict[str, object]], table.to_pylist())
    projected_rows: list[tuple[float, BaseGeometry, bytes]] = []
    transformation_definition = ""
    for row_index, row in enumerate(rows):
        density = _validate_density(row.get("DENSITY"), f"source row {row_index}")
        value = row.get(geometry_name)
        if not isinstance(value, bytes):
            raise WhaleGridInputError(f"source row {row_index} geometry is missing")
        try:
            geometry = cast(BaseGeometry, from_wkb(value))
        except GEOSException as exc:
            raise WhaleGridInputError(
                f"source row {row_index} geometry is invalid WKB"
            ) from exc
        projected, definition = reproject_source_geometry(geometry, WHALE_SOURCE_CRS)
        transformation_definition = definition
        canonical_wkb = cast(
            bytes,
            to_wkb(
                projected,
                hex=False,
                output_dimension=2,
                byte_order=1,
                include_srid=False,
                flavor="iso",
            ),
        )
        projected_rows.append((density, projected, canonical_wkb))
    projected_rows.sort(
        key=lambda item: (
            item[1].bounds[1],
            item[1].bounds[0],
            item[1].bounds[3],
            item[1].bounds[2],
            item[0],
            item[2],
        )
    )
    features = tuple(
        WhaleSourceFeature(index, density, geometry)
        for index, (density, geometry, _wkb) in enumerate(projected_rows)
    )
    if not features:
        raise WhaleGridInputError("whale input contains no source features")
    return WhaleSourceInspection(
        features=features,
        path=path,
        layer=layer,
        source_crs=WHALE_SOURCE_CRS,
        source_sha256=sha256_path(path),
        transformation=transformation_definition,
        validation=validation,
    )


_GRID_FIELDS: Final = (
    ("cell_id", pa.string(), False),
    ("row_index", pa.int16(), False),
    ("column_index", pa.int16(), False),
    ("cell_x_min_m", pa.int32(), False),
    ("cell_y_min_m", pa.int32(), False),
    ("cell_x_max_m", pa.int32(), False),
    ("cell_y_max_m", pa.int32(), False),
    ("water_area_m2", pa.float64(), False),
    ("water_area_km2", pa.float64(), False),
    (GEOMETRY_COLUMN, pa.binary(), False),
)


def _metadata_document(
    schema: pa.Schema, key: bytes, label: str
) -> Mapping[str, object]:
    metadata = schema.metadata
    if metadata is None or key not in metadata:
        raise WhaleGridInputError(f"target grid is missing {label} metadata")
    try:
        value = json.loads(metadata[key])
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WhaleGridInputError(f"target grid has invalid {label} metadata") from exc
    if not isinstance(value, dict):
        raise WhaleGridInputError(f"target grid {label} metadata must be an object")
    return cast(Mapping[str, object], value)


def _validate_grid_schema(schema: pa.Schema) -> None:
    if len(schema) != len(_GRID_FIELDS):
        raise WhaleGridInputError(
            "target grid columns do not match projected_water_grid_v1"
        )
    for actual, (name, data_type, nullable) in zip(schema, _GRID_FIELDS, strict=True):
        if (
            actual.name != name
            or actual.type != data_type
            or actual.nullable != nullable
        ):
            raise WhaleGridInputError(
                "target grid columns do not match projected_water_grid_v1: "
                f"expected {name} {data_type} nullable={nullable}, received "
                f"{actual.name} {actual.type} nullable={actual.nullable}"
            )


def _nested_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise WhaleGridInputError(f"target grid metadata {label} must be an object")
    return cast(Mapping[str, object], value)


def _validate_grid_metadata(
    schema: pa.Schema, config: ProcessingConfig
) -> Mapping[str, object]:
    contract = _metadata_document(schema, b"whale_vessel_analysis", "contract")
    if contract.get("contract") != GRID_INPUT_CONTRACT:
        raise WhaleGridInputError(f"target grid contract must be {GRID_INPUT_CONTRACT}")
    if contract.get("schema_version") != GRID_DATASET_SCHEMA_VERSION:
        raise WhaleGridInputError(
            f"target grid schema_version must be {GRID_DATASET_SCHEMA_VERSION}"
        )
    if contract.get("analysis_crs") != PROJECTED_CRS:
        raise WhaleGridInputError(f"target grid analysis CRS must be {PROJECTED_CRS}")
    grid = _nested_mapping(contract.get("grid"), "grid")
    expected_grid = config.spatial.grid
    expected_grid_values: dict[str, object] = {
        "bounds_m": [
            expected_grid.x_min_m,
            expected_grid.y_min_m,
            expected_grid.x_max_m,
            expected_grid.y_max_m,
        ],
        "cell_size_m": expected_grid.cell_size_m,
        "rows": expected_grid.rows,
        "columns": expected_grid.columns,
        "nominal_cell_count": expected_grid.rows * expected_grid.columns,
    }
    for key, expected in expected_grid_values.items():
        if grid.get(key) != expected:
            raise WhaleGridInputError(
                f"target grid metadata {key} does not match configuration"
            )
    configuration = _nested_mapping(contract.get("configuration"), "configuration")
    if configuration.get("version") != CONFIG_SCHEMA_VERSION:
        raise WhaleGridInputError("target grid configuration version is invalid")
    if configuration.get("sha256") != config.digest():
        raise WhaleGridInputError(
            "target grid configuration checksum does not match selected configuration"
        )
    output = _nested_mapping(contract.get("output"), "output")
    if output.get("row_order") != ROW_ORDER:
        raise WhaleGridInputError("target grid row ordering contract is invalid")
    if output.get("cell_id_pattern") != CELL_ID_PATTERN:
        raise WhaleGridInputError("target grid cell identity contract is invalid")

    geo = _metadata_document(schema, b"geo", "GeoParquet")
    if geo.get("version") != GEOPARQUET_VERSION:
        raise WhaleGridInputError(
            f"target grid GeoParquet version must be {GEOPARQUET_VERSION}"
        )
    if geo.get("primary_column") != GEOMETRY_COLUMN:
        raise WhaleGridInputError("target grid primary geometry column is invalid")
    columns = _nested_mapping(geo.get("columns"), "GeoParquet columns")
    geometry_metadata = _nested_mapping(
        columns.get(GEOMETRY_COLUMN), "GeoParquet geometry"
    )
    if geometry_metadata.get("encoding") != "WKB":
        raise WhaleGridInputError("target grid geometry encoding must be WKB")
    embedded_crs = _parse_crs(geometry_metadata.get("crs"), "target grid")
    if not embedded_crs.equals(CRS.from_user_input(PROJECTED_CRS)):
        raise WhaleGridInputError(f"target grid embedded CRS must be {PROJECTED_CRS}")
    return contract


def _integer_value(row: Mapping[str, object], name: str, row_index: int) -> int:
    value = row.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise WhaleGridInputError(f"target grid row {row_index} has invalid {name}")
    return value


def _float_value(row: Mapping[str, object], name: str, row_index: int) -> float:
    value = row.get(name)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise WhaleGridInputError(f"target grid row {row_index} has invalid {name}")
    result = float(value)
    if not math.isfinite(result):
        raise WhaleGridInputError(f"target grid row {row_index} has non-finite {name}")
    return result


def load_target_grid(
    path: Path,
    config: ProcessingConfig,
    *,
    expected_sha256: str | None = None,
) -> TargetGridInspection:
    """Read and validate one exact projected_water_grid_v1 GeoParquet."""
    if not path.is_file():
        raise WhaleGridInputError(f"target grid does not exist: {path}")
    checksum = _sha256_file(path)
    if expected_sha256 is not None and checksum != expected_sha256:
        raise WhaleGridInputError(
            "target grid checksum does not match expected SHA-256: "
            f"expected {expected_sha256}, received {checksum}"
        )
    try:
        schema = pq.read_schema(path)
        _validate_grid_schema(schema)
        metadata = _validate_grid_metadata(schema, config)
        table = pq.read_table(path)
    except WhaleGridInputError:
        raise
    except (OSError, pa.ArrowException) as exc:
        raise WhaleGridInputError(f"could not read target grid {path}: {exc}") from exc
    if table.num_rows == 0:
        raise WhaleGridInputError("target grid contains no retained water cells")
    output_metadata = _nested_mapping(metadata.get("output"), "output")
    if output_metadata.get("retained_water_cell_count") != table.num_rows:
        raise WhaleGridInputError(
            "target grid row count does not match contract metadata"
        )

    rows = cast(list[dict[str, object]], table.to_pylist())
    cells: list[TargetGridCell] = []
    seen_ids: set[str] = set()
    grid = config.spatial.grid
    nominal_area_m2 = float(grid.cell_size_m * grid.cell_size_m)
    for input_row, row in enumerate(rows):
        cell_id = row.get("cell_id")
        if not isinstance(cell_id, str):
            raise WhaleGridInputError(
                f"target grid row {input_row} has invalid cell_id"
            )
        row_index = _integer_value(row, "row_index", input_row)
        column_index = _integer_value(row, "column_index", input_row)
        if not (0 <= row_index < grid.rows and 0 <= column_index < grid.columns):
            raise WhaleGridInputError(
                f"target grid row {input_row} has out-of-range grid indices"
            )
        expected_id = CELL_ID_PATTERN.format(row=row_index, column=column_index)
        if cell_id != expected_id:
            raise WhaleGridInputError(
                f"target grid row {input_row} cell_id does not match its indices"
            )
        if cell_id in seen_ids:
            raise WhaleGridInputError(f"target grid has duplicate cell_id {cell_id}")
        seen_ids.add(cell_id)
        x_min = _integer_value(row, "cell_x_min_m", input_row)
        y_min = _integer_value(row, "cell_y_min_m", input_row)
        x_max = _integer_value(row, "cell_x_max_m", input_row)
        y_max = _integer_value(row, "cell_y_max_m", input_row)
        expected_bounds = (
            grid.x_min_m + column_index * grid.cell_size_m,
            grid.y_min_m + row_index * grid.cell_size_m,
            grid.x_min_m + (column_index + 1) * grid.cell_size_m,
            grid.y_min_m + (row_index + 1) * grid.cell_size_m,
        )
        if (x_min, y_min, x_max, y_max) != expected_bounds:
            raise WhaleGridInputError(
                f"target grid row {input_row} parent bounds are invalid"
            )
        water_area_m2 = _float_value(row, "water_area_m2", input_row)
        water_area_km2 = _float_value(row, "water_area_km2", input_row)
        if water_area_m2 <= 0 or water_area_m2 > nominal_area_m2 + AREA_TOLERANCE_M2:
            raise WhaleGridInputError(
                f"target grid row {input_row} water area is invalid"
            )
        if not math.isclose(
            water_area_km2,
            water_area_m2 / 1_000_000.0,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise WhaleGridInputError(
                f"target grid row {input_row} water area units are inconsistent"
            )
        geometry_value = row.get(GEOMETRY_COLUMN)
        if not isinstance(geometry_value, bytes):
            raise WhaleGridInputError(
                f"target grid row {input_row} geometry is missing"
            )
        try:
            geometry = cast(BaseGeometry, from_wkb(geometry_value))
        except GEOSException as exc:
            raise WhaleGridInputError(
                f"target grid row {input_row} geometry is invalid WKB"
            ) from exc
        _validate_polygon(geometry, f"target grid row {input_row}")
        parent = box(x_min, y_min, x_max, y_max)
        if not parent.covers(geometry):
            outside_area = float(geometry.difference(parent).area)
            if outside_area > AREA_TOLERANCE_M2:
                raise WhaleGridInputError(
                    f"target grid row {input_row} geometry lies outside parent cell"
                )
        if not math.isclose(
            float(geometry.area),
            water_area_m2,
            rel_tol=1e-12,
            abs_tol=AREA_TOLERANCE_M2,
        ):
            raise WhaleGridInputError(
                f"target grid row {input_row} geometry area is inconsistent"
            )
        cells.append(
            TargetGridCell(
                cell_id=cell_id,
                row_index=row_index,
                column_index=column_index,
                x_min_m=x_min,
                y_min_m=y_min,
                x_max_m=x_max,
                y_max_m=y_max,
                water_area_m2=water_area_m2,
                water_area_km2=water_area_km2,
                geometry=geometry,
                geometry_wkb=geometry_value,
            )
        )
    order = [(cell.row_index, cell.column_index) for cell in cells]
    if order != sorted(order):
        raise WhaleGridInputError(
            "target grid rows are not in documented south-to-north, west-to-east order"
        )
    return TargetGridInspection(
        cells=tuple(cells),
        path=path,
        sha256=checksum,
        metadata=metadata,
    )


def _validate_source_features(features: Sequence[WhaleSourceFeature]) -> None:
    if not features:
        raise WhaleGridInputError("whale source contains no features")
    seen_indices: set[int] = set()
    for position, feature in enumerate(features):
        if feature.source_index in seen_indices:
            raise WhaleGridInputError("whale source indices must be unique")
        seen_indices.add(feature.source_index)
        _validate_density(feature.density_animals_per_km2, f"source row {position}")
        _validate_polygon(feature.geometry, f"source row {position}")


def _source_overlap_diagnostics(
    features: Sequence[WhaleSourceFeature], tree: STRtree
) -> tuple[int, float]:
    geometries = [feature.geometry for feature in features]
    overlap_areas: list[float] = []
    for left_index, left in enumerate(geometries):
        candidate_indices = sorted(int(index) for index in tree.query(left))
        for right_index in candidate_indices:
            if right_index <= left_index:
                continue
            overlap = _polygonal_only(left.intersection(geometries[right_index]))
            area = float(overlap.area)
            if area <= 0:
                continue
            if area > SOURCE_OVERLAP_AREA_TOLERANCE_M2:
                raise WhaleGridOverlapError(
                    "source whale polygon interiors overlap beyond tolerance: "
                    f"source_index={features[left_index].source_index} and "
                    f"source_index={features[right_index].source_index}, "
                    f"overlap_area_m2={area}, "
                    f"tolerance_m2={SOURCE_OVERLAP_AREA_TOLERANCE_M2}"
                )
            overlap_areas.append(area)
    return len(overlap_areas), math.fsum(overlap_areas)


def _coverage_status(uncovered_area_m2: float) -> CoverageStatus:
    if uncovered_area_m2 <= COVERAGE_EXACT_TOLERANCE_M2:
        return "complete"
    if uncovered_area_m2 <= COVERAGE_NUMERICAL_TOLERANCE_M2:
        return "within_numerical_tolerance"
    return "incomplete"


def transfer_whale_density(
    source: WhaleSourceInspection,
    target_grid: TargetGridInspection,
    config: ProcessingConfig,
) -> WhaleGridDataset:
    """Allocate modeled abundance by intersection area and derive cell density."""
    _validate_source_features(source.features)
    if not target_grid.cells:
        raise WhaleGridInputError("target grid contains no cells")
    geometries = [feature.geometry for feature in source.features]
    tree = STRtree(geometries)
    overlap_pair_count, overlap_area_m2 = _source_overlap_diagnostics(
        source.features, tree
    )
    source_contributions: list[list[float]] = [[] for _feature in source.features]
    output_cells: list[WhaleGridCell] = []
    intersection_count = 0
    status_counts: dict[CoverageStatus, int] = {
        "complete": 0,
        "within_numerical_tolerance": 0,
        "incomplete": 0,
    }
    for target in target_grid.cells:
        contributions: list[float] = []
        intersections: list[BaseGeometry] = []
        contributing_sources: set[int] = set()
        candidate_indices = sorted(int(index) for index in tree.query(target.geometry))
        for source_index in candidate_indices:
            feature = source.features[source_index]
            intersection = _polygonal_only(
                feature.geometry.intersection(target.geometry)
            )
            area_m2 = float(intersection.area)
            if area_m2 <= 0:
                continue
            contribution = feature.density_animals_per_km2 * area_m2 / 1_000_000.0
            if not math.isfinite(contribution) or contribution < 0:
                raise WhaleGridError(
                    f"non-finite or negative contribution for {target.cell_id}"
                )
            contributions.append(contribution)
            source_contributions[source_index].append(contribution)
            intersections.append(intersection)
            contributing_sources.add(source_index)
            intersection_count += 1
        covered_geometry = (
            Polygon()
            if not intersections
            else _polygonal_only(unary_union(intersections))
        )
        covered_area_m2 = float(covered_geometry.area)
        if covered_area_m2 > target.water_area_m2 + COVERAGE_NUMERICAL_TOLERANCE_M2:
            raise WhaleGridError(
                f"source coverage exceeds target water area for {target.cell_id}: "
                f"covered={covered_area_m2}, water={target.water_area_m2}"
            )
        uncovered_area_m2 = max(0.0, target.water_area_m2 - covered_area_m2)
        status = _coverage_status(uncovered_area_m2)
        status_counts[status] += 1
        allocation = math.fsum(contributions)
        density = allocation / target.water_area_km2
        coverage_fraction = min(1.0, covered_area_m2 / target.water_area_m2)
        output_cells.append(
            WhaleGridCell(
                target=target,
                modeled_abundance_allocation_animals=allocation,
                modeled_density_animals_per_km2=density,
                source_covered_water_area_m2=covered_area_m2,
                uncovered_water_area_m2=uncovered_area_m2,
                source_coverage_fraction=coverage_fraction,
                coverage_status=status,
                source_polygon_count=len(contributing_sources),
            )
        )
    source_contribution = math.fsum(
        math.fsum(contributions) for contributions in source_contributions
    )
    allocated_abundance = math.fsum(
        cell.modeled_abundance_allocation_animals for cell in output_cells
    )
    diagnostics = WhaleGridDiagnostics(
        source_feature_count=len(source.features),
        target_cell_count=len(target_grid.cells),
        intersection_count=intersection_count,
        source_overlap_pair_count_within_tolerance=overlap_pair_count,
        source_overlap_area_m2_within_tolerance=overlap_area_m2,
        complete_cell_count=status_counts["complete"],
        numerical_tolerance_cell_count=status_counts["within_numerical_tolerance"],
        incomplete_cell_count=status_counts["incomplete"],
        total_water_area_m2=math.fsum(
            cell.target.water_area_m2 for cell in output_cells
        ),
        total_source_covered_water_area_m2=math.fsum(
            cell.source_covered_water_area_m2 for cell in output_cells
        ),
        total_uncovered_water_area_m2=math.fsum(
            cell.uncovered_water_area_m2 for cell in output_cells
        ),
        source_contribution_animals=source_contribution,
        allocated_abundance_animals=allocated_abundance,
        conservation_difference_animals=allocated_abundance - source_contribution,
        conservation_absolute_tolerance_animals=(
            CONSERVATION_ABSOLUTE_TOLERANCE_ANIMALS
        ),
        conservation_relative_tolerance=CONSERVATION_RELATIVE_TOLERANCE,
    )
    if not diagnostics.conservation_passed:
        raise WhaleGridConservationError(
            "modeled abundance allocation did not conserve source contribution: "
            f"source={source_contribution}, allocated={allocated_abundance}, "
            f"difference={diagnostics.conservation_difference_animals}"
        )
    return WhaleGridDataset(
        cells=tuple(output_cells),
        diagnostics=diagnostics,
        source_sha256=source.source_sha256,
        target_grid_sha256=target_grid.sha256,
        configuration_sha256=config.digest(),
        transformation=source.transformation,
    )


def _dataset_metadata(dataset: WhaleGridDataset) -> dict[str, object]:
    return {
        "contract": WHALE_GRID_CONTRACT,
        "schema_version": WHALE_GRID_DATASET_SCHEMA_VERSION,
        "analysis_crs": PROJECTED_CRS,
        "method": {
            "name": "abundance-conserving area-weighted polygon transfer",
            "contribution": (
                "source modeled density (animals/km²) multiplied by overlap area (km²)"
            ),
            "target_density": (
                "modeled abundance allocation (animals) / cell water area (km²)"
            ),
            "source_overlap_area_tolerance_m2": (SOURCE_OVERLAP_AREA_TOLERANCE_M2),
            "coverage_exact_tolerance_m2": COVERAGE_EXACT_TOLERANCE_M2,
            "coverage_numerical_tolerance_m2": (COVERAGE_NUMERICAL_TOLERANCE_M2),
            "uncertainty_propagation": "not_performed",
            "resolution_limit": (
                "5 km reporting grid; biological precision remains limited to the "
                "approximately 0.1-degree source model"
            ),
        },
        "units": {
            "modeled_abundance_allocation_animals": "animals",
            "modeled_density_animals_per_km2": "animals/km²",
            "water_area_m2": "m²",
            "water_area_km2": "km²",
            "source_covered_water_area_m2": "m²",
            "source_covered_water_area_km2": "km²",
            "uncovered_water_area_m2": "m²",
            "uncovered_water_area_km2": "km²",
            "source_coverage_fraction": "unitless [0,1]",
        },
        "identity": {
            "row_order": ROW_ORDER,
            "cell_id_pattern": CELL_ID_PATTERN,
            "target_geometry_preserved": True,
        },
        "inputs": {
            "whale_source_sha256": dataset.source_sha256,
            "target_grid_sha256": dataset.target_grid_sha256,
            "configuration_sha256": dataset.configuration_sha256,
        },
        "transformation": {
            "source_crs": WHALE_SOURCE_CRS,
            "target_crs": PROJECTED_CRS,
            "always_xy": True,
            "definition": dataset.transformation,
        },
        "diagnostics": dataset.diagnostics.to_dict(),
    }


def _table(dataset: WhaleGridDataset) -> pa.Table:
    geo_metadata: dict[str, object] = {
        "version": GEOPARQUET_VERSION,
        "primary_column": GEOMETRY_COLUMN,
        "columns": {
            GEOMETRY_COLUMN: {
                "encoding": "WKB",
                "geometry_types": sorted(
                    {cell.target.geometry.geom_type for cell in dataset.cells}
                ),
                "crs": CRS.from_user_input(PROJECTED_CRS).to_json_dict(),
                "bbox": list(dataset.bounds),
            }
        },
    }
    fields = [
        pa.field("cell_id", pa.string(), nullable=False),
        pa.field("row_index", pa.int16(), nullable=False),
        pa.field("column_index", pa.int16(), nullable=False),
        pa.field("cell_x_min_m", pa.int32(), nullable=False),
        pa.field("cell_y_min_m", pa.int32(), nullable=False),
        pa.field("cell_x_max_m", pa.int32(), nullable=False),
        pa.field("cell_y_max_m", pa.int32(), nullable=False),
        pa.field("water_area_m2", pa.float64(), nullable=False),
        pa.field("water_area_km2", pa.float64(), nullable=False),
        pa.field("modeled_abundance_allocation_animals", pa.float64(), nullable=False),
        pa.field("modeled_density_animals_per_km2", pa.float64(), nullable=False),
        pa.field("source_covered_water_area_m2", pa.float64(), nullable=False),
        pa.field("source_covered_water_area_km2", pa.float64(), nullable=False),
        pa.field("uncovered_water_area_m2", pa.float64(), nullable=False),
        pa.field("uncovered_water_area_km2", pa.float64(), nullable=False),
        pa.field("source_coverage_fraction", pa.float64(), nullable=False),
        pa.field("coverage_status", pa.string(), nullable=False),
        pa.field("source_polygon_count", pa.int32(), nullable=False),
        pa.field(GEOMETRY_COLUMN, pa.binary(), nullable=False),
    ]
    schema = pa.schema(
        fields,
        metadata={
            b"geo": _canonical_json(geo_metadata).encode("utf-8"),
            b"whale_vessel_analysis": _canonical_json(
                _dataset_metadata(dataset)
            ).encode("utf-8"),
        },
    )
    cells = dataset.cells
    arrays: list[pa.Array] = [
        pa.array([cell.target.cell_id for cell in cells], type=pa.string()),
        pa.array([cell.target.row_index for cell in cells], type=pa.int16()),
        pa.array([cell.target.column_index for cell in cells], type=pa.int16()),
        pa.array([cell.target.x_min_m for cell in cells], type=pa.int32()),
        pa.array([cell.target.y_min_m for cell in cells], type=pa.int32()),
        pa.array([cell.target.x_max_m for cell in cells], type=pa.int32()),
        pa.array([cell.target.y_max_m for cell in cells], type=pa.int32()),
        pa.array([cell.target.water_area_m2 for cell in cells], type=pa.float64()),
        pa.array([cell.target.water_area_km2 for cell in cells], type=pa.float64()),
        pa.array(
            [cell.modeled_abundance_allocation_animals for cell in cells],
            type=pa.float64(),
        ),
        pa.array(
            [cell.modeled_density_animals_per_km2 for cell in cells],
            type=pa.float64(),
        ),
        pa.array(
            [cell.source_covered_water_area_m2 for cell in cells], type=pa.float64()
        ),
        pa.array(
            [cell.source_covered_water_area_km2 for cell in cells],
            type=pa.float64(),
        ),
        pa.array([cell.uncovered_water_area_m2 for cell in cells], type=pa.float64()),
        pa.array([cell.uncovered_water_area_km2 for cell in cells], type=pa.float64()),
        pa.array([cell.source_coverage_fraction for cell in cells], type=pa.float64()),
        pa.array([cell.coverage_status for cell in cells], type=pa.string()),
        pa.array([cell.source_polygon_count for cell in cells], type=pa.int32()),
        pa.array([cell.target.geometry_wkb for cell in cells], type=pa.binary()),
    ]
    return pa.Table.from_arrays(arrays, schema=schema)


def _package_version() -> str:
    try:
        return version("socal-whale-vessel-analysis")
    except PackageNotFoundError:
        return "uninstalled"


def _software_versions() -> dict[str, str]:
    gdal_version = getattr(pyogrio, "__gdal_version__", "unknown")
    if isinstance(gdal_version, tuple):
        gdal = ".".join(str(part) for part in gdal_version)
    else:
        gdal = str(gdal_version)
    return {
        "python": platform.python_version(),
        "package": _package_version(),
        "pyarrow": pa.__version__,
        "pyogrio": pyogrio.__version__,
        "gdal": gdal,
        "pyproj": pyproj.__version__,
        "proj": pyproj.proj_version_str,
        "shapely": shapely.__version__,
        "geos": shapely.geos_version_string,
        "platform": sys.platform,
    }


def _lineage_document(
    *,
    dataset: WhaleGridDataset,
    source: WhaleSourceInspection,
    target_grid: TargetGridInspection,
    output_path: Path,
    output_sha256: str,
    started_at: datetime,
    completed_at: datetime,
    expected_grid_sha256: str | None,
) -> dict[str, object]:
    if started_at.utcoffset() != UTC.utcoffset(started_at):
        raise WhaleGridOutputError("started_at must be timezone-aware UTC")
    if completed_at.utcoffset() != UTC.utcoffset(completed_at):
        raise WhaleGridOutputError("completed_at must be timezone-aware UTC")
    if completed_at <= started_at:
        raise WhaleGridOutputError("completed_at must be later than started_at")
    run_key = hashlib.sha256(
        (
            dataset.source_sha256
            + dataset.target_grid_sha256
            + dataset.configuration_sha256
            + output_sha256
            + WHALE_GRID_PROCESSING_VERSION
        ).encode("ascii")
    ).hexdigest()[:20]
    whale_counts = cast(Mapping[str, object], source.validation.to_dict()["counts"])
    validation_counts = {
        str(key): int(cast(int, value)) for key, value in whale_counts.items()
    }
    metadata = RunMetadata(
        run_id=f"whale-grid-{run_key}",
        started_at=started_at,
        completed_at=completed_at,
        configuration_version=CONFIG_SCHEMA_VERSION,
        configuration_sha256=dataset.configuration_sha256,
        steps=(
            ProcessingStep("validate-whale-source", WHALE_GRID_PROCESSING_VERSION),
            ProcessingStep("validate-target-water-grid", WHALE_GRID_PROCESSING_VERSION),
            ProcessingStep("reproject-whale-polygons", WHALE_GRID_PROCESSING_VERSION),
            ProcessingStep("detect-source-overlap", WHALE_GRID_PROCESSING_VERSION),
            ProcessingStep("allocate-modeled-abundance", WHALE_GRID_PROCESSING_VERSION),
            ProcessingStep("validate-conservation", WHALE_GRID_PROCESSING_VERSION),
            ProcessingStep(
                "write-whale-grid-geoparquet", WHALE_GRID_PROCESSING_VERSION
            ),
        ),
        inputs=(
            ArtifactReference(
                artifact_id="noaa-swfsc-blue-whale-source",
                locator=source.path.as_posix(),
                sha256=source.source_sha256,
            ),
            ArtifactReference(
                artifact_id="projected-water-grid",
                locator=target_grid.path.as_posix(),
                sha256=target_grid.sha256,
            ),
        ),
        outputs=(
            ArtifactReference(
                artifact_id="blue-whale-grid-transfer",
                locator=output_path.as_posix(),
                sha256=output_sha256,
            ),
        ),
        validations=(
            ValidationRecord.from_counts(
                "whale-source-contract", source.validation.passed, validation_counts
            ),
            ValidationRecord.from_counts(
                "target-grid-contract",
                True,
                {"retained_water_cell_count": len(target_grid.cells)},
            ),
            ValidationRecord.from_counts(
                "source-polygon-overlap",
                True,
                {
                    "overlap_pair_count_within_tolerance": (
                        dataset.diagnostics.source_overlap_pair_count_within_tolerance
                    ),
                    "source_feature_count": dataset.diagnostics.source_feature_count,
                },
            ),
            ValidationRecord.from_counts(
                "modeled-abundance-conservation",
                dataset.diagnostics.conservation_passed,
                {
                    "intersection_count": dataset.diagnostics.intersection_count,
                    "target_cell_count": dataset.diagnostics.target_cell_count,
                },
            ),
        ),
    )
    return {
        "contract": WHALE_GRID_LINEAGE_CONTRACT,
        "dataset": _dataset_metadata(dataset),
        "run": metadata.to_dict(),
        "inputs": {
            "whale_source": {
                "path": source.path.as_posix(),
                "layer": source.layer,
                "sha256": source.source_sha256,
                "checksum_method": (
                    "SHA-256 of file bytes"
                    if source.path.is_file()
                    else "directory-tree-sha256-v1"
                ),
                "validation": source.validation.to_dict(),
            },
            "target_grid": {
                "path": target_grid.path.as_posix(),
                "sha256": target_grid.sha256,
                "expected_sha256": expected_grid_sha256,
                "checksum_verified": (
                    expected_grid_sha256 is not None
                    and expected_grid_sha256 == target_grid.sha256
                ),
                "contract": GRID_INPUT_CONTRACT,
                "cell_count": len(target_grid.cells),
            },
        },
        "parameters": {
            "conservation_absolute_tolerance_animals": (
                CONSERVATION_ABSOLUTE_TOLERANCE_ANIMALS
            ),
            "conservation_relative_tolerance": CONSERVATION_RELATIVE_TOLERANCE,
            "source_overlap_area_tolerance_m2": SOURCE_OVERLAP_AREA_TOLERANCE_M2,
            "coverage_exact_tolerance_m2": COVERAGE_EXACT_TOLERANCE_M2,
            "coverage_numerical_tolerance_m2": (COVERAGE_NUMERICAL_TOLERANCE_M2),
            "always_xy": True,
            "uncertainty_propagation": "not_performed",
        },
        "software": _software_versions(),
        "output": {"path": output_path.as_posix(), "sha256": output_sha256},
        "visual_inspection_status": "not_completed",
    }


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    payload = (_canonical_json(document) + "\n").encode("utf-8")
    with path.open("xb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())


def _commit_pair(
    temporary_output: Path,
    output_path: Path,
    temporary_lineage: Path,
    lineage_path: Path,
    *,
    overwrite: bool,
) -> None:
    backups: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    try:
        if overwrite:
            for final in (output_path, lineage_path):
                if final.exists():
                    backup = final.with_name(f".{final.name}.{uuid.uuid4().hex}.backup")
                    os.replace(final, backup)
                    backups.append((backup, final))
        elif output_path.exists() or lineage_path.exists():
            raise WhaleGridOutputError(
                "output or lineage already exists; pass overwrite=True to replace both"
            )
        os.replace(temporary_output, output_path)
        committed.append(output_path)
        os.replace(temporary_lineage, lineage_path)
        committed.append(lineage_path)
    except Exception:
        for final in reversed(committed):
            final.unlink(missing_ok=True)
        for backup, final in reversed(backups):
            os.replace(backup, final)
        raise
    else:
        for backup, _final in backups:
            backup.unlink(missing_ok=True)


def _validate_output_target(output_path: Path) -> None:
    resolved = output_path.resolve()
    if resolved == _PROJECT_RAW_ROOT or resolved.is_relative_to(_PROJECT_RAW_ROOT):
        raise WhaleGridOutputError(
            f"whale-grid output cannot be written under raw data: {resolved}"
        )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def write_whale_grid(
    dataset: WhaleGridDataset,
    source: WhaleSourceInspection,
    target_grid: TargetGridInspection,
    output_path: Path,
    *,
    started_at: datetime,
    expected_grid_sha256: str | None = None,
    overwrite: bool = False,
) -> WhaleGridWriteResult:
    """Atomically write the whale-grid GeoParquet and generation lineage."""
    _validate_output_target(output_path)
    if started_at.utcoffset() != UTC.utcoffset(started_at):
        raise WhaleGridOutputError("started_at must be timezone-aware UTC")
    if output_path.suffix.lower() != ".parquet":
        raise WhaleGridOutputError("whale-grid output path must end in .parquet")
    lineage_path = output_path.with_suffix(output_path.suffix + LINEAGE_SUFFIX)
    if not overwrite and (output_path.exists() or lineage_path.exists()):
        raise WhaleGridOutputError(
            "output or lineage already exists; use explicit overwrite authorization"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    temporary_output = output_path.with_name(f".{output_path.name}.{token}.tmp")
    temporary_lineage = lineage_path.with_name(f".{lineage_path.name}.{token}.tmp")
    try:
        pq.write_table(
            _table(dataset),
            temporary_output,
            compression="zstd",
            compression_level=9,
            use_dictionary=False,
            write_statistics=True,
            version="2.6",
            data_page_version="2.0",
            row_group_size=1024,
        )
        output_sha256 = _sha256_file(temporary_output)
        completed_at = _utc_now()
        lineage = _lineage_document(
            dataset=dataset,
            source=source,
            target_grid=target_grid,
            output_path=output_path,
            output_sha256=output_sha256,
            started_at=started_at,
            completed_at=completed_at,
            expected_grid_sha256=expected_grid_sha256,
        )
        _write_json(temporary_lineage, lineage)
        lineage_sha256 = _sha256_file(temporary_lineage)
        _commit_pair(
            temporary_output,
            output_path,
            temporary_lineage,
            lineage_path,
            overwrite=overwrite,
        )
    except WhaleGridError:
        raise
    except Exception as exc:
        raise WhaleGridOutputError(
            f"could not write whale-grid output {output_path}: {exc}"
        ) from exc
    finally:
        temporary_output.unlink(missing_ok=True)
        temporary_lineage.unlink(missing_ok=True)
    return WhaleGridWriteResult(
        output_path=output_path,
        lineage_path=lineage_path,
        output_sha256=output_sha256,
        output_bytes=output_path.stat().st_size,
        lineage_sha256=lineage_sha256,
        dataset=dataset,
    )
