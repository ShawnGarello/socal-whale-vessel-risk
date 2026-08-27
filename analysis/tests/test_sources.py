from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from whale_vessel_analysis.sources import SourceContractError, SourceLocator


def test_source_location_is_configurable_and_platform_safe() -> None:
    source = SourceLocator(
        source_id="noaa-ais",
        path=Path("inputs") / "AIS_2024_07_15.csv",
        retrieved_on=date(2026, 8, 26),
        expected_sha256="a" * 64,
    )

    assert source.to_dict() == {
        "source_id": "noaa-ais",
        "path": "inputs/AIS_2024_07_15.csv",
        "retrieved_on": "2026-08-26",
        "expected_sha256": "a" * 64,
    }


def test_source_checksum_must_be_sha256() -> None:
    with pytest.raises(SourceContractError, match="64 lowercase hexadecimal"):
        SourceLocator("noaa-ais", Path("input.csv"), expected_sha256="not-a-hash")
