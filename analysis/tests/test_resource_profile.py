from __future__ import annotations

import json
from pathlib import Path

import pytest

from whale_vessel_analysis.resource_profile import ResourcePreflightError, _profile


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
