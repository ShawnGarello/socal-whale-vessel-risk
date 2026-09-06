"""ADR 0020 exploratory overlap and its predeclared sensitivity calculations.

Period-total movement, no speed term. All boundary summaries assume uniform
exposure within each cell's water geometry. Results require independent review.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import shapely
from shapely.geometry.base import BaseGeometry

from whale_vessel_analysis.exposure_geometry import CellAreas, ExposureBoundaries
from whale_vessel_analysis.exposure_inputs import ExposureInputCell, number, require

METHOD_VERSION = "1.0.0"
Method = Literal["product", "log_traffic"]
METHODS: tuple[Method, ...] = ("product", "log_traffic")
PERCENTILES = (0.8, 0.9, 0.95)
ASSUMPTION = "uniform exposure within each cell's water geometry"
STATUS = (
    "exploratory overlap proxy; production results pending independent audit "
    "and owner review"
)


@dataclass(frozen=True)
class ExposureCell:
    source: ExposureInputCell
    areas: CellAreas
    qualified_geometry: BaseGeometry


def prepare_cells(
    inputs: Sequence[ExposureInputCell], boundaries: ExposureBoundaries
) -> tuple[ExposureCell, ...]:
    require(
        bool(inputs) and len({c.cell_id for c in inputs}) == len(inputs),
        "empty/duplicate exposure cells",
    )
    cells = []
    for cell in inputs:
        for label, value in (
            ("water km2", cell.water_km2),
            ("whale density", cell.whale_density),
            ("whale abundance", cell.whale_abundance),
            ("vessel km", cell.vessel_km),
        ):
            number(value, label)
        require(cell.water_km2 > 0, "dry input must be omitted")
        require(
            math.isclose(
                cell.water_km2 * 1e6, cell.water.area, rel_tol=1e-10, abs_tol=1e-6
            ),
            "input water area differs from geometry",
        )
        require(
            math.isclose(
                cell.whale_abundance,
                cell.whale_density * cell.water_km2,
                rel_tol=1e-10,
                abs_tol=1e-9,
            ),
            "input whale units differ",
        )
        areas = boundaries.cell_areas(cell.water, water_crs="EPSG:3310")
        require(areas is not None, "dry input must be omitted")
        assert areas is not None
        qualified = shapely.normalize(cell.water.intersection(boundaries.domain))
        cells.append(ExposureCell(cell, areas, qualified))
    require(any(c.areas.qualified_m2 > 0 for c in cells), "empty qualified domain")
    return tuple(cells)


def coarsen_10km(inputs: Sequence[ExposureInputCell]) -> tuple[ExposureInputCell, ...]:
    """Sum input sufficient statistics BEFORE multiplying, on whole 10-km origins."""
    groups: dict[tuple[int, int], list[ExposureInputCell]] = defaultdict(list)
    for cell in inputs:
        groups[(cell.x_min_m // 10000 * 10000, cell.y_min_m // 10000 * 10000)].append(
            cell
        )
    result = []
    for (x, y), members in sorted(
        groups.items(), key=lambda item: (item[0][1], item[0][0])
    ):
        water = shapely.normalize(shapely.union_all([c.water for c in members]))
        area = float(water.area) / 1e6
        require(
            area > 0
            and math.isclose(
                area,
                math.fsum(c.water_km2 for c in members),
                rel_tol=1e-10,
                abs_tol=1e-12,
            ),
            "coarse water union fails area conservation",
        )
        abundance = math.fsum(c.whale_abundance for c in members)
        distance = math.fsum(c.vessel_km for c in members)
        result.append(
            ExposureInputCell(
                f"x{x}_y{y}", x, y, water, area, abundance / area, abundance, distance
            )
        )
    return tuple(result)


def intensities(cells: Sequence[ExposureCell], method: Method) -> list[float]:
    require(method in METHODS, "unknown exposure method")
    values = []
    for cell in cells:
        traffic = cell.source.vessel_km / cell.source.water_km2
        # w0 = 1 animal/km², t0 = 1 vessel-km/km² over the accepted period.
        value = cell.source.whale_density * (
            traffic if method == "product" else math.log1p(traffic)
        )
        number(value, "exposure intensity")
        values.append(value)
    return values


def weighted_quantile(
    values: Sequence[float], weights: Sequence[float], p: float
) -> float:
    """Smallest observed value with ascending cumulative area >= p * area.

    Zero weights are excluded. Ties are grouped before cumulative summation;
    weights are areas, not cell counts. No interpolated percentile or tie split.
    """
    require(0 < p < 1, "percentile must lie strictly between zero and one")
    require(len(values) == len(weights), "quantile values/weights differ")
    grouped: dict[float, list[float]] = defaultdict(list)
    for value, weight in zip(values, weights, strict=True):
        number(value, "quantile value")
        number(weight, "quantile weight")
        if weight > 0:
            grouped[value].append(weight)
    require(bool(grouped), "quantile reference has no positive area")
    ordered = [(value, math.fsum(grouped[value])) for value in sorted(grouped)]
    target = p * math.fsum(weight for _, weight in ordered)
    parts = []
    for value, weight in ordered:
        parts.append(weight)
        if math.fsum(parts) >= target:
            return value
    return ordered[-1][0]


def normalized(
    values: Sequence[float], cells: Sequence[ExposureCell]
) -> tuple[float, list[float | None]]:
    require(len(values) == len(cells), "normalization rows differ")
    maximum = max(
        value
        for value, cell in zip(values, cells, strict=True)
        if cell.areas.qualified_m2 > 0
    )
    return maximum, [
        value / maximum if maximum > 0 and cell.areas.qualified_m2 > 0 else None
        for value, cell in zip(values, cells, strict=True)
    ]


def summarize(cells: Sequence[ExposureCell], values: Sequence[float]) -> dict[str, Any]:
    require(len(values) == len(cells), "summary rows differ")
    for value in values:
        number(value, "summary intensity")
    inside = math.fsum(
        v * c.areas.inside_vsr_m2 / 1e6 for c, v in zip(cells, values, strict=True)
    )
    outside = math.fsum(
        v * c.areas.outside_vsr_m2 / 1e6 for c, v in zip(cells, values, strict=True)
    )
    qualified = math.fsum(
        v * c.areas.qualified_m2 / 1e6 for c, v in zip(cells, values, strict=True)
    )
    require(
        math.isclose(inside + outside, qualified, rel_tol=1e-10, abs_tol=1e-9),
        "integrated exposure not conserved",
    )
    area = math.fsum(c.areas.qualified_m2 for c in cells) / 1e6
    rows = []
    for positive_only in (False, True):
        weights = [
            c.areas.qualified_m2 if not positive_only or value > 0 else 0
            for c, value in zip(cells, values, strict=True)
        ]
        for p in PERCENTILES:
            threshold = (
                weighted_quantile(values, weights, p)
                if math.fsum(weights) > 0
                else None
            )
            selected = [
                i
                for i, (c, value) in enumerate(zip(cells, values, strict=True))
                if threshold is not None
                and threshold > 0
                and value >= threshold
                and c.areas.qualified_m2 > 0
            ]
            high_area = math.fsum(cells[i].areas.qualified_m2 for i in selected) / 1e6
            high_inside = (
                math.fsum(cells[i].areas.inside_vsr_m2 for i in selected) / 1e6
            )
            high_outside = (
                math.fsum(cells[i].areas.outside_vsr_m2 for i in selected) / 1e6
            )
            rows.append(
                {
                    "percentile": p,
                    "reference": "positive_only" if positive_only else "all_valid",
                    "threshold": threshold,
                    "available": high_area > 0,
                    "unavailable_reason": None
                    if high_area > 0
                    else "zero threshold or no positive exposure area",
                    "high_area_km2": high_area if high_area > 0 else None,
                    "high_inside_km2": high_inside if high_area > 0 else None,
                    "high_outside_km2": high_outside if high_area > 0 else None,
                    "share_high_area_inside": high_inside / high_area
                    if high_area > 0
                    else None,
                    "share_high_area_outside": high_outside / high_area
                    if high_area > 0
                    else None,
                    "share_domain_area_high": high_area / area
                    if high_area > 0
                    else None,
                    "threshold_tied_area_km2": math.fsum(
                        c.areas.qualified_m2
                        for c, value in zip(cells, values, strict=True)
                        if value == threshold
                    )
                    / 1e6,
                    "selected_cell_ids": [cells[i].source.cell_id for i in selected],
                }
            )
    contributions = [
        (value * cell.areas.outside_vsr_m2 / 1e6, cell.source)
        for cell, value in zip(cells, values, strict=True)
        if value * cell.areas.outside_vsr_m2 > 0
    ]
    top = sorted(contributions, key=lambda item: (-item[0], item[1].cell_id))[:10]
    maximum, _ = normalized(values, cells)
    return {
        "qualified_area_km2": area,
        "integrated_qualified": qualified,
        "integrated_inside": inside,
        "integrated_outside": outside,
        "share_exposure_inside": inside / qualified if qualified > 0 else None,
        "share_exposure_outside": outside / qualified if qualified > 0 else None,
        "conservation_residual": inside + outside - qualified,
        "normalization_maximum": maximum,
        "thresholds": rows,
        "top_outside_cells": [
            {
                "cell_id": c.cell_id,
                "x_min_m": c.x_min_m,
                "y_min_m": c.y_min_m,
                "outside_integrated": value,
                "share_outside_total": value / outside,
            }
            for value, c in top
        ],
        "top_ten_share_outside": math.fsum(value for value, _ in top) / outside
        if outside > 0
        else None,
    }


def _ranks(values: Sequence[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for i in ordered[start:end]:
            result[i] = rank
        start = end
    return result


def compare_methods(
    cells: Sequence[ExposureCell],
    primary: Sequence[float],
    alternative: Sequence[float],
) -> dict[str, Any]:
    """Unweighted cell-rank comparison, ties receive their average rank."""
    left = _ranks(
        [v for v, c in zip(primary, cells, strict=True) if c.areas.qualified_m2 > 0]
    )
    right = _ranks(
        [v for v, c in zip(alternative, cells, strict=True) if c.areas.qualified_m2 > 0]
    )
    mean = (len(left) + 1) / 2
    numerator = math.fsum(
        (a - mean) * (b - mean) for a, b in zip(left, right, strict=True)
    )
    denominator = math.sqrt(
        math.fsum((a - mean) ** 2 for a in left)
        * math.fsum((b - mean) ** 2 for b in right)
    )
    return {
        "spearman_cell_ranks": numerator / denominator if denominator else None,
        "maximum_absolute_rank_change": max(
            abs(a - b) for a, b in zip(left, right, strict=True)
        ),
    }


def analyze_grid(cells: Sequence[ExposureCell]) -> dict[str, Any]:
    results = {
        method: summarize(cells, intensities(cells, method)) for method in METHODS
    }
    product = intensities(cells, "product")
    maximum, _ = normalized(product, cells)
    eligible = [c for c in cells if c.areas.qualified_m2 > 0]
    wmax = max(c.source.whale_density for c in eligible)
    tmax = max(c.source.vessel_km / c.source.water_km2 for c in eligible)
    controls = {}
    for name, scale in (
        ("product_max", maximum),
        ("separate_input_maxima", wmax * tmax),
    ):
        if scale == 0:
            controls[name] = {"available": False, "reason": "zero normalizer"}
            continue
        summary = summarize(cells, [value / scale for value in product])
        reference = results["product"]
        same_sets = all(
            a["selected_cell_ids"] == b["selected_cell_ids"]
            for a, b in zip(summary["thresholds"], reference["thresholds"], strict=True)
        )
        difference = (
            summary["share_exposure_inside"] - reference["share_exposure_inside"]
        )
        require(
            abs(difference) <= 1e-12 and same_sets, "global scaling invariant failed"
        )
        controls[name] = {
            "available": True,
            "normalizer": scale,
            "inside_share_difference": difference,
            "all_threshold_memberships_equal": same_sets,
        }
    return {
        "methods": results,
        "normalization_controls": controls,
        "product_vs_log": compare_methods(
            cells, product, intensities(cells, "log_traffic")
        ),
        "water_cell_count": len(cells),
        "qualified_cell_count": len(eligible),
        "excluded_cell_count": len(cells) - len(eligible),
        "zero_product_qualified_cells": sum(
            c.areas.qualified_m2 > 0 and v == 0
            for c, v in zip(cells, product, strict=True)
        ),
        "maximum_water_area_residual_m2": max(
            abs(c.areas.water_m2 - c.areas.qualified_m2 - c.areas.excluded_domain_m2)
            for c in cells
        ),
        "maximum_vsr_area_residual_m2": max(
            abs(c.areas.qualified_m2 - c.areas.inside_vsr_m2 - c.areas.outside_vsr_m2)
            for c in cells
        ),
    }
