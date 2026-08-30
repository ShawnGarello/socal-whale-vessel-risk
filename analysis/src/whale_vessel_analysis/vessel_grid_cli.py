"""Focused CLI for candidate multi-day vessel-grid aggregation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.config import (
    ConfigurationError,
    load_config,
    load_default_config,
)
from whale_vessel_analysis.multiday_ais import (
    MultiDayAISInputError,
    load_period_manifest,
)
from whale_vessel_analysis.multiday_ais_relation import (
    DEFAULT_BATCH_SIZE,
    MultiDayRelationError,
    RelationResources,
    open_period_relation,
)
from whale_vessel_analysis.vessel_grid import (
    ALLOW_INCOMPLETE_PERIOD,
    EDGE_TREATMENT,
    REQUIRE_READY_PERIOD,
    SUPPORT_TREATMENT,
    EdgeTreatment,
    PeriodInputReference,
    PeriodReadinessTreatment,
    SupportTreatment,
    VesselGridError,
    VesselGridParameters,
    aggregate_vessel_grid,
    write_vessel_grid,
)
from whale_vessel_analysis.whale_grid import WhaleGridError, load_target_grid


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit candidate vessel-grid command parser."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-vessel-grid",
        description=(
            "Aggregate a verified multi-day cleaned AIS manifest into candidate "
            "per-cell vessel-kilometres on the exact projected water grid. All "
            "methodological choices remain explicit candidate parameters."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="existing multiday_cleaned_ais_input_v1 manifest",
    )
    parser.add_argument(
        "--grid-input",
        type=Path,
        required=True,
        help="exact projected_water_grid_v1 GeoParquet",
    )
    parser.add_argument(
        "--expected-grid-sha256",
        help="optional expected SHA-256 checked before aggregation",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new named bundle beneath the ignored data/derived root",
    )
    parser.add_argument(
        "--maximum-gap-seconds",
        type=float,
        required=True,
        help="explicit candidate maximum consecutive-observation gap",
    )
    parser.add_argument(
        "--implied-speed-ceiling-knots",
        type=float,
        required=True,
        help="explicit candidate projected endpoint-speed ceiling",
    )
    parser.add_argument(
        "--period-readiness-treatment",
        choices=(REQUIRE_READY_PERIOD, ALLOW_INCOMPLETE_PERIOD),
        required=True,
        help=(
            "require all 153 dates, or explicitly authorize an incomplete candidate "
            "output whose missing dates remain recorded"
        ),
    )
    parser.add_argument(
        "--edge-treatment",
        choices=(EDGE_TREATMENT,),
        required=True,
        help=(
            "explicitly retain upstream map-extent censoring; no entry/exit path "
            "is extrapolated"
        ),
    )
    parser.add_argument(
        "--support-treatment",
        choices=(SUPPORT_TREATMENT,),
        required=True,
        help=(
            "allocate exact water geometry and exclude/report unsupported or "
            "ambiguous distance"
        ),
    )
    parser.add_argument(
        "--memory-limit",
        required=True,
        help="explicit DuckDB memory limit with a unit, for example 2GB",
    )
    parser.add_argument(
        "--temp-directory",
        type=Path,
        required=True,
        help="explicit DuckDB spill directory under ignored data/interim",
    )
    parser.add_argument("--threads", type=int, help="optional DuckDB thread count")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="bounded Arrow batch size; operational only, not analytical",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="TOML configuration path; omit to use the packaged default",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="explicitly replace only a complete compatible output bundle",
    )
    return parser


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VesselGridError(f"period manifest {label} must be an object")
    return cast(Mapping[str, object], value)


def main(argv: Sequence[str] | None = None) -> int:
    """Run one bounded candidate aggregation and print its published identity."""
    args = build_parser().parse_args(argv)
    started_at = datetime.now(UTC)
    try:
        config_path = cast(Path | None, args.config)
        config = (
            load_default_config() if config_path is None else load_config(config_path)
        )
        manifest_path = cast(Path, args.manifest).resolve()
        if not manifest_path.is_file():
            raise VesselGridError(f"period manifest does not exist: {manifest_path}")
        manifest = load_period_manifest(manifest_path)
        period_input_id = manifest.get("period_input_id")
        if not isinstance(period_input_id, str):
            raise VesselGridError("period manifest has no valid period_input_id")
        period_input = PeriodInputReference(
            manifest_path=manifest_path,
            manifest_sha256=sha256_file(manifest_path),
            period_input_id=period_input_id,
            period_input_readiness=_mapping(
                manifest.get("period_input_readiness"), "readiness"
            ),
            observational_completeness=_mapping(
                manifest.get("observational_completeness"),
                "observational completeness",
            ),
        )
        parameters = VesselGridParameters(
            maximum_gap_seconds=cast(float, args.maximum_gap_seconds),
            implied_speed_ceiling_knots=cast(float, args.implied_speed_ceiling_knots),
            period_readiness_treatment=cast(
                PeriodReadinessTreatment, args.period_readiness_treatment
            ),
            edge_treatment=cast(EdgeTreatment, args.edge_treatment),
            support_treatment=cast(SupportTreatment, args.support_treatment),
        )
        resources = RelationResources(
            memory_limit=cast(str, args.memory_limit),
            temporary_directory=cast(Path, args.temp_directory),
            threads=cast(int | None, args.threads),
        )
        target_grid = load_target_grid(
            cast(Path, args.grid_input).resolve(),
            config,
            expected_sha256=cast(str | None, args.expected_grid_sha256),
        )
        with open_period_relation(
            manifest,
            resources,
            require_ready=parameters.require_ready_period,
        ) as relation:
            dataset = aggregate_vessel_grid(
                relation,
                target_grid,
                period_input,
                parameters,
                config,
                batch_size=cast(int, args.batch_size),
            )
            result = write_vessel_grid(
                dataset,
                cast(Path, args.output_dir),
                started_at=started_at,
                relation=relation,
                overwrite=cast(bool, args.overwrite),
            )
    except (
        ConfigurationError,
        MultiDayAISInputError,
        MultiDayRelationError,
        VesselGridError,
        WhaleGridError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
