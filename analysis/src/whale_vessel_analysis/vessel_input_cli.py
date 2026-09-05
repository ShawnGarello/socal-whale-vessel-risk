"""Build the selected production vessel input and separate speed descriptors."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.multiday_ais import load_period_manifest
from whale_vessel_analysis.multiday_ais_relation import (
    RelationResources,
    open_period_relation,
)
from whale_vessel_analysis.vessel_grid import (
    PeriodInputReference,
    _validate_output_directory,
    validate_input_output_separation,
)
from whale_vessel_analysis.vessel_grid_cli import _mapping
from whale_vessel_analysis.vessel_input import build_vessel_input, write_vessel_input
from whale_vessel_analysis.whale_grid import load_target_grid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "grid-input", "output-dir", "temp-directory"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--expected-grid-sha256", required=True)
    parser.add_argument("--memory-limit", required=True)
    parser.add_argument("--threads", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started_at = datetime.now(UTC)
    try:
        # Fail on unsafe destinations before scanning the period.
        target = _validate_output_directory(args.output_dir, False)
        manifest_path = args.manifest.resolve()
        validate_input_output_separation(target, [manifest_path, args.grid_input])
        spill = args.temp_directory.resolve()
        if (
            spill == target
            or spill.is_relative_to(target)
            or target.is_relative_to(spill)
        ):
            raise ValueError("production output and spill roots must be disjoint")
        manifest = load_period_manifest(manifest_path)
        period_id = manifest.get("period_input_id")
        if not isinstance(period_id, str):
            raise ValueError("period input identity is missing")
        reference = PeriodInputReference(
            manifest_path,
            sha256_file(manifest_path),
            period_id,
            _mapping(manifest.get("period_input_readiness"), "readiness"),
            _mapping(
                manifest.get("observational_completeness"), "observational completeness"
            ),
        )
        config = load_default_config()
        grid = load_target_grid(
            args.grid_input.resolve(), config, expected_sha256=args.expected_grid_sha256
        )
        resources = RelationResources(args.memory_limit, spill, args.threads)
        with open_period_relation(manifest, resources, require_ready=True) as relation:
            dataset = build_vessel_input(
                relation, grid, reference, config, batch_size=args.batch_size
            )
            result = write_vessel_input(
                dataset, target, relation=relation, started_at=started_at
            )
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
