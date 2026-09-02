"""Shared validation for DuckDB's normalized memory-limit display."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

_MEMORY_SETTING_PATTERN = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>B|KB|MB|GB|TB|KIB|MIB|GIB|TIB)\s*$",
    re.IGNORECASE,
)
_UNIT_BYTES = {
    "B": Decimal(1),
    "KB": Decimal(1000),
    "MB": Decimal(1000**2),
    "GB": Decimal(1000**3),
    "TB": Decimal(1000**4),
    "KIB": Decimal(1024),
    "MIB": Decimal(1024**2),
    "GIB": Decimal(1024**3),
    "TIB": Decimal(1024**4),
}


@dataclass(frozen=True, slots=True)
class ParsedMemorySetting:
    """A memory setting in bytes plus its displayed precision."""

    bytes: Decimal
    display_quantum_bytes: Decimal


def parse_memory_setting(value: str) -> ParsedMemorySetting:
    """Parse decimal or binary DuckDB memory units without float rounding."""
    match = _MEMORY_SETTING_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"unsupported DuckDB memory setting: {value!r}")
    displayed_value = match.group("value")
    unit_bytes = _UNIT_BYTES[match.group("unit").upper()]
    decimal_places = len(displayed_value.partition(".")[2])
    return ParsedMemorySetting(
        bytes=Decimal(displayed_value) * unit_bytes,
        display_quantum_bytes=Decimal(1).scaleb(-decimal_places) * unit_bytes,
    )


def memory_settings_match(requested: str, effective: str) -> bool:
    """Allow only the effective value's displayed-unit rounding quantum."""
    requested_setting = parse_memory_setting(requested)
    effective_setting = parse_memory_setting(effective)
    return (
        abs(requested_setting.bytes - effective_setting.bytes)
        <= effective_setting.display_quantum_bytes
    )
