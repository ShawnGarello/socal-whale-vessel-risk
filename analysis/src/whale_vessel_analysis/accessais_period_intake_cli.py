"""CLI for bounded author-supplied multi-date AccessAIS delivery intake."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import cast

from whale_vessel_analysis.accessais_period_intake import (
    AccessAISPeriodConflictError,
    AccessAISPeriodIntakeError,
    CanonicalizationResources,
    RequestedPeriod,
    load_delivery_manifest,
    orchestrate_accessais_delivery,
    prepare_accessais_delivery,
)
from whale_vessel_analysis.config import load_config, load_default_config
from whale_vessel_analysis.multiday_ais import MultiDayAISInputError

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_NOT_READY = 3
EXIT_CONFLICT = 4


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def _add_delivery_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", type=Path, required=True, help="read-only delivery")
    parser.add_argument(
        "--intake-dir",
        type=Path,
        required=True,
        help="atomic delivery bundle under ignored data/interim",
    )
    parser.add_argument("--requested-start", type=_date, required=True)
    parser.add_argument("--requested-end", type=_date, required=True)
    parser.add_argument(
        "--source-content-length",
        type=int,
        help="optional independently retained source Content-Length",
    )
    parser.add_argument(
        "--memory-limit",
        required=True,
        help="explicit DuckDB canonical-sort memory limit with unit, for example 1GB",
    )
    parser.add_argument(
        "--temp-directory",
        type=Path,
        required=True,
        help="parent for isolated DuckDB spill directories under ignored data/interim",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the three-verb bounded intake parser."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-accessais-period-intake",
        description=(
            "Prepare one author-supplied multi-date AccessAIS CSV/ZIP into "
            "canonical one-date inputs and optionally run the existing cleaner "
            "sequentially into the existing period manifest. No network action is "
            "performed."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="prepare deterministic daily slices")
    _add_delivery_arguments(prepare)

    run = commands.add_parser(
        "run", help="prepare, clean sequentially, record, and resume by UTC date"
    )
    _add_delivery_arguments(run)
    run.add_argument(
        "--cleaned-root",
        type=Path,
        required=True,
        help="one cleaner bundle directory per UTC date under data/interim",
    )
    run.add_argument(
        "--period-manifest",
        type=Path,
        required=True,
        help="existing multiday_cleaned_ais_input_v1 destination",
    )
    run.add_argument("--config", type=Path)

    status = commands.add_parser(
        "status", help="validate and report an established intake bundle"
    )
    status.add_argument("--intake-dir", type=Path, required=True)
    return parser


def _requested(args: argparse.Namespace) -> RequestedPeriod:
    return RequestedPeriod(
        cast(date, args.requested_start), cast(date, args.requested_end)
    )


def _resources(args: argparse.Namespace) -> CanonicalizationResources:
    return CanonicalizationResources(
        cast(str, args.memory_limit), cast(Path, args.temp_directory)
    )


def _emit(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _is_period_ready(payload: dict[str, object]) -> bool:
    readiness = cast(dict[str, object], payload["period_input_readiness"])
    return readiness.get("status") == "ready"


def _run(args: argparse.Namespace) -> int:
    command = cast(str, args.command)
    if command == "prepare":
        preparation_result = prepare_accessais_delivery(
            cast(Path, args.input),
            cast(Path, args.intake_dir),
            _requested(args),
            _resources(args),
            source_content_length=cast(int | None, args.source_content_length),
        )
        _emit(preparation_result.to_dict())
        return EXIT_OK
    if command == "status":
        directory = cast(Path, args.intake_dir).resolve()
        manifest = load_delivery_manifest(directory)
        _emit(
            {
                "intake_directory": str(directory),
                "contract": manifest["contract"],
                "schema_version": manifest["schema_version"],
                "processing_version": manifest["processing_version"],
                "delivery_id": manifest["delivery_id"],
                "preparation_status": manifest["preparation_status"],
                "row_accounting": manifest["row_accounting"],
                "requested_date_coverage": manifest["requested_date_coverage"],
                "independent_transfer_completeness": manifest[
                    "independent_transfer_completeness"
                ],
                "observational_completeness": manifest["observational_completeness"],
                "latest_attempt_outcome": manifest["latest_attempt_outcome"],
            }
        )
        return EXIT_OK
    if command == "run":
        config_path = cast(Path | None, args.config)
        config = (
            load_default_config() if config_path is None else load_config(config_path)
        )
        orchestration_result = orchestrate_accessais_delivery(
            cast(Path, args.input),
            cast(Path, args.intake_dir),
            cast(Path, args.cleaned_root),
            cast(Path, args.period_manifest),
            _requested(args),
            config,
            _resources(args),
            source_content_length=cast(int | None, args.source_content_length),
        )
        payload = orchestration_result.to_dict()
        _emit(payload)
        if orchestration_result.conflicting_dates:
            return EXIT_CONFLICT
        ready = _is_period_ready(
            cast(dict[str, object], orchestration_result.period_status)
        )
        return EXIT_OK if ready else EXIT_NOT_READY
    raise AssertionError(f"unhandled command: {command}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bounded AccessAIS period-intake command."""
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except AccessAISPeriodConflictError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_CONFLICT
    except (AccessAISPeriodIntakeError, MultiDayAISInputError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
