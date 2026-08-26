# 0002 — Southern California study area extent

**Status:** Proposed
**Date:** 2026-08-25, reopened 2026-08-26

> This record was briefly marked Accepted. An audit found that the evidence
> behind it did not support accepting a single extent for both mapping and
> statistics, and it was returned to Proposed rather than patched. The map
> extent below is settled enough to build against. **The analytical domain is
> not, and no headline inside-versus-outside statistic may be published until
> it is.**

## Context

[Architecture](../architecture.md) deferred the study-area extent until data discovery could establish what the inputs actually cover. Discovery inspected all three. Two of them constrain nothing:

- **The blue-whale model** covers longitude −131 to −117.10 and latitude 30.05 to 48.51, clipped to water. It covers everything Southern California needs.
- **The 2026 VSR zone** is a single statewide polygon of 142,155 km². Its portion south of 35°N is 56,011 km², bounded by longitude −122.07 to −117.10 and latitude 32.55 to 35.0.

**The vessel input is the problem.** NOAA states that this AIS product comes from roughly 200 land-based receiving stations and that *"coverage is currently unavailable for … waters extending more than 40 to 50 miles from the coast."* There is no satellite AIS in the product. Forty to fifty miles is roughly 64–80 km, and the Southern California portion of the VSR zone reaches several hundred kilometres offshore at its western vertex.

Three candidate extents were measured, using the whale model's own water coverage as the water mask. Areas in EPSG:3310:

| Candidate | Water area | Inside zone | Outside zone | % inside | Share of the zone south of 35.3°N captured |
|---|---|---|---|---|---|
| A: lon −121.0 to −117.0, lat 32.0 to 35.0 | 76,629 km² | 44,891 km² | 31,738 km² | 58.6% | 73.9% |
| B: lon −122.0 to −117.0, lat 32.0 to 35.0 | 107,293 km² | 55,901 km² | 51,392 km² | 52.1% | 92.0% |
| C: lon −122.5 to −117.0, lat 32.0 to 35.2 | 126,279 km² | 59,070 km² | 67,209 km² | 46.8% | 97.2% |

**What the audit found.** The original version of this record chose candidate B and treated the AIS sample as having confirmed the coverage limitation. It had not. The sample shows that only 1.71% of Southern California records lie west of −120.5, which is *consistent with* the published limitation — but a snapshot of record density cannot distinguish "few ships are here" from "few ships here are heard", and those two explanations imply opposite analytical treatments. Under the first, an offshore result is real. Under the second, it is an artefact, and mapping it would show empty water where traffic may in fact exist.

The gap is not marginal. Within candidate B:

| | Water area | Share of candidate B | VSR zone area affected |
|---|---|---|---|
| East of −120.5 | 61,857 km² | 57.7% | 36,552 km² |
| **West of −120.5** | **45,436 km²** | **42.3%** | **19,349 km² — 34.6% of the in-box zone** |

So roughly two-fifths of the proposed analytical water, holding a third of the in-box zone, sits where the vessel input's trustworthiness is unestablished. A statistic computed over all of it would be a statement partly about ships and partly about radio range, with no way for a reader to tell which.

**A meridian is also the wrong shape for the question.** −120.5 is used above only because it is where the sampled records thin out. The actual constraint is distance from shore, and the Southern California coastline bends sharply west of Point Conception, so a longitude cut is a crude proxy for it. Any accepted nearshore domain needs a real distance-from-coastline criterion, not a line of longitude.

## Decision

**Three different things were previously bundled into one extent. They are separated here, and only the first is settled.**

### 1. Map and context extent — proposed, and safe to build against

**Longitude −122.0 to −117.0, latitude 32.0 to 35.0** (WGS 84) — candidate B.

This is what the application shows: the basemap window, the layer extents, and the initial camera. It captures 92% of the Southern California portion of the VSR zone, so a visitor sees the management area in its regional context rather than a fragment of it. Whole degrees are used deliberately; nothing in the data privileges a particular cut, and a round box is easier to state and reproduce.

Nothing statistical rests on this. The application-foundation milestone may build its map against it.

### 2. Analytical and statistical domain — **not decided**

The region over which relative exposure is computed and over which any inside-versus-outside figure is reported. **This is open.** Three candidates are set out under *Alternatives*, together with the evidence each needs.

Until one is accepted:

- **No headline inside-versus-outside statistic may be published.**
- No exposure surface may be presented as covering the full map extent.
- Nothing in the application may imply that low offshore vessel activity has been observed.

### 3. AIS coverage-quality treatment — required under every candidate

Whichever analytical domain is accepted, the vessel input needs an explicit, documented statement of where it is considered observable, carried through to the map. That is a requirement, not an option, because the publisher has stated a coverage limit and the project cannot present a uniform-looking traffic surface across a non-uniform one.

The form it takes — a hard clip, a mask rendered as a distinct "outside reliable coverage" category, or a per-cell coverage-confidence attribute — depends on which analytical domain is chosen and is settled with it.

## Consequences

- **M2 cannot be complete while this is open.** The roadmap records it as one of the outstanding items, and it is the one that gates the analysis rather than the publication.
- **M3 is not blocked.** Retrieval, cleaning, vessel-class filtering, reprojection, gridding, and the whale-model transfer are all independent of where the reporting boundary ends up, and can proceed over the full map extent. Only the exposure statistics wait.
- Processing over the full map extent and restricting at the reporting step is the right order: it keeps the domain decision reversible, and it means the evidence needed to settle it — the actual spatial distribution of commercial transits over a real period — is produced by work that has to happen anyway.
- The analysis reports on the **Southern California portion of the 2026 VSR zone, not the whole zone**, under any candidate. Every statistic must say so.
- The map extent **truncates the zone at 35.0°N**, where the zone continues north. Exposure near that edge is an artefact of the extent and results must not be read across it.
- Using the whale model's coverage as the water mask means the analysis domain and the biological input share a footprint, so no cell can carry vessel activity without a whale value. It also means the study area inherits the model's coastline, which is a modelling product rather than an authoritative shoreline. **This is one reason a real coastline dataset is needed before a distance-from-shore criterion can be applied** — see alternative 1.

## Alternatives considered

These are the candidate analytical domains, not candidate map extents. The map extent is settled above.

### 1. Conservative nearshore AIS-observable domain

Restrict statistics to water within a stated distance of the coastline, chosen to sit inside NOAA's 40–50 mile statement.

- **For:** every reported number comes from water where the publisher says the input works. It is the most defensible option and the easiest to explain.
- **Against:** it discards a third or more of the in-box VSR zone from the statistics, so the headline becomes a statement about the nearshore portion of the zone rather than about the zone. That is a real scope reduction and would have to be recorded as one.
- **Evidence needed to accept:** an authoritative coastline for the study area — not the whale model's clipped edge — and a stated, justified distance threshold. NOAA's "40 to 50 miles" does not say statute or nautical, so the project must pick and say so. A sensitivity check across the range would show whether the choice matters.

### 2. Coverage-qualified mask inside the broader extent

Compute over the full map extent, but classify each cell by whether the vessel input is considered observable there, and report statistics separately for the observable region and for the whole.

- **For:** keeps the full zone visible and in the analysis, while refusing to present unqualified numbers over it. Probably the most informative option for a reader.
- **Against:** two sets of numbers is exactly the framing that invites a reader to quote the more convenient one. It also requires defining the mask, which is alternative 1's problem plus a presentation problem.
- **Evidence needed to accept:** a defensible basis for the mask. The most promising is the **AIS Vessel Transit Counts** product — it is derived from tracks rather than points, is NOAA-computed at 100 m, and covers whole years, so comparing its offshore behaviour with this project's own point aggregation over a real period would show whether the falloff is a reception artefact or a traffic pattern. Receiver locations are also published as the AIS Base Stations dataset, which would allow a range-based rather than distance-from-shore mask.

### 3. A vessel source with defensible offshore coverage

Replace or supplement the input with satellite AIS.

- **For:** it is the only option that actually resolves the question rather than working around it. Offshore traffic would be observed rather than assumed.
- **Against:** NOAA cannot distribute satellite AIS, so this means a commercial provider — cost, licensing, and a redistribution position that would have to be established before anything derived from it could be published. The project has no budget line and Version 1 has a date.
- **Evidence needed to accept:** an available source, its terms, and confirmation that a derived aggregate may be published. **Not investigated.** Recorded because it is the honest answer to "what would settle this properly", not because it is expected to be taken up in Version 1.

### Extents rejected as the map window

**Candidate A (−121.0 west edge).** Keeps the window inside better-covered water, but captures only 74% of the zone's Southern California area and skews the inside/outside split to 59/41. As a map extent it hides part of the management area for a benefit that belongs to the analytical domain instead — which is precisely the conflation this record now avoids.

**Candidate C (−122.5 west edge, 35.2°N north edge).** Captures 97% of the zone but adds a further 19,000 km² of the least trustworthy water and pushes the inside share below half.

**Fitting the extent to the zone plus a buffer.** A buffer distance would be an arbitrary parameter with no evidence behind it, and an outside region shaped as a thin uniform collar is harder to interpret than real adjacent water.

**Extending north to the full zone.** Out of scope; the question is scoped to Southern California, and AIS volume scales with area.
