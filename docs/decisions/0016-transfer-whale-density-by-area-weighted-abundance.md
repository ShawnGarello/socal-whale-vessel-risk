# 0016 — Transfer whale density by area-weighted abundance

**Status:** Accepted
**Date:** 2026-08-27

## Context

The selected NOAA/SWFSC blue-whale surface is a land-clipped vector grid in
EPSG:4326. Its approximately 0.1° cells carry modeled density in animals per
km², source-cell area, modeled abundance, and a coefficient of variation. The
target is the accepted 5 km EPSG:3310 grid whose retained rows contain the
actual water geometry and water area supported by that same modeling product.

The source and target grids are not aligned, and the equal-angle source cells
have different ground areas. Averaging density values or assigning a source
value by target-cell centroid would not conserve modeled abundance. The
transfer also has to expose gaps and source-polygon overlaps: silently treating
uncovered water as zero or summing overlapping source interiors could create a
plausible but incorrect surface.

The source provides a coefficient of variation for each native model cell, but
no scientifically supported rule has been established for propagating those
values through split and recombined polygons.

## Decision

Transfer the selected `Blue_whale_summer_fall` surface to the existing water
grid by **abundance-conserving area weighting** in EPSG:3310:

1. Validate the source through the versioned NOAA/SWFSC whale-input contract
   and validate the target through the versioned projected-water-grid contract.
2. Reproject source polygons from EPSG:4326 to EPSG:3310 with longitude and
   latitude explicitly treated as x and y.
3. Reject missing, non-finite, or negative modeled density. Reject any
   projected source-interior overlap larger than 1 m². Positive-area residuals
   at or below 1 m² are treated as projection/topology tolerances, but their
   pair count and total area are retained in output metadata and lineage rather
   than silently ignored. Boundary contact with zero intersection area is
   allowed.
4. Intersect each source polygon with each target cell's actual water geometry.
   For every positive-area intersection, calculate
   `source DENSITY × overlap area in km²`.
5. Sum those contributions as the target cell's modeled abundance allocation,
   in animals. Divide that allocation by the target cell's full water area in
   km² to obtain target-cell modeled density in animals per km².
6. Retain covered water area, uncovered water area, coverage fraction, and a
   coverage status that distinguishes complete support, a numerical residual
   within tolerance, and an incomplete gap. Do not silently fill a gap.
7. Verify that summed target allocations equal the source contribution within
   the target water domain. The implementation uses deterministic summation and
   requires both an absolute tolerance of `1e-9` animals and a relative
   tolerance of `1e-10`; diagnostics retain the actual difference.

The versioned whale-grid output preserves `cell_id`, row and column indices,
parent bounds, water areas, and exact water geometry from the target grid. Rows
remain in the grid's documented south-to-north, west-to-east order. Generation
lineage records both input checksums, transformation and tolerance parameters,
software versions, validation and intersection counts, coverage and
conservation diagnostics, and the output checksum.

The transfer does **not** propagate or aggregate `UNCERTAINTY` into a new
coefficient of variation. Native uncertainty remains a source-layer property
until a scientifically supported propagation method is established.

## Consequences

- Modeled abundance contributed inside the target water domain is conserved
  rather than changed by grid alignment.
- Coastal and partial source cells contribute according to their actual
  projected geometry and the target's actual water geometry.
- Coverage gaps and numerical residuals remain visible per cell and in lineage.
- Rejecting material positive-area source overlap prevents unexplained double
  counting; a future source with intentional overlapping model components
  would need a separate combination rule and decision.
- The 5 km output changes the **reporting grid only**. It is not a new 5 km
  biological model and does not add precision beyond the approximately 0.1°
  source model. Adjacent target cells may share very similar values because
  they inherit information from the same coarser source cell.
- Dividing by full target water area means an incomplete-support cell's modeled
  density reflects the explicit uncovered area rather than renormalizing the
  covered portion. Coverage fields must accompany that value wherever it is
  used.
- This whale-input contract does not choose an analytical/reporting domain,
  normalize values to 0–1, define relative exposure, choose weights or hotspot
  thresholds, or calculate VSR statistics.
- The real source scan found three positive-area pairs totaling
  0.311235765 m²; two were near machine precision and none exceeded 1 m². The
  accepted 1 m² tolerance is 0.000004% of one nominal 25 km² target cell. These
  residuals remain reported while contributions follow the source polygons as
  stored; the method does not invent an unsupported rule for assigning a
  sub-square-metre residual to one source value.

## Alternatives considered

**Average intersecting source densities.** Rejected. It weights source cells by
count rather than area and does not conserve modeled abundance.

**Assign the source value at the target centroid.** Rejected. It ignores
partial and coastal intersections and makes the result depend on grid
alignment.

**Allocate source `ABUNDANCE` by overlap fraction of published `AREA_SQKM`.**
Not selected. The inspected source establishes that `ABUNDANCE` is derived as
`DENSITY × AREA_SQKM`; computing contribution directly from density and area in
the accepted equal-area CRS keeps all transfer geometry and area arithmetic in
one coordinate system while the source contract still checks that published
relationship.

**Renormalize each incomplete target cell by covered area.** Rejected. It would
hide missing support and inflate a partial contribution as though the entire
water cell were covered.

**Propagate coefficient of variation by area weighting.** Rejected. A
coefficient of variation is not additive, and the source does not provide the
covariance information or a cited rule needed to combine it defensibly.
