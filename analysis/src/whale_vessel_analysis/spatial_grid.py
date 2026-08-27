"""Deterministic construction of the projected per-cell water grid."""

from __future__ import annotations

import hashlib
import json
import math
import os
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
from pyogrio.errors import DataLayerError, DataSourceError, GeometryError
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError
from shapely import (
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
    AnalysisGrid,
    ProcessingConfig,
)
from whale_vessel_analysis.lineage import (
    ArtifactReference,
    ProcessingStep,
    RunMetadata,
    ValidationRecord,
)

GRID_DATASET_SCHEMA_VERSION: Final = 1
GRID_PROCESSING_VERSION: Final = "1.0.0"
GEOPARQUET_VERSION: Final = "1.1.0"
CELL_ID_PATTERN: Final = "r{row:03d}_c{column:03d}"
ROW_ORDER: Final = "row-major: south-to-north rows, west-to-east columns"
DRY_CELL_BEHAVIOR: Final = "omitted"
AREA_TOLERANCE_M2: Final = 0.1
GEOMETRY_COLUMN: Final = "geometry"
LINEAGE_SUFFIX: Final = ".lineage.json"


class SpatialGridError(ValueError):
    """Raised when a water-grid input or output violates its contract."""


class WaterMaskValidationError(SpatialGridError):
    """Raised when a supplied water mask cannot be used safely."""


class SpatialOutputError(SpatialGridError):
    """Raised when a grid output cannot be written atomically."""


@dataclass(frozen=True, slots=True)
class MaskInspection:
    """Validated mask geometry and the source facts needed for lineage."""

    geometry: BaseGeometry
    path: Path
    layer: str | None
    source_crs: str
    source_sha256: str
    feature_count: int
    null_geometry_count: int
    empty_geometry_count: int
    invalid_geometry_count: int
    non_finite_geometry_count: int


@dataclass(frozen=True, slots=True)
class WaterGridCell:
    """One retained analysis cell containing actual intersected water geometry."""

    cell_id: str
    row_index: int
    column_index: int
    x_min_m: int
    y_min_m: int
    x_max_m: int
    y_max_m: int
    water_area_m2: float
    geometry: BaseGeometry

    @property
    def water_area_km2(self) -> float:
        return self.water_area_m2 / 1_000_000.0

    @property
    def geometry_wkb(self) -> bytes:
        return cast(
            bytes,
            to_wkb(
                self.geometry,
                hex=False,
                output_dimension=2,
                byte_order=1,
                include_srid=False,
                flavor="iso",
            ),
        )


@dataclass(frozen=True, slots=True)
class WaterGridDataset:
    """In-memory deterministic water-grid dataset and validation summary."""

    cells: tuple[WaterGridCell, ...]
    grid: AnalysisGrid
    source_crs: str
    source_sha256: str
    configuration_sha256: str
    transformation: str
    mask_feature_count: int
    mask_intersection_area_m2: float

    @property
    def nominal_cell_count(self) -> int:
        return self.grid.rows * self.grid.columns

    @property
    def retained_water_cell_count(self) -> int:
        return len(self.cells)

    @property
    def dry_cell_count(self) -> int:
        return self.nominal_cell_count - self.retained_water_cell_count

    @property
    def total_water_area_m2(self) -> float:
        return math.fsum(cell.water_area_m2 for cell in self.cells)

    @property
    def total_water_area_km2(self) -> float:
        return self.total_water_area_m2 / 1_000_000.0

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        if not self.cells:
            raise SpatialGridError("water-grid dataset contains no retained cells")
        return (
            min(cell.geometry.bounds[0] for cell in self.cells),
            min(cell.geometry.bounds[1] for cell in self.cells),
            max(cell.geometry.bounds[2] for cell in self.cells),
            max(cell.geometry.bounds[3] for cell in self.cells),
        )

    def summary(self) -> dict[str, object]:
        return {
            "schema_version": GRID_DATASET_SCHEMA_VERSION,
            "crs": PROJECTED_CRS,
            "grid_bounds_m": list(self.grid_bounds),
            "cell_size_m": self.grid.cell_size_m,
            "rows": self.grid.rows,
            "columns": self.grid.columns,
            "nominal_cell_count": self.nominal_cell_count,
            "retained_water_cell_count": self.retained_water_cell_count,
            "dry_cell_count": self.dry_cell_count,
            "total_water_area_m2": self.total_water_area_m2,
            "total_water_area_km2": self.total_water_area_km2,
            "mask_grid_intersection_area_m2": self.mask_intersection_area_m2,
            "output_bounds_m": list(self.bounds),
            "row_order": ROW_ORDER,
            "cell_id_pattern": CELL_ID_PATTERN,
            "dry_cell_behavior": DRY_CELL_BEHAVIOR,
        }

    @property
    def grid_bounds(self) -> tuple[int, int, int, int]:
        return (
            self.grid.x_min_m,
            self.grid.y_min_m,
            self.grid.x_max_m,
            self.grid.y_max_m,
        )


@dataclass(frozen=True, slots=True)
class WaterGridWriteResult:
    """Paths and checksums emitted by one completed grid write."""

    output_path: Path
    lineage_path: Path
    output_sha256: str
    output_bytes: int
    lineage_sha256: str
    dataset: WaterGridDataset

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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    """Hash one file or a directory tree in stable relative-path order."""
    if path.is_file():
        return _sha256_file(path)
    if not path.is_dir():
        raise WaterMaskValidationError(f"water-mask input does not exist: {path}")
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        raise WaterMaskValidationError(
            f"water-mask directory contains no files: {path}"
        )
    digest = hashlib.sha256(b"directory-tree-sha256-v1\0")
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(item.stat().st_size.to_bytes(8, "big"))
        with item.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _parse_crs(value: object, label: str) -> CRS:
    if value is None or not str(value).strip():
        raise WaterMaskValidationError(f"{label} CRS is missing")
    try:
        return CRS.from_user_input(value)
    except CRSError as exc:
        raise WaterMaskValidationError(f"{label} CRS is invalid: {value}") from exc


def _geometry_is_finite(geometry: BaseGeometry) -> bool:
    coordinates = get_coordinates(geometry, include_z=False)
    return bool(
        coordinates.size
        and all(math.isfinite(float(value)) for value in coordinates.flat)
    )


def _validate_polygon(geometry: BaseGeometry, label: str) -> None:
    if geometry.is_empty:
        raise WaterMaskValidationError(f"{label} geometry is empty")
    if not _geometry_is_finite(geometry):
        raise WaterMaskValidationError(f"{label} geometry has non-finite coordinates")
    if not geometry.is_valid:
        raise WaterMaskValidationError(f"{label} geometry is invalid")
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise WaterMaskValidationError(
            f"{label} geometry must be Polygon or MultiPolygon, "
            f"received {geometry.geom_type}"
        )


def load_water_mask(
    path: Path, *, layer: str | None, declared_source_crs: str
) -> MaskInspection:
    """Read and validate every polygon in an explicitly supplied mask layer."""
    if not path.exists():
        raise WaterMaskValidationError(f"water-mask input does not exist: {path}")
    declared = _parse_crs(declared_source_crs, "declared source")
    try:
        info = cast(dict[str, object], pyogrio.read_info(path, layer=layer))
        embedded = _parse_crs(info.get("crs"), "embedded water-mask")
        if not embedded.equals(declared):
            raise WaterMaskValidationError(
                "declared source CRS does not match embedded water-mask CRS: "
                f"declared {declared.to_string()}, embedded {embedded.to_string()}"
            )
        metadata, raw_table = pyogrio.read_arrow(
            path,
            layer=layer,
            columns=[],
            read_geometry=True,
        )
    except WaterMaskValidationError:
        raise
    except (DataLayerError, DataSourceError, GeometryError) as exc:
        raise WaterMaskValidationError(
            f"could not read water-mask input {path}: {exc}"
        ) from exc
    table = cast(pa.Table, raw_table)
    geometry_name = str(metadata.get("geometry_name", ""))
    if not geometry_name or geometry_name not in table.column_names:
        raise WaterMaskValidationError(
            f"water-mask input {path} did not provide a WKB geometry column"
        )
    values = cast(Sequence[bytes | None], table[geometry_name].to_pylist())
    if not values:
        raise WaterMaskValidationError("water-mask layer contains no features")
    reported_feature_count = int(cast(int, info["features"]))
    if reported_feature_count >= 0 and reported_feature_count != len(values):
        raise WaterMaskValidationError(
            "water-mask feature count differs between metadata and geometry read: "
            f"metadata={reported_feature_count}, geometry={len(values)}"
        )

    geometries: list[BaseGeometry] = []
    null_count = 0
    empty_count = 0
    invalid_count = 0
    non_finite_count = 0
    non_polygon_types: set[str] = set()
    for value in values:
        if value is None:
            null_count += 1
            continue
        try:
            geometry = cast(BaseGeometry, from_wkb(value))
        except GEOSException:
            invalid_count += 1
            continue
        if geometry.is_empty:
            empty_count += 1
        if not geometry.is_valid:
            invalid_count += 1
        if not _geometry_is_finite(geometry):
            non_finite_count += 1
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            non_polygon_types.add(geometry.geom_type)
        geometries.append(geometry)

    failures = {
        "null": null_count,
        "empty": empty_count,
        "invalid": invalid_count,
        "non-finite": non_finite_count,
    }
    if any(failures.values()):
        detail = ", ".join(f"{name}={count}" for name, count in failures.items())
        raise WaterMaskValidationError(
            f"water-mask geometry validation failed: {detail}"
        )
    if non_polygon_types:
        raise WaterMaskValidationError(
            "water-mask layer contains non-polygon geometry type(s): "
            + ", ".join(sorted(non_polygon_types))
        )
    try:
        unioned = cast(BaseGeometry, unary_union(geometries))
    except GEOSException as exc:
        raise WaterMaskValidationError(
            "water-mask polygon union could not be constructed"
        ) from exc
    _validate_polygon(unioned, "unioned water-mask")
    return MaskInspection(
        geometry=unioned,
        path=path,
        layer=layer,
        source_crs=declared.to_string(),
        source_sha256=sha256_path(path),
        feature_count=len(values),
        null_geometry_count=null_count,
        empty_geometry_count=empty_count,
        invalid_geometry_count=invalid_count,
        non_finite_geometry_count=non_finite_count,
    )


def _polygonal_parts(geometry: BaseGeometry) -> Iterable[Polygon]:
    if isinstance(geometry, Polygon):
        yield geometry
    elif isinstance(geometry, MultiPolygon | GeometryCollection):
        for part in geometry.geoms:
            yield from _polygonal_parts(cast(BaseGeometry, part))


def _polygonal_only(geometry: BaseGeometry) -> BaseGeometry:
    parts = tuple(_polygonal_parts(geometry))
    if not parts:
        return Polygon()
    combined = parts[0] if len(parts) == 1 else unary_union(parts)
    return cast(BaseGeometry, normalize(combined))


def reproject_mask(geometry: BaseGeometry, source_crs: str) -> tuple[BaseGeometry, str]:
    """Reproject a validated mask to EPSG:3310 with explicit x/y ordering."""
    _validate_polygon(geometry, "source water-mask")
    source = _parse_crs(source_crs, "source")
    target = CRS.from_user_input(PROJECTED_CRS)
    transformer = Transformer.from_crs(source, target, always_xy=True)
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
        raise WaterMaskValidationError(
            "could not transform water mask from "
            f"{source.to_string()} to {PROJECTED_CRS}"
        ) from exc
    _validate_polygon(projected, "projected water-mask")
    definition = transformer.definition
    if not definition or definition == "unavailable until proj_trans is called":
        definition = transformer.to_json()
    return projected, definition


def _cell_id(row_index: int, column_index: int) -> str:
    return CELL_ID_PATTERN.format(row=row_index, column=column_index)


def construct_water_grid(
    mask_geometry: BaseGeometry,
    *,
    source_crs: str,
    source_sha256: str,
    mask_feature_count: int,
    config: ProcessingConfig,
) -> WaterGridDataset:
    """Intersect the configured exact grid with a validated water mask."""
    projected_mask, transformation = reproject_mask(mask_geometry, source_crs)
    grid = config.spatial.grid
    grid_extent = box(grid.x_min_m, grid.y_min_m, grid.x_max_m, grid.y_max_m)
    clipped_mask = _polygonal_only(projected_mask.intersection(grid_extent))
    if clipped_mask.is_empty or clipped_mask.area <= 0:
        raise WaterMaskValidationError(
            "projected water mask does not intersect the configured analysis grid"
        )
    _validate_polygon(clipped_mask, "grid-clipped water-mask")

    nominal_area_m2 = float(grid.cell_size_m * grid.cell_size_m)
    cells: list[WaterGridCell] = []
    for row_index in range(grid.rows):
        y_min = grid.y_min_m + row_index * grid.cell_size_m
        y_max = y_min + grid.cell_size_m
        for column_index in range(grid.columns):
            x_min = grid.x_min_m + column_index * grid.cell_size_m
            x_max = x_min + grid.cell_size_m
            parent = box(x_min, y_min, x_max, y_max)
            water = _polygonal_only(parent.intersection(clipped_mask))
            if water.is_empty or water.area <= 0:
                continue
            _validate_polygon(water, f"water cell {_cell_id(row_index, column_index)}")
            area_m2 = float(water.area)
            if area_m2 > nominal_area_m2 + AREA_TOLERANCE_M2:
                raise SpatialGridError(
                    "water area exceeds parent cell for "
                    f"{_cell_id(row_index, column_index)}"
                )
            if not parent.covers(water):
                outside_area = float(water.difference(parent).area)
                if outside_area > AREA_TOLERANCE_M2:
                    raise SpatialGridError(
                        "water geometry lies outside its parent cell for "
                        f"{_cell_id(row_index, column_index)}"
                    )
            cells.append(
                WaterGridCell(
                    cell_id=_cell_id(row_index, column_index),
                    row_index=row_index,
                    column_index=column_index,
                    x_min_m=x_min,
                    y_min_m=y_min,
                    x_max_m=x_max,
                    y_max_m=y_max,
                    water_area_m2=area_m2,
                    geometry=water,
                )
            )

    if not cells:
        raise WaterMaskValidationError("water mask produced no retained water cells")
    expected_order = sorted(cells, key=lambda cell: (cell.row_index, cell.column_index))
    if cells != expected_order:
        raise SpatialGridError("water-grid cells are not in documented row-major order")
    aggregate_area = math.fsum(cell.water_area_m2 for cell in cells)
    mask_intersection_area = float(clipped_mask.area)
    if not math.isclose(
        aggregate_area,
        mask_intersection_area,
        rel_tol=1e-12,
        abs_tol=AREA_TOLERANCE_M2,
    ):
        raise SpatialGridError(
            "aggregate cell water area does not conserve the mask/grid intersection: "
            f"cells={aggregate_area}, mask={mask_intersection_area}"
        )
    return WaterGridDataset(
        cells=tuple(cells),
        grid=grid,
        source_crs=_parse_crs(source_crs, "source").to_string(),
        source_sha256=source_sha256,
        configuration_sha256=config.digest(),
        transformation=transformation,
        mask_feature_count=mask_feature_count,
        mask_intersection_area_m2=mask_intersection_area,
    )


def build_water_grid(
    mask: MaskInspection, config: ProcessingConfig
) -> WaterGridDataset:
    """Build a water grid from a previously inspected mask artifact."""
    return construct_water_grid(
        mask.geometry,
        source_crs=mask.source_crs,
        source_sha256=mask.source_sha256,
        mask_feature_count=mask.feature_count,
        config=config,
    )


def _canonical_json(value: Mapping[str, object]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _dataset_metadata(dataset: WaterGridDataset) -> dict[str, object]:
    return {
        "contract": "projected_water_grid_v1",
        "schema_version": GRID_DATASET_SCHEMA_VERSION,
        "analysis_crs": PROJECTED_CRS,
        "grid": {
            "bounds_m": list(dataset.grid_bounds),
            "cell_size_m": dataset.grid.cell_size_m,
            "rows": dataset.grid.rows,
            "columns": dataset.grid.columns,
            "nominal_cell_count": dataset.nominal_cell_count,
        },
        "output": {
            "retained_water_cell_count": dataset.retained_water_cell_count,
            "dry_cell_count": dataset.dry_cell_count,
            "dry_cell_behavior": DRY_CELL_BEHAVIOR,
            "row_order": ROW_ORDER,
            "cell_id_pattern": CELL_ID_PATTERN,
            "total_water_area_m2": dataset.total_water_area_m2,
            "total_water_area_km2": dataset.total_water_area_km2,
        },
        "source": {
            "sha256": dataset.source_sha256,
            "crs": dataset.source_crs,
            "feature_count": dataset.mask_feature_count,
        },
        "configuration": {
            "version": CONFIG_SCHEMA_VERSION,
            "sha256": dataset.configuration_sha256,
        },
        "transformation": {
            "source_crs": dataset.source_crs,
            "target_crs": PROJECTED_CRS,
            "always_xy": True,
            "definition": dataset.transformation,
        },
    }


def _table(dataset: WaterGridDataset) -> pa.Table:
    geometries = [cell.geometry_wkb for cell in dataset.cells]
    geometry_types = sorted({cell.geometry.geom_type for cell in dataset.cells})
    geo_metadata: dict[str, object] = {
        "version": GEOPARQUET_VERSION,
        "primary_column": GEOMETRY_COLUMN,
        "columns": {
            GEOMETRY_COLUMN: {
                "encoding": "WKB",
                "geometry_types": geometry_types,
                "crs": CRS.from_user_input(PROJECTED_CRS).to_json_dict(),
                "bbox": list(dataset.bounds),
            }
        },
    }
    schema = pa.schema(
        [
            pa.field("cell_id", pa.string(), nullable=False),
            pa.field("row_index", pa.int16(), nullable=False),
            pa.field("column_index", pa.int16(), nullable=False),
            pa.field("cell_x_min_m", pa.int32(), nullable=False),
            pa.field("cell_y_min_m", pa.int32(), nullable=False),
            pa.field("cell_x_max_m", pa.int32(), nullable=False),
            pa.field("cell_y_max_m", pa.int32(), nullable=False),
            pa.field("water_area_m2", pa.float64(), nullable=False),
            pa.field("water_area_km2", pa.float64(), nullable=False),
            pa.field(GEOMETRY_COLUMN, pa.binary(), nullable=False),
        ],
        metadata={
            b"geo": _canonical_json(geo_metadata).encode("utf-8"),
            b"whale_vessel_analysis": _canonical_json(
                _dataset_metadata(dataset)
            ).encode("utf-8"),
        },
    )
    columns: list[pa.Array] = [
        pa.array([cell.cell_id for cell in dataset.cells], type=pa.string()),
        pa.array([cell.row_index for cell in dataset.cells], type=pa.int16()),
        pa.array([cell.column_index for cell in dataset.cells], type=pa.int16()),
        pa.array([cell.x_min_m for cell in dataset.cells], type=pa.int32()),
        pa.array([cell.y_min_m for cell in dataset.cells], type=pa.int32()),
        pa.array([cell.x_max_m for cell in dataset.cells], type=pa.int32()),
        pa.array([cell.y_max_m for cell in dataset.cells], type=pa.int32()),
        pa.array([cell.water_area_m2 for cell in dataset.cells], type=pa.float64()),
        pa.array([cell.water_area_km2 for cell in dataset.cells], type=pa.float64()),
        pa.array(geometries, type=pa.binary()),
    ]
    return pa.Table.from_arrays(columns, schema=schema)


def _lineage_document(
    *,
    dataset: WaterGridDataset,
    mask: MaskInspection,
    output_path: Path,
    output_sha256: str,
    run_at: datetime,
    visual_inspection_status: str,
) -> dict[str, object]:
    if run_at.utcoffset() != UTC.utcoffset(run_at):
        raise SpatialOutputError("run_at must be timezone-aware UTC")
    run_key = hashlib.sha256(
        (dataset.source_sha256 + dataset.configuration_sha256).encode("ascii")
    ).hexdigest()[:20]
    metadata = RunMetadata(
        run_id=f"water-grid-{run_key}",
        started_at=run_at,
        completed_at=run_at,
        configuration_version=CONFIG_SCHEMA_VERSION,
        configuration_sha256=dataset.configuration_sha256,
        steps=(
            ProcessingStep("validate-water-mask", GRID_PROCESSING_VERSION),
            ProcessingStep("reproject-water-mask", GRID_PROCESSING_VERSION),
            ProcessingStep("intersect-analysis-grid", GRID_PROCESSING_VERSION),
            ProcessingStep("write-geoparquet", GRID_PROCESSING_VERSION),
        ),
        inputs=(
            ArtifactReference(
                artifact_id="water-mask",
                locator=mask.path.as_posix(),
                sha256=mask.source_sha256,
            ),
        ),
        outputs=(
            ArtifactReference(
                artifact_id="projected-water-grid",
                locator=output_path.as_posix(),
                sha256=output_sha256,
            ),
        ),
        validations=(
            ValidationRecord.from_counts(
                "water-mask-geometry",
                True,
                {
                    "empty_geometry_count": mask.empty_geometry_count,
                    "feature_count": mask.feature_count,
                    "invalid_geometry_count": mask.invalid_geometry_count,
                    "non_finite_geometry_count": mask.non_finite_geometry_count,
                    "null_geometry_count": mask.null_geometry_count,
                },
            ),
            ValidationRecord.from_counts(
                "projected-water-grid",
                True,
                {
                    "dry_cell_count": dataset.dry_cell_count,
                    "nominal_cell_count": dataset.nominal_cell_count,
                    "retained_water_cell_count": dataset.retained_water_cell_count,
                },
            ),
        ),
    )
    return {
        "contract": "projected_water_grid_lineage_v1",
        "dataset": _dataset_metadata(dataset),
        "run": metadata.to_dict(),
        "source": {
            "path": mask.path.as_posix(),
            "layer": mask.layer,
            "sha256": mask.source_sha256,
            "checksum_method": (
                "SHA-256 of file bytes"
                if mask.path.is_file()
                else "directory-tree-sha256-v1"
            ),
        },
        "output": {
            "path": output_path.as_posix(),
            "sha256": output_sha256,
        },
        "visual_inspection_status": visual_inspection_status,
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
            raise SpatialOutputError(
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


def write_water_grid(
    dataset: WaterGridDataset,
    mask: MaskInspection,
    output_path: Path,
    *,
    overwrite: bool = False,
    run_at: datetime | None = None,
    visual_inspection_status: str = "not_completed",
) -> WaterGridWriteResult:
    """Atomically write deterministic GeoParquet and its lineage sidecar."""
    if output_path.suffix.lower() != ".parquet":
        raise SpatialOutputError("water-grid output path must end in .parquet")
    if not visual_inspection_status.strip():
        raise SpatialOutputError("visual_inspection_status cannot be blank")
    lineage_path = output_path.with_suffix(output_path.suffix + LINEAGE_SUFFIX)
    if not overwrite and (output_path.exists() or lineage_path.exists()):
        raise SpatialOutputError(
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
        lineage = _lineage_document(
            dataset=dataset,
            mask=mask,
            output_path=output_path,
            output_sha256=output_sha256,
            run_at=datetime.now(UTC) if run_at is None else run_at,
            visual_inspection_status=visual_inspection_status,
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
    except SpatialGridError:
        raise
    except Exception as exc:
        raise SpatialOutputError(
            f"could not write water-grid output {output_path}: {exc}"
        ) from exc
    finally:
        temporary_output.unlink(missing_ok=True)
        temporary_lineage.unlink(missing_ok=True)
    return WaterGridWriteResult(
        output_path=output_path,
        lineage_path=lineage_path,
        output_sha256=output_sha256,
        output_bytes=output_path.stat().st_size,
        lineage_sha256=lineage_sha256,
        dataset=dataset,
    )
