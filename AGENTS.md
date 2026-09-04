# Agent Guidance

Repository-wide instructions for coding agents working in `socal-whale-vessel-risk`.

This file is operational. It does not restate the project documents — it tells you which one to read and what rules apply regardless of the task.

## Read before working

In order, and before making any change:

1. [docs/project-brief.md](docs/project-brief.md) — what Version 1 is, what it is not, and how results must be described.
2. [docs/roadmap.md](docs/roadmap.md) — where the work sits in the sequence and what is actually done.
3. [docs/development.md](docs/development.md) — the working process.

Then read whichever of these your task touches:

- [docs/architecture.md](docs/architecture.md) — system design, component boundaries, deferred decisions.
- [docs/data-sources.md](docs/data-sources.md) — dataset provenance and verification status.
- [docs/decisions/](docs/decisions/README.md) — why past choices were made.
- [docs/project-vision-and-learning-plan.md](docs/project-vision-and-learning-plan.md) — original vision; background only, not current scope.

## Document ownership

Update the owner, not a copy. If two documents disagree, the owner is right and the other gets fixed in the same change.

| Information | Owner |
|---|---|
| Public overview and visible status | [README.md](README.md) |
| Product scope, Version 1 definition, non-goals | [docs/project-brief.md](docs/project-brief.md) |
| Milestones, progress, version direction | [docs/roadmap.md](docs/roadmap.md) |
| System design and boundaries | [docs/architecture.md](docs/architecture.md) |
| Dataset provenance and discovery status | [docs/data-sources.md](docs/data-sources.md) |
| Local data-handling and retrieval policy | [data/README.md](data/README.md) |
| Engineering workflow | [docs/development.md](docs/development.md) |
| Historical decisions | [docs/decisions/](docs/decisions/README.md) |
| Agent instructions | this file |

## Current state

The repository now contains two implemented foundations in addition to the documentation and [M2 verification utility](tools/README.md):

- [web/](web/README.md) is the M4 Next.js/TypeScript application shell with one implemented M5 input-layer slice. Local API-key-backed oceans-basemap rendering, pan/zoom, attribution handoff, and the required responsive viewports are verified. The browser now loads the publisher-hosted 2026 California VSR boundary with `FID = 126`; its visibility control, legend, attribution/use disclosure, single-feature check, duplicate-layer guard, and isolated failure behavior are implemented and locally verified at the same three viewports. No VSR geometry is stored by the application. Current official documentation confirms Location Platform's limited feature/vector-tile/map-tile support, anonymous public sharing, and published free tiers, but the author's actual account controls, billing state, usage, and headroom remain unverified. M4 remains **In progress** because deployment, the authenticated account check, and the conditional Esri-hosted publish-and-serve check are unfinished. M5 is **In progress** because project-derived whale and vessel layers and their public delivery route remain unfinished.
- [analysis/](analysis/README.md) is the M3 Python processing package. It has a committed uv environment, DuckDB as the selected large-tabular engine, versioned spatial/source/lineage contracts, read-only input validators, a local one-artifact AIS retrieval-manifest boundary, and a bounded local Version 2 intake that partitions one author-supplied multi-date AccessAIS CSV or safe ZIP into canonical daily cleaner inputs. Parsed rows are sorted by all 17 fields under an explicit memory limit and isolated spill directory, duplicate multiplicity is preserved, and cleaner reuse is independent of source delivery order while whole-delivery byte provenance remains distinct. Version 1 intake manifests remain read-only valid. The package also has resumable sequential cleaner-to-period-manifest orchestration, CLI boundaries, deterministic one-extract AIS cleaning, deterministic construction of the EPSG:3310 grid and per-cell water geometry from an explicit mask, deterministic area-weighted whale-grid transfer, and a parameterized candidate vessel-grid aggregation boundary that is implemented and synthetically tested. The intake/orchestration path has passed real one-day, overlapping two-day, seven-day, July 1--31, August 1--31, September 1--30, and October 1--31 operational gates; the July run reconciled 17,998,955 rows, the August run 18,284,354 rows, the September run 15,638,516 rows, and the October run 16,355,292 rows, each across exactly its own requested dates, and each with an identical retry that reused every date without regeneration. The shared period manifest now holds 123 compatible dates and 12,637,341 cleaned commercial observations, with exactly the 30 November dates missing and no conflicts. ADR 0017 accepts AccessAIS as the preferred route and authorizes sequential author-submitted August--November monthly extracts under the existing controls, without claiming that the remaining months or the full period are already safe. The candidate boundary has also been exercised across the documented 300/1,800-second by 30/50-knot matrix on the real 15--16 July input; distinct-output repeats reproduced the deterministic GeoParquet and quality-report bytes, and corrected QGIS 4.2.1 views visibly placed the accepted-domain and VSR outlines above all four candidate grids. Independent transfer completeness, observational completeness, accepted vessel rules, November/full-period scaling, final period-wide vessel aggregation, and a production vessel-activity input remain unverified or unfinished. The water grid and whale-grid transfer are tested and reproducible; two clean whale-transfer runs produced byte-identical output, and both exact derived artifacts were visually verified in QGIS 4.2.1 on 2026-08-27. M3 remains **In progress** because analytical-period AIS retrieval, a final vessel-activity input, speed summaries, exposure analysis, and later derived outputs are unfinished. Publication and deployment also remain unfinished.

M2 is **Complete**. [ADR 0019](docs/decisions/0019-reference-the-publisher-hosted-vsr-service.md)
resolves its final publication-posture criterion through a conservative no-copy
route, not through a redistribution-permission claim. Python analysis retains
the exact immutable ignored local VSR snapshot, while the public application
will display `FID = 126` directly from the publisher's public Feature Service.
The project must not commit or publish the snapshot or a copied, clipped,
simplified, converted, or derived VSR geometry. Publication hosting for the
project-derived whale, vessel, and exposure layers remains undecided.

The initial architecture ([ADR 0001](docs/decisions/0001-accept-initial-architecture.md)) is refined by the accepted hybrid GIS toolchain ([ADR 0015](docs/decisions/0015-adopt-a-hybrid-open-source-and-esri-gis-toolchain.md)): Python owns reproducible processing, QGIS owns local inspection and visual verification, and the public Next.js map retains direct Esri integration. ArcGIS Pro is optional and unnecessary for Version 1. The repository has a GitHub Actions CI workflow with stable `analysis` and `web` jobs for pull requests and pushes to `main`; both jobs have run successfully on pull requests and merged `main` commits. An active `main` ruleset requires pull requests, current successful `analysis` and `web` checks, and merge commits, and blocks deletion and force pushes with no bypass actor. CI does not deploy or publish anything. [tools/](tools/README.md) remains a data-discovery evidence utility, not the analysis package.

Do not scaffold implementation directories ahead of the milestone that needs them.

Real datasets **have** now been inspected and their properties recorded in [docs/data-sources.md](docs/data-sources.md), which lifts the blanket ban on writing schemas. What may and may not be written now differs by what the thing depends on:

- **May be written when M3 needs them:** source, processing, analysis-grid, whale-input and vessel-input schemas and contracts. These describe data that has been inspected, and they do not depend on where results are eventually reported.
- **Now settled:** [ADR 0002](docs/decisions/0002-southern-california-study-area-extent.md) accepts the scope-reduced `receivers_50_nautical_miles` analytical domain. Reporting-domain-dependent contracts may be designed when their milestones need them, but none is implemented yet.
- **Still not to be written ahead of its milestone:** the **exposure formula**, inside-versus-outside statistics contract, exposure layer contract, and application-results file. Domain acceptance removes one prerequisite; it does not supply the exposure method, final vessel input, results, or UI integration.

The stable spatial roles must remain distinct: map/context extent, modeled-whale-support water geometry, and the system-performance-qualified AIS analytical domain. The accepted domain is 50 nautical miles (92,600 metres) from the relevant NAIS reception stations, not from the coast and not empirical 2024 coverage. Outside cells are excluded from headline statistics, not classified as low traffic.

## Version 1 scope

Version 1 answers one question: where modeled blue-whale habitat overlaps commercial vessel activity off Southern California, and how much of that relative exposure falls inside versus outside the current VSR zone.

Excluded from Version 1: noise, emissions, scenario comparison, seasonal breakdowns, custom backends, databases, queues, containers, and AI features. Those are not forbidden forever — they are out of scope now, and adding one requires a demonstrated need and a decision record. The full list is in the project brief.

## Scientific and analytical constraints

Non-negotiable. They apply to code, comments, UI text, documentation, and commit messages.

- Never claim to predict individual whale strikes, or to calculate collision probability without cited supporting methodology.
- Never claim to identify optimal VSR boundaries, and never make policy recommendations the analysis cannot support.
- Never present AIS-derived noise or emissions estimates as measured sound levels or as a regulatory-grade inventory.
- Use: relative exposure, spatial overlap, exposure index, proxy, scenario, exploratory analysis. Avoid: risk, probability, predicted strikes, optimal.
- **Do not silently convert an assumption into a fact.** A threshold, weighting, filter, or temporal window chosen because something had to be chosen stays labeled as a choice, with its rationale, wherever its results appear.
- Anything marked **To be verified** in the source register is unverified. Do not use it as a fact, and do not remove the marker without checking the source.

## Implemented versus planned

Most of this repository describes work that does not exist. Never blur that line.

- Write about implemented behavior in the present tense and planned behavior as planned.
- Do not describe a capability as working because the code looks like it should. Run it, or say you did not.
- If you leave something partial, say so in the document that owns it — not only in a commit message.
- Report outcomes accurately. If a check failed or a step was skipped, say so.

## Reproducibility and validation

- Every derived dataset must be regenerable from raw inputs by a documented, ordered process. A sequence of manual clicks that cannot be repeated is not a valid production step.
- Record provenance when data is retrieved: source, method, parameters, retrieval date, version. It cannot be reconstructed afterwards.
- Every published number must trace to an input and a processing step.
- Analytical logic gets tests with small synthetic inputs whose answers are known by construction.
- Spatial output gets looked at on a map. Passing tests do not catch a wrong projection.

## Data and secrets

- Never commit raw source data. It lives in a Git-ignored local data root.
- Never commit credentials, API keys, tokens, or connection strings — including in examples, fixtures, notebooks, or screenshots. Check the diff before committing.
- Keys that reach the browser are public: scoped and origin-restricted only, never with publishing rights.
- Git LFS is not in use. Large binaries need a decision record before they are added.
- Validated project-derived whale, vessel, and exposure datasets cross the provider-neutral publication boundary to
  the selected public delivery route. ArcGIS Location Platform limited data
  services and ArcGIS Online organization-hosted layers are separate
  conditional candidates; a non-Esri public representation must be selected
  later if neither fits. Do not enable pay-as-you-go or authorize spending.
  Derived data is not committed, except small results the application reads.
- The VSR geometry does not cross that boundary. Its immutable local snapshot
  remains ignored for analysis, and public display references the publisher's
  service directly with required attribution, disclaimer, and release-time
  anonymous/version verification. Public access is not treated as a
  redistribution licence.

## Concurrent sessions

- One branch per session. Never work directly on `main`.
- Prefer a separate Git worktree per session; two sessions in one working directory will corrupt each other's work.
- Split concurrent work along ownership lines so sessions do not edit the same files.
- Do not rewrite history on a branch another session may be using.
- Only one session publishes to an ArcGIS Location Platform or ArcGIS Online
  item at a time.

## Preserve work you did not do

If you find uncommitted changes you did not make: **stop and report them.** Do not stage, commit, stash, revert, discard, or tidy them. Do not amend, squash, rebase, or force-update existing commits. Someone else's work in progress is not yours to clean up.

## Commits

- One coherent change per commit — describable in one line without "and".
- Stage the specific files that belong to the commit. Avoid blanket staging when unrelated changes are present.
- Read the staged diff before committing.
- Message format: `<type>: <imperative summary>` using `docs`, `feat`, `fix`, `chore`, `refactor`, `test`.
- Update the documentation your change affects in the same branch as the change.
- **Do not push and do not merge unless explicitly authorized.** Branches stay local by default.
