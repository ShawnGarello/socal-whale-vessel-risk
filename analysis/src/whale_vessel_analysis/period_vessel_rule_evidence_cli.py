"""CLI for bounded period-wide vessel-rule evidence."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.multiday_ais import (
    MultiDayAISInputError,
    load_period_manifest,
)
from whale_vessel_analysis.multiday_ais_relation import (
    DEFAULT_BATCH_SIZE,
    MultiDayRelationError,
    RelationResources,
    open_period_relation,
    period_partitions,
)
from whale_vessel_analysis.period_vessel_rule_evidence import (
    VESSEL_LENGTH_TREATMENT,
    PeriodEvidenceInputReference,
    PeriodVesselRuleEvidenceError,
    PeriodVesselRuleParameters,
    VesselLengthTreatment,
    build_period_vessel_rule_evidence,
    validate_evidence_output_target,
    write_period_vessel_rule_evidence,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit period evidence parser without analytical defaults."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-period-vessel-rule-evidence",
        description=(
            "Summarize the complete ADR 0018 candidate rule matrix from one "
            "bounded, whole-period structural-segment stream. The command does "
            "not select a rule or produce a vessel grid."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="explicit compatible multiday_cleaned_ais_input_v1 manifest",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new named evidence bundle beneath ignored data/interim",
    )
    parser.add_argument(
        "--maximum-gap-seconds",
        type=float,
        action="append",
        required=True,
        help=("repeat explicitly for the required 300 and 1800 second candidates"),
    )
    parser.add_argument(
        "--implied-speed-ceiling-knots",
        type=float,
        action="append",
        required=True,
        help="repeat explicitly for the required 30 and 50 knot candidates",
    )
    parser.add_argument(
        "--vessel-length-treatment",
        choices=(VESSEL_LENGTH_TREATMENT,),
        required=True,
        help=(
            "explicitly retain the upstream type-only population without a "
            "vessel-length filter"
        ),
    )
    parser.add_argument(
        "--allow-incomplete-non-production",
        action="store_true",
        help=(
            "deliberate test-only override; production evidence otherwise requires "
            "all 153 accepted dates"
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
        help="explicit DuckDB spill parent beneath ignored data/interim",
    )
    parser.add_argument("--threads", type=int, help="optional DuckDB thread count")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="bounded Arrow batch size; execution provenance, not identity",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="explicitly replace only a complete compatible evidence bundle",
    )
    return parser


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PeriodVesselRuleEvidenceError(
            f"period manifest {label} must be an object"
        )
    return cast(Mapping[str, object], value)


def main(argv: Sequence[str] | None = None) -> int:
    """Run one bounded candidate-method evidence aggregation."""
    args = build_parser().parse_args(argv)
    started_at = datetime.now(UTC)
    try:
        manifest_path = cast(Path, args.manifest).resolve()
        if not manifest_path.is_file():
            raise PeriodVesselRuleEvidenceError(
                f"period manifest does not exist: {manifest_path}"
            )
        manifest = load_period_manifest(manifest_path)
        period_input_id = manifest.get("period_input_id")
        if not isinstance(period_input_id, str):
            raise PeriodVesselRuleEvidenceError(
                "period manifest has no valid period_input_id"
            )
        period_input = PeriodEvidenceInputReference(
            manifest_path=manifest_path,
            manifest_sha256=sha256_file(manifest_path),
            period_input_id=period_input_id,
            period_input_readiness=_mapping(
                manifest.get("period_input_readiness"), "readiness"
            ),
            independent_transfer_completeness=_mapping(
                manifest.get("independent_transfer_completeness"),
                "independent transfer completeness",
            ),
            observational_completeness=_mapping(
                manifest.get("observational_completeness"),
                "observational completeness",
            ),
        )
        parameters = PeriodVesselRuleParameters(
            maximum_gap_seconds=tuple(cast(list[float], args.maximum_gap_seconds)),
            implied_speed_ceiling_knots=tuple(
                cast(list[float], args.implied_speed_ceiling_knots)
            ),
            vessel_length_treatment=cast(
                VesselLengthTreatment, args.vessel_length_treatment
            ),
            allow_incomplete_non_production=cast(
                bool, args.allow_incomplete_non_production
            ),
        )
        resources = RelationResources(
            memory_limit=cast(str, args.memory_limit),
            temporary_directory=cast(Path, args.temp_directory),
            threads=cast(int | None, args.threads),
        )
        partitions = period_partitions(manifest)
        output_directory = cast(Path, args.output_dir)
        validate_evidence_output_target(
            output_directory,
            (
                manifest_path,
                *(partition.cleaned_path for partition in partitions),
                resources.temporary_directory,
            ),
            overwrite=cast(bool, args.overwrite),
        )
        with open_period_relation(
            manifest,
            resources,
            require_ready=parameters.require_ready_period,
        ) as relation:
            dataset = build_period_vessel_rule_evidence(
                relation,
                period_input,
                parameters,
                batch_size=cast(int, args.batch_size),
            )
            result = write_period_vessel_rule_evidence(
                dataset,
                output_directory,
                relation=relation,
                started_at=started_at,
                overwrite=cast(bool, args.overwrite),
            )
    except (
        MultiDayAISInputError,
        MultiDayRelationError,
        PeriodVesselRuleEvidenceError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
