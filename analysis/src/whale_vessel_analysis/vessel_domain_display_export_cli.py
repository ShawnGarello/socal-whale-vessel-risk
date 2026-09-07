"""Command-line entry point for the vessel/domain public-display export."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from whale_vessel_analysis.vessel_domain_display_export import (
    VesselDomainDisplayExportError,
    build_exports,
    load_domain_source,
    load_vessel_quality_source,
    load_vessel_source,
    write_export_bundle,
)

DESCRIPTION: Final = (
    "Export checksum-verified production vessel activity and the accepted "
    "receiver-qualified analytical domain as deterministic public GeoJSON."
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--vessel-source", required=True, type=Path)
    parser.add_argument("--expected-vessel-sha256", required=True)
    parser.add_argument("--vessel-quality-report", required=True, type=Path)
    parser.add_argument("--expected-vessel-quality-report-sha256", required=True)
    parser.add_argument("--domain-source", required=True, type=Path)
    parser.add_argument("--expected-domain-sha256", required=True)
    parser.add_argument("--domain-report", required=True, type=Path)
    parser.add_argument("--expected-domain-report-sha256", required=True)
    parser.add_argument("--output-directory", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the export, printing only sanitized output identities."""
    args = _parser().parse_args(argv)
    try:
        vessel = load_vessel_source(
            args.vessel_source,
            expected_sha256=args.expected_vessel_sha256,
        )
        vessel_quality = load_vessel_quality_source(
            args.vessel_quality_report,
            expected_sha256=args.expected_vessel_quality_report_sha256,
            vessel=vessel,
        )
        domain = load_domain_source(
            args.domain_source,
            expected_sha256=args.expected_domain_sha256,
            report_path=args.domain_report,
            expected_report_sha256=args.expected_domain_report_sha256,
        )
        bundle = build_exports(vessel, vessel_quality, domain)
        exported_at = datetime.now(UTC)
        result = write_export_bundle(
            bundle,
            args.output_directory,
            exported_at=exported_at,
            overwrite=args.overwrite,
        )
    except VesselDomainDisplayExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
