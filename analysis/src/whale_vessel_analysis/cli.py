"""Command-line boundary for the offline analysis package."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from whale_vessel_analysis.ais import AISValidationError, validate_ais_csv
from whale_vessel_analysis.ais_processing import (
    AISProcessingError,
    AISProcessingResources,
    process_ais_csv,
)
from whale_vessel_analysis.config import (
    ConfigurationError,
    ProcessingConfig,
    load_config,
    load_default_config,
)
from whale_vessel_analysis.vsr import VSRValidationError, validate_vsr_input
from whale_vessel_analysis.whale import (
    WHALE_LAYER_NAME,
    WhaleValidationError,
    validate_whale_input,
)


def _add_config_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        help="TOML configuration path; omit to use the packaged default",
    )


def _load_selected_config(path: Path | None) -> ProcessingConfig:
    return load_default_config() if path is None else load_config(path)


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _emit_compact(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def build_parser() -> argparse.ArgumentParser:
    """Build the package command-line parser."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-analysis",
        description=(
            "Validate inputs and configuration for the Southern California "
            "whale-vessel overlap processing workflow."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    config_parser = commands.add_parser(
        "validate-config", help="validate and fingerprint processing configuration"
    )
    _add_config_argument(config_parser)

    ais_parser = commands.add_parser(
        "validate-ais", help="validate one NOAA Marine Cadastre AIS CSV"
    )
    ais_parser.add_argument("path", type=Path, help="AIS CSV path")
    _add_config_argument(ais_parser)

    process_ais_parser = commands.add_parser(
        "process-ais", help="clean one supplied NOAA Marine Cadastre AIS CSV extract"
    )
    process_ais_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="one single-UTC-date AIS flat-CSV extract path",
    )
    process_ais_parser.add_argument(
        "--memory-limit",
        required=True,
        help="explicit DuckDB memory limit with unit, for example 512MB",
    )
    process_ais_parser.add_argument(
        "--temp-directory",
        type=Path,
        required=True,
        help="parent for one isolated DuckDB spill directory per run",
    )
    process_ais_parser.add_argument(
        "--threads",
        type=int,
        default=1,
        help="explicit DuckDB thread count; defaults to 1",
    )
    process_ais_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new output bundle directory",
    )
    process_ais_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace only an existing complete AIS processing bundle",
    )
    _add_config_argument(process_ais_parser)

    whale_parser = commands.add_parser(
        "validate-whale", help="validate the selected NOAA/SWFSC whale layer"
    )
    whale_parser.add_argument("path", type=Path, help="File Geodatabase path")
    whale_parser.add_argument(
        "--layer",
        default=WHALE_LAYER_NAME,
        help=f"layer name; foundation contract requires {WHALE_LAYER_NAME}",
    )

    vsr_parser = commands.add_parser(
        "validate-vsr", help="validate the published 2026 California VSR GeoJSON"
    )
    vsr_parser.add_argument("path", type=Path, help="VSR GeoJSON path")
    return parser


def _run_command(args: argparse.Namespace) -> int:
    command = cast(str, args.command)
    if command == "validate-config":
        config = _load_selected_config(cast(Path | None, args.config))
        _emit({"configuration": config.to_dict(), "sha256": config.digest()})
        return 0
    if command == "validate-ais":
        config = _load_selected_config(cast(Path | None, args.config))
        validation_result = validate_ais_csv(
            cast(Path, args.path), config.spatial.map_extent
        )
        _emit(validation_result.to_dict())
        return 0 if validation_result.passed else 2
    if command == "process-ais":
        config = _load_selected_config(cast(Path | None, args.config))
        processing_result = process_ais_csv(
            cast(Path, args.input),
            cast(Path, args.output_dir),
            config,
            overwrite=cast(bool, args.overwrite),
            resources=AISProcessingResources(
                cast(str, args.memory_limit),
                cast(Path, args.temp_directory),
                cast(int, args.threads),
            ),
        )
        _emit_compact(processing_result.to_dict())
        return 0
    if command == "validate-whale":
        whale_result = validate_whale_input(
            cast(Path, args.path), layer=cast(str, args.layer)
        )
        _emit(whale_result.to_dict())
        return 0 if whale_result.passed else 2
    if command == "validate-vsr":
        vsr_result = validate_vsr_input(cast(Path, args.path))
        _emit(vsr_result.to_dict())
        return 0 if vsr_result.passed else 2
    raise AssertionError(f"unhandled command: {command}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    args = build_parser().parse_args(argv)
    try:
        return _run_command(args)
    except (
        AISValidationError,
        AISProcessingError,
        ConfigurationError,
        VSRValidationError,
        WhaleValidationError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
