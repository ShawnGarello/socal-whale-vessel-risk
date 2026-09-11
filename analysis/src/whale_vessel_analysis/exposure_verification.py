"""Record a later, read-only check of the existing M6 delivery boundary.

Each invocation reserves a fresh ignored directory and writes request.json before
validation, then result.json on completion. Neither file is replaced. A request
without a result is incomplete evidence, never a successful verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.exposure_delivery import (
    SOURCE_FILES,
    build_delivery_export,
    canonical_json_bytes,
    load_bundle,
    parse_utc_timestamp,
)
from whale_vessel_analysis.exposure_run import validate_destination

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
CONTRACT = "exposure_delivery_verification_v1"
VERIFIER_VERSION = "1.0.0"
ARTIFACT_LABELS = ("5km", "10km", "report", "display", "manifest", "results")
Pin = tuple[Path, str]


class VerificationError(ValueError):
    """A requested artifact or verification destination is incompatible."""


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_new(path: Path, document: Mapping[str, object]) -> None:
    with path.open("xb") as stream:
        stream.write(canonical_json_bytes(document))
        stream.flush()
        os.fsync(stream.fileno())


def verifier_identity() -> dict[str, object]:
    """Identify actual source bytes as well as the nominal version and Git HEAD."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {
        "name": "whale_vessel_analysis.exposure_verification",
        "version": VERIFIER_VERSION,
        "git_head": commit,
        "package_source_sha256": {
            path.relative_to(PACKAGE).as_posix(): sha256_file(path)
            for path in sorted(PACKAGE.rglob("*"))
            if path.suffix in {".py", ".toml"} and path.is_file()
        },
        "uv_lock_sha256": sha256_file(PACKAGE.parents[1] / "uv.lock"),
        "python": platform.python_version(),
        "software": {
            name: version(name)
            for name in ("pyarrow", "shapely", "pyproj", "numpy", "pyogrio")
        },
    }


def verify_delivery(
    *,
    bundle: Path,
    artifacts: Mapping[str, Pin],
    evidence: Sequence[Pin],
    output_dir: Path,
) -> dict[str, Any]:
    """Reuse analytical reconciliation and reproduce the three delivery bytes.

    Evidence references are fingerprinted, not interpreted as visual/scientific
    approval. No raw processing, generation-lineage edit, or network access occurs.
    """
    if set(artifacts) != set(ARTIFACT_LABELS):
        raise VerificationError("exactly the six delivery-boundary pins are required")
    for label, filename in SOURCE_FILES.items():
        if artifacts[label][0].resolve() != (bundle / filename).resolve():
            raise VerificationError("analytical pins must identify the supplied bundle")
    pins = dict(artifacts)
    pins.update({f"evidence_{i}": pin for i, pin in enumerate(evidence, start=1)})
    for _path, digest in pins.values():
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise VerificationError("pins require lowercase SHA-256 strings")

    # Do not resolve the allowed root through a junction into another checkout.
    interim = ROOT.resolve() / "data" / "interim"
    target = output_dir.resolve()
    if target == interim or not target.is_relative_to(interim):
        raise VerificationError("records must be beneath this checkout's data/interim")
    if any(part.lower() in {"raw", ".git"} for part in target.parts):
        raise VerificationError("protected record destination")
    target = validate_destination(target, [bundle, *(p for p, _ in pins.values())])
    target.mkdir(parents=True, exist_ok=False)
    request: dict[str, object] = {
        "contract": CONTRACT,
        "schema_version": 1,
        "started_at_utc": _now(),
        "verifier": verifier_identity(),
        "artifacts": {
            name: {"path": path.resolve().as_posix(), "expected_sha256": digest}
            for name, (path, digest) in pins.items()
        },
        "evidence_scope": "references only; content and approvals are not assessed",
        "visual_inspection": "not_performed",
        "scientific_validation": "not_performed",
        "raw_to_public_rerun": "not_performed",
    }
    _write_new(target / "request.json", request)
    checks: list[dict[str, str]] = []
    observed: dict[str, dict[str, object]] = {}
    reproduced: dict[str, str] = {}
    active = "artifact_and_evidence_identity"
    outcome = "failed"
    try:
        for name, (path, expected) in pins.items():
            actual = sha256_file(path)
            observed[name] = {"sha256": actual, "bytes": path.stat().st_size}
            if actual != expected:
                raise VerificationError(f"{name} checksum mismatch")
        checks.append({"name": active, "outcome": "passed"})

        active = "analytical_tables_and_complete_report_reconciliation"
        inspection = load_bundle(
            bundle,
            expected_5km_sha256=artifacts["5km"][1],
            expected_10km_sha256=artifacts["10km"][1],
            expected_report_sha256=artifacts["report"][1],
        )
        checks.append({"name": active, "outcome": "passed"})

        active = "delivery_reconstruction"
        results = json.loads(artifacts["results"][0].read_bytes())
        manifest = json.loads(artifacts["manifest"][0].read_bytes())
        display_name = manifest["output"]["name"]
        if not isinstance(display_name, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9.-]*\.geojson", display_name
        ):
            raise VerificationError("invalid original display filename")
        export = build_delivery_export(
            inspection,
            display_name=display_name,
            generated_at=parse_utc_timestamp(results["generated_at_utc"]),
        )
        checks.append({"name": active, "outcome": "passed"})
        for name, payload in (
            ("display", export.display.geojson),
            ("manifest", export.display_manifest),
            ("results", export.results.payload),
        ):
            active = f"{name}_byte_reproduction"
            reproduced[name] = hashlib.sha256(payload).hexdigest()
            if artifacts[name][0].read_bytes() != payload:
                raise VerificationError(f"{name} reproduction differs")
            checks.append({"name": active, "outcome": "passed"})

        active = "artifact_evidence_and_verifier_stability"
        for path, expected in pins.values():
            if sha256_file(path) != expected:
                raise VerificationError("input changed during verification")
        if verifier_identity() != request["verifier"]:
            raise VerificationError("verifier changed during verification")
        checks.append({"name": active, "outcome": "passed"})
        outcome = "passed"
    except (Exception, KeyboardInterrupt) as exc:
        outcome = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        # Keep untrusted file contents and exception text out of logs/records.
        checks.append(
            {"name": active, "outcome": outcome, "error_type": type(exc).__name__}
        )
    result: dict[str, Any] = {
        "contract": CONTRACT,
        "schema_version": 1,
        "request_sha256": sha256_file(target / "request.json"),
        "completed_at_utc": _now(),
        "outcome": outcome,
        "checks": checks,
        "observed_artifacts": observed,
        "reproduced_delivery_sha256": reproduced,
        "visual_inspection": "not_performed",
        "scientific_validation": "not_performed",
        "raw_to_public_rerun": "not_performed",
    }
    _write_new(target / "result.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    for label in SOURCE_FILES:
        parser.add_argument(f"--expected-{label}-sha256", required=True)
    for label in ("display", "manifest", "results"):
        parser.add_argument(
            f"--{label}", nargs=2, metavar=("PATH", "SHA256"), required=True
        )
    parser.add_argument(
        "--evidence", nargs=2, metavar=("PATH", "SHA256"), action="append", default=[]
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="fresh ignored attempt directory"
    )
    args = parser.parse_args(argv)
    artifacts: dict[str, Pin] = {
        label: (args.bundle / filename, getattr(args, f"expected_{label}_sha256"))
        for label, filename in SOURCE_FILES.items()
    }
    artifacts.update(
        {
            label: (Path(getattr(args, label)[0]), getattr(args, label)[1])
            for label in ("display", "manifest", "results")
        }
    )
    try:
        result = verify_delivery(
            bundle=args.bundle,
            artifacts=artifacts,
            evidence=[(Path(path), digest) for path, digest in args.evidence],
            output_dir=args.output_dir,
        )
    except (OSError, ValueError) as exc:
        print(
            f"verification could not record an attempt: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {
                "outcome": result["outcome"],
                "record_directory": str(args.output_dir),
                "result_sha256": sha256_file(args.output_dir / "result.json"),
            }
        )
    )
    return 0 if result["outcome"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
