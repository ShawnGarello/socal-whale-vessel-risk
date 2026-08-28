# Roadmap

**Owns:** milestones, sequencing, current progress, and version direction.

Milestones are ordered by **dependency and outcome**, not by calendar date. No individual milestone carries a date. The only date in this project is the Version 1 target recorded in [project-brief.md](project-brief.md).

A milestone is not "in progress" because work has been thought about. It is in progress when something in the repository is changing for it, and complete only when every completion criterion below is satisfied.

**Status legend:** `Not started` · `In progress` · `Blocked` · `Complete`

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Project foundation | Complete |
| M2 | Data discovery and validation | In progress |
| M3 | Processing workflow | In progress |
| M4 | GIS application foundation | In progress |
| M5 | Core input layers | Not started |
| M6 | Whale–vessel exposure analysis | Not started |
| M7 | Application integration | Not started |
| M8 | Verification and reproducibility | Not started |
| M9 | Public release | Not started |

---

## M1 — Project foundation

**Status:** Complete

**Objective**
Establish the documentation baseline that everything else is built against: scope, sequencing, proposed architecture, source register, and working process. Get the project to a state where the next decision is a data decision rather than a scoping decision.

**Dependencies**
None.

**Deliverables**
- Relocated and preserved original project vision.
- Product scope document, roadmap, proposed architecture, data-source register, development process.
- Decision-record directory and format.
- Repository-level agent guidance.
- Recruiter-facing README.

**Completion criteria**
- The Version 1 question, scope, and non-goals are written down in one authoritative place.
- The initial architecture is documented, reviewed, and accepted, with its data-dependent decisions explicitly deferred.
- Every intended data source is registered with its verification status.
- No implementation directories, contracts, or schemas have been created.
- Documents do not contradict each other.

**Risks and open questions**
- The proposed architecture has not been reviewed against real data yet; parts of it may not survive M2.
- Documentation written before data inspection can encourage premature commitment. Anything unverified must stay labeled as unverified.

---

## M2 — Data discovery and validation

**Status:** In progress

> An independent audit of this milestone on 2026-08-26 found five problems: provenance claimed but not recorded, AIS record counts quoted inconsistently and snapshot results generalised into period facts, an analytical domain accepted on evidence that could not support it, a boundary method that would have made the headline statistic an artefact of the grid, and a retrieval policy that contradicted itself. All five have been corrected. The corrections **enlarged** the set of open questions rather than shrinking it, which is the honest outcome.

**Objective**
Obtain and inspect the actual candidate datasets, and determine what analysis the data can genuinely support. This milestone is where assumptions become findings.

**Dependencies**
- M1 (source register exists with the questions each source must answer).

**Deliverables**

| Deliverable | State |
|---|---|
| A small, retrievable sample of each candidate dataset, inspected locally | **Done.** Sixteen artifacts, each with a recorded size and SHA-256 |
| For each source: confirmed format, CRS, spatial extent and resolution, temporal coverage, value meaning and units, and licence or terms of use | **Done**, except redistribution terms for the VSR geometry |
| A written definition of the Southern California study area: extent, projected CRS, and analysis grid | **Partial.** Projected CRS ([0003](decisions/0003-projected-coordinate-system.md)) and grid ([0004](decisions/0004-analysis-grid-resolution.md)) are accepted. Extent is split: the **map extent is proposed**, the **analytical domain is open** ([0002](decisions/0002-southern-california-study-area-extent.md)) |
| A decision on the analytical period | **Done** ([0005](decisions/0005-analytical-period.md)) |
| A decision on whether vessel speed can be derived reliably from the available AIS records | **Done, with its evidentiary limits stated** ([0006](decisions/0006-report-vessel-speed-separately.md)). `SOG` is present, documented, and appears usable in the inspected sample; that is not the same as established across the period |
| Updated source register with verification status replacing every resolved "to be verified" entry | **Done**, with a provenance manifest and a utility that re-checks it |
| Architecture decision records for choices that constrain later work | **Done.** Five records, one of which is deliberately Proposed rather than Accepted |

**Completion criteria**

| Criterion | State |
|---|---|
| Every Version 1 input has an identified, retrievable, authoritative source with recorded provenance | **Met.** Source URL or query endpoint, method and parameters, retrieval date, local filename, byte size and SHA-256 are recorded for all sixteen artifacts in [data-sources.md](data-sources.md), and `python tools/m2_verify.py verify` checks them against the local files. This criterion was previously claimed as met when the checksums did not exist |
| The whale model layer's values are understood well enough to state what they mean in the application legend | **Met.** `DENSITY` is animals per km², publisher-defined, with a per-cell coefficient of variation |
| The AIS extract needed for the study area and analytical period has been scoped, and its volume is known | **Met, with the volume qualified.** The period is fixed and the retrieval footprint is bounded, but the volume is an **order-of-magnitude planning estimate** — 60 to 90 million study-area records, ≈56 GB of transfer — extrapolated from five 34-minute windows all at the same time of day. It is not a measurement and nothing analytical rests on it |
| The VSR boundary geometry is confirmed as obtainable from an authoritative source, or a documented derivation from published coordinates is agreed on | **Met.** A closed, land-clipped polygon is retrievable, and seven of the program's eight published points lie exactly on its boundary |
| Redistribution terms are known for each dataset, so it is clear what may be committed or hosted publicly | **Not met.** Clear for both NOAA sources. **Not clear for the VSR zone geometry** — publicly shared with attribution, but with no redistribution grant, and BWBS/CMSF is not a federal publisher |
| **The analytical and statistical domain over which headline results can be defended has been accepted** | **Not met.** [ADR 0002](decisions/0002-southern-california-study-area-extent.md) is Proposed. The map extent is settled; the domain is not, because AIS coverage offshore is unestablished and cannot be established from the broadcast points themselves. This criterion is not in the original M1 list — it was added on audit, because the milestone cannot honestly be called done while the region the statistics describe is undecided |
| Anything that cannot be verified is explicitly recorded as unresolved rather than assumed | **Met**, and this is what the audit repaired. Several things previously stated as established are now recorded as unresolved |

**M2 is not complete.** Three criteria are unsatisfied or qualified, and one deliverable — the study-area definition — is only half done. **Two separate things are unfinished, and they block different work:**

- **The analytical domain blocks the analysis.** No exposure statistic and no inside-versus-outside figure can be produced or published until it is accepted.
- **VSR redistribution blocks project-hosted public sharing**, and keeps its own completion criterion unmet. It does not block the analysis: the statistics can be computed against the geometry either way, and the application can reference the publisher's service instead of hosting a copy.

Neither is more important than the other for calling M2 done — both criteria are unmet. The domain is the one that stops downstream work.

### Open items, in order of how much they constrain the work

1. **The analytical and statistical domain is undecided.** [ADR 0002](decisions/0002-southern-california-study-area-extent.md) is **Proposed**, not Accepted. NOAA states AIS coverage is unavailable more than 40–50 miles offshore, and 42.3% of the proposed water area — holding 34.6% of the in-box VSR zone — lies west of −120.5, where the sampled record density falls off. **A snapshot cannot distinguish sparse reception from low traffic**, and the two imply opposite treatments. Until a domain is accepted, **no inside-versus-outside statistic may be published.** Three candidates and the evidence each needs are in the record.

2. **Redistribution of the VSR zone geometry is unresolved.** Publicly shared by BWBS/CMSF with attribution and no stated prohibition, but no grant either, and the publisher is not a federal agency. Options: obtain permission, reference the published service rather than copy it, or substitute a federally published geometry. **Gates public hosting, not analysis.**

3. **The whale model's season definition is unconfirmed.** The survey basis is July–November; a redistributor describes the same models' predictions as late June to early December. [ADR 0005](decisions/0005-analytical-period.md) uses the conservative July–November reading and would need revisiting if the publisher states otherwise.

4. **The datum of the published VSR coordinates is unstated.** Assumed WGS 84, consistent with the geometry being served in EPSG:4326, but the program says nothing. At these latitudes a NAD 27 confusion would be on the order of 100 m.

5. **Deferred to M3 rather than blocking M2**, but named so they are not rediscovered: the AIS retrieval route (the one-day AccessAIS direct-CSV compatibility exercise passed, but the route remains Proposed because independent transfer completeness and scaling are unresolved; guarded bulk fallback permitted — see [../data/README.md](../data/README.md)); whether AccessAIS can filter by vessel type server-side; and whether a length threshold is applied on top of the vessel-type filter, and at what value.

### What M3 may safely begin, and what must wait

**May begin now.** None of these depends on where the reporting boundary lands, and the work has to happen regardless:

- AIS retrieval and the route decision, over the full map extent.
- Cleaning, deduplication, sentinel handling, and vessel-class filtering.
- Reprojection of all three inputs to EPSG:3310.
- Construction of the 5 km grid and the per-cell water geometries.
- Area-weighted transfer of the whale model onto the grid, conserving abundance.
- The fractional-intersection machinery and its synthetic tests ([ADR 0004](decisions/0004-analysis-grid-resolution.md)).
- Vessel aggregation onto the grid.

Doing this work gives a far better picture of the traffic the receivers recorded than five half-hour windows do. **It does not settle item 1**, and an earlier version of this roadmap wrongly implied it would. No amount of the same broadcast-point data reveals vessels no receiver heard, so the coverage question has to be answered from outside it — from NOAA's published limit, from the geometry of the receiver network, or from an independent source. See [ADR 0002](decisions/0002-southern-california-study-area-extent.md).

**Must wait for the analytical domain.**

- Any published inside-versus-outside figure.
- Any exposure surface presented as covering the full map extent.
- Any statement in the application about offshore vessel activity.

**Must wait for the redistribution question.** Hosting the VSR geometry as a project-owned layer. Displaying it by referencing the publisher's service does not.

### What was established

Detail is in [data-sources.md](data-sources.md); this is the summary that changes later work.

- **The whale model is vector polygons, not a raster** — 12,257 cells in EPSG:4326 on a 0.1° equal-angle grid, values in animals per km², with a coefficient of variation per cell. It is a **single summer–fall multi-year average, not a time series**, which removes any possibility of seasonal claims from this input.
- **AIS carries no gross tonnage**, so the VSR program's 300 GT criterion cannot be applied directly and any size filter is a project assumption.
- **NOAA states AIS coverage is unavailable beyond 40–50 miles from shore**, and the sampled record density falls off in a way consistent with that. The VSR zone extends well past it. This is the most consequential finding of the milestone and it is what reopened item 1 above.
- **2025 AIS broadcast points are partial through September 30.** NOAA's current vessel-traffic page lists data through 2025, and its January 2026 point-data summary records 273 daily 2025 files covering January 1–September 30 in the new `.zst` compression format. The accepted July–November period therefore cannot be completed from 2025, and 2026 data is not listed. Version 1 pairs the current zone with 2024, the latest published year covering the complete accepted period, and says so.
- **The VSR zone's eight published points do not define a polygon** — they are the seaward boundary only — but a closed geometry is published separately and matches them at seven of eight vertices, the eighth by 455 m.
- **Commercial vessel types were 18.2–20.7% of Southern California records** across five sampled windows. A snapshot result: five dates, one time of day, and the direction of any daily bias is unknown. What it supports is the conclusion that **vessel-class filtering is the most consequential processing choice for this input**, which holds across the sampled range and does not depend on the exact share.

**Decisions recorded**

**Accepted:** [0003](decisions/0003-projected-coordinate-system.md) EPSG:3310 · [0004](decisions/0004-analysis-grid-resolution.md) 5 km grid with fractional VSR-boundary accounting · [0005](decisions/0005-analytical-period.md) 1 July – 30 November 2024 · [0006](decisions/0006-report-vessel-speed-separately.md) speed reported separately.

**Proposed, not accepted:** [0002](decisions/0002-southern-california-study-area-extent.md) study area. Map and context extent settled; **analytical and statistical domain open.**

**Risks and open questions**

- ~~The whale distribution model may not be published at a resolution or in a format that is directly usable.~~ **Resolved:** directly usable, though as vector polygons rather than the raster the architecture also allowed for.
- ~~AIS volume for the study area may be large enough to force a narrower analytical period or a coarser aggregation.~~ **Partly realised:** volume is large — an estimated ≈56 GB of transfer for the chosen period — but the period was narrowed by data availability rather than by volume.
- ~~The authoritative VSR boundary may only be published as text coordinates or as a map image.~~ **Resolved:** a downloadable closed geometry exists.
- ~~Whale-model and AIS temporal coverage may not overlap cleanly.~~ **Realised, differently than expected:** the whale model has no time dimension at all, so there was nothing to overlap. Version 1 pairs a climatological surface with a fixed traffic window and states both vintages.
- **Licensing may restrict redistribution of a processed derivative.** **Still open**, and now specific: it is the VSR zone geometry, not the NOAA data.
- **AIS coverage offshore is unestablished, and it constrains the analytical domain rather than merely the wording.** This was recorded during discovery as a limitation and, on audit, upgraded to an open decision. It is the milestone's principal unfinished item.
- **New:** discovery findings can be written more confidently than the evidence behind them supports. Five such overstatements were found by audit in this milestone alone. The provenance manifest and [`tools/m2_verify.py`](../tools/m2_verify.py) exist so the next reader can check a number rather than trust it.

---

## M3 — Processing workflow

**Status:** In progress

**Objective**
Turn raw source data into validated, derived geospatial datasets through an ordered, repeatable process.

**Dependencies**
- M2 **in part.** Data confirmed, projection and grid defined, analytical period chosen. The **analytical and statistical domain is not defined** — [ADR 0002](decisions/0002-southern-california-study-area-extent.md) is Proposed — so M3 proceeds over the map extent and the exposure statistics in M6 wait. See the M2 entry for the split of what may begin now.

### Progress

**Foundation, first AIS processing slice, projected water grid, and whale transfer implemented and verified**

- A Python 3.13 src package exists under [`../analysis/`](../analysis/) with a
  committed `pyproject.toml` and `uv.lock`. uv sync/lock, Ruff format/lint,
  strict mypy, pytest, package build, and the module CLI boundary are configured.
  The toolchain is recorded in [ADR 0011](decisions/0011-use-uv-for-the-python-analysis-toolchain.md).
- DuckDB is the single production large-tabular engine. A parameterized,
  read-only benchmark compared it with Polars on the same 22.7 MB M2 AIS sample
  and equivalent operation; both returned 13,800 filtered rows in 35 groups.
  The five-run evidence and its half-hour-sample limits are in
  [ADR 0012](decisions/0012-use-duckdb-for-large-tabular-processing.md).
- Versioned contracts now cover configurable source locators, the proposed ADR
  0002 map/context extent, the accepted 1 July–30 November 2024 analytical
  period, EPSG:3310, the accepted 5 km grid, the exact inspected AIS header and
  sentinels, the selected 2020b blue-whale layer and its value relationships,
  the VSR source geometry, and versioned provenance/lineage and run-metadata
  contracts.
- The configuration represents the analytical domain only as **unresolved** and
  rejects any other status. There is no exposure formula, exposure/statistics
  contract, or application-results contract.
- Read-only CLI commands validate configuration and supplied AIS CSV, whale
  File Geodatabase, and VSR GeoJSON paths. They produce JSON diagnostics and no
  analytical output.
- `process-ais` cleans one explicitly supplied, nonempty NOAA flat CSV extract
  whose valid timestamps belong to exactly one UTC date. A partial-day extract
  is allowed, but the quality report records its earliest and latest valid
  timestamps and marks completeness `unverified`; the contract does not promise
  a complete day. The atomic bundle contains deterministic Parquet and a quality
  report plus lineage/run metadata with real UTC execution timestamps kept
  separate from the configured analytical period. It validates the inspected
  header; parses UTC timestamps,
  coordinates, MMSI, reported SOG, and vessel types; scopes positions to the
  ADR 0002 map extent; selects passenger 60–69, cargo 70–79, and tanker 80–89;
  normalizes documented sentinels; and records every removal. Exact duplicates
  and conflicting MMSI/timestamp records follow
  [ADR 0013](decisions/0013-remove-conflicting-ais-key-records.md). The command
  refuses header-only input, input with no valid timestamp, multi-date input,
  raw-directory output, arbitrary overwrite, and incomplete publication.
- Length filtering and behavioral plausibility filtering are explicitly
  disabled and recorded as unresolved project assumptions. No length value is
  presented as equivalent to the BWBS approximately 300 GT condition, and no
  universal speed or implied-speed threshold has been selected.
- [ADR 0017](decisions/0017-prefer-accessais-with-guarded-bulk-fallback.md)
  records the **Proposed** AIS retrieval policy. AccessAIS is preferred when an
  author-submitted order satisfies its documented constraints, with guarded
  one-day-at-a-time bulk retrieval as the proposed fallback. The read-only
  AccessAIS estimator endpoint observed during research is an undocumented web-
  application interface and must not be treated as a stable production API.
  A separate local command now inspects and manifests one explicit supplied
  artifact, with content-based CSV/ZIP detection, safe member and CRC checks,
  exact-header and expected-date validation, immutable retry/conflict behavior,
  optional atomic interim extraction, and an optional checksum-bound bridge to
  the existing cleaner. The manifest starts with all 153 accepted dates and
  cannot report period completion from one verified request. Materialization
  binds extraction to the inspected byte size and SHA-256. The real bounded
  15 July AccessAIS direct CSV passed local byte-identity, exact-header/date,
  and cleaner-compatibility checks. Independent byte completeness remains
  unverified because no HTTP length or object validator was retained;
  observational completeness and the full analytical-period retrieval also
  remain unverified.
- [ADR 0018](decisions/0018-use-vessel-kilometres-for-grid-activity.md)
  records the **Proposed** vessel-activity aggregation design.
  Vessel-kilometres is the proposed primary additive grid metric. Group-specific
  distinct MMSI and MMSI-date counts remain descriptive; their all-commercial
  values must be recomputed as unique MMSIs and MMSI-date pairs from the union
  of retained commercial points rather than summed across passenger, cargo, and
  tanker groups. The modeled-whale-support geometry is biological model
  support, not an authoritative shoreline, general water mask, or AIS
  observability boundary. The production segment/grid process and the
  unresolved gap, implied-speed, edge-support, and vessel-length parameters
  have not been implemented or settled.
- An isolated, read-only vessel-activity evidence harness now validates one
  explicit current cleaner bundle and constructs deterministic consecutive
  pairs for diagnostics. It reports group and commercial-union observation and
  distinct counts, gaps, zero-length segments, group changes, non-increasing
  time, EPSG:3310 and WGS 84 geodesic endpoint distances, their differences,
  implied speed, and separately named reported-SOG availability. Gap,
  implied-speed, and length candidate values have no defaults and are accepted
  only as explicitly supplied, labelled evidence values. The deterministic
  atomic JSON output is restricted to ignored `data/interim/`; actual execution
  timestamps stay outside its content identity.
- The optional evidence-only allocation path validates the exact
  `projected_water_grid_v1` contract and checksum, transforms with explicit x/y
  order, and intersects actual modeled-whale-support geometry separately for
  the unfiltered structural baseline and every explicitly supplied candidate
  scenario. It reports in-support and outside-support vessel-kilometres without
  interpreting outside support's cause, and verifies length conservation and no
  duplicate allocation. Its deterministic identity excludes local input paths
  while retaining them as provenance. It emits no per-cell vessel-activity
  dataset. Synthetic tests passed. The author also exercised the partial harness
  against the real bounded 2024-07-15 cleaned bundle and exact grid: 113,799
  observations, 113,620 structural segments, 1,303 touched grid cells, passing
  conservation, and 25,560.766 km of unfiltered total parent segment distance.
  Of that distance, 24,096.858 km was inside the supplied modeled-whale-support
  grid and 1,463.908 km was outside that support. Runtime was 228.968 seconds and
  approximate peak working set was 243 MiB. The maximum implied speed was
  431,402 knots, confirming that the unfiltered baseline is diagnostic only and
  a plausibility rule remains unresolved. Source-transfer and observational
  completeness remain unverified. The harness remains partial because it does
  not calculate vessel-hours or per-cell candidate sensitivity; no production
  rule or vessel grid was produced.
- Manual smoke checks against the read-only M2 artifacts passed for the selected
  whale layer (12,257 features, with zero null, empty, or invalid geometries)
  and VSR polygon (one valid feature). The required 15 July AIS prefix smoke run
  read 207,849 rows, retained 13,800 in the map extent, selected 2,495 commercial
  rows before deduplication, and wrote 2,490 cleaned rows. It normalized the SOG
  sentinel in 22 retained rows, removed one additional exact duplicate and four
  conflicting-key rows, and wrote only to ignored `data/interim/`. This is
  evidence from the approximately half-hour M2 sample, not a full-day or
  period-wide result; the shared input was not changed. Valid timestamps span
  `2024-07-15T00:00:00Z` to `2024-07-15T15:40:54Z` because the source prefix is
  not strictly ordered. Those bounds do not establish continuous coverage, and
  completeness is `unverified`.
- The real bounded 2024-07-15 AccessAIS direct CSV was exercised read-only on
  2026-08-28. Its 59,497,346 bytes have SHA-256
  `694ea3e8364de21467dea0affeb77e954d339e155d316dc4115b87ac01ffcca3`;
  all 582,419 valid timestamps were on the requested date. Cleaning retained
  113,799 commercial rows with deterministic run ID
  `ais-362502c6a37b53e681b745f5` and cleaned SHA-256
  `efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`
  across two measured repeats. The expected raw-validator failure exposed 825
  invalid/missing MMSIs and 2,233 missing vessel types; the cleaner accounted
  for and removed them. Peak RSS of approximately 1.59 GiB is a scaling
  concern: monthly and full-period execution is not shown safe or authorized.
- A separate spatial CLI now takes an explicit mask path/layer, declared source
  CRS, output path, and optional configuration. It rejects missing, mismatched,
  empty, invalid, non-finite, or non-polygon input, transforms with explicit x/y
  ordering, constructs all 6,460 nominal cells from the accepted bounds, and
  clips the mask to the configured WGS84 map/context polygon after 0.01° edge
  densification and EPSG:3310 projection before intersecting each cell. Dry
  cells are omitted. Retained rows carry stable IDs, parent bounds, normalized
  water geometry, and actual water area in square metres and square kilometres.
- The local output is deterministic GeoParquet 1.1.0 with WKB and explicit
  EPSG:3310 metadata plus a JSON lineage sidecar. The process records source and
  output checksums, configuration digest, CRS transformation, feature counts,
  area totals, validation records, and run metadata. It writes through temporary
  files, refuses replacement without explicit authorization, and refuses output
  beneath `data/raw/`. Actual UTC execution timestamps remain separate from the
  deterministic content-derived run ID. This local format is not claimed to be
  ArcGIS publishing-compatible.
- [ADR 0014](decisions/0014-select-the-grid-water-mask.md) accepts the union of
  the land-clipped NOAA 2020b whale-model polygons as the Version 1 grid mask:
  the model's biological support, not an authoritative shoreline and not a
  future AIS observability mask. The processing API remains mask-agnostic.
- The combined self-contained suite has 155 passing tests using temporary
  synthetic CSVs, Parquet bundles, exact geometry, and in-memory records. It
  covers accepted/rejected configuration and period,
  source schemas, all documented AIS sentinels and malformed codes, whale
  geometry and abundance consistency, CRS/grid invariants, deterministic
  hashes, source locators, benchmark result checks, AIS filter and duplicate
  invariants, temporal coverage, deterministic AIS bundle replacement and
  sidecar integrity, the exact 95 × 68 grid, known full/half/partial water
  areas, CRS transformation,
  containment and area conservation, map-extent containment and boundary
  clipping, deterministic WKB/GeoParquet content identity, truthful execution
  timestamps, vessel evidence ordering and diagnostic arithmetic, explicit
  candidate sensitivity, union-recomputed distinct counts, exact segment-piece
  allocation and conservation, invalid grid inputs, deterministic evidence
  identity, overwrite and raw-output refusal, failed-run atomicity, and all CLI
  boundaries.
- A focused whale-grid command validates the selected NOAA/SWFSC source and the
  exact versioned water-grid input, reprojects source polygons with explicit x/y
  order, detects material source-interior overlap, and transfers modeled density
  by abundance-conserving EPSG:3310 intersection area. Conservation is checked
  independently by intersecting every source polygon with the unioned target
  water domain rather than reusing cell-allocation contributions. Its versioned
  GeoParquet preserves target cell identity, water area, geometry, and row order
  while adding modeled abundance allocation, modeled density, contributor
  count, and explicit source-support coverage fields. It does not normalize
  values, propagate coefficient-of-variation uncertainty, or implement exposure
  logic.
- Synthetic whale-transfer cases cover full and half-cell intersection,
  multiple-to-one and one-to-multiple allocation, partial water geometry,
  independently enumerated conservation including deliberately omitted cell
  intersections, ordering and identity, longitude/latitude axis handling,
  invalid CRS and density values, material and numerical source overlap,
  coverage gaps, invalid grid contracts and checksums, PyArrow read-back,
  lineage, deterministic output, overwrite, atomic failure, and CLI paths.
- Manual smoke checks against the read-only M2 artifacts passed for the selected
  whale layer (12,257 features, with zero null, empty, or invalid geometries)
  and VSR polygon (one valid feature). The raw AIS prefix was correctly reported
  as not yet processing-ready because it contains malformed/missing source
  values; no source file was changed.
- The corrected real derived smoke run used the selected whale layer read-only.
  It retained 4,516 of 6,460 nominal cells and omitted 1,944 dry cells, with
  107,728.695924 km² of biological-support water inside the configured map
  extent in EPSG:3310 and zero null, empty, invalid, or out-of-extent output
  geometry. This is 25 fewer cells and 2,970.781272 km² less than the
  pre-correction run. The 437,466-byte output has SHA-256
  `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`;
  an explicit-overwrite rerun reproduced the output checksum and deterministic
  run ID while recording different execution timestamps. Generated files
  remain under ignored `data/interim/`.
- Visual verification passed on 2026-08-27 in headless QGIS 4.2.1 with GDAL
  3.13.2. QGIS opened the exact GeoParquet directly, confirmed its EPSG:3310
  CRS, 4,516 MultiPolygon features, expected extent and area, and row/column
  orientation, then rendered five ignored high-resolution views. Inspection
  confirmed the correct Southern California location and axis order, alignment
  with the NOAA footprint and configured context boundary, clipped boundary
  cells, plausible coastline/island gaps, and no unexplained geometry or
  projection artifacts. The inspected output SHA-256 was
  `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`.
- The generated lineage sidecar truthfully records
  `visual_inspection_status: not_completed` because it was written before the
  QGIS check. Generation-time lineage must not be manually edited; the later
  QGIS report and documentation are separate evidence tied to the exact output
  checksum. An explicitly authorized overwrite currently replaces the output
  and sidecar without automatically retaining prior run evidence. A formal
  reusable verification record or command, plus append-only or versioned
  lineage, is **not implemented** and remains M3/M8 follow-up work.
- The real whale-transfer run used the selected 12,257-feature NOAA layer and
  verified the target grid SHA-256 before processing. It produced 4,516 unique
  ordered cells from 9,981 positive-area intersections. Three projected-source
  overlap residuals totaled 0.311235765 m² and none exceeded the accepted 1 m²
  numerical tolerance. Every cell had complete source support; the aggregate
  uncovered residual was 0.000000591 m². Source contribution and target
  allocation were both 344.1406562623342 modeled animals, for a conservation
  difference of 0.0. Independent PyArrow/Shapely read-back found zero invalid,
  empty, non-finite, or negative geometry/value records and confirmed byte-for-
  byte preservation of target IDs and geometry.
- Two clean whale-transfer runs produced byte-identical 523,986-byte
  GeoParquet files with SHA-256
  `421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62`.
  On 2026-08-27 QGIS 4.2.1 with GDAL 3.13.2 opened that exact ignored artifact
  directly as Parquet. Five rendered views confirmed correct Southern
  California placement and axis order, source/grid alignment, boundary
  behavior, coastline and island gaps, and a plausible broad source-scale
  modeled-density pattern, with no unexplained holes, slivers, displacement, or
  projection artifacts.

**Not implemented**

- Network AIS transfer, range-resume, and analytical-period retrieval. The local
  supplied-artifact validation, manifest boundary, and one real AccessAIS
  direct-CSV exercise are complete, but independent transfer completeness,
  monthly/full-period memory safety, a guarded daily bulk download, and the
  153-date retrieval remain unverified or unexercised.
- The production vessel-activity aggregation proposed in ADR 0018, including a
  multi-day segment manifest, accepted filtering rules, a final per-cell
  vessel-kilometres dataset, and validated period-wide distinct counts. The
  implemented one-bundle harness supplies partial diagnostics and optional
  non-production aggregate allocation only. One real bounded-day run occurred,
  but behavioral plausibility filtering, a maximum interpolation gap, an
  implied-speed rule, edge-support treatment, any vessel-length threshold,
  vessel-hours comparison, per-cell candidate sensitivity, and final speed
  summaries remain unimplemented, unexercised, or unresolved rather than
  receiving provisional values.
- Normalization of whale values or any vessel-derived spatial dataset. The
  whale input is grid-aligned without normalization; normalization remains part
  of the deferred exposure-method decision.
- A successful GDAL/Pyogrio read-back of the GeoParquet on this machine; its
  driver attempted to load a missing `duckdb.dll`. PyArrow read-back and
  GeoParquet metadata validation passed, but ArcGIS compatibility remains
  unverified.
- Lineage beyond the one-extract AIS bundle, projected water grid, and whale-grid
  transfer, or an end-to-end analytical-period rerun. These outputs are
  processing inputs, not analytical results.
- Anything gated by the unresolved analytical/statistical domain: the exposure
  calculation and surface, inside-versus-outside statistics, and their output
  contracts.

**Deliverables**
- A documented, ordered processing path from raw inputs to derived datasets, implemented as scripts or as recorded tooling steps.
- Clipping, reprojection, and normalization of each input onto the common study area and analysis grid, in EPSG:3310 ([ADR 0003](decisions/0003-projected-coordinate-system.md)) on the 5 km grid ([ADR 0004](decisions/0004-analysis-grid-resolution.md)).
- **A per-cell water geometry and its area**, produced by intersecting each grid cell with the water mask. This is an input to the fractional boundary accounting in M6, not a by-product, and the mask it comes from must be named and inspected.
- Vessel-activity aggregation from AIS records, with vessel-class filtering applied and documented.
- Vessel-speed summarization, if M2 confirmed it is supportable.
- Input-validation checks: geometry validity, CRS correctness, extent coverage, null and outlier handling.
- Recorded data lineage for each derived dataset — source, retrieval date, and the steps applied.

**Completion criteria**
- Each derived dataset can be regenerated from raw inputs by following the documented process.
- Rerunning the process on unchanged inputs produces equivalent outputs.
- Every filtering and aggregation choice is documented with its rationale.
- Per-cell water areas are computed from actual intersected geometry, not from a nominal cell size.
- Intermediate outputs have been inspected visually, not only programmatically.

**Risks and open questions**
- Raster–vector alignment and resampling choices can materially change results; the chosen approach must be justified.
- AIS records commonly contain implausible positions and speeds; the cleaning rules will need documenting and will affect outputs.
- QGIS exploration can reveal useful methods, but no production result may
  depend on manual edits or transformations. Any result-changing step must be
  implemented in the reproducible Python path.

---

## M4 — GIS application foundation

**Status:** In progress

**Objective**
Stand up the web application shell — the framework, the map, and the deployment
path — before there is analytical content to put in it.

**Dependencies**
- M1 (architecture reviewed and accepted).
- Independent of M2 and M3; can proceed in parallel with data work.

**Deliverables**
- Application scaffold created following the reviewed architecture.
- A working map view of the study area using the ArcGIS Maps SDK for JavaScript.
- Environment-variable and credential handling in place, with nothing secret committed.
- **A verified account-type capability check.** For ArcGIS Location Platform,
  record limited feature/vector-tile/map-tile service support, public access,
  storage, bandwidth, monthly free-tier headroom, and billing status. For
  ArcGIS Online, record organization access, publishing/public-sharing
  privileges, hosted feature/tile/imagery support, credits, and storage. The
  check does not enable pay-as-you-go or authorize spending.
- **When either Esri account type safely supports public hosted-feature
  publishing without paid usage**, a minimal test item published, shared
  publicly, and loaded from the application to prove that candidate route end
  to end. If neither does, the outcome is recorded and the public-layer
  end-to-end test waits for the selected non-Esri fallback route.
- A working deployment of the empty shell.
- Formatting, linting, and type-checking configured.

**Completion criteria**
- The application builds locally and in the deployment environment.
- The map renders, pans, and zooms over the study area.
- No API keys or credentials appear in the repository or in committed build output.
- The deployment is reachable and reflects the current main branch state.
- **The applicable account-type checks are complete and recorded.** Location
  Platform's limited data-service, storage, bandwidth, free-tier, and billing
  status and ArcGIS Online's organization privileges, public sharing, service
  types, credits, and storage are each confirmed or confirmed unavailable.
- If either Esri-hosted route safely supports the test, anonymous loading of the
  temporary hosted item is verified. Otherwise the outcome is carried into M5
  as evidence requiring a non-Esri publication-route decision; M4 does not
  invent or verify that fallback.

### Progress

Built on the `feat/web-foundation` branch. The application is in
[`../web/`](../web/); its commands and required environment variables are in
[development.md](development.md).

**Done and verified**

- Next.js 16.3.3 and TypeScript application scaffolded under `web/`, App Router,
  no backend, no database, no server-side analytical processing.
- Static export configured and verified: `npm run build` produces a complete
  static site in `web/out/`, which was served locally and loaded in Chrome.
- ArcGIS map shell with a basemap, an initial viewpoint over the Southern
  California Bight, a zoom control, a loading state, an initialization-error
  state, and SDK teardown on unmount. No project layers and no analytical
  content.
- Formatting (Prettier), linting (ESLint), type checking (`tsc --noEmit`), and
  tests (Vitest, 12 passing) configured and run.
- Credential handling: `web/.env.example` carries variable names only, all other
  `.env*` files are ignored, and no credential is tracked.
- Build output (`web/out/`, `web/.next/`) and `node_modules/` are ignored and
  are not committed.
- Responsive layout checked in Chrome at 390, 820, and 1440 CSS pixels wide: the
  shell fills the viewport with no horizontal overflow at any of them.
- Decisions recorded as [ADR 0007](decisions/0007-use-npm-for-the-web-application.md),
  [0008](decisions/0008-deliver-the-application-as-a-static-export.md),
  [0009](decisions/0009-mount-arcgis-through-client-only-map-components.md), and
  [0010](decisions/0010-use-vitest-for-typescript-tests.md).

**Not done**

- **The static-shell deployment.** This can proceed independently of an ArcGIS
  account. The application has never been deployed anywhere, and there is no
  public URL.
- **A successful basemap render.** This requires a valid, scoped API key. The
  shell is verified only to the point of failing correctly: with no API key it
  reports the problem in the interface. That the map renders, pans, and zooms
  with a valid key has **not** been observed.

- The account-type capability checks. Nothing has been established about
  Location Platform data-service support, public access, storage, bandwidth,
  monthly free-tier headroom, or billing status. ArcGIS Online organization,
  user type, role, publishing/public-sharing privileges, hosted service types,
  credits, and storage are also unverified.
- The conditional Esri-hosted test item and loading it from the application.
  This is attempted only if the applicable account branch establishes public
  hosted-feature support and enough no-cost capacity. The check requires the
  author's real account and never enables billing or authorizes spending.

The ordered steps for all of the above are in
[development.md](development.md#arcgis-account-type-capability-checks-and-service-access).

### Completion criteria status

| Criterion | State |
|---|---|
| Builds locally | **Verified.** `npm run build` succeeds; the export was served and loaded. |
| Builds in the deployment environment | **Unverified.** No deployment environment exists yet. |
| Map renders, pans, and zooms | **Unverified.** Requires an API key. The failure path is verified; the success path is not. |
| No credentials in the repository or committed build output | **Verified.** Staged diffs were scanned before each commit; build output is ignored. |
| Deployment reachable and reflecting main | **Unverified.** No deployment exists; main has not been deployed or verified. |
| Account-type capability checks complete and recorded | **Unverified.** Location Platform and ArcGIS Online checks have not started; they require the author's account. |
| Conditional Esri-hosted publish-and-serve test | **Unverified.** Attempt only if an applicable account branch verifies public hosted-feature support and enough no-cost capacity. |
| Unavailable capabilities recorded as constraints for M5 | **Not applicable yet.** Nothing has been checked, so nothing has been found unavailable. |

M4 is not complete and must not be marked complete until the deployed
application, successful API-key-backed map rendering, and the real account-type
capability checks are verified. An Esri-hosted publish-and-serve test is also
required when either account type safely supports it without paid usage. Any
unavailable capabilities must be recorded as publication constraints for M5;
selection and end-to-end testing of a non-Esri route happen in later milestones
after real layers exist.

### Findings

Recorded because they are version-dependent, were established by running the
tooling rather than reading about it, and constrain later work.

**Toolchain, as verified on the author's machine**

| Component | Version |
|---|---|
| Node.js | 22.16.0 (Next.js 16 requires `>=20.9.0`) |
| npm | 10.9.2 — the only package manager present |
| Next.js | 16.3.3 |
| React | 19.2.8 |
| ArcGIS Maps SDK for JavaScript | 5.1.20 (`@arcgis/core`, `@arcgis/map-components`, `@esri/calcite-components`) |
| Vitest | 4.1.11 |

**The SDK's widgets are deprecated as of 5.0**, and its web components are the
supported path forward. The shell uses components. Later milestones should not
reach for widgets when adding legends, layer lists, or popups.

**SDK assets load from the ArcGIS CDN by default.** Since 4.34 the npm packages
load their own styles and assets from `js.arcgis.com`, so no copy step is
needed. The deployed application therefore depends on that host being reachable.
A disconnected or network-restricted deployment would need assets copied locally
and `assetsPath` configured.

**A browser-delivered API key is required for the basemap.** Without one, the
basemap styles service returns 401 "Token Required". ArcGIS Location Platform
accounts have API-key management privileges by default; ArcGIS Online accounts
have different user-type and privilege requirements. Neither a configured key
nor a successful basemap request proves project-layer hosting. The deployed map
is not proven until a scoped, origin-restricted key works from the real origin.

**The SDK prompts for a sign-in by default, and this is wrong for this
application.** Left at its default, a rejected request opens the SDK's own
username and password dialog and waits — so a missing key looked like an
indefinite loading state with a sign-in prompt over it. The shell sets
`esriConfig.request.useIdentity = false`. Any later work that adds a secured
layer must not undo this without deciding, deliberately, that the application
should ask visitors to sign in.

**The SDK does not time out on its own,** and not every failure raises an event.
Initialization is bounded explicitly in the shell.

**Bundle size — the early look this milestone's risk list asked for.** The
static export is roughly 28 MiB across about 900 files, almost entirely ArcGIS
SDK chunks. That is on-disk size, not download size: the SDK is code-split and a
basemap-only page fetches a small fraction of it. Two consequences: any hosting
platform's file-count and size limits must be checked before it is chosen, and
initial load time should be measured on the real deployment rather than inferred
from this number. First development-server compile of the map route takes
40–55 seconds; subsequent compiles are fast.

**`next dev` generates its own agent guidance.** It writes `AGENTS.md` and
`CLAUDE.md` into the application directory on startup, which would compete with
this repository's own. Disabled with `agentRules: false`.

**Risks and open questions**
- **Both Esri-hosted routes are unverified and constrain publication.** Location
  Platform is limited to feature, vector-tile, and map-tile services and must be
  checked for public access, storage, bandwidth, free-tier headroom, and billing
  status. ArcGIS Online must be checked for organization privileges, service
  types, public sharing, credits, and storage. If neither fits, a later decision
  must select and verify a non-Esri public fallback. **Still entirely open.**
- Location Platform storage/bandwidth usage and ArcGIS Online credit/storage
  consumption could constrain iteration. The project does not enable
  pay-as-you-go or authorize spending. **Still open.**
- ArcGIS SDK licensing and API-key requirements for the intended hosting model need confirming before public deployment. **Partly resolved:** a browser-delivered, origin-restricted API key is required for the basemap, Location Platform accounts have API-key privileges by default, and the requirements for scoping a browser key are recorded in [development.md](development.md). The real account and successful service access remain unverified.
- Bundle size and initial load time of the SDK need an early look rather than a late one. **Resolved for size** — see the findings above. Load time still needs measuring on a real deployment.
- The hosting platform is still unchosen. Its requirements are now written down in [development.md](development.md), so the choice is constrained rather than open-ended.

---

## M5 — Core input layers

**Status:** Not started

**Objective**
Prepare the validated input datasets for public delivery and make them visible
in the application through the evidence-selected publication route.

**Dependencies**
- M3 (validated derived datasets exist).
- M4 (application shell exists and account-type capability evidence is recorded).

**Deliverables**
- Study area, VSR boundary, whale density, and vessel activity prepared in a
  selected public representation based on measured output size, browser
  performance, redistribution terms, and real account capabilities.
- ArcGIS Location Platform feature/vector-tile/map-tile services when its
  verified free-tier capacity and service support fit; ArcGIS Online hosted
  layers and a web map when verified organization capabilities fit; or a
  documented non-Esri public route selected later when neither does. No route
  is implemented yet.
- The ArcGIS Maps SDK application assembling the public layers with symbology
  chosen for legibility, not decoration.
- Layer visibility control and legends in the application.
- Popups or panels that state what each layer's values mean, including units.
- Recorded mapping from each public layer representation back to the validated
  derived dataset, output checksum, visual-verification evidence, and
  processing/export steps that produced it.

**Completion criteria**
- Each layer renders at the study-area scale within an acceptable load time.
- Anonymous access works end to end from the application. When neither Esri
  hosting route is suitable, this criterion is verified later against the
  selected non-Esri fallback rather than waived.
- Every layer's legend states its units and the meaning of its values.
- Every layer names its source and its retrieval or processing date somewhere the user can reach.
- Layer geometry visually aligns across layers; no projection mismatch is visible.

**Risks and open questions**
- Layer size, feature-count limits, or browser performance may force a different
  representation, aggregation, or generalization.
- Raster and vector outputs may need different public delivery methods.
- Symbology for a continuous density surface needs a defensible classification, since the class breaks chosen will shape how the map is read.

---

## M6 — Whale–vessel exposure analysis

**Status:** Not started

**Objective**
Produce the project's own analytical result: a documented relative exposure layer, and the inside-versus-outside VSR statistics derived from it. This is the milestone that makes the project an analysis rather than a viewer.

**Dependencies**
- M3 (validated, grid-aligned whale and vessel inputs).
- M2 (understood value meanings and units for both inputs).

**Deliverables**
- A written definition of the relative exposure calculation: inputs, normalization, weighting, combination method, and units.
- The derived exposure or hotspot layer over the study area.
- Inside-versus-outside VSR statistics: share of total relative exposure, share of high-exposure area, and the threshold definitions used. **Computed by fractional area intersection** — each cell's water geometry is intersected with the VSR polygon and its exposure split by the resulting area fractions. Whole-cell, centroid, and majority-area assignment are all excluded; see [ADR 0004](decisions/0004-analysis-grid-resolution.md).
- **Tests of the fractional accounting** against the synthetic cases in ADR 0004, whose answers are known by construction, including the cell 45% inside the zone that centroid assignment scores as fully outside.
- Identification of the largest concentrations of exposure outside the zone.
- A sensitivity check showing how the reported statistics respond to the main arbitrary choices, particularly the high-exposure threshold and the normalization method.
- An assumptions-and-limitations record covering what the exposure index does and does not represent.

**Completion criteria**
- The exposure calculation is reproducible from the derived inputs.
- Every reported statistic states its basis — area, total exposure, or cell count — and its threshold.
- Boundary-derived statistics are computed fractionally, the synthetic cases pass, and the uniform-exposure-within-cell assumption is stated wherever such a statistic is reported.
- **The analytical domain has been accepted** ([ADR 0002](decisions/0002-southern-california-study-area-extent.md) is still Proposed). No inside-versus-outside figure is published before it is.
- The results are described in the vocabulary required by the project brief, with no risk or probability language.
- The sensitivity check is documented, including any case where a conclusion is not robust.
- The layer and the statistics are consistent: the numbers are computed from the published layer, not from a different intermediate.

**Risks and open questions**
- Combining a modeled density surface with an observed traffic measure implies choices about units and scaling that have no single correct answer; whatever is chosen must be justified and tested.
- Threshold-based "high exposure" statistics are sensitive to the threshold. Reporting a single number without sensitivity context would overstate certainty.
- Differing native resolutions between whale and vessel data force a resampling decision that can bias results toward one input.
- Edge effects at the **study-area** boundary may distort inside/outside comparisons where the extent truncates the zone at 35.0°N. This is separate from the **VSR zone** boundary, whose treatment is settled: fractional area accounting per [ADR 0004](decisions/0004-analysis-grid-resolution.md).

---

## M7 — Application integration

**Status:** Not started

**Objective**
Bring the analysis into the application so a visitor can explore the exposure layer and read the results without prior GIS knowledge.

**Dependencies**
- M5 (input layers publicly delivered and displayed).
- M6 (exposure layer and statistics exist).

**Deliverables**
- The derived exposure layer delivered through the selected public route and
  rendered in the application.
- A results panel presenting the inside-versus-outside statistics.
- Explanatory text stating what the exposure layer represents, in plain language, with its assumptions visible at the point of reading.
- Methodology and limitations reachable from the application, not only from the repository.
- Responsive behavior adequate for a reviewer opening the app on a laptop or phone.

**Completion criteria**
- The statistics displayed match the documented analysis exactly.
- A first-time visitor can tell what they are looking at without reading the repository.
- Limitations are visible in the interface, not hidden behind a link nobody clicks.
- No wording in the interface violates the project's scientific communication rules.
- The application remains usable on a mid-range connection.

**Risks and open questions**
- Presenting a single headline percentage invites overinterpretation; the framing needs care.
- Interactive exploration of a continuous surface may require a pre-rendered or
  tiled representation rather than raw values; the format remains open until
  the real output is measured.

---

## M8 — Verification and reproducibility

**Status:** Not started

**Objective**
Confirm that the results are correct, that the process can be rerun, and that the documentation matches what was actually built.

**Dependencies**
- M6 (analysis complete).
- M7 (application integrated).

**Deliverables**
- End-to-end rerun of the processing path from raw inputs, with outputs compared
  against the public layer representations.
- Verification that every statistic in the application traces to a processing step.
- Automated checks over analytical logic where it exists as code.
- A documentation audit against the implemented behavior, correcting anything described as built that is not, and anything built that is not described.
- Recorded source retrieval dates and dataset versions used for the published results.

**Completion criteria**
- A rerun reproduces the derived outputs behind the public layer
  representations.
- No documented capability is absent from the implementation, and no implemented capability is undocumented.
- Every published number is traceable to an input and a step.
- Known limitations are recorded in one place and referenced from the application.

**Risks and open questions**
- Unrecorded manual QGIS transformations would be a reproducibility gap. QGIS
  remains a verification tool; result-changing production steps belong in the
  tested Python path.
- Source datasets can be revised or withdrawn upstream, which is why retrieval dates and versions must be recorded.

---

## M9 — Public release

**Status:** Not started

**Objective**
Make the project publicly presentable: deployed, documented, and readable by a reviewer who has ten minutes.

**Dependencies**
- M7 (application integrated).
- M8 (results verified).

**Deliverables**
- Deployed application at a stable public URL.
- README updated with the live demo link, screenshots, and headline results.
- Methodology, provenance, assumptions, and limitations complete and linked.
- Repository cleaned of dead files, unused scaffolding, and stale documentation.
- Repository metadata — description, topics, license posture — set appropriately.

**Completion criteria**
- The deployed application works from a clean browser session with no local setup.
- The README communicates the question, the method, the result, and the limitations without requiring any other document.
- Every documentation link resolves.
- Nothing in the repository claims a capability that does not exist.
- Version 1 scope items in [project-brief.md](project-brief.md) are all satisfied or explicitly recorded as reduced, with the reason.

**Risks and open questions**
- **Public delivery depends on a verified publication route.** ArcGIS Location
  Platform limited data services or ArcGIS Online organization hosting may be
  used if the applicable account evidence supports the selected representation.
  If neither does, a non-Esri public fallback must be selected and verified end
  to end before release; none is implemented today.
- Location Platform storage/bandwidth limits and billing status or ArcGIS Online
  credits/storage are constraints if those routes are selected. The project
  does not enable pay-as-you-go or authorize spending. Any non-Esri host will
  have its own measured limits and operating constraints.
- Deployment hosting and any ArcGIS credential requirements must be settled before release, not at release.
- Screenshots and headline numbers go stale if the analysis is later revised; they need a stated "results as of" date.

---

## Version progression beyond Version 1

These are candidate directions for Version 2 and later. They are ordered roughly by how directly they build on Version 1, not by priority, and none is committed. Each requires its own data and methodology validation before it can be attempted, and each may prove infeasible with publicly available data.

Nothing in this section is a guaranteed scientific result. A proxy is a proxy, and a scenario is a hypothetical GIS experiment, not a finding and not a recommendation.

**UI/UX refinement**
Improve how the exposure layer is explained and read: legend and classification design, guided interpretation, comparison views, mobile layout, and accessibility. Depends on Version 1 being deployed and on observing where the current presentation misleads.

**Temporal analysis**
Break the overlap down by month or across the VSR season. Depends on the whale model and the AIS extract both supporting the intended time step, which M2 will determine. If the whale model is not time-varying at that step, seasonal claims cannot be made from it.

**Underwater-noise analysis**
Derive an estimated acoustic proxy from vessel traffic, vessel characteristics, and speed, following published methodology. Requires a defensible published method and the vessel attributes that method needs. AIS alone does not give sound levels, and any output must be presented as a modeled proxy with stated assumptions.

**Emissions analysis**
Estimate relative emissions intensity and how it varies with speed, following published methodology. Requires emission factors and vessel attributes that the AIS data may not carry. Any output is an estimate, not an inventory.

**Scenario analysis**
Compare how hypothetical zone geometries or exposure thresholds would change coverage of high-exposure areas. Depends on a Version 1 exposure layer whose sensitivity is already characterized, since scenario differences are only meaningful if the underlying index is stable. Framed as GIS experiments; the project does not recommend boundary changes.
