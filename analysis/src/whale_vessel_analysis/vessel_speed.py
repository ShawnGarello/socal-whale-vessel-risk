"""Separate distance-weighted reported-SOG descriptors on retained movement.

The five-knot consistency band is an explicit exploratory choice under ADR
0006. It does not validate SOG or alter the vessel-distance population.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from whale_vessel_analysis.vessel_grid import _CompensatedTotal

SPEED_CONTRACT = "descriptive_movement_speed_v1"
SPEED_VERSION = "1.0.0"
SOG_CONSISTENCY_KNOTS = 5.0
SpeedStatus = Literal["available", "unavailable", "inconsistent"]


def endpoint_speed(
    start_sog: object, end_sog: object, implied_knots: float
) -> tuple[SpeedStatus, float | None]:
    """Classify an endpoint mean without imputing unavailable observations."""
    if not math.isfinite(implied_knots) or implied_knots < 0:
        raise ValueError("implied speed must be finite and nonnegative")
    values: list[float] = []
    for value in (start_sog, end_sog):
        if value is None or value == 102.3:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("reported SOG must be numeric or unavailable")
        if not math.isfinite(value) or not 0 <= value <= 102.2:
            raise ValueError("reported SOG is outside the cleaned source contract")
        values.append(float(value))
    if len(values) != 2:
        return "unavailable", None
    mean = math.fsum(values) / 2
    if abs(mean - implied_knots) > SOG_CONSISTENCY_KNOTS:
        return "inconsistent", None
    return "available", mean


@dataclass(frozen=True)
class SpeedSummary:
    available_km: float
    unavailable_km: float
    inconsistent_km: float
    sog_distance_sum: float
    implied_distance_sum: float

    @property
    def total_km(self) -> float:
        return math.fsum((self.available_km, self.unavailable_km, self.inconsistent_km))

    def to_dict(self) -> dict[str, float | None]:
        return {
            "sog_available_km": self.available_km,
            "sog_unavailable_km": self.unavailable_km,
            "sog_inconsistent_km": self.inconsistent_km,
            "reported_sog_mean_knots": (
                self.sog_distance_sum / self.available_km
                if self.available_km > 0
                else None
            ),
            "implied_speed_mean_knots": (
                self.implied_distance_sum / self.total_km if self.total_km > 0 else None
            ),
        }


class SpeedTotals:
    """Bounded compensated sufficient statistics for one cell/group."""

    def __init__(self) -> None:
        self.weights = {
            key: _CompensatedTotal()
            for key in ("available", "unavailable", "inconsistent")
        }
        self.sog = _CompensatedTotal()
        self.implied = _CompensatedTotal()

    def add(
        self,
        distance_m: float,
        implied_knots: float,
        status: SpeedStatus,
        sog_mean: float | None,
    ) -> None:
        if not math.isfinite(distance_m) or distance_m < 0:
            raise ValueError("speed weight must be finite and nonnegative")
        if not math.isfinite(implied_knots) or implied_knots < 0:
            raise ValueError("implied speed must be finite and nonnegative")
        if status not in self.weights or (status == "available") != (
            sog_mean is not None
        ):
            raise ValueError("inconsistent speed availability")
        if sog_mean is not None and (not math.isfinite(sog_mean) or sog_mean < 0):
            raise ValueError("reported mean must be finite and nonnegative")
        self.weights[status].add(distance_m)
        self.implied.add(distance_m * implied_knots)
        if sog_mean is not None:
            self.sog.add(distance_m * sog_mean)

    def finish(self) -> SpeedSummary:
        return SpeedSummary(
            self.weights["available"].total / 1000,
            self.weights["unavailable"].total / 1000,
            self.weights["inconsistent"].total / 1000,
            self.sog.total / 1000,
            self.implied.total / 1000,
        )


def combine_summaries(summaries: list[SpeedSummary]) -> SpeedSummary:
    """Combine sufficient statistics, never average group means."""
    return SpeedSummary(
        *(
            math.fsum(getattr(summary, name) for summary in summaries)
            for name in (
                "available_km",
                "unavailable_km",
                "inconsistent_km",
                "sog_distance_sum",
                "implied_distance_sum",
            )
        )
    )


def speed_method() -> dict[str, object]:
    return {
        "contract": SPEED_CONTRACT,
        "processing_version": SPEED_VERSION,
        "population": (
            "positive-length retained ADR 0018 segments allocated to exact "
            "water support"
        ),
        "weight": (
            "allocated projected distance; not observations, time, vessels or transits"
        ),
        "reported_sog": (
            "arithmetic mean of both reported endpoint SOG values, in knots"
        ),
        "implied_speed": (
            "projected parent distance / elapsed seconds, converted to knots"
        ),
        "consistency_band_knots": SOG_CONSISTENCY_KNOTS,
        "consistency_choice": (
            "exclude endpoint means more than 5 knots from implied speed; "
            "exploratory screen, not independent validation"
        ),
        "unavailable": "either endpoint null or explicit 102.3 sentinel; no imputation",
        "zero_movement": "zero weight; no movement gives null means, not zero speed",
        "exclusions": (
            "rejected segments and outside/ambiguous/invalid support "
            "pieces have no cell speed weight"
        ),
        "activity_unchanged": True,
        "limitations": (
            "movement-weighted descriptive speeds omit stationary "
            "presence; no compliance or inside/outside result; endpoint agreement "
            "can share GPS errors"
        ),
    }
