import math

import pytest

from whale_vessel_analysis.vessel_speed import (
    SpeedTotals,
    combine_summaries,
    endpoint_speed,
)


def test_distance_weighted_means_and_unavailable_accounting():
    total = SpeedTotals()
    total.add(1000, 12, "available", 10)
    total.add(3000, 18, "available", 20)
    total.add(2000, 6, "unavailable", None)
    total.add(4000, 8, "inconsistent", None)
    summary = total.finish()
    assert summary.total_km == 10
    assert summary.to_dict() == {
        "sog_available_km": 4,
        "sog_unavailable_km": 2,
        "sog_inconsistent_km": 4,
        "reported_sog_mean_knots": 17.5,
        "implied_speed_mean_knots": 11,
    }


def test_zero_movement_and_missing_speed_are_not_zero_speed():
    total = SpeedTotals()
    total.add(0, 0, "available", 0)
    assert total.finish().to_dict()["reported_sog_mean_knots"] is None
    assert total.finish().to_dict()["implied_speed_mean_knots"] is None
    total.add(1000, 2, "unavailable", None)
    assert total.finish().to_dict()["reported_sog_mean_knots"] is None
    assert total.finish().to_dict()["implied_speed_mean_knots"] == 2
    zero = SpeedTotals()
    zero.add(1000, 2, "available", 0)
    assert zero.finish().to_dict()["reported_sog_mean_knots"] == 0


@pytest.mark.parametrize(
    "start,end,implied,expected",
    [
        (None, 10, 10, ("unavailable", None)),
        (10, 102.3, 10, ("unavailable", None)),
        (102.3, 102.3, 10, ("unavailable", None)),
        (10, 20, 10, ("available", 15)),
        (10, 20.002, 10, ("inconsistent", None)),
        (20, 20, 10, ("inconsistent", None)),
        (0, 0, 0, ("available", 0)),
    ],
)
def test_endpoint_mean_and_explicit_inclusive_consistency_choice(
    start, end, implied, expected
):
    assert endpoint_speed(start, end, implied) == expected


@pytest.mark.parametrize("value", [-1, 103, math.nan, math.inf, True, "12"])
def test_invalid_sog_is_not_silently_missing(value):
    with pytest.raises(ValueError):
        endpoint_speed(value, None, 10)


def test_group_union_uses_sufficient_statistics():
    a, b = SpeedTotals(), SpeedTotals()
    a.add(1000, 10, "available", 10)
    b.add(3000, 20, "available", 20)
    combined = combine_summaries([a.finish(), b.finish()])
    assert combined.to_dict()["reported_sog_mean_knots"] == 17.5


@pytest.mark.parametrize(
    "distance,implied,status,sog",
    [
        (-1, 1, "available", 1),
        (math.inf, 1, "available", 1),
        (1, math.nan, "available", 1),
        (1, 1, "available", None),
        (1, 1, "unavailable", 1),
        (1, 1, "available", math.inf),
    ],
)
def test_invalid_weights_and_availability_are_refused(distance, implied, status, sog):
    with pytest.raises(ValueError):
        SpeedTotals().add(distance, implied, status, sog)
