from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import box

from whale_vessel_analysis.domain_evidence import Scenario, measure_candidate


def test_distance_units_are_explicit() -> None:
    assert Scenario("a", "coastline", 40, "statute_mile").distance_m == pytest.approx(
        64373.76
    )
    assert Scenario("b", "coastline", 40, "nautical_mile").distance_m == pytest.approx(
        74080.0
    )


def test_candidate_measurement_uses_fractional_geometry() -> None:
    cells = np.array(
        [box(0, 0, 100, 100), box(100, 0, 200, 100), box(200, 0, 300, 100)],
        dtype=object,
    )
    result = measure_candidate(
        cells,
        box(-10, -10, 150, 110),
        box(-10, -10, 100, 110),
        Scenario("synthetic", "receivers", 40, "statute_mile"),
        tolerance_m2=1e-9,
    )
    assert result.included_water_area_m2 == pytest.approx(15000)
    assert result.inside_vsr_area_m2 == pytest.approx(10000)
    assert result.outside_vsr_area_m2 == pytest.approx(5000)
    assert result.fully_inside_cell_count == 1
    assert result.partly_inside_cell_count == 1
    assert result.wholly_outside_cell_count == 1
    assert result.to_dict(10000)["inside_fraction_of_candidate"] == pytest.approx(2 / 3)
