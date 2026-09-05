"""Independently verify fresh production bundles without rerunning aggregation."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import pyarrow.parquet as pq
from pyproj import CRS

from whale_vessel_analysis.cleaned_ais_bundle import canonical_json, sha256_file

GROUPS = ("passenger", "cargo", "tanker", "all_commercial")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_cells(rows):
    """Recompute physical-unit invariants and missing/zero semantics."""
    result = {}
    for group in GROUPS:
        for row in rows:
            distance = row[f"vessel_km_{group}"]
            available, unavailable, inconsistent = (
                row[f"sog_{status}_km_{group}"]
                for status in ("available", "unavailable", "inconsistent")
            )
            require(
                all(
                    math.isfinite(v) and v >= 0
                    for v in (distance, available, unavailable, inconsistent)
                ),
                "invalid distance",
            )
            require(
                math.isclose(
                    distance,
                    math.fsum((available, unavailable, inconsistent)),
                    rel_tol=1e-12,
                    abs_tol=1e-9,
                ),
                "speed categories differ",
            )
            require(
                math.isclose(
                    row[f"vessel_km_per_water_km2_{group}"],
                    distance / row["water_area_km2"],
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ),
                "density units differ",
            )
            for field, denominator, ceiling in (
                ("reported_sog_mean_knots", available, 35),
                ("implied_speed_mean_knots", distance, 30),
            ):
                value = row[f"{field}_{group}"]
                require(
                    (value is None) == (denominator == 0), "null/zero semantics differ"
                )
                if value is not None:
                    require(
                        math.isfinite(value) and 0 <= value <= ceiling + 1e-9,
                        "speed outside selected support",
                    )
        total = math.fsum(row[f"vessel_km_{group}"] for row in rows)
        available = math.fsum(row[f"sog_available_km_{group}"] for row in rows)
        result[group] = {
            "vessel_km": total,
            "sog_available_km": available,
            "sog_unavailable_km": math.fsum(
                row[f"sog_unavailable_km_{group}"] for row in rows
            ),
            "sog_inconsistent_km": math.fsum(
                row[f"sog_inconsistent_km_{group}"] for row in rows
            ),
            "reported_sog_mean_knots": (
                math.fsum(
                    (row[f"reported_sog_mean_knots_{group}"] or 0)
                    * row[f"sog_available_km_{group}"]
                    for row in rows
                )
                / available
                if available
                else None
            ),
            "implied_speed_mean_knots": (
                math.fsum(
                    (row[f"implied_speed_mean_knots_{group}"] or 0)
                    * row[f"vessel_km_{group}"]
                    for row in rows
                )
                / total
                if total
                else None
            ),
            "positive_distance_cells": sum(
                row[f"vessel_km_{group}"] > 0 for row in rows
            ),
            "null_reported_speed_cells": sum(
                row[f"reported_sog_mean_knots_{group}"] is None for row in rows
            ),
            "zero_reported_speed_cells": sum(
                row[f"reported_sog_mean_knots_{group}"] == 0 for row in rows
            ),
        }
    for row in rows:
        for field in (
            "vessel_km",
            "sog_available_km",
            "sog_unavailable_km",
            "sog_inconsistent_km",
        ):
            require(
                math.isclose(
                    row[f"{field}_all_commercial"],
                    math.fsum(row[f"{field}_{g}"] for g in GROUPS[:3]),
                    rel_tol=1e-12,
                    abs_tol=1e-9,
                ),
                "group totals differ",
            )
    return result


def verify_bundle(bundle, grid_table, grid_hash, candidate_table):
    paths = {
        name: bundle / name
        for name in ("vessel-grid.parquet", "quality-report.json", "run-metadata.json")
    }
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    table = pq.read_table(paths["vessel-grid.parquet"])
    rows = table.to_pylist()
    metadata = json.loads(table.schema.metadata[b"whale_vessel_analysis"])
    geo = json.loads(table.schema.metadata[b"geo"])
    quality = json.loads(paths["quality-report.json"].read_text())
    lineage = json.loads(paths["run-metadata.json"].read_text())
    candidate_metadata = json.loads(
        candidate_table.schema.metadata[b"whale_vessel_analysis"]
    )
    require(
        {key: value for key, value in quality.items() if key != "output"}
        == metadata["quality"],
        "embedded and sidecar quality differ",
    )
    require(
        quality["counts"] == candidate_metadata["quality"]["counts"],
        "production counts differ from selected candidate",
    )
    require(
        metadata["input"]["partitions"] == candidate_metadata["input"]["partitions"],
        "production partitions differ from candidate evidence",
    )
    require(
        metadata["contract"] == "production_vessel_input_v1",
        "wrong production contract",
    )
    require(
        quality["contract"] == "production_vessel_input_quality_v1",
        "wrong quality contract",
    )
    require(
        lineage["contract"] == "production_vessel_input_lineage_v1",
        "wrong lineage contract",
    )
    require(
        CRS.from_json_dict(geo["columns"]["geometry"]["crs"]).to_epsg() == 3310,
        "wrong CRS",
    )
    require(table.num_rows == grid_table.num_rows == 4516, "wrong row count")
    for name in grid_table.column_names:
        require(table[name].equals(grid_table[name]), f"target changed: {name}")
    require(
        table.select(candidate_table.column_names).equals(
            candidate_table, check_metadata=False
        ),
        "production activity differs from retained selected candidate",
    )
    require(metadata["input"]["target_grid_sha256"] == grid_hash, "wrong grid lineage")
    require(
        quality["output"]["sha256"] == hashes["vessel-grid.parquet"],
        "output hash differs",
    )
    require(
        quality["input"]["period_input_readiness"]["status"] == "ready",
        "period not ready",
    )
    require(
        quality["input"]["observational_completeness"]["status"] == "unverified",
        "completeness upgraded",
    )
    require(quality["input"]["partition_count"] == 153, "missing partitions")
    partitions = quality["input"]["partitions"]
    require(
        sum(p["cleaned_rows"] for p in partitions)
        == quality["counts"]["observations"]["all_commercial"],
        "observation count differs",
    )
    require(
        lineage["run"]["run_id"] == quality["input_id"] == metadata["grid_id"],
        "identity link differs",
    )
    for output in lineage["run"]["outputs"]:
        require(
            hashes[Path(output["locator"]).name] == output["sha256"],
            "lineage output hash differs",
        )
    input_hashes = {item["sha256"] for item in lineage["run"]["inputs"]}
    require(
        grid_hash in input_hashes
        and all(p["cleaned_parquet_sha256"] in input_hashes for p in partitions),
        "lineage lacks grid or cleaned partition",
    )
    require(quality["distance_conservation"]["passed"] is True, "conservation failed")
    totals = verify_cells(rows)
    require(
        sum(quality["speed_retained_segment_counts"]["all_commercial"].values())
        == quality["counts"]["candidate_segments"]["retained"],
        "retained speed classifications do not reconcile",
    )
    for group in GROUPS:
        conserved = quality["distance_conservation"]["by_group"][group]
        require(
            math.isclose(
                conserved["retained_parent_m"],
                math.fsum(
                    conserved[k]
                    for k in (
                        "allocated_to_cells_m",
                        "outside_support_m",
                        "ambiguous_boundary_m",
                        "invalid_geometry_m",
                    )
                ),
                rel_tol=1e-12,
                abs_tol=1e-6,
            ),
            "parent distance not conserved",
        )
        require(
            math.isclose(
                totals[group]["vessel_km"] * 1000,
                conserved["allocated_to_cells_m"],
                rel_tol=1e-12,
                abs_tol=1e-6,
            ),
            "cell allocation differs",
        )
        for field, value in quality["speed_totals"][group].items():
            require(
                (value is None and totals[group][field] is None)
                or math.isclose(
                    value, totals[group][field], rel_tol=1e-12, abs_tol=1e-9
                ),
                "speed quality totals differ",
            )
    core_quality = dict(metadata["quality"])
    core_quality.pop("input_id")
    source = metadata["input"]
    identity = {
        "contract": metadata["contract"],
        "schema_version": 1,
        "processing_version": metadata["processing_version"],
        "period_input": {
            k: source[k]
            for k in (
                "period_input_id",
                "period_input_readiness",
                "observational_completeness",
            )
        },
        "partitions": source["partitions"],
        "target_grid_sha256": grid_hash,
        "configuration_sha256": source["configuration_sha256"],
        "parameters": metadata["parameters"],
        "quality": core_quality,
        "cells": [
            {
                "cell_id": row["cell_id"],
                **{
                    field: {g: row[f"{field}_{g}"] for g in GROUPS}
                    for field in ("vessel_km", "distinct_mmsi", "distinct_mmsi_dates")
                },
            }
            for row in rows
        ],
        "speeds": [
            {
                g: {
                    field: row[f"{field}_{g}"]
                    for field in (
                        "sog_available_km",
                        "sog_unavailable_km",
                        "sog_inconsistent_km",
                        "reported_sog_mean_knots",
                        "implied_speed_mean_knots",
                    )
                }
                for g in GROUPS
            }
            for row in rows
        ],
    }
    expected_id = (
        "vessel-input-"
        + hashlib.sha256(canonical_json(identity).encode()).hexdigest()[:24]
    )
    require(
        expected_id == metadata["grid_id"],
        "content-derived production identity differs",
    )
    return {
        "input_id": expected_id,
        "hashes": hashes,
        "totals": totals,
        "counts": quality["counts"],
        "speed_retained_segment_counts": quality["speed_retained_segment_counts"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("first", "repeat", "grid", "candidate", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--expected-grid-sha256", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    args = parser.parse_args()
    interim = Path(__file__).resolve().parents[2] / "data/interim"
    require(
        args.output.resolve().is_relative_to(interim) and not args.output.exists(),
        "verification requires fresh ignored interim output",
    )
    require(
        sha256_file(args.grid) == args.expected_grid_sha256, "grid checksum differs"
    )
    require(
        sha256_file(args.candidate) == args.expected_candidate_sha256,
        "candidate checksum differs",
    )
    grid, candidate = pq.read_table(args.grid), pq.read_table(args.candidate)
    first = verify_bundle(args.first, grid, args.expected_grid_sha256, candidate)
    repeat = verify_bundle(args.repeat, grid, args.expected_grid_sha256, candidate)
    for name in ("vessel-grid.parquet", "quality-report.json"):
        require(
            first["hashes"][name] == repeat["hashes"][name],
            "deterministic repeat differs",
        )
    require(
        first["hashes"]["run-metadata.json"] != repeat["hashes"]["run-metadata.json"],
        "execution lineage did not change",
    )
    report = {
        "passed": True,
        "first": first,
        "repeat": repeat,
        "grid_sha256": args.expected_grid_sha256,
        "candidate_sha256": args.expected_candidate_sha256,
        "visual_inspection": "separate required QGIS evidence",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(report) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
