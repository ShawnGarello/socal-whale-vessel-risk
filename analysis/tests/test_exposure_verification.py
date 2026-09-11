"""Small synthetic checks of later evidence recording, not new analysis rules."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from test_exposure_delivery import _load, _make_bundle
from whale_vessel_analysis import exposure_verification as verification
from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.exposure_delivery import SOURCE_FILES, build_delivery_export


@pytest.fixture
def delivery(tmp_path, monkeypatch):
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    monkeypatch.setattr(verification, "ROOT", tmp_path)
    # Source/version identification is tested separately against actual files.
    monkeypatch.setattr(verification, "verifier_identity", lambda: {"version": "test"})
    export = build_delivery_export(
        _load(bundle, hashes),
        display_name="relative-exposure.geojson",
        generated_at=datetime(2026, 9, 6, tzinfo=UTC),
    )
    artifacts = {
        label: (bundle / filename, hashes[label])
        for label, filename in SOURCE_FILES.items()
    }
    public = tmp_path / "data/interim/delivery"
    public.mkdir(parents=True)
    for label, payload in (
        ("display", export.display.geojson),
        ("manifest", export.display_manifest),
        ("results", export.results.payload),
    ):
        path = public / f"{label}.json"
        path.write_bytes(payload)
        artifacts[label] = (path, sha256_file(path))
    evidence = tmp_path / "render-report.json"
    evidence.write_text('{"visual_review":"not_performed_by_this_script"}')
    return {
        "bundle": bundle,
        "artifacts": artifacts,
        "evidence": [(evidence, sha256_file(evidence))],
        "output_dir": tmp_path / "data/interim/check-first",
    }


def test_pass_preserves_lineage_and_prior_records(delivery):
    lineage = delivery["bundle"] / "run-metadata.json"
    before = lineage.read_bytes()
    result = verification.verify_delivery(**delivery)
    assert result["outcome"] == "passed"
    assert all(check["outcome"] == "passed" for check in result["checks"])
    for field in ("visual_inspection", "scientific_validation", "raw_to_public_rerun"):
        assert result[field] == "not_performed"
    record = delivery["output_dir"]
    request = json.loads((record / "request.json").read_bytes())
    assert request["verifier"] == {"version": "test"}
    assert datetime.fromisoformat(request["started_at_utc"]) <= datetime.fromisoformat(
        result["completed_at_utc"]
    )
    assert result["request_sha256"] == sha256_file(record / "request.json")
    assert set(result["reproduced_delivery_sha256"]) == {
        "display",
        "manifest",
        "results",
    }
    old = {p.name: p.read_bytes() for p in record.iterdir()}
    with pytest.raises(ValueError, match="already exists"):
        verification.verify_delivery(**delivery)
    delivery["output_dir"] = record.with_name("check-repeat")
    assert verification.verify_delivery(**delivery)["outcome"] == "passed"
    assert old == {p.name: p.read_bytes() for p in record.iterdir()}
    assert lineage.read_bytes() == before


@pytest.mark.parametrize("label", verification.ARTIFACT_LABELS)
def test_checksum_mismatch_is_retained_with_expected_and_observed(delivery, label):
    path, actual = delivery["artifacts"][label]
    delivery["artifacts"][label] = (path, "0" * 64)
    result = verification.verify_delivery(**delivery)
    assert result["outcome"] == "failed"
    assert result["observed_artifacts"][label]["sha256"] == actual
    request = json.loads((delivery["output_dir"] / "request.json").read_bytes())
    assert request["artifacts"][label]["expected_sha256"] == "0" * 64
    assert (delivery["output_dir"] / "result.json").is_file()


@pytest.mark.parametrize("label", ("display", "manifest", "results", "report"))
def test_matching_checksum_does_not_accept_changed_content(delivery, label):
    path, _ = delivery["artifacts"][label]
    document = json.loads(path.read_bytes())
    if label == "display":
        document["features"][0]["geometry"]["coordinates"][0][0][0] += 1
    elif label == "manifest":
        document["results"]["results_id"] = "exposure-results-" + "0" * 24
    elif label == "results":
        document["scenarios"]["5km_product"]["integrated_exposure"]["inside_vsr"] += 1
    else:
        document["grids"]["5km"]["methods"]["product"]["integrated_inside"] += 1
    path.write_text(json.dumps(document))
    delivery["artifacts"][label] = (path, sha256_file(path))
    result = verification.verify_delivery(**delivery)
    assert result["outcome"] == "failed"
    assert result["checks"][0]["outcome"] == "passed"
    assert result["checks"][-1]["outcome"] == "failed"


def test_missing_artifact_and_failed_evidence_reference_are_recorded(delivery):
    missing = delivery["artifacts"]["display"][0].with_name("missing.json")
    delivery["artifacts"]["display"] = (missing, "0" * 64)
    assert verification.verify_delivery(**delivery)["outcome"] == "failed"
    old = (delivery["output_dir"] / "result.json").read_bytes()
    delivery["output_dir"] = delivery["output_dir"].with_name("second")
    delivery["artifacts"]["display"] = (
        missing.with_name("display.json"),
        sha256_file(missing.with_name("display.json")),
    )
    delivery["evidence"] = [(delivery["evidence"][0][0], "0" * 64)]
    result = verification.verify_delivery(**delivery)
    assert result["outcome"] == "failed"
    assert "evidence_1" in result["observed_artifacts"]
    assert (
        delivery["output_dir"].with_name("check-first") / "result.json"
    ).read_bytes() == old


@pytest.mark.parametrize("exception", (ValueError, KeyboardInterrupt))
def test_failure_and_interruption_preserve_request_without_exception_text(
    delivery, monkeypatch, exception
):
    def fail(*args, **kwargs):
        assert (delivery["output_dir"] / "request.json").is_file()
        raise exception("untrusted exception content")

    monkeypatch.setattr(verification, "load_bundle", fail)
    result = verification.verify_delivery(**delivery)
    assert result["outcome"] == (
        "interrupted" if exception is KeyboardInterrupt else "failed"
    )
    assert "untrusted exception content" not in json.dumps(result)
    assert (
        result["checks"][-1]["name"]
        == "analytical_tables_and_complete_report_reconciliation"
    )


def test_post_validation_input_change_rejects_success(delivery, monkeypatch):
    original = verification.build_delivery_export

    def change(*args, **kwargs):
        export = original(*args, **kwargs)
        delivery["evidence"][0][0].write_text("changed during check")
        return export

    monkeypatch.setattr(verification, "build_delivery_export", change)
    result = verification.verify_delivery(**delivery)
    assert result["outcome"] == "failed"
    assert result["checks"][-1]["name"] == "artifact_evidence_and_verifier_stability"


def test_changed_verifier_rejects_success(delivery, monkeypatch):
    versions = iter(({"version": "first"}, {"version": "second"}))
    monkeypatch.setattr(verification, "verifier_identity", lambda: next(versions))
    assert verification.verify_delivery(**delivery)["outcome"] == "failed"


@pytest.mark.parametrize(
    "location",
    (
        "data/raw/check",
        "data/derived/check",
        "data/interim",
        "other-checkout/data/interim/check",
        ".git/check",
        "data/interim/raw/check",
    ),
)
def test_protected_destinations_write_nothing(delivery, tmp_path, location):
    output = tmp_path / location
    existed = output.exists()
    delivery["output_dir"] = output
    with pytest.raises(ValueError):
        verification.verify_delivery(**delivery)
    assert output.exists() == existed


def test_input_overlap_and_invalid_pins_write_nothing(delivery):
    delivery["output_dir"] = delivery["artifacts"]["display"][0] / "check"
    with pytest.raises(ValueError, match="overlap"):
        verification.verify_delivery(**delivery)
    delivery["output_dir"] = delivery["output_dir"].parents[1] / "attempt"
    path, _ = delivery["artifacts"]["results"]
    delivery["artifacts"]["results"] = (path, "not-a-checksum")
    with pytest.raises(ValueError, match="SHA-256"):
        verification.verify_delivery(**delivery)
    assert not delivery["output_dir"].exists()


def test_symlink_escape_is_refused(delivery, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "data/interim/link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        # Windows junctions exercise resolution without symlink privilege.
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            check=True,
            capture_output=True,
        )
    delivery["output_dir"] = link / "attempt"
    with pytest.raises(ValueError):
        verification.verify_delivery(**delivery)
    assert list(outside.iterdir()) == []


def test_result_write_failure_keeps_incomplete_request(delivery, monkeypatch):
    write = verification._write_new

    def fail_result(path, document):
        if path.name == "result.json":
            raise OSError("simulated full disk")
        write(path, document)

    monkeypatch.setattr(verification, "_write_new", fail_result)
    with pytest.raises(OSError):
        verification.verify_delivery(**delivery)
    assert (delivery["output_dir"] / "request.json").is_file()
    assert not (delivery["output_dir"] / "result.json").exists()


def test_verifier_identifies_actual_code_lock_and_versions():
    identity = verification.verifier_identity()
    assert identity["version"] == verification.VERIFIER_VERSION
    assert identity["package_source_sha256"]["exposure_verification.py"] == sha256_file(
        Path(verification.__file__)
    )
    assert identity["package_source_sha256"]["exposure_delivery.py"]
    assert identity["uv_lock_sha256"] == sha256_file(
        verification.ROOT / "analysis/uv.lock"
    )
    assert identity["software"]["pyarrow"]


def test_cli_success_and_refused_reuse(delivery, capsys):
    argv = [
        "--bundle",
        str(delivery["bundle"]),
        "--output-dir",
        str(delivery["output_dir"]),
    ]
    for name, (path, digest) in delivery["artifacts"].items():
        argv += (
            [f"--expected-{name}-sha256", digest]
            if name in SOURCE_FILES
            else [f"--{name}", str(path), digest]
        )
    assert verification.main(argv) == 0
    assert json.loads(capsys.readouterr().out)["outcome"] == "passed"
    assert verification.main(argv) == 2
    assert "could not record" in capsys.readouterr().err
