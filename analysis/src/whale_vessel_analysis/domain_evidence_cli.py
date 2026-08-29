"""CLI for deterministic analytical-domain evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from whale_vessel_analysis.domain_evidence import (
    DomainEvidenceError,
    run_domain_evidence,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "config",
        "grid",
        "shoreline-archive",
        "station-archive",
        "vsr",
        "report",
        "masks",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = run_domain_evidence(
            config_path=args.config,
            grid_path=args.grid,
            shoreline_archive=args.shoreline_archive,
            station_archive=args.station_archive,
            vsr_path=args.vsr,
            report_path=args.report,
            masks_path=args.masks,
        )
    except (DomainEvidenceError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
