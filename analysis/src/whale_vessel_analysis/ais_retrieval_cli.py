"""Separate CLI boundary for local NOAA AIS delivery verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import cast

from whale_vessel_analysis.ais import validate_ais_csv
from whale_vessel_analysis.ais_processing import process_ais_csv
from whale_vessel_analysis.ais_retrieval import (
    AISRetrievalError,
    RequestBounds,
    RetrievalRequest,
    RetrievalRoute,
    SourceHttpMetadata,
    attach_cleaning_reference,
    inspect_ais_artifact,
    materialize_verified_csv_bundle,
    parse_utc_timestamp,
    record_failed_attempt,
    record_verified_attempt,
)
from whale_vessel_analysis.config import load_config, load_default_config


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    """Build the focused retrieval-verification parser."""
    parser = argparse.ArgumentParser(
        prog="whale-vessel-ais-retrieval",
        description=(
            "Inspect one author-supplied NOAA AIS artifact, record an immutable "
            "retrieval-manifest entry, and optionally exercise the existing cleaner."
        ),
    )
    parser.add_argument("--input", type=Path, required=True, help="read-only artifact")
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="explicit ignored retrieval-manifest JSON path",
    )
    parser.add_argument(
        "--expected-utc-date", type=_date, required=True, help="expected YYYY-MM-DD"
    )
    parser.add_argument("--route", choices=("accessais", "bulk_daily"), required=True)
    parser.add_argument(
        "--request-id", required=True, help="stable token-free local request identifier"
    )
    parser.add_argument(
        "--source-reference",
        required=True,
        help=(
            "token-free description or public bulk URL; sensitive URL parts are "
            "redacted"
        ),
    )
    parser.add_argument(
        "--requested-from", type=_date, required=True, help="inclusive YYYY-MM-DD"
    )
    parser.add_argument(
        "--requested-through", type=_date, required=True, help="inclusive YYYY-MM-DD"
    )
    parser.add_argument("--lon-min", type=float, required=True)
    parser.add_argument("--lat-min", type=float, required=True)
    parser.add_argument("--lon-max", type=float, required=True)
    parser.add_argument("--lat-max", type=float, required=True)
    parser.add_argument(
        "--source-filename", required=True, help="NOAA-supplied filename"
    )
    parser.add_argument(
        "--retrieved-at-utc",
        required=True,
        help="actual author-supplied retrieval timestamp with explicit UTC offset",
    )
    parser.add_argument("--http-content-length", type=int)
    parser.add_argument("--http-etag")
    parser.add_argument("--http-last-modified")
    parser.add_argument(
        "--csv-bundle-dir",
        type=Path,
        help="explicit ignored data/interim directory for a verified ZIP member",
    )
    parser.add_argument(
        "--clean-output-dir",
        type=Path,
        help="optional new data/interim cleaner output bundle",
    )
    parser.add_argument("--config", type=Path)
    return parser


def _request(args: argparse.Namespace) -> RetrievalRequest:
    return RetrievalRequest(
        expected_utc_date=cast(date, args.expected_utc_date),
        route=cast(RetrievalRoute, args.route),
        request_id=cast(str, args.request_id),
        source_reference=cast(str, args.source_reference),
        request_parameters=RequestBounds(
            from_date=cast(date, args.requested_from),
            through_date=cast(date, args.requested_through),
            lon_min=cast(float, args.lon_min),
            lat_min=cast(float, args.lat_min),
            lon_max=cast(float, args.lon_max),
            lat_max=cast(float, args.lat_max),
        ),
        source_filename=cast(str, args.source_filename),
        retrieved_at_utc=parse_utc_timestamp(cast(str, args.retrieved_at_utc)),
        source_http_metadata=SourceHttpMetadata(
            content_length=cast(int | None, args.http_content_length),
            etag=cast(str | None, args.http_etag),
            last_modified=cast(str | None, args.http_last_modified),
        ),
    )


def _run(args: argparse.Namespace) -> tuple[int, dict[str, object]]:
    request = _request(args)
    input_path = cast(Path, args.input).resolve()
    manifest_path = cast(Path, args.manifest).resolve()
    try:
        inspection = inspect_ais_artifact(
            input_path,
            request.expected_utc_date,
            source_content_length=request.source_http_metadata.content_length,
        )
    except AISRetrievalError as exc:
        record_failed_attempt(manifest_path, request, str(exc))
        raise
    update = record_verified_attempt(manifest_path, request, inspection)
    if update.outcome == "conflict":
        raise AISRetrievalError(
            "retrieval conflict recorded: retry bytes differ from current evidence"
        )
    csv_path = input_path
    bundle_payload: dict[str, object] | None = None
    bundle_directory = cast(Path | None, args.csv_bundle_dir)
    if bundle_directory is not None:
        bundle = materialize_verified_csv_bundle(
            input_path,
            inspection,
            request.expected_utc_date,
            bundle_directory,
        )
        csv_path = bundle.csv_path
        bundle_payload = {
            "directory": str(bundle.directory),
            "csv_path": str(bundle.csv_path),
            "csv_byte_size": bundle.csv_byte_size,
            "csv_sha256": bundle.csv_sha256,
            "reused": bundle.reused,
        }
    elif inspection.container == "zip" and args.clean_output_dir is not None:
        raise AISRetrievalError(
            "--clean-output-dir for a ZIP also requires an explicit --csv-bundle-dir"
        )
    cleaning_payload: dict[str, object] | None = None
    clean_output = cast(Path | None, args.clean_output_dir)
    if clean_output is not None:
        config_path = cast(Path | None, args.config)
        config = (
            load_default_config() if config_path is None else load_config(config_path)
        )
        source_validation = validate_ais_csv(csv_path, config.spatial.map_extent)
        processing = process_ais_csv(csv_path, clean_output, config)
        quality = json.loads(processing.quality_report.read_text(encoding="utf-8"))
        completeness = quality["temporal_coverage"]["completeness"]["status"]
        if completeness != "unverified":
            raise AISRetrievalError(
                "cleaner changed observational completeness away from unverified"
            )
        cleaning_payload = {
            "contract": quality["contract"],
            "output_directory": str(processing.output_directory),
            "cleaned_parquet_sha256": processing.output_sha256,
            "quality_report_sha256": _sha256(processing.quality_report),
            "run_metadata_sha256": _sha256(processing.run_metadata),
            "input_rows": processing.input_rows,
            "output_rows": processing.output_rows,
            "source_validator": source_validation.to_dict(),
            "cleaner_reported_completeness": "unverified",
        }
        attach_cleaning_reference(
            manifest_path, request.expected_utc_date, cleaning_payload
        )
    payload: dict[str, object] = {
        "status": "success",
        "manifest": str(manifest_path),
        "manifest_outcome": update.outcome,
        "entry_status": update.entry_status,
        "artifact": {
            "byte_size": inspection.byte_size,
            "sha256": inspection.sha256,
            "container": inspection.container,
            "archive_members": list(inspection.archive_members),
            "selected_csv_member": inspection.selected_csv_member,
            "crc_valid": inspection.crc_valid,
        },
        "date_verification": inspection.date_inspection.to_dict(),
        "csv_bundle": bundle_payload,
        "cleaning": cleaning_payload,
        "observational_completeness": "unverified",
    }
    return 0, payload


def main(argv: Sequence[str] | None = None) -> int:
    """Run the retrieval-verification command."""
    args = build_parser().parse_args(argv)
    try:
        exit_code, payload = _run(args)
    except (AISRetrievalError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
