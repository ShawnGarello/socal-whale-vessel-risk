"""Verify and compare the four completed, repeated M3 candidate bundles."""

import argparse
import itertools
import json
import math
from pathlib import Path

import pyarrow.parquet as pq

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file

GROUPS = ("passenger", "cargo", "tanker", "all_commercial")


def compare_cells(first, second, group):
    """Compare aligned physical-unit cells; thresholds are reporting choices."""
    if [row["cell_id"] for row in first] != [row["cell_id"] for row in second]:
        raise ValueError("cell identities/order differ")
    field = f"vessel_km_{group}"
    differences = [b[field] - a[field] for a, b in zip(first, second, strict=True)]
    absolute_total = math.fsum(abs(value) for value in differences)
    top = sorted(
        range(len(first)), key=lambda i: (-abs(differences[i]), first[i]["cell_id"])
    )[:10]
    return {
        "changed_above_1e_minus_9_km": sum(abs(value) > 1e-9 for value in differences),
        "changed_at_least_1_km": sum(abs(value) >= 1 for value in differences),
        "positive_cells_first": sum(row[field] > 0 for row in first),
        "positive_cells_second": sum(row[field] > 0 for row in second),
        "net_difference_km": math.fsum(differences),
        "absolute_difference_km": absolute_total,
        "top_ten_share_of_absolute_difference": (
            math.fsum(abs(differences[i]) for i in top) / absolute_total
            if absolute_total
            else None
        ),
        "top_ten_cells": [
            {
                "cell_id": first[i]["cell_id"],
                "first_km": first[i][field],
                "second_km": second[i][field],
                "difference_km": differences[i],
            }
            for i in top
        ],
    }


def rank_positions(values):
    """Average ranks in descending order; tied values share their mean rank.

    Ordinal ranks broken by cell index would invent an ordering the data does
    not contain. Many cells hold identical vessel-kilometres, including the
    many that hold exactly zero, so tie handling changes the result: it can
    reverse the sign of the correlation and make a constant column look
    perfectly correlated with anything.
    """
    order = sorted(range(len(values)), key=lambda i: -values[i])
    positions = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        mean_rank = (start + end) / 2
        for index in order[start : end + 1]:
            positions[index] = mean_rank
        start = end + 1
    return positions


def spearman(first, second):
    """Tie-corrected rank correlation over the identical cell set.

    Returns None when either side has no rank variance at all, because the
    correlation is undefined rather than perfect.
    """
    a, b = rank_positions(first), rank_positions(second)
    count = len(a)
    mean_a, mean_b = math.fsum(a) / count, math.fsum(b) / count
    numerator = math.fsum((a[i] - mean_a) * (b[i] - mean_b) for i in range(count))
    deviation_a = math.sqrt(math.fsum((value - mean_a) ** 2 for value in a))
    deviation_b = math.sqrt(math.fsum((value - mean_b) ** 2 for value in b))
    if deviation_a == 0.0 or deviation_b == 0.0:
        return None
    return numerator / (deviation_a * deviation_b)


def pattern_stability(first, second, group):
    """Report whether a candidate change reorders cells or only rescales them.

    Whole-period totals cannot show this. Relative change is defined only where
    the baseline cell already carries distance; newly touched cells are counted
    separately rather than treated as an infinite increase.
    """
    field = f"vessel_km_{group}"
    a = [row[field] for row in first]
    b = [row[field] for row in second]
    relative = [(b[i] - a[i]) / a[i] for i in range(len(a)) if a[i] > 0]
    return {
        "spearman_rank_correlation": spearman(a, b),
        "maximum_relative_increase": max(relative) if relative else None,
        "cells_above_10_percent_relative": sum(value > 0.10 for value in relative),
        "cells_above_50_percent_relative": sum(value > 0.50 for value in relative),
        "cells_with_baseline_distance": len(relative),
        "newly_positive_cells": sum(1 for i in range(len(a)) if a[i] == 0 and b[i] > 0),
        "top_ten_cell_ids_first": [
            first[i]["cell_id"]
            for i in sorted(range(len(a)), key=lambda i: (-a[i], i))[:10]
        ],
        "top_ten_cell_ids_second": [
            second[i]["cell_id"]
            for i in sorted(range(len(b)), key=lambda i: (-b[i], i))[:10]
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-root", type=Path, required=True)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    interim = Path(__file__).resolve().parents[2] / "data/interim"
    if not args.output.resolve().is_relative_to(interim) or args.output.exists():
        raise ValueError("comparison requires a fresh ignored interim output")
    grid_hash = sha256_file(args.grid)
    if grid_hash != "7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031":
        raise ValueError("water-grid checksum mismatch")
    grid = pq.read_table(args.grid).to_pylist()
    bundles, tables = {}, {}
    for gap, speed in ((300, 30), (300, 50), (1800, 30), (1800, 50)):
        name = f"g{gap}-s{speed}"
        first, repeat = (
            args.matrix_root / f"{name}-{suffix}" for suffix in ("first", "repeat")
        )
        hashes = {}
        for filename in ("vessel-grid.parquet", "quality-report.json"):
            digest = sha256_file(first / filename)
            if sha256_file(repeat / filename) != digest:
                raise ValueError(f"repeat bytes differ: {name}/{filename}")
            hashes[filename] = digest
        quality = json.loads((first / "quality-report.json").read_text())
        if quality["input"]["target_grid"]["sha256"] != grid_hash:
            raise ValueError("candidate has a different grid")
        if (
            quality["parameters"]["maximum_gap_seconds"] != gap
            or quality["parameters"]["implied_speed_ceiling_knots"] != speed
        ):
            raise ValueError("candidate parameter mismatch")
        if (
            quality["input"]["period_input_id"]
            != "multiday-ais-17e982f999f7093945193378"
        ):
            raise ValueError("period identity mismatch")
        for directory in (first, repeat):
            lineage = json.loads((directory / "run-metadata.json").read_text())
            assert lineage["run"]["run_id"] == quality["grid_id"]
            assert {item["sha256"] for item in lineage["run"]["outputs"]} == set(
                hashes.values()
            )
        table = pq.read_table(first / "vessel-grid.parquet").to_pylist()
        assert len(table) == len(grid) == 4516
        for actual, expected in zip(table, grid, strict=True):
            assert all(actual[key] == value for key, value in expected.items())
            assert all(value is not None for value in actual.values())
            for group in GROUPS:
                km = actual[f"vessel_km_{group}"]
                assert math.isfinite(km) and km >= 0
                assert math.isclose(
                    actual[f"vessel_km_per_water_km2_{group}"],
                    km / actual["water_area_km2"],
                    rel_tol=1e-10,
                    abs_tol=1e-10,
                )
            assert math.isclose(
                actual["vessel_km_all_commercial"],
                math.fsum(actual[f"vessel_km_{group}"] for group in GROUPS[:3]),
                abs_tol=1e-8,
            )
        for group in GROUPS:
            distance = quality["distance_conservation"]["by_group"][group]
            assert math.isclose(
                math.fsum(row[f"vessel_km_{group}"] for row in table) * 1000,
                distance["allocated_to_cells_m"],
                rel_tol=1e-12,
                abs_tol=1e-6,
            )
        tables[name] = table
        bundles[name] = {
            "grid_id": quality["grid_id"],
            "hashes": hashes,
            "conservation": quality["distance_conservation"],
            "counts": quality["counts"],
            "exclusions": quality["exclusions"],
        }
    comparisons = {}
    names = ("g300-s30", "g300-s50", "g1800-s30", "g1800-s50")
    for a, b in itertools.combinations(names, 2):
        comparisons[f"{a}_to_{b}"] = {
            group: {
                **compare_cells(tables[a], tables[b], group),
                **pattern_stability(tables[a], tables[b], group),
            }
            for group in GROUPS
        }
        for x, y in zip(tables[a], tables[b], strict=True):
            assert all(x[key] == y[key] for key in x if key.startswith("distinct_"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "bundles": bundles,
                "comparisons": comparisons,
                "distinct_counts_candidate_invariant": True,
                "limitations": (
                    "Parent and allocated distance are distinct; "
                    "no coverage or exposure result. Rank correlation and "
                    "relative change describe candidate sensitivity only; "
                    "neither establishes that any candidate is correct."
                ),
            },
            stream,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        stream.write("\n")
    print(sha256_file(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
