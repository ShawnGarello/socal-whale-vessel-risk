# Development

**Owns:** the engineering workflow — how work is done, recorded, verified, and reviewed in this repository.

> The **web application shell and Python analysis package exist, and their commands are real** — they are recorded below and were run to write them down. The repository also contains the [M2 verification utility](../tools/README.md), which is separate from the analysis package. The ArcGIS Pro project is **not** built. The analysis package validates source inputs and configuration and processes one explicitly supplied AIS CSV into an atomic local bundle. It does not retrieve AIS, aggregate vessel activity, or produce an exposure result.

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
Python analysis foundation exist**; the ArcGIS Pro project does not.

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

### Analysis (Python) — foundation and AIS extract processing implemented

The src-based package lives in [`../analysis/`](../analysis/). It owns versioned
processing/source/lineage contracts, the selected DuckDB large-tabular boundary,
read-only AIS/whale/VSR validators, a CLI, synthetic tests, and deterministic
processing of one supplied NOAA AIS flat CSV extract. It does **not** retrieve AIS,
reproject or grid spatial inputs, aggregate vessel activity, or produce a
relative-exposure result. Run every command below from `analysis/`.

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

### ArcGIS Pro — not built

Pending implementation. A documented project location and the version used,
since Pro projects are version-sensitive.

Whoever creates each of these updates this section in the same branch.

## Environment variables and secrets

- Never commit a credential, API key, token, connection string, or account password. This includes example files, notebooks, screenshots, and test fixtures.
- Local configuration lives in an ignored `.env.local`. A committed `.env.example` lists required variable **names** with empty or placeholder values only.
- Deployment configuration is set in the hosting platform, not in the repository.
- Any key shipped to the browser is public. It must be scoped and origin-restricted, and must never carry publishing or account-management rights.
- ArcGIS Online publishing credentials stay on the author's machine. Publishing is a local, authenticated operation and is never automated from the repository in Version 1.
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

## ArcGIS Online capability check and publishing

Everything in this section is an **authenticated, author-run action**. An agent
does not perform any of it: it does not sign in, publish items, change sharing,
alter organization settings, or spend credits. The steps are written so the
author can run them and record the findings.

Run them in order. Record each answer in [roadmap.md](roadmap.md) under M4, and
record anything that turns out to be unavailable as a constraint carried into
the core-input-layers milestone.

### 1. Identify the account and organization

1. Sign in at <https://www.arcgis.com/> (or the ArcGIS Location Platform
   dashboard at <https://location.arcgis.com/>).
2. Open the account menu → **My settings**, and record:
   - the **organization name and URL** (`https://<org>.maps.arcgis.com`), or that
     the account is a Location Platform account with no organization;
   - the **user type** (for example Creator, Professional, Viewer);
   - the **role** (Administrator, Publisher, User, or custom).

The user type and role together determine what can be published. A Viewer user
type cannot create content at all. Location Platform accounts can issue API keys
and use basemaps but are not the same as an ArcGIS Online organization; if that
is what exists, hosted-layer publishing needs checking specifically rather than
assumed.

### 2. Confirm privileges

In **Organization → Members**, open the account, or check **My settings →
Licenses**. Record whether each of these is present:

- **Create, update, and delete content** — required to publish anything.
- **Publish hosted feature layers** — required for vector layers.
- **Publish hosted tile layers** — required for pre-rendered raster or tiled
  delivery.
- **Publish hosted imagery layers** — required if the exposure surface is
  delivered as imagery rather than features or tiles. This is the one most
  likely to be missing, and it constrains how the derived layer can be
  represented.
- **Share with everyone (public)** — required for anonymous visitors.

Also check **Organization → Settings → Sharing** for an organization-level
policy that blocks public sharing regardless of individual privilege. If public
sharing is blocked, the delivery path in
[architecture.md](architecture.md) does not hold and needs a decision record.

### 3. Record credits and storage

- **Organization → Credits** (or the Location Platform dashboard usage page):
  record remaining credits and any per-member budget.
- **Organization → Status → Content** or the storage summary: record storage
  used against quota.

Publishing, storing, and tile generation consume credits. Record the current
figures before publishing anything so later consumption can be attributed.

### 4. Publish a minimally scoped public test item

The point is to prove the publish-and-serve path end to end while risking
nothing. Use throwaway data — **not** project data, and nothing derived from a
dataset whose redistribution terms are still unverified.

1. Create a CSV with a handful of arbitrary points inside the Southern
   California Bight, for example three rows of `name,latitude,longitude`.
2. **Content → New item → Your device**, upload the CSV, and choose to publish
   it as a **hosted feature layer**.
3. Name it so it is obviously disposable and dated, for example
   `m4-publish-path-test-<yyyy-mm-dd>`. Add a description saying it is a
   temporary capability test to be deleted.
4. Open the item → **Share** → **Everyone (public)**.
5. Record: whether publishing succeeded, whether public sharing was permitted,
   the item id, and the credits consumed.

If any step is refused, record exactly which one and the message shown. That
refusal is the finding — it is more valuable than a success.

### 5. Verify anonymous access

Do not skip this. An item can appear shared and still not be reachable.

1. Copy the layer's **service URL** from the item page.
2. Open a **private/incognito window** with no ArcGIS session and request
   `<service URL>/0?f=pjson`.
3. Confirm JSON comes back rather than a token or sign-in response.
4. Then load the item in the application to close the loop end to end.

### 6. Configure the API key

1. In the developer credentials area, create **API key credentials**.
2. Scope the key to the minimum needed: basemap styles, plus read access to the
   public test item. **No publishing, content-management, or
   account-management privilege** — those belong to the author's interactive
   sign-in, never to a key shipped to a browser.
3. Set **referrer URLs** to `http://localhost:3000` and the deployed origin.
   A browser-delivered key is public by definition; referrer restriction is what
   limits its use.
4. Put the key in `web/.env.local` as `NEXT_PUBLIC_ARCGIS_API_KEY`. Never in
   `.env.example`, never in a commit, never in a screenshot.
5. Set the same variable in the hosting platform's build environment.

Record the key's expiry. API keys are valid for up to a year, and an expired key
takes the deployed map down.

### 7. Deploy and verify

Follow "Deploying the application" above, then verify from a clean browser
session as described there.

### 8. Clean up the test item

Once the path is proven and recorded:

1. Delete the hosted feature layer and its source CSV item.
2. If the API key was scoped to that item, remove that scope.
3. Record the deletion, so a later reader does not go looking for an item that
   was removed on purpose.

Leaving a stray public item costs storage and creates something publicly shared
that nothing documents.

## Raw data

- **Raw source data is never committed.** It lives under the Git-ignored local data root described in [../data/README.md](../data/README.md).
- Extract only what the study area and analytical period need. **Retrieval rules for large sources live in [../data/README.md](../data/README.md)**, which owns the local data-handling policy — including the AIS retrieval policy and the standing prohibition on staging an entire national season locally. Do not restate those rules here; they have already drifted once.
- Every raw dataset must be *re-obtainable*: its source, retrieval method, parameters, and retrieval date are recorded in [data-sources.md](data-sources.md) at the time of retrieval, not from memory later.
- Do not modify files in the raw directory. Cleaning produces new files elsewhere; the raw copy stays as downloaded so processing can be rerun from a known starting point.
- Git LFS is not in use. If large binaries ever seem necessary, that needs a decision record before anything is added.

## Generated outputs

- Derived datasets are generated by the processing path, not hand-edited. If a derived file needs changing, change the process that produces it.
- Derived datasets are published to ArcGIS Online rather than committed, with one exception: small results the application reads — such as the summary-statistics file — may be committed so the application and its numbers stay versioned together.
- A committed generated file must record what produced it and when.
- Build output, caches, virtual environments, ArcGIS Pro scratch data, and editor state are ignored, never committed.
- Deleting everything under the derived directory and rerunning the process must be a safe operation. If it is not, something important is only stored in a generated file, which is a bug in the process.

## Testing and verification

Effort follows consequence. Detail on where testing does and does not apply is in [architecture.md](architecture.md#testing-boundaries).

In practice:

- Analytical logic — aggregation, normalization, the exposure calculation, inside/outside statistics — gets tests with small synthetic inputs whose correct answers are known by construction.
- Input validation — coordinate reference system, extent, nulls, value ranges — is asserted inside the processing path so a bad input fails loudly rather than producing a plausible-looking wrong map.
- Application code gets type checking and linting, plus tests for non-trivial presentational logic.
- **Visual inspection is mandatory** for every derived spatial layer. Some errors — a wrong projection, an off-by-one grid, a flipped sign — are only visible on a map. Passing tests do not substitute for looking at the result.
- Any statistic that appears in the application must be traceable to a processing step, and the displayed value must match the documented one.

**Application (TypeScript).** `npm test` in `web/` runs Vitest once; `npm run test:watch` watches. The suite covers the configuration logic in `web/lib/` — how environment values resolve, and how the map component's reported load failures become text for the interface. Rendering, the ArcGIS SDK, and ArcGIS Online are not unit-tested; the map is verified by building it and looking at it in a browser. Vitest was chosen in [ADR 0010](decisions/0010-use-vitest-for-typescript-tests.md).

**Analysis (Python).** `python -m uv run pytest` in `analysis/` runs tests over
project logic with values known by construction: accepted and rejected spatial
configuration, the exact AIS header and documented sentinels, invalid source
values, whale schema and abundance consistency, VSR source schema, deterministic
lineage/configuration hashing, configurable source locators, and the CLI help
boundary. Tests create temporary CSVs or data in memory; the ignored M2
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
- **Publishing to ArcGIS Online is not concurrent-safe.** Two sessions publishing layers to the same items will overwrite each other. Only one session performs publishing at a time.

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
