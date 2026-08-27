# Architecture

**Owns:** system design, component boundaries, and deferred design decisions.

> **Status: accepted as the initial architecture.** Recorded in [ADR 0001](decisions/0001-accept-initial-architecture.md).
>
> Accepted means this is the direction implementation follows. It does not mean it is proven. The application shell, Python processing foundation, one-extract AIS cleaning slice, and projected water-grid slice are implemented — see M3 and M4 in the [roadmap](roadmap.md). Retrieval, remaining spatial aggregation and exposure processing, publishable derived layers, deployment, and the hosting half of this design are not. The repository also contains one data-discovery verification utility, [tools/](../tools/README.md), which is separate from the analysis package.
>
> Data discovery has established the dataset formats and resolutions several parts depended on, and the licensing position for both NOAA sources — see [data-sources.md](data-sources.md) — and some of the deferred decisions at the end of this document are now resolved. **Three things remain open, and each gates a different part of delivery:**
>
> 1. **The analytical and statistical domain** — [ADR 0002](decisions/0002-southern-california-study-area-extent.md), still Proposed, because AIS coverage offshore is unestablished. Gates the exposure statistics.
> 2. **Redistribution of the VSR zone geometry** — publicly shared by BWBS/CMSF with attribution, but with no redistribution grant, and the publisher is not a federal agency. Gates hosting that geometry as a project-owned layer. **Referencing the publisher's own service from the application remains available and is not affected**, so this constrains the hosting approach rather than the delivery.
> 3. **The ArcGIS Online capability gate** — still unverified.
>
> Changes to an accepted architecture are recorded as decision records under [decisions/](decisions/README.md) rather than made silently.
>
> Of the source-code layout near the end of this document, `web/` and `analysis/` now exist. `arcgis/` and `results/` remain deliberately uncreated.

---

## System context

The system has three kinds of participant:

- **Authoritative external publishers** — NOAA and the California BWBS program — who publish the whale distribution model, the AIS vessel records, and the VSR zone definition. They are read-only upstreams. See [data-sources.md](data-sources.md).
- **The author, working offline**, who retrieves that data, inspects it, processes it into derived datasets, and publishes the results. All analysis happens here.
- **A visitor's browser**, which loads a static web application and reads published layers. The browser displays and filters; it does not analyze.

The important boundary is between the second and third: **every analytical decision is made offline and published as a result.** The browser never recomputes the exposure index. This keeps the analysis reproducible, keeps the client fast, and keeps the numbers shown to a visitor identical to the numbers in the documentation.

## End-to-end data flow

```
Authoritative sources
  NOAA whale distribution model
  NOAA / USCG AIS vessel records
  California BWBS VSR zone definition
        |
        v
Local raw data store  (not committed to Git)
        |
        v
Offline processing    (ArcGIS Pro and/or Python)
  inspect -> clean -> reproject -> clip to study area
  -> aggregate onto analysis grid -> combine -> derive exposure
        |
        v
Validated derived datasets  (+ recorded lineage)
        |
        v
ArcGIS Online
  hosted feature / tile layers
  web map
        |
        v
Next.js + TypeScript application
  ArcGIS Maps SDK for JavaScript
        |
        v
Static deployment  ->  visitor's browser
```

Summary statistics follow the same path: they are computed offline in the processing step, checked against the published layers, and delivered to the application as a small committed data file rather than recomputed client-side.

## Component responsibilities

### ArcGIS Pro

- Visual inspection of source data — the fastest way to notice that a dataset is in the wrong place, the wrong projection, or the wrong units.
- Exploratory spatial analysis while the method is still being worked out.
- Cartographic work: symbology, classification, and layouts.
- Publishing derived datasets to ArcGIS Online.
- Geoprocessing that is materially easier in Pro than in code.

**Constraint:** anything done in Pro that affects a published result must be reproducible. A sequence of manual clicks that cannot be repeated is not an acceptable production step. Pro work that shapes results should be either recorded as an ordered, parameter-level written procedure, or exported to a script or model that can be rerun.

### Python

**Implemented in part.** The src-based package under
[`analysis/`](../analysis/README.md) has a uv-locked Python 3.13 environment, a
module/console entry points, versioned analytical-period,
map/grid/source/whale/AIS/VSR/lineage contracts, read-only source validators,
and deterministic processing for one explicitly supplied NOAA AIS flat CSV
extract whose valid timestamps belong to exactly one UTC date. The extract may
cover only part of that date, so completeness remains `unverified` without
retrieval evidence. The command emits an atomic cleaned Parquet/report/lineage
bundle over the map extent, records real execution timestamps separately from
the analytical period, and applies the duplicate policy in
[ADR 0013](decisions/0013-remove-conflicting-ais-key-records.md). The
configuration records the accepted 1 July–30 November 2024 period while keeping
the analytical/statistical domain unresolved. A separate spatial module
validates and unions an explicitly supplied polygon mask, reprojects it to
EPSG:3310 with explicit x/y ordering, clips it to a densified projection of the
configured WGS84 map/context extent, constructs the exact configured grid, and
writes actual per-cell water intersections as deterministic GeoParquet with
lineage. The map/context clip is not a statistical-domain decision. It does not
retrieve data, transfer whale values, aggregate vessels, calculate relative
exposure, or derive statistics.

DuckDB is the single primary engine for large AIS tables, selected by the
equivalent-operation benchmark in [ADR 0012](decisions/0012-use-duckdb-for-large-tabular-processing.md).
Polars remains only in a benchmark dependency group and is not a second
production pipeline.

- Retrieval and bulk handling of AIS records, which are too large and too repetitive for manual work.
- Cleaning and filtering: vessel-class selection, implausible-position and implausible-speed removal, deduplication.
- Grid construction and water-mask intersection. **Implemented.** The grid is
  always constructed from the accepted bounds and does not infer its extent or
  origin from the input. The biological-support mask is first clipped to the
  configured WGS84 map/context polygon after 0.01° edge densification and
  EPSG:3310 projection. Dry cells are omitted and every retained row carries
  actual intersected geometry and area in EPSG:3310. [ADR
  0014](decisions/0014-select-the-grid-water-mask.md) selects the NOAA 2020b
  whale-model footprint as the biological-support mask while keeping it
  separate from both an authoritative shoreline and future AIS observability.
- Aggregation onto the analysis grid.
- The relative exposure calculation itself — this is the project's own analytical contribution and should live in code that can be read, reviewed, and rerun.
- Computation of the inside-versus-outside VSR summary statistics. **These are computed by fractional area intersection, not by classifying cells.** Each grid cell is intersected with the water mask, that water geometry is intersected with the VSR polygon, and the cell's exposure is split by the resulting area fractions. A boundary cell is never assigned whole to one side, by centroid or by majority area — doing so would make the headline statistic depend on grid origin and cell size. See [ADR 0004](decisions/0004-analysis-grid-resolution.md), which also records the assumption this introduces and the synthetic cases that must verify it.
- Validation checks over inputs and outputs.
- Emission of lineage metadata alongside each derived dataset.

Python is the preferred home for any step that must be reproducible or that will be run more than once.

The implemented grid boundary uses GeoParquet 1.1.0 with WKB and explicit
EPSG:3310 metadata as a **local deterministic processing format**. A sibling
JSON file records lineage and the Parquet checksum. This is not a publishing
decision: ArcGIS compatibility has not been verified, and the eventual hosted
representation remains constrained by the ArcGIS Online capability gate.
Execution timestamps record actual start-before-load and post-Parquet-write
completion, while the deterministic run ID is derived from input,
configuration, processing version, and output content rather than timestamps.
Generated grid output is refused beneath the project `data/raw/` tree.

### ArcGIS Online

- Hosting the derived layers as feature or tile services.
- Holding the web map that assembles them with agreed symbology.
- Serving those layers to the application over HTTPS.
- Sharing and access control for the published items.

ArcGIS Online is a publication and hosting target, not a processing tier. Analysis is not performed there for Version 1.

**Account capability is an unverified delivery gate.** This architecture assumes ArcGIS Online can host the project's eventual layers and serve them publicly. That assumption has not been checked against an actual account, and it is a hard delivery constraint rather than a detail: if the available account cannot publish or share what the analysis produces, the delivery path does not work. The following must all be verified before the hosting approach is considered proven:

- access to an ArcGIS Online organization, and which one;
- content-creation and publishing privileges on that account;
- permission to share items publicly, and whether the organization allows public sharing at all;
- availability of hosted imagery or tile publishing, not only hosted feature layers;
- credit availability, and which publishing operations consume credits;
- storage availability against the account's quota;
- whether the account supports the raster-delivery method the exposure layer ends up needing.

The last two points matter most for the whale-density input and the derived exposure result, which may be raster or tiled imagery rather than features. **The final layer representation and hosting approach therefore depend partly on verified account capabilities**, not only on the analytical resolution chosen. No layer format is selected here; the choice is made once both the resolution and the account capabilities are known. Verification is a deliverable of the application-foundation milestone in the [roadmap](roadmap.md).

### Next.js, TypeScript, and the ArcGIS Maps SDK for JavaScript

- Loading the published layers and rendering the map.
- Layer visibility, legends, and popups.
- Presenting precomputed summary statistics.
- Explaining what each layer means, including units, assumptions, and limitations.
- Client-side filtering and view state — cheap, presentational operations only.

The application is a presentation layer. It does not compute exposure, does not derive statistics, and does not transform data in ways that would change a reported number.

## Offline processing versus browser-side processing

| Concern | Offline (Pro / Python) | Browser (Next.js / SDK) |
|---|---|---|
| Raw source retrieval and cleaning | Yes | Never |
| Reprojection, clipping, gridding | Yes | Never |
| Exposure index computation | Yes | Never |
| Inside/outside VSR statistics | Yes | Never |
| Symbology decisions | Yes (authored) | Applied as published |
| Layer visibility, opacity, basemap | — | Yes |
| Attribute filtering of a displayed layer | — | Yes |
| Map extent, zoom, popups | — | Yes |

The rule behind the table: **if it changes a number a reader might quote, it happens offline.** If it only changes what is currently visible, it can happen in the browser.

## Proposed deployment model

- A static or statically-rendered Next.js build, deployed to a hosting platform that serves it over HTTPS from a stable public URL.
- No application server, no server-side rendering of analytical content, no server-side data processing.
- Layers served directly from ArcGIS Online to the browser.
- Deployments triggered from the repository's default branch.

Specific hosting platform: **to be decided.** The constraints that matter are HTTPS, a stable URL, static hosting of a Next.js build, and the ability to inject environment variables at build time.

This model has two halves, and only one of them is about the web host. The application half is straightforward. The layer half depends entirely on ArcGIS Online account capabilities — publishing privileges, public sharing, imagery or tile support, credits, and storage — as set out under [ArcGIS Online](#arcgis-online) above. The deployment path is not proven until both halves are verified: a deployed application that cannot load a publicly shared layer is not a deployment.

## Secrets and credentials

- No credential, API key, token, or ArcGIS Online password is ever committed. This includes example files, screenshots, notebooks, and test fixtures.
- Configuration reaches the application through environment variables, supplied locally by an ignored `.env.local` and in deployment by the hosting platform's environment settings.
- A committed `.env.example` lists required variable **names** with empty or placeholder values, and never real values.
- Any key that reaches the browser is public by definition. Any such key must be scoped and referrer-restricted to the deployed origin, and must never be a key with publishing or account-management rights.
- Publishing to ArcGIS Online is an authenticated, local, author-run operation. Those credentials stay on the author's machine and never enter the repository or the application build.
- If a credential is ever committed, it is treated as compromised: rotate it first, then clean up history.

## Large-data handling

- **Raw source data is never committed.** AIS extracts in particular can be very large. Raw data lives in a local, Git-ignored directory.
- Derived datasets are published to ArcGIS Online rather than committed, except where a derived output is genuinely small and benefits from being versioned — for example the summary-statistics file the application reads.
- Git LFS is **not** planned for Version 1. If a real need appears, it gets a decision record first.
- Every dataset the project depends on must be *retrievable*: the register in [data-sources.md](data-sources.md) records the source, retrieval method, and retrieval date so that an uncommitted file can be obtained again.
- The AIS extract is scoped to the study area and analytical period as early as the chosen route allows. **The route itself is an M3 decision**: NOAA's AccessAIS tool returns a spatial and temporal subset directly and is preferred, but it was not exercised during discovery, and the only confirmed route is the bulk daily national files. Bulk retrieval is therefore permitted under the guard in [data/README.md](../data/README.md) — one day at a time, filtered immediately, national copy discarded once a validated scoped output exists. **What is prohibited in every case is staging an entire national season locally.**
- Data volumes are now estimated rather than unknown: discovery puts the study-area extract at order 10⁸ records and ≈56 GB of transfer for the analytical period, as an order-of-magnitude planning figure scaled from a small sample. **The measured volume is not known and will not be until M3 retrieval runs.** If it turns out large enough to break this model, that finding gets recorded and the model gets revised.

**The tabular engine is now settled; the retrieval route is not.** DuckDB is the
production scan/filter/aggregation boundary per [ADR 0012](decisions/0012-use-duckdb-for-large-tabular-processing.md).
On the 22.7 MB M2 AIS prefix it produced the same grouped result as Polars with
a lower median elapsed time and peak RSS. That half-hour benchmark chooses one
foundation engine; it does not establish full-day or full-period performance.
At least one complete scoped day must be measured before resource behavior is
described as established.

## Testing boundaries

Testing effort follows consequence, not coverage.

- **Analytical code (Python)** — the highest-value target. Aggregation, normalization, the exposure calculation, and the inside/outside statistics should be tested with small synthetic inputs whose correct answers are known by construction. A geometry whose area is known, a grid whose totals are known, and — specifically — the fractional boundary cases set out in [ADR 0004](decisions/0004-analysis-grid-resolution.md), including the case of a cell 45% inside the zone that centroid and majority-area assignment both score as entirely outside.
- **Validation checks** — CRS correctness, extent coverage, null handling, and value ranges are asserted as part of processing rather than as a separate test suite.
- **Application code (TypeScript)** — type checking and linting, plus tests for any non-trivial presentational logic such as number formatting or classification. UI tests are not a Version 1 priority.
- **Not tested** — third-party libraries, the ArcGIS SDK, ArcGIS Online itself, and the correctness of upstream datasets. Upstream data is *inspected and documented*, not unit-tested.
- **Manual verification remains part of the process.** Some spatial errors are only visible on a map. Visual inspection of each derived layer is a required step, not a substitute for tests.

TypeScript tests run on Vitest — see [ADR 0010](decisions/0010-use-vitest-for-typescript-tests.md). Python tests run on pytest, with Ruff for formatting/linting and strict mypy for package source — see [ADR 0011](decisions/0011-use-uv-for-the-python-analysis-toolchain.md). Exact commands for both packages are in [development.md](development.md).

## Reproducibility and data lineage

Reproducibility is a Version 1 requirement, not a nice-to-have. It rests on three practices:

1. **Recorded provenance.** For each source: publisher, exact URL or tool used, retrieval date, any query parameters or extract bounds, and dataset version or vintage where one is published.
2. **An ordered processing path.** Each derived dataset records the steps that produced it, in order, with the parameters used. Steps performed in ArcGIS Pro are written down at parameter level. Code is not self-documenting for this purpose — source alone does not capture how it was run — so a coded step is reproducible only when all of the following exist: version-controlled code; configuration and parameters that are themselves versioned rather than passed ad hoc; a documented invocation or entrypoint; a pinned or recorded environment, including runtime and dependency versions; and run metadata tying that execution to the specific input datasets and output datasets it consumed and produced. The locked environment, versioned configuration with a deterministic digest, CLI boundary, and run-metadata structures now support a real one-extract AIS cleaning step. The complete retrieval-to-derived workflow is not implemented, and no workflow engine has been selected.
3. **Traceable outputs.** Each published layer and each reported statistic maps back to the derived dataset and processing step that produced it. Nothing is published whose origin cannot be stated.

The intended test of all this is simple: rerun the process from raw inputs and compare against the published layers. That check happens in M8 of the [roadmap](roadmap.md).

## Initial performance considerations

These are early concerns to keep in view, not measured problems:

- **ArcGIS SDK payload.** The Maps SDK is substantial. Import only what is used, and watch initial load time from the start rather than at release.
- **Feature count and geometry complexity.** Vessel-activity layers can carry very high feature counts. Aggregating to the analysis grid before publishing is both the analytical choice and the performance choice.
- **Raster versus vector delivery.** A continuous exposure surface may be better served as tiles than as features. The decision depends on the resolution chosen in discovery.
- **Classification cost.** Client-side renderer classification over large layers is slower than publishing a layer with symbology already defined.
- **Basemap and layer requests** on a mid-range connection: a reviewer opening the deployed app should see something meaningful quickly.

No performance budget has been set. One should be set once the real layers exist.

## Version 1 architectural constraints

For Version 1, the project deliberately does **not** introduce:

- a custom backend or API service,
- microservices,
- PostGIS or any self-hosted database,
- job queues or schedulers,
- containers or Kubernetes,
- AI or machine-learning features.

Each of these would add operational surface without serving the Version 1 question. Any of them may be introduced later if a concrete, demonstrated need appears — and if it does, it gets a decision record explaining the need before it gets an implementation.

## Current and planned repository structure

`web/` and `analysis/` now exist, created by their respective foundation work.
The analysis package has foundation modules, source validators, one-extract AIS
processing, the projected water-grid implementation, and tests. The other
processing responsibilities listed below remain intended boundaries rather than
a claim that all of them exist. `arcgis/` and `results/` remain proposed and are not
created before a milestone needs them.

```
socal-whale-vessel-risk/
├── docs/                  # documentation (exists)
│   └── decisions/         # architecture decision records (exists)
├── analysis/              # Python analysis package  (exists)
│   ├── src/               #   contracts, validators, AIS/grid processing, CLIs  (exists)
│   └── tests/             #   synthetic foundation/processing tests  (exists)
├── data/                  # local data root, Git-ignored  (exists)
│   ├── raw/               #   untouched source downloads
│   ├── interim/           #   intermediate processing outputs
│   └── derived/           #   validated outputs for publication
├── arcgis/                # ArcGIS Pro project and exported tools  [proposed]
├── web/                   # Next.js + TypeScript application  (exists)
│   ├── app/               #   routes and pages  (exists)
│   ├── components/        #   map and UI components  (exists)
│   ├── lib/               #   configuration and formatting helpers  (exists)
│   └── types/             #   ambient type declarations  (exists)
└── results/               # small committed outputs the app reads  [proposed]
```

Open questions about the uncreated portion: whether `results/` is distinct
enough from `data/derived/` to justify existing, and whether the ArcGIS Pro
project belongs in the repository at all given its file sizes. These are settled
at the milestone that needs them. The placement of both implemented packages in
root subdirectories is settled by their existing layouts.

## Explicitly deferred decisions

Deferred on purpose. Each should be resolved by evidence — real data, real measurements — and recorded as a decision record when it is.

| Decision | Deferred until | Why it is not decided now |
|---|---|---|
| Study area extent, projected CRS, and analysis grid resolution | **Partly resolved** | Projection settled in [ADR 0003](decisions/0003-projected-coordinate-system.md) and grid in [ADR 0004](decisions/0004-analysis-grid-resolution.md). Extent is **split and only half settled** in [ADR 0002](decisions/0002-southern-california-study-area-extent.md), which is Proposed: the map and context extent is fixed, the **analytical and statistical domain is not**, because AIS coverage offshore is unestablished. |
| ~~Analytical period for Version 1~~ | **Resolved by data discovery** | [ADR 0005](decisions/0005-analytical-period.md). The whale model turned out not to be a time series at all, and AIS is only published through 2024. |
| Exposure index formula, normalization, and weighting | After both inputs are inspected | Cannot be defined responsibly before the units and value distributions of the inputs are known. |
| High-exposure threshold definition | After the exposure surface exists | Should be chosen against the real value distribution and tested for sensitivity. |
| Raster versus vector representation for the exposure layer | After resolution is chosen and account capabilities are verified | Drives both publishing method and client performance, and is constrained by what the ArcGIS Online account can actually publish. |
| ~~Whether vessel speed is used in the index or reported separately~~ | **Resolved by data discovery** | [ADR 0006](decisions/0006-report-vessel-speed-separately.md). `SOG` is present, documented, and appears usable in the inspected sample — not established across the full period — and is reported separately rather than weighted into the index, because weighting it would require a lethality assumption the brief forbids. |
| Split of work between ArcGIS Pro and Python for each processing step | Processing workflow | Depends on which operations turn out to be awkward in code. |
| Hosting platform for the deployed application | Still open | The requirements a host must satisfy are now written down in [development.md](development.md), so the choice is constrained. The platform itself is still not chosen, and nothing is deployed. |
| ArcGIS Online account capability and publishing feasibility — organization access, publishing privileges, public sharing, hosted imagery and tile support, credits, storage | Application foundation, before the deployment path is treated as proven | Unverified against a real account. It gates what can be published at all, and therefore constrains the layer representation and the hosting approach. |
| ArcGIS Online sharing model and API-key scoping | Application foundation | Depends on the account and licensing available, and on the capability check above. |
| ~~Test framework and toolchain for Python~~ | **Resolved by the processing foundation** | uv, Ruff, mypy, pytest, and Hatchling are recorded in [ADR 0011](decisions/0011-use-uv-for-the-python-analysis-toolchain.md). The TypeScript half remains Vitest in [ADR 0010](decisions/0010-use-vitest-for-typescript-tests.md). |
| Layer schemas, field names, and any data or API contract | **Partly resolved.** M3 implements source, processing, grid, whale-input, AIS-input, VSR-source, lineage, and local projected-water-grid contracts under `analysis/`. The exposure-layer, statistics, and results-file contracts still wait on [ADR 0002](decisions/0002-southern-california-study-area-extent.md). | Contracts written against imagined data are wrong contracts — and contracts written against an undecided reporting domain are wrong for the same reason. |

The last row matters most, and its rule has moved on now that the data has been inspected: **a contract may be written when the data it describes has been inspected and settling the analytical domain could not change it.** The exposure formula and every reporting-domain-dependent contract still wait. The operative wording is in [../AGENTS.md](../AGENTS.md).
