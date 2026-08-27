# Development

**Owns:** the engineering workflow — how work is done, recorded, verified, and reviewed in this repository.

> The **web application and Python analysis package are implemented in part and
> their commands are real** — they are recorded below and were run to write them
> down. The repository also contains the [M2 verification
> utility](../tools/README.md), which is separate from the analysis package. The
> ArcGIS Pro is optional and unnecessary for Version 1; no ArcGIS Pro project
> is planned as a repository component. The analysis package validates source
> inputs and configuration, processes one explicitly supplied AIS extract into
> an atomic local bundle, and generates the projected per-cell water grid.
> QGIS is the local inspection and visual-verification tool. Retrieval and all
> other derived processing remain unfinished.

---

## Documentation sources of truth

Each kind of information has exactly one owning document. When information changes, update the owner. Other documents may link to it; they must not restate it in a way that can drift.

| Document | Owns |
|---|---|
| [../README.md](../README.md) | Public overview and current visible status |
| [project-brief.md](project-brief.md) | Authoritative product scope, Version 1 definition, non-goals, scientific communication rules |
| [roadmap.md](roadmap.md) | Milestones, sequencing, progress, version direction |
| [architecture.md](architecture.md) | System design, component boundaries, deferred design decisions |
| [data-sources.md](data-sources.md) | Dataset provenance, source register, discovery status |
| [../data/README.md](../data/README.md) | Local data-handling policy, including the AIS retrieval policy |
| [../tools/README.md](../tools/README.md) | Verification utilities and the versions they were run against |
| [development.md](development.md) | Engineering workflow — this document |
| [project-vision-and-learning-plan.md](project-vision-and-learning-plan.md) | Original project vision and GIS learning reference |
| [decisions/](decisions/README.md) | Historical architectural decisions and their rationale |
| [../AGENTS.md](../AGENTS.md) | Operational instructions for coding agents |
| [../CLAUDE.md](../CLAUDE.md) | Claude entrypoint pointing to canonical instructions |

If two documents contradict each other, the owner above wins and the other is corrected in the same change that discovers the contradiction.

## Local development

This section fills in as each part is built. The **web application shell and
Python analysis foundation exist**. QGIS has verified the exact generated
water-grid artifact; ArcGIS Pro is not a Version 1 prerequisite.

### Application (Next.js / TypeScript) — implemented

The application lives in [`../web/`](../web/). It is a presentation layer only:
no backend, no database, and no analysis. Run every command below from `web/`.

**Prerequisites**

| Tool | Required | Verified against |
|---|---|---|
| Node.js | `>=20.9.0` (enforced by `web/package.json` `engines`, and required by Next.js 16) | 22.16.0 |
| npm | Ships with Node.js | 10.9.2 |

npm is the package manager and `web/package-lock.json` is committed. Do not
install with pnpm, Yarn, or Bun — see [ADR 0007](decisions/0007-use-npm-for-the-web-application.md).

**Commands**

| Command | What it does |
|---|---|
| `npm install` | Installs dependencies from the committed lockfile. |
| `npm run dev` | Development server on <http://localhost:3000>. |
| `npm run lint` | ESLint, using `eslint-config-next` flat config. |
| `npm run typecheck` | `tsc --noEmit` over the whole project. |
| `npm test` | Vitest, run once. `npm run test:watch` for watch mode. |
| `npm run format` | Rewrites files with Prettier. |
| `npm run format:check` | Fails if anything is unformatted. |
| `npm run build` | Production build **and static export**. |

There is no `npm start`. `next start` serves a Node build, and this application
is exported as static files, so the script would only mislead.

**Static output**

`npm run build` writes a complete static site to `web/out/` — HTML, CSS, and
JavaScript with no server component. Serve that directory with any static file
server to check the real build locally; opening the files directly over
`file://` will not work, because the application fetches its own JavaScript
chunks over HTTP.

`web/out/` and `web/.next/` are Git-ignored and must never be committed.

The export is roughly 30 MB on disk, almost all of it ArcGIS Maps SDK chunks.
That is the on-disk size, not the download: the SDK is code-split and the
browser fetches only what the current map needs. Check any host's file-count and
size limits against this before choosing one.

**Environment variables**

| Name | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_ARCGIS_API_KEY` | Yes, for the map to render | Access token the browser sends to the ArcGIS basemap styles service. |
| `NEXT_PUBLIC_ARCGIS_BASEMAP` | No | Basemap style id. Defaults to `arcgis/oceans`. |

Names and their constraints are documented in
[`../web/.env.example`](../web/.env.example). Copy it to `web/.env.local` — which
is Git-ignored — and fill in values there.

`NEXT_PUBLIC_` variables are inlined into the JavaScript bundle **at build
time**. They are public, and they are baked into the deployed files, so changing
one requires a rebuild, not just a restart.

Without a key the application still loads and reports the problem in the
interface rather than failing silently: it names the unset variable and shows the
service's own response. That behaviour is verified. A **successful** basemap
render has **not** been verified — see [roadmap.md](roadmap.md) M4.

### Analysis (Python) — AIS extract and water-grid processing implemented

The src-based package lives in [`../analysis/`](../analysis/). It owns versioned
processing/source/lineage contracts, the selected DuckDB large-tabular boundary,
read-only AIS/whale/VSR validators, CLI boundaries, deterministic processing of
one supplied NOAA AIS flat CSV extract, the deterministic EPSG:3310 water-grid
process, and synthetic tests. It does **not** retrieve AIS, transfer whale
values, aggregate vessels, or produce an exposure dataset or statistics. Run
every command below from `analysis/`.

**Prerequisites**

| Tool | Required | Verified against |
|---|---|---|
| Python | `>=3.13,<3.14` (enforced by `analysis/pyproject.toml`) | 3.13.7 |
| uv | 0.12 or later, invoked as `python -m uv` | 0.12.6 |

uv is the environment and dependency manager; `analysis/uv.lock` is committed.
Do not infer dependencies from an existing `.venv`. Runtime requirements are
declared separately from development and benchmark groups. A default sync
includes both local-only groups so all checks and the evidence benchmark can be
re-run; the built package declares only runtime requirements.

**Setup and quality commands**

| Command | What it does |
|---|---|
| `python -m uv sync --locked` | Creates or updates the ignored environment from the committed lock without changing it. |
| `python -m uv lock --check` | Fails if `pyproject.toml` and `uv.lock` disagree. |
| `python -m uv run ruff format .` | Rewrites Python source and test files to the configured format. |
| `python -m uv run ruff format --check .` | Checks formatting without rewriting. |
| `python -m uv run ruff check .` | Runs Ruff linting. |
| `python -m uv run mypy src/whale_vessel_analysis` | Strictly type-checks package source. |
| `python -m uv run pytest` | Runs the self-contained synthetic test suite. |
| `python -m uv build` | Builds the source distribution and wheel. `analysis/dist/` is generated and must not be committed. |
| `python -m uv run python -m whale_vessel_analysis --help` | Proves the package module and command boundary load. |

The toolchain decision is [ADR 0011](decisions/0011-use-uv-for-the-python-analysis-toolchain.md).

**Read-only validation**

Input paths are always supplied at runtime. Omitting `--config` uses the
version-controlled packaged configuration.

```text
python -m uv run python -m whale_vessel_analysis validate-config
python -m uv run python -m whale_vessel_analysis validate-config --config <config.toml>
python -m uv run python -m whale_vessel_analysis validate-ais <ais.csv>
python -m uv run python -m whale_vessel_analysis validate-whale <model.gdb>
python -m uv run python -m whale_vessel_analysis validate-vsr <zone.geojson>
```

The commands print JSON and write no analytical output. Exit 0 means the
supplied artifact passed the implemented contract; exit 2 means a configuration,
schema, or value check failed. Raw AIS is expected to contain records that later
cleaning must reject, so a non-zero source inspection is recorded rather than
"fixed" in place.

**One-extract AIS processing**

The processing command requires both paths and never discovers a date,
directory, or season on its own:

```text
python -m uv run whale-vessel-analysis process-ais --input <one-ais.csv> --output-dir <new-output-directory>
python -m uv run whale-vessel-analysis process-ais --input <one-ais.csv> --output-dir <new-output-directory> --config <config.toml>
```

The output directory must not exist. To repeat the identical invocation into a
bundle previously created by this command:

```text
python -m uv run whale-vessel-analysis process-ais --input <one-ais.csv> --output-dir <existing-bundle> --overwrite
```

`--overwrite` refuses arbitrary directories and replaces only a complete bundle
whose metadata identifies the AIS processing contract. The command publishes
`cleaned.parquet`, `quality-report.json`, and `run-metadata.json` together by an
atomic directory rename. A failure before publication leaves no completed target
bundle. Outputs belong under the ignored `data/interim/` or `data/derived/`
roots, never `data/raw/`; the command enforces the repository raw-data boundary.
Header-only input, input with no valid timestamp, and input spanning multiple
UTC dates fail without publishing a target bundle. A partial-day extract is
allowed, but the quality report records its observed timestamp bounds and marks
date completeness `unverified`; a filename or timestamp range is not evidence
of complete retrieval.

The output and cleaning contract, including the disabled length and behavioral
thresholds, is in [`../analysis/README.md`](../analysis/README.md). The duplicate
policy is [ADR 0013](decisions/0013-remove-conflicting-ais-key-records.md).

The required local M2-sample smoke invocation is:

```text
python -m uv run whale-vessel-analysis process-ais --input C:\Users\teche\socal-whale-vessel-risk-data-discovery\data\interim\m2-inspection\AIS_2024_07_15.head_sample.csv --output-dir ..\data\interim\ais-ingestion-smoke
```

That path is specific to the author's worktrees. Use `--overwrite` only to
repeat it after the first successful bundle. On 2026-08-27 the command processed
the unchanged 22.7 MB M2 prefix extracted by the M2 utility from 15 July 2024: it
read 207,849 source rows, retained 13,800 in the map extent, selected 2,495
commercial rows before deduplication, and wrote 2,490 cleaned rows. This is
sample evidence from an approximately half-hour prefix, not a complete day or
analytical-period result. Its valid timestamps range from
`2024-07-15T00:00:00Z` to `2024-07-15T15:40:54Z` because the source prefix is
not strictly time ordered; this does not establish continuous coverage between
those bounds, and completeness remains `unverified`.

**Projected water-grid generation**

This derived command is deliberately separate from the primary CLI while the
AIS processing branch owns that shared surface:

```text
python -m uv run python -m whale_vessel_analysis.spatial_cli --input <mask-dataset> --layer <layer> --source-crs <crs> --output <water-grid.parquet> [--config <config.toml>] [--overwrite]
```

The command requires a polygon mask supplied at runtime and verifies the
declared source CRS against the dataset. It builds the 95 × 68 grid from the
versioned bounds, reprojects with longitude/latitude treated as x/y, and clips
the mask to the configured WGS84 map/context extent after densifying its edges
to at most 0.01° and projecting it to EPSG:3310. It then intersects each cell
with that clipped support, omits dry cells, and writes deterministic GeoParquet
plus a lineage JSON sidecar. It refuses to replace either file unless
`--overwrite` is supplied and refuses generated destinations beneath
`data/raw/`. The output directory may be created by the command; generated
files remain ignored and are never staged. The CLI captures UTC start before
configuration and mask loading; the writer records completion after the
Parquet write succeeds. Timestamps do not participate in content/run identity.

The exact read-only NOAA smoke invocation used on 2026-08-27 was:

```text
python -m uv run python -m whale_vessel_analysis.spatial_cli --input "C:\Users\teche\socal-whale-vessel-risk-data-discovery\data\raw\noaa-swfsc-becker-2020b\swfsc_cce_becker_et_al_2020b.gdb" --layer Blue_whale_summer_fall --source-crs EPSG:4326 --output "..\data\interim\m3-spatial-grid\noaa-whale-footprint-water-grid.parquet"
```

The input remains unchanged. The output and sidecar are under the ignored local
interim root. [ADR 0014](decisions/0014-select-the-grid-water-mask.md) explains
why the union of the selected whale-model polygons is the Version 1 grid mask
and why it must not be described as an authoritative shoreline or as AIS
observability. The output contract and smoke results are in
[`../analysis/README.md`](../analysis/README.md).

PyArrow read-back and GeoParquet metadata validation passed. ArcGIS publishing
compatibility is unverified. GDAL/Pyogrio read-back on the current machine
failed because its Parquet driver could not load `duckdb.dll`; this is recorded
as a local driver limitation, not silently treated as format verification.
Visual map inspection passed on 2026-08-27 in headless QGIS 4.2.1 with GDAL
3.13.2. QGIS opened the exact ignored
`data/interim/m3-spatial-grid/noaa-whale-footprint-water-grid.parquet` directly
through OGR as Parquet; no conversion was used. The inspected file's SHA-256
was `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`.
QGIS confirmed EPSG:3310, 4,516 MultiPolygon features, the expected extent and
area, zero null/empty/invalid geometry, negligible numerical outside-context
area, and south-to-north row and west-to-east column progression. Five
2200×1400 QGIS renders under the ignored
`data/interim/m3-spatial-grid/qgis-verification/` directory were inspected:
`full-context.png`, `northern-boundary.png`, `southern-boundary.png`,
`coast-and-islands.png`, and `grid-detail.png`. They showed the correct Southern
California location and axis order, alignment with the NOAA whale footprint,
visibly clipped boundary cells, plausible coastline and island gaps, correct
index orientation, and no unexplained gaps, spikes, slivers, displaced cells,
or projection artifacts. The renders, temporary QGIS project, and evidence
report remain ignored and are not project deliverables.

**Reviewing the exact derived output in QGIS**

1. Obtain or regenerate the local GeoParquet at the documented path. Do not
   convert or export it before review.
2. From `analysis/`, compute its SHA-256 before opening it. On this Windows
   environment:

   ```text
   Get-FileHash -Algorithm SHA256 -LiteralPath "..\data\interim\m3-spatial-grid\noaa-whale-footprint-water-grid.parquet"
   ```

3. In QGIS, use **Layer → Add Layer → Add Vector Layer** and select that exact
   `.parquet` file, or pass the same path to the recorded headless review
   procedure. Do not save a converted copy and inspect that instead.
4. Inspect the CRS, extent, location and axis order, row/column orientation,
   context-boundary clipping, NOAA-footprint alignment, coastline/island gaps,
   geometry artifacts, and any layer-specific checks. Record both failures and
   passes.
5. Tie the evidence to the pre-open checksum and record the date, QGIS
   tool/version, inspected views/checks, result, and relevant observations.

Generation-time lineage must not be manually edited. The existing sidecar
records `visual_inspection_status: not_completed` because it was written before
the QGIS check; that value remains truthful for that generation. Under the
current implementation, an explicitly authorized overwrite replaces both the
output and sidecar, and prior run evidence is not retained automatically. The
later QGIS report and the documentation above are separate evidence for output
SHA-256 `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`.
A formal reusable verification-record command and append-only or versioned
lineage are not implemented; the [roadmap](roadmap.md) carries that M3/M8
follow-up.

QGIS is not a production transformation boundary. If inspection or exploration
reveals a needed clip, repair, field calculation, reprojection, classification,
or other result-changing operation, implement it in Python with configuration,
tests, and lineage, then generate and inspect a new artifact. Do not carry an
unrecorded QGIS-edited file forward to publication.

**Large-tabular evidence benchmark**

The parameterized command supporting [ADR 0012](decisions/0012-use-duckdb-for-large-tabular-processing.md)
accepts a local AIS CSV and prints JSON to standard output:

```text
python -m uv run python -m whale_vessel_analysis.benchmark --input <ais-csv> --runs 5
```

It compares DuckDB and Polars in isolated processes and fails unless their
grouped results agree. Each measured operation includes the selected engine's
module import; its separate warm-up process only warms the operating-system
file cache. Polars and psutil are benchmark-only dependencies; DuckDB is the
sole production large-tabular engine.

### QGIS — inspection and visual verification

QGIS is used locally to inspect exact source and derived spatial artifacts,
explore methods or cartography, and perform the required visual-verification
step described above. It does not own deterministic processing, configuration,
tests, lineage, or production transformations; Python owns those boundaries.

ArcGIS Pro is optional and unnecessary for Version 1. There is no planned
ArcGIS Pro directory or project to implement.

## Environment variables and secrets

- Never commit a credential, API key, token, connection string, or account password. This includes example files, notebooks, screenshots, and test fixtures.
- Local configuration lives in an ignored `.env.local`. A committed `.env.example` lists required variable **names** with empty or placeholder values only.
- Deployment configuration is set in the hosting platform, not in the repository.
- Any key shipped to the browser is public. It must be scoped and origin-restricted, and must never carry publishing or account-management rights.
- The browser key provides access to intended ArcGIS platform/basemap services
  and explicitly authorized items. It never proves publishing capability.
- If an Esri-hosted publication route is selected, authenticated publication
  credentials stay on the author's machine. Publishing is a local,
  author-run action and is never automated from the repository in Version 1.
- A committed secret is treated as compromised. Rotate it first; clean history second. Do not reverse that order.
- Before every commit, check the diff for values that look like credentials. This is a habit, not a tool.

## Deploying the application

**Status: not deployed.** Nothing has been published to any host. The
requirements below are what a host must satisfy; the platform itself is still an
open decision in [architecture.md](architecture.md).

**Requirements**

- Serves static files over **HTTPS** from a **stable public URL** — the ArcGIS
  API key is restricted by referrer, so the origin has to stop changing.
- Build command `npm install && npm run build` with the project root at `web/`,
  publishing the `out/` directory. Or build locally and upload `out/`.
- Node.js `>=20.9.0` available in the build environment.
- Build-time environment variables, because `NEXT_PUBLIC_` values are inlined
  during the build and cannot be injected afterwards.
- Tolerates roughly 30 MB and several hundred files of build output.
- Serves `out/<route>/index.html` for directory URLs. The build sets
  `trailingSlash: true` so this works on hosts that do not rewrite
  extensionless paths.

**Before calling a deployment done**

A deployment is not proven by a successful build. Open the public URL in a
browser with no existing session — a private window, or a different device —
and confirm the map renders and the console is clean. Until that has been done,
the deployment is unverified and must be described that way.

## ArcGIS account-type capability checks and service access

There are three publication candidates: ArcGIS Location Platform limited data
services, ArcGIS Online organization-hosted layers, and a non-Esri public route
if neither Esri option fits. The browser API-key check is related but separate:
it proves access to the basemap, location services, and explicitly authorized
items; it does not by itself prove that either account can host the project
layers.

Esri documents Location Platform as a limited single-user organization that can
create feature, vector-tile, and map-tile services. Storage and bandwidth use a
monthly free tier with optional pay-as-you-go billing. ArcGIS Online has a
different organization, privilege, credit, and storage model. See Esri's
[portal and data services FAQ](https://developers.arcgis.com/documentation/portal-and-data-services/faq/)
and [API-key authentication documentation](https://developers.arcgis.com/documentation/security-and-authentication/api-key-authentication/).

Everything involving an account is an **authenticated, author-run action**. An
agent does not sign in, publish, change sharing, alter organization settings,
enable billing, add a payment method, or spend money. A test is not attempted
if it could exceed an already available free tier or consume paid capacity.

Record capability outcomes under M4 in [roadmap.md](roadmap.md) without
committing account identifiers, credentials, billing details, or item ids.
Carry unavailable or unsuitable capabilities into M5 as evidence for the
publication-format and route decision.

### 1. Identify the account type

Sign in privately at <https://www.arcgis.com/> or the ArcGIS Location Platform
dashboard at <https://location.arcgis.com/> and determine which branch applies:

- **ArcGIS Location Platform:** a limited single-user organization. API-key
  management privileges are available by default, but actual data-service,
  public-access, usage, and billing status still require checking.
- **ArcGIS Online:** an organization account whose user type, role, and custom
  privileges determine available capabilities.

Do not commit the organization URL, account name, user name, subscription id,
or another account identifier.

### 2A. Check ArcGIS Location Platform data services

For a Location Platform account, record only the capability outcomes:

- whether hosted feature, vector-tile, and map-tile service creation is
  available to the account;
- whether the intended service can be shared for anonymous public access;
- current storage and bandwidth usage, the applicable monthly free-tier limits,
  and enough remaining headroom for a minimal test and the likely project
  representation; and
- whether pay-as-you-go billing is disabled or already enabled.

Do **not** enable pay-as-you-go, add or change payment information, or publish a
test that could incur a charge. If the account is already pay-as-you-go, that is
a constraint to record, not authorization to spend. Location Platform does not
offer hosted imagery or scene services under the documented limited data-service
support; if the eventual output needs one, this route is unsuitable unless the
representation changes on measured evidence.

### 2B. Check ArcGIS Online organization capabilities

For an ArcGIS Online account, inspect the user type, role, and organization
policy, then record whether these capabilities are available:

- create, update, and delete content;
- publish hosted feature, tile, and imagery layers;
- share with everyone, including any organization-level policy restriction;
- sufficient credits and any per-member budget; and
- sufficient storage.

Do not change the role, privileges, organization policy, credit budget, or
subscription. If public sharing or a required service type is unavailable,
record ArcGIS Online hosting as constrained and continue evaluating the other
publication candidates.

### 3. Conditionally test an Esri-hosted feature service

Attempt a minimal hosted-feature-service test only when the applicable branch
has already verified public sharing and enough no-cost capacity. Use throwaway
data — **not** project data and nothing derived from a source whose
redistribution terms remain unverified.

1. Create a CSV with a handful of arbitrary Southern California Bight points.
2. Publish it as a hosted feature service through the applicable Location
   Platform or ArcGIS Online portal workflow.
3. Mark it clearly as a disposable, dated capability test.
4. Share it with everyone.
5. Record whether publication and public sharing succeeded, which account-type
   branch was tested, and whether storage, bandwidth, or credits changed. Keep
   the item id privately only until cleanup; do not commit it.

If a prerequisite is missing, the portal refuses a step, or the operation could
incur a charge, stop. Record the outcome and do not work around account or
billing policy.

### 4. Verify anonymous access

When a test service exists, copy its service URL and request its JSON metadata
from a private browser session with no ArcGIS sign-in. Confirm the response is
available without an interactive token, then load the service in the
application. If no safe test was possible, record this check as not attempted
and why.

### 5. Configure and verify the browser API key

ArcGIS Location Platform accounts have API-key management privileges by
default. ArcGIS Online API-key availability depends on user type and privileges;
the account check records the actual outcome.

1. Create API key credentials in the applicable developer-credentials area.
2. Scope the key to the minimum needed: basemap styles and intended location
   services, plus read access to a project/test item only when required. It has
   no publishing, content-management, organization, billing, or
   account-management rights.
3. Restrict referrer URLs to `http://localhost:3000` and the deployed origin.
4. Put the key in ignored `web/.env.local` as
   `NEXT_PUBLIC_ARCGIS_API_KEY`; never put a value in `.env.example`, a commit,
   or a screenshot.
5. Set the same variable in the host's build environment without exposing it in
   repository or deployment logs.

Record expiry and rotation details outside the repository. Successful basemap
rendering with the key is a distinct M4 check and does not prove project-layer
hosting.

### 6. Deploy and verify

Follow "Deploying the application" above, then verify from a clean browser
session as described there.

### 7. Clean up a test service, if created

Delete the hosted feature service and its source item. Remove item access from
the API key if it was granted, and record the deletion without committing the
item id. Leaving a test item consumes storage and may consume bandwidth or
credits.

## Raw data

- **Raw source data is never committed.** It lives under the Git-ignored local data root described in [../data/README.md](../data/README.md).
- Extract only what the study area and analytical period need. **Retrieval rules for large sources live in [../data/README.md](../data/README.md)**, which owns the local data-handling policy — including the AIS retrieval policy and the standing prohibition on staging an entire national season locally. Do not restate those rules here; they have already drifted once.
- Every raw dataset must be *re-obtainable*: its source, retrieval method, parameters, and retrieval date are recorded in [data-sources.md](data-sources.md) at the time of retrieval, not from memory later.
- Do not modify files in the raw directory. Cleaning produces new files elsewhere; the raw copy stays as downloaded so processing can be rerun from a known starting point.
- Git LFS is not in use. If large binaries ever seem necessary, that needs a decision record before anything is added.

## Generated outputs

- Derived datasets are generated by the processing path, not hand-edited. If a derived file needs changing, change the process that produces it.
- Validated derived datasets cross the provider-neutral publication boundary to
  the evidence-selected public delivery route. ArcGIS Location Platform limited
  data services and ArcGIS Online organization-hosted layers are separate Esri
  candidates; a non-Esri public representation must be selected and verified if
  neither is suitable. No route is selected or implemented yet.
- Small results the application reads — such as a future summary-statistics
  file — may be committed once their contract is allowed, so the application
  and its numbers stay versioned together.
- A committed generated file must record what produced it and when.
- Build output, caches, virtual environments, QGIS/ArcGIS scratch data, and
  editor state are ignored, never committed.
- Deleting everything under the derived directory and rerunning the process must be a safe operation. If it is not, something important is only stored in a generated file, which is a bug in the process.

## Testing and verification

Effort follows consequence. Detail on where testing does and does not apply is
in [architecture.md](architecture.md#testing-and-visual-verification-boundaries).

In practice:

- Analytical logic — aggregation, normalization, the exposure calculation, inside/outside statistics — gets tests with small synthetic inputs whose correct answers are known by construction.
- Input validation — coordinate reference system, extent, nulls, value ranges — is asserted inside the processing path so a bad input fails loudly rather than producing a plausible-looking wrong map.
- Application code gets type checking and linting, plus tests for non-trivial presentational logic.
- **Visual inspection is mandatory** for every derived spatial layer. Some errors — a wrong projection, an off-by-one grid, a flipped sign — are only visible on a map. Passing tests do not substitute for looking at the result.
- Visual inspection evidence is recorded separately from generation-time
  lineage and tied to the exact output SHA-256. The generated sidecar is not
  manually edited; an explicitly authorized overwrite currently replaces it
  and does not retain prior run evidence. Until a reusable record or command
  exists, documentation must explicitly record the checksum, date, GIS
  tool/version, inspected views/checks, result, and relevant observations.
- Any statistic that appears in the application must be traceable to a processing step, and the displayed value must match the documented one.

**Application (TypeScript).** `npm test` in `web/` runs Vitest once; `npm run test:watch` watches. The suite covers the configuration logic in `web/lib/` — how environment values resolve, and how the map component's reported load failures become text for the interface. Rendering, the ArcGIS SDK, and ArcGIS Online are not unit-tested; the map is verified by building it and looking at it in a browser. Vitest was chosen in [ADR 0010](decisions/0010-use-vitest-for-typescript-tests.md).

**Analysis (Python).** `python -m uv run pytest` in `analysis/` runs 87 tests
over project logic with values known by construction: accepted and rejected
spatial configuration, the exact AIS header and documented sentinels, invalid
source values, whale schema and abundance consistency, VSR source schema,
deterministic lineage/configuration hashing, configurable source locators, the
exact grid and water-area invariants, configured-extent clipping, deterministic
spatial serialization and content identity, truthful execution timestamps,
raw-output refusal, atomic-write failure behavior, and both CLI boundaries.
Tests create temporary CSVs and geometry or use data in memory; the ignored M2
artifacts are not test prerequisites. Third-party libraries are not themselves
unit-tested.

## Formatting and linting

**Application (TypeScript).** Prettier formats, ESLint lints, and `tsc` type-checks. Configuration is in `web/.prettierrc.json` and `web/eslint.config.mjs`; commands are in the table above. Run `npm run lint`, `npm run typecheck`, and `npm run format:check` before proposing a branch.

**Analysis (Python).** Ruff formats and lints, and mypy type-checks package source
in strict mode. Configuration is in `analysis/pyproject.toml`; exact commands
are in the analysis table above. The untyped third-party geospatial boundaries
are isolated behind explicit mypy overrides and typed project contracts rather
than weakening strict checking for project modules.

The expectations that hold for both:

- Formatting is automated and not argued about in review.
- Linting and type checking run locally before a branch is proposed for review.
- Markdown in this repository stays plain and portable: relative links between repository documents, no HTML unless genuinely needed, UTF-8 punctuation preserved.

## Keeping documentation synchronized with implementation

Documentation drift is the most likely failure mode of this project, because the documentation currently describes work that does not exist.

The rules:

1. **Same branch, same change.** A change to architecture, behavior, data handling, or scope updates the owning document in the same branch as the code. Not afterwards.
2. **Status language is load-bearing.** Documents distinguish what exists from what is planned. When something becomes real, the status changes with it — including the roadmap milestone status.
3. **Discovery updates the register.** When a dataset property is verified, replace the "to be verified" entry in [data-sources.md](data-sources.md) with the finding. Do not leave a verified fact marked unverified, and do not quietly upgrade an assumption to a fact.
4. **Decisions get records.** A choice that constrains later work gets an entry under [decisions/](decisions/README.md) — particularly anything listed as a deferred decision in [architecture.md](architecture.md).
5. **Scope changes go to the brief first.** If Version 1 scope is reduced or expanded, [project-brief.md](project-brief.md) changes first and everything else follows from it.
6. **Reductions are recorded, not dropped.** If a scope item is narrowed because the data cannot support it, say so and say why. Silence reads as failure to notice.

## Concurrent sessions

Multiple coding sessions — human or agent — may run at once. They must not share a working tree.

- **One branch per session.** Never two sessions on the same branch, and never work directly on `main`.
- **Prefer a separate Git worktree per session.** Two sessions in one working directory will overwrite each other's files, stage each other's changes, and produce commits neither intended. A worktree gives each session its own checkout against the same repository:

  ```
  git worktree add ../socal-whale-vessel-risk-<topic> -b <branch-name>
  ```

  Remove it when the branch is finished:

  ```
  git worktree remove ../socal-whale-vessel-risk-<topic>
  ```

- **Split work along ownership lines.** Concurrent sessions should touch different areas — for example analysis versus application. Two sessions editing the same document will conflict, and documentation conflicts are harder to resolve correctly than code conflicts because both sides usually look fine.
- **Preserve unrelated changes.** If a session finds uncommitted changes it did not make, it stops and reports them. It does not stage, commit, stash, revert, or "clean up" work belonging to someone else.
- **Rebase and history rewriting are not shared operations.** Do not rewrite history on a branch another session may be using.
- **Publishing to an Esri-hosted item is not concurrent-safe.** Two sessions
  publishing to the same Location Platform or ArcGIS Online item can overwrite
  each other. Only one session performs publishing at a time.

## Recording incomplete or uncertain work

Work in this project will frequently be partial or provisional. That is fine as long as it is visible.

- **State what is unfinished, in the document that owns it.** A half-built capability is described as half-built, not as finished.
- **Mark unverified facts as unverified.** `To be verified` in the source register, and an explicit statement of the assumption anywhere a provisional value is used.
- **A blocked milestone is marked blocked** in the roadmap, with what it is blocked on.
- **Provisional analytical choices carry their rationale** — a threshold picked because something had to be picked is labeled as such, along with what would replace it.
- **Do not leave uncertainty only in a commit message.** Commit messages are not read by the next person; documents are.
- Use `TODO` sparingly and only for small, local, near-term items. Anything that affects scope, method, or architecture belongs in the owning document or in a decision record, not in a code comment.

## Commits

Applies to all future implementation work as well as documentation work.

- **One coherent change per commit.** A commit should be describable in one line without "and".
- **Stage deliberately.** Stage the specific files belonging to the commit. Avoid blanket staging when unrelated changes are present in the working tree.
- **Review the diff before committing.** Read what is actually staged, including for accidentally included credentials, large files, or generated output.
- **Message format:** `<type>: <imperative summary>`, using `docs`, `feat`, `fix`, `chore`, `refactor`, or `test`. Body when the reasoning is not obvious from the diff — explain why, not what.
- **No large files or secrets**, ever, in any commit.
- **Scientific language rules apply to commit messages too.** Do not describe a proxy as a measurement or an overlap as a risk.
- **Do not rewrite existing commits** — no amend, squash, rebase, or force-update of work that already exists — unless explicitly asked to.
- **Do not push or merge without explicit authorization.** Branches stay local until the author says otherwise.

## Review before merge

Before a branch is merged:

1. The working tree is clean and every intended change is committed.
2. The branch does one thing, and its commits are individually coherent.
3. Documentation owned by the changed area has been updated in the same branch.
4. Any capability described as implemented actually is, and anything implemented is described.
5. No credentials, raw data, or generated output that should be ignored has been committed.
6. Analytical changes have been visually inspected as well as tested.
7. Every statement about the data is supported by something in the source register.
8. No wording violates the scientific communication rules in [project-brief.md](project-brief.md).
9. Every relative documentation link resolves.
10. Decisions that constrain future work have decision records.

Merging is the author's call. An agent does not merge, and does not push, unless explicitly told to.
