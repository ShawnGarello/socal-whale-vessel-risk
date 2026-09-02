"""Slow subprocess target used only by resource-profiler tests."""

from __future__ import annotations

import time
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Wait long enough for the parent profiler to sample or interrupt us."""
    del argv
    time.sleep(30)
    return 0
