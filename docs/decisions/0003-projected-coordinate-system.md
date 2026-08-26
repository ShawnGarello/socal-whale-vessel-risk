# 0003 — Use California Albers (EPSG:3310) as the analysis projection

**Status:** Accepted
**Date:** 2026-08-25

## Context

[Architecture](../architecture.md) deferred the projected coordinate system until the inputs were known. All three are now inspected, and none of them arrives projected:

- The **blue-whale model** is EPSG:4326, on a 0.1° equal-angle grid. Its cells are not equal-area: `AREA_SQKM` averages 105.4 km² at 30–31°N and 82.7 km² at 48–49°N, and varies measurably even across the study area.
- The **VSR zone** is served in EPSG:3857 and was requested as EPSG:4326.
- **AIS records** are decimal degrees, WGS 84.

So the analysis has to project, and the choice matters more here than in a typical mapping project for one specific reason: **Version 1's headline outputs are area-based ratios.** The project brief requires the share of total relative exposure inside versus outside the zone, and the share of high-exposure *area* inside versus outside. The biological input is a density — animals per km². Any projection that distorts area distorts those numbers directly, and does so differently in different parts of the study area, which is the hardest kind of error to notice on a map.

The study area spans longitude −122.0 to −117.0, which straddles the UTM zone 10N/11N boundary at −120°.

## Decision

All analysis is performed in **EPSG:3310, NAD83 / California Albers Equal Area**.

Specifically:

- Every input is reprojected to EPSG:3310 before clipping, gridding, area computation, or any statistic is derived from it.
- The analysis grid ([ADR 0004](0004-analysis-grid-resolution.md)) is defined in EPSG:3310.
- All reported areas and area-based shares are computed in EPSG:3310.
- Layers published for display may be reprojected to EPSG:3857 as the web map requires. **Display reprojection happens after the numbers are computed, never before.** No statistic is ever derived from the Web Mercator copy.

The study area's projected bounds are x −189,429 to 284,118, y −667,727 to −330,859 — 473.5 km by 336.9 km.

## Consequences

- Area-based statistics are trustworthy. This is the whole point of the choice.
- Transferring the blue-whale model onto the analysis grid must be **area-weighted and must conserve abundance** — `DENSITY` × cell area — rather than averaging density, because the source cells are equal-angle and their ground areas differ. Reprojecting to an equal-area system makes that transfer correct; it does not make it automatic, and the processing milestone has to do it explicitly.
- **Datum note:** EPSG:3310 is NAD83 while the source data are WGS 84. The difference in California is on the order of 1–2 metres. Against a 5 km analysis grid that is about 0.03% of a cell, and against AIS positions it is far below the data's own error. It is recorded here as considered and negligible, not ignored.
- The projection is valid for California and nothing else. If the project ever extends beyond the California Current it needs a different projection and a record superseding this one.
- Web Mercator is now explicitly a presentation format in this project. Anyone computing a number from a displayed layer is doing it wrong, and this record is what that claim rests on.

## Alternatives considered

**UTM zone 10N or 11N (EPSG:26910 / 26911).** Rejected. The study area straddles −120°, the boundary between the two zones, so either choice puts roughly half the Southern California Bight in a zone it does not belong to, with growing scale distortion toward the far edge. UTM is also conformal, not equal-area, which is the wrong property for this analysis. Its advantage — metres, and familiarity — is shared by California Albers.

**Web Mercator (EPSG:3857).** Rejected for analysis. It is what the web map uses, and the temptation to compute in the display projection is exactly the failure this record exists to prevent. Web Mercator's area distortion at 32–35°N is roughly 40% and varies with latitude, so an area share computed in it would be wrong by an amount that changes across the study area.

**Working in geographic coordinates and computing areas geodesically.** Rejected. It is defensible for area alone, but a regular analysis grid in degrees produces cells of unequal ground area — the same problem the whale model already has — which would then have to be corrected in every subsequent step rather than once, at the start.

**California Albers on the NAD83(2011) realisation, or a WGS 84 Albers definition.** Not pursued. The 1–2 m difference is immaterial at this grid resolution, and EPSG:3310 is the standard, widely recognised choice for statewide California work, which matters for a project meant to be checked by others.
