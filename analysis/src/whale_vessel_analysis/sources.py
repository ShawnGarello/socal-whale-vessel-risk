"""Configurable source-locator contract for local processing inputs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SourceContractError(ValueError):
    """Raised when a source locator is incomplete or malformed."""


@dataclass(frozen=True, slots=True)
class SourceLocator:
    """Locate one source artifact without embedding machine-specific paths."""

    source_id: str
    path: Path
    retrieved_on: date | None = None
    expected_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise SourceContractError("source_id cannot be blank")
        if not str(self.path).strip():
            raise SourceContractError("source path cannot be blank")
        if self.expected_sha256 is not None and not _SHA256_PATTERN.fullmatch(
            self.expected_sha256
        ):
            raise SourceContractError(
                "expected_sha256 must be 64 lowercase hexadecimal characters"
            )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "path": self.path.as_posix(),
            "retrieved_on": (
                None if self.retrieved_on is None else self.retrieved_on.isoformat()
            ),
            "expected_sha256": self.expected_sha256,
        }
