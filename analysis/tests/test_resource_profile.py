from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import NoReturn

import psutil
import pytest

import whale_vessel_analysis.resource_profile as resource_profile
from whale_vessel_analysis.resource_profile import (
    ResourcePreflightError,
    RuntimeResourceReadings,
    RuntimeThresholds,
    _profile,
    _validate_cli_paths,
    evaluate_runtime_thresholds,
)


def test_profile_writes_path_free_report_for_direct_module(tmp_path: Path) -> None:
    output = tmp_path / "profile.json"
    disk_root = tmp_path / "generated"
    disk_root.mkdir()

    report = _profile(
        module="whale_vessel_analysis.cli",
        module_arguments=["--help"],
        output_path=output,
        label="test-profile",
        disk_root=disk_root,
        spill_root=None,
        sample_interval_seconds=0.05,
        baseline_samples=3,
    )

    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted == report
    assert report["contract"] == "resource-profile-v1"
    assert report["exit_code"] == 0
    assert report["memory_bytes"]["application_baseline_rss"] > 0
    assert report["memory_bytes"]["application_peak_sampled_rss"] > 0
    assert report["memory_bytes"]["direct_spawn_root_baseline_rss"] > 0
    assert report["memory_bytes"]["descendants_peak_sampled_rss_sum"] >= 0
    assert report["target_output"]["stdout_bytes"] > 0
    assert report["preflight"]["available_memory_bytes"] > 0
    assert report["preflight"]["free_disk_bytes"] > 0
    assert report["runtime_resources"]["minimum_available_memory_bytes"] > 0
    assert report["runtime_resources"]["minimum_free_disk_bytes"] > 0
    assert report["software_versions"]["python"]
    assert report["software_versions"]["psutil"]
    assert report["software_versions"]["platform"]
    assert str(tmp_path) not in output.read_text(encoding="utf-8")


def test_profile_refuses_to_overwrite_evidence(tmp_path: Path) -> None:
    output = tmp_path / "existing.json"
    output.write_text("existing\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="profile output already exists"):
        _profile(
            module="whale_vessel_analysis.cli",
            module_arguments=["--help"],
            output_path=output,
            label="test-profile",
            disk_root=None,
            spill_root=None,
            baseline_samples=3,
        )


def test_profile_does_not_reuse_or_overwrite_predictable_temporary_name(
    tmp_path: Path,
) -> None:
    output = tmp_path / "profile.json"
    unrelated = tmp_path / ".profile.json.tmp"
    unrelated.write_text("unrelated\n", encoding="utf-8")

    _profile(
        module="whale_vessel_analysis.cli",
        module_arguments=["--help"],
        output_path=output,
        label="test-profile",
        disk_root=None,
        spill_root=None,
        baseline_samples=3,
    )

    assert unrelated.read_text(encoding="utf-8") == "unrelated\n"


@pytest.mark.parametrize(
    ("thresholds", "expected"),
    [
        (
            RuntimeThresholds(minimum_available_memory_bytes=101),
            "minimum_available_memory",
        ),
        (RuntimeThresholds(minimum_free_disk_bytes=201), "minimum_free_disk"),
        (
            RuntimeThresholds(maximum_application_rss_bytes=300),
            "maximum_application_rss",
        ),
        (RuntimeThresholds(maximum_spill_bytes=400), "maximum_spill"),
    ],
)
def test_runtime_threshold_evaluation_is_deterministic(
    thresholds: RuntimeThresholds, expected: str
) -> None:
    readings: RuntimeResourceReadings = {
        "available_memory_bytes": 100,
        "free_disk_bytes": 200,
        "application_rss_bytes": 300,
        "spill_bytes": 400,
    }

    assert evaluate_runtime_thresholds(readings, thresholds) == expected


def test_profile_aborts_target_and_writes_orderly_report_from_mocked_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "profile.json"
    spill = tmp_path / "spill"
    spill.mkdir()
    mocked: RuntimeResourceReadings = {
        "available_memory_bytes": 10_000,
        "free_disk_bytes": 10_000,
        "application_rss_bytes": 501,
        "spill_bytes": 25,
    }
    monkeypatch.setattr(resource_profile, "_runtime_readings", lambda **_: mocked)

    report = _profile(
        module="tests.resource_profile_target",
        module_arguments=[],
        output_path=output,
        label="test-resource-abort",
        disk_root=tmp_path / "generated",
        spill_root=spill,
        sample_interval_seconds=0.05,
        baseline_samples=3,
        runtime_thresholds=RuntimeThresholds(maximum_application_rss_bytes=500),
    )

    assert report["target_outcome"] == "resource_abort"
    assert report["runtime_guard"]["termination_threshold"] == (
        "maximum_application_rss"
    )
    assert report["runtime_guard"]["termination_readings"] == mocked
    assert report["exit_code"] != 0
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_profiler_cli_uses_distinct_resource_abort_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim = (tmp_path / "data" / "interim").resolve()
    raw = (tmp_path / "data" / "raw").resolve()
    monkeypatch.setattr(resource_profile, "_PROJECT_INTERIM_ROOT", interim)
    monkeypatch.setattr(resource_profile, "_PROJECT_RAW_ROOT", raw)
    monkeypatch.setattr(
        resource_profile,
        "_profile",
        lambda **_: {"target_outcome": "resource_abort", "exit_code": 0},
    )

    assert (
        resource_profile.main(
            [
                "--module",
                "whale_vessel_analysis.cli",
                "--output",
                str(interim / "profile.json"),
                "--label",
                "resource-abort",
            ]
        )
        == resource_profile.RESOURCE_ABORT_EXIT_CODE
    )


def test_profile_reaps_target_when_sampling_is_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_pid: int | None = None
    real_terminate = resource_profile._terminate_and_reap

    def capture_terminate(child: subprocess.Popen[str]) -> None:
        nonlocal target_pid
        target_pid = child.pid
        real_terminate(child)

    def interrupt(**_: object) -> NoReturn:
        raise KeyboardInterrupt

    monkeypatch.setattr(resource_profile, "_terminate_and_reap", capture_terminate)
    monkeypatch.setattr(resource_profile, "_runtime_readings", interrupt)

    with pytest.raises(KeyboardInterrupt):
        _profile(
            module="tests.resource_profile_target",
            module_arguments=[],
            output_path=tmp_path / "profile.json",
            label="test-interrupt",
            disk_root=tmp_path / "generated",
            spill_root=None,
            sample_interval_seconds=0.05,
            baseline_samples=3,
        )

    assert target_pid is not None
    assert not psutil.pid_exists(target_pid)


def test_cli_path_boundary_requires_interim_output_and_rejects_broad_roots(
    tmp_path: Path,
) -> None:
    valid_output = resource_profile._PROJECT_INTERIM_ROOT / "profile" / "run.json"
    _validate_cli_paths(valid_output, tmp_path / "run", tmp_path / "spill")

    with pytest.raises(ValueError, match="data/raw"):
        _validate_cli_paths(
            resource_profile._PROJECT_RAW_ROOT / "profile.json", None, None
        )
    with pytest.raises(ValueError, match="data/interim"):
        _validate_cli_paths(tmp_path / "profile.json", None, None)
    with pytest.raises(ValueError, match="too broad"):
        _validate_cli_paths(valid_output, resource_profile._PROJECT_ROOT, None)
    with pytest.raises(ValueError, match="too broad"):
        _validate_cli_paths(valid_output, None, Path(valid_output.anchor))


def test_profile_refuses_before_start_when_memory_gate_cannot_pass(
    tmp_path: Path,
) -> None:
    output = tmp_path / "profile.json"

    with pytest.raises(ResourcePreflightError, match="available memory is below"):
        _profile(
            module="whale_vessel_analysis.cli",
            module_arguments=["--help"],
            output_path=output,
            label="test-profile",
            disk_root=None,
            spill_root=None,
            baseline_samples=3,
            minimum_free_memory_bytes=2**100,
        )

    assert not output.exists()


@pytest.mark.parametrize(
    ("sample_interval_seconds", "baseline_samples", "message"),
    [
        (0.049, 3, "sample interval"),
        (0.1, 2, "baseline samples"),
    ],
)
def test_profile_rejects_intrusive_or_insufficient_sampling(
    tmp_path: Path,
    sample_interval_seconds: float,
    baseline_samples: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _profile(
            module="whale_vessel_analysis.cli",
            module_arguments=["--help"],
            output_path=tmp_path / "profile.json",
            label="test-profile",
            disk_root=None,
            spill_root=None,
            sample_interval_seconds=sample_interval_seconds,
            baseline_samples=baseline_samples,
        )
