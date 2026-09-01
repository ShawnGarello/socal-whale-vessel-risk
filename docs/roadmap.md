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
| A small, retrievable sample of each candidate dataset, inspected locally | **Done.** Eighteen artifacts, each with a recorded size and SHA-256 |
| For each source: confirmed format, CRS, spatial extent and resolution, temporal coverage, value meaning and units, and licence or terms of use | **Done**, except redistribution terms for the VSR geometry |
| A written definition of the Southern California study area: extent, projected CRS, and analysis grid | **Done.** The map/context extent and scope-reduced `receivers_50_nautical_miles` analytical domain ([0002](decisions/0002-southern-california-study-area-extent.md)), projected CRS ([0003](decisions/0003-projected-coordinate-system.md)), grid ([0004](decisions/0004-analysis-grid-resolution.md)), and modeled-whale-support water geometry ([0014](decisions/0014-select-the-grid-water-mask.md)) are accepted and explicitly distinct |
| A decision on the analytical period | **Done** ([0005](decisions/0005-analytical-period.md)) |
| A decision on whether vessel speed can be derived reliably from the available AIS records | **Done, with its evidentiary limits stated** ([0006](decisions/0006-report-vessel-speed-separately.md)). `SOG` is present, documented, and appears usable in the inspected sample; that is not the same as established across the period |
| Updated source register with verification status replacing every resolved "to be verified" entry | **Done**, with a provenance manifest and a utility that re-checks it |
| Architecture decision records for choices that constrain later work | **Done.** ADR 0002 is accepted; the separate AIS retrieval and vessel-activity method records remain Proposed |

**Completion criteria**

| Criterion | State |
|---|---|
| Every Version 1 input has an identified, retrievable, authoritative source with recorded provenance | **Met.** Source URL or query endpoint, method and parameters, retrieval date, local filename, byte size and SHA-256 are recorded for all twenty artifacts in [data-sources.md](data-sources.md), and `python tools/m2_verify.py verify` parses that register and checks retained local copies against those identities. The two USCG PDFs added on 2026-08-31 matched their recorded identities. The separate [analytical-domain evidence command](analytical-domain-evidence.md#reproducible-calculation) regenerates the candidate-domain report and mask when its ignored inputs are present. This criterion was previously claimed as met when the checksums did not exist |
| The whale model layer's values are understood well enough to state what they mean in the application legend | **Met.** `DENSITY` is animals per km², publisher-defined, with a per-cell coefficient of variation |
| The AIS extract needed for the study area and analytical period has been scoped, and its volume is known | **Met, with the volume qualified.** The period is fixed and the retrieval footprint is bounded, but the volume is an **order-of-magnitude planning estimate** — 60 to 90 million study-area records, ≈56 GB of transfer — extrapolated from five 34-minute windows all at the same time of day. It is not a measurement and nothing analytical rests on it |
| The VSR boundary geometry is confirmed as obtainable from an authoritative source, or a documented derivation from published coordinates is agreed on | **Met.** A closed, land-clipped polygon is retrievable, and seven of the program's eight published points lie exactly on its boundary |
| Redistribution terms are known for each dataset, so it is clear what may be committed or hosted publicly | **Not met.** Clear for both NOAA sources. **Not clear for the VSR zone geometry** — publicly shared with attribution, but with no redistribution grant, and BWBS/CMSF is not a federal publisher |
| **The analytical and statistical domain over which headline results can be defended has been accepted** | **Met.** [ADR 0002](decisions/0002-southern-california-study-area-extent.md) accepts `receivers_50_nautical_miles`: 50 nautical miles, exactly 92,600 metres, from the relevant NAIS reception stations, not from the coast. It is a scope-reduced, system-performance-qualified AIS receiver domain, not empirical 2024 coverage. Unknown receiver uptime, station completeness, feed interruptions, antenna and terrain effects, and observational completeness remain limitations |
| Anything that cannot be verified is explicitly recorded as unresolved rather than assumed | **Met**, and this is what the audit repaired. Several things previously stated as established are now recorded as unresolved |

**M2 is not complete.** VSR redistribution remains unresolved and keeps its completion criterion unmet. The analytical-domain criterion is now met, but acceptance does not resolve or weaken the separate publication constraint.

- **VSR redistribution blocks project-hosted public sharing**, and keeps its own completion criterion unmet. It does not block the analysis: the statistics can be computed against the geometry either way, and the application can reference the publisher's service instead of hosting a copy.

### Open items, in order of how much they constrain the work

1. **Redistribution of the VSR zone geometry is unresolved.** Publicly shared by BWBS/CMSF with attribution and no stated prohibition, but no grant either, and the publisher is not a federal agency. Options: obtain permission, reference the published service rather than copy it, or substitute a federally published geometry. **Gates public hosting, not analysis.**

2. **The whale model's season definition is unconfirmed.** The survey basis is July–November; a redistributor describes the same models' predictions as late June to early December. [ADR 0005](decisions/0005-analytical-period.md) uses the conservative July–November reading and would need revisiting if the publisher states otherwise.

3. **The datum of the published VSR coordinates is unstated.** Assumed WGS 84, consistent with the geometry being served in EPSG:4326, but the program says nothing. At these latitudes a NAD 27 confusion would be on the order of 100 m.

4. **Deferred to M3 rather than blocking M2**, but named so they are not rediscovered: the AIS retrieval route (the one-day AccessAIS direct-CSV compatibility exercise passed, but the route remains Proposed because independent transfer completeness and scaling are unresolved; guarded bulk fallback permitted — see [../data/README.md](../data/README.md)); whether AccessAIS can filter by vessel type server-side; and whether a length threshold is applied on top of the vessel-type filter, and at what value.

### What M3 may safely begin, and what must wait

**May continue now.** These steps process the full map/context extent before the accepted analytical-domain mask is applied at the reporting boundary:

- AIS retrieval and the route decision, over the full map extent.
- Cleaning, deduplication, sentinel handling, and vessel-class filtering.
- Reprojection of all three inputs to EPSG:3310.
- Construction of the 5 km grid and the per-cell water geometries.
- Area-weighted transfer of the whale model onto the grid, conserving abundance.
- The fractional-intersection machinery and its synthetic tests ([ADR 0004](decisions/0004-analysis-grid-resolution.md)).
- Vessel aggregation onto the grid.

Doing this work gives a far better picture of the traffic the receivers recorded than five half-hour windows do. It does not turn the accepted system-performance-qualified domain into empirical 2024 coverage. No amount of the same broadcast-point data reveals vessels no receiver heard or reconstructs receiver and public-feed outages. See [ADR 0002](decisions/0002-southern-california-study-area-extent.md).

**The analytical-domain gate is resolved, but later work remains unimplemented.**

- Reporting-domain-dependent contracts may now use the accepted stable identity and semantics when M6 and M7 require them.
- Exposure formulas, surfaces, statistics, application results, and UI integration remain later milestone work and are not created by accepting the domain.
- No exposure surface may be presented as covering the full map extent, and no application wording may treat outside-domain cells as observed low traffic.

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

**Accepted:** [0002](decisions/0002-southern-california-study-area-extent.md) map/context extent and scope-reduced `receivers_50_nautical_miles` analytical domain · [0003](decisions/0003-projected-coordinate-system.md) EPSG:3310 · [0004](decisions/0004-analysis-grid-resolution.md) 5 km grid with fractional VSR-boundary accounting · [0005](decisions/0005-analytical-period.md) 1 July – 30 November 2024 · [0006](decisions/0006-report-vessel-speed-separately.md) speed reported separately.

**Risks and open questions**

- ~~The whale distribution model may not be published at a resolution or in a format that is directly usable.~~ **Resolved:** directly usable, though as vector polygons rather than the raster the architecture also allowed for.
- ~~AIS volume for the study area may be large enough to force a narrower analytical period or a coarser aggregation.~~ **Partly realised:** volume is large — an estimated ≈56 GB of transfer for the chosen period — but the period was narrowed by data availability rather than by volume.
- ~~The authoritative VSR boundary may only be published as text coordinates or as a map image.~~ **Resolved:** a downloadable closed geometry exists.
- ~~Whale-model and AIS temporal coverage may not overlap cleanly.~~ **Realised, differently than expected:** the whale model has no time dimension at all, so there was nothing to overlap. Version 1 pairs a climatological surface with a fixed traffic window and states both vintages.
- **Licensing may restrict redistribution of a processed derivative.** **Still open**, and now specific: it is the VSR zone geometry, not the NOAA data.
- **AIS observation remains unestablished outside the accepted receiver domain and incomplete observation remains possible inside it.** The author accepted a system-performance-qualified scope reduction, not empirical 2024 coverage; receiver uptime, station completeness, feed interruptions, antenna and terrain effects, and observational completeness remain limitations.
- **New:** discovery findings can be written more confidently than the evidence behind them supports. Five such overstatements were found by audit in this milestone alone. The provenance manifest and [`tools/m2_verify.py`](../tools/m2_verify.py) exist so the next reader can check a number rather than trust it.

---

## M3 — Processing workflow

**Status:** In progress

**Objective**
Turn raw source data into validated, derived geospatial datasets through an ordered, repeatable process.

**Dependencies**
- M2 **in part.** Data, projection, grid, analytical period, and analytical domain are accepted. M2 remains In progress only because VSR redistribution is unresolved; that question gates project-hosted sharing, not processing or analysis against the local geometry.

### Progress

**Foundation, first AIS processing slice, projected water grid, whale transfer,
and candidate vessel-grid aggregation implemented; candidate vessel-grid also
exercised with bounded two-day real data**

- A Python 3.13 src package exists under [`../analysis/`](../analysis/) with a
  committed `pyproject.toml` and `uv.lock`. uv sync/lock, Ruff format/lint,
  strict mypy, pytest, package build, and the module CLI boundary are configured.
  The toolchain is recorded in [ADR 0011](decisions/0011-use-uv-for-the-python-analysis-toolchain.md).
- DuckDB is the single production large-tabular engine. A parameterized,
  read-only benchmark compared it with Polars on the same 22.7 MB M2 AIS sample
  and equivalent operation; both returned 13,800 filtered rows in 35 groups.
  The five-run evidence and its half-hour-sample limits are in
  [ADR 0012](decisions/0012-use-duckdb-for-large-tabular-processing.md).
- Versioned contracts now cover configurable source locators, the accepted ADR
  0002 map/context extent and analytical-domain semantics, the accepted 1 July–
  30 November 2024 analytical period, EPSG:3310, the accepted 5 km grid, the
  exact inspected AIS header and sentinels, the selected 2020b blue-whale layer
  and its value relationships, the VSR source geometry, and versioned
  provenance/lineage and run-metadata contracts.
- The schema-1 upstream processing configuration and its established digest
  remain frozen for AIS cleaning, projected water-grid generation, whale-grid
  transfer, and map-extent vessel aggregation. A separate schema-1 downstream
  reporting-domain contract identifies the map/context extent, the
  modeled-whale-support water geometry, and the accepted
  `receivers_50_nautical_miles` system-performance-qualified AIS analytical
  domain. It preserves the exact fractional boundary rule and the unknown
  operational and observational limitations without invalidating existing M3
  artifacts. There is no exposure formula, exposure/statistics contract, or
  application-results contract.
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
- A versioned `accessais_period_delivery_v2` boundary now accepts one explicit
  author-supplied multi-date AccessAIS direct CSV or safe ZIP. It reuses the
  content-based and archive-safety checks, streams without materializing the
  delivery in Python, accounts for every valid, malformed/unassignable, and
  out-of-request timestamp row, and atomically publishes canonical exact-date
  cleaner inputs. DuckDB sorts the parsed 17-field rows by every field under an
  explicit memory limit and isolated ignored spill directory, while preserving
  duplicate multiplicity. Stable UTF-8/LF CSV serialization makes daily content
  identity independent of source order, quoting, and record endings. Immutable
  whole-delivery identity remains separate. Version 1 manifests remain
  recognizable and read-only valid, and Version 2 refuses an established
  Version 1 intake directory. Manifest validation binds every slice to exactly
  `daily/<UTC-date>.csv`; alternate spellings, traversal, and paths escaping the
  intake are refused. Row counts must be non-boolean integers, slice dates must
  equal the reported present requested dates, and each slice count must equal
  its date's `rows_by_utc_date` count rather than merely conserve the total.
  Intake and cleaner roots must be disjoint, and the period manifest cannot be
  placed inside either managed bundle.
- The intake orchestration cleans one daily slice at a time through the existing
  cleaner, verifies that each newly created bundle records the established
  daily-slice input SHA-256, and records compatible bundles immediately through
  `multiday_cleaned_ais_input_v1`. An interrupted retry skips only dates whose
  exact compatible cleaner identity is already recorded. Separate explicit
  deliveries can use unique intake directories while accumulating into the
  same cleaned root and 153-date period manifest. Synthetic integration tests
  verify disjoint deliveries, identical overlap, shared-root conflict refusal
  before canonical-bundle replacement, independently produced cleaner-identity
  conflict recording, preservation of earlier successes, and distinct conflict
  exit diagnostics. This implements local intake and preparation, not
  AccessAIS order submission, email/application automation, network retrieval,
  segment construction, or vessel aggregation.
- [ADR 0018](decisions/0018-use-vessel-kilometres-for-grid-activity.md)
  records the **Proposed** vessel-activity aggregation design.
  Vessel-kilometres is the proposed primary additive grid metric. Group-specific
  distinct MMSI and MMSI-date counts remain descriptive; their all-commercial
  values must be recomputed as unique MMSIs and MMSI-date pairs from the union
  of retained commercial points rather than summed across passenger, cargo, and
  tanker groups. The modeled-whale-support geometry is biological model
  support, not an authoritative shoreline, general water mask, or AIS
  observability boundary. A candidate segment/grid processing foundation
  is now implemented, but the gap, implied-speed, edge-support, and vessel-
  length choices remain unresolved and ADR 0018 remains Proposed.
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
  order, and calculates exact modeled-whale-support intersections once for the
  structural baseline. Every explicit candidate scenario filters and aggregates
  the same stable parent/piece cache. Each population reports all 4,516 cells,
  including zeros, with group and all-commercial segment-piece,
  vessel-kilometre and evidence-only vessel-hour diagnostics. Constant progress
  allocates positive-length time proportionally; zero-length time is assigned
  only for one unambiguous support cell, otherwise retained as outside or
  unallocated. Cleaned-point context reports per-cell observations and union-
  recomputed distinct MMSI/MMSI-date values, plus outside and ambiguous counts.
  Distance and time conservation and no duplicate allocation are verified.
- The author exercised `vessel_activity_evidence_v2` processing version `2.0.0`
  against the real bounded 2024-07-15 cleaned bundle and exact grid with no
  candidate thresholds: 113,799 observations, 113,620 structural segments,
  77,887 cached pieces, 1,303 touched cells, and 25,560.766048547 km parent
  distance (24,096.858442602 km inside support; 1,463.907605945 km outside).
  Parent vessel time was 3,672.903055556 hours (1,929.780498228 inside;
  1,743.122557328 outside; zero unallocated). Point context classified 71,482
  observations inside, 42,316 outside and one ambiguous. The deterministic
  report ID is `vessel-evidence-8432d5193107b94d88873201`; exact report SHA-256
  is `60e6a02be98d8cf5edd45af56a5adcfac001681a71e868dd438c4db0894a4d6e`,
  reproduced by a second clean output. The harness-recorded processing interval
  inside `run_evidence` was 25.007583 seconds; it begins after Python imports,
  CLI parsing and configuration loading and is not an end-to-end CLI runtime. A
  separate process-tree RSS sampling protocol took 59.562371 seconds and
  observed approximately 309.441 MiB peak. These observations used different
  protocols; sampling may have contributed overhead, but the measurements do
  not isolate its effect. Independent end-to-end CLI runs took approximately
  64.4 and 66.4 seconds while reproducing the exact report. Against the prior
  aggregate harness's 228.968-second observation, these measurements provide
  directional evidence of improved runtime, not a generally reproducible
  speedup factor. The approximate memory comparison with the prior 243 MiB
  measurement is also directional. The 431,402.639804-knot maximum confirms the
  baseline is diagnostic only. Source-transfer and
  observational completeness remain unverified; one day does not validate the
  period; edge support and production thresholds remain unresolved; no
  production vessel grid or exposure result was produced.
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
- The same real direct CSV was exercised through the bounded period-intake and
  orchestration path. Streaming intake assigned all 582,419 source rows to
  2024-07-15 with no malformed or out-of-request timestamps, emitted a byte-
  identical daily slice, reproduced the cleaner identity and 113,799-row
  Parquet checksum, and recorded one compatible date with 152 missing. The
  directly spawned end-to-end CLI took 83.735669 seconds and showed an
  approximate 990.379 MiB sampled process-tree RSS peak under a different
  protocol from the earlier cleaner measurement. This is backward-
  compatibility evidence for one direct-CSV date, not real multi-date or
  monthly scaling evidence; transfer and observational completeness remain
  `unverified`.
- The same immutable one-day source was rerun read-only through the updated
  accumulation gate on 2026-08-30. Source size/checksum, all 582,419 assigned
  rows, the byte-identical daily slice, the 113,799-row cleaner identity and
  Parquet checksum, and the one-compatible/152-missing period state were
  unchanged. A second invocation reused the delivery and skipped the compatible
  date. No new runtime or memory measurement was made. This is one-day
  regression evidence, not real multi-date evidence.
- The real Version 2 pilot ran the immutable one-day delivery first, then the
  separate 1,135,408-row 2024-07-15 through 2024-07-16 direct CSV through a
  different intake directory against the same cleaned root and period manifest
  on 2026-09-01. The two deliveries' 582,419-row 15 July multisets were equal
  under exact 17-field `EXCEPT ALL` comparison despite different source order.
  The corrected processing version `2.0.1` fresh rerun produced canonical daily
  SHA-256
  `bf5a46c6196cf8a51ebfd62907f085a093afa64e2d4474c71ab7f441e68cf5cd`,
  so 15 July was reused; 16 July's 552,989 rows were cleaned and recorded. The
  period ended with two compatible dates, 151 missing, and `not_ready` state.
  An identical retry reused both dates. Transfer and observational completeness
  remained `unverified`. Measured one-day/first-two-day/retry wall times were
  12.1394198/19.2814239/10.1271792 seconds, with sampled process-tree RSS peaks
  of 1,593,458,688/1,514,594,304/102,436,864 bytes. These bounded results are
  not extrapolated to monthly or full-period execution.
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
- The combined self-contained suite has 333 passing tests using temporary
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
  candidate sensitivity, union-recomputed distinct counts, exact reusable
  segment-piece allocation, proportional and zero-length time allocation,
  per-cell group/additive totals, point ambiguity, proof that scenarios do not
  repeat intersections, distance/time conservation, invalid grid inputs,
  deterministic evidence identity, overwrite and raw-output refusal, failed-run
  atomicity, multi-date delivery partitioning and row conservation, separate
  disjoint-delivery accumulation, identical overlap, shared-root conflict
  refusal, independently recorded cleaner conflict with prior-date preservation,
  and distinct conflict exit diagnostics, strict daily manifest paths and
  traversal refusal, strict count types and per-date
  reconciliation, managed-path separation, cleaner-input checksum binding,
  interruption/resume, a one-date period manifest leaving 152 dates missing,
  153 synthetic dates becoming ready,
  missing/duplicate/out-of-period/conflicting date
  entries, bundle-checksum and sidecar tampering, mismatched quality-report and
  run-metadata identities, path-independent period identity, cross-midnight
  ordering for one MMSI, absence of an artificial daily partition break,
  ordering stability regardless of recorded input order, one period identity
  across real and synthetic bundles regenerated at different paths and
  execution times, matching/mismatching/absent/partial retrieval
  `cleaning_reference` linkage, streamed DuckDB scanning without Python
  materialization, memory and spill validation, candidate whole-period pairing,
  explicit gap and implied-speed exclusions, exact multi-cell vessel-kilometre
  allocation, output conservation, zero-length/outside-support/boundary-
  ambiguity treatment, union-recomputed distinct-vessel output, deterministic
  candidate GeoParquet and quality JSON, manifest-provenance-independent output
  identity, evidence/candidate parity for their shared nonambiguous logic,
  sanitized execution settings in lineage, candidate-bundle atomicity and
  output safeguards, and all CLI boundaries.
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
- A versioned `multiday_cleaned_ais_input_v1` boundary now assembles explicitly
  supplied one-date cleaner bundles into one analytical-period input manifest.
  It initializes all 153 accepted UTC dates and keeps expected date,
  retrieval-manifest state, independently verified retained-byte/archive state,
  retrieval-to-cleaner linkage, cleaner-bundle compatibility,
  missing/conflicting status, and unverified observational completeness as
  separate states. Every supplied bundle is
  validated through the existing sidecar and checksum boundary: the exact three
  files, the supported cleaner contract and processing version, one shared
  cleaner run identity, matching cleaned-Parquet and quality-report checksums,
  the exact cleaner schema, exactly one UTC date read from the Parquet and
  cross-checked against the quality report, membership in the accepted period,
  and an unchanged `unverified` completeness claim. An identical retry is
  reusable evidence; different bytes create a conflict that preserves the
  recorded identity and attempt history. The period is `ready` only when all 153
  dates hold a compatible verified current entry; timestamp bounds, filenames,
  and plausible row counts are explicitly recorded as insufficient. When a
  retrieval manifest is supplied, its per-date `cleaning_reference` checksums
  are validated against the recorded bundle instead of matching on UTC date
  alone; a reference naming a different bundle is refused, and an absent or
  partial reference leaves the linkage explicitly unverified. The deterministic
  `period_input_id` derives from contracts, expected dates, deterministic
  cleaned-Parquet checksums and deterministic cleaner run identities. The
  quality-report and run-metadata checksums are recorded and validated but
  excluded from it, because the cleaner writes local paths and real execution
  timestamps into those sidecars; regenerating the same analytical data
  elsewhere or later therefore keeps one identity, while different recorded
  bytes still conflict.
- A focused three-verb CLI (`record`, `status`, `scan`) takes explicit paths,
  performs no discovery outside them, writes only an explicit ignored
  `data/interim/` destination, publishes atomically, refuses raw destinations and
  arbitrary overwrites, and returns distinct exit codes for success, refusal,
  not-ready, and recorded conflict.
- The bounded DuckDB relation re-verifies each recorded cleaned-Parquet checksum,
  requires an explicit memory limit with a unit and an explicit ignored spill
  directory, and scans daily Parquet partitions without concatenating the period
  in Python, Pandas, Polars, or PyArrow. Aggregates run in SQL and ordered
  results stream as bounded Arrow record batches in the deterministic global
  order MMSI, UTC timestamp, latitude, longitude, vessel type code, vessel group.
  Consecutive pairs are formed across the whole period per MMSI, so no vessel is
  split solely because the UTC date changed; the continuity summary reports how
  many pairs an artificial daily partitioning would have lost. No maximum gap,
  implied-speed, length, or edge-support rule is applied and no segment or
  vessel grid is emitted.
- A focused candidate vessel-grid boundary now consumes that verified relation
  and the exact `projected_water_grid_v1` contract. It requires explicit maximum
  gap, implied-speed ceiling, period-readiness, cleaned-extent censoring, and
  exact-support allocation arguments; none has an analytical default. Length
  filtering has no command option and remains recorded as disabled and
  unresolved. Whole-period DuckDB `lead` pairing preserves valid cross-midnight
  segments while ordered Arrow batches keep Python processing bounded.
- Retained straight segments are split across exact modeled-whale-support water
  geometry in EPSG:3310. Candidate per-cell vessel-kilometres are emitted for
  passenger, cargo, tanker, and their additive commercial total, together with
  vessel-kilometres per stored support-water area. Descriptive distinct MMSI and
  MMSI-date values are recomputed from underlying identity unions for all
  commercial vessels rather than summed from group counts. Zero-length,
  outside-support, invalid-intersection, point-boundary, and positive-length
  boundary-ambiguity populations remain explicit. Parent, allocated, outside,
  ambiguous, and invalid distances conserve within recorded absolute and
  relative tolerances.
- The atomic `candidate_vessel_grid_v1` bundle is restricted to ignored
  `data/derived/` and contains deterministic GeoParquet and quality JSON plus
  time-bearing lineage metadata. It preserves exact grid identity, ordering,
  areas, and geometry, includes every cell including zeros, refuses raw or
  non-derived output, input/output overlap, arbitrary overwrite, and partial
  publication, and records source artifact checksums, candidate parameters,
  exclusions, counts, conservation, sanitized bounded-execution settings,
  software versions, and validation steps. Synthetic tests verify the candidate
  processing boundary. On 2026-09-01 the real 15--16 July delivery was also
  exercised through all four 300/1,800-second by 30/50-knot candidate
  combinations. All four passed report validation and distance conservation,
  and distinct-output repeats reproduced exact candidate IDs, GeoParquet bytes,
  and deterministic quality-report bytes. The exact four outputs were visually
  inspected in QGIS 4.2.1 across the full domain, shipping-lane concentrations,
  support edges, zero/nonzero cells, and contextual VSR boundary without a
  projection, geometry, or clipping anomaly. This is bounded two-day candidate
  evidence: no parameter was accepted and no period-wide vessel input was
  produced.
- The 2026-08-28 real read-only smoke run recorded the existing bounded
  2024-07-15 cleaner bundle and retrieval manifest without modifying either. It
  reported exactly one compatible date, 152 missing dates, `not_ready` period
  readiness, and `unverified` observational completeness, with path- and
  clock-independent `period_input_id` `multiday-ais-aeaf8f584d830ed98ef2b52d`.
  The retrieval state was recorded separately as entry status `retrieved` with
  verified retained byte identity and `unverified` independent byte
  completeness; its own `cleaning_reference` bound to the supplied bundle, so
  the retrieval-to-cleaner linkage was `verified`. The bounded scan
  streamed 113,799 observations in three 50,000-row Arrow batches and reported
  113,620 whole-period consecutive pairs — the same structural segment count the
  one-bundle evidence harness produced independently for that input. With one
  date present, cross-date pairs were 0. Three end-to-end scans took
  approximately 0.63, 0.68, and 0.78 seconds. One date does not validate the
  analytical period, and neither transfer nor observational completeness was
  established.

**Not implemented**

- Network AIS transfer, range-resume, and analytical-period retrieval. The local
  supplied-artifact validation, bounded multi-date delivery intake, resumable
  daily-cleaner orchestration, and overlapping real one-day/two-day canonical
  compatibility exercise are complete. Independent transfer completeness,
  monthly/full-period memory safety, a guarded daily bulk download, and the
  153-date retrieval remain unverified or unexercised.
- The final vessel-activity input proposed in ADR 0018. Candidate period segment
  construction, explicit filtering, exact grid allocation, per-cell vessel-
  kilometres, union-recomputed distinct counts, quality metadata, and lineage
  are implemented, synthetically verified, and exercised across the four
  documented parameter combinations on the real 15--16 July delivery. The
  requested analytical period remains `not_ready` with 151 dates missing;
  transfer and observational completeness remain `unverified`. No production
  threshold was selected;
  accepted maximum-gap and implied-speed rules, alternative edge support,
  vessel-length population treatment, period-wide stability, observational
  completeness, monthly/full-period safety, and final speed summaries remain
  unresolved. The implemented output therefore remains a candidate result, no
  exposure analysis has been performed, and ADR 0018 remains Proposed.
- Normalization of whale or vessel values. Both grid-aligned candidate inputs
  preserve physical or source units; normalization remains part of the deferred
  exposure-method decision.
- A successful GDAL/Pyogrio read-back of the GeoParquet on this machine; its
  driver attempted to load a missing `duckdb.dll`. PyArrow read-back and
  GeoParquet metadata validation passed, but ArcGIS compatibility remains
  unverified.
- End-to-end analytical-period lineage and rerun. Candidate vessel-grid lineage
  now joins the one-extract AIS, projected water-grid, and whale-grid lineage
  boundaries, but no full-period source set or final analytical result exists.
- The exposure calculation and surface, inside-versus-outside statistics, and
  their output contracts. The analytical-domain prerequisite is resolved, but
  these later analytical products are not implemented.

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
- A persistent application-level `Powered by Esri` fallback remains visible
  while the SDK loads and whenever initialization does not reach a ready map.
  On a ready map the application removes that fallback and leaves the SDK's
  automatic, dynamic data attribution enabled; it does not hide or replace the
  SDK attribution.
- Formatting (Prettier), linting (ESLint), type checking (`tsc --noEmit`), and
  tests (Vitest, 23 passing) configured and run.
- Clean-checkout verification is implemented and exercised through
  `npm run verify:clean`: it installs dependencies from the committed lockfile,
  generates Next.js route types, runs formatting, linting, type checking, and
  tests in order, then produces the local static export. This verifies the
  local build path only; the separate browser check below verifies local keyed
  service access, and neither check verifies a deployment.
- Credential handling: `web/.env.example` carries variable names only, all other
  `.env*` files are ignored, and no credential is tracked.
- Build output (`web/out/`, `web/.next/`) and `node_modules/` are ignored and
  are not committed.
- A real keyless production/static export was checked in headless Chrome on
  2026-08-30 at exact 390 x 844, 820 x 1180, and 1440 x 900 CSS-pixel
  viewports. Initial SDK loading, map initialization with the missing-key
  configuration warning, and the resulting `arcgisViewReadyError`
  initialization-error state were observed at every size. In every sampled
  state exactly one attribution treatment was visually unobscured and within
  the viewport, and neither the document nor body had horizontal overflow. The
  timeout path was not observed in this run.
- A real keyed production/static export was served from the authorized
  `http://localhost:3000` origin and checked on 2026-08-31 in headless Google
  Chrome 151.0.7922.174 at exact 390 x 844, 820 x 1180, and 1440 x 900
  CSS-pixel viewports. The `arcgis/oceans` basemap rendered and reached a ready,
  non-updating view with zero reported map load errors at every size. Pointer
  drag and wheel interaction changed the center and zoom at every size. The
  application fallback remained present throughout pre-ready samples and was
  removed only at readiness; after readiness the SDK's dynamic Esri and data-
  provider attribution was the single visible attribution treatment, remained
  unobscured and inside the viewport after pan and zoom, and the application
  fallback was absent. Loading/status content remained readable, the map
  remained usable, neither the document nor body overflowed horizontally, no
  `Token Required` response or ArcGIS identity prompt appeared, and all
  observed ArcGIS responses succeeded. The final sanitized console contained
  only the SDK's Calcite version information. A local missing-favicon 404 and a
  narrow-viewport composited-map paint escape found during the check were fixed
  with a declared SVG favicon and an explicit map-frame paint-containment
  boundary, then rechecked. No credential value or credential-bearing request
  URL was retained.
- Decisions recorded as [ADR 0007](decisions/0007-use-npm-for-the-web-application.md),
  [0008](decisions/0008-deliver-the-application-as-a-static-export.md),
  [0009](decisions/0009-mount-arcgis-through-client-only-map-components.md), and
  [0010](decisions/0010-use-vitest-for-typescript-tests.md).

**Documentation-only capability inventory completed; account verification not done**

- Current official Esri documentation was checked on 2026-08-31. Location
  Platform is documented as a limited single-user organization that can create
  hosted feature, vector-tile, and map-tile services, but not hosted image or
  scene services. `Everyone` sharing is documented to allow anonymous access,
  without requiring a separate ArcGIS Online organization.
- The current documented monthly free tiers relevant here are 2,000,000 basemap
  tiles or 1,000 basemap sessions; 250 MB of feature storage; 250 MB of
  tiles/files/attachments storage; 125 MB each of feature-query and feature-edit
  bandwidth; 25 GB each of vector-tile and map-tile bandwidth; and 25,000 tiles
  generated during publishing. Feature-service access is bandwidth-metered,
  not covered by a documented request-count allowance. These are product-wide
  allowances, not this account's verified balances.
- Location Platform is documented to use free tiers plus optional pay-as-you-go,
  not ArcGIS Online credits. Pay-as-you-go is documented as off by default for
  new accounts, but the author's actual billing state is unverified.
- The author reports creating a Location Platform account and a restricted
  browser API key. The key was absent and was not inspected. No authenticated
  account session was available, so the product identity, service-creation and
  public-sharing controls, billing mode, usage, and free-tier headroom have not
  been verified from the real account. The short private author checklist is in
  [development.md](development.md#read-only-capability-inventory-2026-08-31).
- On documentation alone, a later minimal public hosted-feature test appears
  capable of remaining inside the free tiers. It is not yet permitted by the
  evidence: actual pay-as-you-go status, controls, usage, and headroom must be
  confirmed first. No item was created or published on this branch.

**Not done**

- **The static-shell deployment.** This can proceed independently of an ArcGIS
  account. The application has never been deployed anywhere, and there is no
  public URL.
- The authenticated account portion of the account-type capability check.
  Location Platform product behavior and current published allowances are
  documented, but the author's actual account type, service controls, public
  sharing, storage/bandwidth usage, remaining headroom, and billing status are
  unverified. ArcGIS Online organization privileges and credits are not
  applicable to the reported Location Platform branch unless the product check
  fails.
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
| Map renders, pans, and zooms | **Verified locally.** The keyed static export rendered `arcgis/oceans`, panned, zoomed, and completed the ready-map attribution handoff in Chrome at all three required viewports. The deployed-origin path remains unverified. |
| No credentials in the repository or committed build output | **Verified.** Staged diffs were scanned before each commit; build output is ignored. |
| Deployment reachable and reflecting main | **Unverified.** No deployment exists; main has not been deployed or verified. |
| Account-type capability checks complete and recorded | **Partial.** Current Location Platform documentation and allowances are recorded. The author reports a Location Platform account, but no authenticated session was available; actual product identity, billing, usage, controls, and headroom remain unverified. |
| Conditional Esri-hosted publish-and-serve test | **Not attempted.** Documentation indicates a minimal public feature service can fit the free tiers, but the test waits for actual pay-as-you-go, control, usage, and headroom checks. |
| Unavailable capabilities recorded as constraints for M5 | **Partial.** Location Platform hosted image and scene creation are documentation-only unavailable; ArcGIS Online credits/privileges are not applicable to the reported branch. Actual account constraints remain unverified. |

M4 is not complete and must not be marked complete until the deployed
application and the real account-type capability checks are verified. An
Esri-hosted publish-and-serve test is also
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
basemap styles service returns 401 "Token Required". With the local key supplied
through ignored configuration, the authorized localhost origin successfully
rendered `arcgis/oceans` in Chrome on 2026-08-31. ArcGIS Location Platform
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
- **The Location Platform product boundary is documented, but the real account
  remains unverified and constrains publication.** Official documentation
  supports feature, vector-tile, and map-tile services plus public anonymous
  sharing and identifies the current free tiers. Actual service controls,
  usage, headroom, and billing state still require the author's private check.
  If that account does not fit, ArcGIS Online and then a non-Esri public route
  remain candidates. **Partly resolved from documentation only.**
- Location Platform storage/bandwidth usage and ArcGIS Online credit/storage
  consumption could constrain iteration. The project does not enable
  pay-as-you-go or authorize spending. **Still open.**
- ArcGIS SDK licensing and API-key requirements for the intended hosting model need confirming before public deployment. **Partly resolved:** a browser-delivered, origin-restricted API key is required for the basemap, Location Platform accounts have API-key privileges by default, the requirements for scoping a browser key are recorded in [development.md](development.md), and local service access succeeded from the authorized localhost origin. The real account capabilities and deployed-origin service access remain unverified.
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
- **The analytical domain has been accepted** in [ADR 0002](decisions/0002-southern-california-study-area-extent.md), and every result applies its exact qualified geometry and outside-domain treatment.
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
