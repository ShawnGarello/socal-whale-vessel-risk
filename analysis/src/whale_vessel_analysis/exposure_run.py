"""Generate a fresh local M6 exploratory bundle; no publication or AIS processing.

python -m whale_vessel_analysis.exposure_run --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from pyproj import CRS

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.exposure import (
    ASSUMPTION,
    METHOD_VERSION,
    METHODS,
    PERCENTILES,
    STATUS,
    ExposureCell,
    analyze_grid,
    coarsen_10km,
    intensities,
    normalized,
    prepare_cells,
)
from whale_vessel_analysis.exposure_geometry import (
    DOMAIN_SHA256,
    VSR_SHA256,
    load_local_boundaries,
)
from whale_vessel_analysis.exposure_inputs import load_exposure_inputs, require
from whale_vessel_analysis.reporting_domain import load_default_reporting_domain

CONTRACT = "exploratory_relative_exposure_v1"
ROOT = Path(__file__).resolve().parents[3]


def json_text(value: object) -> str:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    )


def method_contract() -> dict[str, Any]:
    return {
        "contract": CONTRACT,
        "method_version": METHOD_VERSION,
        "decision": "ADR 0020",
        "status": STATUS,
        "assumption": ASSUMPTION,
        "period_start_utc": "2024-07-01T00:00:00Z",
        "period_end_exclusive_utc": "2024-12-01T00:00:00Z",
        "whale_vintage": (
            "NOAA/SWFSC 2020b multi-year summer-fall; survey basis 1991-2018"
        ),
        "vsr_snapshot_retrieved": "2026-08-25",
        "vsr_fid": 126,
        "product": "W * (L / full_water_km2)",
        "log_traffic": "(W / 1 animal_per_km2) * log1p(T / 1 period_vessel_km_per_km2)",
        "product_intensity_units": "modeled animals * vessel-km / km^4, period total",
        "product_integrated_units": "modeled animals * vessel-km / km^2, period total",
        "log_traffic_intensity_units": "dimensionless",
        "log_traffic_integrated_units": "index-km^2",
        "normalization": (
            "divide by maximum intensity among positive-qualified-area cells"
        ),
        "integration": "intensity * exact qualified/inside/outside area in km2",
        "high_percentiles": PERCENTILES,
        "high_reference_populations": ["all_valid", "positive_only"],
        "quantile": (
            "smallest observed intensity attaining cumulative qualified area "
            ">= p * reference area; include all ties"
        ),
        "high_zero_threshold": "unavailable",
        "speed_weight": "none",
        "outside_domain": "null result; excluded from statistics; not low traffic",
        "zero_movement": "zero retained movement, not verified absence",
        "observational_completeness": "unverified",
        "publisher_transfer_completeness": "unverified",
        "10km": (
            "whole-10000-m-aligned union of water; sum abundance and vessel-km "
            "before product"
        ),
        "outside_concentrations": (
            "top 10 cells ranked by integrated outside contribution; "
            "ID breaks exact ties; not inferred clusters"
        ),
        "reporting_domain": load_default_reporting_domain().to_dict(),
        "public_delivery": (
            "not selected here; no copied or derived VSR geometry in output"
        ),
    }


def exposure_table(
    cells: Sequence[ExposureCell], report: dict[str, Any], identity: dict[str, Any]
) -> pa.Table:
    """One primary geometry: exact domain-qualified water, never VSR-clipped.

    Excluded cells remain as rows with null geometry/results and explicit status.
    Original full-water input scalars are retained for arithmetic verification.
    """
    values = {m: intensities(cells, m) for m in METHODS}
    indices = {m: normalized(values[m], cells)[1] for m in METHODS}
    rows = []
    for i, cell in enumerate(cells):
        s, a = cell.source, cell.areas
        included = a.qualified_m2 > 0
        if included:
            require(
                cell.qualified_geometry.geom_type in ("Polygon", "MultiPolygon"),
                "nonpolygon qualified output",
            )
        row: dict[str, Any] = {
            "cell_id": s.cell_id,
            "x_min_m": s.x_min_m,
            "y_min_m": s.y_min_m,
            "analysis_status": "qualified" if included else "excluded_domain",
            "water_area_km2": s.water_km2,
            "qualified_area_km2": a.qualified_m2 / 1e6,
            "inside_vsr_area_km2": a.inside_vsr_m2 / 1e6,
            "outside_vsr_area_km2": a.outside_vsr_m2 / 1e6,
            "excluded_domain_area_km2": a.excluded_domain_m2 / 1e6,
            "whale_density_animals_per_km2": s.whale_density,
            "whale_abundance_animals": s.whale_abundance,
            "vessel_km": s.vessel_km,
            "geometry": bytes(cell.qualified_geometry.wkb) if included else None,
        }
        for method in METHODS:
            value = values[method][i]
            row[f"{method}_intensity"] = value if included else None
            row[f"{method}_index"] = indices[method][i]
            for suffix, area in (
                ("qualified", a.qualified_m2),
                ("inside", a.inside_vsr_m2),
                ("outside", a.outside_vsr_m2),
            ):
                row[f"{method}_integrated_{suffix}"] = (
                    value * area / 1e6 if included else None
                )
            for threshold in report["methods"][method]["thresholds"]:
                if threshold["reference"] == "all_valid":
                    p = round(threshold["percentile"] * 100)
                    row[f"{method}_high_p{p}"] = (
                        value >= threshold["threshold"]
                        if included and threshold["available"]
                        else None
                    )
        rows.append(row)
    # Explicit types preserve all-zero/all-excluded nullable result schemas.
    fields = []
    for key in rows[0]:
        kind = (
            pa.binary()
            if key == "geometry"
            else pa.string()
            if key in ("cell_id", "analysis_status")
            else pa.int64()
            if key in ("x_min_m", "y_min_m")
            else pa.bool_()
            if "_high_p" in key
            else pa.float64()
        )
        fields.append(pa.field(key, kind))
    geo = {
        "version": "1.1.0",
        "primary_column": "geometry",
        "columns": {
            "geometry": {
                "encoding": "WKB",
                "geometry_types": ["MultiPolygon", "Polygon"],
                "crs": CRS.from_epsg(3310).to_json_dict(),
            }
        },
    }
    schema = pa.schema(
        fields,
        metadata={
            b"geo": json_text(geo).encode(),
            b"whale_vessel_analysis": json_text(identity).encode(),
        },
    )
    return pa.Table.from_pylist(rows, schema=schema)


def verify_table(table: pa.Table, report: dict[str, Any]) -> None:
    """Independently recompute formula, units, masks and totals from stored rows."""
    rows = table.to_pylist()
    require(len({r["cell_id"] for r in rows}) == len(rows), "output duplicate IDs")
    for row in rows:
        q = row["qualified_area_km2"]
        require(
            math.isclose(
                row["inside_vsr_area_km2"] + row["outside_vsr_area_km2"],
                q,
                rel_tol=1e-10,
                abs_tol=1e-12,
            ),
            "stored areas not conserved",
        )
        if q == 0:
            require(
                row["analysis_status"] == "excluded_domain" and row["geometry"] is None,
                "excluded geometry/status differs",
            )
        else:
            geometry = shapely.from_wkb(row["geometry"])
            require(
                geometry.is_valid
                and math.isclose(geometry.area / 1e6, q, rel_tol=1e-10, abs_tol=1e-12),
                "qualified geometry area differs",
            )
        for method in METHODS:
            if q == 0:
                require(
                    all(row[k] is None for k in row if k.startswith(method + "_")),
                    "excluded results must be null",
                )
                continue
            traffic = row["vessel_km"] / row["water_area_km2"]
            expected = row["whale_density_animals_per_km2"] * (
                traffic if method == "product" else math.log1p(traffic)
            )
            require(
                math.isclose(
                    row[f"{method}_intensity"], expected, rel_tol=1e-12, abs_tol=1e-15
                ),
                "stored formula differs",
            )
            maximum = report["methods"][method]["normalization_maximum"]
            index = row[f"{method}_index"]
            require(
                index is None
                if maximum == 0
                else index is not None
                and math.isclose(
                    index, expected / maximum, rel_tol=1e-12, abs_tol=1e-15
                ),
                "stored index differs",
            )
            for suffix, field in (
                ("qualified", "qualified_area_km2"),
                ("inside", "inside_vsr_area_km2"),
                ("outside", "outside_vsr_area_km2"),
            ):
                require(
                    math.isclose(
                        row[f"{method}_integrated_{suffix}"],
                        expected * row[field],
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    ),
                    "stored integration differs",
                )
    for method in METHODS:
        for suffix in ("qualified", "inside", "outside"):
            actual = math.fsum(r[f"{method}_integrated_{suffix}"] or 0 for r in rows)
            require(
                math.isclose(
                    actual,
                    report["methods"][method][f"integrated_{suffix}"],
                    rel_tol=1e-12,
                    abs_tol=1e-9,
                ),
                "stored summary differs",
            )
        for threshold in report["methods"][method]["thresholds"]:
            selected = [
                r
                for r in rows
                if r["qualified_area_km2"] > 0
                and threshold["available"]
                and r[f"{method}_intensity"] >= threshold["threshold"]
            ]
            require(
                [r["cell_id"] for r in selected] == threshold["selected_cell_ids"],
                "stored threshold membership differs",
            )
            if selected:
                require(
                    math.isclose(
                        math.fsum(r["qualified_area_km2"] for r in selected),
                        threshold["high_area_km2"],
                        rel_tol=1e-12,
                        abs_tol=1e-9,
                    ),
                    "stored high area differs",
                )
            if threshold["reference"] == "all_valid":
                key = f"{method}_high_p{round(threshold['percentile'] * 100)}"
                require(
                    [r["cell_id"] for r in rows if r[key] is True]
                    == threshold["selected_cell_ids"],
                    "stored high flags differ",
                )


def validate_destination(path: Path, inputs: Sequence[Path]) -> Path:
    target = path.resolve()
    roots = [(ROOT / "data" / part).resolve() for part in ("interim", "derived")]
    require(
        any(target.is_relative_to(root) and target != root for root in roots),
        "output must be beneath this worktree's ignored interim/derived root",
    )
    require(not target.exists(), "output already exists; no overwrite")
    require(
        not any(
            p.resolve().is_relative_to(target) or target.is_relative_to(p.resolve())
            for p in inputs
        ),
        "input/output overlap",
    )
    return target


def write_bundle(
    destination: Path,
    grids: dict[str, tuple[ExposureCell, ...]],
    identity: dict[str, Any],
    started: datetime,
    paths: dict[str, str],
    input_lineage_sha256: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Fresh atomic directory; failed temporary evidence is preserved."""
    target = validate_destination(destination, [Path(p) for p in paths.values()])
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.temporary-", dir=target.parent)
    )
    try:
        reports = {name: analyze_grid(cells) for name, cells in grids.items()}
        report = {"identity": identity, "grids": reports}
        outputs = {}
        for name, cells in grids.items():
            table = exposure_table(cells, reports[name], identity)
            path = temporary / f"exposure-{name}.parquet"
            pq.write_table(
                table,
                path,
                compression="zstd",
                compression_level=9,
                use_dictionary=False,
                write_statistics=True,
                version="2.6",
                data_page_version="2.0",
                row_group_size=1024,
            )
            stored = pq.read_table(path)
            require(
                stored.equals(table, check_metadata=True), "Parquet read-back differs"
            )
            verify_table(stored, reports[name])
            outputs[path.name] = sha256_file(path)
        report["output_sha256"] = outputs.copy()
        report_path = temporary / "sensitivity-report.json"
        report_path.write_text(json_text(report), encoding="utf-8")
        outputs[report_path.name] = sha256_file(report_path)
        lineage = {
            "run_id": identity["run_id"],
            "started_at_utc": started.isoformat(),
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "input_paths": paths,
            "input_lineage_sha256": input_lineage_sha256 or {},
            "input_sha256": identity["input_sha256"],
            "output_sha256": outputs,
            "visual_inspection_status": "not_completed_by_generation",
            "status": STATUS,
        }
        (temporary / "run-metadata.json").write_text(
            json_text(lineage), encoding="utf-8"
        )
        require(not target.exists(), "concurrent output arrived; refusing replacement")
        temporary.rename(target)
    except Exception as exc:
        raise ValueError(
            f"M6 bundle failed; retained evidence at {temporary}: {exc}"
        ) from exc
    return {
        "run_id": identity["run_id"],
        "output_directory": str(target),
        "output_sha256": outputs,
        "status": STATUS,
    }


def run(
    water: Path, whale: Path, vessel: Path, domain: Path, vsr: Path, output: Path
) -> dict[str, Any]:
    started = datetime.now(UTC)
    paths = {
        "water": str(water.resolve()),
        "whale": str(whale.resolve()),
        "vessel": str(vessel.resolve()),
        "domain": str(domain.resolve()),
        "vsr": str(vsr.resolve()),
    }
    validate_destination(output, [Path(p) for p in paths.values()])
    cells, hashes = load_exposure_inputs(water, whale, vessel)
    lineage_hashes = {k: v for k, v in hashes.items() if k.endswith("_lineage")}
    hashes = {k: v for k, v in hashes.items() if k not in lineage_hashes}
    boundaries = load_local_boundaries(domain, vsr)
    identity: dict[str, Any] = {
        "method": method_contract(),
        "input_sha256": {**hashes, "domain": DOMAIN_SHA256, "vsr": VSR_SHA256},
        "software": {
            "python": platform.python_version(),
            **{p: version(p) for p in ("pyarrow", "shapely", "pyproj")},
        },
    }
    identity["run_id"] = (
        "exposure-" + hashlib.sha256(json_text(identity).encode()).hexdigest()[:24]
    )
    fine = prepare_cells(cells, boundaries)
    coarse_inputs = coarsen_10km(cells)
    for field in ("water_km2", "whale_abundance", "vessel_km"):
        require(
            math.isclose(
                math.fsum(getattr(c, field) for c in cells),
                math.fsum(getattr(c, field) for c in coarse_inputs),
                rel_tol=1e-10,
                abs_tol=1e-9,
            ),
            f"coarse {field} not conserved",
        )
    coarse = prepare_cells(coarse_inputs, boundaries)
    for grid in (fine, coarse):
        require(
            math.isclose(
                math.fsum(c.areas.qualified_m2 for c in grid),
                boundaries.domain.area,
                rel_tol=1e-10,
                abs_tol=1e-6,
            ),
            "qualified area does not match independent union",
        )
    return write_bundle(
        output, {"5km": fine, "10km": coarse}, identity, started, paths, lineage_hashes
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("water", "whale", "vessel", "domain", "vsr", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(
            args.water, args.whale, args.vessel, args.domain, args.vsr, args.output
        )
    except (ValueError, OSError, KeyError, pa.ArrowException) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json_text(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
