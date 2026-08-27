# 0004 — Use a 5 km analysis grid with fractional VSR-boundary accounting

**Status:** Accepted
**Date:** 2026-08-25, revised 2026-08-26

> Revised after an audit. The 5 km grid is unchanged. What changed is the
> method for handling cells that straddle the VSR boundary: the original record
> discussed *assigning* such cells to one side, which would have made the
> headline statistic an artefact of the grid. Fractional area accounting is now
> required, and the case for 5 km is restated on the grounds that survive it.

## Context

[Architecture](../architecture.md) deferred the analysis-grid resolution until the native resolutions of the real inputs were known. They now are, and they differ by two orders of magnitude:

| Input | Native resolution |
|---|---|
| Blue-whale model | 0.1° equal-angle cells — **9.12 to 9.44 km east–west and 11.06 km north–south** across the study area |
| AIS broadcast points | Point positions, roughly one per minute per moving commercial vessel |
| VSR zone polygon | A vector boundary, 37,239 vertices, effectively exact at any grid size |

The whale model is the coarsest input and sets the ceiling on how much spatial detail the combined result can honestly claim.

Cell counts over the 107,293 km² of water in the proposed map extent ([ADR 0002](0002-southern-california-study-area-extent.md)):

| Cell size | Water cells |
|---|---|
| 10 km | ≈ 1,073 |
| 5 km | ≈ 4,292 |
| 2.5 km | ≈ 17,167 |
| 2 km | ≈ 26,823 |
| 1 km | ≈ 107,293 |

**The audit's finding.** The first version of this record justified 5 km largely on the grounds that it reduced the damage done by assigning a whole boundary cell to one side of the zone. That reasoning accepted a bad method and then tuned a parameter to limit the harm. Whole-cell or centroid assignment makes the inside/outside split depend on where the grid happens to start and how big the cells happen to be — properties of the analyst's choices, not of the data. Halving the cell size reduces that sensitivity; it does not remove it, and it leaves the headline number carrying an arbitrary component that no sensitivity check can fully characterise.

The VSR polygon is exact. There is no reason to discretise it.

## Decision

### Grid

The analysis grid is **5 km × 5 km cells in EPSG:3310** ([ADR 0003](0003-projected-coordinate-system.md)), aligned to whole 5,000 m multiples of the projected coordinate system.

The grid covers x −190,000 to 285,000 and y −670,000 to −330,000 — 95 columns by 68 rows, 6,460 cells, of which roughly 4,292 contain water. Snapping the origin to round 5,000 m multiples means the grid is reproducible from the cell size alone and stays aligned if the extent is adjusted.

### Boundary accounting — fractional, not categorical

Every statistic that divides the study area by the VSR boundary is computed from **actual intersected polygon areas**, by this sequence:

1. Intersect each analysis cell with the **water mask**. Call the result the cell's *water geometry*; its area is the cell's water area. A cell with no water contributes nothing and is skipped — it is never a divide-by-zero.
2. Intersect the water geometry with the **VSR polygon**. The area of that intersection is the cell's *inside area*; the remainder of the water geometry is its *outside area*.
3. Derive `f_in = inside area / water area` and `f_out = 1 − f_in`.
4. Split the cell's exposure total as `E × f_in` inside and `E × f_out` outside. **Do not** assign the whole of `E` to either side.
5. Compute high-exposure **area** statistics from the intersected polygon areas themselves, not from cell counts multiplied by a nominal cell size.

**A boundary cell is never classified by its centroid, and never by which side holds the majority of its area.** Both discard the fraction that makes the result stable.

All intersections happen in EPSG:3310 so the areas are equal-area.

### The assumption this introduces, stated plainly

Splitting a cell's exposure by area fraction assumes **exposure is uniform within the cell.** It is not — exposure is a derived quantity varying continuously, and the grid is a discretisation of it. For a cell that is 30% inside the zone, this treats 30% of its exposure as inside, which is exact only if the exposure is evenly spread across the cell's water.

This assumption is why the cell size still matters after fractional accounting is adopted: **it is an assumption over one cell's area, so smaller cells make it milder.** At 10 km it spans 100 km²; at 5 km, 25 km². That, and not edge assignment, is now the principal argument for 5 km over the whale model's native ~10 km.

The assumption is labelled wherever a boundary-derived statistic is reported, per the project brief's rule on assumptions.

### Planned verification

Not yet implemented — the analysis package now has a tested foundation, but it
deliberately does not include grid generation or fractional-boundary machinery.
These cases remain the target for the later grid/analysis slice, and are written
in EPSG:3310 metres with answers known by construction.

Let cell `C` be the square from (0, 0) to (5000, 5000): area 25,000,000 m².

| Case | Water mask | VSR polygon | Expected |
|---|---|---|---|
| **1 — plain fraction** | all of `C` | `x ≤ 1500` | water area 25,000,000; inside 7,500,000; `f_in` = **0.30** exactly. Exposure 100 splits 30 / 70 |
| **2 — the fraction is of water, not of cell** | `x ≥ 1000` within `C` (water area 20,000,000) | `x ≤ 2000` | inside 5,000,000; `f_in` = **0.25**. A cell-area denominator would give 0.40, so this case fails loudly if the water mask is skipped |
| **3 — centroid and majority both fail** | all of `C` | `x ≤ 2250` | `f_in` = **0.45**. `C`'s centroid is (2500, 2500), which is outside, so centroid assignment yields 0.00; majority-area assignment also yields 0.00 since 0.45 < 0.5. Only fractional accounting gives 0.45 |
| **4 — dry cell** | empty | any | cell is skipped; no exception, no contribution |
| **5 — conservation** | any | any | over all cells, `Σ(E × f_in) + Σ(E × f_out) = ΣE` to floating-point tolerance, and `f_in + f_out = 1` per cell |

Case 3 is the one that matters most: it is a cell nearly half inside the zone that both discarded methods score as entirely outside.

## Consequences

- **The headline inside/outside split stops depending on grid origin.** Shifting the grid by half a cell changes which cells straddle the boundary but not the total area on each side, so the reported figure moves only through the uniformity assumption rather than through reassignment.
- The 5 km versus 10 km **sensitivity check stays in the analysis milestone**, but its meaning changes. It no longer measures edge-assignment noise; it measures how much the uniform-within-cell assumption is worth. It is **not** a substitute for fractional accounting, and reporting a sensitivity range would not excuse a categorical method.
- Intersecting every cell with two polygons is more work than a point-in-polygon test on 4,292 centroids. At this scale that is irrelevant; the VSR polygon has 37,239 exterior vertices, so the implementation should prepare or index it rather than intersect naively.
- **5 km is finer than the whale model, and that does not create whale information.** Each analysis cell takes an area-weighted share of the abundance of the ~10 km source cells it falls within, so four analysis cells inside one source cell carry near-identical whale values. The grid resolves the boundary and the water mask, not the biology, and the application must not present it as though the whale model resolves 5 km detail.
- 4,292 water cells is a comfortable hosted-layer size — small enough to publish without generalisation, which keeps the published layer and the analysed layer identical.
- The vessel input is aggregated **down** to 5 km from point positions, discarding detail AIS genuinely has. That is the correct direction: the combined layer cannot be more precise than its coarsest input.
- **The water mask becomes load-bearing.** Case 2 exists because an error there silently changes every fraction. Whatever supplies the mask has to be stated and inspected, and it interacts with the unresolved analytical-domain question in [ADR 0002](0002-southern-california-study-area-extent.md), since a coverage restriction would be applied in the same step.

## Alternatives considered

**Whole-cell or centroid assignment at any resolution.** Rejected — this is the audit finding. It makes a reported number depend on grid origin and cell size, and case 3 shows a cell 45% inside the zone being scored entirely outside. No amount of resolution or sensitivity reporting repairs that.

**Majority-area assignment.** Rejected. Better than centroid, since it at least looks at area, but it still collapses a fraction to a binary and fails case 3 identically.

**10 km, matching the whale model's native resolution.** The most conservative option on resolution grounds: it claims no more spatial detail than the coarsest input has. Rejected because the uniform-within-cell assumption would then span 100 km², and because the water mask and coastline would be represented coarsely enough to distort the area denominators that fractional accounting depends on. It remains the natural comparison point for the sensitivity check.

**2 km or finer.** Rejected. It would soften the uniformity assumption further and represent the coastline better, but 26,823 cells carrying whale values constant across each ~25-cell block is false precision made visible, and it multiplies the published layer for no analytical gain.

**1 km.** Rejected. 107,293 cells is a hosted-layer problem as well as a false-precision problem, and it is a hundredfold finer than the biological input.

**Abandon the grid and compute statistics directly on intersected polygons.** Rejected for Version 1, though it is the logical endpoint of fractional accounting. A regular grid is what makes the exposure surface mappable, comparable between inputs, and publishable as a single layer. Fractional accounting already recovers most of the precision a polygon-only method would offer, at the boundary where it matters.

**A variable or nested grid — finer near the zone boundary, coarser offshore.** Rejected for Version 1. Fractional accounting removes most of the motivation for it, and it would complicate every area-weighted statistic and every legend.
