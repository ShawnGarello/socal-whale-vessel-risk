"""Known-answer accounting, without real whale, vessel or VSR fixtures."""

import math

import pytest
from shapely.geometry import LineString, MultiPolygon, Polygon, box

from whale_vessel_analysis.exposure_geometry import (
    CellAreas,
    ExposureBoundaries,
    load_local_boundaries,
)

CRS = "EPSG:3310"
CELL = box(0, 0, 5000, 5000)


@pytest.mark.parametrize(
    ("water", "cut", "expected_water", "expected_inside", "fraction"),
    [
        (CELL, 1500, 25_000_000, 7_500_000, 0.30),
        (box(1000, 0, 5000, 5000), 2000, 20_000_000, 5_000_000, 0.25),
        (CELL, 2250, 25_000_000, 11_250_000, 0.45),
        (CELL, 0, 25_000_000, 0, 0),
        (CELL, 5000, 25_000_000, 25_000_000, 1),
    ],
)
def test_adr0004_water_fractions(water, cut, expected_water, expected_inside, fraction):
    boundaries = ExposureBoundaries(CELL, box(-1, -1, cut, 5001), CRS)
    areas = boundaries.cell_areas(water, water_crs=CRS)
    assert areas.water_m2 == expected_water
    assert areas.inside_vsr_m2 == expected_inside
    assert areas.inside_fraction_of_qualified == fraction
    total = areas.split_water_total(100)
    assert total.inside_vsr == pytest.approx(100 * fraction)
    assert total.outside_vsr == pytest.approx(100 * (1 - fraction))
    assert total.excluded_domain == 0


def test_centroid_and_majority_fail_for_45_percent_case():
    vsr = box(-1, -1, 2250, 5001)
    assert not vsr.covers(CELL.centroid)
    areas = ExposureBoundaries(CELL, vsr, CRS).cell_areas(CELL, water_crs=CRS)
    assert areas.inside_fraction_of_qualified == 0.45
    assert areas.split_water_total(100).inside_vsr == 45


def test_joint_intersection_is_not_product_of_independent_fractions():
    # Domain is left half, VSR is right half: each covers half of the water,
    # but their joint positive area is zero, not one quarter.
    boundaries = ExposureBoundaries(
        box(0, 0, 2500, 5000), box(2500, 0, 5000, 5000), CRS
    )
    areas = boundaries.cell_areas(CELL, water_crs=CRS)
    assert areas.qualified_m2 == 12_500_000
    assert areas.inside_vsr_m2 == 0
    assert areas.inside_fraction_of_qualified == 0
    split = areas.split_water_total(100)
    assert (split.inside_vsr, split.outside_vsr, split.excluded_domain) == (0, 50, 50)


def test_nested_partial_domain_uses_full_water_total_once():
    boundaries = ExposureBoundaries(box(0, 0, 2500, 5000), box(0, 0, 1000, 5000), CRS)
    areas = boundaries.cell_areas(CELL, water_crs=CRS)
    assert areas.inside_fraction_of_qualified == 0.4
    split = areas.split_water_total(100)
    assert (split.inside_vsr, split.outside_vsr, split.excluded_domain) == (20, 30, 50)


def test_dry_and_wholly_excluded_are_distinct():
    boundaries = ExposureBoundaries(CELL, CELL, CRS)
    assert boundaries.cell_areas(Polygon(), water_crs=CRS) is None
    excluded = boundaries.cell_areas(box(6000, 0, 7000, 1000), water_crs=CRS)
    assert excluded.qualified_m2 == 0
    assert excluded.inside_fraction_of_qualified is None
    assert excluded.split_water_total(100).excluded_domain == 100
    assert excluded.split_water_total(0).excluded_domain == 0


def test_holes_disconnected_water_and_vsr_hole():
    water = MultiPolygon([box(0, 0, 2, 2), box(3, 0, 4, 2)])
    vsr = Polygon(
        [(0, 0), (4, 0), (4, 2), (0, 2)],
        holes=[[(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)]],
    )
    areas = ExposureBoundaries(box(-1, -1, 5, 3), vsr, CRS).cell_areas(
        water, water_crs=CRS
    )
    assert areas.water_m2 == 6
    assert areas.inside_vsr_m2 == 5
    assert areas.outside_vsr_m2 == 1


def test_positive_slivers_are_not_thresholded_away():
    boundaries = ExposureBoundaries(box(0, 0, 1e-8, 1), box(0, 0, 1, 1), CRS)
    areas = boundaries.cell_areas(box(0, 0, 1, 1), water_crs=CRS)
    assert areas.qualified_m2 == 1e-8
    assert areas.inside_fraction_of_qualified == 1


def test_multicell_conservation_and_refinement_for_uniform_intensity():
    boundaries = ExposureBoundaries(box(0, 0, 7, 10), box(0, 0, 3, 10), CRS)
    water_cells = [box(x, 0, x + 1, 10) for x in range(10)]
    parts = [boundaries.cell_areas(water, water_crs=CRS) for water in water_cells]
    splits = [part.split_water_total(20) for part in parts]  # 2 units / m²
    assert math.fsum(p.inside_vsr_m2 for p in parts) == 30
    assert math.fsum(p.outside_vsr_m2 for p in parts) == 40
    assert math.fsum(p.excluded_domain_m2 for p in parts) == 30
    assert (
        math.fsum(s.inside_vsr + s.outside_vsr + s.excluded_domain for s in splits)
        == 200
    )
    coarse = boundaries.cell_areas(box(0, 0, 10, 10), water_crs=CRS).split_water_total(
        200
    )
    assert math.fsum(s.inside_vsr for s in splits) == coarse.inside_vsr == 60
    assert math.fsum(s.outside_vsr for s in splits) == coarse.outside_vsr == 80
    assert math.fsum(s.excluded_domain for s in splits) == coarse.excluded_domain == 60


@pytest.mark.parametrize("invalid", [None, -1, float("nan"), float("inf"), True])
def test_missing_or_invalid_total_is_never_zero(invalid):
    areas = ExposureBoundaries(CELL, CELL, CRS).cell_areas(CELL, water_crs=CRS)
    with pytest.raises(ValueError, match="finite and nonnegative"):
        areas.split_water_total(invalid)


@pytest.mark.parametrize(
    "geometry",
    [
        LineString([(0, 0), (1, 1)]),
        Polygon([(0, 0), (2, 2), (0, 2), (2, 0)]),
        Polygon([(0, 0, 1), (1, 0, 1), (1, 1, 1)]),
    ],
)
def test_invalid_or_non_area_water_fails(geometry):
    with pytest.raises(ValueError):
        ExposureBoundaries(CELL, CELL, CRS).cell_areas(geometry, water_crs=CRS)


def test_wrong_crs_and_inconsistent_areas_fail():
    with pytest.raises(ValueError, match="EPSG:3310"):
        ExposureBoundaries(CELL, CELL, "EPSG:4326")
    with pytest.raises(ValueError, match="EPSG:3310"):
        ExposureBoundaries(CELL, CELL, CRS).cell_areas(CELL, water_crs="EPSG:4326")
    with pytest.raises(ValueError, match="conserve"):
        CellAreas(100, 50, 40, 20, 50)


def test_numerical_overlay_residual_is_retained_not_repaired():
    # Polygon overlays can differ by a few ulps even for containment. Apply
    # the same declared numerical tolerance to conservation and nesting.
    residual = 1e-8
    areas = CellAreas(
        25_000_000, 25_000_000 + residual, 10_000_000, 15_000_000 + residual, 0
    )
    assert areas.qualified_m2 > areas.water_m2
    with pytest.raises(ValueError):
        CellAreas(25_000_000, 25_000_001, 10_000_000, 15_000_001, 0)


def test_local_loader_refuses_unverified_bytes_without_writing(tmp_path):
    domain = tmp_path / "domain.parquet"
    snapshot = tmp_path / "vsr.geojson"
    domain.write_bytes(b"unverified")
    snapshot.write_bytes(b"unverified")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_local_boundaries(domain, snapshot)
    assert domain.read_bytes() == snapshot.read_bytes() == b"unverified"
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "domain.parquet",
        "vsr.geojson",
    ]
