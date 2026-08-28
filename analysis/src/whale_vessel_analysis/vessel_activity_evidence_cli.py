"""CLI for the read-only vessel-activity evidence harness."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from whale_vessel_analysis.config import (
    ConfigurationError,
    load_config,
    load_default_config,
)
from whale_vessel_analysis.vessel_activity_evidence import (
    VesselActivityEvidenceError,
    run_evidence,
)
from whale_vessel_analysis.whale_grid import WhaleGridError


def build_parser() -> argparse.ArgumentParser:
    """Build the isolated non-production evidence command parser."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-activity-evidence",
        description=(
            "Create a deterministic, non-production vessel-activity evidence "
            "report from one explicitly supplied cleaned AIS bundle."
        ),
    )
    parser.add_argument(
        "--cleaned-bundle",
        type=Path,
        required=True,
        help="exact output directory produced by the one-extract AIS cleaner",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="explicit JSON report path under the ignored data/interim root",
    )
    parser.add_argument(
        "--candidate-maximum-gap-seconds",
        type=float,
        action="append",
        default=[],
        help=(
            "candidate evidence value; repeat for sensitivity (no default and no "
            "accepted rule)"
        ),
    )
    parser.add_argument(
        "--candidate-implied-speed-ceiling-knots",
        type=float,
        action="append",
        default=[],
        help=(
            "candidate evidence value; repeat for sensitivity (no default and no "
            "accepted rule)"
        ),
    )
    parser.add_argument(
        "--candidate-minimum-vessel-length-m",
        type=float,
        action="append",
        default=[],
        help=(
            "candidate evidence value; repeat for sensitivity (no default and no "
            "accepted rule)"
        ),
    )
    parser.add_argument(
        "--grid-input",
        type=Path,
        help=(
            "optional exact projected_water_grid_v1 GeoParquet for diagnostic "
            "segment allocation"
        ),
    )
    parser.add_argument(
        "--expected-grid-sha256",
        help="optional expected SHA-256 checked before grid allocation",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="TOML configuration path; omit to use the packaged default",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="explicitly authorize replacement of an existing evidence report",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the evidence harness and print execution metadata separately."""
    args = build_parser().parse_args(argv)
    try:
        config_path = cast(Path | None, args.config)
        config = (
            load_default_config() if config_path is None else load_config(config_path)
        )
        result = run_evidence(
            cast(Path, args.cleaned_bundle),
            cast(Path, args.output),
            config,
            candidate_maximum_gap_seconds=cast(
                list[float], args.candidate_maximum_gap_seconds
            ),
            candidate_implied_speed_ceiling_knots=cast(
                list[float], args.candidate_implied_speed_ceiling_knots
            ),
            candidate_minimum_vessel_length_m=cast(
                list[float], args.candidate_minimum_vessel_length_m
            ),
            grid_input=cast(Path | None, args.grid_input),
            expected_grid_sha256=cast(str | None, args.expected_grid_sha256),
            overwrite=cast(bool, args.overwrite),
        )
    except (ConfigurationError, VesselActivityEvidenceError, WhaleGridError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
