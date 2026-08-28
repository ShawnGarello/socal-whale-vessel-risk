"""Read-only vessel-activity diagnostics for one cleaned AIS bundle.

This module is an evidence harness, not the production vessel-grid process. It
constructs deterministic consecutive-observation candidates and reports the
effects of only those candidate values supplied explicitly by the caller.
"""

from __future__ import annotations

import hashlib
import math
import os
import uuid
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, cast

import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import Geod, Transformer
from shapely import STRtree, unary_union
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis.ais_processing import (
    AIS_PROCESSING_CONTRACT,
    CLEANED_FILENAME,
)
from whale_vessel_analysis.cleaned_ais_bundle import (
    CLEANED_BUNDLE_FILENAMES,
    CLEANED_COLUMNS,
    CleanedAISBundleError,
    canonical_json,
    read_json_object,
    require_mapping,
    sha256_file,
    validate_bundle_layout,
    validate_bundle_sidecars,
    validate_cleaned_schema,
)
from whale_vessel_analysis.config import PROJECTED_CRS, ProcessingConfig
from whale_vessel_analysis.whale_grid import TargetGridInspection, load_target_grid

EVIDENCE_REPORT_CONTRACT: Final = "vessel_activity_evidence_v2"
EVIDENCE_PROCESSING_VERSION: Final = "2.0.0"
WGS84_CRS: Final = "EPSG:4326"
KNOTS_PER_METRE_PER_SECOND: Final = 1.9438444924406046
LENGTH_TOLERANCE_M: Final = 1e-6
TIME_TOLERANCE_SECONDS: Final = 1e-9
CONSERVATION_RELATIVE_TOLERANCE: Final = 1e-12
VESSEL_GROUPS: Final = ("passenger", "cargo", "tanker")
ALL_COMMERCIAL: Final = "all_commercial"
_EXPECTED_COLUMNS: Final = CLEANED_COLUMNS
_BUNDLE_FILES: Final = CLEANED_BUNDLE_FILENAMES
_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
_PROJECT_RAW_ROOT: Final = (_PROJECT_ROOT / "data" / "raw").resolve()
_PROJECT_INTERIM_ROOT: Final = (_PROJECT_ROOT / "data" / "interim").resolve()

VesselGroup = Literal["passenger", "cargo", "tanker"]
AllocationStatus = Literal[
    "positive_length_in_support",
    "positive_length_partially_outside_support",
    "positive_length_outside_support",
    "zero_length_in_support",
    "zero_length_outside_support",
    "zero_length_ambiguous",
]
ALLOCATION_STATUSES: Final[tuple[AllocationStatus, ...]] = (
    "positive_length_in_support",
    "positive_length_partially_outside_support",
    "positive_length_outside_support",
    "zero_length_in_support",
    "zero_length_outside_support",
    "zero_length_ambiguous",
)


class VesselActivityEvidenceError(ValueError):
    """Raised when evidence input, processing, or output is invalid."""


@contextmanager
def _shared_bundle_errors() -> Iterator[None]:
    """Present shared cleaned-bundle failures under this module's error type."""
    try:
        yield
    except CleanedAISBundleError as exc:
        raise VesselActivityEvidenceError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class Observation:
    """One validated cleaned AIS observation."""

    mmsi: str
    observed_at_utc: datetime
    latitude: float
    longitude: float
    sog_knots: float | None
    vessel_type_code: int
    vessel_type_group: VesselGroup
    length_m: float | None

    @property
    def utc_date(self) -> str:
        return self.observed_at_utc.date().isoformat()


@dataclass(frozen=True, slots=True)
class CandidateSegment:
    """One deterministic consecutive-observation pair."""

    sequence: int
    start: Observation
    end: Observation
    elapsed_seconds: float
    projected_distance_m: float
    geodesic_distance_m: float
    implied_speed_knots: float | None
    start_xy_m: tuple[float, float]
    end_xy_m: tuple[float, float]

    @property
    def group_changed(self) -> bool:
        return self.start.vessel_type_group != self.end.vessel_type_group

    @property
    def strictly_increasing(self) -> bool:
        return self.elapsed_seconds > 0

    @property
    def structurally_eligible(self) -> bool:
        return self.strictly_increasing and not self.group_changed


@dataclass(frozen=True, slots=True)
class CandidateScenarioEvaluation:
    """One explicitly supplied candidate-rule combination and retained segments."""

    scenario_id: str
    maximum_gap_seconds: float | None
    implied_speed_ceiling_knots: float | None
    minimum_vessel_length_m: float | None
    retained_segments: tuple[CandidateSegment, ...]
    primary_exclusion_counts: tuple[tuple[str, int], ...]

    def rules(self) -> dict[str, float | None]:
        return {
            "candidate_maximum_gap_seconds": self.maximum_gap_seconds,
            "candidate_implied_speed_ceiling_knots": (self.implied_speed_ceiling_knots),
            "candidate_minimum_vessel_length_m": self.minimum_vessel_length_m,
        }


@dataclass(frozen=True, slots=True)
class CandidateSensitivityEvaluation:
    """Normalized candidate inputs, baseline, and all explicit combinations."""

    maximum_gap_seconds: tuple[float, ...]
    implied_speed_ceiling_knots: tuple[float, ...]
    minimum_vessel_length_m: tuple[float, ...]
    structural_baseline: tuple[CandidateSegment, ...]
    scenarios: tuple[CandidateScenarioEvaluation, ...]


@dataclass(frozen=True, slots=True)
class SegmentPiece:
    """One stable in-support piece of a structural parent segment."""

    parent_segment_id: str
    parent_sequence: int
    vessel_group: VesselGroup
    parent_elapsed_seconds: float
    parent_projected_distance_m: float
    cell_id: str
    cell_order: int
    piece_order: int
    piece_distance_m: float
    piece_elapsed_seconds: float
    zero_length: bool


@dataclass(frozen=True, slots=True)
class SegmentPieceAllocation:
    """One structural segment and all of its cached grid-allocation evidence."""

    segment: CandidateSegment
    segment_id: str
    pieces: tuple[SegmentPiece, ...]
    inside_support_distance_m: float
    outside_support_distance_m: float
    inside_support_elapsed_seconds: float
    outside_support_elapsed_seconds: float
    unallocated_elapsed_seconds: float
    status: AllocationStatus


@dataclass(frozen=True, slots=True)
class SegmentPieceCache:
    """Reusable exact intersections for the unfiltered structural population."""

    target_grid: TargetGridInspection
    allocations: tuple[SegmentPieceAllocation, ...]


@dataclass(frozen=True, slots=True)
class CleanedBundleInspection:
    """Validated cleaner bundle and its deterministic observations."""

    bundle_path: Path
    cleaned_path: Path
    cleaned_sha256: str
    cleaner_run_id: str
    temporal_coverage: Mapping[str, object]
    observations: tuple[Observation, ...]


@dataclass(frozen=True, slots=True)
class EvidenceRunResult:
    """One completed report write plus nondeterministic execution facts."""

    report_path: Path
    report_sha256: str
    report_id: str
    started_at: datetime
    completed_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "report": {
                "path": str(self.report_path),
                "sha256": self.report_sha256,
                "report_id": self.report_id,
            },
            "execution": {
                "started_at": _timestamp(self.started_at),
                "completed_at": _timestamp(self.completed_at),
                "elapsed_seconds": round(
                    (self.completed_at - self.started_at).total_seconds(), 6
                ),
                "identity_note": (
                    "execution timestamps and elapsed time are not stored in the "
                    "deterministic evidence report and do not affect report_id"
                ),
            },
        }


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return sha256_file(path)


def _canonical_json(value: object) -> str:
    return canonical_json(value)


def _content_report_id(report: Mapping[str, object]) -> str:
    identity_material = dict(report)
    identity_material.pop("report_id", None)
    identity_material.pop("local_provenance", None)
    return (
        "vessel-evidence-"
        + hashlib.sha256(
            _canonical_json(identity_material).encode("utf-8")
        ).hexdigest()[:24]
    )


def _read_json_object(path: Path, label: str) -> Mapping[str, object]:
    with _shared_bundle_errors():
        return read_json_object(path, label)


def _mapping(value: object, label: str) -> Mapping[str, object]:
    with _shared_bundle_errors():
        return require_mapping(value, label)


def _validate_bundle_metadata(
    bundle_path: Path, cleaned_sha256: str
) -> tuple[str, Mapping[str, object]]:
    with _shared_bundle_errors():
        sidecars = validate_bundle_sidecars(bundle_path, cleaned_sha256)
    return sidecars.cleaner_run_id, sidecars.temporal_coverage


def _validate_schema(schema: pa.Schema) -> None:
    with _shared_bundle_errors():
        validate_cleaned_schema(schema)


def _finite_number(value: object, label: str, row_index: int) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise VesselActivityEvidenceError(f"row {row_index} has invalid {label}")
    result = float(value)
    if not math.isfinite(result):
        raise VesselActivityEvidenceError(f"row {row_index} has non-finite {label}")
    return result


def _optional_nonnegative(value: object, label: str, row_index: int) -> float | None:
    if value is None:
        return None
    result = _finite_number(value, label, row_index)
    if result < 0:
        raise VesselActivityEvidenceError(f"row {row_index} has negative {label}")
    return result


def _observations(table: pa.Table) -> tuple[Observation, ...]:
    timestamp_type = table.schema.field("observed_at_utc").type
    if not isinstance(timestamp_type, pa.TimestampType):
        raise VesselActivityEvidenceError("observed_at_utc is not a timestamp")
    seconds_per_unit = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}[
        timestamp_type.unit
    ]
    timestamp_values = table["observed_at_utc"].cast(pa.int64()).to_pylist()
    columns = {
        name: table[name].to_pylist()
        for name in _EXPECTED_COLUMNS
        if name != "observed_at_utc"
    }
    observations: list[Observation] = []
    for row_index, timestamp_integer in enumerate(timestamp_values):
        mmsi = columns["mmsi"][row_index]
        group = columns["vessel_type_group"][row_index]
        vessel_type_code = columns["vessel_type_code"][row_index]
        if not isinstance(mmsi, str) or not mmsi.strip():
            raise VesselActivityEvidenceError(f"row {row_index} has invalid mmsi")
        if not isinstance(timestamp_integer, int) or isinstance(
            timestamp_integer, bool
        ):
            raise VesselActivityEvidenceError(
                f"row {row_index} has invalid observed_at_utc"
            )
        timestamp = datetime.fromtimestamp(timestamp_integer * seconds_per_unit, UTC)
        if group not in VESSEL_GROUPS:
            raise VesselActivityEvidenceError(
                f"row {row_index} has invalid vessel_type_group"
            )
        if not isinstance(vessel_type_code, int) or isinstance(vessel_type_code, bool):
            raise VesselActivityEvidenceError(
                f"row {row_index} has invalid vessel_type_code"
            )
        latitude = _finite_number(columns["latitude"][row_index], "latitude", row_index)
        longitude = _finite_number(
            columns["longitude"][row_index], "longitude", row_index
        )
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise VesselActivityEvidenceError(
                f"row {row_index} has out-of-range coordinates"
            )
        observations.append(
            Observation(
                mmsi=mmsi,
                observed_at_utc=timestamp,
                latitude=latitude,
                longitude=longitude,
                sog_knots=_optional_nonnegative(
                    columns["sog_knots"][row_index], "sog_knots", row_index
                ),
                vessel_type_code=vessel_type_code,
                vessel_type_group=group,
                length_m=_optional_nonnegative(
                    columns["length_m"][row_index], "length_m", row_index
                ),
            )
        )
    if not observations:
        raise VesselActivityEvidenceError("cleaned Parquet contains no observations")
    return tuple(
        sorted(
            observations,
            key=lambda item: (
                item.mmsi,
                item.observed_at_utc,
                item.latitude,
                item.longitude,
                item.vessel_type_code,
                item.vessel_type_group,
            ),
        )
    )


def load_cleaned_bundle(bundle_path: Path) -> CleanedBundleInspection:
    """Validate and read an explicitly supplied current cleaner bundle."""
    with _shared_bundle_errors():
        bundle_path = validate_bundle_layout(bundle_path)
    cleaned_path = bundle_path / CLEANED_FILENAME
    cleaned_sha256 = _sha256_file(cleaned_path)
    cleaner_run_id, temporal_coverage = _validate_bundle_metadata(
        bundle_path, cleaned_sha256
    )
    try:
        schema = pq.read_schema(cleaned_path)
        _validate_schema(schema)
        table = pq.read_table(cleaned_path)
    except VesselActivityEvidenceError:
        raise
    except (OSError, pa.ArrowException) as exc:
        raise VesselActivityEvidenceError(
            f"could not read cleaned Parquet {cleaned_path}: {exc}"
        ) from exc
    return CleanedBundleInspection(
        bundle_path=bundle_path,
        cleaned_path=cleaned_path,
        cleaned_sha256=cleaned_sha256,
        cleaner_run_id=cleaner_run_id,
        temporal_coverage=temporal_coverage,
        observations=_observations(table),
    )


def _finite_xy(
    transformer: Transformer, longitude: float, latitude: float
) -> tuple[float, float]:
    x, y = transformer.transform(longitude, latitude)
    if not math.isfinite(x) or not math.isfinite(y):
        raise VesselActivityEvidenceError("coordinate transformation was non-finite")
    return float(x), float(y)


def construct_candidate_segments(
    observations: Sequence[Observation],
) -> tuple[CandidateSegment, ...]:
    """Order by MMSI/time and pair each observation with its chronological next."""
    ordered = sorted(
        observations,
        key=lambda item: (
            item.mmsi,
            item.observed_at_utc,
            item.latitude,
            item.longitude,
            item.vessel_type_code,
            item.vessel_type_group,
        ),
    )
    transformer = Transformer.from_crs(WGS84_CRS, PROJECTED_CRS, always_xy=True)
    geod = Geod(ellps="WGS84")
    segments: list[CandidateSegment] = []
    previous: Observation | None = None
    for current in ordered:
        if previous is None or previous.mmsi != current.mmsi:
            previous = current
            continue
        start_xy = _finite_xy(transformer, previous.longitude, previous.latitude)
        end_xy = _finite_xy(transformer, current.longitude, current.latitude)
        projected_distance = math.hypot(
            end_xy[0] - start_xy[0], end_xy[1] - start_xy[1]
        )
        _azimuth_1, _azimuth_2, geodesic_distance = geod.inv(
            previous.longitude,
            previous.latitude,
            current.longitude,
            current.latitude,
        )
        geodesic_distance = abs(float(geodesic_distance))
        elapsed = (current.observed_at_utc - previous.observed_at_utc).total_seconds()
        implied = (
            projected_distance / elapsed * KNOTS_PER_METRE_PER_SECOND
            if elapsed > 0
            else None
        )
        segments.append(
            CandidateSegment(
                sequence=len(segments),
                start=previous,
                end=current,
                elapsed_seconds=float(elapsed),
                projected_distance_m=projected_distance,
                geodesic_distance_m=geodesic_distance,
                implied_speed_knots=implied,
                start_xy_m=start_xy,
                end_xy_m=end_xy,
            )
        )
        previous = current
    return tuple(segments)


def _round(value: float) -> float:
    return round(value, 12)


def _distribution(values: Iterable[float]) -> dict[str, object]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return {"count": 0}

    def quantile(fraction: float) -> float:
        position = fraction * (len(ordered) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    return {
        "count": len(ordered),
        "minimum": _round(ordered[0]),
        "p25": _round(quantile(0.25)),
        "median": _round(quantile(0.5)),
        "p75": _round(quantile(0.75)),
        "p95": _round(quantile(0.95)),
        "maximum": _round(ordered[-1]),
        "mean": _round(math.fsum(ordered) / len(ordered)),
    }


def _grouped_observation_diagnostics(
    observations: Sequence[Observation],
) -> dict[str, object]:
    result: dict[str, object] = {}
    group_mmsi_sum = 0
    group_mmsi_date_sum = 0
    group_observation_sum = 0
    for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
        selected = (
            list(observations)
            if group == ALL_COMMERCIAL
            else [item for item in observations if item.vessel_type_group == group]
        )
        unique_mmsi = {item.mmsi for item in selected}
        unique_mmsi_dates = {(item.mmsi, item.utc_date) for item in selected}
        available_sog = [
            item.sog_knots for item in selected if item.sog_knots is not None
        ]
        result[group] = {
            "observation_count": len(selected),
            "unique_mmsi_count": len(unique_mmsi),
            "unique_mmsi_date_count": len(unique_mmsi_dates),
            "reported_sog": {
                "available_observation_count": len(available_sog),
                "unavailable_observation_count": len(selected) - len(available_sog),
                "availability_fraction": (
                    None if not selected else _round(len(available_sog) / len(selected))
                ),
                "available_value_distribution_knots": _distribution(
                    cast(Iterable[float], available_sog)
                ),
                "separation_note": (
                    "reported SOG is an endpoint observation attribute and is not "
                    "substituted for implied segment speed"
                ),
            },
        }
        if group != ALL_COMMERCIAL:
            group_observation_sum += len(selected)
            group_mmsi_sum += len(unique_mmsi)
            group_mmsi_date_sum += len(unique_mmsi_dates)
    all_values = cast(dict[str, object], result[ALL_COMMERCIAL])
    all_values["union_recomputation"] = {
        "method": (
            "distinct values recomputed from the union of commercial observations"
        ),
        "sum_of_group_observation_counts": group_observation_sum,
        "all_commercial_observation_count": all_values["observation_count"],
        "observation_counts_are_additive": (
            group_observation_sum == all_values["observation_count"]
        ),
        "sum_of_group_unique_mmsi_counts": group_mmsi_sum,
        "union_unique_mmsi_count": all_values["unique_mmsi_count"],
        "sum_minus_union_unique_mmsi_count": (
            group_mmsi_sum - cast(int, all_values["unique_mmsi_count"])
        ),
        "sum_of_group_unique_mmsi_date_counts": group_mmsi_date_sum,
        "union_unique_mmsi_date_count": all_values["unique_mmsi_date_count"],
        "sum_minus_union_unique_mmsi_date_count": (
            group_mmsi_date_sum - cast(int, all_values["unique_mmsi_date_count"])
        ),
    }
    return result


def _segments_for_group(
    segments: Sequence[CandidateSegment], group: str
) -> list[CandidateSegment]:
    if group == ALL_COMMERCIAL:
        return list(segments)
    return [item for item in segments if item.start.vessel_type_group == group]


def _grouped_segment_diagnostics(
    segments: Sequence[CandidateSegment],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
        selected = _segments_for_group(segments, group)
        increasing = [item for item in selected if item.strictly_increasing]
        distance_population = increasing
        geodesic_nonzero = [
            item for item in distance_population if item.geodesic_distance_m > 0
        ]
        result[group] = {
            "candidate_pair_count": len(selected),
            "time_gap_seconds": _distribution(
                item.elapsed_seconds for item in selected
            ),
            "non_increasing_timestamp_count": sum(
                not item.strictly_increasing for item in selected
            ),
            "zero_length_consecutive_segment_count": sum(
                item.projected_distance_m <= LENGTH_TOLERANCE_M for item in increasing
            ),
            "projected_endpoint_distance_m": _distribution(
                item.projected_distance_m for item in distance_population
            ),
            "wgs84_geodesic_endpoint_distance_m": _distribution(
                item.geodesic_distance_m for item in distance_population
            ),
            "projected_minus_geodesic_distance_m": _distribution(
                item.projected_distance_m - item.geodesic_distance_m
                for item in distance_population
            ),
            "absolute_projected_geodesic_difference_m": _distribution(
                abs(item.projected_distance_m - item.geodesic_distance_m)
                for item in distance_population
            ),
            "relative_projected_geodesic_difference_fraction": _distribution(
                (item.projected_distance_m - item.geodesic_distance_m)
                / item.geodesic_distance_m
                for item in geodesic_nonzero
            ),
            "absolute_relative_projected_geodesic_difference_fraction": _distribution(
                abs(item.projected_distance_m - item.geodesic_distance_m)
                / item.geodesic_distance_m
                for item in geodesic_nonzero
            ),
            "relative_difference_undefined_zero_geodesic_count": (
                len(distance_population) - len(geodesic_nonzero)
            ),
            "implied_speed_knots": _distribution(
                item.implied_speed_knots
                for item in increasing
                if item.implied_speed_knots is not None
            ),
            "group_basis": (
                "starting endpoint vessel group; all_commercial is recomputed from "
                "the union of all candidate pairs"
            ),
        }
    transitions: dict[str, int] = defaultdict(int)
    for segment in segments:
        if segment.group_changed:
            transitions[
                f"{segment.start.vessel_type_group}_to_{segment.end.vessel_type_group}"
            ] += 1
    return {
        "by_group": result,
        "vessel_group_changes": {
            "count": sum(transitions.values()),
            "transitions": dict(sorted(transitions.items())),
        },
        "population_note": (
            "distance and implied-speed distributions use strictly increasing pairs; "
            "structural allocation additionally excludes vessel-group changes"
        ),
    }


def _validated_candidates(values: Sequence[float], label: str) -> tuple[float, ...]:
    normalized: list[float] = []
    for value in values:
        candidate = float(value)
        if not math.isfinite(candidate) or candidate <= 0:
            raise VesselActivityEvidenceError(
                f"{label} values must be finite and positive"
            )
        normalized.append(candidate)
    if len(normalized) != len(set(normalized)):
        raise VesselActivityEvidenceError(f"{label} values must not be duplicated")
    return tuple(sorted(normalized))


def _evaluate_candidate_sensitivity(
    segments: Sequence[CandidateSegment],
    *,
    maximum_gap_seconds: Sequence[float],
    implied_speed_ceiling_knots: Sequence[float],
    minimum_vessel_length_m: Sequence[float],
) -> CandidateSensitivityEvaluation:
    gaps = _validated_candidates(maximum_gap_seconds, "maximum-gap")
    speeds = _validated_candidates(implied_speed_ceiling_knots, "implied-speed")
    lengths = _validated_candidates(minimum_vessel_length_m, "minimum-length")
    structural = tuple(item for item in segments if item.structurally_eligible)
    if not gaps and not speeds and not lengths:
        return CandidateSensitivityEvaluation(
            maximum_gap_seconds=gaps,
            implied_speed_ceiling_knots=speeds,
            minimum_vessel_length_m=lengths,
            structural_baseline=structural,
            scenarios=(),
        )
    axes: list[tuple[float | None, ...]] = [
        gaps if gaps else (None,),
        speeds if speeds else (None,),
        lengths if lengths else (None,),
    ]
    scenarios: list[CandidateScenarioEvaluation] = []
    for gap in axes[0]:
        for speed in axes[1]:
            for length in axes[2]:
                retained: list[CandidateSegment] = []
                exclusions = {"gap": 0, "implied_speed": 0, "length": 0}
                for segment in structural:
                    if gap is not None and segment.elapsed_seconds > gap:
                        exclusions["gap"] += 1
                        continue
                    if (
                        speed is not None
                        and segment.implied_speed_knots is not None
                        and segment.implied_speed_knots > speed
                    ):
                        exclusions["implied_speed"] += 1
                        continue
                    if length is not None and (
                        segment.start.length_m is None
                        or segment.end.length_m is None
                        or segment.start.length_m < length
                        or segment.end.length_m < length
                    ):
                        exclusions["length"] += 1
                        continue
                    retained.append(segment)
                rules = {
                    "candidate_maximum_gap_seconds": gap,
                    "candidate_implied_speed_ceiling_knots": speed,
                    "candidate_minimum_vessel_length_m": length,
                }
                scenarios.append(
                    CandidateScenarioEvaluation(
                        scenario_id=(
                            "candidate-"
                            + hashlib.sha256(
                                _canonical_json(rules).encode("utf-8")
                            ).hexdigest()[:16]
                        ),
                        maximum_gap_seconds=gap,
                        implied_speed_ceiling_knots=speed,
                        minimum_vessel_length_m=length,
                        retained_segments=tuple(retained),
                        primary_exclusion_counts=tuple(sorted(exclusions.items())),
                    )
                )
    return CandidateSensitivityEvaluation(
        maximum_gap_seconds=gaps,
        implied_speed_ceiling_knots=speeds,
        minimum_vessel_length_m=lengths,
        structural_baseline=structural,
        scenarios=tuple(scenarios),
    )


def _candidate_scenario_diagnostics(
    scenario: CandidateScenarioEvaluation,
) -> dict[str, object]:
    retained = scenario.retained_segments
    return {
        "scenario_id": scenario.scenario_id,
        **scenario.rules(),
        "retained_segment_count": len(retained),
        "retained_projected_distance_m": _round(
            math.fsum(item.projected_distance_m for item in retained)
        ),
        "primary_exclusion_counts": dict(scenario.primary_exclusion_counts),
        "by_group": {
            group: {
                "retained_segment_count": sum(
                    item.start.vessel_type_group == group for item in retained
                ),
                "retained_projected_distance_m": _round(
                    math.fsum(
                        item.projected_distance_m
                        for item in retained
                        if item.start.vessel_type_group == group
                    )
                ),
            }
            for group in VESSEL_GROUPS
        },
    }


def _candidate_sensitivity(
    evaluation: CandidateSensitivityEvaluation,
) -> dict[str, object]:
    structural = evaluation.structural_baseline
    return {
        "status": "candidate evidence values only; no rule is accepted",
        "implicit_defaults": False,
        "supplied_values": {
            "maximum_gap_seconds": list(evaluation.maximum_gap_seconds),
            "implied_speed_ceiling_knots": list(evaluation.implied_speed_ceiling_knots),
            "minimum_vessel_length_m": list(evaluation.minimum_vessel_length_m),
        },
        "candidate_definitions": {
            "maximum_gap": "retain elapsed seconds less than or equal to the value",
            "implied_speed_ceiling": (
                "retain EPSG:3310 projected endpoint distance divided by elapsed "
                "time less than or equal to the value"
            ),
            "minimum_vessel_length": (
                "retain only when both endpoint length values are available and "
                "greater than or equal to the value"
            ),
        },
        "structural_baseline": {
            "definition": (
                "strictly increasing consecutive pairs with unchanged vessel group; "
                "no gap, implied-speed, or length filter"
            ),
            "segment_count": len(structural),
            "projected_distance_m": _round(
                math.fsum(item.projected_distance_m for item in structural)
            ),
        },
        "candidate_scenarios": [
            _candidate_scenario_diagnostics(scenario)
            for scenario in evaluation.scenarios
        ],
        "precedence": ["maximum_gap", "implied_speed", "minimum_length"],
    }


def _censoring_diagnostics(observations: Sequence[Observation]) -> dict[str, object]:
    counts: dict[str, int] = defaultdict(int)
    for observation in observations:
        counts[observation.mmsi] += 1
    endpoint_count = sum(1 if count == 1 else 2 for count in counts.values())
    return {
        "bundle_endpoint_observation_count": endpoint_count,
        "single_observation_mmsi_count": sum(count == 1 for count in counts.values()),
        "period_censoring": (
            "No track is extrapolated before the first or after the last supplied "
            "cleaned observation. This one-bundle harness cannot construct cross-day "
            "pairs, so omitted before/after distance is unknown."
        ),
        "spatial_edge_support": (
            "The current cleaner removed positions outside the map/context extent "
            "before this harness. A bundle endpoint may reflect time-window censoring, "
            "spatial-edge censoring, or an actual track endpoint; this report does not "
            "assign a cause and does not infer the missing portion."
        ),
        "outside_support_semantics": (
            "Outside modeled-whale-support length is reported only as outside that "
            "biological model support. It is not classified as land, dry area, or "
            "absent AIS coverage."
        ),
    }


def _segment_id(segment: CandidateSegment) -> str:
    material = {
        "mmsi": segment.start.mmsi,
        "start_observed_at_utc": _timestamp(segment.start.observed_at_utc),
        "end_observed_at_utc": _timestamp(segment.end.observed_at_utc),
        "start_longitude": segment.start.longitude,
        "start_latitude": segment.start.latitude,
        "end_longitude": segment.end.longitude,
        "end_latitude": segment.end.latitude,
        "start_vessel_group": segment.start.vessel_type_group,
        "end_vessel_group": segment.end.vessel_type_group,
    }
    return (
        "segment-"
        + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()[:24]
    )


def _geometry_intersection(left: BaseGeometry, right: BaseGeometry) -> BaseGeometry:
    """Isolate exact intersection calls so cache reuse can be verified."""
    return cast(BaseGeometry, left.intersection(right))


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


def _time_tolerance(elapsed_seconds: float) -> float:
    return max(
        TIME_TOLERANCE_SECONDS,
        abs(elapsed_seconds) * CONSERVATION_RELATIVE_TOLERANCE,
    )


def _validate_elapsed_conservation(allocation: SegmentPieceAllocation) -> None:
    elapsed = allocation.segment.elapsed_seconds
    accounted = math.fsum(
        (
            allocation.inside_support_elapsed_seconds,
            allocation.outside_support_elapsed_seconds,
            allocation.unallocated_elapsed_seconds,
        )
    )
    if not math.isclose(
        elapsed,
        accounted,
        rel_tol=CONSERVATION_RELATIVE_TOLERANCE,
        abs_tol=_time_tolerance(elapsed),
    ):
        raise VesselActivityEvidenceError(
            "segment elapsed time is not conserved across in-support, "
            "outside-support, and unallocated time"
        )


def build_segment_piece_cache(
    segments: Sequence[CandidateSegment], target_grid: TargetGridInspection
) -> SegmentPieceCache:
    """Calculate exact structural segment/grid intersections exactly once."""
    geometries = [cell.geometry for cell in target_grid.cells]
    tree = STRtree(geometries)
    structural = [segment for segment in segments if segment.structurally_eligible]
    sequences = [segment.sequence for segment in structural]
    if len(sequences) != len(set(sequences)):
        raise VesselActivityEvidenceError(
            "structural segment sequence values must be unique for cached allocation"
        )
    segment_ids = [_segment_id(segment) for segment in structural]
    if len(segment_ids) != len(set(segment_ids)):
        raise VesselActivityEvidenceError(
            "structural segment identities must be unique for cached allocation"
        )

    allocations: list[SegmentPieceAllocation] = []
    for segment, segment_id in zip(structural, segment_ids, strict=True):
        elapsed = segment.elapsed_seconds
        pieces: tuple[SegmentPiece, ...]
        if segment.projected_distance_m <= LENGTH_TOLERANCE_M:
            point = Point(segment.start_xy_m)
            matching_indices = [
                index
                for index in sorted(int(value) for value in tree.query(point))
                if geometries[index].covers(point)
            ]
            if len(matching_indices) == 1:
                cell_order = matching_indices[0]
                pieces = (
                    SegmentPiece(
                        parent_segment_id=segment_id,
                        parent_sequence=segment.sequence,
                        vessel_group=segment.start.vessel_type_group,
                        parent_elapsed_seconds=elapsed,
                        parent_projected_distance_m=segment.projected_distance_m,
                        cell_id=target_grid.cells[cell_order].cell_id,
                        cell_order=cell_order,
                        piece_order=0,
                        piece_distance_m=0.0,
                        piece_elapsed_seconds=elapsed,
                        zero_length=True,
                    ),
                )
                allocation = SegmentPieceAllocation(
                    segment=segment,
                    segment_id=segment_id,
                    pieces=pieces,
                    inside_support_distance_m=0.0,
                    outside_support_distance_m=0.0,
                    inside_support_elapsed_seconds=elapsed,
                    outside_support_elapsed_seconds=0.0,
                    unallocated_elapsed_seconds=0.0,
                    status="zero_length_in_support",
                )
            elif not matching_indices:
                allocation = SegmentPieceAllocation(
                    segment=segment,
                    segment_id=segment_id,
                    pieces=(),
                    inside_support_distance_m=0.0,
                    outside_support_distance_m=0.0,
                    inside_support_elapsed_seconds=0.0,
                    outside_support_elapsed_seconds=elapsed,
                    unallocated_elapsed_seconds=0.0,
                    status="zero_length_outside_support",
                )
            else:
                allocation = SegmentPieceAllocation(
                    segment=segment,
                    segment_id=segment_id,
                    pieces=(),
                    inside_support_distance_m=0.0,
                    outside_support_distance_m=0.0,
                    inside_support_elapsed_seconds=0.0,
                    outside_support_elapsed_seconds=0.0,
                    unallocated_elapsed_seconds=elapsed,
                    status="zero_length_ambiguous",
                )
            _validate_elapsed_conservation(allocation)
            allocations.append(allocation)
            continue

        line = LineString([segment.start_xy_m, segment.end_xy_m])
        raw_pieces: list[tuple[float, int, float, str, BaseGeometry]] = []
        intersection_geometries: list[BaseGeometry] = []
        for cell_order in sorted(int(value) for value in tree.query(line)):
            intersection = _geometry_intersection(line, geometries[cell_order])
            for component in _linear_components(intersection):
                length = float(component.length)
                if length <= LENGTH_TOLERANCE_M:
                    continue
                coordinates = list(component.coords)
                start_position = float(line.project(Point(coordinates[0])))
                end_position = float(line.project(Point(coordinates[-1])))
                raw_pieces.append(
                    (
                        min(start_position, end_position),
                        cell_order,
                        length,
                        component.wkb_hex,
                        component,
                    )
                )
                intersection_geometries.append(component)
        raw_pieces.sort(key=lambda item: item[:4])
        piece_length = math.fsum(item[2] for item in raw_pieces)
        if not intersection_geometries:
            union_length = 0.0
        elif len(intersection_geometries) == 1:
            union_length = float(intersection_geometries[0].length)
        else:
            union_length = float(unary_union(intersection_geometries).length)
        tolerance = max(
            LENGTH_TOLERANCE_M,
            segment.projected_distance_m * CONSERVATION_RELATIVE_TOLERANCE,
        )
        if not math.isclose(
            piece_length,
            union_length,
            rel_tol=CONSERVATION_RELATIVE_TOLERANCE,
            abs_tol=tolerance,
        ):
            raise VesselActivityEvidenceError(
                "segment-piece lengths do not conserve their union; exact modeled-"
                "support cells would double allocate this parent segment"
            )
        if union_length > segment.projected_distance_m + tolerance:
            raise VesselActivityEvidenceError(
                "segment allocation exceeds parent projected length"
            )
        outside_distance = max(0.0, segment.projected_distance_m - union_length)
        pieces = tuple(
            SegmentPiece(
                parent_segment_id=segment_id,
                parent_sequence=segment.sequence,
                vessel_group=segment.start.vessel_type_group,
                parent_elapsed_seconds=elapsed,
                parent_projected_distance_m=segment.projected_distance_m,
                cell_id=target_grid.cells[cell_order].cell_id,
                cell_order=cell_order,
                piece_order=piece_order,
                piece_distance_m=length,
                piece_elapsed_seconds=(elapsed * length / segment.projected_distance_m),
                zero_length=False,
            )
            for piece_order, (
                _position,
                cell_order,
                length,
                _wkb,
                _geometry,
            ) in enumerate(raw_pieces)
        )
        inside_elapsed = math.fsum(piece.piece_elapsed_seconds for piece in pieces)
        outside_elapsed = elapsed * outside_distance / segment.projected_distance_m
        if union_length <= LENGTH_TOLERANCE_M:
            status: AllocationStatus = "positive_length_outside_support"
        elif outside_distance <= LENGTH_TOLERANCE_M:
            status = "positive_length_in_support"
        else:
            status = "positive_length_partially_outside_support"
        allocation = SegmentPieceAllocation(
            segment=segment,
            segment_id=segment_id,
            pieces=pieces,
            inside_support_distance_m=union_length,
            outside_support_distance_m=outside_distance,
            inside_support_elapsed_seconds=inside_elapsed,
            outside_support_elapsed_seconds=outside_elapsed,
            unallocated_elapsed_seconds=0.0,
            status=status,
        )
        _validate_elapsed_conservation(allocation)
        allocations.append(allocation)
    return SegmentPieceCache(target_grid=target_grid, allocations=tuple(allocations))


def _group_additive_values(
    values: Mapping[str, float], *, divisor: float = 1.0
) -> dict[str, float]:
    grouped = {group: _round(values[group] / divisor) for group in VESSEL_GROUPS}
    grouped[ALL_COMMERCIAL] = _round(
        math.fsum(values[group] for group in VESSEL_GROUPS) / divisor
    )
    return grouped


def aggregate_segment_piece_cache(
    cache: SegmentPieceCache,
    segments: Sequence[CandidateSegment],
    *,
    population_label: str,
) -> dict[str, object]:
    """Aggregate a selected structural population without repeating intersections."""
    selected_ids = {_segment_id(segment) for segment in segments}
    if len(selected_ids) != len(segments):
        raise VesselActivityEvidenceError(
            "selected segment population contains duplicate parent identities"
        )
    available_ids = {allocation.segment_id for allocation in cache.allocations}
    if not selected_ids <= available_ids:
        raise VesselActivityEvidenceError(
            "selected segment population is not a subset of the structural cache"
        )
    allocations = [
        allocation
        for allocation in cache.allocations
        if allocation.segment_id in selected_ids
    ]
    metrics = (
        "parent_length_m",
        "in_support_length_m",
        "outside_support_length_m",
        "parent_elapsed_seconds",
        "in_support_elapsed_seconds",
        "outside_support_elapsed_seconds",
        "unallocated_elapsed_seconds",
    )
    group_totals: dict[str, dict[str, float]] = {
        group: {metric: 0.0 for metric in metrics} for group in VESSEL_GROUPS
    }
    group_segment_counts = {group: 0 for group in VESSEL_GROUPS}
    cell_piece_counts = [0 for _cell in cache.target_grid.cells]
    cell_distances = {
        group: [0.0 for _cell in cache.target_grid.cells] for group in VESSEL_GROUPS
    }
    cell_elapsed = {
        group: [0.0 for _cell in cache.target_grid.cells] for group in VESSEL_GROUPS
    }
    status_counts: dict[str, int] = defaultdict(int)
    maximum_piece_difference = 0.0
    for allocation in allocations:
        segment = allocation.segment
        group_name = segment.start.vessel_type_group
        group_segment_counts[group_name] += 1
        values = group_totals[group_name]
        values["parent_length_m"] += segment.projected_distance_m
        values["in_support_length_m"] += allocation.inside_support_distance_m
        values["outside_support_length_m"] += allocation.outside_support_distance_m
        values["parent_elapsed_seconds"] += segment.elapsed_seconds
        values["in_support_elapsed_seconds"] += (
            allocation.inside_support_elapsed_seconds
        )
        values["outside_support_elapsed_seconds"] += (
            allocation.outside_support_elapsed_seconds
        )
        values["unallocated_elapsed_seconds"] += allocation.unallocated_elapsed_seconds
        status_counts[allocation.status] += 1
        allocation_piece_length = math.fsum(
            piece.piece_distance_m for piece in allocation.pieces
        )
        maximum_piece_difference = max(
            maximum_piece_difference,
            abs(allocation_piece_length - allocation.inside_support_distance_m),
        )
        for piece in allocation.pieces:
            cell_piece_counts[piece.cell_order] += 1
            cell_distances[group_name][piece.cell_order] += piece.piece_distance_m
            cell_elapsed[group_name][piece.cell_order] += piece.piece_elapsed_seconds

    total_parent = math.fsum(
        group_totals[group]["parent_length_m"] for group in VESSEL_GROUPS
    )
    total_inside = math.fsum(
        group_totals[group]["in_support_length_m"] for group in VESSEL_GROUPS
    )
    total_outside = math.fsum(
        group_totals[group]["outside_support_length_m"] for group in VESSEL_GROUPS
    )
    total_parent_elapsed = math.fsum(
        group_totals[group]["parent_elapsed_seconds"] for group in VESSEL_GROUPS
    )
    total_inside_elapsed = math.fsum(
        group_totals[group]["in_support_elapsed_seconds"] for group in VESSEL_GROUPS
    )
    total_outside_elapsed = math.fsum(
        group_totals[group]["outside_support_elapsed_seconds"]
        for group in VESSEL_GROUPS
    )
    total_unallocated_elapsed = math.fsum(
        group_totals[group]["unallocated_elapsed_seconds"] for group in VESSEL_GROUPS
    )
    distance_difference = total_parent - total_inside - total_outside
    time_difference = (
        total_parent_elapsed
        - total_inside_elapsed
        - total_outside_elapsed
        - total_unallocated_elapsed
    )
    if not math.isclose(
        distance_difference,
        0.0,
        rel_tol=CONSERVATION_RELATIVE_TOLERANCE,
        abs_tol=max(
            LENGTH_TOLERANCE_M,
            total_parent * CONSERVATION_RELATIVE_TOLERANCE,
        ),
    ):
        raise VesselActivityEvidenceError(
            "aggregate parent distance is not conserved by cached allocation"
        )
    if not math.isclose(
        time_difference,
        0.0,
        rel_tol=CONSERVATION_RELATIVE_TOLERANCE,
        abs_tol=_time_tolerance(total_parent_elapsed),
    ):
        raise VesselActivityEvidenceError(
            "aggregate parent elapsed time is not conserved by cached allocation"
        )

    all_commercial_values = {
        metric: math.fsum(group_totals[group][metric] for group in VESSEL_GROUPS)
        for metric in metrics
    }
    group_report: dict[str, object] = {}
    report_groups: tuple[str, ...] = (*VESSEL_GROUPS, ALL_COMMERCIAL)
    for report_group_name in report_groups:
        values = (
            all_commercial_values
            if report_group_name == ALL_COMMERCIAL
            else group_totals[report_group_name]
        )
        group_report[report_group_name] = {
            "segment_count": (
                len(allocations)
                if report_group_name == ALL_COMMERCIAL
                else group_segment_counts[report_group_name]
            ),
            "parent_length_m": _round(values["parent_length_m"]),
            "parent_length_km": _round(values["parent_length_m"] / 1_000),
            "in_support_length_m": _round(values["in_support_length_m"]),
            "in_support_length_km": _round(values["in_support_length_m"] / 1_000),
            "outside_support_length_m": _round(values["outside_support_length_m"]),
            "outside_support_length_km": _round(
                values["outside_support_length_m"] / 1_000
            ),
            "parent_elapsed_seconds": _round(values["parent_elapsed_seconds"]),
            "parent_vessel_hours": _round(values["parent_elapsed_seconds"] / 3_600),
            "in_support_elapsed_seconds": _round(values["in_support_elapsed_seconds"]),
            "in_support_vessel_hours": _round(
                values["in_support_elapsed_seconds"] / 3_600
            ),
            "outside_support_elapsed_seconds": _round(
                values["outside_support_elapsed_seconds"]
            ),
            "outside_support_vessel_hours": _round(
                values["outside_support_elapsed_seconds"] / 3_600
            ),
            "unallocated_elapsed_seconds": _round(
                values["unallocated_elapsed_seconds"]
            ),
            "unallocated_vessel_hours": _round(
                values["unallocated_elapsed_seconds"] / 3_600
            ),
        }
    per_cell: list[dict[str, object]] = []
    for cell_order, cell in enumerate(cache.target_grid.cells):
        distance_values = {
            group: cell_distances[group][cell_order] for group in VESSEL_GROUPS
        }
        elapsed_values = {
            group: cell_elapsed[group][cell_order] for group in VESSEL_GROUPS
        }
        per_cell.append(
            {
                "cell_id": cell.cell_id,
                "segment_piece_count": cell_piece_counts[cell_order],
                "vessel_kilometres": _group_additive_values(
                    distance_values, divisor=1_000
                ),
                "vessel_hours": _group_additive_values(elapsed_values, divisor=3_600),
            }
        )
    total_piece_length = math.fsum(
        piece.piece_distance_m
        for allocation in allocations
        for piece in allocation.pieces
    )
    touched_cell_count = sum(count > 0 for count in cell_piece_counts)
    return {
        "status": "non-production diagnostic allocation",
        "segment_population": population_label,
        "target_grid": {
            "contract": "projected_water_grid_v1",
            "sha256": cache.target_grid.sha256,
            "analysis_crs": PROJECTED_CRS,
            "transformation": {"source_crs": WGS84_CRS, "always_xy": True},
            "cell_geometry": "exact modeled-whale-support geometry",
        },
        "counts": {
            "allocated_segment_count": len(allocations),
            "zero_length_segment_count": sum(
                allocation.segment.projected_distance_m <= LENGTH_TOLERANCE_M
                for allocation in allocations
            ),
            "positive_length_piece_count": sum(
                not piece.zero_length
                for allocation in allocations
                for piece in allocation.pieces
            ),
            "segment_piece_count": sum(cell_piece_counts),
            "touched_cell_count": touched_cell_count,
            "allocation_status_counts": {
                status: status_counts[status] for status in ALLOCATION_STATUSES
            },
        },
        "lengths": {
            "parent_projected_length_m": _round(total_parent),
            "parent_projected_length_km": _round(total_parent / 1_000),
            "in_support_piece_length_m": _round(total_piece_length),
            "in_support_piece_length_km": _round(total_piece_length / 1_000),
            "in_support_union_intersection_length_m": _round(total_inside),
            "in_support_union_intersection_length_km": _round(total_inside / 1_000),
            "outside_support_length_m": _round(total_outside),
            "outside_support_length_km": _round(total_outside / 1_000),
        },
        "vessel_hours_comparison": {
            "status": "evidence-only comparison; not an accepted production rule",
            "assumption": (
                "constant progress along each positive-length straight segment; "
                "piece time is proportional to parent projected length"
            ),
            "zero_length_semantics": (
                "full elapsed time is assigned only for exactly one support cell; "
                "no match is outside support and multiple matches are unallocated"
            ),
            "parent_elapsed_seconds": _round(total_parent_elapsed),
            "parent_vessel_hours": _round(total_parent_elapsed / 3_600),
            "in_support_elapsed_seconds": _round(total_inside_elapsed),
            "in_support_vessel_hours": _round(total_inside_elapsed / 3_600),
            "outside_support_elapsed_seconds": _round(total_outside_elapsed),
            "outside_support_vessel_hours": _round(total_outside_elapsed / 3_600),
            "unallocated_elapsed_seconds": _round(total_unallocated_elapsed),
            "unallocated_vessel_hours": _round(total_unallocated_elapsed / 3_600),
        },
        "by_group": group_report,
        "per_cell": per_cell,
        "conservation": {
            "passed": True,
            "piece_minus_union_intersection_m": _round(
                total_piece_length - total_inside
            ),
            "parent_minus_in_support_minus_outside_m": _round(distance_difference),
            "parent_elapsed_minus_allocated_seconds": _round(time_difference),
            "maximum_segment_piece_difference_m": _round(maximum_piece_difference),
            "no_double_allocation": True,
            "distance_absolute_tolerance_m": LENGTH_TOLERANCE_M,
            "time_absolute_tolerance_seconds": TIME_TOLERANCE_SECONDS,
            "relative_tolerance": CONSERVATION_RELATIVE_TOLERANCE,
        },
        "outside_support_note": (
            "outside-support portions are outside the supplied biological model "
            "support only; no land, dry-area, or AIS-coverage inference is made"
        ),
        "output_note": (
            "per-cell values are evidence diagnostics inside this JSON report; no "
            "production vessel-activity dataset is emitted"
        ),
    }


def _point_context_diagnostics(
    observations: Sequence[Observation], target_grid: TargetGridInspection
) -> dict[str, object]:
    geometries = [cell.geometry for cell in target_grid.cells]
    tree = STRtree(geometries)
    transformer = Transformer.from_crs(WGS84_CRS, PROJECTED_CRS, always_xy=True)
    counts = {group: [0 for _cell in target_grid.cells] for group in VESSEL_GROUPS}
    mmsi = {
        group: [set[str]() for _cell in target_grid.cells] for group in VESSEL_GROUPS
    }
    mmsi_dates = {
        group: [set[tuple[str, str]]() for _cell in target_grid.cells]
        for group in VESSEL_GROUPS
    }
    outside_counts = {group: 0 for group in VESSEL_GROUPS}
    ambiguous_counts = {group: 0 for group in VESSEL_GROUPS}
    for observation in observations:
        point = Point(
            _finite_xy(transformer, observation.longitude, observation.latitude)
        )
        matching_indices = [
            index
            for index in sorted(int(value) for value in tree.query(point))
            if geometries[index].covers(point)
        ]
        group = observation.vessel_type_group
        if not matching_indices:
            outside_counts[group] += 1
            continue
        if len(matching_indices) > 1:
            ambiguous_counts[group] += 1
            continue
        cell_order = matching_indices[0]
        counts[group][cell_order] += 1
        mmsi[group][cell_order].add(observation.mmsi)
        mmsi_dates[group][cell_order].add((observation.mmsi, observation.utc_date))

    per_cell: list[dict[str, object]] = []
    inside_count = 0
    for cell_order, cell in enumerate(target_grid.cells):
        observation_values = {
            group: counts[group][cell_order] for group in VESSEL_GROUPS
        }
        unique_mmsi_values = {
            group: len(mmsi[group][cell_order]) for group in VESSEL_GROUPS
        }
        unique_mmsi_date_values = {
            group: len(mmsi_dates[group][cell_order]) for group in VESSEL_GROUPS
        }
        union_mmsi = set().union(*(mmsi[group][cell_order] for group in VESSEL_GROUPS))
        union_mmsi_dates = set().union(
            *(mmsi_dates[group][cell_order] for group in VESSEL_GROUPS)
        )
        all_observations = sum(observation_values.values())
        inside_count += all_observations
        per_cell.append(
            {
                "cell_id": cell.cell_id,
                "observation_count": {
                    **observation_values,
                    ALL_COMMERCIAL: all_observations,
                },
                "distinct_mmsi": {
                    **unique_mmsi_values,
                    ALL_COMMERCIAL: len(union_mmsi),
                },
                "distinct_mmsi_date": {
                    **unique_mmsi_date_values,
                    ALL_COMMERCIAL: len(union_mmsi_dates),
                },
            }
        )
    outside_all = sum(outside_counts.values())
    ambiguous_all = sum(ambiguous_counts.values())
    return {
        "status": "cleaned-observation population context; not candidate-filtered",
        "population_note": (
            "point and distinct-vessel values describe all cleaned observations; "
            "candidate segment rules do not filter this population"
        ),
        "classification": (
            "a point is assigned only when exact support geometry covers it in "
            "exactly one cell; no match is outside support and multiple matches "
            "are ambiguous"
        ),
        "counts": {
            "cleaned_observation_count": len(observations),
            "in_support_observation_count": inside_count,
            "outside_support_observation_count": {
                **outside_counts,
                ALL_COMMERCIAL: outside_all,
            },
            "ambiguous_observation_count": {
                **ambiguous_counts,
                ALL_COMMERCIAL: ambiguous_all,
            },
            "conservation_passed": (
                inside_count + outside_all + ambiguous_all == len(observations)
            ),
        },
        "per_cell": per_cell,
    }


def allocate_segments_to_grid(
    segments: Sequence[CandidateSegment],
    target_grid: TargetGridInspection,
    *,
    population_label: str = "unfiltered structural baseline",
) -> dict[str, object]:
    """Allocate one named structural-candidate population for diagnostics only."""
    structural = tuple(segment for segment in segments if segment.structurally_eligible)
    cache = build_segment_piece_cache(structural, target_grid)
    return aggregate_segment_piece_cache(
        cache, structural, population_label=population_label
    )


def _grid_allocation_diagnostics(
    observations: Sequence[Observation],
    evaluation: CandidateSensitivityEvaluation,
    target_grid: TargetGridInspection,
) -> dict[str, object]:
    cache = build_segment_piece_cache(evaluation.structural_baseline, target_grid)
    baseline = aggregate_segment_piece_cache(
        cache,
        evaluation.structural_baseline,
        population_label="unfiltered structural baseline",
    )
    scenario_allocations: list[dict[str, object]] = []
    for scenario in evaluation.scenarios:
        allocation = aggregate_segment_piece_cache(
            cache,
            scenario.retained_segments,
            population_label=f"explicit candidate scenario {scenario.scenario_id}",
        )
        scenario_allocations.append(
            {
                "scenario_id": scenario.scenario_id,
                **scenario.rules(),
                "retained_segment_count": len(scenario.retained_segments),
                "allocation": allocation,
            }
        )
    return {
        "performed": True,
        "reusable_segment_piece_representation": {
            "status": "calculated once for the structural baseline and reused",
            "structural_parent_segment_count": len(cache.allocations),
            "cached_segment_piece_count": sum(
                len(allocation.pieces) for allocation in cache.allocations
            ),
            "candidate_population_count": len(evaluation.scenarios),
            "geometry_intersection_pass_count": 1,
            "scenario_behavior": (
                "candidate scenarios filter cached parent records and do not repeat "
                "Shapely segment/grid intersections"
            ),
        },
        "baseline": baseline,
        "candidate_scenarios": scenario_allocations,
        "cleaned_observation_point_context": _point_context_diagnostics(
            observations, target_grid
        ),
        "interpretation": (
            "the baseline remains unfiltered by gap, implied speed, or vessel length; "
            "candidate scenarios aggregate the same cached structural pieces"
        ),
    }


def build_evidence_report(
    bundle: CleanedBundleInspection,
    *,
    candidate_maximum_gap_seconds: Sequence[float] = (),
    candidate_implied_speed_ceiling_knots: Sequence[float] = (),
    candidate_minimum_vessel_length_m: Sequence[float] = (),
    target_grid: TargetGridInspection | None = None,
) -> dict[str, object]:
    """Build deterministic evidence content without writing or timing it."""
    segments = construct_candidate_segments(bundle.observations)
    sensitivity = _evaluate_candidate_sensitivity(
        segments,
        maximum_gap_seconds=candidate_maximum_gap_seconds,
        implied_speed_ceiling_knots=candidate_implied_speed_ceiling_knots,
        minimum_vessel_length_m=candidate_minimum_vessel_length_m,
    )
    report: dict[str, object] = {
        "contract": EVIDENCE_REPORT_CONTRACT,
        "processing_version": EVIDENCE_PROCESSING_VERSION,
        "status": "non-production evidence; no production vessel rule selected",
        "input": {
            "cleaned_parquet_sha256": bundle.cleaned_sha256,
            "cleaner_contract": AIS_PROCESSING_CONTRACT,
            "cleaner_run_id": bundle.cleaner_run_id,
            "temporal_coverage": dict(bundle.temporal_coverage),
            "read_only": True,
        },
        "local_provenance": {
            "identity_excluded": True,
            "cleaned_bundle_path": str(bundle.bundle_path),
            "cleaned_parquet_path": str(bundle.cleaned_path),
            "target_grid_path": None if target_grid is None else str(target_grid.path),
            "identity_note": (
                "local filesystem paths are execution provenance and do not affect "
                "report_id"
            ),
        },
        "ordering": {
            "keys": [
                "mmsi",
                "observed_at_utc",
                "latitude",
                "longitude",
                "vessel_type_code",
                "vessel_type_group",
            ],
            "pairing": "each observation with the next observation for the same MMSI",
            "duplicate_policy_precondition": "ADR 0013 cleaner output",
        },
        "observations": _grouped_observation_diagnostics(bundle.observations),
        "candidate_segments": _grouped_segment_diagnostics(segments),
        "candidate_rule_sensitivity": _candidate_sensitivity(sensitivity),
        "censoring_and_support_limitations": _censoring_diagnostics(
            bundle.observations
        ),
        "optional_grid_allocation": (
            {"performed": False}
            if target_grid is None
            else _grid_allocation_diagnostics(
                bundle.observations, sensitivity, target_grid
            )
        ),
        "prohibited_interpretations": [
            "not a production vessel-activity grid",
            "not an exposure layer",
            "not inside-versus-outside VSR statistics",
            "not evidence of uniform offshore observability",
            "candidate values are not accepted thresholds",
        ],
    }
    report["report_id"] = _content_report_id(report)
    return report


def _validate_output_path(output_path: Path, overwrite: bool) -> Path:
    resolved = output_path.resolve()
    if resolved == _PROJECT_RAW_ROOT or resolved.is_relative_to(_PROJECT_RAW_ROOT):
        raise VesselActivityEvidenceError(
            f"evidence output cannot be written under raw data: {resolved}"
        )
    if not (
        resolved == _PROJECT_INTERIM_ROOT
        or resolved.is_relative_to(_PROJECT_INTERIM_ROOT)
    ):
        raise VesselActivityEvidenceError(
            "evidence output must be an explicit path under ignored data/interim"
        )
    if resolved.suffix.lower() != ".json":
        raise VesselActivityEvidenceError("evidence output path must end in .json")
    if resolved.exists() and not resolved.is_file():
        raise VesselActivityEvidenceError(f"evidence output is not a file: {resolved}")
    if resolved.exists() and not overwrite:
        raise VesselActivityEvidenceError(
            "evidence output already exists; use explicit overwrite authorization"
        )
    if resolved.exists():
        existing = _read_json_object(resolved, "existing evidence output")
        if existing.get("contract") != EVIDENCE_REPORT_CONTRACT:
            raise VesselActivityEvidenceError(
                "overwrite only replaces an existing vessel-activity evidence report"
            )
    return resolved


def _replace_file(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def write_evidence_report(
    report: Mapping[str, object], output_path: Path, *, overwrite: bool = False
) -> tuple[str, str]:
    """Atomically write one deterministic report and return id and checksum."""
    resolved = _validate_output_path(output_path, overwrite)
    report_id = report.get("report_id")
    if report.get("contract") != EVIDENCE_REPORT_CONTRACT or not isinstance(
        report_id, str
    ):
        raise VesselActivityEvidenceError(
            "evidence report contract or report_id is invalid"
        )
    if report_id != _content_report_id(report):
        raise VesselActivityEvidenceError(
            "evidence report_id does not match deterministic report content"
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temporary = resolved.with_name(f".{resolved.name}.{uuid.uuid4().hex}.tmp")
    payload = (_canonical_json(dict(report)) + "\n").encode("utf-8")
    try:
        with temporary.open("xb") as destination:
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        _replace_file(temporary, resolved)
    except Exception as exc:
        raise VesselActivityEvidenceError(
            f"could not atomically write evidence report {resolved}: {exc}"
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)
    return report_id, hashlib.sha256(payload).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def run_evidence(
    bundle_path: Path,
    output_path: Path,
    config: ProcessingConfig,
    *,
    candidate_maximum_gap_seconds: Sequence[float] = (),
    candidate_implied_speed_ceiling_knots: Sequence[float] = (),
    candidate_minimum_vessel_length_m: Sequence[float] = (),
    grid_input: Path | None = None,
    expected_grid_sha256: str | None = None,
    overwrite: bool = False,
) -> EvidenceRunResult:
    """Inspect one explicit bundle and atomically publish one evidence report."""
    started_at = _utc_now()
    bundle = load_cleaned_bundle(bundle_path)
    if expected_grid_sha256 is not None and grid_input is None:
        raise VesselActivityEvidenceError(
            "expected grid checksum requires an explicit grid input"
        )
    target_grid = (
        None
        if grid_input is None
        else load_target_grid(
            grid_input.resolve(), config, expected_sha256=expected_grid_sha256
        )
    )
    report = build_evidence_report(
        bundle,
        candidate_maximum_gap_seconds=candidate_maximum_gap_seconds,
        candidate_implied_speed_ceiling_knots=candidate_implied_speed_ceiling_knots,
        candidate_minimum_vessel_length_m=candidate_minimum_vessel_length_m,
        target_grid=target_grid,
    )
    report_id, report_sha256 = write_evidence_report(
        report, output_path, overwrite=overwrite
    )
    completed_at = _utc_now()
    return EvidenceRunResult(
        report_path=output_path.resolve(),
        report_sha256=report_sha256,
        report_id=report_id,
        started_at=started_at,
        completed_at=completed_at,
    )
