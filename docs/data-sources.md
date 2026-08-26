# Data Sources

**Owns:** dataset provenance, source register, and data-discovery status.

> **This is a source register, not a data contract.** It records which sources the project intends to use, what each is for, what has been established about it, and what has not. Recording an inspected property here — a field name, a resolution, a CRS, a licence term — is a statement of what the data was found to contain on the retrieval date. It is **not** a contract, a schema, or a commitment that the analysis will use that field, and no data contract, layer contract, or exposure formula is written from it until the discovery findings have been audited.
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

Verification status now differs between entries and is stated at the top of each one. Where an entry reports a verified property, it also says whether that means a webpage was read or an actual downloaded dataset was inspected. Those are not the same standard, and the register distinguishes them deliberately.

---

## 1. Modeled blue-whale distribution

**Analytical role**
The biological input to the exposure analysis: where blue whales are more or less likely to occur across the study area. The project uses a modeled distribution or density surface rather than raw sighting points, because sightings reflect survey effort as much as whale presence.

**Verification status: verified by inspection of the downloaded dataset** (retrieved 2026-08-25). Every property in the table headed *Verified properties* was read out of the actual file or computed from it, except where the "How established" column says it came from the publisher's metadata record. Unresolved items are listed at the end of this entry and remain unresolved.

### Selected product

| | |
|---|---|
| **Product** | Predictive Models of Cetacean Densities in the California Current Ecosystem, **2020b** |
| **Layer used** | `Blue_whale_summer_fall` |
| **Publisher** | NMFS Office of Science and Technology; models produced by NOAA Fisheries Southwest Fisheries Science Center (SWFSC) |
| **Metadata record** | InPort item [64349](https://www.fisheries.noaa.gov/inport/item/64349); field definitions in child item [64350](https://www.fisheries.noaa.gov/inport/item/64350) |
| **Distribution item** | <https://noaa.maps.arcgis.com/home/item.html?id=566b4ad31f1d40eeb65b8cf3a4f087ca> |
| **Direct retrieval** | `https://www.arcgis.com/sharing/rest/content/items/566b4ad31f1d40eeb65b8cf3a4f087ca/data` — anonymous HTTP GET, no account or token |
| **Retrieved** | 2026-08-25 |

**Underlying study and requested citation**

> Becker EA, Forney KA, Miller DL, Fiedler PC, Barlow J, Moore JE. 2020. *Habitat-based density estimates for cetaceans in the California Current Ecosystem based on 1991-2018 survey data.* U.S. Department of Commerce, NOAA Technical Memorandum NMFS-SWFSC-638. <https://doi.org/10.25923/3znq-yx13>

The InPort record additionally asks that the metadata record itself be cited: "NMFS Office of Science and Technology, 2026: Predictive Models of Cetacean Densities in the California Current Ecosystem, 2020b, https://www.fisheries.noaa.gov/inport/item/64349." Both are reproduced wherever this layer is shown.

### Verified properties

| Property | Finding | How established |
|---|---|---|
| **Format** | Esri File Geodatabase, zip-compressed. **Vector polygons, not a raster.** | Opened with GDAL 3.12.4 `OpenFileGDB` driver |
| **Geometry type** | `MultiPolygon` — one polygon per grid cell | Read from the file |
| **Feature count** | 12,257 cells | Read from the file |
| **CRS** | EPSG:4326 (WGS 84 geographic, degrees) — **unprojected** | Read from the file; matches InPort |
| **Spatial extent** | lon −131.0 to −117.09756, lat 30.05 to 48.50610 | Read from the file; matches the InPort bounding coordinates exactly |
| **Native resolution** | 0.1° × 0.1° equal-angle cells. `Shape_Area` maxes at exactly 0.01 square degrees; median cell width and height are both exactly 0.100000° | Computed from the file |
| **Grid origin** | Offset by 0.05°, not aligned to whole 0.1° multiples — the southern edge sits at 30.05°N | Computed from the file |
| **Cell area** | `AREA_SQKM` mean 93.08, max 106.75. Area falls with latitude as expected for equal-angle cells: mean 105.4 km² at 30–31°N, 101.7 at 34–35°N, 82.7 at 48–49°N | Computed from the file |
| **Land handling** | Clipped to water. Land and islands are absent — a point on San Nicolas Island returns no cell. 69 cells are sub-1 km² coastline slivers | Point-in-polygon tests against the file |
| **Value meaning and units** | `DENSITY` = **animals per km²**. Publisher definition: "Density value in animals/km^2; Source: From model" | InPort item 64350 |
| **Value range** | `DENSITY` 9.67 × 10⁻⁶ to 1.169 × 10⁻² animals/km²; median 4.01 × 10⁻⁴; 95th percentile 4.91 × 10⁻³ | Computed from the file |
| **Uncertainty** | **Provided.** `UNCERTAINTY` is a coefficient of variation. Range 0.354–1.623, median 0.804. The publisher's `-99999` "not available" sentinel does **not** occur in this layer | Definition from InPort item 64350; range computed from the file |
| **Derived field** | `ABUNDANCE` = `DENSITY` × `AREA_SQKM`. Verified: maximum absolute discrepancy 3.3 × 10⁻⁷ animals across all 12,257 cells | Computed from the file |
| **Internal consistency** | Total modeled abundance over the whole model domain is 1,239.0 animals across 1,140,912.7 km² | Computed from the file |
| **Temporal coverage** | A **single multi-year seasonal average**, `SEASON` = `Summer-Fall` for every cell. It is **not** a time series | Read from the file |
| **Why it is not time-varying** | `MONTH_NUMB` and `MONTH_NAME` are null throughout. Publisher: "This field NOT USED because densities are averaged over multiple months." | Definition from InPort item 64350; nulls confirmed in the file |
| **Model vintage** | Survey basis July–November in 1991, 1993, 1996, 2001, 2005, 2008, 2009, 2014 and 2018 | InPort item 64349 |
| **Model type** | `MODEL_TYPE` has the single value `Habitat based density model` across every cell — no gap-filled or substituted cells in this layer | Read from the file |

### Coverage of the intended study area

**Verified as sufficient.** The model covers every part of the Southern California Bight the analysis needs. Point tests returned a cell at each of these locations:

| Location | Density (animals/km²) | CV |
|---|---|---|
| Point Conception approach | 0.005919 | 0.399 |
| Santa Barbara Channel (mid) | 0.003787 | 0.398 |
| Santa Monica Bay | 0.002861 | 0.401 |
| San Pedro Channel / LA approach | 0.002817 | 0.398 |
| Long Beach outer anchorage | 0.003008 | 0.399 |
| San Diego approach | 0.005219 | 0.392 |
| Tanner / Cortes Bank | 0.003520 | 0.489 |

The eastern boundary of the model follows the coastline rather than a straight meridian, reaching −117.10 off San Diego and −120.61 off Point Conception.

For scale: the 777 cells falling entirely within lon −121 to −117 and lat 32 to 35 hold 258.4 of the 1,239.0 modeled animals — **20.9% of the whole California Current total in roughly 6.5% of its area.** Modeled uncertainty in this region (CV ≈ 0.39–0.43) is also markedly lower than the model-wide median of 0.80.

### Licensing, attribution, and redistribution

The distribution item is shared publicly by a NOAA account and carries no access restriction and no stated redistribution prohibition. Its licence field is a warranty disclaimer, quoted here in full because it is the only licence text the publisher provides:

> \*\*\* No Warranty\*\*\* The user assumes the entire risk related to its use of these data. NMFS is providing these data "as is," and NMFS disclaims any and all warranties, whether express or implied, including (without limitation) any implied warranties of merchantability or fitness for a particular purpose. No warranty expressed or implied is made regarding the accuracy or utility of the data on any other system or for general or scientific purposes, nor shall the act of distribution constitute any such warranty. It is strongly recommended that careful attention be paid to the contents of the metadata file associated with these data to evaluate dataset limitations, restrictions or intended use. In no event will NMFS be liable to you or to any third party for any direct, indirect, incidental, consequential, special or exemplary damages or lost profit resulting from any use or misuse of these data.

**Assessment:** a U.S. federal work, publicly distributed, with a citation request and a warranty disclaimer but no redistribution clause. Republishing a clipped and regridded derivative as a hosted layer, with the citation attached, is consistent with those terms. **This is the project's own reading of the terms, not legal advice and not an explicit permission from the publisher.**

### Considered and not selected

| Candidate | Why not selected |
|---|---|
| **Predictive Models of Cetacean Densities in the CCE, 2020** (ArcGIS Online item `96ae05c033a540bf83e0f6c00a25cf5a`, 22.3 MB, also downloaded and inspected) | Older survey basis (1991–2014). Its `Blue_whale_summer_fall` layer contains cells whose `MODEL_TYPE` is `Density value of adjacent HBDM data` — values borrowed from neighbouring cells — and its CVs reach 11.1. The 2020b layer has neither problem. **Retained locally as a cross-check**, and as the only source of a winter–spring blue-whale surface. |
| `Blue_whale_winter_spring` in that same 2020 product | A different study and a different method — `Telemetry based habitat model`, Hazen et al. 2016 — with median CV 1.25 and total modeled abundance of 53.6 animals. Combining it with the summer–fall surface would mix methodologies. Out of scope for Version 1 in any case, which uses one analytical period. |
| **WhaleWatch** (<https://oceanview.pfeg.noaa.gov/WhaleWatch/>) | Blue-whale-specific and monthly, which would be attractive for later temporal work. The site responds, but no machine-readable download endpoint was found: searches of the NOAA CoastWatch, `oceanview` and `upwell` ERDDAP servers and of ArcGIS Online returned no WhaleWatch dataset. **Retrieval path unresolved**, not rejected on merit. |
| **OBIS-SEAMAP / Navy Marine Species Density Database** (Duke) and **Data Basin** | Redistributors of the same SWFSC models, not the originating publisher. Register rule 2 requires recording the originating publisher, and the NOAA-hosted item is the originating distribution. |

### Consequences for the analysis

- The input is **vector polygons in EPSG:4326**, not a raster. Any analysis grid the project defines requires an area-weighted transfer from these cells, and the transfer must conserve **abundance** — `DENSITY` × area — rather than averaging density, or total modeled animals will not be preserved.
- Cells are **equal-angle, so their ground area varies with latitude.** Over the Southern California study area that variation is small but not zero, and it is one reason a projected, equal-area analysis grid is preferable.
- The model is a **single summer–fall average.** Version 1 cannot make monthly or seasonal claims from it, and the analytical period must be described in the model's terms rather than in finer ones.
- Uncertainty is available per cell and can be shown in the application. It is a CV on a modeled density, not an observation error.

### Remaining unresolved

- The **exact season definition** behind the `Summer-Fall` label. The survey basis is July–November; a redistributor's description of the same models says predictions represent late June to early December. Those are not identical, and the publisher's own authoritative statement of the prediction window has not been located. Version 1 must describe the period as the publisher does, so this needs settling before the period wording is finalised.
- Whether SWFSC has published a **version newer than 2020b**.
- Whether a **finer-resolution** blue-whale product exists for the Southern California Bight.

### Anticipated limitations

- A modeled surface estimates likelihood of occurrence; it is not observed whale locations, and the application must say so.
- Model uncertainty is substantial in absolute terms — a median CV of 0.80 across the model domain, though lower in the study area.
- The 0.1° native resolution is coarser than AIS positions, forcing a resampling choice that affects results.

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

**Verification status: program terms verified from the official BWBS webpage and the program's own 2026 zone map PDF; geometry verified by inspection of a downloaded dataset** (retrieved 2026-08-25). The two are separate standards and are labelled separately below.

### Program terms — verified

Every claim carried forward from the original project plan has now been checked. All four were correct.

| Claim carried from the original plan | Outcome | Source |
|---|---|---|
| The 2026 season runs April 22 through December 31 | **Confirmed.** "The 2026 voluntary Vessel Speed Reduction (VSR) Season will be in effect April 22 through December 31, 2026 off the coast of California." | [bluewhalesblueskies.org/operators/](https://bluewhalesblueskies.org/operators/); repeated on the 2026 zone map PDF |
| Vessels of at least 300 gross tons are asked to participate | **Confirmed, with a wording difference worth noting.** The FAQ says "Vessels greater than 300 gross tons are asked to reduce their speed"; the eligibility answer says "300 gross registered tons or larger"; the map PDF says "Oceangoing vessels 300 gross tons or larger". The program uses *greater than* and *or larger* interchangeably. The project should describe the threshold as approximately 300 GT and not lean on the boundary case. | Same page; map PDF |
| The requested speed is 10 knots or less | **Confirmed.** "reduce their speed to 10 knots or less". | Same page; map PDF |
| Designated zones exist in California waters, including a Southern California zone | **Superseded for 2026.** There is now a **single** California VSR zone, not separate northern and southern zones. The program states the 2026 zone "is optimized for both conservation benefit, and to provide a simplified zone more straightforward for navigation purposes." Southern California is a *portion* of one statewide zone. | Same page |

**Voluntary status — confirmed.** The program describes "voluntary Vessel Speed Reduction zones" and a "voluntary Vessel Speed Reduction (VSR) Season" throughout. The map PDF frames it as a request: vessels "are asked to travel at 10 knots or less".

**Eligible vessel types — verified.** "Bulk, tanker, auto carrier, container ships and passenger vessels 300 gross registered tons or larger are eligible to participate in the BWBS program." The 2026 season is the first in which cruise ships are eligible.

**An exclusion that matters to the analysis.** The map PDF states that vessels in coastal or internal waters requiring a state-licensed or federally-endorsed pilot "are not subject to the voluntary VSR", because the pilot retains navigational authority. Speeds above 10 knots on pilotage grounds are removed from a fleet's end-of-season calculation. The zone polygon nonetheless extends into those waters — a point inside Los Angeles inner harbour tests as inside the zone. **An "inside the zone" statistic therefore includes water where the speed request does not actually apply.** This is a limitation of any inside/outside summary and must be stated wherever one is reported.

### Published zone points — verified

The program publishes eight points under the heading "2026 VSR Zone Points", with the column heading "Point. Latitude, Longitude" — **coordinate order is explicitly latitude then longitude.**

| # | Latitude | Longitude |
|---|---|---|
| 1 | 41.97 | −125.46 |
| 2 | 40.34 | −125.18 |
| 3 | 37.69 | −124.11 |
| 4 | 36.32 | −123.00 |
| 5 | 35.50 | −123.00 |
| 6 | 35.05 | −122.10 |
| 7 | 33.30 | −121.21 |
| 8 | 32.55 | −117.13 |

**No coordinate reference system or datum is stated anywhere on the page or the map.** WGS 84 is the only reasonable assumption for published marine coordinates, and the downloaded geometry is served in EPSG:4326, which is consistent with it — but **the program has not stated a datum, and this remains an assumption rather than a verified fact.** At these latitudes a NAD 27 / WGS 84 confusion would be on the order of 100 m, which is small against the zone but not nothing.

**Do the eight points alone define a polygon? No — verified.** They describe only the **seaward** boundary. They run from offshore northern California south-east to the coast at the Mexican border, and closing them into an area requires the California coastline on the landward side plus a northern closing segment. Constructing a polygon from these points alone would require the project to supply a shoreline and to decide how to close the north end — both of which would be project assumptions affecting exactly the inside/outside edge the analysis reports on.

**That construction is not necessary**, because an authoritative closed geometry exists.

### Zone geometry — verified by inspection

| | |
|---|---|
| **Feature** | `California Voluntary Vessel Speed Reduction Zone` (FID 126) in the `WhaleAtlas_2026` layer |
| **Attributes as published** | `Season` = "April 22 - December 31, 2026"; `ShipReq` = "Vessels 300 gross tons or larger are requested to reduce speeds to 10 knots or less when transiting through the CA VSR Zone"; `Source` = "Protecting Blue Whales & Blue Skies Coalition"; `Species` = "Blue Whale, Fin Whale, and Humpback Whale" |
| **Publisher** | Danielle Alvarez, California Marine Sanctuary Foundation (CMSF) and BWBS — the same person listed as a BWBS contact on the official 2026 zone map PDF |
| **Item** | ArcGIS Online `b400c7f418b04dc5a9d7ce5015adae32`, public |
| **Service** | `https://services5.arcgis.com/4biRnCjZju47bNvA/arcgis/rest/services/WhaleAtlas_2026/FeatureServer/0` |
| **Retrieval** | Anonymous `query` with `where=FID=126`, `outSR=4326`, `f=geojson`. No account or token |
| **Retrieved** | 2026-08-25 |

| Property | Finding |
|---|---|
| **Format** | Feature service, queryable as GeoJSON; also offered as a shapefile item |
| **Geometry** | Single valid `Polygon` — outer ring of 37,239 vertices plus **104 interior rings** |
| **CRS** | Service is stored in EPSG:3857; requested and returned as EPSG:4326 |
| **Extent** | lon −125.46 to −117.104, lat 32.5498 to 41.9985 |
| **Area** | **142,155 km²**, computed in EPSG:3310 (California Albers, equal-area) |
| **Interior rings** | Islands, excluded from the zone. Areas match published island areas: 250.3 km² at (−119.75, 34.01) = Santa Cruz; 214.7 at (−120.11, 33.97) = Santa Rosa; 193.8 at (−118.43, 33.38) = Santa Catalina; 146.7 at (−118.49, 32.90) = San Clemente; 58.6 at (−119.51, 33.25) = San Nicolas; 38.5 at (−120.37, 34.04) = San Miguel; 2.6 at (−119.04, 33.48) = Santa Barbara Island. Total hole area 916.8 km² |
| **Landward boundary** | Follows the coastline. The 37,239-vertex outer ring and the island holes together confirm the polygon is already land-clipped — **the project does not need to supply a shoreline or make a closure assumption** |

**The geometry was checked against the published points and matches.** Distance from each published point to the polygon's outer boundary, measured in EPSG:3310:

| Point | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Distance | 0 m | 0 m | 0 m | 0 m | 0 m | 0 m | **455 m** | 0 m |

Seven of the eight published points lie exactly on the boundary. Point 7 (33.30, −121.21) is 455 m from it. The map PDF gives a finer value for the same point — 33°18.066′, −121°12.7234′ — which is 377 m from the boundary, so the discrepancy is not simply the webpage's two-decimal rounding. **It is a real, small inconsistency between the published point list and the published geometry.** At 455 m against a 142,155 km² zone it does not affect any statistic this project will report, but it is recorded rather than smoothed over, and the geometry — not the point list — is what the analysis uses.

### Which portion applies to the Southern California study area

There is one zone, so the question is which part of it the study area must contain rather than which zone to pick.

- The portion of the zone south of 35°N covers **56,011 km², 39.4% of the whole zone.**
- Its bounds are lon −122.07 to −117.10, lat 32.5498 to 35.0.
- Point tests confirm the zone includes the Santa Barbara Channel, the Point Conception approach, Santa Monica Bay, the San Pedro Channel and Long Beach outer anchorage, the Catalina offshore lane, and the San Diego approach.
- Point tests confirm it **excludes** Tanner/Cortes Bank (−119.10, 32.75) and the waters well offshore of the Bight.

That last result is directly relevant to the research question: Tanner/Cortes Bank sits outside the zone and carries a modeled blue-whale density of 0.00352 animals/km², above the study-area median.

### Licensing, attribution, and redistribution

**This is the weakest licensing position of the three sources, and it is not fully resolved.**

- The BWBS webpage carries **no copyright notice, no terms of use, and no data-use statement.** A search of the page text for copyright, licence, terms and attribution language returned nothing.
- The zone map PDF states "This map is not to be used for navigational purposes" and credits "Map source: Jess Morten/NOAA ONMS".
- The ArcGIS Online item's licence field is a **use disclaimer, not a licence grant**: the layer "should not be used for navigation purposes", mariners should operate at their own discretion, and "these measures may not be comprehensive and lack of inclusion does not indicate the absence of a VSR Zone, ATBA, or TSS". Attribution is given as "Created by Danielle Alvarez, with CMSF and BWBS."
- The item is shared publicly and is queryable anonymously.

**Assessment:** public sharing plus a stated attribution and no redistribution prohibition is a reasonable basis for using the geometry in this analysis and displaying it with attribution. It is **not** an explicit redistribution grant, and BWBS/CMSF is a non-profit coalition rather than a federal data publisher, so the public-domain reasoning that applies to the NOAA sources does not apply here. **Unresolved: whether republishing this geometry as a project-hosted layer is permitted.** Until that is settled, the safer options are to reference the BWBS service directly rather than copy it, or to ask the program. This must be decided before any public hosting, not at release.

### Considered and not selected

| Candidate | Why not selected |
|---|---|
| Constructing a polygon from the eight published points plus a coastline | Unnecessary, and worse. It would require the project to choose a shoreline dataset and a northern closure, both of which would be project assumptions at exactly the inside/outside boundary the analysis reports on. The published geometry already resolves both. |
| **Northern California Vessel Speed Reduction Zone — Greater Farallones** (ArcGIS Online, owner `anastasia.kunz_noaa`, NOAA) | A NOAA-published VSR geometry, but for northern California only. Not applicable to the Southern California study area. Noted because it is a federally published alternative if a NOAA-sourced geometry is ever preferred for licensing reasons. |
| Previous-season zone geometries (`WhaleAtlas_2025`) | Version 1 analyses one season. The 2026 zone is a redesign, so mixing seasons would be wrong. |

### Remaining unresolved

- **Redistribution permission for the zone geometry** (above). This is the one licensing question in the project that is genuinely open.
- **The datum of the published coordinates.** Assumed WGS 84; not stated by the program.
- **The 455 m discrepancy at point 7** between the published point list and the published geometry. Recorded, not explained.
- Whether NOAA ONMS, which produced the map, publishes the 2026 statewide zone as a federal GIS layer. Only the Greater Farallones northern zone was found under a NOAA account.

### Anticipated limitations

- Season definitions and boundaries change between years — the 2026 zone is itself a redesign that merged the previous separate zones. Results must state the season they describe.
- The program is a voluntary request rather than an enforced rule, which limits what the boundary implies about actual vessel behaviour.
- The zone extends into pilotage waters where the request does not apply, so "inside the zone" is not the same as "where ships are asked to slow down".

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
