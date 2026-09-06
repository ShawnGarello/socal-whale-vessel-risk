"""CLI boundary for the deterministic public-display whale-layer export."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from whale_vessel_analysis.whale_display_export import (
    WhaleDisplayExportError,
    build_export,
    load_source,
    write_display_export,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit single-input display-export parser."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-whale-display-export",
        description=(
            "Export a validated blue_whale_grid_transfer_v1 GeoParquet artifact "
            "as deterministic WGS 84 GeoJSON for public display, together with a "
            "sanitized export manifest. Analytical values are preserved exactly; "
            "no geometry is simplified and no coordinate is rounded."
        ),
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="existing blue_whale_grid_transfer_v1 GeoParquet path",
    )
    parser.add_argument(
        "--expected-source-sha256",
        required=True,
        help=(
            "SHA-256 the source artifact must match; required so a public "
            "artifact can never be produced from an unidentified input"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="output GeoJSON path; the manifest is written beside it",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="explicitly authorize replacement of the output and its manifest",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one validated display export and emit a JSON summary."""
    args = build_parser().parse_args(argv)
    try:
        source = load_source(
            cast(Path, args.source),
            expected_sha256=cast(str, args.expected_source_sha256),
        )
        export = build_export(source)
        result = write_display_export(
            export,
            cast(Path, args.output),
            exported_at=datetime.now(UTC),
            overwrite=cast(bool, args.overwrite),
        )
    except WhaleDisplayExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
