from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from whale_vessel_analysis.lineage import (
    ArtifactReference,
    LineageContractError,
    ProcessingStep,
    RunMetadata,
    ValidationRecord,
)

_INPUT_SHA = "a" * 64
_OUTPUT_SHA = "b" * 64
_CONFIG_SHA = "c" * 64


def _metadata(counts: dict[str, int]) -> RunMetadata:
    return RunMetadata(
        run_id="run-2026-08-26T120000Z",
        started_at=datetime(2026, 8, 26, 12, tzinfo=UTC),
        completed_at=datetime(2026, 8, 26, 12, 5, tzinfo=UTC),
        configuration_version=1,
        configuration_sha256=_CONFIG_SHA,
        steps=(ProcessingStep("validate-source", "1.0.0"),),
        inputs=(
            ArtifactReference(
                artifact_id="ais-day",
                locator="data/raw/AIS_2024_07_15.csv",
                sha256=_INPUT_SHA,
                source_id="noaa-marine-cadastre-ais",
                retrieved_on=date(2026, 8, 26),
            ),
        ),
        outputs=(
            ArtifactReference(
                artifact_id="validation-report",
                locator="data/interim/AIS_2024_07_15.validation.json",
                sha256=_OUTPUT_SHA,
            ),
        ),
        validations=(ValidationRecord.from_counts("ais-input", True, counts),),
    )


def test_lineage_serialization_and_hashing_are_deterministic() -> None:
    first = _metadata({"valid": 2, "invalid": 0})
    second = _metadata({"invalid": 0, "valid": 2})

    assert first.canonical_json() == second.canonical_json()
    assert first.digest() == second.digest()
    assert first.digest() == (
        "0b5e6c774f136e982e5ae5bd03834b6741035ce964aadfc993ee17e9d327396a"
    )


def test_source_artifact_requires_retrieval_date() -> None:
    with pytest.raises(LineageContractError, match="must either both be set"):
        ArtifactReference(
            artifact_id="source",
            locator="input.csv",
            sha256=_INPUT_SHA,
            source_id="publisher-source",
        )


def test_run_timestamp_must_be_utc() -> None:
    metadata = _metadata({"rows": 1})

    with pytest.raises(LineageContractError, match="timezone-aware UTC"):
        RunMetadata(
            run_id=metadata.run_id,
            started_at=datetime(2026, 8, 26, 12),
            configuration_version=metadata.configuration_version,
            configuration_sha256=metadata.configuration_sha256,
            steps=metadata.steps,
            inputs=metadata.inputs,
            outputs=metadata.outputs,
            validations=metadata.validations,
        )
