"""CLI boundary for modeled blue-whale transfer to the analysis water grid."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from whale_vessel_analysis.config import (
    ConfigurationError,
    load_config,
    load_default_config,
)
from whale_vessel_analysis.whale import WHALE_LAYER_NAME, WhaleValidationError
from whale_vessel_analysis.whale_grid import (
    WhaleGridError,
    load_target_grid,
    load_whale_source,
    transfer_whale_density,
    write_whale_grid,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit two-input whale-grid transfer parser."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-whale-grid",
        description=(
            "Transfer the selected NOAA/SWFSC modeled blue-whale density surface "
            "to an existing EPSG:3310 projected water grid by abundance-conserving "
            "area weighting."
        ),
    )
    parser.add_argument(
        "--whale-input",
        type=Path,
        required=True,
        help="selected NOAA/SWFSC File Geodatabase path",
    )
    parser.add_argument(
        "--whale-layer",
        default=WHALE_LAYER_NAME,
        help=f"source layer name; contract requires {WHALE_LAYER_NAME}",
    )
    parser.add_argument(
        "--grid-input",
        type=Path,
        required=True,
        help="existing projected_water_grid_v1 GeoParquet path",
    )
    parser.add_argument(
        "--expected-grid-sha256",
        help="optional expected SHA-256 that must match the target grid before work",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="output whale-grid GeoParquet path",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="TOML configuration path; omit to use the packaged default",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="explicitly authorize replacement of output and lineage files",
    )
    return parser


def _utc_now() -> datetime:
    return datetime.now(UTC)


def main(argv: Sequence[str] | None = None) -> int:
    """Run one validated whale-grid transfer and emit a JSON summary."""
    args = build_parser().parse_args(argv)
    started_at = _utc_now()
    try:
        config_path = cast(Path | None, args.config)
        config = (
            load_default_config() if config_path is None else load_config(config_path)
        )
        expected_grid_sha256 = cast(str | None, args.expected_grid_sha256)
        target_grid = load_target_grid(
            cast(Path, args.grid_input),
            config,
            expected_sha256=expected_grid_sha256,
        )
        source = load_whale_source(
            cast(Path, args.whale_input), layer=cast(str, args.whale_layer)
        )
        dataset = transfer_whale_density(source, target_grid, config)
        result = write_whale_grid(
            dataset,
            source,
            target_grid,
            cast(Path, args.output),
            started_at=started_at,
            expected_grid_sha256=expected_grid_sha256,
            overwrite=cast(bool, args.overwrite),
        )
    except (ConfigurationError, WhaleValidationError, WhaleGridError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
