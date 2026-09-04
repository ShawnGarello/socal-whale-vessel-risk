"""Candidate vessel-kilometre aggregation on the exact projected water grid.

This module promotes the segment/filter/allocation logic exercised by the
vessel-activity evidence harness into a bounded multi-day processing boundary.
Every methodological choice needed by this boundary is explicit. The output is
a candidate vessel-activity input; it does not apply the accepted reporting
domain, accept ADR 0018, or calculate exposure or inside/outside statistics.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final, Literal, cast

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pyproj
import shapely
from pyproj import Transformer
from shapely import STRtree, unary_union
from shapely.errors import GEOSException
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis.cleaned_ais_bundle import canonical_json, sha256_file
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
from whale_vessel_analysis.multiday_ais_relation import (
    GLOBAL_ORDER_COLUMNS,
    PeriodRelation,
)
from whale_vessel_analysis.spatial_grid import (
    CELL_ID_PATTERN,
    GEOMETRY_COLUMN,
    GEOPARQUET_VERSION,
    ROW_ORDER,
)
from whale_vessel_analysis.whale_grid import TargetGridInspection

VESSEL_GRID_CONTRACT: Final = "candidate_vessel_grid_v1"
VESSEL_GRID_QUALITY_CONTRACT: Final = "candidate_vessel_grid_quality_v1"
VESSEL_GRID_LINEAGE_CONTRACT: Final = "candidate_vessel_grid_lineage_v1"
VESSEL_GRID_SCHEMA_VERSION: Final = 1
VESSEL_GRID_PROCESSING_VERSION: Final = "1.0.0"
VESSEL_GRID_ID_PREFIX: Final = "candidate-vessel-grid-"
VESSEL_GRID_FILENAME: Final = "vessel-grid.parquet"
QUALITY_REPORT_FILENAME: Final = "quality-report.json"
RUN_METADATA_FILENAME: Final = "run-metadata.json"
VESSEL_GRID_BUNDLE_FILENAMES: Final = (
    VESSEL_GRID_FILENAME,
    QUALITY_REPORT_FILENAME,
    RUN_METADATA_FILENAME,
)
WGS84_CRS: Final = "EPSG:4326"
KNOTS_PER_METRE_PER_SECOND: Final = 1.9438444924406046
LENGTH_TOLERANCE_M: Final = 1e-6
CONSERVATION_RELATIVE_TOLERANCE: Final = 1e-12
VESSEL_GROUPS: Final = ("passenger", "cargo", "tanker")
ALL_COMMERCIAL: Final = "all_commercial"
EDGE_TREATMENT: Final = "censor-at-cleaned-extent"
SUPPORT_TREATMENT: Final = "exact-water-geometry-exclude-and-report"
REQUIRE_READY_PERIOD: Final = "require-ready"
ALLOW_INCOMPLETE_PERIOD: Final = "allow-incomplete-candidate"

_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
_PROJECT_RAW_ROOT: Final = (_PROJECT_ROOT / "data" / "raw").resolve()
_PROJECT_DERIVED_ROOT: Final = (_PROJECT_ROOT / "data" / "derived").resolve()

VesselGroup = Literal["passenger", "cargo", "tanker"]
PeriodReadinessTreatment = Literal["require-ready", "allow-incomplete-candidate"]
EdgeTreatment = Literal["censor-at-cleaned-extent"]
SupportTreatment = Literal["exact-water-geometry-exclude-and-report"]
CandidateExclusionReason = Literal[
    "invalid_coordinate_transform",
    "non_increasing_time",
    "vessel_group_change",
    "maximum_gap",
    "implied_speed",
]


class VesselGridError(ValueError):
    """Raised when candidate vessel-grid input, processing, or output is invalid."""


def candidate_primary_exclusion(
    *,
    coordinate_valid: bool,
    elapsed_seconds: float,
    group_changed: bool,
    implied_speed_knots: float,
    maximum_gap_seconds: float,
    implied_speed_ceiling_knots: float,
) -> CandidateExclusionReason | None:
    """Return the shared primary candidate exclusion in stable precedence order."""
    if not coordinate_valid:
        return "invalid_coordinate_transform"
    if elapsed_seconds <= 0:
        return "non_increasing_time"
    if group_changed:
        return "vessel_group_change"
    if elapsed_seconds > maximum_gap_seconds:
        return "maximum_gap"
    if implied_speed_knots > implied_speed_ceiling_knots:
        return "implied_speed"
    return None


@dataclass(frozen=True, slots=True)
class VesselGridParameters:
    """Explicit candidate methodology; no analytical value has a default."""

    maximum_gap_seconds: float
    implied_speed_ceiling_knots: float
    period_readiness_treatment: PeriodReadinessTreatment
    edge_treatment: EdgeTreatment
    support_treatment: SupportTreatment

    def __post_init__(self) -> None:
        for label, value in (
            ("maximum gap seconds", self.maximum_gap_seconds),
            ("implied-speed ceiling knots", self.implied_speed_ceiling_knots),
        ):
            if not math.isfinite(value) or value <= 0:
                raise VesselGridError(f"{label} must be finite and positive")
        if self.period_readiness_treatment not in (
            REQUIRE_READY_PERIOD,
            ALLOW_INCOMPLETE_PERIOD,
        ):
            raise VesselGridError("period readiness treatment is invalid")
        if self.edge_treatment != EDGE_TREATMENT:
            raise VesselGridError(
                "edge treatment must explicitly retain the current cleaned-extent "
                "censoring"
            )
        if self.support_treatment != SUPPORT_TREATMENT:
            raise VesselGridError(
                "support treatment must explicitly allocate exact water geometry "
                "and exclude/report unsupported portions"
            )

    @property
    def require_ready_period(self) -> bool:
        return self.period_readiness_treatment == REQUIRE_READY_PERIOD

    def to_dict(self) -> dict[str, object]:
        return {
            "maximum_gap_seconds": self.maximum_gap_seconds,
            "implied_speed_ceiling_knots": self.implied_speed_ceiling_knots,
            "period_readiness_treatment": self.period_readiness_treatment,
            "edge_treatment": self.edge_treatment,
            "support_treatment": self.support_treatment,
            "vessel_length_filter": {
                "status": "disabled_unresolved",
                "minimum_length_m": None,
                "reason": (
                    "AIS length is not gross tonnage and no defensible mapping to "
                    "the approximately 300 GT program population is accepted"
                ),
            },
        }


@dataclass(frozen=True, slots=True)
class PeriodInputReference:
    """Stable analytical identity and local lineage for one period manifest."""

    manifest_path: Path
    manifest_sha256: str
    period_input_id: str
    period_input_readiness: Mapping[str, object]
    observational_completeness: Mapping[str, object]

    def stable_dict(self) -> dict[str, object]:
        return {
            "period_input_id": self.period_input_id,
            "period_input_readiness": dict(self.period_input_readiness),
            "observational_completeness": dict(self.observational_completeness),
        }


@dataclass(frozen=True, slots=True)
class VesselGridCell:
    """One exact target cell carrying candidate vessel-activity measures."""

    cell_order: int
    vessel_km: Mapping[str, float]
    distinct_mmsi: Mapping[str, int]
    distinct_mmsi_dates: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class VesselGridDataset:
    """Deterministic candidate grid values and their quality evidence."""

    grid_id: str
    cells: tuple[VesselGridCell, ...]
    target_grid: TargetGridInspection
    period_input: PeriodInputReference
    parameters: VesselGridParameters
    quality: Mapping[str, object]
    configuration_sha256: str
    partitions: tuple[Mapping[str, object], ...]
    partition_paths: tuple[Path, ...]
    batch_size: int


@dataclass(frozen=True, slots=True)
class VesselGridWriteResult:
    """One atomically published candidate bundle."""

    output_directory: Path
    grid_path: Path
    quality_path: Path
    lineage_path: Path
    grid_id: str
    grid_sha256: str
    quality_sha256: str
    lineage_sha256: str
    output_rows: int

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": VESSEL_GRID_CONTRACT,
            "processing_version": VESSEL_GRID_PROCESSING_VERSION,
            "status": "candidate vessel-activity output",
            "grid_id": self.grid_id,
            "output": {
                "directory": str(self.output_directory),
                "grid": {
                    "path": str(self.grid_path),
                    "sha256": self.grid_sha256,
                    "rows": self.output_rows,
                },
                "quality_report": {
                    "path": str(self.quality_path),
                    "sha256": self.quality_sha256,
                },
                "run_metadata": {
                    "path": str(self.lineage_path),
                    "sha256": self.lineage_sha256,
                },
            },
        }


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _round(value: float) -> float:
    return round(value, 12)


def _group_float_values(values: Mapping[str, float]) -> dict[str, float]:
    result = {group: _round(values[group]) for group in VESSEL_GROUPS}
    result[ALL_COMMERCIAL] = _round(math.fsum(values[group] for group in VESSEL_GROUPS))
    return result


def _group_int_values(values: Mapping[str, int]) -> dict[str, int]:
    result = {group: values[group] for group in VESSEL_GROUPS}
    result[ALL_COMMERCIAL] = sum(values[group] for group in VESSEL_GROUPS)
    return result


def _finite_number(value: object, label: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise VesselGridError(f"bounded relation has invalid {label}")
    result = float(value)
    if not math.isfinite(result):
        raise VesselGridError(f"bounded relation has non-finite {label}")
    return result


def _datetime_value(value: object, label: str) -> datetime:
    if isinstance(value, int) and not isinstance(value, bool):
        return datetime.fromtimestamp(value / 1_000_000.0, UTC)
    if isinstance(value, datetime) and value.utcoffset() is not None:
        return value.astimezone(UTC)
    raise VesselGridError(f"bounded relation has invalid {label}")


def _group_value(value: object, label: str) -> VesselGroup:
    if value not in VESSEL_GROUPS:
        raise VesselGridError(f"bounded relation has invalid {label}")
    return value


def _mmsi_value(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise VesselGridError("bounded relation has invalid MMSI")
    return value


def _linear_components(geometry: BaseGeometry) -> list[BaseGeometry]:
    if geometry.is_empty:
        return []
    if geometry.geom_type in {"LineString", "LinearRing"}:
        return [geometry]
    if geometry.geom_type in {"MultiLineString", "GeometryCollection"}:
        components: list[BaseGeometry] = []
        for part in cast(Iterable[BaseGeometry], geometry.geoms):
            components.extend(_linear_components(part))
        return components
    return []


class _Accumulator:
    """Incremental point classification and segment allocation for one grid."""

    def __init__(
        self, target_grid: TargetGridInspection, parameters: VesselGridParameters
    ) -> None:
        if not target_grid.cells:
            raise VesselGridError("target water grid contains no cells")
        self.target_grid = target_grid
        self.parameters = parameters
        self.geometries = [cell.geometry for cell in target_grid.cells]
        self.tree = STRtree(self.geometries)
        self.transformer = Transformer.from_crs(
            WGS84_CRS, PROJECTED_CRS, always_xy=True
        )
        count = len(target_grid.cells)
        self.cell_distance_m = {
            group: [0.0 for _ in range(count)] for group in VESSEL_GROUPS
        }
        self.cell_mmsi = {
            group: [set[str]() for _ in range(count)] for group in VESSEL_GROUPS
        }
        self.cell_mmsi_dates = {
            group: [set[tuple[str, str]]() for _ in range(count)]
            for group in VESSEL_GROUPS
        }
        self.observation_counts: dict[str, int] = defaultdict(int)
        self.outside_observation_counts: dict[str, int] = defaultdict(int)
        self.ambiguous_observation_counts: dict[str, int] = defaultdict(int)
        self.candidate_counts: dict[str, int] = defaultdict(int)
        self.exclusion_counts: dict[str, int] = defaultdict(int)
        self.exclusion_distance_m: dict[str, float] = defaultdict(float)
        self.retained_counts: dict[str, int] = defaultdict(int)
        self.status_counts: dict[str, int] = defaultdict(int)
        self.distance_by_group = {
            group: {
                "parent_m": 0.0,
                "allocated_m": 0.0,
                "outside_support_m": 0.0,
                "ambiguous_boundary_m": 0.0,
                "invalid_geometry_m": 0.0,
            }
            for group in VESSEL_GROUPS
        }
        self.cross_midnight_candidate_count = 0
        self.cross_midnight_retained_count = 0
        self.zero_length_count = 0
        self.maximum_segment_conservation_difference_m = 0.0

    def _xy(self, longitude: float, latitude: float) -> tuple[float, float]:
        x, y = self.transformer.transform(longitude, latitude)
        if not math.isfinite(x) or not math.isfinite(y):
            raise VesselGridError("coordinate transformation produced non-finite xy")
        return float(x), float(y)

    def _matching_cells(self, geometry: BaseGeometry) -> list[int]:
        return [
            index
            for index in sorted(int(value) for value in self.tree.query(geometry))
            if self.geometries[index].covers(geometry)
        ]

    def add_observation(
        self,
        *,
        mmsi: str,
        observed_at_utc: datetime,
        latitude: float,
        longitude: float,
        group: VesselGroup,
    ) -> None:
        self.observation_counts[group] += 1
        point = Point(self._xy(longitude, latitude))
        matching = self._matching_cells(point)
        if not matching:
            self.outside_observation_counts[group] += 1
            return
        if len(matching) > 1:
            self.ambiguous_observation_counts[group] += 1
            return
        cell_order = matching[0]
        self.cell_mmsi[group][cell_order].add(mmsi)
        self.cell_mmsi_dates[group][cell_order].add(
            (mmsi, observed_at_utc.date().isoformat())
        )

    def add_candidate_segment(self, row: Mapping[str, object]) -> None:
        group = _group_value(row.get("vessel_type_group"), "vessel group")
        next_group_value = row.get("next_vessel_type_group")
        self.candidate_counts[group] += 1
        start_time = _datetime_value(row.get("observed_at_utc"), "timestamp")
        end_time = _datetime_value(row.get("next_observed_at_utc"), "next timestamp")
        if start_time.date() != end_time.date():
            self.cross_midnight_candidate_count += 1
        elapsed_seconds = (end_time - start_time).total_seconds()
        try:
            start_xy = self._xy(
                _finite_number(row.get("longitude"), "longitude"),
                _finite_number(row.get("latitude"), "latitude"),
            )
            end_xy = self._xy(
                _finite_number(row.get("next_longitude"), "next longitude"),
                _finite_number(row.get("next_latitude"), "next latitude"),
            )
        except VesselGridError:
            reason = candidate_primary_exclusion(
                coordinate_valid=False,
                elapsed_seconds=elapsed_seconds,
                group_changed=False,
                implied_speed_knots=math.nan,
                maximum_gap_seconds=self.parameters.maximum_gap_seconds,
                implied_speed_ceiling_knots=(
                    self.parameters.implied_speed_ceiling_knots
                ),
            )
            assert reason == "invalid_coordinate_transform"
            self.exclusion_counts[reason] += 1
            return
        parent_distance = math.dist(start_xy, end_xy)
        implied_speed = (
            math.nan
            if elapsed_seconds <= 0
            else parent_distance / elapsed_seconds * KNOTS_PER_METRE_PER_SECOND
        )
        reason = candidate_primary_exclusion(
            coordinate_valid=True,
            elapsed_seconds=elapsed_seconds,
            group_changed=(
                next_group_value not in VESSEL_GROUPS or next_group_value != group
            ),
            implied_speed_knots=implied_speed,
            maximum_gap_seconds=self.parameters.maximum_gap_seconds,
            implied_speed_ceiling_knots=self.parameters.implied_speed_ceiling_knots,
        )
        if reason is not None:
            self._exclude(reason, parent_distance)
            return
        self.retained_counts[group] += 1
        if start_time.date() != end_time.date():
            self.cross_midnight_retained_count += 1
        totals = self.distance_by_group[group]
        totals["parent_m"] += parent_distance
        if parent_distance <= LENGTH_TOLERANCE_M:
            self.zero_length_count += 1
            self._record_zero_length(Point(start_xy))
            return
        self._allocate_positive_segment(
            LineString([start_xy, end_xy]), parent_distance, group
        )

    def _exclude(self, reason: str, distance_m: float) -> None:
        self.exclusion_counts[reason] += 1
        self.exclusion_distance_m[reason] += distance_m

    def _record_zero_length(self, point: Point) -> None:
        matching = self._matching_cells(point)
        if not matching:
            self.status_counts["zero_length_outside_support"] += 1
        elif len(matching) == 1:
            self.status_counts["zero_length_in_support"] += 1
        else:
            self.status_counts["zero_length_ambiguous_boundary"] += 1

    def _allocate_positive_segment(
        self, line: LineString, parent_distance: float, group: VesselGroup
    ) -> None:
        raw_pieces: list[tuple[float, int, float, str, BaseGeometry]] = []
        intersections: list[BaseGeometry] = []
        try:
            for cell_order in sorted(int(value) for value in self.tree.query(line)):
                intersection = cast(
                    BaseGeometry, line.intersection(self.geometries[cell_order])
                )
                for component in _linear_components(intersection):
                    length = float(component.length)
                    if length <= LENGTH_TOLERANCE_M:
                        continue
                    coordinates = list(component.coords)
                    first = float(line.project(Point(coordinates[0])))
                    last = float(line.project(Point(coordinates[-1])))
                    raw_pieces.append(
                        (
                            min(first, last),
                            cell_order,
                            length,
                            component.wkb_hex,
                            component,
                        )
                    )
                    intersections.append(component)
        except GEOSException:
            self.status_counts["invalid_intersection_geometry"] += 1
            self.distance_by_group[group]["invalid_geometry_m"] += parent_distance
            return
        raw_pieces.sort(key=lambda item: item[:4])
        piece_sum = math.fsum(item[2] for item in raw_pieces)
        if not intersections:
            union_length = 0.0
        elif len(intersections) == 1:
            union_length = float(intersections[0].length)
        else:
            union_length = float(unary_union(intersections).length)
        tolerance = max(
            LENGTH_TOLERANCE_M,
            parent_distance * CONSERVATION_RELATIVE_TOLERANCE,
        )
        if union_length > parent_distance + tolerance:
            raise VesselGridError(
                "segment intersection exceeds its parent projected distance"
            )
        outside = max(0.0, parent_distance - union_length)
        totals = self.distance_by_group[group]
        totals["outside_support_m"] += outside
        if not math.isclose(
            piece_sum,
            union_length,
            rel_tol=CONSERVATION_RELATIVE_TOLERANCE,
            abs_tol=tolerance,
        ):
            totals["ambiguous_boundary_m"] += union_length
            self.status_counts["positive_length_ambiguous_boundary"] += 1
            difference = parent_distance - outside - union_length
            self.maximum_segment_conservation_difference_m = max(
                self.maximum_segment_conservation_difference_m, abs(difference)
            )
            return
        for _position, cell_order, length, _wkb, _geometry in raw_pieces:
            self.cell_distance_m[group][cell_order] += length
        totals["allocated_m"] += piece_sum
        if union_length <= LENGTH_TOLERANCE_M:
            self.status_counts["positive_length_outside_support"] += 1
        elif outside <= LENGTH_TOLERANCE_M:
            self.status_counts["positive_length_in_support"] += 1
        else:
            self.status_counts["positive_length_partially_outside_support"] += 1
        difference = parent_distance - piece_sum - outside
        self.maximum_segment_conservation_difference_m = max(
            self.maximum_segment_conservation_difference_m, abs(difference)
        )

    def finish(self) -> tuple[tuple[VesselGridCell, ...], dict[str, object]]:
        cells: list[VesselGridCell] = []
        for cell_order, _target in enumerate(self.target_grid.cells):
            distance_values = {
                group: self.cell_distance_m[group][cell_order] / 1_000.0
                for group in VESSEL_GROUPS
            }
            distinct = {
                group: len(self.cell_mmsi[group][cell_order]) for group in VESSEL_GROUPS
            }
            distinct_dates = {
                group: len(self.cell_mmsi_dates[group][cell_order])
                for group in VESSEL_GROUPS
            }
            union_mmsi = set().union(
                *(self.cell_mmsi[group][cell_order] for group in VESSEL_GROUPS)
            )
            union_dates = set().union(
                *(self.cell_mmsi_dates[group][cell_order] for group in VESSEL_GROUPS)
            )
            distinct[ALL_COMMERCIAL] = len(union_mmsi)
            distinct_dates[ALL_COMMERCIAL] = len(union_dates)
            cells.append(
                VesselGridCell(
                    cell_order=cell_order,
                    vessel_km=_group_float_values(distance_values),
                    distinct_mmsi=distinct,
                    distinct_mmsi_dates=distinct_dates,
                )
            )
        quality = self._quality(cells)
        return tuple(cells), quality

    def _quality(self, cells: list[VesselGridCell]) -> dict[str, object]:
        total_observations = sum(self.observation_counts.values())
        outside_observations = sum(self.outside_observation_counts.values())
        ambiguous_observations = sum(self.ambiguous_observation_counts.values())
        inside_observations = (
            total_observations - outside_observations - ambiguous_observations
        )
        candidate_total = sum(self.candidate_counts.values())
        excluded_total = sum(self.exclusion_counts.values())
        retained_total = sum(self.retained_counts.values())
        if candidate_total != excluded_total + retained_total:
            raise VesselGridError(
                "candidate segment counts do not reconcile with exclusions"
            )
        group_distance: dict[str, object] = {}
        commercial_totals = {
            key: math.fsum(
                self.distance_by_group[group][key] for group in VESSEL_GROUPS
            )
            for key in (
                "parent_m",
                "allocated_m",
                "outside_support_m",
                "ambiguous_boundary_m",
                "invalid_geometry_m",
            )
        }
        for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
            values = (
                commercial_totals
                if group == ALL_COMMERCIAL
                else self.distance_by_group[group]
            )
            difference = values["parent_m"] - math.fsum(
                (
                    values["allocated_m"],
                    values["outside_support_m"],
                    values["ambiguous_boundary_m"],
                    values["invalid_geometry_m"],
                )
            )
            tolerance = max(
                LENGTH_TOLERANCE_M,
                values["parent_m"] * CONSERVATION_RELATIVE_TOLERANCE,
            )
            if not math.isclose(
                difference,
                0.0,
                rel_tol=CONSERVATION_RELATIVE_TOLERANCE,
                abs_tol=tolerance,
            ):
                raise VesselGridError(f"retained distance is not conserved for {group}")
            group_distance[group] = {
                "retained_parent_m": _round(values["parent_m"]),
                "allocated_to_cells_m": _round(values["allocated_m"]),
                "outside_support_m": _round(values["outside_support_m"]),
                "ambiguous_boundary_m": _round(values["ambiguous_boundary_m"]),
                "invalid_geometry_m": _round(values["invalid_geometry_m"]),
                "difference_m": _round(difference),
            }
        output_total_m = math.fsum(
            cell.vessel_km[ALL_COMMERCIAL] * 1_000.0 for cell in cells
        )
        if not math.isclose(
            output_total_m,
            commercial_totals["allocated_m"],
            rel_tol=CONSERVATION_RELATIVE_TOLERANCE,
            abs_tol=max(
                LENGTH_TOLERANCE_M,
                commercial_totals["allocated_m"] * CONSERVATION_RELATIVE_TOLERANCE,
            ),
        ):
            raise VesselGridError(
                "per-cell vessel-kilometres do not reconcile with allocated pieces"
            )
        return {
            "counts": {
                "observations": {
                    "all_commercial": total_observations,
                    "inside_support": inside_observations,
                    "outside_support": _group_int_values(
                        self.outside_observation_counts
                    ),
                    "ambiguous_boundary": _group_int_values(
                        self.ambiguous_observation_counts
                    ),
                },
                "candidate_segments": {
                    **_group_int_values(self.candidate_counts),
                    "retained": retained_total,
                    "excluded": excluded_total,
                    "cross_midnight_candidates": (self.cross_midnight_candidate_count),
                    "cross_midnight_retained": self.cross_midnight_retained_count,
                    "zero_length_retained": self.zero_length_count,
                },
                "primary_exclusions": {
                    key: self.exclusion_counts[key]
                    for key in (
                        "non_increasing_time",
                        "vessel_group_change",
                        "invalid_coordinate_transform",
                        "maximum_gap",
                        "implied_speed",
                    )
                },
                "allocation_status": dict(sorted(self.status_counts.items())),
            },
            "exclusions": {
                "precedence": [
                    "invalid_coordinate_transform",
                    "non_increasing_time",
                    "vessel_group_change",
                    "maximum_gap",
                    "implied_speed",
                ],
                "projected_distance_m_by_reason": {
                    key: _round(value)
                    for key, value in sorted(self.exclusion_distance_m.items())
                },
                "source_point_removals": (
                    "owned by the upstream one-date cleaner and not counted again"
                ),
            },
            "distance_conservation": {
                "passed": True,
                "by_group": group_distance,
                "per_cell_output_total_m": _round(output_total_m),
                "maximum_segment_difference_m": _round(
                    self.maximum_segment_conservation_difference_m
                ),
                "absolute_tolerance_m": LENGTH_TOLERANCE_M,
                "relative_tolerance": CONSERVATION_RELATIVE_TOLERANCE,
                "ambiguous_boundary_treatment": (
                    "positive-length overlap assigned to more than one exact cell "
                    "is excluded from cells and reported as ambiguous distance"
                ),
            },
            "distinct_count_method": (
                "group values use underlying identity sets; all_commercial values "
                "are recomputed from their union and never summed across groups"
            ),
        }


def _identity_material(
    *,
    cells: tuple[VesselGridCell, ...],
    target_grid: TargetGridInspection,
    period_input: PeriodInputReference,
    parameters: VesselGridParameters,
    partitions: tuple[Mapping[str, object], ...],
    quality: Mapping[str, object],
    configuration_sha256: str,
) -> dict[str, object]:
    return {
        "contract": VESSEL_GRID_CONTRACT,
        "schema_version": VESSEL_GRID_SCHEMA_VERSION,
        "processing_version": VESSEL_GRID_PROCESSING_VERSION,
        "period_input": period_input.stable_dict(),
        "partitions": list(partitions),
        "target_grid_sha256": target_grid.sha256,
        "configuration_sha256": configuration_sha256,
        "parameters": parameters.to_dict(),
        "quality": dict(quality),
        "cells": [
            {
                "cell_id": target_grid.cells[cell.cell_order].cell_id,
                "vessel_km": dict(cell.vessel_km),
                "distinct_mmsi": dict(cell.distinct_mmsi),
                "distinct_mmsi_dates": dict(cell.distinct_mmsi_dates),
            }
            for cell in cells
        ],
    }


def aggregate_vessel_grid(
    relation: PeriodRelation,
    target_grid: TargetGridInspection,
    period_input: PeriodInputReference,
    parameters: VesselGridParameters,
    config: ProcessingConfig,
    *,
    batch_size: int,
) -> VesselGridDataset:
    """Stream one bounded relation into a deterministic candidate vessel grid."""
    if batch_size < 1:
        raise VesselGridError("batch size must be at least one")
    accumulator = _Accumulator(target_grid, parameters)
    try:
        reader = relation.adjacent_observation_batches(batch_size)
        for batch in reader:
            rows = cast(list[dict[str, object]], batch.to_pylist())
            for row in rows:
                mmsi = _mmsi_value(row.get("mmsi"))
                observed_at = _datetime_value(row.get("observed_at_utc"), "timestamp")
                latitude = _finite_number(row.get("latitude"), "latitude")
                longitude = _finite_number(row.get("longitude"), "longitude")
                group = _group_value(row.get("vessel_type_group"), "vessel group")
                accumulator.add_observation(
                    mmsi=mmsi,
                    observed_at_utc=observed_at,
                    latitude=latitude,
                    longitude=longitude,
                    group=group,
                )
                if row.get("next_observed_at_utc") is not None:
                    accumulator.add_candidate_segment(row)
    except duckdb.Error as exc:
        raise VesselGridError(
            f"could not scan whole-period consecutive observations: {exc}"
        ) from exc
    cells, core_quality = accumulator.finish()
    partitions = tuple(partition.to_dict() for partition in relation.partitions)
    quality: dict[str, object] = {
        "contract": VESSEL_GRID_QUALITY_CONTRACT,
        "processing_version": VESSEL_GRID_PROCESSING_VERSION,
        "status": "candidate results; methodological parameters are not accepted",
        "input": {
            **period_input.stable_dict(),
            "partition_count": len(partitions),
            "partitions": list(partitions),
            "target_grid": {
                "contract": "projected_water_grid_v1",
                "sha256": target_grid.sha256,
                "cell_count": len(target_grid.cells),
                "analysis_crs": PROJECTED_CRS,
            },
        },
        "parameters": parameters.to_dict(),
        "ordering": {
            "keys": list(GLOBAL_ORDER_COLUMNS),
            "pairing": (
                "whole-period lead per MMSI; UTC date is not a partition boundary"
            ),
        },
        **core_quality,
        "scope_and_limitations": {
            "analytical_domain": (
                "accepted as receivers_50_nautical_miles under ADR 0002; this "
                "candidate vessel grid remains scoped to modeled-whale support "
                "and does not apply the reporting-domain mask"
            ),
            "outside_support": (
                "outside the modeled-whale-support water geometry only; not land "
                "and not an AIS observability classification"
            ),
            "edge_censoring": (
                "the upstream cleaner removed observations outside the map/context "
                "extent; no missing entry or exit path is extrapolated"
            ),
            "observational_completeness": dict(period_input.observational_completeness),
            "not_produced": [
                "relative exposure",
                "inside-versus-outside VSR statistics",
                "exposure layer",
                "application results",
            ],
        },
    }
    identity = _identity_material(
        cells=cells,
        target_grid=target_grid,
        period_input=period_input,
        parameters=parameters,
        partitions=partitions,
        quality=quality,
        configuration_sha256=config.digest(),
    )
    grid_id = (
        VESSEL_GRID_ID_PREFIX
        + hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()[:24]
    )
    quality["grid_id"] = grid_id
    return VesselGridDataset(
        grid_id=grid_id,
        cells=cells,
        target_grid=target_grid,
        period_input=period_input,
        parameters=parameters,
        quality=quality,
        configuration_sha256=config.digest(),
        partitions=partitions,
        partition_paths=tuple(
            partition.cleaned_path for partition in relation.partitions
        ),
        batch_size=batch_size,
    )


def _dataset_metadata(dataset: VesselGridDataset) -> dict[str, object]:
    return {
        "contract": VESSEL_GRID_CONTRACT,
        "schema_version": VESSEL_GRID_SCHEMA_VERSION,
        "processing_version": VESSEL_GRID_PROCESSING_VERSION,
        "status": "candidate vessel activity; parameters are not accepted rules",
        "grid_id": dataset.grid_id,
        "analysis_crs": PROJECTED_CRS,
        "units": {
            "vessel_km": "km travelled during supplied period",
            "vessel_km_per_water_km2": (
                "km travelled per km² modeled-whale-support water geometry"
            ),
            "distinct_mmsi": "unique MMSI observed in exact cell support",
            "distinct_mmsi_dates": (
                "unique MMSI and UTC-date pairs observed in exact cell support"
            ),
        },
        "identity": {
            "row_order": ROW_ORDER,
            "cell_id_pattern": CELL_ID_PATTERN,
            "target_geometry_preserved": True,
        },
        "input": {
            **dataset.period_input.stable_dict(),
            "partitions": list(dataset.partitions),
            "target_grid_sha256": dataset.target_grid.sha256,
            "configuration_sha256": dataset.configuration_sha256,
        },
        "parameters": dataset.parameters.to_dict(),
        "quality": dict(dataset.quality),
    }


def _table(dataset: VesselGridDataset) -> pa.Table:
    targets = dataset.target_grid.cells
    geometry_types = sorted({cell.geometry.geom_type for cell in targets})
    bounds = [
        min(cell.geometry.bounds[0] for cell in targets),
        min(cell.geometry.bounds[1] for cell in targets),
        max(cell.geometry.bounds[2] for cell in targets),
        max(cell.geometry.bounds[3] for cell in targets),
    ]
    geo = {
        "version": GEOPARQUET_VERSION,
        "primary_column": GEOMETRY_COLUMN,
        "columns": {
            GEOMETRY_COLUMN: {
                "encoding": "WKB",
                "geometry_types": geometry_types,
                "crs": pyproj.CRS.from_user_input(PROJECTED_CRS).to_json_dict(),
                "bbox": bounds,
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
    ]
    for prefix, data_type in (
        ("vessel_km", pa.float64()),
        ("vessel_km_per_water_km2", pa.float64()),
        ("distinct_mmsi", pa.int32()),
        ("distinct_mmsi_dates", pa.int32()),
    ):
        for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
            fields.append(pa.field(f"{prefix}_{group}", data_type, nullable=False))
    fields.append(pa.field(GEOMETRY_COLUMN, pa.binary(), nullable=False))
    schema = pa.schema(
        fields,
        metadata={
            b"geo": canonical_json(geo).encode("utf-8"),
            b"whale_vessel_analysis": canonical_json(_dataset_metadata(dataset)).encode(
                "utf-8"
            ),
        },
    )
    arrays: list[pa.Array] = [
        pa.array([cell.cell_id for cell in targets], type=pa.string()),
        pa.array([cell.row_index for cell in targets], type=pa.int16()),
        pa.array([cell.column_index for cell in targets], type=pa.int16()),
        pa.array([cell.x_min_m for cell in targets], type=pa.int32()),
        pa.array([cell.y_min_m for cell in targets], type=pa.int32()),
        pa.array([cell.x_max_m for cell in targets], type=pa.int32()),
        pa.array([cell.y_max_m for cell in targets], type=pa.int32()),
        pa.array([cell.water_area_m2 for cell in targets], type=pa.float64()),
        pa.array([cell.water_area_km2 for cell in targets], type=pa.float64()),
    ]
    for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
        arrays.append(
            pa.array([cell.vessel_km[group] for cell in dataset.cells], pa.float64())
        )
    for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
        arrays.append(
            pa.array(
                [
                    cell.vessel_km[group] / targets[cell.cell_order].water_area_km2
                    for cell in dataset.cells
                ],
                pa.float64(),
            )
        )
    for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
        arrays.append(
            pa.array([cell.distinct_mmsi[group] for cell in dataset.cells], pa.int32())
        )
    for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
        arrays.append(
            pa.array(
                [cell.distinct_mmsi_dates[group] for cell in dataset.cells],
                pa.int32(),
            )
        )
    arrays.append(pa.array([cell.geometry_wkb for cell in targets], pa.binary()))
    return pa.Table.from_arrays(arrays, schema=schema)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(canonical_json(dict(payload)) + "\n")
        output.flush()
        os.fsync(output.fileno())


def _package_version() -> str:
    try:
        return version("socal-whale-vessel-analysis")
    except PackageNotFoundError:
        return "uninstalled"


def _software_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "package": _package_version(),
        "duckdb": duckdb.__version__,
        "pyarrow": pa.__version__,
        "pyproj": pyproj.__version__,
        "proj": pyproj.proj_version_str,
        "shapely": shapely.__version__,
        "geos": shapely.geos_version_string,
    }


def _lineage_document(
    *,
    dataset: VesselGridDataset,
    relation: PeriodRelation,
    grid_path: Path,
    grid_sha256: str,
    quality_path: Path,
    quality_sha256: str,
    started_at: datetime,
    completed_at: datetime,
) -> dict[str, object]:
    inputs = [
        ArtifactReference(
            artifact_id="multi-day-cleaned-ais-manifest",
            locator=str(dataset.period_input.manifest_path),
            sha256=dataset.period_input.manifest_sha256,
        ),
        ArtifactReference(
            artifact_id="projected-water-grid",
            locator=str(dataset.target_grid.path),
            sha256=dataset.target_grid.sha256,
        ),
    ]
    inputs.extend(
        ArtifactReference(
            artifact_id=f"cleaned-ais-{partition['utc_date']}",
            locator=str(partition["local_path"]),
            sha256=cast(str, partition["cleaned_parquet_sha256"]),
        )
        for partition in _partition_lineage(dataset)
    )
    counts = cast(Mapping[str, object], dataset.quality["counts"])
    candidate = cast(Mapping[str, object], counts["candidate_segments"])
    conservation = cast(Mapping[str, object], dataset.quality["distance_conservation"])
    effective_settings = relation.effective_settings()
    run = RunMetadata(
        run_id=dataset.grid_id,
        started_at=started_at,
        completed_at=completed_at,
        configuration_version=CONFIG_SCHEMA_VERSION,
        configuration_sha256=dataset.configuration_sha256,
        steps=(
            ProcessingStep("form-whole-period-consecutive-pairs", "1.0.0"),
            ProcessingStep("apply-explicit-candidate-segment-rules", "1.0.0"),
            ProcessingStep("allocate-distance-to-exact-water-grid", "1.0.0"),
            ProcessingStep("recompute-union-distinct-vessel-counts", "1.0.0"),
            ProcessingStep("write-deterministic-candidate-vessel-grid", "1.0.0"),
        ),
        inputs=tuple(inputs),
        outputs=(
            ArtifactReference(
                artifact_id="candidate-vessel-grid",
                locator=str(grid_path),
                sha256=grid_sha256,
            ),
            ArtifactReference(
                artifact_id="candidate-vessel-grid-quality-report",
                locator=str(quality_path),
                sha256=quality_sha256,
            ),
        ),
        validations=(
            ValidationRecord.from_counts(
                "candidate-segment-accounting",
                True,
                {
                    "candidate_segments": cast(int, candidate[ALL_COMMERCIAL]),
                    "excluded_segments": cast(int, candidate["excluded"]),
                    "retained_segments": cast(int, candidate["retained"]),
                },
            ),
            ValidationRecord.from_counts(
                "distance-conservation",
                conservation.get("passed") is True,
                {"output_cells": len(dataset.cells)},
            ),
        ),
    )
    return {
        "contract": VESSEL_GRID_LINEAGE_CONTRACT,
        "processing_version": VESSEL_GRID_PROCESSING_VERSION,
        "status": "candidate vessel-activity output",
        "method_status": (
            "parameters remain explicit candidate assumptions; ADR 0018 remains "
            "Proposed"
        ),
        "parameters": dataset.parameters.to_dict(),
        "execution_settings": {
            "arrow_batch_size_rows": dataset.batch_size,
            "duckdb": {
                "requested_memory_limit": relation.resources.memory_limit,
                "effective_memory_limit": effective_settings["memory_limit"],
                "requested_threads": relation.resources.threads,
                "effective_threads": effective_settings["threads"],
            },
            "spill_directory": {
                "configured": True,
                "run_isolated": True,
                "location_class": "ignored data/interim",
                "local_path_recorded": False,
            },
            "identity_note": (
                "operational settings and local spill paths do not participate in "
                "candidate analytical identity or deterministic output metadata"
            ),
        },
        "software_versions": _software_versions(),
        "run": run.to_dict(),
        "visual_inspection_status": "not_completed",
    }


def _partition_lineage(dataset: VesselGridDataset) -> list[dict[str, object]]:
    return [
        {
            **dict(item),
            "local_path": str(path),
        }
        for item, path in zip(dataset.partitions, dataset.partition_paths, strict=True)
    ]


def _validate_output_directory(output_directory: Path, overwrite: bool) -> Path:
    resolved = output_directory.resolve()
    if resolved == _PROJECT_RAW_ROOT or resolved.is_relative_to(_PROJECT_RAW_ROOT):
        raise VesselGridError(
            f"candidate vessel-grid output cannot be written under raw data: {resolved}"
        )
    if resolved == _PROJECT_DERIVED_ROOT or not resolved.is_relative_to(
        _PROJECT_DERIVED_ROOT
    ):
        raise VesselGridError(
            "candidate vessel-grid output must be a named bundle beneath ignored "
            "data/derived"
        )
    if resolved.exists() and not resolved.is_dir():
        raise VesselGridError(f"output path is not a directory: {resolved}")
    if resolved.exists() and not overwrite:
        raise VesselGridError(
            "output directory already exists; use explicit overwrite authorization"
        )
    if resolved.exists():
        entries = {item.name for item in resolved.iterdir()}
        if entries != set(VESSEL_GRID_BUNDLE_FILENAMES):
            raise VesselGridError(
                "overwrite only replaces a complete candidate vessel-grid bundle"
            )
        try:
            marker = json.loads(
                (resolved / RUN_METADATA_FILENAME).read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise VesselGridError(
                "existing run metadata is not a readable vessel-grid marker"
            ) from exc
        if marker.get("contract") != VESSEL_GRID_LINEAGE_CONTRACT:
            raise VesselGridError(
                "overwrite only replaces this candidate vessel-grid contract"
            )
    return resolved


def validate_input_output_separation(
    output_directory: Path, input_paths: Iterable[Path]
) -> None:
    """Refuse a bundle that contains, replaces, or is contained by an input."""
    output = output_directory.resolve()
    for input_path in input_paths:
        source = input_path.resolve()
        if (
            source == output
            or source.is_relative_to(output)
            or output.is_relative_to(source)
        ):
            raise VesselGridError(
                f"input and output paths must be separate: {source} and {output}"
            )


def _cleanup_bundle(path: Path) -> None:
    if not path.exists():
        return
    for filename in VESSEL_GRID_BUNDLE_FILENAMES:
        candidate = path / filename
        if candidate.is_file():
            candidate.unlink()
    # Leave anything unexpected in place for inspection. This helper only
    # deletes the three files owned by this contract.
    with suppress(OSError):
        path.rmdir()


def _publish_bundle(temporary: Path, target: Path, overwrite: bool) -> None:
    if not target.exists():
        temporary.rename(target)
        return
    if not overwrite:
        raise VesselGridError(f"output directory already exists: {target}")
    backup = target.with_name(f".{target.name}.previous-{os.getpid()}")
    if backup.exists():
        raise VesselGridError(f"narrow overwrite backup already exists: {backup}")
    target.rename(backup)
    try:
        temporary.rename(target)
    except OSError:
        backup.rename(target)
        raise
    _cleanup_bundle(backup)


def write_vessel_grid(
    dataset: VesselGridDataset,
    output_directory: Path,
    *,
    started_at: datetime,
    relation: PeriodRelation,
    overwrite: bool = False,
) -> VesselGridWriteResult:
    """Write deterministic data/quality plus truthful lineage as one atomic bundle."""
    if started_at.utcoffset() != UTC.utcoffset(started_at):
        raise VesselGridError("started_at must be timezone-aware UTC")
    target = _validate_output_directory(output_directory, overwrite)
    input_paths = [
        dataset.period_input.manifest_path,
        dataset.target_grid.path,
        *(partition.cleaned_path for partition in relation.partitions),
    ]
    validate_input_output_separation(target, input_paths)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.temporary-", dir=target.parent)
    )
    grid_path = temporary / VESSEL_GRID_FILENAME
    quality_path = temporary / QUALITY_REPORT_FILENAME
    lineage_path = temporary / RUN_METADATA_FILENAME
    try:
        pq.write_table(
            _table(dataset),
            grid_path,
            compression="zstd",
            compression_level=9,
            use_dictionary=False,
            write_statistics=True,
            version="2.6",
            data_page_version="2.0",
            row_group_size=1024,
        )
        grid_sha256 = sha256_file(grid_path)
        quality = dict(dataset.quality)
        quality["output"] = {
            "contract": VESSEL_GRID_CONTRACT,
            "grid_id": dataset.grid_id,
            "rows": len(dataset.cells),
            "sha256": grid_sha256,
        }
        _write_json(quality_path, quality)
        quality_sha256 = sha256_file(quality_path)
        completed_at = datetime.now(UTC)
        lineage = _lineage_document(
            dataset=dataset,
            relation=relation,
            grid_path=target / VESSEL_GRID_FILENAME,
            grid_sha256=grid_sha256,
            quality_path=target / QUALITY_REPORT_FILENAME,
            quality_sha256=quality_sha256,
            started_at=started_at,
            completed_at=completed_at,
        )
        _write_json(lineage_path, lineage)
        lineage_sha256 = sha256_file(lineage_path)
        _publish_bundle(temporary, target, overwrite)
    except VesselGridError:
        raise
    except Exception as exc:
        raise VesselGridError(
            f"could not atomically write candidate vessel-grid bundle: {exc}"
        ) from exc
    finally:
        _cleanup_bundle(temporary)
    return VesselGridWriteResult(
        output_directory=target,
        grid_path=target / VESSEL_GRID_FILENAME,
        quality_path=target / QUALITY_REPORT_FILENAME,
        lineage_path=target / RUN_METADATA_FILENAME,
        grid_id=dataset.grid_id,
        grid_sha256=grid_sha256,
        quality_sha256=quality_sha256,
        lineage_sha256=lineage_sha256,
        output_rows=len(dataset.cells),
    )
