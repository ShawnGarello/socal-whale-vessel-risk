# 0004 — Use a 5 km analysis grid

**Status:** Accepted
**Date:** 2026-08-25

## Context

[Architecture](../architecture.md) deferred the analysis-grid resolution until the native resolutions of the real inputs were known. They now are, and they differ by two orders of magnitude:

| Input | Native resolution |
|---|---|
| Blue-whale model | 0.1° equal-angle cells — **9.12 to 9.44 km east–west and 11.06 km north–south** across the study area |
| AIS broadcast points | Point positions, roughly one per minute per moving commercial vessel |
| VSR zone polygon | A vector boundary, 37,239 vertices, effectively exact at any grid size |

The whale model is the coarsest input by far and therefore sets the ceiling on how much spatial detail the combined result can honestly claim. But the *floor* is set by something else: the headline statistic is an inside-versus-outside split against a polygon boundary, and a boundary-sensitive statistic computed on a grid whose cells are larger than the features they straddle is dominated by how cells are assigned at the edge.

Cell counts over the study area's 107,293 km² of water ([ADR 0002](0002-southern-california-study-area-extent.md)):

| Cell size | Water cells |
|---|---|
| 10 km | ≈ 1,073 |
| 5 km | ≈ 4,292 |
| 2.5 km | ≈ 17,167 |
| 2 km | ≈ 26,823 |
| 1 km | ≈ 107,293 |

## Decision

The analysis grid is **5 km × 5 km cells in EPSG:3310** ([ADR 0003](0003-projected-coordinate-system.md)), aligned to whole 5,000 m multiples of the projected coordinate system.

The grid covers x −190,000 to 285,000 and y −670,000 to −330,000 — 95 columns by 68 rows, 6,460 cells, of which roughly 4,292 contain water.

Snapping the origin to round 5,000 m multiples rather than to the study-area bounding box means the grid is reproducible from the cell size alone, and stays aligned if the extent is ever adjusted.

## Consequences

- **5 km is finer than the whale model, and that is deliberate — but it does not create whale information.** Each analysis cell takes an area-weighted share of the abundance of the roughly 10 km source cells it falls within. Four analysis cells inside one source cell will carry near-identical whale values. The grid resolves the *boundary*, not the biology, and the application must not present it as though the whale model resolves 5 km detail.
- The inside/outside statistic is far less sensitive to edge assignment than it would be at 10 km, where a single cell straddling the zone boundary covers 100 km².
- 4,292 water cells is a comfortable size for a hosted feature layer — small enough to publish and draw without generalisation, which keeps the published layer and the analysed layer identical.
- The vessel input is aggregated **down** to 5 km from point positions, discarding detail the AIS data genuinely has. That is the correct direction: the combined layer cannot be more precise than its coarsest input, and presenting vessel detail the whale model cannot match would misrepresent the result.
- Choosing 5 km rather than the native ~10 km is a **choice, not a data property.** It should be included in the sensitivity check the analysis milestone performs, alongside the high-exposure threshold — if the inside/outside share moves materially between a 5 km and a 10 km grid, that is a result worth reporting rather than hiding.

## Alternatives considered

**10 km, matching the whale model's native resolution.** The most conservative option, and genuinely defensible: it claims no more resolution than the coarsest input has. Rejected because the headline output is an inside/outside split against a polygon boundary, and at 10 km a single boundary cell spans 100 km² — roughly 0.2% of the study area's water in one cell's assignment decision. The blockiness would also be plainly visible against the zone boundary on the map, inviting exactly the misreading the project is trying to avoid.

**2 km or finer.** Rejected. It would represent the boundary and coastline better still, but 26,823 cells carrying whale values that are constant across each ~25-cell block is false precision made visible, and it multiplies the published layer size for no analytical gain.

**1 km.** Rejected. 107,293 cells is a hosted-layer problem as well as a false-precision problem, and it is a hundredfold finer than the biological input.

**A variable or nested grid — finer near the zone boundary, coarser offshore.** Rejected for Version 1. It would give the best of both, but it complicates every area-weighted statistic and every legend, and there is no evidence yet that the uniform grid is inadequate. Worth revisiting only if the sensitivity check shows the boundary assignment actually matters.
