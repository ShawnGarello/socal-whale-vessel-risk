# 0002 — Southern California study area extent

**Status:** Accepted
**Date:** 2026-08-25

## Context

[Architecture](../architecture.md) deferred the study-area extent until data discovery could establish what the inputs actually cover. Discovery (M2) has now inspected all three, and the constraints are known:

- **The blue-whale model** covers longitude −131 to −117.10 and latitude 30.05 to 48.51, clipped to water. It covers everything Southern California needs, so it does not constrain the extent.
- **The 2026 VSR zone** is a single statewide polygon of 142,155 km². Its Southern California portion — the part south of 35°N — is 56,011 km², 39.4% of the zone. Its bounds there are longitude −122.07 to −117.10, latitude 32.55 to 35.0.
- **AIS coverage is the binding constraint.** NOAA states coverage is unavailable "for waters extending more than 40 to 50 miles from the coast", and the inspected sample confirms it: in a 34-minute Southern California snapshot there were 13,380 records east of −120.5 and only 103 west of it.

The research question requires a meaningful **outside** as well as a meaningful **inside**, so the study area cannot simply be the zone. It also has to be described honestly: any extent that captures most of the zone necessarily reaches into water where AIS coverage is thin.

Three candidates were measured. Water area was computed using the blue-whale model's own coverage as the water mask — it is already land- and island-clipped, and using it keeps the analysis domain identical to the domain of the biological input. Areas are in EPSG:3310.

| Candidate | Water area | Inside zone | Outside zone | % inside | Share of the zone south of 35.3°N captured |
|---|---|---|---|---|---|
| A: lon −121.0 to −117.0, lat 32.0 to 35.0 | 76,629 km² | 44,891 km² | 31,738 km² | 58.6% | 73.9% |
| **B: lon −122.0 to −117.0, lat 32.0 to 35.0** | **107,293 km²** | **55,901 km²** | **51,392 km²** | **52.1%** | **92.0%** |
| C: lon −122.5 to −117.0, lat 32.0 to 35.2 | 126,279 km² | 59,070 km² | 67,209 km² | 46.8% | 97.2% |

## Decision

The Version 1 study area is the geographic box **longitude −122.0 to −117.0, latitude 32.0 to 35.0** (WGS 84), restricted to water as defined by the blue-whale model's coverage.

Candidate B is chosen because it captures 92% of the zone's Southern California extent while leaving 51,392 km² of water outside the zone — an inside/outside split of 52/48, close enough to balanced that the comparison is not dominated by one side. Candidate A leaves too little of the zone in (74%) and skews inside. Candidate C buys the last five points of zone coverage with a further 15,800 km² of offshore water where AIS coverage is weakest, which degrades the vessel input more than it improves the management comparison.

The boundaries are whole degrees deliberately. Nothing in the data privileges a particular cut, and a round box is easier to state, reproduce, and check than one fitted to a coastline or a zone edge.

## Consequences

- The analysis reports on the **Southern California portion of the 2026 VSR zone, not the whole zone.** Every inside/outside statistic must say so. It is not a statewide result and must never be described as one.
- The study area **truncates the zone at 35.0°N**, where the zone continues north. Exposure near that northern edge is a boundary artefact of the study area, not a feature of the zone, and results should not be read across it.
- **The western part of the study area is in thin AIS coverage.** Roughly the band west of −120.5 will show low vessel activity that reflects receiver range at least as much as vessel behaviour. This has to be stated wherever an offshore result appears, and it is the single most likely way a reader could be misled by the map.
- Using the whale model's coverage as the water mask means the analysis domain and the biological input have identical footprints, so no cell can carry vessel activity without a whale value. It also means the study area inherits the model's coastline, which is a modelling product rather than an authoritative shoreline.
- If the AIS coverage limitation later proves more severe than the sample suggests, the western boundary is the thing to move, and this record is superseded.

## Alternatives considered

**Candidate A (−121.0 west edge).** Rejected. Keeps the analysis inside well-covered AIS water, which is genuinely attractive, but captures only 74% of the zone's Southern California area and skews the inside/outside split to 59/41. The research question is about the zone, so cutting a quarter of it out of the study area weakens the answer more than the cleaner vessel data strengthens it.

**Candidate C (−122.5 west edge, 35.2°N north edge).** Rejected. Captures 97% of the zone but adds a large offshore area where the vessel input is least trustworthy, pushing the inside share below half and making the "outside" result increasingly a statement about AIS coverage.

**Fitting the study area to the zone plus a fixed buffer.** Rejected. A buffer distance would be an arbitrary parameter with no evidence behind it, and a study area whose shape follows the zone makes the inside/outside comparison harder to interpret, not easier, because the outside region would be a thin uniform collar rather than real adjacent water.

**Extending north to Point Conception or beyond to include the full zone.** Rejected for Version 1. The question is scoped to Southern California, and the volume of AIS involved scales directly with area.
