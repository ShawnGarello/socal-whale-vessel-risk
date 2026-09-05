"""Read-only, bounded follow-up of the exact M3 period evidence.

Run as scripts.m3_completion_diagnostics through the resource profiler.
This produces diagnostics, never a production vessel input or coverage claim.
"""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.multiday_ais import load_period_manifest
from whale_vessel_analysis.multiday_ais_relation import (
    RelationResources,
    open_period_relation,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temp-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2] / "data" / "interim"
    if not args.output.resolve().is_relative_to(root) or args.output.exists():
        raise ValueError("output must be a fresh ignored interim file")
    manifest = load_period_manifest(args.manifest)
    assert manifest["period_input_id"] == "multiday-ais-17e982f999f7093945193378"
    quality = []
    for entry in manifest["dates"]:
        bundle = Path(entry["local_provenance"]["bundle_path"])
        identity = entry["cleaner_bundle_compatibility"]
        for name, field in (
            ("quality-report.json", "quality_report_sha256"),
            ("run-metadata.json", "run_metadata_sha256"),
        ):
            assert sha256_file(bundle / name) == identity[field]
        report = json.loads((bundle / "quality-report.json").read_text())
        quality.append({"date": entry["utc_date"], "counts": report["counts"]})
    resources = RelationResources("1GB", args.temp_directory, 1)
    transformer = Transformer.from_crs(4326, 3310, always_xy=True)
    strata = defaultdict(lambda: defaultdict(float))
    with open_period_relation(manifest, resources, require_ready=True) as relation:
        hourly = relation.connection.execute(
            f"SELECT observed_utc_date, hour(observed_at_utc), vessel_type_group, "
            f"count(*), count(DISTINCT mmsi) FROM {relation.view_name} "
            "GROUP BY 1,2,3 ORDER BY 1,2,3"
        ).fetchall()
        lengths = relation.connection.execute(
            f"SELECT vessel_type_group, CASE WHEN length_m IS NULL THEN 'null' "
            "WHEN length_m < 20 THEN '0-20' WHEN length_m < 50 THEN '20-50' "
            "WHEN length_m < 100 THEN '50-100' ELSE '100+' END, "
            f"count(*), count(DISTINCT mmsi) FROM {relation.view_name} "
            "GROUP BY 1,2 ORDER BY 1,2"
        ).fetchall()
        # Entire-period adjacency is preserved. Only bounded batches enter Python.
        for batch in relation.adjacent_observation_batches(50000):
            data = batch.to_pydict()
            xs, ys = transformer.transform(data["longitude"], data["latitude"])
            next_lons = [v if v is not None else 0 for v in data["next_longitude"]]
            next_lats = [v if v is not None else 0 for v in data["next_latitude"]]
            nx, ny = transformer.transform(next_lons, next_lats)
            for i, end in enumerate(data["next_observed_at_utc"]):
                if end is None:
                    continue
                gap = (end - data["observed_at_utc"][i]) / 1e6
                if gap <= 0 or gap > 1800:
                    continue
                distance = math.hypot(nx[i] - xs[i], ny[i] - ys[i])
                implied = distance / gap * 1.9438444924406046
                speed_band = (
                    "0-30" if implied <= 30 else "30-50" if implied <= 50 else "50+"
                )
                gap_band = "0-300" if gap <= 300 else "300-1800"
                key = f"{data['vessel_type_group'][i]}/{gap_band}/{speed_band}"
                bucket = strata[key]
                bucket["segments"] += 1
                bucket["parent_metres"] += distance
                a, b = data["sog_knots"][i], data["next_sog_knots"][i]
                if a is not None and b is not None:
                    bucket["both_sog_available"] += 1
                    difference = abs(implied - (a + b) / 2)
                    bucket["within_2_knots_of_endpoint_mean"] += difference <= 2
                    bucket["within_5_knots_of_endpoint_mean"] += difference <= 5
                    bucket["both_reported_sog_above_30"] += a > 30 and b > 30
                # Geographic edge proximity is an explicit diagnostic band, not
                # a reception mask or an estimate of lost entry/exit distance.
                lon, lat = data["longitude"][i], data["latitude"][i]
                if min(lon + 122, -117 - lon, lat - 32, 35 - lat) <= 0.05:
                    bucket["starts_within_005_degree_context_edge"] += 1
                    bucket["edge_parent_metres"] += distance
    payload = {
        "period_input_id": manifest["period_input_id"],
        "manifest_sha256": sha256_file(args.manifest),
        "cleaner_reports": quality,
        "hourly_columns": [
            "UTC_date",
            "UTC_hour",
            "group",
            "observations",
            "distinct_mmsi",
        ],
        "hourly": [[str(row[0]), *row[1:]] for row in hourly],
        "length_columns": ["group", "metres_band", "observations", "distinct_mmsi"],
        "lengths": lengths,
        "segment_strata": dict(sorted(strata.items())),
        "limitations": [
            "SOG agreement is a cross-check, not ground truth.",
            "2/5 knot agreement and 0.05 degree edge bands are diagnostic choices.",
            "Length-band distinct MMSIs may overlap; do not sum them.",
            "Parent distance is not allocated cell distance.",
            "Neither low hourly counts nor gaps establish missing coverage.",
            "No absent outside-extent observations or omitted distance is estimated.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(
            payload, stream, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        stream.write("\n")
    print(json.dumps({"output_sha256": sha256_file(args.output), "strata": strata}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
