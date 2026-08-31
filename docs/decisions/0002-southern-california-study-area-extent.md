# 0002 — Southern California study area extent

**Status:** Proposed
**Date:** 2026-08-25, reopened 2026-08-26, evidence corrected 2026-08-29, authoritative closure attempted 2026-08-31

> This record was briefly marked Accepted. An audit found that the evidence
> behind it did not support accepting a single extent for both mapping and
> statistics, and it was returned to Proposed rather than patched. The map
> extent below is settled enough to build against. **The analytical domain is
> not, and no headline inside-versus-outside statistic may be published until
> it is.**

## Context

[Architecture](../architecture.md) deferred the study-area extent until data discovery could establish what the inputs actually cover. Discovery inspected all three. Two of them constrain nothing:

- **The blue-whale model** covers longitude −131 to −117.10 and latitude 30.05 to 48.51, clipped to water. It covers everything Southern California needs.
- **The 2026 VSR zone** is a single statewide polygon of 143,035.5 km² after its geographic edges are densified before EPSG:3310 projection. Its portion south of 35°N is 56,627.6 km², bounded by longitude −122.07 to −117.10 and latitude 32.55 to 35.0.

**The vessel input is the problem.** NOAA states that this AIS product comes from roughly 200 land-based receiving stations and that *"coverage is currently unavailable for … waters extending more than 40 to 50 miles from the coast."* There is no satellite AIS in the product. That FAQ sentence does not say statute or nautical miles or define "coast." USCG's current waterway-analysis instruction supplies a more specific NAIS system interpretation separately: at least 50 nautical miles from each reception antenna site. The Southern California portion of the VSR zone reaches several hundred kilometres offshore at its western vertex.

### 2026-08-28 evidence update

NOAA NGS CUSP now supplies an independently published coastline, and NOAA OCM's 2024 AIS Base Stations dataset supplies receiver geometry derived from USCG Light Lists. Their provenance, limitations, transformations, deterministic command, ignored output identities, synthetic tests, and measurements are in [analytical-domain-evidence.md](../analytical-domain-evidence.md).

All four range/unit interpretations were tested against both inputs on the accepted 5 km water grid. Coastline buffers include 57,027–71,940 km² of water and represent 82.94–95.72% of the in-grid VSR area. Receiver buffers include 46,098–64,717 km² and represent 66.63–85.62%. Every boundary cell is intersected fractionally; no centroid, majority, or whole-cell classification is used.

At the time, this did not identify one defensible domain. NOAA's range statement describes where data are generally unavailable, not guaranteed observation inside the line. The base-station metadata marks completeness untested and provides no antenna height, operating interval, outage record, or reception footprint. The spread among scenarios is analytically material. The later authoritative search below supplies a general performance basis for one receiver scenario but does not supply 2024 operating history.

### 2026-08-31 authoritative closure attempt

Only NOAA OCM/MarineCadastre, USCG NAVCEN, and official federal metadata and technical material were searched. AIS broadcast-point density and NOAA transit-count layers were not used because neither can reveal transmissions the same land-receiver feed did not capture.

| Publisher and exact source | Source date; access date | Establishes | Does not establish |
|---|---|---|---|
| NOAA OCM, [*Automatic Identification System Frequently Asked Questions*](https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf), pp. 1–3 | May 2026; accessed 2026-08-31 | Public NAIS data generally are unavailable beyond "40 to 50 miles from coast"; NAIS has about 200 land receivers; sensor interruptions occur; the USCG feed typically does not give NOAA their cause or duration. | Whether "miles" are statute or nautical; what "coast" means; a guaranteed inside boundary; station-specific 2024 outages or coverage. |
| USCG NAVCEN, [Work Instruction 2022-01, *Waterway Analysis Tactics, Techniques and Procedures*](https://www.navcen.uscg.gov/sites/default/files/pdf/waterways/nsra/NAVCEN%20Work%20Instruction%202022-01%20v2.pdf), pp. 1, 7 | September 2022; Change 01 dated 2023-09-22; accessed 2026-08-31 | NAIS provides coastal AIS signal-reception coverage to at least **50 nautical miles from each NAIS reception antenna site**; USCG calls this a 50-mile performance standard and says reception can extend farther. This supplies the unit, boundary basis, and general inside-boundary treatment. | Whether every listed Southern California site operated throughout July 1–November 30, 2024; station-specific outages; whether every received message reached NOAA's public daily files. |
| NOAA OCM, [AIS Base Stations, InPort item 73206](https://www.fisheries.noaa.gov/inport/item/73206) | Published 2024-08-01; metadata updated 2025-11-11; accessed 2026-08-31 | Locations and identities derived from USCG Light Lists; nine NAIS points in the expanded Southern California filter; 10 m stated horizontal accuracy. | Attribute accuracy or completeness, which NOAA marks untested; antenna properties, operations, outages, or coverage geometry. |
| USCG NAVCEN, [*2024 Light List, Volume VI, Pacific Coast and Pacific Islands*](https://www.navcen.uscg.gov/sites/default/files/pdf/lightLists/LightList_V6_2024.pdf), front matter pp. xix, xlii–xliii | 2024; accessed 2026-08-31 | NAIS uses approximately 200 VHF receiver sites and lists the relevant Southern California station names and coordinates. | Commissioning dates, operating intervals, outages, antenna properties, or station-specific footprints. |
| USCG NAVCEN, [*How AIS Works*](https://www.navcen.uscg.gov/how-ais-works) | No publication or update date shown; accessed 2026-08-31 | General AIS range depends principally on antenna height; nominal ship-to-ship range at sea is 20 nautical miles and terrain can obstruct reception. | A NAIS performance boundary or 2024 station operations. |
| USCG NAVCEN, [*Pacific Seacoast Level of Service Study*](https://www.navcen.uscg.gov/sites/default/files/pdf/waterways/pacific/Pacific_Seacoast_Final.pdf) and [enclosure 3](https://www.navcen.uscg.gov/sites/default/files/pdf/waterways/pacific/Encl_3_Pacific_SeaCoast_D11_D13_NAIS_coverage_maps_sites_with_24_NM_range.PNG) | 2020-06-17; accessed 2026-08-31 | A historical District 11 schematic shows station-centred 24-nautical-mile circles for shore-transmitted AIS aids to navigation. | 2024 ship-to-shore reception coverage; the purpose, year, and range differ from this analysis. |
| USCG NAVCEN, [*Vessel Information Verification Service Coverage*](https://www.navcen.uscg.gov/sites/default/files/pdf/AIS/VIVS_Coverage.pdf) | No date shown; accessed 2026-08-31 | A national, low-resolution service-coverage illustration exists. | A dated 2024 Southern California boundary, station operations, or geometry precise enough for the analytical grid. |

**Finding.** NOAA's sentence remains ambiguous on its own, but the USCG instruction provides an official NAIS interpretation that supports one already-calculated scenario: the union of 50-nautical-mile buffers around the 2024 published NAIS reception sites. "To at least" and "performance standard" support calling water inside that union **system-performance-qualified**. They do not support calling it continuously observed, complete, or an empirical reception footprint. No parameter changed, so the existing evidence does not need regeneration.

**Exact questions still unanswered.** No public official source found identifies when each of the nine Southern California sites was operational during July 1–November 30, 2024, what outages occurred, or whether every message received by NAIS reached NOAA's public daily files. The current NOAA FAQ instead says outage cause and duration typically are not supplied with the USCG feed.

**Proposed author decision.** Consider the existing `receivers_50_nautical_miles` mask as the analytical and statistical domain, explicitly described as a scope-reduced, system-performance-qualified domain rather than observed coverage. This would retain unknown 2024 receiver and feed interruptions as observational-completeness limitations and would continue to exclude all cells beyond the mask from headline statistics. ADR 0002 remains Proposed pending author review. If the author does not approve that scope reduction, the remaining route is publisher clarification about 2024 station operations and feed completeness; no arbitrary fallback domain is authorized.

Questions suitable for a publisher clarification request, but not sent by this project, are:

1. Were the nine listed Southern California NAIS reception sites operational throughout July 1–November 30, 2024, and are station-level outage intervals available?
2. Does the 50-nautical-mile reception performance standard apply to each of those listed sites during that period?
3. Did the NOAA OCM public daily AIS files preserve all messages delivered by NAIS, or were there additional feed, processing, or publication gaps?

Three candidate extents were measured, using the whale model's own water coverage as the water mask. Areas in EPSG:3310:

The table below records the original map-box comparison. It projected only the stored VSR vertices and is superseded for quantitative domain selection by the densified, exact-grid measurements in [analytical-domain-evidence.md](../analytical-domain-evidence.md). It remains here because it explains why candidate B became the map extent; no current statistic uses these areas.

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

The new evidence supports a future **coverage-qualified mask**, not a second unqualified full-map statistic. Once an exact boundary is accepted, headline results exclude all area beyond it. The application may retain the full map for whale, VSR, and regional context, but outside cells must be explicitly shown as outside defensible AIS observability and never as observed low traffic. Partial cells retain exact qualified geometry and area fractions.

**Smallest remaining step for acceptance:** author approval of the evidence-supported 50-nautical-mile receiver mask as an explicit, system-performance-qualified scope reduction, with unknown 2024 operations retained as a limitation; or publisher clarification supplying period-specific receiver operations and public-feed completeness. The evidence does not support a coastline mask or an arbitrary smaller fallback.

## Consequences

- **M2 cannot be complete while this is open.** The roadmap records it as one of the outstanding items, and it is the one that gates the analysis rather than the publication.
- **M3 is not blocked.** Retrieval, cleaning, vessel-class filtering, reprojection, gridding, and the whale-model transfer are all independent of where the reporting boundary ends up, and can proceed over the full map extent. Only the exposure statistics wait.
- Processing over the full map extent and restricting at the reporting step is the right order: it keeps the domain decision reversible, so accepting a domain later is a change to one reporting step rather than a reprocessing run. **It does not produce the evidence needed to settle the domain** — see "Why same-source comparison cannot settle this" below.
- The analysis reports on the **Southern California portion of the 2026 VSR zone, not the whole zone**, under any candidate. Every statistic must say so.
- The map extent **truncates the zone at 35.0°N**, where the zone continues north. Exposure near that edge is an artefact of the extent and results must not be read across it.
- Using the whale model's coverage as the water mask means the analysis domain and the biological input share a footprint, so no cell can carry vessel activity without a whale value. The mask edge remains biological-model support rather than a coastline. NOAA NGS CUSP now supplies the separate authoritative shoreline needed to calculate distance-from-coast candidates reproducibly; it does not establish that AIS observation is complete inside any candidate.

## Alternatives considered

These are the candidate analytical domains, not candidate map extents. The map extent is settled above.

### 1. Conservative nearshore AIS-observable domain

Restrict statistics to water within a stated distance of the coastline, chosen to sit inside NOAA's 40–50 mile statement.

- **For:** if the publisher confirms an exact conservative threshold and inside-boundary treatment, every reported number could be limited to the resulting coverage-qualified population. It would be straightforward to explain.
- **Against:** it discards a third or more of the in-box VSR zone from the statistics, so the headline becomes a statement about the nearshore portion of the zone rather than about the zone. That is a real scope reduction and would have to be recorded as one.
- **Evidence needed to accept:** CUSP now supplies the authoritative coastline. What remains is a stated, justified distance and unit, confirmation that the resulting inside area may be treated as coverage-qualified despite receiver outages and other reception variation, and confirmation that CUSP is the coast basis meant by that threshold. The completed sensitivity calculation shows that the choice materially changes the population.

### 2. Coverage-qualified mask inside the broader extent

Compute vessel activity over the full map extent for reversible processing, then intersect cells fractionally with an accepted observability mask. Headline statistics use only the coverage-qualified population. The remainder stays visible only as explicitly masked or qualified map context, never as observed low traffic and never as a second whole-map statistic.

- **For:** keeps the full zone visible for context while restricting every headline number to the defensible statistical population.
- **Against:** it still requires clear presentation of excluded and partial-cell areas. The USCG standard is general rather than a station-specific 2024 operating record, and the NOAA station inventory has untested completeness.
- **Evidence needed to accept:** the basis must come from **outside the broadcast-point data itself.** USCG's 50-nautical-mile-from-each-reception-site performance standard and NOAA's 2024 station locations now supply that basis for the existing receiver mask. Author acceptance must preserve the distinction between system-performance-qualified geometry and messages actually received, including unknown station and feed interruptions. NOAA's unitless coastline wording still does not support a coastline mask.
- **What cannot supply this evidence:** any comparison against another product derived from the same land-receiver feed — see the note below.

### Why same-source comparison cannot settle this

An earlier version of this record proposed comparing NOAA's **AIS Vessel Transit Counts** against this project's own aggregation to distinguish reception loss from a real traffic pattern. **That reasoning is circular and is withdrawn.** Transit counts are built from the same U.S. Coast Guard land-receiver broadcast points this project uses. A vessel no receiver heard is absent from both, so the two agreeing offshore says only that they share an input — it is a check on this project's aggregation arithmetic, which is worth having, and nothing at all about coverage.

The same objection applies to scale. Processing the full 153-day period gives a much better sample of the traffic the receivers *did* hear, and it is worth doing for its own sake, **but no quantity of the same data reveals vessels that were never recorded.** A gap that is uniform across five half-hour windows and a gap that is uniform across 153 days are equally consistent with empty water and with a dead spot.

Evidence about coverage has to come from outside the broadcast-point record: from the publisher's own statement of its limits, from the physical geometry of the receiver network, or from an independent observation of the same vessels.

### 3. A vessel source with defensible offshore coverage

Replace or supplement the input with satellite AIS.

- **For:** it is the only option that actually resolves the question rather than working around it. Offshore traffic would be observed rather than assumed.
- **Against:** NOAA cannot distribute satellite AIS, so this means a commercial provider — cost, licensing, and a redistribution position that would have to be established before anything derived from it could be published. The project has no budget line and Version 1 has a date.
- **Evidence needed to accept:** an available source, its terms, and confirmation that a derived aggregate may be published. **Not investigated.** Recorded because it is the honest answer to "what would settle this properly" — it is the only one of the three that observes the offshore vessels rather than reasoning about whether they could have been heard — not because it is expected to be taken up in Version 1.

### Extents rejected as the map window

**Candidate A (−121.0 west edge).** Keeps the window inside better-covered water, but captures only 74% of the zone's Southern California area and skews the inside/outside split to 59/41. As a map extent it hides part of the management area for a benefit that belongs to the analytical domain instead — which is precisely the conflation this record now avoids.

**Candidate C (−122.5 west edge, 35.2°N north edge).** Captures 97% of the zone but adds a further 19,000 km² of the least trustworthy water and pushes the inside share below half.

**Fitting the extent to the zone plus a buffer.** A buffer distance would be an arbitrary parameter with no evidence behind it, and an outside region shaped as a thin uniform collar is harder to interpret than real adjacent water.

**Extending north to the full zone.** Out of scope; the question is scoped to Southern California, and AIS volume scales with area.
