# 0014 — Use the NOAA whale-model footprint as the grid water mask

**Status:** Accepted
**Date:** 2026-08-27

## Context

[ADR 0004](0004-analysis-grid-resolution.md) makes actual per-cell water area a
load-bearing input to later fractional boundary accounting. A nominal 25 km²
cell area is not sufficient at the coast or around islands. The mask that
creates those water geometries therefore has to be selected explicitly.

Three different concepts could otherwise be conflated:

- the **biological support** of the selected NOAA whale model: its land-clipped
  polygons identify where that modeling product provides a value;
- an **authoritative shoreline/water mask** intended to represent the physical
  land-water boundary; and
- a future **AIS observability or reporting-domain mask** describing where the
  land-receiver vessel input can support analysis.

They answer different questions. In particular, proposed
[ADR 0002](0002-southern-california-study-area-extent.md) still needs an
authoritative coastline before it can define a distance-from-shore AIS coverage
treatment. Using the observed edge of the whale model for that purpose would
turn a modeling-product coastline into a claim about radio coverage.

The inspected NOAA 2020b `Blue_whale_summer_fall` layer contains 12,257 valid
MultiPolygon features in EPSG:4326. NOAA clipped the model cells to its water
footprint: land and islands are absent and coastline slivers remain. The source,
retrieval method, archive size and SHA-256, CRS, redistribution assessment, and
model limitations are already verified in
[`data-sources.md`](../data-sources.md#1-modeled-blue-whale-distribution).

No separate authoritative shoreline artifact has been registered or inspected
for this project. Selecting one now solely to construct this grid would add a
second coastline whose relation to the biological surface would itself need a
rule: cells marked as water by the shoreline but lacking a whale-model value
could not enter later overlap calculations without inventing a biological
value.

## Decision

Version 1 uses the **polygon union of the selected NOAA 2020b
`Blue_whale_summer_fall` layer as the analysis-grid water mask**.

This is accepted as a decision about the support of the biological input, not
as a finding that the footprint is an authoritative shoreline. It means a
retained grid-water geometry answers: “what portion of this 5 km cell is inside
the land-clipped area where the selected whale modeling product supplies
values?”

The processing API remains mask-agnostic. It requires an explicit input path,
layer where applicable, and declared source CRS, and validates the embedded CRS
and every geometry before use. The selected NOAA layer is supplied through that
boundary at runtime; its location is not embedded in code.

The grid water mask remains separate from any AIS observability, analytical-
domain, or reporting-domain mask. ADR 0002 remains Proposed. The grid is
generated over the accepted map/context bounds: its exact ADR 0004 origin and
indices are preserved, while the biological-support mask is clipped to a
densified EPSG:3310 projection of the configured WGS84 −122° to −117°, 32° to
35° polygon before cell intersection. Neither this decision nor the resulting
4,516 retained water cells accepts that full footprint as a statistical domain.

The geographic rectangle is not projected from four corners alone. Each edge
is deterministically subdivided into segments no longer than 0.01° (roughly one
kilometre at this latitude) before projection so the curved projected boundary
is represented adequately relative to 5 km cells. The segment limit,
geographic and projected bounds, transformation, and 0.1 m² outside-area
tolerance are recorded in dataset metadata.

## Consequences

- Every retained cell has a whale-model support area by construction. Later
  whale transfer does not need to invent values outside the source footprint.
- The grid inherits the modeling product's treatment of coastlines and islands.
  It must be described as a **modeling-product coastline**, never as an
  authoritative shoreline or exact ocean area.
- Apparent coastal detail is limited by how NOAA clipped the approximately
  0.1° source cells. The 5 km intersections refine the arithmetic of the mask
  boundary; they do not create 5 km biological resolution.
- A future authoritative shoreline remains necessary if ADR 0002 chooses a
  distance-from-coast AIS observability treatment. Adding that source does not
  supersede this biological-support decision; it creates a separate coverage
  mask with separate provenance and meaning.
- A future AIS mask must not erase or relabel grid water geometry. It is an
  additional per-cell qualification applied later, so readers can distinguish
  “outside whale-model support” from “outside defensible AIS coverage.”
- The NOAA redistribution assessment supports local derivation and later
  publication with citation, subject to the limitations already recorded in
  the source register.
- The corrected real smoke run produced 4,516 retained cells and
  107,728.695924 km² of model-footprint water inside the configured context
  extent. It removed 25 cells and 2,970.781272 km² that the earlier grid-bounds-
  only implementation retained outside that extent. Programmatic geometry and
  read-back checks passed. On 2026-08-27, headless QGIS 4.2.1 with GDAL 3.13.2
  opened the exact GeoParquet directly and rendered five views against
  OpenStreetMap, the NOAA source footprint, and the configured context polygon.
  Inspection confirmed the correct Southern California location and axis order,
  source alignment, boundary clipping, plausible coastline/island gaps, correct
  grid orientation, and no unexplained geometry or projection artifacts. The
  inspected output SHA-256 was
  `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`.

## Alternatives considered

**Register and use an authoritative shoreline now.** Not selected for this
grid. It would better represent physical land and water, but it would also
create areas with water geometry and no whale-model support. No candidate has
been inspected or registered, so choosing one in this slice would silently add
a source and an untested rule. An authoritative shoreline remains required for
the distinct ADR 0002 coverage question.

**Treat the whale footprint as provisional until a shoreline is selected.**
Rejected. The grid mask has a stable, defensible role independent of physical
shoreline authority: it represents where the biological product exists. Calling
that role provisional would obscure rather than reduce the distinction.

**Use the VSR polygon's land-clipped geometry as the water mask.** Rejected. The
zone is a management boundary, covers only part of the map, and has unresolved
redistribution permission. It cannot define the outside-zone water needed by
the project.

**Use AIS point presence or density as a water/coverage mask.** Rejected. A
vessel point is neither a shoreline observation nor evidence that unobserved
water lacks coverage. This would make the coverage reasoning circular in the
same way ADR 0002 already rejects.
