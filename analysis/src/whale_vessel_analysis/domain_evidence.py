"""Deterministic, non-production evidence for AIS coverage-domain candidates."""

from __future__ import annotations

import hashlib
import json
import tomllib
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
        factor = STATUTE_MILE_M if self.unit == "statute_mile" else NAUTICAL_MILE_M
        return self.distance * factor


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


def _box_filter(geometries: np.ndarray, values: dict[str, object]) -> np.ndarray:
    xmin = cast(float, values["lon_min"])
    ymin = cast(float, values["lat_min"])
    xmax = cast(float, values["lon_max"])
    ymax = cast(float, values["lat_max"])
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
    records = {
        "scenario_id": [item.scenario.id for item in measurements],
        "basis": [item.scenario.basis for item in measurements],
        "distance_m": [item.scenario.distance_m for item in measurements],
        "geometry": [shapely.normalize(item.geometry).wkb for item in measurements],
    }
    geo = {
        "version": "1.1.0",
        "primary_column": "geometry",
        "columns": {
            "geometry": {
                "encoding": "WKB",
                "geometry_types": ["MultiPolygon"],
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
    return sha256_file(path)


def run_domain_evidence(
    *,
    config_path: Path,
    grid_path: Path,
    shoreline_archive: Path,
    station_archive: Path,
    vsr_path: Path,
    report_path: Path,
    masks_path: Path,
) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = tomllib.loads(config_bytes.decode("utf-8"))
    hashes = cast(dict[str, str], config["source_sha256"])
    _require_hash(shoreline_archive, hashes["shoreline_archive"], "shoreline archive")
    _require_hash(station_archive, hashes["station_archive"], "station archive")
    _require_hash(vsr_path, hashes["vsr"], "VSR input")
    processing_config = load_default_config()
    grid = load_target_grid(
        grid_path, processing_config, expected_sha256=hashes["grid"]
    )
    cells = np.array([cell.geometry for cell in grid.cells], dtype=object)
    shoreline_table, shoreline = _load_geometries(
        _zip_uri(shoreline_archive, str(config["shoreline_member"])),
        str(config["shoreline_crs"]),
    )
    del shoreline_table
    shoreline = _box_filter(
        shoreline, cast(dict[str, object], config["shoreline_filter"])
    )
    station_table, stations = _load_geometries(
        _zip_uri(station_archive, str(config["station_member"])),
        str(config["station_crs"]),
    )
    station_filter = cast(dict[str, object], config["station_filter"])
    station_indices = [
        index
        for index, geometry in enumerate(stations)
        if geometry.bounds[2] >= cast(float, station_filter["lon_min"])
        and geometry.bounds[0] <= cast(float, station_filter["lon_max"])
        and geometry.bounds[3] >= cast(float, station_filter["lat_min"])
        and geometry.bounds[1] <= cast(float, station_filter["lat_max"])
    ]
    stations = stations[station_indices]
    all_station_names = cast(list[str], station_table["stationName"].to_pylist())
    station_names = sorted(all_station_names[index] for index in station_indices)
    to_analysis = Transformer.from_crs(
        config["shoreline_crs"], config["analysis_crs"], always_xy=True
    ).transform
    projected_shoreline = np.array(
        [transform(to_analysis, item) for item in shoreline], dtype=object
    )
    projected_shoreline = shapely.simplify(
        projected_shoreline,
        float(config["shoreline_simplification_m"]),
        preserve_topology=False,
    )
    projected_stations = np.array(
        [transform(to_analysis, item) for item in stations], dtype=object
    )
    _, vsr_geometries = _load_geometries(str(vsr_path), str(config["vsr_crs"]))
    source_vsr = vsr_geometries[0]
    source_vsr = shapely.segmentize(
        source_vsr, float(config["vsr_segment_max_degrees"])
    )
    vsr = transform(
        Transformer.from_crs(
            config["vsr_crs"], config["analysis_crs"], always_xy=True
        ).transform,
        source_vsr,
    )
    if not vsr.is_valid:
        raise DomainEvidenceError("densified projected VSR geometry is invalid")
    total_water_area = float(shapely.area(cells).sum())
    total_vsr_area = float(_within_areas(cells, vsr).sum())
    scenarios = [
        Scenario(
            id=cast(str, item["id"]),
            basis=cast(Literal["coastline", "receivers"], item["basis"]),
            distance=cast(int, item["distance"]),
            unit=cast(Literal["statute_mile", "nautical_mile"], item["unit"]),
        )
        for item in cast(list[dict[str, object]], config["scenarios"])
    ]
    measurements: list[CandidateMeasurement] = []
    for scenario in scenarios:
        basis = (
            projected_shoreline if scenario.basis == "coastline" else projected_stations
        )
        mask = shapely.union_all(
            shapely.buffer(
                basis,
                scenario.distance_m,
                quad_segs=int(config["buffer_quadrant_segments"]),
            )
        )
        measurements.append(
            measure_candidate(
                cells,
                mask,
                vsr,
                scenario,
                tolerance_m2=float(config["cell_area_tolerance_m2"]),
            )
        )
    masks_sha256 = _write_masks(masks_path, measurements)
    core = {
        "contract": "analytical_domain_evidence_v1",
        "schema_version": 1,
        "configuration_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "sources": {**hashes, "grid_path_sha256": grid.sha256},
        "processing": {
            "analysis_crs": config["analysis_crs"],
            "shoreline_feature_count": len(shoreline),
            "receiver_feature_count": len(stations),
            "receiver_names_in_filter": station_names,
            "shoreline_simplification_m": config["shoreline_simplification_m"],
            "vsr_segment_max_degrees": config["vsr_segment_max_degrees"],
            "buffer_quadrant_segments": config["buffer_quadrant_segments"],
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
    report = {
        **core,
        "evidence_id": f"domain-evidence-{identity[:24]}",
        "mask_output": {"sha256": masks_sha256, "feature_count": len(measurements)},
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
