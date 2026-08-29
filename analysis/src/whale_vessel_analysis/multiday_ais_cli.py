"""Focused CLI for the multi-day cleaned AIS input foundation.

Every input and output location is supplied explicitly. The command performs no
discovery outside the supplied paths, writes only to an explicit ignored
`data/interim/` destination, publishes atomically, and refuses raw destinations
and arbitrary overwrites.

Exit codes:

* ``0`` — the requested operation succeeded.
* ``2`` — an input, destination, or contract check refused the request.
* ``3`` — the operation succeeded but the analytical period is not ready.
* ``4`` — a conflicting date entry was recorded and preserved for review.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from whale_vessel_analysis.multiday_ais import (
    MULTIDAY_INPUT_CONTRACT,
    MultiDayAISInputError,
    load_period_manifest,
    period_status,
    record_cleaned_days,
)
from whale_vessel_analysis.multiday_ais_relation import (
    DEFAULT_BATCH_SIZE,
    RelationResources,
    open_period_relation,
)

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_NOT_READY = 3
EXIT_CONFLICT = 4


def build_parser() -> argparse.ArgumentParser:
    """Build the isolated multi-day cleaned-input command parser."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-multiday-ais",
        description=(
            "Assemble independently verified one-date cleaner bundles into one "
            f"explicit {MULTIDAY_INPUT_CONTRACT} period-input manifest and scan "
            "it through a bounded DuckDB relation."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    record = commands.add_parser(
        "record",
        help="validate supplied cleaner bundles and publish the period manifest",
    )
    record.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="explicit period-manifest JSON path under the ignored data/interim root",
    )
    record.add_argument(
        "--cleaned-bundle",
        type=Path,
        action="append",
        required=True,
        default=[],
        help="exact cleaner output directory; repeat for more UTC dates",
    )
    record.add_argument(
        "--retrieval-manifest",
        type=Path,
        help=(
            "optional read-only noaa_ais_retrieval_manifest_v1 path whose per-date "
            "retrieval and byte/archive states are recorded separately"
        ),
    )

    status = commands.add_parser(
        "status", help="report one existing period manifest without writing"
    )
    status.add_argument("--manifest", type=Path, required=True, help="manifest path")

    scan = commands.add_parser(
        "scan",
        help="open the bounded DuckDB relation over the manifest's verified dates",
    )
    scan.add_argument("--manifest", type=Path, required=True, help="manifest path")
    scan.add_argument(
        "--memory-limit",
        required=True,
        help="explicit DuckDB memory limit with a unit, for example 2GB",
    )
    scan.add_argument(
        "--temp-directory",
        type=Path,
        required=True,
        help="explicit DuckDB temporary/spill directory under ignored data/interim",
    )
    scan.add_argument(
        "--threads", type=int, help="optional explicit DuckDB thread count"
    )
    scan.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="streamed Arrow record-batch size for the ordered scan",
    )
    scan.add_argument(
        "--require-ready",
        action="store_true",
        help="exit non-zero instead of scanning an incomplete analytical period",
    )
    return parser


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _record(args: argparse.Namespace) -> int:
    update = record_cleaned_days(
        cast(Path, args.manifest),
        cast(list[Path], args.cleaned_bundle),
        retrieval_manifest_path=cast(Path | None, args.retrieval_manifest),
    )
    _emit(update.to_dict())
    if any(outcome.entry_status == "conflict" for outcome in update.outcomes):
        return EXIT_CONFLICT
    return EXIT_OK


def _status(args: argparse.Namespace) -> int:
    manifest_path = cast(Path, args.manifest)
    if not manifest_path.is_file():
        raise MultiDayAISInputError(f"period manifest does not exist: {manifest_path}")
    manifest = load_period_manifest(manifest_path)
    _emit(period_status(manifest))
    return EXIT_OK if _is_ready(manifest) else EXIT_NOT_READY


def _is_ready(manifest: dict[str, object]) -> bool:
    readiness = cast(dict[str, object], manifest["period_input_readiness"])
    return readiness.get("status") == "ready"


def _scan(args: argparse.Namespace) -> int:
    manifest_path = cast(Path, args.manifest)
    if not manifest_path.is_file():
        raise MultiDayAISInputError(f"period manifest does not exist: {manifest_path}")
    manifest = load_period_manifest(manifest_path)
    resources = RelationResources(
        memory_limit=cast(str, args.memory_limit),
        temporary_directory=cast(Path, args.temp_directory),
        threads=cast(int | None, args.threads),
    )
    batch_size = cast(int, args.batch_size)
    with open_period_relation(
        manifest, resources, require_ready=cast(bool, args.require_ready)
    ) as relation:
        batches = 0
        streamed_rows = 0
        for batch in relation.ordered_batches(batch_size):
            batches += 1
            streamed_rows += batch.num_rows
        payload: dict[str, object] = {
            "manifest": {
                "path": str(manifest_path.resolve()),
                "period_input_id": manifest["period_input_id"],
            },
            "relation": relation.to_dict(),
            "observations": relation.count_observations(),
            "streamed": {"record_batches": batches, "rows": streamed_rows},
            "partition_row_counts": relation.partition_row_counts(),
            "continuity": relation.continuity_summary(),
            "period_input_readiness": manifest["period_input_readiness"],
            "observational_completeness": manifest["observational_completeness"],
        }
    _emit(payload)
    return EXIT_OK if _is_ready(manifest) else EXIT_NOT_READY


def main(argv: Sequence[str] | None = None) -> int:
    """Run the multi-day cleaned-input command."""
    args = build_parser().parse_args(argv)
    command = cast(str, args.command)
    try:
        if command == "record":
            return _record(args)
        if command == "status":
            return _status(args)
        if command == "scan":
            return _scan(args)
    except MultiDayAISInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    raise AssertionError(f"unhandled command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
