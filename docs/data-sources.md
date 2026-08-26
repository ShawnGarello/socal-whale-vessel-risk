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

## Retrieval provenance and local artifacts

**Owns the provenance manifest for M2.** Every finding in this register was read
from one of the artifacts below. They are **not committed** — they live under the
ignored local data root described in [../data/README.md](../data/README.md) —
so this table is what makes them re-obtainable and what proves a local copy is
the same file that was inspected.

The sizes and checksums here are load-bearing, not decorative.
[`tools/m2_verify.py`](../tools/m2_verify.py) parses the *Local artifacts* table
below and checks every row against the file on disk. If this document and the
data disagree, the tool fails. Do not edit a size or checksum by hand.

### How each artifact was retrieved

All retrievals were anonymous HTTPS GETs. **No credential, token, or API key was
used or required for any of them.**

| # | Artifact | Source URL or endpoint | Method and parameters | Retrieved |
|---|---|---|---|---|
| 1 | Whale model, selected product (2020b) | `https://www.arcgis.com/sharing/rest/content/items/566b4ad31f1d40eeb65b8cf3a4f087ca/data` | `GET`, no parameters. Item is the distribution link named by InPort record [64349](https://www.fisheries.noaa.gov/inport/item/64349) and is shared publicly by a NOAA account | 2026-08-25 |
| 2 | Whale model, comparison product (2020) | `https://www.arcgis.com/sharing/rest/content/items/96ae05c033a540bf83e0f6c00a25cf5a/data` | `GET`, no parameters. Retrieved only to justify not selecting it | 2026-08-25 |
| 3 | VSR zone geometry | `https://services5.arcgis.com/4biRnCjZju47bNvA/arcgis/rest/services/WhaleAtlas_2026/FeatureServer/0/query` | `GET` with `where=FID=126`, `outFields=*`, `returnGeometry=true`, `outSR=4326`, `f=geojson` | 2026-08-25 |
| 4 | 2026 VSR zone map | `https://bluewhalesblueskies.org/wp-content/uploads/2026-VSR-Zone-Map_July-2026.pdf` | `GET` with a browser `User-Agent`; the site returns HTTP 403 to a default `curl` agent | 2026-08-25 |
| 5 | Marine Cadastre AIS FAQ (May 2026) | `https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf` | `GET`, no parameters | 2026-08-25 |
| 6 | AIS Vessel Type and Group Codes | `https://coast.noaa.gov/data/marinecadastre/ais/VesselTypeCodes2018.pdf` | `GET`, no parameters | 2026-08-25 |
| 7 | AIS daily prefixes, five dates | `https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_<date>.zip` | `GET` with header `Range: bytes=0-8388607`, returning HTTP 206. **Only the first 8 MiB of each file was transferred.** Dates: `2024_07_15`, `2024_08_15`, `2024_09_16`, `2024_10_15`, `2024_11_15` | 2026-08-25 (`2024_07_15`), 2026-08-26 (the other four) |

**Why the AIS retrieval looks unusual.** Each daily file is a zip containing one
CSV, and is 330–420 MB. Retrieving five of them in full would be 1.8 GB for a
schema inspection. Instead the zip local file header at offset 0 was parsed to
locate the start of the deflate stream, and that stream was inflated as far as
the retrieved bytes allow. This is exactly what
`python tools/m2_verify.py extract` does, and it is deterministic: re-running it
reproduces the `.csv` files below byte for byte, which is why their checksums
are meaningful despite being derived rather than downloaded.

### Local artifacts

Paths are relative to the repository root. Verify with
`python tools/m2_verify.py verify`.

| # | Local file | Bytes | SHA-256 | Relationship |
|---|---|---|---|---|
| 1 | `data/raw/noaa-swfsc-becker-2020b/swfsc_cce_becker_et_al_2020b.gdb.zip` | 16136589 | `5677b95178b507337d2bdf048c9ad69383b0b48f7c7a1cd829774eeecd8c7a5d` | As downloaded. Extracted in place to `swfsc_cce_becker_et_al_2020b.gdb/` (67 MB), which is what GDAL reads |
| 2 | `data/raw/noaa-swfsc-becker-2020/swfsc_cce_becker_et_al_2020.gdb.zip` | 22263387 | `ba772bcb209c1455d657d9deec6ac047686fbfd22fc05362dd75de75646fda0e` | As downloaded. Extracted in place to `swfsc_cce_becker_et_al_2020.gdb/` |
| 3 | `data/raw/bwbs-vsr-2026/bwbs_ca_vsr_zone_2026.geojson` | 1591003 | `2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783` | The query response body, unmodified |
| 4 | `data/raw/bwbs-vsr-2026/2026-VSR-Zone-Map_July-2026.pdf` | 1750275 | `fb16fb49a6ca3ed59aa3c0a3d2c3f40f20c70ea77adac65eea6d8de2e23df375` | As downloaded |
| 5 | `data/raw/noaa-ais-2024/docs/marinecadastre_ais_faq.pdf` | 506349 | `1dcd64e439618d482878435d6c5ce0bcbf0791f99006a3974dd0757b467691c3` | As downloaded |
| 6 | `data/raw/noaa-ais-2024/docs/VesselTypeCodes2018.pdf` | 117526 | `e10c70bd5aaa25d11acbe09b351a340470614c0ba749059344a7f7f2f17d72be` | As downloaded |
| 7 | `data/raw/noaa-ais-2024/AIS_2024_07_15.head8MB.part` | 8388608 | `eaa212da534842a61400dd8d68359e73329ce4892b4af2f195840d65bbade797` | Partial HTTP 206 response, first 8 MiB of the daily zip |
| 8 | `data/raw/noaa-ais-2024/AIS_2024_07_15.head_sample.csv` | 22723368 | `228247d2d6ede6c9d38602f388577b78c59697a19059918bcbcf69495b309e6d` | **Derived from #7** by `m2_verify.py extract`. 207,849 data rows |
| 9 | `data/raw/noaa-ais-2024/AIS_2024_08_15.head8MB.part` | 8388608 | `3072ddd38249129b8a9a50798aff3bdae3ba07de49863bb20656a5079ca2be12` | Partial HTTP 206 response |
| 10 | `data/raw/noaa-ais-2024/AIS_2024_08_15.head_sample.csv` | 22671033 | `d3eda3dfca6cb9c7cf45eef05f34f86c27156f9ecf0f7311bb106040e54608c5` | **Derived from #9.** 207,420 data rows |
| 11 | `data/raw/noaa-ais-2024/AIS_2024_09_16.head8MB.part` | 8388608 | `b1998980f54a9eed29bd4e2dd66eebc8ceb62c5f617e1b30d7896792c78f74e8` | Partial HTTP 206 response |
| 12 | `data/raw/noaa-ais-2024/AIS_2024_09_16.head_sample.csv` | 22586931 | `7b8451bc83aa1f7080052965d62c53bfe3ee9451ddb50182877a2ac32b254b79` | **Derived from #11.** 205,322 data rows |
| 13 | `data/raw/noaa-ais-2024/AIS_2024_10_15.head8MB.part` | 8388608 | `ee868ee0097fc83bd925928f7a277f301250cfae838973f1924a810ca69b43c7` | Partial HTTP 206 response |
| 14 | `data/raw/noaa-ais-2024/AIS_2024_10_15.head_sample.csv` | 22620135 | `3e925b56a1555935b9379d428b76a94eb0db3c30aa830b832a1d91967911f8b3` | **Derived from #13.** 204,861 data rows |
| 15 | `data/raw/noaa-ais-2024/AIS_2024_11_15.head8MB.part` | 8388608 | `7a72e3cdcd92b605133cd6f17274c1c4b89eeb2b71f25f277978fe2e1fc3ec51` | Partial HTTP 206 response |
| 16 | `data/raw/noaa-ais-2024/AIS_2024_11_15.head_sample.csv` | 22807974 | `937f028539cd8d79b15700217a5fed3f6f91f3d8285a236245220ae32cc3799c` | **Derived from #15.** 207,129 data rows |

Total local footprint: roughly 300 MB, of which about 90 MB is downloaded bytes
and the rest is extracted geodatabases and decompressed samples.

**Full compressed size of each sampled AIS day**, read from the server's
`Content-Length` on the retrieval date. Used only to scale the volume estimate,
and recorded because those files were deliberately *not* retrieved in full:

| Day | Compressed size |
|---|---|
| `AIS_2024_07_15.zip` | 395,954,655 bytes |
| `AIS_2024_08_15.zip` | 417,410,095 bytes |
| `AIS_2024_09_16.zip` | 367,566,530 bytes |
| `AIS_2024_10_15.zip` | 333,802,661 bytes |
| `AIS_2024_11_15.zip` | 329,394,301 bytes |

### Reproducing the M2 statistics

Every computed figure in this register and in decision records
[0002](decisions/0002-southern-california-study-area-extent.md) through
[0006](decisions/0006-report-vessel-speed-separately.md) is regenerated by:

```
python tools/m2_verify.py verify
```

This checks the manifest above against the local files and then recomputes the
schema and feature counts, value ranges and percentiles, AIS row populations and
filters, geographic subset counts, VSR geometry checks and area, and the study-area
candidate comparison. Tool versions and the exact invocation are recorded in
[../tools/README.md](../tools/README.md).

**Figures that are not regenerable are not quoted.** Where a value in this
register came from a publisher's webpage or PDF rather than from a computation,
the source is named at the point of use.

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

**Verification status: schema, values and data quality verified by inspection of downloaded records; field semantics, units, coverage and terms verified from the publisher's own documentation** (retrieved 2026-08-25). Volume figures are **extrapolations from a 34-minute sample** and are labelled as estimates throughout, not measurements.

### Selected product

| | |
|---|---|
| **Product** | AIS Broadcast Points, daily nationwide files |
| **Publisher** | NOAA Office for Coastal Management (Marine Cadastre), from U.S. Coast Guard Nationwide AIS (NAIS) |
| **Bulk directory** | `https://coast.noaa.gov/htdata/CMSP/AISDataHandler/{year}/` — one `AIS_YYYY_MM_DD.zip` per day, 365/366 per year |
| **Custom extracts** | AccessAIS — <https://coast.noaa.gov/digitalcoast/tools/ais.html> |
| **Documentation** | AIS FAQ (May 2026) — <https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf>; Vessel Type and Group Codes — <https://coast.noaa.gov/data/marinecadastre/ais/VesselTypeCodes2018.pdf> |
| **Retrieved** | 2026-08-25 |

**Requested citation** (from the FAQ): "NOAA Office for Coastal Management. ([Year]). [Title of Dataset]. Marine Cadastre. https://marinecadastre.gov."

**What was actually downloaded.** No national dataset was retrieved. `AIS_2024_07_15.zip` is 395,954,655 bytes and expands to 1,077,218,608 bytes. The server supports byte ranges, so **only the first 8 MB was requested** and the deflate stream was decompressed in place, yielding 207,849 real records. The records are ordered by time, so this prefix is a **nationwide snapshot covering 34 complete minutes** — spatially complete, temporally tiny. That is what every finding below was read from.

### Verified schema

Header, exactly as it appears in the file:

```
MMSI,BaseDateTime,LAT,LON,SOG,COG,Heading,VesselName,IMO,CallSign,VesselType,Status,Length,Width,Draft,Cargo,TransceiverClass
```

| Field | Meaning and units | Established from |
|---|---|---|
| `MMSI` | Maritime Mobile Service Identity, 9 digits. The FAQ names MMSI, IMO and CallSign as the stable identifiers; `VesselName` is mariner-entered and changes | FAQ; file |
| `BaseDateTime` | ISO 8601, no offset suffix. **UTC** — "All time stamps in the NMEA record use Coordinated Universal Time (UTC)." Down-sampled "to the nearest whole minute" | FAQ; format confirmed in file |
| `LAT`, `LON` | Decimal degrees, 5 decimal places, WGS 84 | File |
| `SOG` | Speed over ground in **knots**. **102.3 is the "not available" sentinel** | FAQ; sentinel confirmed in file |
| `COG` | Course over ground, degrees. **360.0 means unavailable and should be ignored** | FAQ; confirmed in file |
| `Heading` | Degrees. **511 means not available** | FAQ; confirmed in file |
| `VesselType` | AIS ship-and-cargo-type code, 0–99 standard NMEA. Grouped into Cargo, Tanker, Passenger, Tug Tow, Fishing, Pleasure Craft/Sailing, Military, Other by the published code table | Vessel Type and Group Codes PDF |
| `Status` | AIS navigational status code | AIS standard |
| `Length`, `Width` | Metres | FAQ |
| `Draft` | Metres at 1/10 m resolution for 2015-present | FAQ |
| `Cargo` | "For practical purposes, cargo codes are identical to vessel types" | FAQ |
| `TransceiverClass` | `A` or `B`. Class B is present from 2015 and the designation is provided per record after 2017 | FAQ; both values present in file |

**Gross tonnage is not present, and cannot be.** The FAQ is explicit: *"Are parameters like tonnage, horsepower, or fuel type included? No, these parameters are not part of the standard AIS broadcast."* The VSR program's 300 GT threshold therefore **cannot be applied directly to these data** — see "Defining the commercial-vessel population" below.

**Vessel attributes are corrected, not raw.** Since January 2024 the AIS Vessel Identification Database (AVID) populates nulls and fixes gross errors in vessel-dependent fields, "correcting approximately 10–15 percent of records". The 2024 sample inspected here is AVID-corrected. Between 2015 and 2023 the predecessor AVIS did the same, and the uncorrected `vessel_type` for that period survives in the `Cargo` field.

### Verified data quality

Measured on the 34-minute national window (202,530 records) and on its Southern California subset — lon −122.5 to −117.0, lat 32.0 to 35.2 — of 13,483 records.

| Check | Result |
|---|---|
| Coordinate sentinels | **None.** No `LAT`=91, no `LON`=181, no (0,0), nothing outside ±90/±180. LAT spans 14.20–49.67, LON −159.65 to −63.10 |
| Fully identical duplicate rows | 3 in 207,849 — 0.001% |
| Duplicate `(MMSI, BaseDateTime)` | 16 — 0.008% |
| Malformed MMSI | 50 records not 9 digits; 26 beginning with `0` — together 0.024% |
| Missing values | `LAT`, `LON`, `SOG`, `COG`, `Heading`, `MMSI`, `BaseDateTime`, `TransceiverClass` are **never** missing. `IMO` missing 37.3%, `Status` 32.6%, `Draft` 32.6%, `Cargo` 32.5%, `CallSign` 14.4%, `Width` 2.9%, `Length` 1.6%, `VesselType` 0.1% |
| `SOG` sentinel in the SoCal subset | 66 records at 102.3; no negative values; no other value above 40 knots |
| `Heading` unavailable | 52.6% of national records are 511 |
| `COG` unavailable | 16.5% of national records are 360.0 |
| Sort order | Time-ordered but **not strictly**: 374 records in the sample carry timestamps 12+ hours later than their neighbours. Any processing that assumes monotonic time within a file will be wrong |

**The obvious position errors have already been removed upstream.** This is better than the register anticipated: no invalid-coordinate cleaning rule is needed for gross errors. Plausibility filtering against vessel behaviour is still the project's responsibility.

### Verified reporting interval

Time between consecutive records for the same MMSI, Southern California subset:

| Population | Median gap |
|---|---|
| All vessels | 175 s |
| Commercial (types 60–89) | 71 s |
| Commercial and moving (SOG ≥ 1 kn) | 70 s |

Gaps cluster near 60–70 s, 180 s and 360 s. This is consistent with the FAQ's statement that raw NMEA is down-sampled to the nearest whole minute, with the longer clusters representing reception gaps rather than a different transmission rate. **Roughly one position per minute per moving commercial vessel is the practical resolution.**

### Verified volume — estimates, not measurements

Extrapolated from the 34-minute window. Rates are linear extrapolations and take no account of diurnal or seasonal variation.

| Quantity | Estimate |
|---|---|
| National records per day | **≈ 8.6 million** |
| Cross-check | 1,077,218,608 uncompressed bytes ÷ 8.6 M ≈ 125 bytes/record — consistent with the observed row width |
| Southern California box, share of national | 6.66% |
| Southern California box, records per day | **≈ 571,000** |
| Southern California box, over a 254-day VSR season | **≈ 145 million records** |
| Distinct MMSI in the box during 34 minutes | 1,263 |

**This is the volume constraint the roadmap anticipated, and it binds.** Two retrieval routes exist and neither is comfortable:

- **Bulk download.** Getting one VSR season for the study area means downloading 254 national daily files at ~396 MB each — **roughly 100 GB of transfer** to keep ~2% of it. Filtering happens locally.
- **AccessAIS.** Requests are capped: *"For requests under 2 GB, use the AccessAIS application."* At ~125 bytes/record, 145 million records is on the order of **18 GB**, so a full season for the study area **cannot be a single AccessAIS request** and would need splitting. AccessAIS also holds only a five-year rolling window, adds data every 90 days with a 145–165 day lag, and its links expire after 14 days or five accesses.

Either route is workable but neither is trivial, and the choice belongs to the processing milestone.

### Defining the commercial-vessel population

**The AIS type groups map cleanly onto the BWBS eligible vessel types.** BWBS names "Bulk, tanker, auto carrier, container ships and passenger vessels". In the published Marine Cadastre code table those fall into three groups:

| BWBS eligible type | AIS group | Codes |
|---|---|---|
| Bulk, auto carrier, container | Cargo | 70–79 |
| Tanker | Tanker | 80–89 |
| Passenger (incl. cruise, new for 2026) | Passenger | 60–69 |

Measured on the Southern California subset, types 60–89 are **2,448 of 13,483 records — 18.2%**, from 154 distinct MMSI. The other 82% is dominated by pleasure craft (type 37, 39.7%) and sailing (type 36, 16.1%). **Vessel-class filtering is therefore the single most consequential processing choice for this input**, far more than any later smoothing or aggregation decision.

**The 300 GT threshold has no direct equivalent and must be approximated.** `Length` is the only size attribute available. Among the 153 distinct commercial MMSI with a length, the distribution is strongly bimodal:

| Length band (m) | Distinct MMSI |
|---|---|
| 0–20 | 8 |
| 20–50 | 46 |
| 50–100 | 4 |
| 100–150 | 1 |
| 150–200 | 31 |
| 200–250 | 16 |
| 250–300 | 22 |
| 300–400 | 25 |

There is a near-empty gap between 50 m and 150 m separating small harbour and passenger craft from oceangoing ships. That gap is a convenient place to cut, **but it is not 300 GT** — 300 GT corresponds to a far smaller vessel than 100 m, so a length cut at the gap is more restrictive than the program's own criterion. **Any length threshold used is a project assumption, not the program's threshold, and must be labelled as such and tested for sensitivity.** Whether to apply one at all, on top of the type-group filter, is a processing-milestone decision.

### Verified coverage limitation

**This is the most important limitation of this input, and it is stated by the publisher.** The FAQ: *"Coverage is currently unavailable for remote Pacific territories, foreign waters, or waters extending more than 40 to 50 miles from the coast."* The data come from roughly 200 land-based receiving stations; **there is no satellite AIS in this product** — federal agencies that buy satellite AIS "are restricted from distributing satellite data to the public".

The sample bears this out. Records per 0.5° longitude band in the Southern California box:

| Longitude band | All records | Commercial 60–89 |
|---|---|---|
| −122.5 to −120.5 | 103 | 62 |
| −120.5 to −117.0 | 13,380 | 2,386 |

Traffic effectively disappears west of about −120.5. **The VSR zone extends far beyond that** — its vertex at (33.30, −121.21) sits hundreds of kilometres offshore — so the offshore portion of the zone is in water where AIS coverage is thin by construction. The FAQ notes that records *do* appear beyond normal radio range through tropospheric ducting and high-elevation receivers, and that these "should not be viewed as erroneous", but they are not a uniform sample.

**Consequence:** apparent low vessel activity in the offshore part of the study area may reflect receiver coverage rather than vessel behaviour. This must be stated wherever an offshore result is reported, and it is an argument for keeping the Version 1 study area within the well-covered nearshore band rather than extending it to the full offshore reach of the zone.

For orientation only, in the 34-minute snapshot 87.6% of Southern California commercial records fell inside the 2026 VSR zone (82.7% for vessels ≥100 m). **This is a snapshot, not an analytical result**, and is recorded here as evidence that the data and the zone geometry line up sensibly — not as a finding about traffic.

### Licensing, attribution, and redistribution

**This is the clearest licensing position of the three sources, and it explicitly permits what the project needs.**

The FAQ answers the question directly:

> **Can I use and redistribute these data on other websites?**
> Yes, you may release derived products built from these data. Please cite your data source to promote transparency.

The underlying USCG condition, quoted in the same FAQ, is narrower about the raw records:

> These data are derived from the U.S. Coast Guard NAIS subject to the conditions of data sharing category "Level C (Historical Data)" … The historical data are generally considered public domain.
>
> All provided data may not be used for purposes other than those intended for the disclosure. Foreign governments, Federal, State, local and tribal government agencies, and non-governmental entities shall not retransmit or redistribute AIS information (real-time or stored) in any form other than those intended for the disclosure as approved, and shall not charge a fee for its usage.

NOAA's own terms are the standard 17 U.S.C. § 403 public-domain statement.

**Assessment:** publishing a **derived, aggregated** traffic layer with citation is expressly allowed. Republishing **raw broadcast points** is not what these terms contemplate, and the project should not do it. Charging for the result is prohibited. The FAQ also states these data "are intended for coastal and ocean planning purposes only" and not for regulatory or enforcement purposes — which matches the project's own non-goals.

### Considered and not selected as the primary input

| Candidate | Assessment |
|---|---|
| **AIS Vessel Transit Counts** — NOAA OCM, 2009–2025, 100 m cells, defined as "the actual number of unique vessel tracks passing through a specified cell". Services at `https://coast.noaa.gov/arcgis/rest/services/MarineCadastre/AISVesselTransitCounts{year}/MapServer`; public domain | **Rejected as the primary input, retained as a cross-check.** It is annual, so it cannot be restricted to the VSR season; it is published "All Vessels", so it cannot be filtered to the BWBS-eligible types that matter most; and it carries no speed. The service inspected is a rendered raster layer, not a value-queryable one. Its virtue is that it is a NOAA-computed traffic surface at 100 m, which makes it a good independent check on the project's own aggregation. |
| **AIS Broadcast Points 2009–2015** | Different structure — three related tables rather than one flat CSV — and older. No reason to use it when 2015-onward flat files exist. |
| **Satellite AIS** | Not available. The publisher cannot distribute it. |

### Remaining unresolved

- **Which retrieval route the project uses** — bulk daily files versus chunked AccessAIS requests. Both work; the trade is transfer volume against request management. A processing-milestone decision.
- **Whether a length threshold is applied on top of the type-group filter**, and at what value. The data support a defensible cut but not the program's actual 300 GT criterion.
- ~~Whether the analytical period is one VSR season or several.~~ Resolved in [ADR 0005](decisions/0005-analytical-period.md): 1 July to 30 November 2024, because AIS is not published beyond 2024.
- Whether AccessAIS can filter by vessel type server-side, which would change the volume arithmetic substantially. Not established — the tool is interactive and was not exercised in this session.

### Anticipated limitations

- **Coverage is not uniform and degrades offshore** (verified above). This is the dominant caveat.
- Vessel-type coding is self-reported, though AVID now corrects 10–15% of records.
- Aggregating records to a grid conflates transit frequency with time spent in a cell. Whichever measure is used has to be named precisely — a vessel stopped at anchor emits roughly as many positions as one under way, so a naive point count measures presence, not passage.
- `Heading` is unavailable in over half of records and `COG` in a sixth; neither can be relied on.
- Speed is present and usable — `SOG` is populated, in knots, with a single well-documented sentinel and no negative or implausible values in the sample. **Whether speed enters the exposure index or is reported separately is a separate question**, settled in [ADR 0006](decisions/0006-report-vessel-speed-separately.md): reported separately.

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
