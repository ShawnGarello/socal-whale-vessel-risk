from __future__ import annotations

import pytest

from whale_vessel_analysis.duckdb_resources import memory_settings_match


@pytest.mark.parametrize(
    ("requested", "effective"),
    [("512MB", "488.2 MiB"), ("1GB", "953.6 MiB"), ("1GiB", "1.0 GiB")],
)
def test_normalized_duckdb_memory_displays_match(
    requested: str, effective: str
) -> None:
    assert memory_settings_match(requested, effective)


def test_materially_different_duckdb_memory_setting_does_not_match() -> None:
    assert not memory_settings_match("512MB", "400.0 MiB")
