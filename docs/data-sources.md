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
