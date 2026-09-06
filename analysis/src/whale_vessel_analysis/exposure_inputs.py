"""Narrow, checksum-bound M6 join of the retained M3 production inputs."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import CRS
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.multiday_ais import accepted_utc_dates
from whale_vessel_analysis.vessel_input import selected_method
from whale_vessel_analysis.whale_grid import TargetGridInspection, load_target_grid

WATER_SHA256 = "7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031"
WHALE_SHA256 = "421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62"
VESSEL_SHA256 = "5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0"
VESSEL_QUALITY_SHA256 = (
    "4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7"
)
PERIOD_ID = "multiday-ais-17e982f999f7093945193378"
INPUT_ID = "vessel-input-5e590ff3d85ee7acb16e2fd1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"{label}: missing/nonnumeric",
    )
    result = float(value)  # type: ignore[arg-type]
    require(math.isfinite(result) and result >= 0, f"{label}: nonfinite/negative")
    return result


@dataclass(frozen=True)
class ExposureInputCell:
    cell_id: str
    x_min_m: int
    y_min_m: int
    water: BaseGeometry
    water_km2: float
    whale_density: float
    whale_abundance: float
    vessel_km: float


def join_inputs(
    grid: TargetGridInspection, whale: pa.Table, vessel: pa.Table
) -> tuple[ExposureInputCell, ...]:
    """Validate one-to-one grid geometry and scientific values, not an inner join."""
    expected = [c.cell_id for c in grid.cells]
    require(
        bool(expected) and len(set(expected)) == len(expected),
        "grid IDs must be unique and nonempty",
    )
    for table in (whale, vessel):
        require(
            table.num_rows == len(expected), "input row count differs from water grid"
        )
        require(
            table["cell_id"].to_pylist() == expected, "input IDs/order differ from grid"
        )
    result = []
    for cell, w, v in zip(
        grid.cells, whale.to_pylist(), vessel.to_pylist(), strict=True
    ):
        for row in (w, v):
            require(row["geometry"] == cell.geometry_wkb, "water geometry differs")
            for field, value in (
                ("row_index", cell.row_index),
                ("column_index", cell.column_index),
                ("cell_x_min_m", cell.x_min_m),
                ("cell_y_min_m", cell.y_min_m),
                ("cell_x_max_m", cell.x_max_m),
                ("cell_y_max_m", cell.y_max_m),
                ("water_area_m2", cell.water_area_m2),
                ("water_area_km2", cell.water_area_km2),
            ):
                require(row[field] == value, f"grid {field} differs")
        require(w["coverage_status"] == "complete", "whale support is not complete")
        gap = number(w["uncovered_water_area_m2"], "whale support gap")
        require(gap <= 1e-6, "whale support gap exceeds complete tolerance")
        covered = number(w["source_covered_water_area_m2"], "covered area")
        fraction = number(w["source_coverage_fraction"], "coverage fraction")
        require(
            fraction <= 1
            and math.isclose(
                covered / cell.water_area_m2, fraction, rel_tol=1e-10, abs_tol=1e-12
            ),
            "coverage fraction inconsistent",
        )
        require(
            math.isclose(
                covered + gap, cell.water_area_m2, rel_tol=1e-10, abs_tol=1e-6
            ),
            "support area inconsistent",
        )
        density = number(w["modeled_density_animals_per_km2"], "whale density")
        abundance = number(w["modeled_abundance_allocation_animals"], "whale abundance")
        require(
            math.isclose(
                density * cell.water_area_km2, abundance, rel_tol=1e-10, abs_tol=1e-9
            ),
            "whale units inconsistent",
        )
        distance = number(v["vessel_km_all_commercial"], "vessel km")
        intensity = number(
            v["vessel_km_per_water_km2_all_commercial"], "vessel intensity"
        )
        require(
            math.isclose(
                distance / cell.water_area_km2, intensity, rel_tol=1e-12, abs_tol=1e-12
            ),
            "vessel units inconsistent",
        )
        groups = [
            number(v[f"vessel_km_{g}"], g) for g in ("passenger", "cargo", "tanker")
        ]
        require(
            math.isclose(math.fsum(groups), distance, rel_tol=1e-12, abs_tol=1e-9),
            "vessel group totals inconsistent",
        )
        result.append(
            ExposureInputCell(
                cell.cell_id,
                cell.x_min_m,
                cell.y_min_m,
                cell.geometry,
                cell.water_area_km2,
                density,
                abundance,
                distance,
            )
        )
    return tuple(result)


def _metadata(table: pa.Table, contract: str) -> dict[str, Any]:
    metadata = table.schema.metadata or {}
    product: dict[str, Any] = json.loads(metadata[b"whale_vessel_analysis"])
    geo = json.loads(metadata[b"geo"])
    geometry = geo["columns"][geo["primary_column"]]
    require(
        geometry["encoding"] == "WKB"
        and CRS.from_user_input(geometry["crs"]) == CRS.from_epsg(3310),
        "input CRS/encoding differs",
    )
    require(
        product["contract"] == contract and product["schema_version"] == 1,
        "unexpected production input contract",
    )
    return product


def load_exposure_inputs(
    water_path: Path, whale_path: Path, vessel_path: Path
) -> tuple[tuple[ExposureInputCell, ...], dict[str, str]]:
    """Require accepted analytical bytes and consistent regenerated lineage.

    Deliberately not a generic artifact importer. Future analytical source vintages
    require a reviewed contract update.
    Execution-specific lineage digests are returned as provenance only.
    """
    paths = {
        "water": (water_path, WATER_SHA256),
        "whale": (whale_path, WHALE_SHA256),
        "vessel": (vessel_path, VESSEL_SHA256),
        "whale_lineage": (
            Path(str(whale_path) + ".lineage.json"),
            None,
        ),
        "vessel_quality": (
            vessel_path.parent / "quality-report.json",
            VESSEL_QUALITY_SHA256,
        ),
        "vessel_lineage": (
            vessel_path.parent / "run-metadata.json",
            None,
        ),
    }
    for label, (path, checksum) in paths.items():
        require(
            path.is_file() and (checksum is None or sha256_file(path) == checksum),
            f"{label}: retained checksum mismatch",
        )
    grid = load_target_grid(
        water_path, load_default_config(), expected_sha256=WATER_SHA256
    )
    whale, vessel = pq.read_table(whale_path), pq.read_table(vessel_path)
    wm = _metadata(whale, "blue_whale_grid_transfer_v1")
    vm = _metadata(vessel, "production_vessel_input_v1")
    require(
        wm["inputs"]["target_grid_sha256"]
        == vm["input"]["target_grid_sha256"]
        == WATER_SHA256,
        "target identity differs",
    )
    require(
        wm["inputs"]["configuration_sha256"] == vm["input"]["configuration_sha256"],
        "configuration identities differ",
    )
    require(
        vm["grid_id"] == INPUT_ID and vm["input"]["period_input_id"] == PERIOD_ID,
        "vessel/period identity differs",
    )
    require(vm["parameters"] == selected_method(), "selected vessel method differs")
    require(
        vm["input"]["period_input_readiness"]["status"] == "ready", "period not ready"
    )
    require(
        vm["input"]["observational_completeness"]["status"] == "unverified",
        "completeness upgraded",
    )
    require(
        [p["utc_date"] for p in vm["input"]["partitions"]]
        == list(accepted_utc_dates()),
        "exact accepted UTC dates differ",
    )
    validate_generation_lineage(
        json.loads(paths["whale_lineage"][0].read_bytes()), wm, "whale"
    )
    validate_generation_lineage(
        json.loads(paths["vessel_lineage"][0].read_bytes()), vm, "vessel"
    )
    quality = json.loads(paths["vessel_quality"][0].read_bytes())
    require(
        quality["output"]["sha256"] == VESSEL_SHA256, "quality output digest differs"
    )
    return join_inputs(grid, whale, vessel), {
        label: sha256_file(path) for label, (path, _) in paths.items()
    }


def validate_generation_lineage(
    doc: dict[str, Any], metadata: dict[str, Any], kind: str
) -> None:
    """Reconcile source/output references with checksum-verified dataset metadata.

    Clocks, locators, software and resource settings describe an execution.
    The period manifest itself may be regenerated; its daily analytical inputs
    must still match every accepted partition. No historical paths are opened.
    """
    try:
        require(kind in ("whale", "vessel"), "unknown lineage kind")
        whale = kind == "whale"
        contract = (
            "blue_whale_grid_transfer_lineage_v1"
            if whale
            else "production_vessel_input_lineage_v1"
        )
        require(doc["contract"] == contract, "lineage contract differs")
        run = doc["run"]
        for field in ("started_at", "completed_at"):
            stamp = datetime.fromisoformat(run[field])
            require(stamp.utcoffset() == UTC.utcoffset(stamp), "lineage clock not UTC")
        require(
            datetime.fromisoformat(run["completed_at"])
            >= datetime.fromisoformat(run["started_at"]),
            "lineage clocks reversed",
        )
        require(bool(run["run_id"].strip()), "lineage run ID missing")
        inputs = metadata["inputs" if whale else "input"]
        require(
            run["configuration"]
            == {"sha256": inputs["configuration_sha256"], "version": 1},
            "lineage configuration differs",
        )
        references = {}
        for direction in ("inputs", "outputs"):
            refs = run[direction]
            require(bool(refs), "lineage references missing")
            require(
                len({r["artifact_id"] for r in refs}) == len(refs),
                "duplicate lineage references",
            )
            for ref in refs:
                require(bool(ref["locator"].strip()), "lineage locator missing")
                require(
                    bool(re.fullmatch(r"[0-9a-f]{64}", ref["sha256"])),
                    "invalid lineage digest",
                )
            references[direction] = {r["artifact_id"]: r["sha256"] for r in refs}
        expected_inputs = {"projected-water-grid": WATER_SHA256}
        if whale:
            require(doc["dataset"] == metadata, "lineage whale dataset differs")
            expected_parameters = {
                key: metadata["method"][key]
                for key in (
                    "coverage_exact_tolerance_m2",
                    "coverage_numerical_tolerance_m2",
                    "source_overlap_area_tolerance_m2",
                    "uncertainty_propagation",
                )
            }
            expected_parameters["always_xy"] = metadata["transformation"]["always_xy"]
            conservation = metadata["diagnostics"]["conservation"]
            expected_parameters.update(
                {
                    "conservation_absolute_tolerance_animals": conservation[
                        "absolute_tolerance_animals"
                    ],
                    "conservation_relative_tolerance": conservation[
                        "relative_tolerance"
                    ],
                }
            )
            require(
                doc["parameters"] == expected_parameters, "lineage whale method differs"
            )
            expected_inputs["noaa-swfsc-blue-whale-source"] = inputs[
                "whale_source_sha256"
            ]
            expected_outputs = {"blue-whale-grid-transfer": WHALE_SHA256}
            require(doc["output"]["sha256"] == WHALE_SHA256, "lineage output differs")
            for name, key in (
                ("target_grid", "target_grid_sha256"),
                ("whale_source", "whale_source_sha256"),
            ):
                require(
                    doc["inputs"][name]["sha256"] == inputs[key],
                    "lineage source differs",
                )
            validations = {
                "whale-source-contract",
                "target-grid-contract",
                "source-polygon-overlap",
                "modeled-abundance-conservation",
            }
        else:
            require(run["run_id"] == metadata["grid_id"], "lineage vessel ID differs")
            require(
                doc["parameters"] == metadata["parameters"], "lineage method differs"
            )
            require(
                doc["processing_version"] == metadata["processing_version"],
                "lineage processing version differs",
            )
            expected_inputs.update(
                {
                    "cleaned-ais-" + p["utc_date"]: p["cleaned_parquet_sha256"]
                    for p in inputs["partitions"]
                }
            )
            manifest = references["inputs"].pop("multi-day-cleaned-ais-manifest")
            require(bool(manifest), "lineage period manifest missing")
            expected_outputs = {
                "production-vessel-input": VESSEL_SHA256,
                "production-vessel-input-quality": VESSEL_QUALITY_SHA256,
            }
            validations = {"candidate-segment-accounting", "distance-conservation"}
        require(
            references["inputs"] == expected_inputs, "lineage analytical inputs differ"
        )
        require(
            references["outputs"] == expected_outputs, "lineage output digests differ"
        )
        records = run["validations"]
        require(
            {r["name"] for r in records} == validations
            and len(records) == len(validations)
            and all(r["passed"] is True for r in records),
            "lineage validations missing or failed",
        )
        require(
            bool(run["steps"])
            and all(s["name"].strip() and s["version"].strip() for s in run["steps"]),
            "lineage processing steps missing",
        )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"{kind} lineage malformed: {exc}") from exc
