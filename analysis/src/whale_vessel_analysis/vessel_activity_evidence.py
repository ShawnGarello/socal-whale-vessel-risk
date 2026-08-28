"""Read-only vessel-activity diagnostics for one cleaned AIS bundle.

This module is an evidence harness, not the production vessel-grid process. It
constructs deterministic consecutive-observation candidates and reports the
effects of only those candidate values supplied explicitly by the caller.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, cast

import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import Geod, Transformer
from shapely import STRtree, unary_union
from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis.ais_processing import (
    AIS_PROCESSING_CONTRACT,
    CLEANED_FILENAME,
    QUALITY_REPORT_FILENAME,
    RUN_METADATA_FILENAME,
)
from whale_vessel_analysis.config import PROJECTED_CRS, ProcessingConfig
from whale_vessel_analysis.whale_grid import TargetGridInspection, load_target_grid

EVIDENCE_REPORT_CONTRACT: Final = "vessel_activity_evidence_v1"
EVIDENCE_PROCESSING_VERSION: Final = "1.0.0"
WGS84_CRS: Final = "EPSG:4326"
KNOTS_PER_METRE_PER_SECOND: Final = 1.9438444924406046
LENGTH_TOLERANCE_M: Final = 1e-6
VESSEL_GROUPS: Final = ("passenger", "cargo", "tanker")
ALL_COMMERCIAL: Final = "all_commercial"
_EXPECTED_COLUMNS: Final = (
    "mmsi",
    "observed_at_utc",
    "latitude",
    "longitude",
    "sog_knots",
    "cog_degrees",
    "heading_degrees",
    "vessel_type_code",
    "vessel_type_group",
    "length_m",
)
_BUNDLE_FILES: Final = frozenset(
    {CLEANED_FILENAME, QUALITY_REPORT_FILENAME, RUN_METADATA_FILENAME}
)
_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
_PROJECT_RAW_ROOT: Final = (_PROJECT_ROOT / "data" / "raw").resolve()
_PROJECT_INTERIM_ROOT: Final = (_PROJECT_ROOT / "data" / "interim").resolve()

VesselGroup = Literal["passenger", "cargo", "tanker"]


class VesselActivityEvidenceError(ValueError):
    """Raised when evidence input, processing, or output is invalid."""


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
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _content_report_id(report_without_id: Mapping[str, object]) -> str:
    return (
        "vessel-evidence-"
        + hashlib.sha256(
            _canonical_json(report_without_id).encode("utf-8")
        ).hexdigest()[:24]
    )


def _read_json_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VesselActivityEvidenceError(
            f"{label} is not readable JSON: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise VesselActivityEvidenceError(f"{label} must contain a JSON object")
    return cast(Mapping[str, object], value)


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VesselActivityEvidenceError(f"{label} must be an object")
    return cast(Mapping[str, object], value)


def _validate_bundle_metadata(
    bundle_path: Path, cleaned_sha256: str
) -> tuple[str, Mapping[str, object]]:
    quality = _read_json_object(bundle_path / QUALITY_REPORT_FILENAME, "quality report")
    metadata = _read_json_object(bundle_path / RUN_METADATA_FILENAME, "run metadata")
    if quality.get("contract") != AIS_PROCESSING_CONTRACT:
        raise VesselActivityEvidenceError(
            f"quality report contract must be {AIS_PROCESSING_CONTRACT}"
        )
    if metadata.get("contract") != AIS_PROCESSING_CONTRACT:
        raise VesselActivityEvidenceError(
            f"run metadata contract must be {AIS_PROCESSING_CONTRACT}"
        )
    quality_output = _mapping(quality.get("output"), "quality report output")
    if quality_output.get("sha256") != cleaned_sha256:
        raise VesselActivityEvidenceError(
            "cleaned Parquet checksum does not match the quality report"
        )
    run = _mapping(metadata.get("run"), "run metadata run")
    run_id = run.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise VesselActivityEvidenceError("cleaner run metadata has no valid run_id")
    outputs = run.get("outputs")
    if not isinstance(outputs, list):
        raise VesselActivityEvidenceError("cleaner run metadata outputs must be a list")
    cleaned_outputs = [
        item
        for item in outputs
        if isinstance(item, Mapping)
        and item.get("artifact_id") == "cleaned-ais-parquet"
    ]
    if len(cleaned_outputs) != 1 or cleaned_outputs[0].get("sha256") != cleaned_sha256:
        raise VesselActivityEvidenceError(
            "cleaned Parquet checksum does not match cleaner run metadata"
        )
    temporal = _mapping(quality.get("temporal_coverage"), "temporal coverage")
    return run_id, temporal


def _validate_schema(schema: pa.Schema) -> None:
    if tuple(schema.names) != _EXPECTED_COLUMNS:
        raise VesselActivityEvidenceError(
            "cleaned Parquet columns do not match the one-extract cleaner contract"
        )
    expected_types = (
        pa.types.is_string,
        pa.types.is_timestamp,
        pa.types.is_floating,
        pa.types.is_floating,
        pa.types.is_floating,
        pa.types.is_floating,
        pa.types.is_floating,
        pa.types.is_integer,
        pa.types.is_string,
        pa.types.is_floating,
    )
    for field, predicate in zip(schema, expected_types, strict=True):
        if not predicate(field.type):
            raise VesselActivityEvidenceError(
                f"cleaned Parquet column {field.name} has invalid type {field.type}"
            )
    timestamp_type = schema.field("observed_at_utc").type
    if not isinstance(timestamp_type, pa.TimestampType) or timestamp_type.tz is None:
        raise VesselActivityEvidenceError(
            "cleaned Parquet observed_at_utc must be timezone-aware"
        )


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
    bundle_path = bundle_path.resolve()
    if not bundle_path.is_dir():
        raise VesselActivityEvidenceError(
            f"cleaned AIS bundle does not exist: {bundle_path}"
        )
    entries = {entry.name for entry in bundle_path.iterdir()}
    if entries != _BUNDLE_FILES:
        raise VesselActivityEvidenceError(
            "cleaned AIS bundle must contain exactly cleaned.parquet, "
            "quality-report.json, and run-metadata.json"
        )
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


def allocate_segments_to_grid(
    segments: Sequence[CandidateSegment],
    target_grid: TargetGridInspection,
    *,
    population_label: str = "unfiltered structural baseline",
) -> dict[str, object]:
    """Allocate one named structural-candidate population for diagnostics only."""
    geometries = [cell.geometry for cell in target_grid.cells]
    support_union = cast(BaseGeometry, unary_union(geometries))
    tree = STRtree(geometries)
    total_parent = 0.0
    total_piece = 0.0
    total_union = 0.0
    piece_count = 0
    allocated_segment_count = 0
    zero_length_count = 0
    touched_cells: set[str] = set()
    maximum_difference = 0.0
    group_totals: dict[str, dict[str, float | int]] = {
        group: {"segment_count": 0, "parent_length_m": 0.0, "in_support_length_m": 0.0}
        for group in VESSEL_GROUPS
    }
    for segment in segments:
        if not segment.structurally_eligible:
            continue
        allocated_segment_count += 1
        group = group_totals[segment.start.vessel_type_group]
        group["segment_count"] = cast(int, group["segment_count"]) + 1
        group["parent_length_m"] = (
            cast(float, group["parent_length_m"]) + segment.projected_distance_m
        )
        total_parent += segment.projected_distance_m
        if segment.projected_distance_m <= LENGTH_TOLERANCE_M:
            zero_length_count += 1
            continue
        line = LineString([segment.start_xy_m, segment.end_xy_m])
        cell_piece_length = 0.0
        candidate_indices = sorted(int(value) for value in tree.query(line))
        for index in candidate_indices:
            intersection = line.intersection(geometries[index])
            length = float(intersection.length)
            if length <= LENGTH_TOLERANCE_M:
                continue
            cell_piece_length += length
            piece_count += 1
            touched_cells.add(target_grid.cells[index].cell_id)
        union_length = float(line.intersection(support_union).length)
        difference = cell_piece_length - union_length
        maximum_difference = max(maximum_difference, abs(difference))
        tolerance = max(LENGTH_TOLERANCE_M, segment.projected_distance_m * 1e-12)
        if not math.isclose(
            cell_piece_length, union_length, rel_tol=1e-12, abs_tol=tolerance
        ):
            raise VesselActivityEvidenceError(
                "segment-piece lengths do not conserve the intersection with the "
                "union of exact modeled-whale-support cell geometries"
            )
        if union_length > segment.projected_distance_m + tolerance:
            raise VesselActivityEvidenceError(
                "segment allocation exceeds parent projected length"
            )
        total_piece += cell_piece_length
        total_union += union_length
        group["in_support_length_m"] = (
            cast(float, group["in_support_length_m"]) + union_length
        )
    outside = total_parent - total_union
    if outside < -LENGTH_TOLERANCE_M:
        raise VesselActivityEvidenceError(
            "aggregate allocated length exceeds parent length"
        )
    outside = max(0.0, outside)
    group_report: dict[str, object] = {}
    for group_name, values in group_totals.items():
        parent = cast(float, values["parent_length_m"])
        inside = cast(float, values["in_support_length_m"])
        group_report[group_name] = {
            "segment_count": values["segment_count"],
            "parent_length_m": _round(parent),
            "parent_length_km": _round(parent / 1_000),
            "in_support_length_m": _round(inside),
            "in_support_length_km": _round(inside / 1_000),
            "outside_support_length_m": _round(max(0.0, parent - inside)),
            "outside_support_length_km": _round(max(0.0, parent - inside) / 1_000),
        }
    return {
        "status": "non-production diagnostic allocation",
        "segment_population": population_label,
        "target_grid": {
            "contract": "projected_water_grid_v1",
            "path": str(target_grid.path),
            "sha256": target_grid.sha256,
            "analysis_crs": PROJECTED_CRS,
            "transformation": {"source_crs": WGS84_CRS, "always_xy": True},
            "cell_geometry": "exact modeled-whale-support geometry",
        },
        "counts": {
            "allocated_segment_count": allocated_segment_count,
            "zero_length_segment_count": zero_length_count,
            "positive_length_piece_count": piece_count,
            "touched_cell_count": len(touched_cells),
        },
        "lengths": {
            "parent_projected_length_m": _round(total_parent),
            "parent_projected_length_km": _round(total_parent / 1_000),
            "in_support_piece_length_m": _round(total_piece),
            "in_support_piece_length_km": _round(total_piece / 1_000),
            "in_support_union_intersection_length_m": _round(total_union),
            "in_support_union_intersection_length_km": _round(total_union / 1_000),
            "outside_support_length_m": _round(outside),
            "outside_support_length_km": _round(outside / 1_000),
        },
        "by_group": group_report,
        "conservation": {
            "passed": True,
            "piece_minus_union_intersection_m": _round(total_piece - total_union),
            "parent_minus_in_support_minus_outside_m": _round(
                total_parent - total_union - outside
            ),
            "maximum_segment_piece_difference_m": _round(maximum_difference),
            "no_double_allocation": True,
            "absolute_tolerance_m": LENGTH_TOLERANCE_M,
            "relative_tolerance": 1e-12,
        },
        "outside_support_note": (
            "outside-support portions are outside the supplied biological model "
            "support only; no land, dry-area, or AIS-coverage inference is made"
        ),
        "output_note": "no per-cell vessel-activity dataset is emitted",
    }


def _grid_allocation_diagnostics(
    evaluation: CandidateSensitivityEvaluation,
    target_grid: TargetGridInspection,
) -> dict[str, object]:
    baseline = allocate_segments_to_grid(
        evaluation.structural_baseline,
        target_grid,
        population_label="unfiltered structural baseline",
    )
    scenario_allocations: list[dict[str, object]] = []
    for scenario in evaluation.scenarios:
        allocation = allocate_segments_to_grid(
            scenario.retained_segments,
            target_grid,
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
        "baseline": baseline,
        "candidate_scenarios": scenario_allocations,
        "interpretation": (
            "each explicitly supplied candidate scenario is allocated independently; "
            "the baseline remains unfiltered by gap, implied speed, or vessel length"
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
            "bundle_path": str(bundle.bundle_path),
            "cleaned_parquet_path": str(bundle.cleaned_path),
            "cleaned_parquet_sha256": bundle.cleaned_sha256,
            "cleaner_contract": AIS_PROCESSING_CONTRACT,
            "cleaner_run_id": bundle.cleaner_run_id,
            "temporal_coverage": dict(bundle.temporal_coverage),
            "read_only": True,
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
            else _grid_allocation_diagnostics(sensitivity, target_grid)
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
    identity_material = dict(report)
    identity_material.pop("report_id")
    if report_id != _content_report_id(identity_material):
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
