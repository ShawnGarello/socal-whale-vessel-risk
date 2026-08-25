# Data Sources

**Owns:** dataset provenance, source register, and data-discovery status.

> **This is a source register, not a data contract.** It records which sources the project intends to use, what each is for, and what still has to be established about it. It deliberately does **not** specify field names, schemas, spatial resolutions, file formats, temporal coverage, or licensing terms, because none of those have been confirmed against the actual data yet. Those are settled during data discovery (M2 in the [roadmap](roadmap.md)) and only then written down.
>
> Anything not yet confirmed is marked **To be verified**. That label is not a formality — a "to be verified" item must not be relied on in analysis, documentation, or the application until it has been checked against the source.

## How to read this register

Each entry records:

- **Analytical role** — what the source is for in this project.
- **Publisher** — who produces it.
- **Source** — the entry-point URL already identified for it.
- **Expected data type** — the general kind of data expected, at the level of "raster surface" or "point records". Not a format claim.
- **Verification status** — what has actually been confirmed.
- **Discovery questions** — what must be answered before the source can be used.
- **Provenance expectations** — what has to be recorded when the data is retrieved.
- **Licensing and redistribution** — what must be established about reuse.
- **Anticipated limitations** — what is likely to constrain the analysis, stated as expectation rather than fact.

Verification status across every entry below is currently the same: **not verified.** No dataset has been downloaded or inspected. The register exists so that discovery has a checklist rather than a memory.

---

## 1. Modeled blue-whale distribution

**Analytical role**
The biological input to the exposure analysis: where blue whales are more or less likely to occur across the study area. The project uses a modeled distribution or density surface rather than raw sighting points, because sightings reflect survey effort as much as whale presence.

**Publisher**
NOAA Fisheries (West Coast Region / Southwest Fisheries Science Center).

**Source**
- Species distribution models — <https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models>

Supporting context, not primary inputs:
- Ship-based cetacean and ecosystem assessment surveys, California Current — <https://www.fisheries.noaa.gov/west-coast/science-data/ship-based-cetacean-and-ecosystem-assessment-surveys-california-current>
- WhaleWatch — <https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/whalewatch>
- Blue whale hot spots — <https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/blue-whale-hot-spots>

**Expected data type**
A continuous modeled surface over the California Current or a portion of it. Whether it is delivered as raster, as gridded vector cells, or through a service is **to be verified**.

**Verification status**
Not verified. The page is known to exist and to concern California Current cetacean distribution models; nothing about the blue-whale product specifically has been confirmed.

**Discovery questions**
- Is a blue-whale product available separately, and in a form usable in GIS?
- What do the values represent — density, relative density, probability of occurrence, or something else — and in what units?
- What is the spatial extent, and does it fully cover the intended study area?
- What is the native spatial resolution?
- What temporal coverage does it represent, and is it a single climatological surface or a time series?
- Is uncertainty published alongside the estimates, and can it be shown in the application?
- What model and survey years underlie it, and is there a stated version or vintage?
- Which citation does NOAA ask users to give?

**Provenance expectations**
Record the exact product name, the page or service it came from, the retrieval date, any stated version or model year, and the requested citation. If the product is reached through an intermediate portal, record both the portal and the originating product.

**Licensing and redistribution**
To be verified. U.S. federal scientific data is commonly openly available, but that must be confirmed for this specific product, along with attribution requirements and whether a derived product may be republished as a hosted layer.

**Anticipated limitations**
- A modeled surface estimates likelihood of occurrence; it is not observed whale locations, and the application must say so.
- Native resolution may be coarser than the vessel data, forcing a resampling choice that affects results.
- Temporal coverage may not align with the AIS period chosen, which would constrain what the combined layer can claim.
- Model uncertainty may be substantial in parts of the study area, particularly near its edges.

---

## 2. Commercial vessel activity (AIS)

**Analytical role**
The vessel input to the exposure analysis: where large commercial vessels travel within the study area, how much traffic there is, and — if the data supports it — how fast they are moving.

**Publisher**
NOAA Office for Coastal Management (Digital Coast), from U.S. Coast Guard AIS data.

**Source**
- Vessel traffic data — <https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html>
- AccessAIS extract tool — <https://coast.noaa.gov/digitalcoast/tools/ais.html>
- Marine Cadastre National Viewer — <https://coast.noaa.gov/digitalcoast/tools/mmc.html>
- Digital Coast data catalog — <https://coast.noaa.gov/digitalcoast/data/home.html>

**Expected data type**
Vessel position records with associated attributes, extractable for a user-defined area and time period. Whether the project uses point records, derived tracks, or a published density product is **to be verified**.

**Verification status**
Not verified. AccessAIS is known to allow extraction by geographic area and time period; nothing about the extract's contents, size, or attributes has been confirmed.

**Discovery questions**
- What attributes accompany each record, and which of them identify vessel type, size, speed, and time?
- Is speed present and reliable enough to summarize, or does it require reconstruction from consecutive positions?
- How are vessel classes encoded, and how should "large commercial vessel" be defined from them?
- What temporal coverage is available, and at what reporting interval?
- How large is an extract for the study area at the intended period, and does that force a narrower window or a coarser aggregation?
- What known quality problems exist — implausible positions, duplicate or missing identifiers, gaps in coverage, receiver-range effects?
- Is a pre-aggregated vessel-density product available, and would using it be preferable to aggregating raw records?
- Does the vessel-size threshold relevant to the VSR program correspond to anything recorded in these data, or must it be approximated?

**Provenance expectations**
Record the extract bounds, the time period requested, the exact tool and options used, the retrieval date, and any dataset version. Record every filter applied afterwards — vessel classes kept, records discarded, and the rule that discarded them — because these choices shape the traffic surface more than any later step.

**Licensing and redistribution**
To be verified. Terms of use, attribution requirements, and any restriction on republishing derived products need confirming before a derived layer is hosted publicly.

**Anticipated limitations**
- AIS coverage is not uniform; shore-based reception varies with distance from receivers, so apparent traffic offshore may be affected by coverage rather than by vessel behavior.
- Position and speed errors are common and must be filtered with documented rules.
- Vessel-type coding is self-reported and imperfect.
- Aggregating records to a grid conflates transit frequency with time spent in a cell; whichever measure is used has to be named precisely.
- Raw records are large; the volume constrains the analytical period.

---

## 3. Vessel Speed Reduction zone boundary and season

**Analytical role**
The management input: the geographic boundary against which exposure is summarized inside versus outside, plus the season and vessel-size conditions that define what the program asks for.

**Publisher**
Protecting Blue Whales and Blue Skies (BWBS) program; California Ocean Protection Council for state-level program description.

**Source**
- BWBS program — <https://bluewhalesblueskies.org/>
- Ship operator and VSR zone information — <https://bluewhalesblueskies.org/operators/>
- Methods and monitoring — <https://bluewhalesblueskies.org/operators/methods-and-monitoring/>
- Program impact — <https://bluewhalesblueskies.org/impact/>
- California Ocean Protection Council overview — <https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/>

**Expected data type**
A polygon boundary, or the coordinates from which one can be constructed, together with descriptive season and speed-request information. Whether a downloadable geometry exists is **to be verified**.

**Verification status**
Not verified. The following program details appear in the original project plan and are carried here **as claims to check, not as established facts**:

| Claim recorded in the original plan | Status |
|---|---|
| The 2026 season runs April 22 through December 31 | To be verified against the program's own published statement |
| Vessels of at least 300 gross tons are asked to participate | To be verified |
| The requested speed is 10 knots or less | To be verified |
| Designated zones exist in California waters, including a Southern California zone | To be verified, including which zone or zones the study area should use |

Nothing in the analysis or the application may state these until they have been confirmed against the source, and each must carry the season year it applies to.

**Discovery questions**
- Is the zone boundary published as a downloadable geometry, as a service, or only as coordinates or a map image?
- If only coordinates are published, what is the exact list, and what assumptions does constructing a polygon from them require?
- Which zone or zones fall within the intended Southern California study area?
- Do the boundaries differ between seasons, and which season does Version 1 use?
- Are the season dates, vessel-size threshold, and requested speed stated authoritatively, and where?
- Is the program voluntary in the period analyzed, and is that stated precisely enough to describe correctly in the application?
- Does a state or federal agency republish the boundary in an authoritative GIS format that would be preferable to reconstructing it?

**Provenance expectations**
Record the page or document the boundary came from, the retrieval date, the season year it applies to, and — if the polygon was constructed rather than downloaded — the exact source coordinates and the construction steps, including the assumed coordinate reference system. A constructed boundary is a derived dataset and must be labeled as one.

**Licensing and redistribution**
To be verified. The BWBS program is not a federal data publisher, so reuse terms for its published boundary need explicit checking before the geometry is redistributed as a hosted layer.

**Anticipated limitations**
- Season definitions and boundaries can change between years; results must state the season they describe.
- A boundary reconstructed from published coordinates may differ slightly from the official geometry, and that difference matters most exactly where it is used — at the inside/outside edge.
- The program is a voluntary request rather than an enforced rule, which limits what its boundary implies about actual vessel behavior.

---

## 4. Supporting references

Not analytical inputs. Used for methodology, framing, and terminology.

| Reference | Use |
|---|---|
| [BWBS methods and monitoring](https://bluewhalesblueskies.org/operators/methods-and-monitoring/) | How the program itself frames speed, strike risk, noise, and emissions; a guide to careful language. |
| [BWBS / Scripps underwater-noise report (PDF)](https://bluewhalesblueskies.org/wp-content/uploads/BWBS_2025_ZoBell_Report_final.pdf) | Background for any future noise proxy. Not used in Version 1. |
| [NOAA blue whale hot spots](https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/blue-whale-hot-spots) | Context on frequently used blue-whale areas off Southern California. |
| [ArcGIS Living Atlas](https://livingatlas.arcgis.com/) | Discovery aid for existing published layers — **not** an authority in itself. Anything found there must be traced to its originating publisher, and that publisher recorded as the source. |

## Rules for adding a source

1. Register it here before it is used anywhere in the project.
2. Record the originating publisher, not the portal it was found through.
3. Mark every unconfirmed property **To be verified** rather than guessing it.
4. Record retrieval date and any version at the moment of retrieval — it cannot be reconstructed later.
5. Establish redistribution terms before any derived product is published publicly.
6. If a source is rejected during discovery, leave it here with the reason rather than deleting it. Knowing what was ruled out, and why, is part of the provenance.
