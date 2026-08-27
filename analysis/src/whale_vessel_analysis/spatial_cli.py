"""Separate CLI boundary for deterministic projected water-grid generation."""

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
from whale_vessel_analysis.spatial_grid import (
    SpatialGridError,
    build_water_grid,
    load_water_mask,
    write_water_grid,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the spatial-grid command parser without changing the shared CLI."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-grid",
        description=(
            "Build the deterministic EPSG:3310 analysis grid and intersect it "
            "with an explicitly supplied polygon water mask."
        ),
    )
    parser.add_argument("--input", type=Path, required=True, help="water-mask dataset")
    parser.add_argument(
        "--layer", help="input layer name where the format requires one"
    )
    parser.add_argument(
        "--source-crs",
        required=True,
        help="declared input CRS, verified against the dataset's embedded CRS",
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="output GeoParquet path"
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


def main(argv: Sequence[str] | None = None) -> int:
    """Generate one projected water-grid dataset and print its run summary."""
    args = build_parser().parse_args(argv)
    try:
        config_path = cast(Path | None, args.config)
        config = (
            load_default_config() if config_path is None else load_config(config_path)
        )
        mask = load_water_mask(
            cast(Path, args.input),
            layer=cast(str | None, args.layer),
            declared_source_crs=cast(str, args.source_crs),
        )
        dataset = build_water_grid(mask, config)
        result = write_water_grid(
            dataset,
            mask,
            cast(Path, args.output),
            overwrite=cast(bool, args.overwrite),
        )
    except (ConfigurationError, SpatialGridError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
