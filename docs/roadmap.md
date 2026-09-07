# Roadmap

**Owns:** milestones, sequencing, current progress, and version direction.

Milestones are ordered by **dependency and outcome**, not by calendar date. No individual milestone carries a date. The only date in this project is the Version 1 target recorded in [project-brief.md](project-brief.md).

A milestone is not "in progress" because work has been thought about. It is in progress when something in the repository is changing for it, and complete only when every completion criterion below is satisfied.

**Status legend:** `Not started` · `In progress` · `Blocked` · `Complete`

| #   | Milestone                        | Status      |
| --- | -------------------------------- | ----------- |
| M1  | Project foundation               | Complete    |
| M2  | Data discovery and validation    | Complete    |
| M3  | Processing workflow              | Complete    |
| M4  | GIS application foundation       | In progress |
| M5  | Core input layers                | In progress |
| M6  | Whale–vessel exposure analysis   | In progress |
| M7  | Application integration          | Not started |
| M8  | Verification and reproducibility | Not started |
| M9  | Public release                   | Not started |

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

**Status:** Complete

> An independent audit of this milestone on 2026-08-26 found five problems: provenance claimed but not recorded, AIS record counts quoted inconsistently and snapshot results generalised into period facts, an analytical domain accepted on evidence that could not support it, a boundary method that would have made the headline statistic an artefact of the grid, and a retrieval policy that contradicted itself. All five have been corrected. The corrections **enlarged** the set of open questions rather than shrinking it, which is the honest outcome.

**Objective**
Obtain and inspect the actual candidate datasets, and determine what analysis the data can genuinely support. This milestone is where assumptions become findings.

**Dependencies**

- M1 (source register exists with the questions each source must answer).

**Deliverables**

| Deliverable                                                                                                                                    | State                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A small, retrievable sample of each candidate dataset, inspected locally                                                                       | **Done.** Twenty artifacts, each with a recorded size and SHA-256                                                                                                                                                                                                                                                                                                                                                                            |
| For each source: confirmed format, CRS, spatial extent and resolution, temporal coverage, value meaning and units, and licence or terms of use | **Done.** The VSR review found no explicit redistribution grant; ADR 0019 records a conservative no-copy public-use posture instead of converting that uncertainty into permission                                                                                                                                                                                                                                                           |
| A written definition of the Southern California study area: extent, projected CRS, and analysis grid                                           | **Done.** The map/context extent and scope-reduced `receivers_50_nautical_miles` analytical domain ([0002](decisions/0002-southern-california-study-area-extent.md)), projected CRS ([0003](decisions/0003-projected-coordinate-system.md)), grid ([0004](decisions/0004-analysis-grid-resolution.md)), and modeled-whale-support water geometry ([0014](decisions/0014-select-the-grid-water-mask.md)) are accepted and explicitly distinct |
| A decision on the analytical period                                                                                                            | **Done** ([0005](decisions/0005-analytical-period.md))                                                                                                                                                                                                                                                                                                                                                                                       |
| A decision on whether vessel speed can be derived reliably from the available AIS records                                                      | **Done, with its evidentiary limits stated** ([0006](decisions/0006-report-vessel-speed-separately.md)). `SOG` is present, documented, and appears usable in the inspected sample; that is not the same as established across the period                                                                                                                                                                                                     |
| Updated source register with verification status replacing every resolved "to be verified" entry                                               | **Done**, with a provenance manifest and a utility that re-checks it                                                                                                                                                                                                                                                                                                                                                                         |
| Architecture decision records for choices that constrain later work                                                                            | **Done.** ADRs 0002 and 0019 were accepted at M2; the separate AIS retrieval (0017) and vessel-activity method (0018) records were Proposed M3 decisions then and have since been accepted                                                                                                                                                                                                                                                   |

**Completion criteria**

| Criterion                                                                                                                                             | State                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Every Version 1 input has an identified, retrievable, authoritative source with recorded provenance                                                   | **Met.** Source URL or query endpoint, method and parameters, retrieval date, local filename, byte size and SHA-256 are recorded for all twenty artifacts in [data-sources.md](data-sources.md), and `python tools/m2_verify.py verify` parses that register and checks retained local copies against those identities. The two USCG PDFs added on 2026-08-31 matched their recorded identities. The separate [analytical-domain evidence command](analytical-domain-evidence.md#reproducible-calculation) regenerates the candidate-domain report and mask when its ignored inputs are present. This criterion was previously claimed as met when the checksums did not exist |
| The whale model layer's values are understood well enough to state what they mean in the application legend                                           | **Met.** `DENSITY` is animals per km², publisher-defined, with a per-cell coefficient of variation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| The AIS extract needed for the study area and analytical period has been scoped, and its volume is known                                              | **Met, with the volume qualified.** The period is fixed and the retrieval footprint is bounded, but the volume is an **order-of-magnitude planning estimate** — 60 to 90 million study-area records, ≈56 GB of transfer — extrapolated from five 34-minute windows all at the same time of day. It is not a measurement and nothing analytical rests on it                                                                                                                                                                                                                                                                                                                     |
| The VSR boundary geometry is confirmed as obtainable from an authoritative source, or a documented derivation from published coordinates is agreed on | **Met.** A closed, land-clipped polygon is retrievable, and seven of the program's eight published points lie exactly on its boundary                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Each input has a documented public-use and publication posture, so it is clear what may be committed, hosted, or referenced publicly                  | **Met.** The NOAA postures are recorded. For the VSR geometry, permission to redistribute remains unconfirmed, so [ADR 0019](decisions/0019-reference-the-publisher-hosted-vsr-service.md) prohibits project-hosted copies and selects direct display from the publisher's service with attribution, disclaimer, and release-time verification                                                                                                                                                                                                                                                                                                                                 |
| **The analytical and statistical domain over which headline results can be defended has been accepted**                                               | **Met.** [ADR 0002](decisions/0002-southern-california-study-area-extent.md) accepts `receivers_50_nautical_miles`: 50 nautical miles, exactly 92,600 metres, from the relevant NAIS reception stations, not from the coast. It is a scope-reduced, system-performance-qualified AIS receiver domain, not empirical 2024 coverage. Unknown receiver uptime, station completeness, feed interruptions, antenna and terrain effects, and observational completeness remain limitations                                                                                                                                                                                           |
| Anything that cannot be verified is explicitly recorded as unresolved rather than assumed                                                             | **Met**, and this is what the audit repaired. Several things previously stated as established are now recorded as unresolved                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

**M2 is complete.** Every criterion above is met. The original redistribution
criterion was not satisfied by obtaining permission: no explicit grant was
found, and public access is not treated as a redistribution licence. It was
revised to the outcome discovery actually needs—a truthful public-use and
publication posture—and [ADR 0019](decisions/0019-reference-the-publisher-hosted-vsr-service.md)
meets it by prohibiting project-hosted VSR copies and selecting direct use of
the publisher's public Feature Service.

### Open items, in order of how much they constrain the work

1. **The whale model's season definition is unconfirmed.** The survey basis is July–November; a redistributor describes the same models' predictions as late June to early December. [ADR 0005](decisions/0005-analytical-period.md) uses the conservative July–November reading and would need revisiting if the publisher states otherwise.

2. **The datum of the published VSR coordinates is unstated.** Assumed WGS 84, consistent with the geometry being served in EPSG:4326, but the program says nothing. At these latitudes a NAD 27 confusion would be on the order of 100 m.

3. **VSR redistribution permission remains unconfirmed but no longer blocks Version 1.** ADR 0019 prohibits committing or publishing the snapshot or a project-created derivative. This no-copy architecture does not make a legal determination about other terms governing direct service use. A later choice to host a copy requires a confirmed permission posture.

4. **Deferred to M3 rather than blocking M2**, but named so they are not rediscovered: at M2 completion, the AIS retrieval route remained Proposed after the one-day AccessAIS direct-CSV compatibility exercise, with independent transfer completeness and scaling unresolved and guarded bulk fallback permitted (see [../data/README.md](../data/README.md)); whether AccessAIS can filter by vessel type server-side; and whether a length threshold is applied on top of the vessel-type filter, and at what value.

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

**Public VSR display is settled but not implemented.** M5 may load `FID = 126`
directly from the publisher's public Feature Service. Hosting a project-owned
copy remains prohibited.

### What was established

Detail is in [data-sources.md](data-sources.md); this is the summary that changes later work.

- **The whale model is vector polygons, not a raster** — 12,257 cells in EPSG:4326 on a 0.1° equal-angle grid, values in animals per km², with a coefficient of variation per cell. It is a **single summer–fall multi-year average, not a time series**, which removes any possibility of seasonal claims from this input.
- **AIS carries no gross tonnage**, so the VSR program's 300 GT criterion cannot be applied directly and any size filter is a project assumption.
- **NOAA states AIS coverage is unavailable beyond 40–50 miles from shore**, and the sampled record density falls off in a way consistent with that. The VSR zone extends well past it. This is the most consequential finding of the milestone and it drove the analytical-domain audit resolved in ADR 0002.
- **2025 AIS broadcast points are partial through September 30.** NOAA's current vessel-traffic page lists data through 2025, and its January 2026 point-data summary records 273 daily 2025 files covering January 1–September 30 in the new `.zst` compression format. The accepted July–November period therefore cannot be completed from 2025, and 2026 data is not listed. Version 1 pairs the current zone with 2024, the latest published year covering the complete accepted period, and says so.
- **The VSR zone's eight published points do not define a polygon** — they are the seaward boundary only — but a closed geometry is published separately and matches them at seven of eight vertices, the eighth by 455 m.
- **Commercial vessel types were 18.2–20.7% of Southern California records** across five sampled windows. A snapshot result: five dates, one time of day, and the direction of any daily bias is unknown. What it supports is the conclusion that **vessel-class filtering is the most consequential processing choice for this input**, which holds across the sampled range and does not depend on the exact share.

**Decisions recorded**

**Accepted:** [0002](decisions/0002-southern-california-study-area-extent.md) map/context extent and scope-reduced `receivers_50_nautical_miles` analytical domain · [0003](decisions/0003-projected-coordinate-system.md) EPSG:3310 · [0004](decisions/0004-analysis-grid-resolution.md) 5 km grid with fractional VSR-boundary accounting · [0005](decisions/0005-analytical-period.md) 1 July – 30 November 2024 · [0006](decisions/0006-report-vessel-speed-separately.md) speed reported separately · [0019](decisions/0019-reference-the-publisher-hosted-vsr-service.md) publisher-hosted VSR display with no project-controlled copy.

**Risks and open questions**

- ~~The whale distribution model may not be published at a resolution or in a format that is directly usable.~~ **Resolved:** directly usable, though as vector polygons rather than the raster the architecture also allowed for.
- ~~AIS volume for the study area may be large enough to force a narrower analytical period or a coarser aggregation.~~ **Partly realised:** volume is large — an estimated ≈56 GB of transfer for the chosen period — but the period was narrowed by data availability rather than by volume.
- ~~The authoritative VSR boundary may only be published as text coordinates or as a map image.~~ **Resolved:** a downloadable closed geometry exists.
- ~~Whale-model and AIS temporal coverage may not overlap cleanly.~~ **Realised, differently than expected:** the whale model has no time dimension at all, so there was nothing to overlap. Version 1 pairs a climatological surface with a fixed traffic window and states both vintages.
- **VSR redistribution permission is not established.** **Handled for Version 1 by avoidance:** the project will not host a copy or derivative and will reference the publisher's service directly. This is not a legal conclusion or a permission claim.
- **AIS observation remains unestablished outside the accepted receiver domain and incomplete observation remains possible inside it.** The author accepted a system-performance-qualified scope reduction, not empirical 2024 coverage; receiver uptime, station completeness, feed interruptions, antenna and terrain effects, and observational completeness remain limitations.
- **New:** discovery findings can be written more confidently than the evidence behind them supports. Five such overstatements were found by audit in this milestone alone. The provenance manifest and [`tools/m2_verify.py`](../tools/m2_verify.py) exist so the next reader can check a number rather than trust it.

---

## M3 — Processing workflow

**Status:** Complete

**Objective**
Turn raw source data into validated, derived geospatial datasets through an ordered, repeatable process.

**Dependencies**

- M2. Data, projection, grid, analytical period, analytical domain, and the VSR no-copy publication posture are accepted. Permission to redistribute the VSR geometry remains unconfirmed, but Version 1 does not depend on it because project-hosted copies are prohibited.

### Progress

**Foundation, first AIS processing slice, projected water grid, whale transfer,
candidate vessel-grid aggregation, and period vessel-rule evidence boundary
implemented; candidate vessel-grid exercised with bounded two-day real data and
non-spatial rule evidence exercised with the real ready 153-date input**

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
  records the **Accepted** AIS retrieval policy. AccessAIS is the preferred
  route, and the audited July monthly gate authorizes sequential author-
  submitted August--November calendar-month extracts under the existing
  resource controls. Guarded one-day-at-a-time bulk retrieval remains fallback
  only. The read-only
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
  records the vessel-activity aggregation design, **Accepted** on 2026-09-05.
  Vessel-kilometres is the primary additive grid metric. Group-specific
  distinct MMSI and MMSI-date counts remain descriptive; their all-commercial
  values must be recomputed as unique MMSIs and MMSI-date pairs from the union
  of retained commercial points rather than summed across passenger, cargo, and
  tanker groups. The modeled-whale-support geometry is biological model
  support, not an authoritative shoreline, general water mask, or AIS
  observability boundary. A candidate segment/grid processing foundation
  is now implemented, but the gap, implied-speed, edge-support, and vessel-
  length choices remain unresolved and ADR 0018 remains Proposed. _(History: all
  four were resolved and ADR 0018 was accepted on 2026-09-05.)_
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
  for and removed them. At that stage, peak RSS of approximately 1.59 GiB was a
  scaling concern: monthly and full-period execution had not been shown safe or
  authorized.
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
- A 2026-09-02 controlled stage investigation established that the earlier high
  RSS came from the daily cleaner, which had inherited DuckDB's machine defaults
  of `12.5 GiB` and 12 threads. Fingerprinting, streaming partitioning,
  canonical sorting, intake validation, and manifest recording did not produce
  the peak. The cleaner now receives and verifies the intake command's explicit
  memory limit, isolated spill directory, and one-thread setting. Three isolated
  `512MB` cleaner runs peaked at 550.410--551.098 MiB application RSS and
  reproduced the established deterministic output. Two corrected fresh
  two-day runs peaked at 556.922/558.699 MiB application RSS and
  949.652/952.223 MiB private bytes; a date-restricted run peaked at 552.910 MiB
  RSS, and a compatible retry at 65.918 MiB. Spill peaked at 625.469--678.594
  MiB and returned to zero after every successful run. A third fresh two-day
  run passed the implemented 2 GiB memory/8 GiB disk preflight, peaked at
  558.859 MiB application RSS and 618.188 MiB spill, and reproduced the same
  identities. At that stage, this supported per-date bounded execution for the
  observed input but did not establish monthly safety. A direct-
  process profiler now separates application, descendant, tree, baseline,
  peak, private-byte, disk, and spill measurements and enforces optional
  preflight headroom. It now also enforces explicit runtime minimum-memory,
  minimum-disk, maximum-application-RSS, and maximum-spill choices; reports
  live state and sampled extrema; reaps the target tree on abort, exception, or
  interruption; and restricts normal evidence reports to ignored
  `data/interim/`. The author subsequently supplied the requested continuous
  2024-07-15 through 2024-07-21 direct CSV over longitude -122 to -117 and
  latitude 32 to 35. Read-only inspection identified 399,148,173 local bytes
  and SHA-256
  `0cc4ede8dc16504641f91e4ba44c1ce128933958abec1f855dc91196ae58dbd2`,
  but no independent HTTP `Content-Length` was retained. The first processing
  attempt was refused below the required 2 GiB available-memory preflight
  before intake launched; it produced no report or processing artifacts, and
  the stop rule prohibited the retry. At that point, independent transfer
  completeness, seven-day/monthly safety, and observational completeness
  remained unresolved; ADR 0017 remained Proposed and M3 remained in progress.
  The session later resumed after available memory recovered, without changing
  a threshold. The first run reconciled 3,928,736 rows across exactly the seven
  requested dates, sequentially cleaned and recorded every date, reproduced the
  established 15--16 July identities, and peaked at 581.512 MiB application RSS
  and 710.594 MiB spill before spill returned to zero. An identical retry
  skipped all seven dates with unchanged identities, 70.367 MiB peak application
  RSS, and zero spill. The seven-day processing/resource conditions therefore
  passed. A separate completed browser download then reproduced the exact
  399,148,173-byte source and SHA-256. No HTTP `Content-Length` was retained, so
  publisher-side independent byte completeness remains `unverified`. For this
  portfolio MVP, the repeat-transfer, parsing, date/row, identity, resource, and
  retry evidence authorized at that stage only the 2024-07-01 through 2024-07-31
  monthly scale test. It did not authorize the other four months or establish
  full-period or observational completeness. ADR 0017 remained Proposed pending
  that monthly exercise, and M3 remained in progress.
  The authorized July monthly test subsequently reconciled 17,998,955 rows
  across exactly 31 dates, cleaned 3,384,056 commercial observations, reproduced
  every 15--21 July canonical and cleaner identity from the seven-day evidence,
  and recorded 31 compatible dates with 122 August--November dates missing. The
  first run took 848.101 seconds and peaked at 587.934 MiB application RSS,
  1,002.828 MiB private bytes, 591.973 MiB process-tree RSS, 744.344 MiB spill,
  and 4.044 GiB generated-root size; minimum available memory/free disk were
  1.652/16.146 GiB and spill returned to zero. The identical 179.454-second
  retry skipped all 31 dates with unchanged deterministic identities, peaked at
  71.379 MiB application RSS, and used zero spill. Both targets returned the
  expected exit code `3` because 122 dates remain absent; both profiler runs
  completed without a resource abort. No HTTP `Content-Length` was retained,
  so publisher-side transfer completeness and observational completeness remain
  `unverified`. The July evidence passed independent audit and satisfied ADR
  0017's acceptance condition. ADR 0017 now authorizes sequential author-
  submitted August--November calendar-month extracts under the same controls;
  it does not establish later-month or full-period safety. M3 remains in
  progress.
  The first authorized later month was then accumulated into that same state on
  2026-09-04. The August delivery reconciled 18,284,354 rows across exactly its
  31 requested dates, cleaned 3,501,843 commercial observations, and raised the
  period manifest to 62 compatible dates with 91 September--November dates
  missing and no conflicts. Its first run took 567.190 seconds and peaked at
  579.422 MiB application RSS, 999.125 MiB private bytes, 583.238 MiB
  process-tree RSS, and 764.719 MiB spill; minimum available memory/free disk
  were 2.351/65.224 GiB and spill returned to zero. The identical
  171.885-second retry skipped all 31 August dates with unchanged deterministic
  identities, peaked at 74.164 MiB application RSS, and used zero spill. Both
  targets returned the expected exit code `3`, and neither profiler run aborted
  on a resource threshold. An independent read-only audit recomputed all 31
  canonical daily slice checksums and all 186 recorded cleaned-bundle file
  checksums with zero mismatches and confirmed that every July identity was
  unchanged.
  September was accumulated the same way on the same date. Its delivery
  reconciled 15,638,516 rows across exactly its 30 requested dates, cleaned
  2,861,837 commercial observations, and raised the manifest to 92 compatible
  dates with 61 October--November dates missing and no conflicts. Its first run
  took 442.139 seconds and peaked at 595.102 MiB application RSS, 992.887 MiB
  private bytes, 599.180 MiB process-tree RSS, and 752.438 MiB spill; minimum
  available memory/free disk were 2.580/60.813 GiB and spill returned to zero.
  The identical 136.475-second retry skipped all 30 September dates with
  unchanged identities, peaked at 73.684 MiB application RSS, and used zero
  spill. Its audit recomputed 30 canonical daily slice checksums and all 276
  recorded cleaned-bundle file checksums with zero mismatches. No HTTP
  `Content-Length` was retained for either month, so publisher-side transfer
  completeness and observational completeness remain `unverified`.
  October was accumulated the same way on the same date. Its delivery reconciled
  16,355,292 rows across exactly its 31 requested dates, cleaned 2,889,605
  commercial observations, and raised the manifest to 123 compatible dates with
  exactly the 30 dates 2024-11-01 through 2024-11-30 missing and no conflicts.
  Its first run took 526.627 seconds and peaked at 589.160 MiB application RSS,
  997.145 MiB private bytes, 593.195 MiB process-tree RSS, and 685.781 MiB
  spill; minimum available memory/free disk were 2.645/49.774 GiB and spill
  returned to zero. Two earlier retry invocations ended unexpectedly at the
  host/session level during source fingerprinting; neither produced a profiler
  report, so their cause and classification are not established, though the last
  observed guard state was within the configured thresholds. Neither recorded a
  delivery attempt or published a bundle, spill stayed empty, and the audited
  123-date state was unchanged. The repeated 145.569-second retry then completed
  normally, skipping all 31 October dates with unchanged identities, peaking at
  73.777 MiB application RSS, and using zero spill. Its
  audit recomputed 31 canonical daily slice checksums and all 369 recorded
  cleaned-bundle file checksums with zero mismatches.
  November, the fourth and last authorized month, was accumulated the same way on
  the same date. Its 1,461,597,110-byte delivery with SHA-256
  `4cecc4641cc83b14d08b5bd98392bdecfe68a638224dbd456b6e80ff76f508dc`
  reconciled 14,342,365 rows across exactly its 30 requested dates, cleaned
  2,821,226 commercial observations, and raised the manifest to 153 compatible
  dates with zero missing dates and no conflicts, moving
  `period_input_readiness` to `ready`. Its first run took 472.146 seconds and
  peaked at 596.336 MiB application RSS, 999.770 MiB private bytes, 600.184 MiB
  process-tree RSS, and 663.375 MiB spill; minimum available memory/free disk
  were 2.196/58.261 GiB and spill returned to zero. The identical 152.785-second
  retry skipped all 30 November dates with unchanged identities, peaked at
  74.637 MiB application RSS, and used zero spill. Both targets returned the
  expected exit code `0` — not `3` — because the November append completes all
  153 accepted dates, and neither profiler run aborted on a resource threshold.
  Its audit rehashed the source, recomputed all 153 canonical daily slice
  checksums and all 459 recorded cleaned-bundle file checksums with zero
  mismatches, and confirmed every July through October identity unchanged, one
  per-date attempt per compatible date, empty spill directories, and no
  temporary or staging artifact.
  The accumulated state is therefore 153 of 153 expected dates and 15,458,567
  cleaned commercial observations with no conflict, and the period input is
  `ready`. No HTTP `Content-Length` was retained for any month, so publisher-side
  transfer completeness and observational completeness remain `unverified`. A
  complete, ready cleaned-input period is not a final vessel-activity grid or an
  exposure result; neither exists, so M3 remains **In progress**.
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
- The combined self-contained suite has 361 passing tests using temporary
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
  output safeguards, DuckDB normalized-memory verification, deterministic
  profiler threshold evaluation, mocked resource abort and process cleanup,
  profiler output/path safeguards and version reporting, and all CLI boundaries.
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
- A focused `period_vessel_rule_evidence_v1` boundary now reuses the relation's
  single whole-period same-MMSI adjacency stream to evaluate all four explicit
  300/1,800-second by 30/50-knot combinations without grid intersection. Its
  production path requires the ready 153-date manifest, all candidate values,
  and the explicit type-only/no-length-filter treatment; a clearly named
  incomplete-period override is non-production only. Daily segment accounting
  uses the starting observation's UTC date and reports cross-midnight segments
  separately. Date, whole-period, passenger, cargo, tanker, and union-
  recomputed commercial summaries retain every structural and candidate
  exclusion reason, SOG and length availability, and projected/geodesic
  comparisons. Exact scalar aggregates plus fixed bins and one bounded Arrow
  iteration avoid retaining full populations. Deterministic evidence JSON and
  a time-bearing lineage sidecar are atomically restricted to ignored interim
  storage; paths, clocks, runtime, output names, machine details, and resource
  settings do not enter evidence identity. The boundary is synthetically
  tested. On 2026-09-04 it also completed two profiled runs against the exact
  ready 153-date manifest. Both streamed 15,458,567 observations and reconciled
  15,457,099 structural segments, all four candidate populations, all dates,
  and all vessel groups. The repeat reproduced evidence ID
  `period-vessel-rule-evidence-cb2525fab34c4b8848146365` and the exact
  `evidence.json` bytes (SHA-256
  `1b90ebd4e8d340cdb09709557d154f5b55f7882cba8cbc08b548958edbb25ff4`);
  time-bearing lineage bytes differed as intended and both spill directories
  ended empty. This non-spatial JSON evidence required no QGIS verification.
  It selects no rule, emits no production grid, and performs no exposure
  analysis. Publisher-side transfer and AIS observational completeness remain
  `unverified`.
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
  support edges, zero/nonzero cells, and contextual VSR boundary. Corrected
  renders placed the blue accepted-domain and orange VSR outlines above every
  candidate grid; exact RGB checks and manual review confirmed both were
  visible. No projection, geometry, or clipping anomaly was found. This is
  bounded two-day candidate
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

**Final vessel-activity input and descriptive speed summaries, 2026-09-05**

- The production vessel input was generated from the ready 153-date manifest
  `multiday-ais-17e982f999f7093945193378` on the exact water grid
  `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031` under the
  ADR 0018 configuration, giving input identity
  `vessel-input-5e590ff3d85ee7acb16e2fd1`, `vessel-grid.parquet`
  `5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0` and
  `quality-report.json`
  `4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7`.
  An independent repeat in a separate location reproduced both bytes exactly;
  only `run-metadata.json` differed, carrying real execution timestamps as the
  contract intends.
- 4,516 cells; 14,946,183 retained segments; 510,916 excluded (461,769 gap,
  49,147 implied speed); observations 15,458,567 matching the period manifest.
  Distance conservation passed at 0.0 m per group. All-commercial activity is
  2,084,502.496 km, exactly equal in every group to the retained 300/30
  candidate, so the production boundary reuses the tested engine rather than
  duplicating or relabelling it.
- `scripts/verify_production_vessel_input.py` independently reconstructed
  identity, units, speed invariants, lineage and candidate parity across both
  bundles and returned `passed: true`.
- Per-cell water area comes from actual intersected geometry: 431 distinct
  partial areas from 0.002163 to 25 km², 4,085 full-water cells, none above the
  nominal maximum. Speed nulls occur in exactly the 140 cells with no usable SOG
  distance, and that equivalence holds for every row.
- QGIS 4.2.1 inspected the exact checksums across full-context, corridor and
  northern-edge views for activity and a corridor view for reported SOG. It
  confirmed correct placement, islands as holes, peak values at the Los
  Angeles/Long Beach approach, coherent corridors, a speed field structurally
  distinct from activity, and the expected censoring effect at the boundary.
- The first attempt aborted on the profiler's `minimum_available_memory` guard
  with no output; the gate was not relaxed and its evidence is retained. See the
  [M3 completion handoff](m3-completion-handoff.md).

**Not implemented**

- Network AIS transfer and range-resume. The local
  supplied-artifact validation, bounded multi-date delivery intake, resumable
  daily-cleaner orchestration, overlapping real one-day/two-day canonical
  compatibility exercise, seven-day operational gate, July monthly operational
  gate, and August, September, October, and November monthly accumulations are
  complete, so all 153 accepted dates now hold compatible cleaned inputs.
  Publisher-side independent
  byte completeness and observational completeness remain `unverified`; a
  guarded daily bulk download remains unexercised. Independent
  audit of the July evidence passed, and ADR 0017 authorized the author to submit
  and process the August--November calendar-month extracts sequentially under
  the existing controls. Assembling every accepted date is a cleaned-input
  result, not an analytical result.
- Historical route to the final vessel-activity input of ADR 0018, retained
  because it records how the candidates were exercised. Candidate period segment
  construction, explicit filtering, exact grid allocation, per-cell vessel-
  kilometres, union-recomputed distinct counts, quality metadata, and lineage
  are implemented, synthetically verified, and exercised across the four
  documented parameter combinations on the real 15--16 July delivery. The
  candidate exercise used its own separate two-date period manifest, not the
  now-`ready` accumulation-gate manifest. The separate non-spatial period-rule
  evidence command has now run twice on the real 153-date state and reproduced
  exact deterministic evidence bytes, while transfer and observational
  completeness remain `unverified`.
  On 2026-09-05 the same four-candidate matrix was executed against the ready
  153-date manifest on the exact water grid. Eight sequential profiled runs
  completed with no resource abort; each candidate reproduced its GeoParquet and
  quality-report bytes exactly on an independent repeat; all six candidate pairs
  were compared per cell and by vessel group; and the four checksum-bound
  outputs were inspected in QGIS 4.2.1. A distance-accumulation defect found by
  that run was corrected, raising the candidate processing version to `1.1.0`,
  so identities recorded under `1.0.0` no longer reproduce byte-for-byte. The
  edge-support treatment, the type-only vessel-length population, and the
  interpretation of the flagged daily and vessel-group variation are now
  resolved in the [method review](m3-vessel-method-review.md).
  ADR 0018 selected 300 seconds / 30 knots for production, with type-only
  population, cleaned-extent censoring and exact-support treatment. **That final
  production-validation criterion was completed on 2026-09-05 and ADR 0018 is now
  Accepted**; see "Final vessel-activity input" in Progress above. Observational
  and publisher-transfer completeness remain `unverified`, and no exposure
  analysis has been performed, which belongs to M6.
- Normalization of whale or vessel values. Both grid-aligned candidate inputs
  preserve physical or source units; normalization remains part of the deferred
  exposure-method decision.
- A successful GDAL/Pyogrio read-back of the GeoParquet on this machine; its
  driver attempted to load a missing `duckdb.dll`. PyArrow read-back and
  GeoParquet metadata validation passed, but ArcGIS compatibility remains
  unverified.
- End-to-end analytical-period lineage and rerun. Candidate vessel-grid lineage
  now joins the one-extract AIS, projected water-grid, and whale-grid lineage
  boundaries, and a complete 153-date cleaned-input source set now exists. No
  accepted final period-wide vessel grid, speed summaries, exposure result, or
  end-to-end analytical output exists.
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

### Completion criteria status, 2026-09-05

| Criterion                                                                  | State                                                                                                                                                                                                                                                          |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Each derived dataset regenerable from raw inputs by the documented process | **Satisfied.** Documented commands exist for the projected water grid, the whale-density transfer and the production vessel input; the vessel input was regenerated from the ready period and exact grid on 2026-09-05.                                        |
| Rerunning on unchanged inputs produces equivalent outputs                  | **Satisfied.** All three reproduce byte-identically: water grid `7229098c…`, whale grid `421dc7bf…` across two clean runs, and the vessel input's Parquet and quality bytes across an independent repeat. Only timestamp-bearing lineage differs, by contract. |
| Every filtering and aggregation choice documented with rationale           | **Satisfied.** ADR 0013 covers conflicting-key removal, ADR 0018 the gap, speed, population, censoring and support choices, ADR 0006 the speed-summary semantics, with limitations recorded rather than resolved away.                                         |
| Per-cell water areas from actual intersected geometry                      | **Satisfied.** 431 distinct partial areas from 0.002163 to 25 km², 4,085 full-water cells, none above the nominal maximum; verified directly against the output.                                                                                               |
| Intermediate outputs inspected visually, not only programmatically         | **Satisfied.** Water and whale grids in QGIS 4.2.1 on 2026-08-27; the production vessel activity and speed fields on 2026-09-05, each bound to the exact output checksum. Rendering was not treated as inspection.                                             |

All five criteria are satisfied on the evidence above, and **M3 is Complete as
of 2026-09-05**.

Two follow-ups remain explicitly tracked and are **not** M3 completion criteria.
They did not gate this milestone and are now carried forward to named owners so
completing M3 does not drop them:

- a formal reusable verification record with append-only or versioned lineage,
  carried to **M8**; and
- the unverified GDAL/Pyogrio read-back, so publication compatibility with
  ArcGIS is still unestablished, carried to **M5**.

Publisher-side transfer completeness and observational completeness remain
`unverified` and are limitations of the source, not criteria. Exposure
calculation is M6 and is not an M3 criterion.

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
- **Verified route-specific account checks.** Confirm the actual Vercel plan and
  Hobby personal-use eligibility. For the ArcGIS account used only for the
  basemap, confirm the product, pay-as-you-go disabled, remaining applicable
  free-tier headroom, and a read-only browser key restricted to the exact local
  and production origins. Hosted-data publishing, storage, sharing and ArcGIS
  Online organization privileges are not M4 requirements for this selected
  static route and remain unverified unless a later decision selects them.
- A checksum-bound Vercel static deployment that includes the exact ignored
  project files and public manifests selected by the application, then loads
  them token-free from the deployed origin. An Esri publish-and-serve test is
  required only if an accepted decision selects Esri hosting for project data.
- A working deployment of the empty shell.
- Formatting, linting, and type-checking configured.

**Completion criteria**

- The application builds locally and in the deployment environment.
- The map renders, pans, and zooms over the study area.
- No API keys or credentials appear in the repository or in committed build output.
- The deployment is reachable and reflects the current main branch state.
- **The selected route's account checks are complete and recorded.** Vercel is
  confirmed as an eligible Hobby account with no paid plan, trial or add-on.
  The ArcGIS basemap account is identified, pay-as-you-go is confirmed disabled,
  current basemap free-tier headroom is sufficient, and the browser key is
  confirmed read-only and restricted to the exact approved origins.
- From a clean browser with no visitor sign-in, the deployed application loads
  every selected project file token-free from its Vercel origin, verifies the
  fetched checksums, and isolates a failed file without losing the other layers.
  No Esri hosted-data publication test is applicable while ADR 0021 remains the
  selected project-data route.

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
  scene services.
- **Corrected on 2026-09-06.** The 2026-08-31 inventory recorded that
  `Everyone` sharing gives Location Platform hosted services anonymous access.
  That was wrong; it applied cross-product sharing guidance to Location
  Platform. Esri's product-specific
  [data sharing and access guide](https://location.arcgis.com/help/data-sharing-and-access/)
  states that hosted data services in ArcGIS Location Platform are not shared
  publicly, and directs public-facing applications to authenticated access with
  developer credentials such as an API key. The
  [feature-service sharing and security guide](https://developers.arcgis.com/documentation/portal-and-data-services/data-services/feature-services/sharing-and-security/)
  lists `Owner (private)` as the only Location Platform sharing level, requiring
  a scoped API key, while ArcGIS Online additionally offers Organization,
  Group, and `Everyone (public)`. A visitor who never signs in is not the same
  as a token-free service request: a scoped browser key can serve visitors
  without a sign-in, but the service is not anonymous and the account owner
  carries the usage.
- The current documented monthly free tiers relevant here are 2,000,000 basemap
  tiles or 1,000 basemap sessions; 250 MB of feature storage; 250 MB of
  tiles/files/attachments storage; 125 MB each of feature-query and feature-edit
  bandwidth; 25 GB each of vector-tile and map-tile bandwidth; and 25,000 tiles
  generated during publishing. Feature-service access is bandwidth-metered,
  not covered by a documented request-count allowance. These are product-wide
  allowances, not this account's verified balances.
- Location Platform is documented to use free tiers plus optional pay-as-you-go,
  not ArcGIS Online credits. Pay-as-you-go is documented as off by default for
  new accounts, and the author confirmed it disabled on 2026-09-07.
- The author reports creating a Location Platform account and a restricted
  browser API key. The key was absent and was not inspected. No authenticated
  account session was available, so the product identity, service-creation and
  available sharing levels, billing mode, usage, and free-tier headroom have not
  been verified from the real account. The short private author checklist is in
  [development.md](development.md#read-only-capability-inventory-2026-08-31).
- This historical inventory did not create or publish an item. ADR 0021 now
  selects static Vercel delivery for project files, so Location Platform hosted
  data capabilities are unselected and remain unverified; M4 no longer requires
  a throwaway hosted-feature test.

**Not done**

- **The static-shell deployment and deployed-browser verification.** The
  isolated project, stable hostname, completed route-specific account checks,
  and reviewed-main keyed candidate are ready, but no upload has been approved
  or attempted and the hostname serves no production deployment.
- The Vercel deploy-and-serve test. The earlier rehearsal remains deliberately
  keyless and ineligible; only the fresh keyed candidate described below may be
  proposed for upload.

The ordered steps for all of the above are in
[development.md](development.md#selected-route-account-and-service-checks).

### Completion criteria status

**2026-09-07 closure preparation:** `main` and freshly fetched `origin/main`
matched at `c8bf3977b4a43f7b2e691e87011bdda34300fbf7`, with a clean starting
tree. Existing M4 branches were inspected and predated that main state. Work
continues on `feat/m4-release-staging` in a dedicated worktree.

The three retained input GeoJSON files were rehashed and match the application
bindings: whale `831a5412…662e154`, vessel `3a7f2dee…0d3288`, and domain
`7020ca8d…b3bc7bf` (full identities in `web/scripts/release-inputs.json`). The
retained vessel/domain QGIS and browser reports match their previously recorded
SHA-256 values `2cfca5ca…e55a140` and `8e9e1395…5501a`; the inspected geometry
has not changed. The selected whale manifest records a later generation time,
with the same inspected GeoJSON identity. This recheck does not claim a new
spatial inspection or deployed browser test.

Anonymous HTTP requests on 2026-09-07 confirmed public item
`b400c7f418b04dc5a9d7ce5015adae32`, its expected Feature Service, and one
`FID = 126` feature named `California Voluntary Vessel Speed Reduction Zone`,
season `April 22 - December 31, 2026`. Item credit and the non-navigational
disclaimer remain present. No geometry was requested, retained or compared:
the final-results snapshot-comparison gate remains open.

Local staging tooling is implemented for the initial three-input application,
with pinned public manifests, isolated committed-source builds and full upload
inventories. [ADR 0021](decisions/0021-propose-vercel-static-input-delivery.md)
was accepted by the author on 2026-09-07. It selects free Vercel Hobby static
delivery and route-specific checks; an Esri hosted-data test is not applicable
unless a later accepted decision selects that route. That closure-preparation
session did not access an account, create a project or obtain deployment
approval. The later initial-setup evidence below supersedes its then-open
account, hostname and release-key checks. Development owns staging and the
deployment checkpoint.

The keyless isolated rehearsal at implementation commit `4f9b2c2` passed locked
installation, formatting, lint, generated-type checking, all 79 tests and static
build. The prepared package is 36,021,239 bytes across 901 files; receipt SHA-256
is `7cf829418f808bd1092547ebe0e2790eec5220616cc1e4ee353d518d5ef0d815`.
Read-back verification matched the complete upload inventory and all three
compiled checksum-addressed layer URLs. The package is explicitly **not for
deployment** because it has no basemap key and is not a reviewed main release.
Independent audit found a release-root ignore gap and stale test-count prose;
both are corrected and the final independent audit of `5c9d58d` passed with no
unresolved blocking findings, including receipt read-back. No application or analytical behavior
changed. [The M4 handoff](m4-release-staging-handoff.md) retains commands,
artifact locations, failures and the next approval checkpoint.

**2026-09-07 initial deployment setup:** Authenticated Vercel CLI 59.11.7
confirmed the `Stemry` Hobby scope and found only the existing
`stemry-waitlist` project. The separately authorized
`socal-whale-vessel-overlap` project was therefore created without Git
integration or deployment; its verified reserved production hostname is
`https://socal-whale-vessel-overlap.vercel.app`. Only the ignored release
candidate's isolated `deploy/` directory is linked. The existing Stemry project
was not changed.

The author confirmed this is a personal, unpaid, non-monetized portfolio and
confirmed ArcGIS Location Platform with pay-as-you-go disabled. Current basemap
use was 5,292 of the 2,000,000 monthly tile allowance. The replacement key has
no item access or analysis, general or administrator privileges. Service checks
allowed Basemap Styles from exactly `http://localhost:3000` and the reserved
production origin, refused an unrelated origin, and refused Static Basemap
Tiles. No credential value or credential-bearing URL was retained.

The keyed candidate `m4-initial-production-01` was staged from exact merged
`origin/main` commit `8b1f65c8556955d6f28ee86426c09d55b7ea71fa` with the same six pinned
GeoJSON/manifest inputs. Locked installation, formatting, linting,
generated-type checking, all 79 tests and the static build passed. Its 901-file,
36,021,531-byte upload receipt is
`194f8877d040220214205af1b03917fc320e703114513e7ea04bb819f700352a`;
complete read-back passed before and after local project linking. The candidate
is awaiting explicit deployment approval and has not been uploaded.

| Criterion                                                  | State                                                                                                                                                                                                                                        |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Builds locally                                             | **Verified.** Historical browser evidence remains local. Both the keyless rehearsal and reviewed-main keyed candidate passed all 79 tests and the static build with the six pinned input files.                                              |
| Builds in the deployment environment                       | **Unverified.** No deployment environment exists yet.                                                                                                                                                                                        |
| Map renders, pans, and zooms                               | **Verified locally.** The keyed static export rendered `arcgis/oceans`, panned, zoomed, and completed the ready-map attribution handoff in Chrome at all three required viewports. The deployed-origin path remains unverified.              |
| No credentials in the repository or committed build output | **Verified.** Staged diffs were scanned before each commit; build output is ignored.                                                                                                                                                         |
| Deployment reachable and reflecting main                   | **Unverified.** No deployment exists; main has not been deployed or verified.                                                                                                                                                                |
| Route-specific account checks complete and recorded        | **Verified.** Vercel Hobby personal-use eligibility, ArcGIS Location Platform free-tier-only status and headroom, and browser-key validity, minimum scope, no item access and exact referrers were confirmed on 2026-09-07.                  |
| Selected static publish-and-serve test                     | **Not attempted.** The exact files are staged, locally verified and linked to the isolated project, but no upload is approved and no deployment exists. An Esri hosted-data test is not applicable under ADR 0021.                           |
| Unselected Esri hosted-data capabilities                   | **Not applicable to M4 and unverified.** Static project files need no Esri hosted-data service. Documentation-only product facts remain background; actual service creation, storage, sharing and ArcGIS Online privileges were not checked. |

M4 is not complete and must not be marked complete until the route-specific
account checks and the reviewed main-backed Vercel deployment are verified.
The project files must load token-free from the deployed origin with exact
checksums; the basemap remains separately keyed with no visitor sign-in. The
entire route must stay within verified free capacity. Paid plans, trials,
add-ons, pay-as-you-go and other charged usage are prohibited.

### Findings

Recorded because they are version-dependent, were established by running the
tooling rather than reading about it, and constrain later work.

**Toolchain, as verified on the author's machine**

| Component                      | Version                                                                     |
| ------------------------------ | --------------------------------------------------------------------------- |
| Node.js                        | 22.16.0 (Next.js 16 requires `>=20.9.0`)                                    |
| npm                            | 10.9.2 — the only package manager present                                   |
| Next.js                        | 16.3.3                                                                      |
| React                          | 19.2.8                                                                      |
| ArcGIS Maps SDK for JavaScript | 5.1.20 (`@arcgis/core` and `@arcgis/map-components`)                        |
| Calcite components             | 5.1.2 (`@esri/calcite-components`) — versioned separately from the Maps SDK |
| Vitest                         | 4.1.11                                                                      |

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

- **The project-data route is resolved.** ADR 0021 selects checksum-addressed
  static files on free Vercel Hobby. Esri hosted-data product facts remain
  documented background; actual publishing capabilities are unverified and do
  not constrain M4 while those routes remain unselected.
- Vercel Hobby eligibility and ArcGIS Location Platform free-tier-only basemap
  access were verified on 2026-09-07. Continued free capacity and deployed
  behavior remain release checks; no paid fallback is authorized. **Resolved
  for initial deployment eligibility; runtime verification remains open.**
- ArcGIS SDK licensing and API-key requirements for the intended hosting model need confirming before public deployment. **Resolved for setup:** the minimum browser key and its exact localhost and production referrers were verified against the Basemap Styles service. Clean-browser access from the actual deployment remains unverified.
- Bundle size and initial load time of the SDK need an early look rather than a late one. **Resolved for size** — see the findings above. Load time still needs measuring on a real deployment.
- Vercel Hobby is selected and the route-specific account checks passed. The
  isolated project and reviewed-main keyed candidate exist; no deployment has
  been uploaded.

---

## M5 — Core input layers

**Status:** In progress

**Objective**
Prepare the validated input datasets for public delivery and make them visible
in the application through the evidence-selected publication route.

**Dependencies**

- M3 (validated derived datasets exist).
- M4 (application shell exists and selected-route capability evidence is recorded).

### Progress

**All core input-layer displays implemented and locally verified; public
delivery remains unfinished**

- The static client creates an ArcGIS `FeatureLayer` from the publisher's exact
  `WhaleAtlas_2026/FeatureServer/0` URL and applies `FID = 126`. Source identity,
  item, filter, expected one-feature response, attribution, and disclaimer live
  in one typed configuration module; no VSR geometry is stored, transformed, or
  republished by the application.
- A stable layer ID and owned-resource cleanup prevent duplicate layers across
  repeated ready events and React cleanup/remount behavior. Loading is tracked
  separately from basemap initialization, bounded to 15 seconds, and verified
  to reject a zero or otherwise unexpected filtered feature count.
- The map provides a native checked visibility control, compact line legend,
  publisher attribution, and an inline disclosure carrying the complete
  non-navigational use notice. Controls have visible keyboard focus and preserve
  space for ArcGIS zoom controls and SDK attribution.
- On 2026-09-02 the keyed production/static export rendered the oceans basemap
  and filtered boundary in the correct Southern California location in headless
  Chrome at exact 390 × 844, 820 × 1180, and 1440 × 900 viewports. Visibility
  hid and restored the layer, repeated ready events retained exactly one layer,
  source/use content was reachable, and no horizontal overflow, HTTP error,
  unexpected request failure, sign-in prompt, or unexpected console error was
  observed. Publisher layer metadata and filtered query requests returned HTTP 200.
- A separate 820 × 1180 check blocked only the publisher endpoint. It produced
  the accessible VSR warning and the expected SDK layer-load console errors,
  removed the failed layer, and retained a ready, non-updating oceans basemap,
  zoom controls, and SDK attribution without an indefinite loading state or
  sign-in prompt.

**Whale display representation implemented and locally verified; not published**

- A versioned `blue_whale_display_export_v1` boundary in `analysis/` turns the
  validated `blue_whale_grid_transfer_v1` GeoParquet into RFC 7946 WGS 84
  GeoJSON plus a sanitized, publishable manifest. It requires the source
  checksum, validates the source contract before transforming anything, and
  changes representation only: no value is recomputed, rescaled, rounded, or
  simplified, and no geometry is densified. Destinations are an allowlist of
  this checkout's Git-ignored output roots, and generated layer data is not
  committed. The commands are in
  [development.md](development.md); the contract is in
  [`../analysis/README.md`](../analysis/README.md).
- The export from source
  `421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62` is
  3,277,329 bytes with SHA-256
  `831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154`: 4,516
  features, 4,561 polygon parts, 35 interior rings, 44,773 positions, modeled
  density 0.00083394 to 0.007648247 animals/km², conserving 344.1406562623342
  modeled animals. Two exports from separately generated source copies were
  byte-identical.
- The manifest publishes seven fields and records the reason each of twelve
  source columns is withheld. It is rebuilt field by field from a named
  allowlist, so no filesystem path, credential, raw input, private lineage, or
  VSR-derived value can reach a public artifact.
- **QGIS 4.2.1 with GDAL 3.13.2 verified the exact browser-facing file on
  2026-09-06**, opened directly through OGR and bound to its output checksum.
  Counts, rings, positions, extent and value range all matched the manifest.
  Five checksum-recorded renders showed correct Southern California placement
  and axis order, clean 35° N and southern clipping, correct island holes, and
  cell-scale detail with no unexplained gap, sliver, displacement, or
  projection artifact.
- The application draws the layer with an ArcGIS `GeoJSONLayer` whose geometry
  type, spatial reference, object-id field and field schema are declared
  explicitly, added beneath the VSR outline, bounded to 30 seconds, asserting
  the expected 4,516 cells, and failing in isolation. It carries a density
  legend in animals/km², per-cell popups, a visibility control, and an
  accessible source-and-method disclosure with the NOAA/SWFSC credit, the
  requested citations, the method, and the artifact checksums. The browser
  hashes the fetched bytes and refuses a file that does not match the checksum
  this build records, so the identity shown is verified rather than asserted.
- **Browser verification on 2026-09-06** in headless Chrome, from the
  authorized localhost origin, at exact 390 × 844, 820 × 1180 and 1440 × 900:
  the layer loaded with 4,516 features at every size, exactly one whale layer
  and one VSR layer were present with the whale layer beneath, the legend and
  all five class labels were readable, the visibility control worked, keyboard
  traversal gave a visible focus outline, and a popup reported values matching
  the export exactly at the declared precision. Blocking the layer left the
  basemap and VSR usable with an accessible warning; serving a different file
  with the same feature count was refused on the checksum.
- Symbology is five equal 0.001 animals/km² classes with an open lowest and
  highest class, **recorded as a display choice and stated as one in the
  interface**, holding 1,103 / 1,388 / 765 / 527 / 733 of the 4,516 cells.
- The earlier whale-only stage measured 3.13 MiB uncompressed, 0.55 MiB
  gzipped, and 0.38 MiB Brotli; its contemporaneous static export was 30.75 MiB
  across 895 files. The layer was usable roughly 1.9 s after navigation cold and
  1.0 s warm over loopback without compression or throttling. These are local
  observations of this project's own asset, not a benchmark of ArcGIS services
  and not evidence about a deployed origin.

**Vessel-activity and analytical-domain displays implemented and locally
verified; not published**

- `commercial_vessel_display_export_v1` and
  `analytical_domain_display_export_v1` checksum-verify the accepted production
  vessel grid, its quality report, the analytical-domain mask, and its evidence
  report before exporting two deterministic RFC 7946 WGS 84 GeoJSON files with
  sanitized manifests. The vessel export clips source-cell water geometry to
  the exact `receivers_50_nautical_miles` domain in EPSG:3310 but preserves each
  complete source-cell vessel value; no speed, distinct-vessel descriptor, value
  rescaling, simplification, rounding, densification, or VSR geometry enters
  either display artifact.
- The vessel export has 2,793 features: 2,641 full cells and 152 partial cells,
  including 137 cells with zero retained movement. Its SHA-256 is
  `3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288`.
  The one-feature domain export has SHA-256
  `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf`.
  A separate repeat reproduced both GeoJSON files byte-identically.
- **QGIS 4.2.1 with GDAL 3.13.2 verified both exact files on 2026-09-06.**
  Counts and geometry diagnostics matched the manifests; neither layer had an
  empty or invalid geometry, no vessel geometry lay outside the domain, and
  five checksum-recorded views showed coherent receiver-boundary clipping,
  holes/islands, and traffic corridors without visible displacement, sliver,
  or unexpected gap.
- The client checksum-verifies all project GeoJSON bytes before creating an
  ArcGIS layer. Each invocation has independent fetch, load, count, timeout,
  failure, cleanup, and stale-execution protection, so an old completion or
  rejection cannot overwrite or remove a replacement or another input layer.
  Deterministic order keeps whale and vessel fills below the analytical-domain
  and publisher VSR outlines. Whale and domain start visible; vessel starts
  hidden so the two analytical fills do not obscure each other initially.
- The vessel legend uses a neutral zero-retained-movement class and fixed
  intervals over 0–1, 1–5, 5–20, 20–100, and over 100
  vessel-km/km² of modeled-whale-support water. These are stated display
  intervals, not analytical categories. The domain legend says that outside
  water is excluded, not low activity, and the disclosures retain the
  unverified-observational-completeness limitation.
- **Browser verification on 2026-09-06** in headless Chrome 152 at exact
  390 × 844, 820 × 1180, and 1440 × 900 viewports loaded 4,516 whale cells,
  2,793 vessel cells, one domain feature, and one publisher VSR feature exactly
  once with the intended ordering. Controls, legends, disclosures, constrained
  panel scrolling, keyboard focus, attribution, and responsive containment
  passed. Missing, checksum-mismatched, and ArcGIS-malformed vessel files failed
  in isolation while the other layers remained ready.
- The new files measure 2,720,788 and 867,910 raw bytes, or 385,764 and 199,834
  bytes with Brotli. All three project input files total 6,866,027 raw bytes
  and 982,450 Brotli bytes. The completed local static export contains 899 files
  and 35,862,761 bytes. These are local file and rendering measurements, not
  deployed transfer claims or evidence of hosting access.

**What this does not establish**

- **Nothing has been deployed or published.** There is no public URL, and no
  anonymous end-to-end access, deployed-origin service access, real compression
  or cache behaviour, or clean-browser verification exists. ADR 0021 selects
  checksum-addressed static same-origin delivery on free Vercel Hobby, but the
  actual plan, personal-use eligibility and provider acceptance of the staged
  prebuilt deployment remain unverified.
- The exposure display/results contract is implemented and locally verified,
  but M7 integration and deployment remain open.
- The route-specific Vercel and ArcGIS basemap account checks M4 requires are
  still outstanding. Esri hosted-data capabilities are unselected and are not
  M4 gates.
- M5 remains in progress, and its completion criteria are not met.

**Deliverables**

- Study area, whale density, and vessel activity prepared in a selected public
  representation based on measured output size, browser performance,
  redistribution terms, and real account capabilities.
- **Carried forward from M3:** establish publication compatibility for the
  derived GeoParquet outputs. A GDAL/Pyogrio read-back on this machine failed
  when its driver could not load `duckdb.dll`; PyArrow read-back and GeoParquet
  metadata validation passed, so ArcGIS compatibility is unverified rather than
  known bad. This did not gate M3.
- The VSR boundary loaded inside the project map directly from the publisher's
  public `WhaleAtlas_2026` Feature Service using `FID = 126`, with Danielle
  Alvarez, CMSF, and BWBS attribution and the publisher's non-navigational
  disclaimer. No VSR geometry is copied into project-controlled hosting.
- A public representation for the project-derived layers. **ADR 0021 selects
  deterministic, checksum-addressed static same-origin files on free Vercel
  Hobby.** The whale, vessel-activity, and accepted analytical-domain exports are
  verified locally but not published. The exposure display/results contract is
  also locally verified and awaits M7 integration. Esri hosted-data routes are
  unselected and remain unverified.
- The ArcGIS Maps SDK application assembling the public layers with symbology
  chosen for legibility, not decoration.
- Layer visibility control and legends in the application.
- Popups or panels that state what each layer's values mean, including units.
- Recorded mapping from each project-derived public layer representation back to the validated
  derived dataset, output checksum, visual-verification evidence, and
  processing/export steps that produced it. **Recorded for the whale,
  vessel-activity, and analytical-domain layers** in this milestone's progress
  notes and the [whale](m5-whale-display-handoff.md) and
  [vessel/domain](m5-vessel-domain-display-handoff.md) handoffs.
- Recorded VSR item, service, feature filter, attribution, disclaimer, and
  comparison with the analytical snapshot.

**Completion criteria**

- Each layer renders at the study-area scale within an acceptable load time.
  **Met locally only for all three project input layers**, on one machine over
  loopback; deployed load time is unmeasured.
- Public access works end to end from the application: a visitor reaches every
  layer from the deployed origin without an interactive sign-in, and the record
  states for each layer whether that access is token-free or carried by a
  scoped browser credential, since those are different claims. When neither
  Esri hosting route is suitable, this criterion is verified later against the
  selected route rather than waived. **Not met for any project-derived layer:
  nothing is deployed and there is no public URL.** The implemented whale route
  would be token-free, because a static same-origin file needs no credential,
  but that is unverified from a deployed origin. The same is true of the
  implemented vessel and domain routes.
- Every layer's legend states its units and the meaning of its values.
  **Met locally for the whale, vessel-activity, and analytical-domain layers.**
- Every layer names its source and its retrieval or processing date somewhere the user can reach.
  **Met for the whale layer; incomplete for vessel and domain.** The vessel
  disclosure names its source and analytical period but not a retrieval or
  processing date. The domain disclosure names its source inputs but not their
  retrieval or processing date.
- Layer geometry visually aligns across layers; no projection mismatch is visible.
  **Observed among the whale, vessel-activity, analytical-domain, publisher VSR,
  and basemap layers in the local browser check**, with separate checksum-bound
  QGIS inspection of all three project input files.
- The VSR feature loads anonymously from the publisher's service and is not a
  project-hosted copy. **Met locally.**

The local display, legend, provenance, and alignment evidence now covers every
core input layer. Static delivery is selected by ADR 0021; deployment, remaining
route-specific account evidence, and deployed-origin verification remain
unfinished, so M5 stays in progress.

**Risks and open questions**

- Deployed transfer behavior, low-end-device performance, or host limits may
  still force a different representation, aggregation, or generalization.
- Raster and vector outputs may need different public delivery methods.
- Symbology for a continuous density surface needs a defensible classification, since the class breaks chosen will shape how the map is read.
- The publisher can change, remove, rate-limit, or make the VSR service private.
  The displayed remote geometry can also drift from the local analytical
  snapshot; release verification in M9 must detect and address that condition.

---

## M6 — Whale–vessel exposure analysis

**Status:** In progress

**Objective**
Produce the project's own analytical result: a documented relative exposure layer, and the inside-versus-outside VSR statistics derived from it. This is the milestone that makes the project an analysis rather than a viewer.

**Dependencies**

- M3 (validated, grid-aligned whale and vessel inputs).
- M2 (understood value meanings and units for both inputs).

### Progress

**Method accepted for exploratory execution, computed and locally verified;
downstream delivery contracts implemented; independent audit, owner acceptance,
M7 integration, and release remain open**

- [ADR 0020](decisions/0020-propose-area-integrated-relative-exposure.md)
  defines the calculation: per cell, modeled whale density multiplied by period
  vessel distance, both taken over that cell's **full** water area, and the
  resulting intensity then integrated over its **qualified** water and that
  water's exact inside/outside VSR split. Speed is kept separate under
  [ADR 0006](decisions/0006-report-vessel-speed-separately.md). Physical values
  are used for calculation and a maximum-scaled index for display. High exposure
  is the qualified-area-weighted 90th percentile, reported alongside 80 and 95,
  a positive-only reference, a nonlinear traffic-scaling comparison and a 10 km
  grid comparison. The owner authorized this method for bounded exploratory
  execution on 2026-09-06; that authorization does not accept the results.
- The fractional VSR accounting required by
  [ADR 0004](decisions/0004-analysis-grid-resolution.md) is implemented in
  `exposure_geometry` and passes the ADR's synthetic cases, including the cell
  45% inside the zone that centroid and majority assignment both score as fully
  outside. Area conservation and the uniform-within-water-cell assumption are
  tested and labelled.
- Exploratory production and repeat runs completed on 2026-09-06 against the
  exact retained M3 water, whale and vessel inputs, under the established M3
  resource gates, and produced byte-identical deterministic outputs. The
  recorded run identity `exposure-cc50a1e9fb06ca3ae5b5e395` and the artifact
  hashes in the handoff are **historical**: they predate the later correction
  that removed execution lineage from run identity. The numerical evidence below
  remains valid, but a newly generated bundle will carry a different identity
  and different `run-metadata.json` hashes, so those values are a record of what
  was run, not expected outputs to reproduce. Qualified water area is
  64,716.65982166734 km² at both resolutions; the 5 km layer has 4,516 rows
  (2,793 qualified) and the 10 km layer 1,155 rows (738 qualified). The bundle
  is ignored local evidence under `data/derived/`; nothing is published.
- Two fresh current-code analytical runs preserved those numerical values and
  produced the same run ID, `exposure-6dd927974fae959765c9b5c3`, plus
  byte-identical 5 km, 10 km, and sensitivity-report files despite distinct
  timestamp-bearing upstream lineage. This verifies the corrected separation
  between deterministic analytical identity and private execution provenance.
  The runs processed only the retained small grid tables under the documented
  memory/disk/RSS gates; no AIS retrieval, five-month cleaning, cache clearing,
  or historical-artifact replacement occurred.
- Distinct downstream contracts now exist:
  `relative_exposure_display_v1`, its
  `relative_exposure_display_manifest_v1`, and
  `relative_exposure_application_results_v1` schema 1. The display has 2,793
  qualified-water 5 km features and is 2,542,744 bytes raw, 528,235 gzip, and
  375,238 Brotli; the small tracked results artifact is 31,381 bytes. The
  manifest binds the exact display checksum to results ID
  `exposure-results-8a0bf6c27e00fb40a13d6870` and its checksum. Static
  same-origin delivery is selected by ADR 0021; publication, application
  integration, deployment and deployed verification remain unfinished.
- The exporter verifies pinned source bytes, re-verifies both analytical tables,
  recomputes the accepted summaries from their serialized rows, and reconciles
  the complete supplied report. A matching checksum identifies report bytes but
  does not establish their numerical correctness. Public nested objects are
  built through explicit typed allowlists; unexpected fields, invalid controlled
  text/enumerations, private paths, credentials, debug metadata, execution
  clocks, and private generation lineage cannot propagate.
- The final display and manifest passed checksum-bound inspection in QGIS 4.2.1
  / GDAL 3.13.2: EPSG:4326, 2,793 nonempty valid geometries, and matching feature,
  part, hole, vertex, area, extent, and threshold-flag summaries. Qualified
  domain-water geometry is the only public geometry. The immutable local VSR was
  inspection context only; no copied or derived VSR geometry was exported.
- Final verification passed 24 focused exposure-delivery tests and the full 647-
  test analysis suite, plus lock, format, lint, strict type-check, and build
  gates. Known answers cover statistics, denominators, nulls, thresholds,
  presentation rounding, incompatible provenance, checksum-matched but
  internally inconsistent reports, private/debug injection, deterministic
  repeat, and timestamp-independent results identity.
- Primary 5 km product results: **92.2185%** of integrated exposure inside the
  VSR zone, and 93.6947 / 98.5024 / 99.9401% of selected high-exposure water
  area at the 80th, 90th and 95th percentiles. These are exploratory overlap
  shares, not collision probabilities, predicted strikes or accepted headlines.
- The sensitivity check is documented and one result is **not robust**:
  log-compressing traffic moves the 5 km inside share down 17.2741 percentage
  points, to 74.9444%. That is dependence on the chosen formula, not a
  confidence interval, and its magnitude is in different units and cannot be
  compared with the product magnitude. Coarsening to 10 km changes the product
  integrated total by −0.006753% and its inside share by +0.027805 points, but
  the p80 high-area share by about 4.15 points, so integrated stability does not
  generalize to every statistic. Product/log cell-rank Spearman correlation is
  0.959254 at 5 km, and the two methods' top-ten outside contributor lists share
  only five cells.
- Largest outside concentrations are recorded as contribution rankings, not
  validated hotspot clusters: the product method's leading outside cells are
  `r015_c079`, `r015_c078` and `r016_c054`, whose top ten contribute 9.4717% of
  outside exposure.
- **Proposed interpretation, pending owner review:** under the proportional
  product, most modeled blue-whale-habitat and commercial-vessel-activity
  co-occurrence in receiver-qualified Southern California water is concentrated
  inside the current VSR zone. This is not formula-invariant: the required
  log-traffic sensitivity materially lowers the integrated inside share and
  broadens the spatial pattern. The defensible scope is exploratory spatial
  overlap, not collision probability, causation, avoided collisions, VSR
  effectiveness, an optimal boundary, or a policy recommendation. The mixed
  vintages — modeled multi-year whale density, July–November 2024 traffic, and
  the 2026 VSR boundary — and the uniform-within-water-cell assumption must
  remain visible. These sentences are interpretation for review, distinct from
  the computed observations above, and are not accepted website copy.
- QGIS 4.2.1 rendered the exact first-bundle checksums with the pinned local VSR
  and domain. Coastline and island holes, curved receiver clipping, absence of
  colored geometry outside qualification, and VSR boundaries crossing cells
  without whole-cell assignment were all confirmed; both EPSG:3310 layers had
  zero invalid nonempty geometries. No VSR-derived geometry or image was
  committed or exported.
- Review status, stated separately because the two are easy to conflate:
  - **Done.** The owner authorized the method, its threshold family and its
    sensitivity checks for exploratory execution on 2026-09-06. In-session
    implementation verification is complete: the synthetic suites pass, the
    first and repeat runs are byte-identical, `exposure_run` reads its own
    output back and re-checks formula, integration, geometry, nulls, indices,
    flags and summaries, and the bundle was rendered in QGIS against its exact
    checksums. The downstream delivery boundary additionally reconciles the full
    report against the verified tables, sanitizes typed public projections,
    reproduces exact bytes from independent current-code bundles, and has its
    own checksum-bound final-display QGIS evidence.
  - **Pending.** Independent review of the implementation and the results by
    another session, per the
    [review workflow](development.md#pull-request-and-continuous-integration-workflow),
    covering units, the full-water-intensity versus qualified-integration
    split, complete-support admission, fractional joint geometry, quantiles and
    ties, coarsening and retained source evidence. Then owner acceptance of the
    results and of the final messaging — the 2026-09-06 authorization permits
    the calculation, it does not settle which statements, if any, become
    headline findings. Human scientific and cartographic review of the maps is
    also outstanding.
- Also not done: independent audit, owner conclusion/map review, propagation of
  native whale uncertainty, M7 application consumption through the static route
  selected by ADR 0021, browser verification, and the M9 release-time VSR
  comparison. Analytical execution detail is in the
  [M6 foundation handoff](m6-exposure-foundation-handoff.md); downstream contract,
  artifact, resource, repeat, and final QGIS evidence is in the
  [M6 exposure-results delivery handoff](m6-exposure-results-delivery-handoff.md).
  These are navigation and evidence, not the owner of this status.

**Deliverables**

- A written definition of the relative exposure calculation: inputs, normalization, weighting, combination method, and units.
- The derived exposure or hotspot layer over the study area.
- Inside-versus-outside VSR statistics: share of total relative exposure, share of high-exposure area, and the threshold definitions used. **Computed from the immutable local analytical snapshot by fractional area intersection** — each cell's water geometry is intersected with that VSR polygon and its exposure split by the resulting area fractions. The remotely displayed service is not substituted for this input. Whole-cell, centroid, and majority-area assignment are all excluded; see [ADR 0004](decisions/0004-analysis-grid-resolution.md).
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
- The project-derived exposure layer and the statistics are consistent: the
  numbers are computed from the validated analytical output, and VSR fractions
  use the recorded local snapshot. Before release, the publisher-hosted display
  geometry is compared with that snapshot. If they differ, the application is
  not released while displaying the mismatched boundary: the analysis is rerun
  or reconciled so they match, or the remote boundary is omitted. A warning
  alone does not satisfy this release gate.

**Completion criteria status, 2026-09-06**

- Reproducible from the derived inputs: **met for the exploratory bundle** —
  first and repeat runs produced byte-identical deterministic files from pinned,
  checksum-verified retained inputs.
- Every statistic states its basis and threshold: **met in the retained report
  and machine-readable results contract** —
  integrated shares are distinguished from high-exposure **water-area** shares,
  and thresholds are qualified-area-weighted observed quantiles including zeros
  and all ties. Not yet met in application-facing narrative, because M7 has not
  started.
- Fractional boundary statistics with passing synthetic cases and a labelled
  uniformity assumption: **met**.
- Accepted analytical domain applied exactly: **met** — results use the
  `receivers_50_nautical_miles` qualified geometry, and outside-domain cells are
  excluded rather than reclassified.
- Brief-compliant vocabulary with no risk or probability language: **met in the
  handoff and this record**; unverified for release text.
- Sensitivity documented, including non-robust conclusions: **met** — the
  log-traffic result is recorded as materially non-robust.
- Layer and statistics consistent, with the pre-release comparison of the
  publisher-hosted display geometry against the local snapshot: **met locally
  for the checksum-bound delivery artifacts; release criterion not met** — the
  exporter verifies every public numerical field against the analytical bundle
  and the final display passed QGIS inspection, but no exposure layer is
  published and the publisher-hosted VSR comparison still belongs to M9.

Independent review of the exact commit and artifacts, and owner acceptance of
the results, sensitivity, maps and final messaging, are also outstanding, so M6
stays in progress.

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

The M6 display/results artifacts now exist for integration without recomputing
science, but M5 remains incomplete, the selected static route is not deployed,
M6 still awaits independent audit and owner acceptance, and M7 has not started.

**Deliverables**

- The derived exposure layer delivered through the selected public route and
  rendered in the application.
- A results panel presenting the inside-versus-outside statistics.
- Explanatory text stating what the exposure layer represents, in plain language, with its assumptions visible at the point of reading.
- Methodology and limitations reachable from the application, not only from the repository.
- Responsive behavior adequate for a reviewer opening the app on a laptop or phone.
- Contract-pinned consumption of `results/exposure-results.v1.json`: use
  `scenarios.5km_product` as the primary measure, keep
  `scenarios.5km_log_traffic` plainly visible as required sensitivity, and use
  the generated presentation strings rather than transcribing or recalculating
  values. Default high-exposure text to the all-valid p90 definition while
  retaining p80/p95 and positive-only sensitivity information.
- Exact pairing of the selected display bytes and manifest with the committed
  results checksum and results ID. Excluded cells render as no analytical
  coverage, never low or zero; indices remain release-relative. Public VSR
  context continues to reference publisher-hosted `FID = 126` and never copies
  local analytical VSR geometry.

**Completion criteria**

- The statistics displayed match the documented analysis exactly.
- A first-time visitor can tell what they are looking at without reading the repository.
- Limitations are visible in the interface, not hidden behind a link nobody clicks.
- No wording in the interface violates the project's scientific communication rules.
- The application remains usable on a mid-range connection.

**Risks and open questions**

- Presenting a single headline percentage invites overinterpretation; the framing needs care.
- The measured static exposure artifact uses the selected same-origin route,
  but browser performance with all layers and responsive behavior remain open.

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
- **Carried forward from M3:** a formal reusable verification record or command,
  plus append-only or versioned lineage. Generation-time lineage is written once
  and must not be hand-edited, so a later verification currently lives only in
  documentation tied to an output checksum. This did not gate M3.

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
- Anonymous release-time verification that ArcGIS item
  `b400c7f418b04dc5a9d7ce5015adae32`, its expected layer, and `FID = 126` still
  exist, plus a comparison of the current remote geometry with the immutable
  local analytical snapshot.

**Completion criteria**

- The deployed application works from a clean browser session with no local setup.
- The README communicates the question, the method, the result, and the limitations without requiring any other document.
- Every documentation link resolves.
- Nothing in the repository claims a capability that does not exist.
- Version 1 scope items in [project-brief.md](project-brief.md) are all satisfied or explicitly recorded as reduced, with the reason.
- The displayed VSR source matches the analytical snapshot that produced the
  statistics. If release-time verification finds a mismatch, the analysis is
  rerun or reconciled so they match, or the mismatched remote boundary is not
  displayed in the released application; a warning alone is insufficient.

**Risks and open questions**

- **Public delivery depends on verifying the selected route.** ADR 0021 selects
  checksum-addressed static files on free Vercel Hobby, which the author
  confirmed on 2026-09-07. Personal-use eligibility, free capacity, and
  deployed-browser behavior remain unverified. A failed free check stops
  deployment; no paid fallback is authorized.
- Esri hosted-data services are unselected. Choosing one later requires a
  superseding decision and route-specific evidence; their current account
  capabilities are not M4 prerequisites.
- Deployment hosting and any ArcGIS credential requirements must be settled before release, not at release.
- The external VSR service can change, disappear, be rate-limited, or become
  private. Version 1 uses a documented release-time check rather than an
  automatic monitoring or synchronization service.
- Screenshots and headline numbers go stale if the analysis is later revised; they need a stated "results as of" date.

---

## Version progression beyond Version 1

These are candidate directions for Version 2 and later. They are ordered roughly by how directly they build on Version 1, not by priority, and none is committed. Each requires its own data and methodology validation before it can be attempted, and each may prove infeasible with publicly available data.

Nothing in this section is a guaranteed scientific result. A proxy is a proxy, and a scenario is a hypothetical GIS experiment, not a finding and not a recommendation.

**UI/UX refinement**
Improve how the exposure layer is explained and read: legend and classification design, guided interpretation, comparison views, mobile layout, and accessibility. Depends on Version 1 being deployed and on observing where the current presentation misleads.

**Temporal analysis**
Break the overlap down by month or across the VSR season. M2 found that the selected whale model is not time-varying, so the current input cannot support seasonal claims. This direction requires a different validated whale input as well as AIS coverage at the intended time step.

**Underwater-noise analysis**
Derive an estimated acoustic proxy from vessel traffic, vessel characteristics, and speed, following published methodology. Requires a defensible published method and the vessel attributes that method needs. AIS alone does not give sound levels, and any output must be presented as a modeled proxy with stated assumptions.

**Emissions analysis**
Estimate relative emissions intensity and how it varies with speed, following published methodology. Requires emission factors and vessel attributes that the AIS data may not carry. Any output is an estimate, not an inventory.

**Scenario analysis**
Compare how hypothetical zone geometries or exposure thresholds would change coverage of high-exposure areas. Depends on a Version 1 exposure layer whose sensitivity is already characterized, since scenario differences are only meaningful if the underlying index is stable. Framed as GIS experiments; the project does not recommend boundary changes.
