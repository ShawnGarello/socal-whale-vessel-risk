import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "production_verifier",
    Path(__file__).resolve().parents[1] / "scripts/verify_production_vessel_input.py",
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
verify_cells = _module.verify_cells


def known_rows():
    row = {"water_area_km2": 2}
    for group, distance, sog, implied in (
        ("passenger", 1, 10, 12),
        ("cargo", 3, 20, 18),
        ("tanker", 0, None, None),
        ("all_commercial", 4, 17.5, 16.5),
    ):
        row.update(
            {
                f"vessel_km_{group}": distance,
                f"vessel_km_per_water_km2_{group}": distance / 2,
                f"sog_available_km_{group}": distance,
                f"sog_unavailable_km_{group}": 0,
                f"sog_inconsistent_km_{group}": 0,
                f"reported_sog_mean_knots_{group}": sog,
                f"implied_speed_mean_knots_{group}": implied,
            }
        )
    return [row]


def test_independent_verifier_recomputes_totals():
    result = verify_cells(known_rows())
    assert result["all_commercial"]["vessel_km"] == 4
    assert result["all_commercial"]["reported_sog_mean_knots"] == 17.5
    assert result["tanker"]["null_reported_speed_cells"] == 1
    assert result["tanker"]["zero_reported_speed_cells"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("reported_sog_mean_knots_tanker", 0),
        ("reported_sog_mean_knots_cargo", None),
        ("sog_unavailable_km_cargo", 1),
        ("implied_speed_mean_knots_cargo", 31),
        ("vessel_km_per_water_km2_cargo", 3),
    ],
)
def test_independent_verifier_rejects_wrong_semantics(field, value):
    rows = deepcopy(known_rows())
    rows[0][field] = value
    with pytest.raises(ValueError):
        verify_cells(rows)
