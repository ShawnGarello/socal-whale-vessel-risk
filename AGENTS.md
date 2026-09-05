# Agent Guidance

Operational rules for all coding agents. Keep project status and execution
history in their owning documents, not in this file.

## Read before working

At session start, before changes:

1. Read [project-brief.md](docs/project-brief.md) for scope and scientific framing.
2. Read the [roadmap](docs/roadmap.md) status table and the relevant milestone's
   objective, dependencies, current progress, remaining work, and completion
   criteria. Read historical run records when the task depends on that evidence.
3. Read [Agent reading and handoff workflow](docs/development.md#agent-reading-and-handoff-workflow)
   and its applicable workflow sections. Then follow the task routes below.

Use headings and search; read each selected section completely. Do not repeatedly
reload unchanged documents. After a branch change, compaction, or handoff,
refresh relevant instructions and changed or missing context. Never skip an
applicable constraint merely to save tokens.

| Task | Additional reading before acting |
|---|---|
| Design or implementation | Relevant [architecture](docs/architecture.md) sections, component README ([analysis](analysis/README.md) or [web](web/README.md)), and applicable [ADRs](docs/decisions/README.md) |
| Data, methodology, or real-data runs | Relevant [source register](docs/data-sources.md) entries, [data policy](data/README.md), contracts/ADRs, and exact run procedure including resource gates |
| Tests or audit | Changed implementation/tests, [testing policy](docs/development.md#testing-and-verification), and retained evidence needed to verify claims |
| Publication, credentials, or deployment | Development's secrets, deployment and account-check sections; source-use terms; [ADR 0019](docs/decisions/0019-reference-the-publisher-hosted-vsr-service.md) |
| Documentation only | Changed document's owner and affected references; no unrelated historical evidence dump |

The [original vision](docs/project-vision-and-learning-plan.md) is background,
not current scope. A branch handoff aids navigation but does not override owners,
contracts, or ADRs. Verify its claims against code and retained evidence.

## Document ownership

Update the owner, not a copy. If documents disagree, the owner wins and affected
restatements are corrected in the same change.

| Information | Owner |
|---|---|
| Public overview and visible status | [README.md](README.md) |
| Scope, Version 1 definition, non-goals | [Project brief](docs/project-brief.md) |
| Milestones, progress, version direction | [Roadmap](docs/roadmap.md) |
| System design and boundaries | [Architecture](docs/architecture.md) |
| Dataset provenance and verification | [Data sources](docs/data-sources.md) |
| Local data handling and retrieval | [Data policy](data/README.md) |
| Engineering workflow | [Development](docs/development.md) |
| Decisions and rationale | [ADRs](docs/decisions/README.md) |
| Agent instructions | This file; [CLAUDE.md](CLAUDE.md) is only an entrypoint |

## Scope and analytical constraints

- Version 1 measures modeled blue-whale habitat overlap with commercial vessel
  activity and relative exposure inside versus outside the current VSR zone.
  Noise, emissions, scenarios, seasonal breakdowns, custom backends, databases,
  queues, containers, and AI features are out of scope. Expansion needs a
  demonstrated need and decision record; scope changes go to the brief first.
- Python owns reproducible processing, QGIS local spatial inspection, and the
  Next.js application direct Esri integration. ArcGIS Pro is optional.
- Use relative exposure, spatial overlap, exposure index, proxy, or exploratory
  analysis. Never claim individual strike prediction, unsupported collision
  probability, optimal boundaries, or unsupported policy recommendations.
  Never present AIS noise/emissions proxies as measured sound or a
  regulatory-grade inventory.
- Assumptions stay labelled choices with rationale. Unverified source facts stay
  unverified until checked. Do not infer observational completeness from counts,
  successful processing, or period readiness.
- Keep map/context extent, modeled-whale-support water geometry, and the accepted
  AIS analytical domain distinct. The latter is 50 nautical miles (92,600 m)
  from relevant NAIS reception stations, not from the coast or empirical 2024
  coverage. Outside cells are excluded from headline statistics, not classified
  as low traffic. See [ADR 0002](docs/decisions/0002-southern-california-study-area-extent.md).
- Do not scaffold ahead of milestone need. Inspected-data source/processing/grid
  and input contracts may be implemented when M3 needs them. Domain acceptance
  does not authorize premature exposure formulas, statistics/layer contracts,
  or application-results files; follow milestone prerequisites.
- Distinguish implemented, tested, planned, and unverified behavior. Record
  failed/skipped checks and unfinished work in the owner. A milestone is complete
  only when its actual completion criteria are met.

## Data, reproducibility, and safety

- Never modify or commit raw data. Never commit credentials, API keys, tokens,
  or connection strings, including examples, fixtures, notebooks, or images.
  Browser keys are public: scoped, origin-restricted, without publishing rights.
  Inspect staged diffs for secrets and unintended data.
- Record retrieval provenance when obtained: source, method, parameters, date,
  version. Every derived dataset must be regenerable and every published number
  traceable. No unrecorded manual production transformations or hand-edited
  generation-time lineage.
- Analytical logic requires known-answer synthetic tests. Spatial outputs require
  actual map inspection tied to exact checksums, separately from generation-time
  lineage. CI does not replace these checks.
- Before heavy execution, read and enforce the run's documented resource settings,
  preflight/runtime gates, stop conditions, and output safeguards. Run resource
  experiments sequentially. Preserve inputs, failed-run evidence, and existing
  artifacts; do not relax gates, clear caches, or rerun expensive work blindly.
- Derived data stays ignored except permitted small application results.
  Large binaries require a decision record; Git LFS is not in use.
- Validated derived whale/vessel/exposure data crosses the provider-neutral
  publication boundary only through an evidence-selected route. Do not infer
  publishing access from a working basemap key, conflate Location Platform with
  ArcGIS Online organization hosting, enable pay-as-you-go, or authorize spending.
  Account operations/publication follow development's author-run controls.
  CI neither publishes nor deploys.
- VSR analysis uses the immutable ignored local snapshot. Public display
  references publisher `FID = 126` directly with attribution, disclaimer, and
  release-time anonymous/version verification. Never commit or publish the
  snapshot or copied, clipped, simplified, converted, or derived VSR geometry.
  Public access is not a redistribution licence; follow ADR 0019.

## Worktrees, commits, and handoff

- One branch per session; never work directly on `main`. Prefer a separate
  worktree and split concurrent work by file ownership. Only one session may
  publish to a given Esri item at a time.
- If uncommitted changes are not yours, **stop and report them**. Do not stage,
  commit, stash, revert, discard, or tidy someone else's work.
- Do not amend, squash, rebase, or force-update existing commits without explicit
  authorization. Never rewrite a branch another session may be using.
- Make coherent, reversible commits. Stage specific files and read the staged
  diff. Use `<type>: <imperative summary>` with `docs`, `feat`, `fix`, `chore`,
  `refactor`, or `test`; update affected documentation in the same branch.
- **Do not push or merge without explicit authorization.** Follow development's
  independent audit, PR, and CI workflow. Both `analysis` and `web` checks must
  pass on the current PR head before an authorized GitHub merge; no direct-main
  updates or ruleset bypass.
- Continue routine authorized work without extra approval pauses. Stop for
  unsupported material scientific choices, missing authority, unsafe resource
  conditions, or scope expansion; report the specific blocker and next action.
- Keep updates concise. Use focused checks during development and required
  component gates at handoff. Repeat/broaden checks when changes, failures, or
  unresolved concerns justify them; follow the testing policy, not an arbitrary
  test or token budget. Do not install skills or change model/context settings
  merely because a session uses a different model.
- Before ending partial work, commit only intended changes and leave a current
  handoff with completed/remaining steps, commands, artifact identities, checks,
  failures, and next action. Label historical records as history.
