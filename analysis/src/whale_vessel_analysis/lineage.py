"""Deterministic provenance, lineage, and run-metadata contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class LineageContractError(ValueError):
    """Raised when lineage metadata is incomplete or ambiguous."""


def _nonblank(value: str, name: str) -> None:
    if not value.strip():
        raise LineageContractError(f"{name} cannot be blank")


def _sha256(value: str, name: str) -> None:
    if not _SHA256_PATTERN.fullmatch(value):
        raise LineageContractError(
            f"{name} must be 64 lowercase hexadecimal characters"
        )


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    """Trace one input or output artifact to a source and checksum reference."""

    artifact_id: str
    locator: str
    sha256: str
    source_id: str | None = None
    retrieved_on: date | None = None

    def __post_init__(self) -> None:
        _nonblank(self.artifact_id, "artifact_id")
        _nonblank(self.locator, "artifact locator")
        _sha256(self.sha256, "artifact sha256")
        if self.source_id is not None:
            _nonblank(self.source_id, "source_id")
        if (self.source_id is None) != (self.retrieved_on is None):
            raise LineageContractError(
                "source_id and retrieved_on must either both be set for a source "
                "artifact or both be absent for a produced artifact"
            )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "artifact_id": self.artifact_id,
            "locator": self.locator,
            "sha256": self.sha256,
            "source_id": self.source_id,
            "retrieved_on": (
                None if self.retrieved_on is None else self.retrieved_on.isoformat()
            ),
        }


@dataclass(frozen=True, slots=True)
class ProcessingStep:
    """Name and version one reproducible processing step."""

    name: str
    version: str

    def __post_init__(self) -> None:
        _nonblank(self.name, "processing step name")
        _nonblank(self.version, "processing step version")

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True, slots=True)
class ValidationRecord:
    """Store one named validation outcome and its auditable counts."""

    name: str
    passed: bool
    counts: tuple[tuple[str, int], ...]
    messages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonblank(self.name, "validation name")
        keys = [key for key, _value in self.counts]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise LineageContractError(
                "validation counts must have unique keys in sorted order"
            )
        for key, value in self.counts:
            _nonblank(key, "validation count key")
            if value < 0:
                raise LineageContractError("validation counts cannot be negative")
        if any(not message.strip() for message in self.messages):
            raise LineageContractError("validation messages cannot be blank")

    @classmethod
    def from_counts(
        cls,
        name: str,
        passed: bool,
        counts: dict[str, int],
        messages: tuple[str, ...] = (),
    ) -> ValidationRecord:
        return cls(name, passed, tuple(sorted(counts.items())), messages)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "passed": self.passed,
            "counts": dict(self.counts),
            "messages": list(self.messages),
        }


@dataclass(frozen=True, slots=True)
class RunMetadata:
    """Tie one execution to configuration, artifacts, steps, and validation."""

    run_id: str
    started_at: datetime
    configuration_version: int
    configuration_sha256: str
    steps: tuple[ProcessingStep, ...]
    inputs: tuple[ArtifactReference, ...]
    outputs: tuple[ArtifactReference, ...]
    validations: tuple[ValidationRecord, ...]
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        _nonblank(self.run_id, "run_id")
        if self.started_at.utcoffset() != UTC.utcoffset(self.started_at):
            raise LineageContractError("started_at must be timezone-aware UTC")
        if self.completed_at is not None:
            if self.completed_at.utcoffset() != UTC.utcoffset(self.completed_at):
                raise LineageContractError("completed_at must be timezone-aware UTC")
            if self.completed_at < self.started_at:
                raise LineageContractError("completed_at cannot precede started_at")
        if self.configuration_version < 1:
            raise LineageContractError("configuration_version must be positive")
        _sha256(self.configuration_sha256, "configuration_sha256")
        if not self.steps:
            raise LineageContractError("a run must record at least one processing step")
        if not self.inputs:
            raise LineageContractError("a run must record at least one input artifact")

    @staticmethod
    def _timestamp(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "started_at": self._timestamp(self.started_at),
            "completed_at": self._timestamp(self.completed_at),
            "configuration": {
                "version": self.configuration_version,
                "sha256": self.configuration_sha256,
            },
            "steps": [step.to_dict() for step in self.steps],
            "inputs": [artifact.to_dict() for artifact in self.inputs],
            "outputs": [artifact.to_dict() for artifact in self.outputs],
            "validations": [record.to_dict() for record in self.validations],
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
