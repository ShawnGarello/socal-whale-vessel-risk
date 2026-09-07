"""CLI for validated M6 display and application-results delivery artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from whale_vessel_analysis.exposure_delivery import (
    ExposureDeliveryError,
    load_bundle,
    parse_utc_timestamp,
    write_delivery,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whale-vessel-exposure-delivery",
        description=(
            "Export a checksum-identified exploratory_relative_exposure_v1 bundle "
            "as deterministic qualified-water WGS 84 GeoJSON plus a separate "
            "small application-results JSON. No VSR geometry, local path, or "
            "private generation lineage enters either public contract."
        ),
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        required=True,
        help="existing M6 analytical bundle directory",
    )
    for label in ("5km", "10km", "report"):
        parser.add_argument(
            f"--expected-{label}-sha256",
            required=True,
            help=f"required SHA-256 for the analytical {label} artifact",
        )
    parser.add_argument(
        "--display-output",
        type=Path,
        required=True,
        help="qualified-water WGS 84 GeoJSON destination",
    )
    parser.add_argument(
        "--results-output",
        type=Path,
        required=True,
        help="small application-results JSON destination",
    )
    parser.add_argument(
        "--generated-at-utc",
        required=True,
        help=(
            "explicit ISO 8601 UTC delivery timestamp; excluded from analytical "
            "results identity and reusable for deterministic reproduction"
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="explicitly authorize coordinated replacement of all three outputs",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        inspection = load_bundle(
            cast(Path, args.bundle),
            expected_5km_sha256=cast(str, args.expected_5km_sha256),
            expected_10km_sha256=cast(str, args.expected_10km_sha256),
            expected_report_sha256=cast(str, args.expected_report_sha256),
        )
        result = write_delivery(
            inspection,
            cast(Path, args.display_output),
            cast(Path, args.results_output),
            generated_at=parse_utc_timestamp(cast(str, args.generated_at_utc)),
            overwrite=cast(bool, args.overwrite),
        )
    except ExposureDeliveryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
