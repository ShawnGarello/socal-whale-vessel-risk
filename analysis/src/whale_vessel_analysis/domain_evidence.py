"""Deterministic, non-production evidence for AIS coverage-domain candidates."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tomllib
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import shapely
from pyproj import CRS, Transformer
from shapely import from_wkb
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.whale_grid import load_target_grid

STATUTE_MILE_M: Final = 1609.344
NAUTICAL_MILE_M: Final = 1852.0
_PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]
_PROJECT_INTERIM_ROOT: Final = (_PROJECT_ROOT / "data" / "interim").resolve()
_EVIDENCE_CONTRACT: Final = "analytical_domain_evidence_v1"
_EXPECTED_CRS: Final = {
    "analysis_crs": "EPSG:3310",
    "shoreline_crs": "EPSG:4269",
    "station_crs": "EPSG:4269",
    "vsr_crs": "EPSG:4326",
}


class DomainEvidenceError(ValueError):
    """Raised when evidence inputs or configuration are invalid."""


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    basis: Literal["coastline", "receivers"]
    distance: int
    unit: Literal["statute_mile", "nautical_mile"]

    @property
    def distance_m(self) -> float:
        if self.unit == "statute_mile":
            factor = STATUTE_MILE_M
        elif self.unit == "nautical_mile":
            factor = NAUTICAL_MILE_M
        else:
            raise DomainEvidenceError(f"unsupported scenario unit: {self.unit}")
        return self.distance * factor


@dataclass(frozen=True, slots=True)
class DomainEvidenceConfig:
    """Validated configuration for one evidence calculation."""

    analysis_crs: str
    shoreline_crs: str
    station_crs: str
    vsr_crs: str
    shoreline_member: str
    station_member: str
    shoreline_simplification_m: float
    vsr_segment_max_degrees: float
    buffer_quadrant_segments: int
    cell_area_tolerance_m2: float
    source_sha256: dict[str, str]
    shoreline_filter: dict[str, float]
    station_filter: dict[str, float]
    scenarios: tuple[Scenario, ...]


@dataclass(frozen=True, slots=True)
class CandidateMeasurement:
    scenario: Scenario
    included_water_area_m2: float
    inside_vsr_area_m2: float
    outside_vsr_area_m2: float
    fully_inside_cell_count: int
    partly_inside_cell_count: int
    wholly_outside_cell_count: int
    geometry: BaseGeometry

    def to_dict(self, total_vsr_area_m2: float) -> dict[str, object]:
        return {
            "id": self.scenario.id,
            "basis": self.scenario.basis,
            "distance": self.scenario.distance,
            "unit": self.scenario.unit,
            "distance_m": self.scenario.distance_m,
            "included_water_area_km2": self.included_water_area_m2 / 1_000_000,
            "inside_vsr_area_km2": self.inside_vsr_area_m2 / 1_000_000,
            "outside_vsr_area_km2": self.outside_vsr_area_m2 / 1_000_000,
            "inside_fraction_of_candidate": (
                self.inside_vsr_area_m2 / self.included_water_area_m2
            ),
            "outside_fraction_of_candidate": (
                self.outside_vsr_area_m2 / self.included_water_area_m2
            ),
            "fraction_of_map_grid_vsr_area_represented": (
                self.inside_vsr_area_m2 / total_vsr_area_m2
            ),
            "cells": {
                "fully_inside": self.fully_inside_cell_count,
                "partly_inside": self.partly_inside_cell_count,
                "wholly_outside": self.wholly_outside_cell_count,
            },
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise DomainEvidenceError(f"{label} does not exist: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise DomainEvidenceError(
            f"{label} SHA-256 mismatch: expected {expected}, received {actual}"
        )
    return actual


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DomainEvidenceError(f"{label} must be a table")
    return cast(dict[str, object], value)


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainEvidenceError(f"{label} must be a nonempty string")
    if value != value.strip():
        raise DomainEvidenceError(f"{label} cannot have leading or trailing whitespace")
    return value


def _number(value: object, label: str, *, positive: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DomainEvidenceError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise DomainEvidenceError(f"{label} must be finite")
    if positive and result <= 0:
        raise DomainEvidenceError(f"{label} must be positive")
    if not positive and result < 0:
        raise DomainEvidenceError(f"{label} cannot be negative")
    return result


def _spatial_filter(value: object, label: str) -> dict[str, float]:
    table = _mapping(value, label)
    result: dict[str, float] = {}
    for key in ("lon_min", "lat_min", "lon_max", "lat_max"):
        coordinate = table.get(key)
        if isinstance(coordinate, bool) or not isinstance(coordinate, int | float):
            raise DomainEvidenceError(f"{label}.{key} must be numeric")
        result[key] = float(coordinate)
        if not math.isfinite(result[key]):
            raise DomainEvidenceError(f"{label}.{key} must be finite")
    if result["lon_min"] >= result["lon_max"]:
        raise DomainEvidenceError(f"{label} longitude bounds must be increasing")
    if result["lat_min"] >= result["lat_max"]:
        raise DomainEvidenceError(f"{label} latitude bounds must be increasing")
    return result


def _load_config(config_bytes: bytes) -> DomainEvidenceConfig:
    raw = _mapping(tomllib.loads(config_bytes.decode("utf-8")), "configuration")
    if raw.get("schema_version") != 1:
        raise DomainEvidenceError("schema_version must be 1")

    crs_values: dict[str, str] = {}
    for key, expected in _EXPECTED_CRS.items():
        actual = _nonempty_string(raw.get(key), key)
        if actual != expected:
            raise DomainEvidenceError(f"{key} must be {expected}, received {actual}")
        crs_values[key] = actual

    raw_hashes = _mapping(raw.get("source_sha256"), "source_sha256")
    hashes: dict[str, str] = {}
    for key in ("grid", "shoreline_archive", "station_archive", "vsr"):
        value = _nonempty_string(raw_hashes.get(key), f"source_sha256.{key}")
        if len(value) != 64 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise DomainEvidenceError(
                f"source_sha256.{key} must be a lowercase SHA-256 digest"
            )
        hashes[key] = value

    raw_scenarios = raw.get("scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise DomainEvidenceError("scenarios must be a nonempty array of tables")
    scenarios: list[Scenario] = []
    scenario_ids: set[str] = set()
    for index, value in enumerate(raw_scenarios):
        item = _mapping(value, f"scenarios[{index}]")
        scenario_id = _nonempty_string(item.get("id"), f"scenarios[{index}].id")
        if scenario_id in scenario_ids:
            raise DomainEvidenceError(f"scenario id must be unique: {scenario_id}")
        scenario_ids.add(scenario_id)
        basis = _nonempty_string(item.get("basis"), f"scenarios[{index}].basis")
        if basis not in ("coastline", "receivers"):
            raise DomainEvidenceError(
                f"scenarios[{index}].basis must be coastline or receivers"
            )
        unit = _nonempty_string(item.get("unit"), f"scenarios[{index}].unit")
        if unit not in ("statute_mile", "nautical_mile"):
            raise DomainEvidenceError(
                f"scenarios[{index}].unit must be statute_mile or nautical_mile"
            )
        distance_value = item.get("distance")
        if isinstance(distance_value, bool) or not isinstance(distance_value, int):
            raise DomainEvidenceError(f"scenarios[{index}].distance must be an integer")
        if distance_value <= 0:
            raise DomainEvidenceError(f"scenarios[{index}].distance must be positive")
        scenarios.append(
            Scenario(
                id=scenario_id,
                basis=cast(Literal["coastline", "receivers"], basis),
                distance=distance_value,
                unit=cast(Literal["statute_mile", "nautical_mile"], unit),
            )
        )

    buffer_segments = raw.get("buffer_quadrant_segments")
    if isinstance(buffer_segments, bool) or not isinstance(buffer_segments, int):
        raise DomainEvidenceError("buffer_quadrant_segments must be an integer")
    if buffer_segments <= 0:
        raise DomainEvidenceError("buffer_quadrant_segments must be positive")

    return DomainEvidenceConfig(
        analysis_crs=crs_values["analysis_crs"],
        shoreline_crs=crs_values["shoreline_crs"],
        station_crs=crs_values["station_crs"],
        vsr_crs=crs_values["vsr_crs"],
        shoreline_member=_nonempty_string(
            raw.get("shoreline_member"), "shoreline_member"
        ),
        station_member=_nonempty_string(raw.get("station_member"), "station_member"),
        shoreline_simplification_m=_number(
            raw.get("shoreline_simplification_m"),
            "shoreline_simplification_m",
            positive=False,
        ),
        vsr_segment_max_degrees=_number(
            raw.get("vsr_segment_max_degrees"),
            "vsr_segment_max_degrees",
            positive=True,
        ),
        buffer_quadrant_segments=buffer_segments,
        cell_area_tolerance_m2=_number(
            raw.get("cell_area_tolerance_m2"),
            "cell_area_tolerance_m2",
            positive=False,
        ),
        source_sha256=hashes,
        shoreline_filter=_spatial_filter(
            raw.get("shoreline_filter"), "shoreline_filter"
        ),
        station_filter=_spatial_filter(raw.get("station_filter"), "station_filter"),
        scenarios=tuple(scenarios),
    )


def _within_areas(
    geometries: np.ndarray[tuple[int], np.dtype[np.object_]], boundary: BaseGeometry
) -> np.ndarray[tuple[int], np.dtype[np.float64]]:
    shapely.prepare(boundary)
    areas = shapely.area(geometries)
    fully_inside = shapely.covers(boundary, geometries)
    intersects = shapely.intersects(boundary, geometries)
    partial = intersects & ~fully_inside
    result = np.zeros(len(geometries), dtype=np.float64)
    result[fully_inside] = areas[fully_inside]
    result[partial] = shapely.area(shapely.intersection(geometries[partial], boundary))
    return result


def measure_candidate(
    cells: np.ndarray[tuple[int], np.dtype[np.object_]],
    candidate_mask: BaseGeometry,
    vsr: BaseGeometry,
    scenario: Scenario,
    *,
    tolerance_m2: float,
) -> CandidateMeasurement:
    """Measure exact candidate/cell intersections; never classify by a point."""
    cell_areas = shapely.area(cells)
    shapely.prepare(candidate_mask)
    fully_inside = shapely.covers(candidate_mask, cells)
    intersects = shapely.intersects(candidate_mask, cells)
    partial = intersects & ~fully_inside
    pieces = np.empty(len(cells), dtype=object)
    pieces[fully_inside] = cells[fully_inside]
    pieces[~intersects] = None
    pieces[partial] = shapely.intersection(cells[partial], candidate_mask)
    included = np.zeros(len(cells), dtype=np.float64)
    included[fully_inside] = cell_areas[fully_inside]
    included[partial] = shapely.area(pieces[partial])
    effective_full = cell_areas - included <= tolerance_m2
    effective_outside = included <= tolerance_m2
    effective_partial = ~(effective_full | effective_outside)
    valid_pieces = pieces[~effective_outside]
    inside_values = _within_areas(valid_pieces, vsr)
    included_area = float(included.sum())
    inside_area = float(inside_values.sum())
    geometry = shapely.union_all(valid_pieces)
    return CandidateMeasurement(
        scenario=scenario,
        included_water_area_m2=included_area,
        inside_vsr_area_m2=inside_area,
        outside_vsr_area_m2=included_area - inside_area,
        fully_inside_cell_count=int(effective_full.sum()),
        partly_inside_cell_count=int(effective_partial.sum()),
        wholly_outside_cell_count=int(effective_outside.sum()),
        geometry=geometry,
    )


def _zip_uri(path: Path, member: str) -> str:
    return f"zip://{path.resolve()}!{member}"


def _load_geometries(uri: str, expected_crs: str) -> tuple[pa.Table, np.ndarray]:
    info = cast(dict[str, object], pyogrio.read_info(uri))
    if str(info["crs"]) != expected_crs:
        raise DomainEvidenceError(
            f"{uri} CRS must be {expected_crs}, received {info['crs']}"
        )
    metadata, raw = pyogrio.read_arrow(uri, read_geometry=True)
    table = pa.table(raw)
    geometry_name = str(metadata.get("geometry_name") or "wkb_geometry")
    return table, from_wkb(table[geometry_name].to_numpy(zero_copy_only=False))


def _box_filter(geometries: np.ndarray, values: Mapping[str, float]) -> np.ndarray:
    xmin = values["lon_min"]
    ymin = values["lat_min"]
    xmax = values["lon_max"]
    ymax = values["lat_max"]
    return np.array(
        [
            geometry
            for geometry in geometries
            if geometry.bounds[2] >= xmin
            and geometry.bounds[0] <= xmax
            and geometry.bounds[3] >= ymin
            and geometry.bounds[1] <= ymax
        ],
        dtype=object,
    )


def _write_masks(path: Path, measurements: list[CandidateMeasurement]) -> str:
    geometries = [shapely.normalize(item.geometry) for item in measurements]
    geometry_types = sorted({geometry.geom_type for geometry in geometries})
    records = {
        "scenario_id": [item.scenario.id for item in measurements],
        "basis": [item.scenario.basis for item in measurements],
        "distance_m": [item.scenario.distance_m for item in measurements],
        "geometry": [geometry.wkb for geometry in geometries],
    }
    geo = {
        "version": "1.1.0",
        "primary_column": "geometry",
        "columns": {
            "geometry": {
                "encoding": "WKB",
                "geometry_types": geometry_types,
                "crs": CRS.from_epsg(3310).to_json_dict(),
            }
        },
    }
    schema = pa.schema(
        [
            ("scenario_id", pa.string()),
            ("basis", pa.string()),
            ("distance_m", pa.float64()),
            ("geometry", pa.binary()),
        ],
        metadata={
            b"geo": json.dumps(geo, sort_keys=True, separators=(",", ":")).encode()
        },
    )
    table = pa.Table.from_pydict(records, schema=schema)
    pq.write_table(
        table, path, compression="zstd", use_dictionary=False, write_statistics=False
    )
    with path.open("r+b") as output:
        os.fsync(output.fileno())
    return sha256_file(path)


def _read_existing_report(path: Path) -> dict[str, object]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainEvidenceError(
            "overwrite only replaces a readable analytical-domain evidence pair"
        ) from exc
    if not isinstance(document, dict):
        raise DomainEvidenceError(
            "overwrite only replaces a readable analytical-domain evidence pair"
        )
    return cast(dict[str, object], document)


def _validate_existing_pair(report_path: Path, masks_path: Path) -> None:
    report = _read_existing_report(report_path)
    evidence_id = report.get("evidence_id")
    mask_output = report.get("mask_output")
    if (
        report.get("contract") != _EVIDENCE_CONTRACT
        or report.get("schema_version") != 1
        or not isinstance(evidence_id, str)
        or not isinstance(mask_output, dict)
    ):
        raise DomainEvidenceError(
            "overwrite only replaces an analytical-domain evidence output pair"
        )
    mask_details = cast(dict[str, object], mask_output)
    expected_sha256 = mask_details.get("sha256")
    feature_count = mask_details.get("feature_count")
    if not isinstance(expected_sha256, str) or not isinstance(feature_count, int):
        raise DomainEvidenceError(
            "existing analytical-domain evidence report has invalid mask identity"
        )
    core = {
        key: value
        for key, value in report.items()
        if key not in ("evidence_id", "mask_output")
    }
    identity = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if evidence_id != f"domain-evidence-{identity[:24]}":
        raise DomainEvidenceError(
            "existing analytical-domain evidence report identity is invalid"
        )
    if sha256_file(masks_path) != expected_sha256:
        raise DomainEvidenceError(
            "existing analytical-domain evidence mask does not match its report"
        )
    try:
        metadata = pq.read_metadata(masks_path)
    except Exception as exc:
        raise DomainEvidenceError(
            "existing analytical-domain evidence mask is not readable Parquet"
        ) from exc
    if metadata.num_rows != feature_count or metadata.schema.names != [
        "scenario_id",
        "basis",
        "distance_m",
        "geometry",
    ]:
        raise DomainEvidenceError(
            "existing analytical-domain evidence mask contract is invalid"
        )


def _validate_output_paths(
    report_path: Path,
    masks_path: Path,
    input_paths: tuple[Path, ...],
    *,
    overwrite: bool,
) -> tuple[Path, Path]:
    report = report_path.resolve()
    masks = masks_path.resolve()
    if report == masks:
        raise DomainEvidenceError("report and masks outputs must be distinct")
    for label, output, suffix in (
        ("report", report, ".json"),
        ("masks", masks, ".parquet"),
    ):
        if not output.is_relative_to(_PROJECT_INTERIM_ROOT):
            raise DomainEvidenceError(
                f"{label} output must be beneath ignored data/interim: {output}"
            )
        if output.suffix.lower() != suffix:
            raise DomainEvidenceError(f"{label} output path must end in {suffix}")
        if output.exists() and not output.is_file():
            raise DomainEvidenceError(f"{label} output is not a file: {output}")
    resolved_inputs = {path.resolve() for path in input_paths}
    for output in (report, masks):
        if output in resolved_inputs:
            raise DomainEvidenceError(
                "evidence outputs must be distinct from every input"
            )

    existing = (report.exists(), masks.exists())
    if any(existing) and not overwrite:
        raise DomainEvidenceError(
            "evidence output already exists; use explicit overwrite authorization"
        )
    if overwrite and any(existing):
        if not all(existing):
            raise DomainEvidenceError(
                "overwrite requires a complete existing report-and-mask pair"
            )
        _validate_existing_pair(report, masks)
    return report, masks


def _replace_file(source: Path, destination: Path) -> None:
    os.replace(source, destination)


def _commit_output_pair(
    temporary_report: Path,
    report_path: Path,
    temporary_masks: Path,
    masks_path: Path,
    *,
    overwrite: bool,
) -> None:
    backups: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    try:
        if overwrite:
            for final in (masks_path, report_path):
                if final.exists():
                    backup = final.with_name(f".{final.name}.{uuid.uuid4().hex}.backup")
                    _replace_file(final, backup)
                    backups.append((backup, final))
        elif report_path.exists() or masks_path.exists():
            raise DomainEvidenceError(
                "evidence output appeared during processing; refusing overwrite"
            )
        _replace_file(temporary_masks, masks_path)
        committed.append(masks_path)
        _replace_file(temporary_report, report_path)
        committed.append(report_path)
    except Exception:
        for final in reversed(committed):
            final.unlink(missing_ok=True)
        for backup, final in reversed(backups):
            _replace_file(backup, final)
        raise
    else:
        for backup, _final in backups:
            backup.unlink(missing_ok=True)


def _write_report(path: Path, report: Mapping[str, object]) -> None:
    payload = (
        (json.dumps(report, indent=2, sort_keys=True) + "\n")
        .replace("\n", "\r\n")
        .encode("utf-8")
    )
    with path.open("xb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())


def run_domain_evidence(
    *,
    config_path: Path,
    grid_path: Path,
    shoreline_archive: Path,
    station_archive: Path,
    vsr_path: Path,
    report_path: Path,
    masks_path: Path,
    overwrite: bool = False,
) -> dict[str, object]:
    report_path, masks_path = _validate_output_paths(
        report_path,
        masks_path,
        (config_path, grid_path, shoreline_archive, station_archive, vsr_path),
        overwrite=overwrite,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    masks_path.parent.mkdir(parents=True, exist_ok=True)
    config_bytes = config_path.read_bytes()
    config = _load_config(config_bytes)
    hashes = config.source_sha256
    _require_hash(shoreline_archive, hashes["shoreline_archive"], "shoreline archive")
    _require_hash(station_archive, hashes["station_archive"], "station archive")
    _require_hash(vsr_path, hashes["vsr"], "VSR input")
    processing_config = load_default_config()
    grid = load_target_grid(
        grid_path, processing_config, expected_sha256=hashes["grid"]
    )
    cells = np.array([cell.geometry for cell in grid.cells], dtype=object)
    if len(cells) == 0:
        raise DomainEvidenceError("grid source subset cannot be empty")
    shoreline_table, shoreline = _load_geometries(
        _zip_uri(shoreline_archive, config.shoreline_member),
        config.shoreline_crs,
    )
    del shoreline_table
    shoreline = _box_filter(shoreline, config.shoreline_filter)
    if len(shoreline) == 0:
        raise DomainEvidenceError("shoreline source subset cannot be empty")
    station_table, stations = _load_geometries(
        _zip_uri(station_archive, config.station_member),
        config.station_crs,
    )
    for required_column in ("stationName", "stationType"):
        if required_column not in station_table.column_names:
            raise DomainEvidenceError(
                f"station source is missing required column: {required_column}"
            )
    station_filter = config.station_filter
    all_station_types = station_table["stationType"].to_pylist()
    station_indices = [
        index
        for index, geometry in enumerate(stations)
        if all_station_types[index] == "NAIS"
        and geometry.bounds[2] >= station_filter["lon_min"]
        and geometry.bounds[0] <= station_filter["lon_max"]
        and geometry.bounds[3] >= station_filter["lat_min"]
        and geometry.bounds[1] <= station_filter["lat_max"]
    ]
    stations = stations[station_indices]
    if len(stations) == 0:
        raise DomainEvidenceError("NAIS station source subset cannot be empty")
    selected_station_types = [all_station_types[index] for index in station_indices]
    if any(station_type != "NAIS" for station_type in selected_station_types):
        raise DomainEvidenceError(
            "station source subset must contain only NAIS stations"
        )
    all_station_names = station_table["stationName"].to_pylist()
    station_names = sorted(str(all_station_names[index]) for index in station_indices)
    to_analysis = Transformer.from_crs(
        config.shoreline_crs, config.analysis_crs, always_xy=True
    ).transform
    projected_shoreline = np.array(
        [transform(to_analysis, item) for item in shoreline], dtype=object
    )
    projected_shoreline = shapely.simplify(
        projected_shoreline,
        config.shoreline_simplification_m,
        preserve_topology=False,
    )
    projected_stations = np.array(
        [transform(to_analysis, item) for item in stations], dtype=object
    )
    _, vsr_geometries = _load_geometries(str(vsr_path), config.vsr_crs)
    if len(vsr_geometries) != 1:
        raise DomainEvidenceError("VSR source subset must contain exactly one geometry")
    source_vsr = vsr_geometries[0]
    source_vsr = shapely.segmentize(source_vsr, config.vsr_segment_max_degrees)
    vsr = transform(
        Transformer.from_crs(
            config.vsr_crs, config.analysis_crs, always_xy=True
        ).transform,
        source_vsr,
    )
    if not vsr.is_valid:
        raise DomainEvidenceError("densified projected VSR geometry is invalid")
    total_water_area = float(shapely.area(cells).sum())
    total_vsr_area = float(_within_areas(cells, vsr).sum())
    measurements: list[CandidateMeasurement] = []
    for scenario in config.scenarios:
        if scenario.basis == "coastline":
            basis = projected_shoreline
        elif scenario.basis == "receivers":
            basis = projected_stations
        else:
            raise DomainEvidenceError(f"unsupported scenario basis: {scenario.basis}")
        mask = shapely.union_all(
            shapely.buffer(
                basis,
                scenario.distance_m,
                quad_segs=config.buffer_quadrant_segments,
            )
        )
        measurements.append(
            measure_candidate(
                cells,
                mask,
                vsr,
                scenario,
                tolerance_m2=config.cell_area_tolerance_m2,
            )
        )
    temporary_report = report_path.with_name(
        f".{report_path.name}.{uuid.uuid4().hex}.tmp"
    )
    temporary_masks = masks_path.with_name(f".{masks_path.name}.{uuid.uuid4().hex}.tmp")
    core = {
        "contract": _EVIDENCE_CONTRACT,
        "schema_version": 1,
        "configuration_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "sources": {**hashes, "grid_path_sha256": grid.sha256},
        "processing": {
            "analysis_crs": config.analysis_crs,
            "shoreline_feature_count": len(shoreline),
            "receiver_feature_count": len(stations),
            "receiver_names_in_filter": station_names,
            "shoreline_simplification_m": config.shoreline_simplification_m,
            "vsr_segment_max_degrees": config.vsr_segment_max_degrees,
            "buffer_quadrant_segments": config.buffer_quadrant_segments,
            "boundary_treatment": (
                "exact area intersection of each water geometry; no centroid, "
                "majority, or whole-cell assignment"
            ),
        },
        "map_grid": {
            "water_cell_count": len(cells),
            "water_area_km2": total_water_area / 1_000_000,
            "vsr_area_km2": total_vsr_area / 1_000_000,
            "outside_vsr_area_km2": (total_water_area - total_vsr_area) / 1_000_000,
        },
        "candidates": [item.to_dict(total_vsr_area) for item in measurements],
    }
    identity = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    try:
        masks_sha256 = _write_masks(temporary_masks, measurements)
        report = {
            **core,
            "evidence_id": f"domain-evidence-{identity[:24]}",
            "mask_output": {
                "sha256": masks_sha256,
                "feature_count": len(measurements),
            },
        }
        _write_report(temporary_report, report)
        _commit_output_pair(
            temporary_report,
            report_path,
            temporary_masks,
            masks_path,
            overwrite=overwrite,
        )
    except Exception as exc:
        raise DomainEvidenceError(
            f"could not atomically publish analytical-domain evidence: {exc}"
        ) from exc
    finally:
        temporary_report.unlink(missing_ok=True)
        temporary_masks.unlink(missing_ok=True)
    return report
