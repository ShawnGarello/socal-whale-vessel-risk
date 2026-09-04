"""Bounded period-wide evidence for explicit candidate vessel rules.

The boundary consumes the verified multi-day DuckDB relation once as a globally
ordered observation/adjacency stream. It does not intersect segments with the
water grid, select a production rule, or calculate exposure.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final, Literal, cast

import duckdb
import pyarrow as pa
import pyproj
from pyproj import Geod, Transformer

from whale_vessel_analysis.cleaned_ais_bundle import canonical_json, sha256_file
from whale_vessel_analysis.config import PROJECTED_CRS
from whale_vessel_analysis.lineage import (
    ArtifactReference,
    ProcessingStep,
    RunMetadata,
    ValidationRecord,
)
from whale_vessel_analysis.multiday_ais import accepted_utc_dates
from whale_vessel_analysis.multiday_ais_relation import PeriodRelation
from whale_vessel_analysis.vessel_grid import (
    ALL_COMMERCIAL,
    KNOTS_PER_METRE_PER_SECOND,
    LENGTH_TOLERANCE_M,
    VESSEL_GROUPS,
)

EVIDENCE_CONTRACT: Final = "period_vessel_rule_evidence_v1"
EVIDENCE_LINEAGE_CONTRACT: Final = "period_vessel_rule_evidence_lineage_v1"
EVIDENCE_SCHEMA_VERSION: Final = 1
EVIDENCE_PROCESSING_VERSION: Final = "1.0.0"
EVIDENCE_ID_PREFIX: Final = "period-vessel-rule-evidence-"
EVIDENCE_FILENAME: Final = "evidence.json"
RUN_METADATA_FILENAME: Final = "run-metadata.json"
EVIDENCE_BUNDLE_FILENAMES: Final = (EVIDENCE_FILENAME, RUN_METADATA_FILENAME)
REQUIRED_MAXIMUM_GAP_SECONDS: Final = (300.0, 1_800.0)
REQUIRED_IMPLIED_SPEED_CEILING_KNOTS: Final = (30.0, 50.0)
VESSEL_LENGTH_TREATMENT: Final = "type-only-no-length-filter"
WGS84_CRS: Final = "EPSG:4326"
PERIOD_KEY: Final = "whole_period"
DAILY_SEGMENT_ACCOUNTING: Final = "starting-observation-utc-date"
ACCEPTED_UTC_DATES: Final = accepted_utc_dates()
ACCEPTED_UTC_DATE_SET: Final = frozenset(ACCEPTED_UTC_DATES)

TIME_GAP_EDGES: Final = (
    0.0,
    30.0,
    60.0,
    90.0,
    120.0,
    180.0,
    300.0,
    600.0,
    900.0,
    1_800.0,
    3_600.0,
    7_200.0,
    21_600.0,
    86_400.0,
)
DISTANCE_EDGES_M: Final = (
    0.0,
    1.0,
    10.0,
    100.0,
    500.0,
    1_000.0,
    2_500.0,
    5_000.0,
    10_000.0,
    25_000.0,
    50_000.0,
    100_000.0,
)
DISTANCE_DIFFERENCE_EDGES_M: Final = (
    -100.0,
    -10.0,
    -1.0,
    -0.1,
    -0.01,
    0.0,
    0.01,
    0.1,
    1.0,
    10.0,
    100.0,
)
SPEED_EDGES_KNOTS: Final = (
    0.0,
    0.1,
    1.0,
    5.0,
    10.0,
    15.0,
    20.0,
    30.0,
    40.0,
    50.0,
    75.0,
    100.0,
    250.0,
    1_000.0,
)
LENGTH_EDGES_M: Final = (
    0.0,
    20.0,
    50.0,
    100.0,
    150.0,
    200.0,
    250.0,
    300.0,
    400.0,
    500.0,
)

_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
_PROJECT_RAW_ROOT: Final = (_PROJECT_ROOT / "data" / "raw").resolve()
_PROJECT_INTERIM_ROOT: Final = (_PROJECT_ROOT / "data" / "interim").resolve()

VesselLengthTreatment = Literal["type-only-no-length-filter"]


class PeriodVesselRuleEvidenceError(ValueError):
    """Raised when period evidence input, processing, or output is invalid."""


def _validated_required_values(
    supplied: Sequence[float], required: tuple[float, ...], label: str
) -> tuple[float, ...]:
    values = tuple(float(value) for value in supplied)
    if not values:
        raise PeriodVesselRuleEvidenceError(f"{label} values must be supplied")
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise PeriodVesselRuleEvidenceError(
            f"{label} values must be finite and positive"
        )
    if len(values) != len(set(values)):
        raise PeriodVesselRuleEvidenceError(f"{label} values must not be duplicated")
    normalized = tuple(sorted(values))
    if normalized != required:
        rendered = ", ".join(format(value, "g") for value in required)
        raise PeriodVesselRuleEvidenceError(
            f"{label} values must explicitly contain the ADR 0018 matrix: {rendered}"
        )
    return normalized


@dataclass(frozen=True, slots=True)
class PeriodVesselRuleParameters:
    """The complete explicit ADR 0018 candidate matrix and length treatment."""

    maximum_gap_seconds: tuple[float, ...]
    implied_speed_ceiling_knots: tuple[float, ...]
    vessel_length_treatment: VesselLengthTreatment
    allow_incomplete_non_production: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "maximum_gap_seconds",
            _validated_required_values(
                self.maximum_gap_seconds,
                REQUIRED_MAXIMUM_GAP_SECONDS,
                "maximum-gap",
            ),
        )
        object.__setattr__(
            self,
            "implied_speed_ceiling_knots",
            _validated_required_values(
                self.implied_speed_ceiling_knots,
                REQUIRED_IMPLIED_SPEED_CEILING_KNOTS,
                "implied-speed ceiling",
            ),
        )
        if self.vessel_length_treatment != VESSEL_LENGTH_TREATMENT:
            raise PeriodVesselRuleEvidenceError(
                "vessel-length treatment must explicitly retain the type-only "
                "population without a length filter"
            )

    @property
    def require_ready_period(self) -> bool:
        return not self.allow_incomplete_non_production

    def to_dict(self) -> dict[str, object]:
        return {
            "maximum_gap_seconds": list(self.maximum_gap_seconds),
            "implied_speed_ceiling_knots": list(self.implied_speed_ceiling_knots),
            "vessel_length_treatment": self.vessel_length_treatment,
            "period_readiness_treatment": (
                "allow-incomplete-non-production"
                if self.allow_incomplete_non_production
                else "require-ready"
            ),
            "implicit_methodological_defaults": False,
            "method_status": "candidate evidence only; no rule is accepted",
        }


@dataclass(frozen=True, slots=True)
class PeriodEvidenceInputReference:
    """Stable period identity plus non-identity local manifest provenance."""

    manifest_path: Path
    manifest_sha256: str
    period_input_id: str
    period_input_readiness: Mapping[str, object]
    independent_transfer_completeness: Mapping[str, object]
    observational_completeness: Mapping[str, object]

    def stable_dict(self) -> dict[str, object]:
        return {
            "period_input_id": self.period_input_id,
            "period_input_readiness": dict(self.period_input_readiness),
            "independent_transfer_completeness": dict(
                self.independent_transfer_completeness
            ),
            "observational_completeness": dict(self.observational_completeness),
        }


@dataclass(frozen=True, slots=True)
class CandidateRule:
    maximum_gap_seconds: float
    implied_speed_ceiling_knots: float
    candidate_id: str

    @classmethod
    def create(cls, gap: float, speed: float) -> CandidateRule:
        material = {
            "maximum_gap_seconds": gap,
            "implied_speed_ceiling_knots": speed,
        }
        candidate_id = (
            "candidate-rule-"
            + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:16]
        )
        return cls(gap, speed, candidate_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "maximum_gap_seconds": self.maximum_gap_seconds,
            "implied_speed_ceiling_knots": self.implied_speed_ceiling_knots,
        }


@dataclass(slots=True)
class BoundedDistribution:
    """Exact scalar aggregates plus fixed-bin counts with constant memory."""

    edges: tuple[float, ...]
    count: int = 0
    minimum: float | None = None
    maximum: float | None = None
    total: float = 0.0
    bins: list[int] = field(init=False)

    def __post_init__(self) -> None:
        self.bins = [0] * (len(self.edges) + 1)

    def add(self, value: float) -> None:
        if not math.isfinite(value):
            raise PeriodVesselRuleEvidenceError(
                "a non-finite value reached a bounded distribution"
            )
        self.count += 1
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        self.total += value
        index = 0
        while index < len(self.edges) and value >= self.edges[index]:
            index += 1
        self.bins[index] += 1

    def to_dict(self) -> dict[str, object]:
        if self.count == 0:
            return {
                "count": 0,
                "minimum": None,
                "maximum": None,
                "sum": 0.0,
                "mean": None,
                "bin_counts": self.bins,
            }
        return {
            "count": self.count,
            "minimum": _round(cast(float, self.minimum)),
            "maximum": _round(cast(float, self.maximum)),
            "sum": _round(self.total),
            "mean": _round(self.total / self.count),
            "bin_counts": self.bins,
        }


@dataclass(slots=True)
class CandidateCounts:
    retained: int = 0
    zero_length_retained: int = 0
    cross_midnight_retained: int = 0
    retained_projected_distance_m: float = 0.0
    retained_geodesic_distance_m: float = 0.0
    exclusions: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def exclude(self, reason: str) -> None:
        self.exclusions[reason] += 1

    def to_dict(self, candidate_segments: int) -> dict[str, object]:
        ordered_reasons = (
            "invalid_coordinate_transform",
            "non_increasing_time",
            "vessel_group_change",
            "maximum_gap",
            "implied_speed",
        )
        exclusions = {reason: self.exclusions[reason] for reason in ordered_reasons}
        excluded = sum(exclusions.values())
        if candidate_segments != self.retained + excluded:
            raise PeriodVesselRuleEvidenceError(
                "candidate rule counts do not reconcile with structural segments"
            )
        return {
            "retained_segments": self.retained,
            "excluded_segments": excluded,
            "primary_exclusions": exclusions,
            "zero_length_retained_segments": self.zero_length_retained,
            "cross_midnight_retained_segments": self.cross_midnight_retained,
            "retained_projected_endpoint_distance_m": _round(
                self.retained_projected_distance_m
            ),
            "retained_geodesic_endpoint_distance_m": _round(
                self.retained_geodesic_distance_m
            ),
        }


@dataclass(slots=True)
class PopulationSummary:
    observation_count: int = 0
    invalid_coordinate_observation_count: int = 0
    sog_available_count: int = 0
    sog_unavailable_count: int = 0
    sog_invalid_count: int = 0
    length_valid_count: int = 0
    length_missing_count: int = 0
    length_invalid_count: int = 0
    structural_segment_count: int = 0
    non_increasing_timestamp_count: int = 0
    vessel_group_change_count: int = 0
    invalid_coordinate_segment_count: int = 0
    zero_length_segment_count: int = 0
    cross_midnight_segment_count: int = 0
    time_gap: BoundedDistribution = field(
        default_factory=lambda: BoundedDistribution(TIME_GAP_EDGES)
    )
    projected_distance: BoundedDistribution = field(
        default_factory=lambda: BoundedDistribution(DISTANCE_EDGES_M)
    )
    geodesic_distance: BoundedDistribution = field(
        default_factory=lambda: BoundedDistribution(DISTANCE_EDGES_M)
    )
    projected_minus_geodesic: BoundedDistribution = field(
        default_factory=lambda: BoundedDistribution(DISTANCE_DIFFERENCE_EDGES_M)
    )
    implied_speed: BoundedDistribution = field(
        default_factory=lambda: BoundedDistribution(SPEED_EDGES_KNOTS)
    )
    reported_sog: BoundedDistribution = field(
        default_factory=lambda: BoundedDistribution(SPEED_EDGES_KNOTS)
    )
    vessel_length: BoundedDistribution = field(
        default_factory=lambda: BoundedDistribution(LENGTH_EDGES_M)
    )
    candidates: dict[str, CandidateCounts] = field(default_factory=dict)

    def ensure_candidates(self, rules: Sequence[CandidateRule]) -> None:
        if not self.candidates:
            self.candidates = {rule.candidate_id: CandidateCounts() for rule in rules}

    def to_dict(
        self,
        rules: Sequence[CandidateRule],
        distinct: Mapping[str, int],
    ) -> dict[str, object]:
        if self.observation_count != (
            self.sog_available_count
            + self.sog_unavailable_count
            + self.sog_invalid_count
        ):
            raise PeriodVesselRuleEvidenceError(
                "reported-SOG availability does not reconcile with observations"
            )
        if self.observation_count != (
            self.length_valid_count
            + self.length_missing_count
            + self.length_invalid_count
        ):
            raise PeriodVesselRuleEvidenceError(
                "vessel-length availability does not reconcile with observations"
            )
        return {
            "cleaned_observations": self.observation_count,
            "distinct_mmsi": distinct["distinct_mmsi"],
            "distinct_mmsi_date_combinations": distinct["distinct_mmsi_dates"],
            "observation_quality": {
                "invalid_coordinate_values": self.invalid_coordinate_observation_count,
                "reported_sog": {
                    "available": self.sog_available_count,
                    "unavailable_null": self.sog_unavailable_count,
                    "invalid_retained_value": self.sog_invalid_count,
                    "available_value_distribution_knots": self.reported_sog.to_dict(),
                },
                "vessel_length": {
                    "valid": self.length_valid_count,
                    "missing_or_upstream_invalid_null": self.length_missing_count,
                    "invalid_retained_value": self.length_invalid_count,
                    "valid_value_distribution_m": self.vessel_length.to_dict(),
                },
            },
            "structural_segments": {
                "candidate_segments": self.structural_segment_count,
                "non_increasing_timestamps": self.non_increasing_timestamp_count,
                "vessel_group_changes": self.vessel_group_change_count,
                "invalid_coordinate_transform": self.invalid_coordinate_segment_count,
                "zero_length_movement": self.zero_length_segment_count,
                "cross_midnight": self.cross_midnight_segment_count,
                "time_gap_seconds": self.time_gap.to_dict(),
                "projected_endpoint_distance_m": self.projected_distance.to_dict(),
                "wgs84_geodesic_endpoint_distance_m": (
                    self.geodesic_distance.to_dict()
                ),
                "projected_minus_geodesic_distance_m": (
                    self.projected_minus_geodesic.to_dict()
                ),
                "implied_speed_knots": self.implied_speed.to_dict(),
            },
            "candidate_matrix": [
                {
                    **rule.to_dict(),
                    **self.candidates[rule.candidate_id].to_dict(
                        self.structural_segment_count
                    ),
                }
                for rule in rules
            ],
        }


@dataclass(frozen=True, slots=True)
class EvidenceExecutionStats:
    arrow_record_batches: int
    maximum_arrow_batch_rows: int
    streamed_observations: int

    def to_dict(self) -> dict[str, int]:
        return {
            "arrow_record_batches": self.arrow_record_batches,
            "maximum_arrow_batch_rows": self.maximum_arrow_batch_rows,
            "streamed_observations": self.streamed_observations,
        }


@dataclass(frozen=True, slots=True)
class PeriodVesselRuleEvidenceDataset:
    evidence_id: str
    document: Mapping[str, object]
    period_input: PeriodEvidenceInputReference
    partition_paths: tuple[Path, ...]
    parameters: PeriodVesselRuleParameters
    batch_size: int
    execution_stats: EvidenceExecutionStats


@dataclass(frozen=True, slots=True)
class PeriodVesselRuleEvidenceWriteResult:
    output_directory: Path
    evidence_path: Path
    lineage_path: Path
    evidence_id: str
    evidence_sha256: str
    lineage_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": EVIDENCE_CONTRACT,
            "processing_version": EVIDENCE_PROCESSING_VERSION,
            "status": "candidate methodological evidence; no rule is accepted",
            "evidence_id": self.evidence_id,
            "output": {
                "directory": str(self.output_directory),
                "evidence": {
                    "path": str(self.evidence_path),
                    "sha256": self.evidence_sha256,
                },
                "run_metadata": {
                    "path": str(self.lineage_path),
                    "sha256": self.lineage_sha256,
                },
            },
        }


def _round(value: float) -> float:
    return round(value, 12)


def _datetime_value(value: object, label: str) -> datetime:
    if isinstance(value, int) and not isinstance(value, bool):
        return datetime.fromtimestamp(value / 1_000_000.0, UTC)
    if isinstance(value, datetime) and value.utcoffset() is not None:
        return value.astimezone(UTC)
    raise PeriodVesselRuleEvidenceError(f"bounded relation has invalid {label}")


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float) or isinstance(value, bool):
        return math.nan
    return float(value)


def _valid_coordinate(latitude: float | None, longitude: float | None) -> bool:
    return (
        latitude is not None
        and longitude is not None
        and math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90.0 <= latitude <= 90.0
        and -180.0 <= longitude <= 180.0
    )


def _group(value: object) -> str:
    if not isinstance(value, str) or value not in VESSEL_GROUPS:
        raise PeriodVesselRuleEvidenceError(
            "bounded relation contains an unsupported or ambiguous vessel group"
        )
    return value


def _rules(parameters: PeriodVesselRuleParameters) -> tuple[CandidateRule, ...]:
    return tuple(
        CandidateRule.create(gap, speed)
        for gap in parameters.maximum_gap_seconds
        for speed in parameters.implied_speed_ceiling_knots
    )


def _distribution_contract() -> dict[str, object]:
    return {
        "representation": "exact scalar aggregates plus fixed half-open bins",
        "memory_behavior": (
            "each distribution stores count, min, max, running sum, and one "
            "counter per fixed bin; individual observation and segment values are "
            "not retained"
        ),
        "bin_semantics": (
            "bin 0 is below the first edge; interior bins are lower-inclusive and "
            "upper-exclusive; the final bin is greater than or equal to the last edge"
        ),
        "edges": {
            "time_gap_seconds": list(TIME_GAP_EDGES),
            "endpoint_distance_m": list(DISTANCE_EDGES_M),
            "projected_minus_geodesic_distance_m": list(DISTANCE_DIFFERENCE_EDGES_M),
            "speed_knots": list(SPEED_EDGES_KNOTS),
            "vessel_length_m": list(LENGTH_EDGES_M),
        },
        "percentiles": "not calculated; fixed bins avoid retaining full populations",
    }


def _summary_keys(utc_date: str, group: str) -> tuple[tuple[str, str], ...]:
    return (
        (utc_date, group),
        (utc_date, ALL_COMMERCIAL),
        (PERIOD_KEY, group),
        (PERIOD_KEY, ALL_COMMERCIAL),
    )


def _new_summaries(
    rules: Sequence[CandidateRule],
) -> dict[tuple[str, str], PopulationSummary]:
    summaries: dict[tuple[str, str], PopulationSummary] = {}
    for date_key in (*ACCEPTED_UTC_DATES, PERIOD_KEY):
        for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
            summary = PopulationSummary()
            summary.ensure_candidates(rules)
            summaries[(date_key, group)] = summary
    return summaries


def _distinct_observation_counts(
    relation: PeriodRelation,
) -> dict[tuple[str, str], dict[str, int]]:
    query = f"""
        SELECT
            CASE WHEN grouping(observed_utc_date) = 1
                 THEN '{PERIOD_KEY}' ELSE cast(observed_utc_date AS VARCHAR) END,
            CASE WHEN grouping(vessel_type_group) = 1
                 THEN '{ALL_COMMERCIAL}' ELSE vessel_type_group END,
            count(*),
            count(DISTINCT mmsi),
            count(DISTINCT (mmsi, observed_utc_date))
        FROM {relation.view_name}
        GROUP BY GROUPING SETS (
            (observed_utc_date, vessel_type_group),
            (observed_utc_date),
            (vessel_type_group),
            ()
        )
        ORDER BY 1, 2
    """
    try:
        rows = relation.connection.execute(query).fetchall()
    except duckdb.Error as exc:
        raise PeriodVesselRuleEvidenceError(
            f"could not compute exact distinct observation counts: {exc}"
        ) from exc
    result: dict[tuple[str, str], dict[str, int]] = {}
    for row in rows:
        key = (str(row[0]), str(row[1]))
        result[key] = {
            "observations": int(cast(int, row[2])),
            "distinct_mmsi": int(cast(int, row[3])),
            "distinct_mmsi_dates": int(cast(int, row[4])),
        }
    for date_key in (*ACCEPTED_UTC_DATES, PERIOD_KEY):
        for group in (*VESSEL_GROUPS, ALL_COMMERCIAL):
            result.setdefault(
                (date_key, group),
                {"observations": 0, "distinct_mmsi": 0, "distinct_mmsi_dates": 0},
            )
    return result


def _record_observation(summary: PopulationSummary, row: Mapping[str, object]) -> None:
    summary.observation_count += 1
    latitude = _optional_float(row.get("latitude"))
    longitude = _optional_float(row.get("longitude"))
    if not _valid_coordinate(latitude, longitude):
        summary.invalid_coordinate_observation_count += 1

    sog = _optional_float(row.get("sog_knots"))
    if sog is None:
        summary.sog_unavailable_count += 1
    elif not math.isfinite(sog) or sog < 0:
        summary.sog_invalid_count += 1
    else:
        summary.sog_available_count += 1
        summary.reported_sog.add(sog)

    length = _optional_float(row.get("length_m"))
    if length is None:
        summary.length_missing_count += 1
    elif not math.isfinite(length) or length < 0:
        summary.length_invalid_count += 1
    else:
        summary.length_valid_count += 1
        summary.vessel_length.add(length)


def _candidate_primary_reason(
    *,
    coordinate_valid: bool,
    elapsed_seconds: float,
    group_changed: bool,
    implied_speed_knots: float | None,
    rule: CandidateRule,
) -> str | None:
    if not coordinate_valid:
        return "invalid_coordinate_transform"
    if elapsed_seconds <= 0:
        return "non_increasing_time"
    if group_changed:
        return "vessel_group_change"
    if elapsed_seconds > rule.maximum_gap_seconds:
        return "maximum_gap"
    if (
        implied_speed_knots is not None
        and implied_speed_knots > rule.implied_speed_ceiling_knots
    ):
        return "implied_speed"
    return None


def _record_segment(
    summary: PopulationSummary,
    *,
    elapsed_seconds: float,
    projected_distance_m: float | None,
    geodesic_distance_m: float | None,
    implied_speed_knots: float | None,
    group_changed: bool,
    cross_midnight: bool,
    rules: Sequence[CandidateRule],
) -> None:
    summary.structural_segment_count += 1
    summary.time_gap.add(elapsed_seconds)
    coordinate_valid = (
        projected_distance_m is not None and geodesic_distance_m is not None
    )
    if not coordinate_valid:
        summary.invalid_coordinate_segment_count += 1
    else:
        projected = cast(float, projected_distance_m)
        geodesic = cast(float, geodesic_distance_m)
        summary.projected_distance.add(projected)
        summary.geodesic_distance.add(geodesic)
        summary.projected_minus_geodesic.add(projected - geodesic)
        if projected <= LENGTH_TOLERANCE_M:
            summary.zero_length_segment_count += 1
    if elapsed_seconds <= 0:
        summary.non_increasing_timestamp_count += 1
    if group_changed:
        summary.vessel_group_change_count += 1
    if cross_midnight:
        summary.cross_midnight_segment_count += 1
    if implied_speed_knots is not None:
        summary.implied_speed.add(implied_speed_knots)

    for rule in rules:
        candidate = summary.candidates[rule.candidate_id]
        reason = _candidate_primary_reason(
            coordinate_valid=coordinate_valid,
            elapsed_seconds=elapsed_seconds,
            group_changed=group_changed,
            implied_speed_knots=implied_speed_knots,
            rule=rule,
        )
        if reason is not None:
            candidate.exclude(reason)
            continue
        candidate.retained += 1
        projected = cast(float, projected_distance_m)
        geodesic = cast(float, geodesic_distance_m)
        candidate.retained_projected_distance_m += projected
        candidate.retained_geodesic_distance_m += geodesic
        if projected <= LENGTH_TOLERANCE_M:
            candidate.zero_length_retained += 1
        if cross_midnight:
            candidate.cross_midnight_retained += 1


def _stream_summaries(
    relation: PeriodRelation,
    rules: Sequence[CandidateRule],
    *,
    batch_size: int,
) -> tuple[dict[tuple[str, str], PopulationSummary], EvidenceExecutionStats]:
    if batch_size < 1:
        raise PeriodVesselRuleEvidenceError("batch size must be at least one")
    summaries = _new_summaries(rules)
    transformer = Transformer.from_crs(WGS84_CRS, PROJECTED_CRS, always_xy=True)
    geod = Geod(ellps="WGS84")
    batch_count = 0
    maximum_batch_rows = 0
    streamed_observations = 0
    try:
        reader = relation.adjacent_observation_batches(batch_size)
        for batch in reader:
            batch_count += 1
            maximum_batch_rows = max(maximum_batch_rows, batch.num_rows)
            rows = cast(list[dict[str, object]], batch.to_pylist())
            streamed_observations += len(rows)
            projected_by_row: dict[int, tuple[float, float]] = {}
            coordinate_rows: list[int] = []
            start_longitudes: list[float] = []
            start_latitudes: list[float] = []
            end_longitudes: list[float] = []
            end_latitudes: list[float] = []
            for row_index, row in enumerate(rows):
                if row.get("next_observed_at_utc") is None:
                    continue
                start_lat = _optional_float(row.get("latitude"))
                start_lon = _optional_float(row.get("longitude"))
                end_lat = _optional_float(row.get("next_latitude"))
                end_lon = _optional_float(row.get("next_longitude"))
                if not (
                    _valid_coordinate(start_lat, start_lon)
                    and _valid_coordinate(end_lat, end_lon)
                ):
                    continue
                coordinate_rows.append(row_index)
                start_longitudes.append(cast(float, start_lon))
                start_latitudes.append(cast(float, start_lat))
                end_longitudes.append(cast(float, end_lon))
                end_latitudes.append(cast(float, end_lat))
            if coordinate_rows:
                start_x, start_y = transformer.transform(
                    start_longitudes, start_latitudes
                )
                end_x, end_y = transformer.transform(end_longitudes, end_latitudes)
                _azimuth_1, _azimuth_2, geodesic_values = geod.inv(
                    start_longitudes,
                    start_latitudes,
                    end_longitudes,
                    end_latitudes,
                )
                for position, row_index in enumerate(coordinate_rows):
                    xy = (
                        float(start_x[position]),
                        float(start_y[position]),
                        float(end_x[position]),
                        float(end_y[position]),
                    )
                    geodesic = float(geodesic_values[position])
                    if all(math.isfinite(value) for value in xy) and math.isfinite(
                        geodesic
                    ):
                        projected_by_row[row_index] = (
                            math.hypot(xy[2] - xy[0], xy[3] - xy[1]),
                            abs(geodesic),
                        )

            for row_index, row in enumerate(rows):
                group = _group(row.get("vessel_type_group"))
                start = _datetime_value(row.get("observed_at_utc"), "timestamp")
                utc_date = start.date().isoformat()
                if utc_date not in ACCEPTED_UTC_DATE_SET:
                    raise PeriodVesselRuleEvidenceError(
                        f"bounded relation contains unexpected UTC date {utc_date}"
                    )
                keys = _summary_keys(utc_date, group)
                for key in keys:
                    _record_observation(summaries[key], row)

                next_value = row.get("next_observed_at_utc")
                if next_value is None:
                    continue
                end = _datetime_value(next_value, "next timestamp")
                elapsed_seconds = (end - start).total_seconds()
                next_group = row.get("next_vessel_type_group")
                group_changed = next_group != group
                distances = projected_by_row.get(row_index)
                projected_distance = None if distances is None else distances[0]
                geodesic_distance = None if distances is None else distances[1]
                implied_speed: float | None = None
                if projected_distance is not None and elapsed_seconds > 0:
                    implied_speed = (
                        projected_distance
                        / elapsed_seconds
                        * KNOTS_PER_METRE_PER_SECOND
                    )
                cross_midnight = start.date() != end.date()
                for key in keys:
                    _record_segment(
                        summaries[key],
                        elapsed_seconds=elapsed_seconds,
                        projected_distance_m=projected_distance,
                        geodesic_distance_m=geodesic_distance,
                        implied_speed_knots=implied_speed,
                        group_changed=group_changed,
                        cross_midnight=cross_midnight,
                        rules=rules,
                    )
    except duckdb.Error as exc:
        raise PeriodVesselRuleEvidenceError(
            f"could not stream whole-period candidate segments: {exc}"
        ) from exc
    return summaries, EvidenceExecutionStats(
        arrow_record_batches=batch_count,
        maximum_arrow_batch_rows=maximum_batch_rows,
        streamed_observations=streamed_observations,
    )


def _serialized_summaries(
    summaries: Mapping[tuple[str, str], PopulationSummary],
    distinct: Mapping[tuple[str, str], Mapping[str, int]],
    rules: Sequence[CandidateRule],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    period: dict[str, object] = {
        group: summaries[(PERIOD_KEY, group)].to_dict(
            rules, distinct[(PERIOD_KEY, group)]
        )
        for group in (*VESSEL_GROUPS, ALL_COMMERCIAL)
    }
    daily: list[dict[str, object]] = [
        {
            "utc_date": utc_date,
            "by_vessel_group": {
                group: summaries[(utc_date, group)].to_dict(
                    rules, distinct[(utc_date, group)]
                )
                for group in (*VESSEL_GROUPS, ALL_COMMERCIAL)
            },
        }
        for utc_date in ACCEPTED_UTC_DATES
    ]
    return period, daily


def build_period_vessel_rule_evidence(
    relation: PeriodRelation,
    period_input: PeriodEvidenceInputReference,
    parameters: PeriodVesselRuleParameters,
    *,
    batch_size: int,
) -> PeriodVesselRuleEvidenceDataset:
    """Build deterministic evidence from one bounded ordered structural stream."""
    readiness = period_input.period_input_readiness.get("status")
    if parameters.require_ready_period and readiness != "ready":
        raise PeriodVesselRuleEvidenceError(
            "production period evidence requires a ready manifest containing all "
            "153 accepted UTC dates"
        )
    rules = _rules(parameters)
    distinct = _distinct_observation_counts(relation)
    summaries, execution_stats = _stream_summaries(
        relation, rules, batch_size=batch_size
    )
    for key, counts in distinct.items():
        if summaries[key].observation_count != counts["observations"]:
            raise PeriodVesselRuleEvidenceError(
                "streamed observations do not reconcile with exact SQL counts"
            )
    period, daily = _serialized_summaries(summaries, distinct, rules)
    partitions = [partition.to_dict() for partition in relation.partitions]
    document: dict[str, object] = {
        "contract": EVIDENCE_CONTRACT,
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "processing_version": EVIDENCE_PROCESSING_VERSION,
        "status": "candidate methodological evidence; no rule is accepted",
        "input": {
            **period_input.stable_dict(),
            "partition_count": len(partitions),
            "partitions": partitions,
            "local_partition_checksums_reverified": True,
        },
        "parameters": parameters.to_dict(),
        "candidate_rules": [rule.to_dict() for rule in rules],
        "ordering_and_accounting": {
            "whole_period_order": [
                "mmsi",
                "observed_at_utc",
                "latitude",
                "longitude",
                "vessel_type_code",
                "vessel_type_group",
            ],
            "pairing": (
                "lead within MMSI across the whole period; UTC date is not a "
                "partition boundary"
            ),
            "daily_segment_accounting": DAILY_SEGMENT_ACCOUNTING,
            "daily_segment_accounting_note": (
                "a segment is assigned to the UTC date of its starting observation; "
                "cross-midnight segments are also reported separately and remain "
                "paired across the date boundary"
            ),
            "candidate_exclusion_precedence": [
                "invalid_coordinate_transform",
                "non_increasing_time",
                "vessel_group_change",
                "maximum_gap",
                "implied_speed",
            ],
            "candidate_evaluation": (
                "all four rules are evaluated from the same ordered structural-"
                "segment stream"
            ),
        },
        "distribution_contract": _distribution_contract(),
        "whole_period_by_vessel_group": period,
        "daily_by_utc_date": daily,
        "reconciliation": {
            "passed": True,
            "commercial_union_method": (
                "all-commercial observation and segment populations are updated "
                "from underlying rows; exact distinct MMSI and MMSI-date counts "
                "are recomputed in DuckDB from the commercial union and are never "
                "formed by adding group distinct counts"
            ),
            "bounded_iteration": (
                "DuckDB owns global ordering and exact distinct aggregation; one "
                "ordered Arrow stream is consumed in bounded batches; summaries "
                "retain only scalar aggregates and fixed-bin counters"
            ),
        },
        "evidence_state_distinctions": {
            "ready_cleaned_input_coverage": dict(period_input.period_input_readiness),
            "local_checksum_identity": "verified before relation scanning",
            "publisher_side_transfer_completeness": dict(
                period_input.independent_transfer_completeness
            ),
            "ais_observational_completeness": dict(
                period_input.observational_completeness
            ),
            "candidate_methodological_evidence": "generated by this boundary",
            "accepted_production_rules": "none; ADR 0018 remains Proposed",
        },
        "preserved_populations": {
            "upstream_source_record_removals": (
                "unsupported vessel types, invalid source values, duplicates, and "
                "conflicting MMSI/timestamp rows remain owned and counted by each "
                "one-date cleaner quality report; this boundary does not count them "
                "again"
            ),
            "structural_and_candidate_exclusions": (
                "all input adjacencies receive diagnostics and each candidate rule "
                "assigns exactly one primary retained/excluded outcome"
            ),
            "zero_length_movement": (
                "retained when other candidate rules pass and reported separately; "
                "no movement is invented"
            ),
            "vessel_length": (
                "no length filter is applied; valid, null, and unexpected invalid "
                "retained values are reported separately"
            ),
        },
        "scope_and_limitations": {
            "not_a_grid": (
                "segments are not intersected with the spatial grid; the existing "
                "candidate vessel-grid command owns spatial allocation"
            ),
            "edge_support": (
                "the upstream cleaner censors observations at the map/context "
                "extent; no missing entry or exit path is extrapolated"
            ),
            "not_produced": [
                "accepted production vessel rules",
                "production vessel grid",
                "relative exposure",
                "inside-versus-outside VSR statistics",
                "exposure layer",
            ],
        },
    }
    evidence_id = (
        EVIDENCE_ID_PREFIX
        + hashlib.sha256(canonical_json(document).encode("utf-8")).hexdigest()[:24]
    )
    document["evidence_id"] = evidence_id
    validate_evidence_document(document)
    return PeriodVesselRuleEvidenceDataset(
        evidence_id=evidence_id,
        document=document,
        period_input=period_input,
        partition_paths=tuple(
            partition.cleaned_path for partition in relation.partitions
        ),
        parameters=parameters,
        batch_size=batch_size,
        execution_stats=execution_stats,
    )


def validate_evidence_document(document: Mapping[str, object]) -> None:
    """Validate the deterministic evidence contract before atomic publication."""
    if document.get("contract") != EVIDENCE_CONTRACT:
        raise PeriodVesselRuleEvidenceError("unsupported evidence contract")
    if document.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise PeriodVesselRuleEvidenceError("unsupported evidence schema version")
    if document.get("processing_version") != EVIDENCE_PROCESSING_VERSION:
        raise PeriodVesselRuleEvidenceError("unsupported evidence processing version")
    evidence_id = document.get("evidence_id")
    if not isinstance(evidence_id, str):
        raise PeriodVesselRuleEvidenceError("evidence document has no valid identity")
    identity = dict(document)
    del identity["evidence_id"]
    expected_id = (
        EVIDENCE_ID_PREFIX
        + hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()[:24]
    )
    if evidence_id != expected_id:
        raise PeriodVesselRuleEvidenceError(
            "evidence identity does not match deterministic content"
        )
    daily = document.get("daily_by_utc_date")
    if not isinstance(daily, list):
        raise PeriodVesselRuleEvidenceError("daily evidence must be a list")
    dates = [item.get("utc_date") for item in daily if isinstance(item, Mapping)]
    if dates != list(ACCEPTED_UTC_DATES):
        raise PeriodVesselRuleEvidenceError(
            "daily evidence must contain every accepted UTC date exactly once"
        )
    rules = document.get("candidate_rules")
    if not isinstance(rules, list) or len(rules) != 4:
        raise PeriodVesselRuleEvidenceError(
            "evidence must contain all four explicit candidate rules"
        )
    combinations = {
        (
            item.get("maximum_gap_seconds"),
            item.get("implied_speed_ceiling_knots"),
        )
        for item in rules
        if isinstance(item, Mapping)
    }
    expected = {
        (gap, speed)
        for gap in REQUIRED_MAXIMUM_GAP_SECONDS
        for speed in REQUIRED_IMPLIED_SPEED_CEILING_KNOTS
    }
    if combinations != expected:
        raise PeriodVesselRuleEvidenceError(
            "evidence candidate rules do not match the required matrix"
        )


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
    }


def _lineage_document(
    *,
    dataset: PeriodVesselRuleEvidenceDataset,
    relation: PeriodRelation,
    evidence_path: Path,
    evidence_sha256: str,
    started_at: datetime,
    completed_at: datetime,
) -> dict[str, object]:
    inputs = [
        ArtifactReference(
            artifact_id="multi-day-cleaned-ais-manifest",
            locator=str(dataset.period_input.manifest_path),
            sha256=dataset.period_input.manifest_sha256,
        )
    ]
    inputs.extend(
        ArtifactReference(
            artifact_id=f"cleaned-ais-{partition.utc_date}",
            locator=str(partition.cleaned_path),
            sha256=partition.cleaned_sha256,
        )
        for partition in relation.partitions
    )
    period_summary = cast(
        Mapping[str, object], dataset.document["whole_period_by_vessel_group"]
    )
    commercial = cast(Mapping[str, object], period_summary[ALL_COMMERCIAL])
    structural = cast(Mapping[str, object], commercial["structural_segments"])
    run = RunMetadata(
        run_id=dataset.evidence_id,
        started_at=started_at,
        completed_at=completed_at,
        configuration_version=EVIDENCE_SCHEMA_VERSION,
        configuration_sha256=hashlib.sha256(
            canonical_json(dataset.parameters.to_dict()).encode("utf-8")
        ).hexdigest(),
        steps=(
            ProcessingStep("verify-ready-period-input", "1.0.0"),
            ProcessingStep("form-whole-period-consecutive-pairs", "1.0.0"),
            ProcessingStep("summarize-fixed-bin-rule-evidence", "1.0.0"),
            ProcessingStep("evaluate-explicit-candidate-matrix", "1.0.0"),
            ProcessingStep("write-deterministic-period-rule-evidence", "1.0.0"),
        ),
        inputs=tuple(inputs),
        outputs=(
            ArtifactReference(
                artifact_id="period-vessel-rule-evidence",
                locator=str(evidence_path),
                sha256=evidence_sha256,
            ),
        ),
        validations=(
            ValidationRecord.from_counts(
                "period-input-readiness",
                (
                    dataset.period_input.period_input_readiness.get("status") == "ready"
                    or dataset.parameters.allow_incomplete_non_production
                ),
                {"partitions": len(relation.partitions)},
            ),
            ValidationRecord.from_counts(
                "whole-period-stream-reconciliation",
                dataset.execution_stats.streamed_observations
                == cast(int, commercial["cleaned_observations"]),
                {
                    "observations": dataset.execution_stats.streamed_observations,
                    "structural_segments": cast(int, structural["candidate_segments"]),
                },
            ),
        ),
    )
    effective = relation.effective_settings()
    return {
        "contract": EVIDENCE_LINEAGE_CONTRACT,
        "processing_version": EVIDENCE_PROCESSING_VERSION,
        "status": "candidate methodological evidence; no rule is accepted",
        "method_status": "ADR 0018 remains Proposed",
        "execution": {
            "elapsed_seconds": _round((completed_at - started_at).total_seconds()),
            "arrow_batch_size_rows": dataset.batch_size,
            **dataset.execution_stats.to_dict(),
            "duckdb": {
                "requested_memory_limit": relation.resources.memory_limit,
                "effective_memory_limit": effective["memory_limit"],
                "requested_threads": relation.resources.threads,
                "effective_threads": effective["threads"],
                "spill_directory": str(relation.spill_directory),
            },
            "identity_note": (
                "timestamps, elapsed time, local paths, resource settings, and "
                "machine-specific software values are execution provenance only "
                "and do not participate in evidence identity"
            ),
        },
        "software_versions": _software_versions(),
        "run": run.to_dict(),
    }


def _validate_output_directory(output_directory: Path, overwrite: bool) -> Path:
    target = output_directory.resolve()
    if target == _PROJECT_RAW_ROOT or target.is_relative_to(_PROJECT_RAW_ROOT):
        raise PeriodVesselRuleEvidenceError(
            f"period vessel-rule evidence cannot be written under raw data: {target}"
        )
    if target == _PROJECT_INTERIM_ROOT or not target.is_relative_to(
        _PROJECT_INTERIM_ROOT
    ):
        raise PeriodVesselRuleEvidenceError(
            "period vessel-rule evidence must be a named bundle beneath ignored "
            "data/interim"
        )
    if target.exists() and not target.is_dir():
        raise PeriodVesselRuleEvidenceError(f"output path is not a directory: {target}")
    if target.exists() and not overwrite:
        raise PeriodVesselRuleEvidenceError(
            "output directory already exists; use explicit overwrite authorization"
        )
    if target.exists():
        entries = {item.name for item in target.iterdir()}
        if entries != set(EVIDENCE_BUNDLE_FILENAMES):
            raise PeriodVesselRuleEvidenceError(
                "overwrite only replaces a complete period vessel-rule evidence bundle"
            )
        try:
            marker = json.loads(
                (target / RUN_METADATA_FILENAME).read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise PeriodVesselRuleEvidenceError(
                "existing run metadata is not a readable evidence marker"
            ) from exc
        if marker.get("contract") != EVIDENCE_LINEAGE_CONTRACT:
            raise PeriodVesselRuleEvidenceError(
                "overwrite only replaces this period vessel-rule evidence contract"
            )
    return target


def validate_input_output_separation(
    output_directory: Path, input_paths: Iterable[Path]
) -> None:
    """Refuse equality, ancestry, or descent between output and any input path."""
    output = output_directory.resolve()
    for input_path in input_paths:
        source = input_path.resolve()
        if (
            source == output
            or source.is_relative_to(output)
            or output.is_relative_to(source)
        ):
            raise PeriodVesselRuleEvidenceError(
                f"input and output paths must be separate: {source} and {output}"
            )


def validate_evidence_output_target(
    output_directory: Path,
    input_paths: Iterable[Path],
    *,
    overwrite: bool = False,
) -> Path:
    """Preflight the output contract and all known path-separation constraints."""
    target = _validate_output_directory(output_directory, overwrite)
    validate_input_output_separation(target, input_paths)
    return target


def _cleanup_bundle(path: Path) -> None:
    if not path.exists():
        return
    for filename in EVIDENCE_BUNDLE_FILENAMES:
        candidate = path / filename
        if candidate.is_file():
            candidate.unlink()
    with suppress(OSError):
        path.rmdir()


def _publish_bundle(temporary: Path, target: Path, overwrite: bool) -> None:
    if not target.exists():
        temporary.rename(target)
        return
    if not overwrite:
        raise PeriodVesselRuleEvidenceError(f"output already exists: {target}")
    backup = target.with_name(f".{target.name}.previous-{os.getpid()}")
    if backup.exists():
        raise PeriodVesselRuleEvidenceError(
            f"narrow overwrite backup already exists: {backup}"
        )
    target.rename(backup)
    try:
        temporary.rename(target)
    except OSError:
        backup.rename(target)
        raise
    _cleanup_bundle(backup)


def write_period_vessel_rule_evidence(
    dataset: PeriodVesselRuleEvidenceDataset,
    output_directory: Path,
    *,
    relation: PeriodRelation,
    started_at: datetime,
    overwrite: bool = False,
) -> PeriodVesselRuleEvidenceWriteResult:
    """Atomically publish deterministic evidence and time-bearing lineage."""
    if started_at.utcoffset() != UTC.utcoffset(started_at):
        raise PeriodVesselRuleEvidenceError("started_at must be timezone-aware UTC")
    target = validate_evidence_output_target(
        output_directory,
        (
            dataset.period_input.manifest_path,
            *dataset.partition_paths,
            relation.resources.temporary_directory,
        ),
        overwrite=overwrite,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.temporary-", dir=target.parent)
    )
    evidence_path = temporary / EVIDENCE_FILENAME
    lineage_path = temporary / RUN_METADATA_FILENAME
    try:
        validate_evidence_document(dataset.document)
        _write_json(evidence_path, dataset.document)
        evidence_sha256 = sha256_file(evidence_path)
        parsed = json.loads(evidence_path.read_text(encoding="utf-8"))
        if not isinstance(parsed, Mapping):
            raise PeriodVesselRuleEvidenceError(
                "written evidence did not read back as an object"
            )
        validate_evidence_document(cast(Mapping[str, object], parsed))
        completed_at = datetime.now(UTC)
        lineage = _lineage_document(
            dataset=dataset,
            relation=relation,
            evidence_path=target / EVIDENCE_FILENAME,
            evidence_sha256=evidence_sha256,
            started_at=started_at,
            completed_at=completed_at,
        )
        _write_json(lineage_path, lineage)
        lineage_sha256 = sha256_file(lineage_path)
        _publish_bundle(temporary, target, overwrite)
    except PeriodVesselRuleEvidenceError:
        raise
    except Exception as exc:
        raise PeriodVesselRuleEvidenceError(
            f"could not atomically write period vessel-rule evidence: {exc}"
        ) from exc
    finally:
        _cleanup_bundle(temporary)
    return PeriodVesselRuleEvidenceWriteResult(
        output_directory=target,
        evidence_path=target / EVIDENCE_FILENAME,
        lineage_path=target / RUN_METADATA_FILENAME,
        evidence_id=dataset.evidence_id,
        evidence_sha256=evidence_sha256,
        lineage_sha256=lineage_sha256,
    )
