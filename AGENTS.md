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
| Engineering workflow | [docs/development.md](docs/development.md) |
| Historical decisions | [docs/decisions/](docs/decisions/README.md) |
| Agent instructions | this file |

## Current state

The repository is documentation plus one verification utility. No application, analysis package, tests, or CI exist yet. The exception is [tools/](tools/README.md), which holds a single script that re-checks the evidence behind data discovery; it verifies claims the documents already make and is explicitly not the analysis package. The architecture has been accepted as an initial direction ([ADR 0001](docs/decisions/0001-accept-initial-architecture.md)), but nothing has been built against it, and several of its data-dependent decisions remain open.

Do not scaffold implementation directories ahead of the milestone that needs them, and do not create data contracts, API contracts, layer contracts, analytical schemas, or the exposure formula at all yet. Those wait for inspection of real datasets, which has not happened.

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
- Derived datasets are published to ArcGIS Online, not committed, except small results the application reads.

## Concurrent sessions

- One branch per session. Never work directly on `main`.
- Prefer a separate Git worktree per session; two sessions in one working directory will corrupt each other's work.
- Split concurrent work along ownership lines so sessions do not edit the same files.
- Do not rewrite history on a branch another session may be using.
- Only one session publishes to ArcGIS Online at a time.

## Preserve work you did not do

If you find uncommitted changes you did not make: **stop and report them.** Do not stage, commit, stash, revert, discard, or tidy them. Do not amend, squash, rebase, or force-update existing commits. Someone else's work in progress is not yours to clean up.

## Commits

- One coherent change per commit — describable in one line without "and".
- Stage the specific files that belong to the commit. Avoid blanket staging when unrelated changes are present.
- Read the staged diff before committing.
- Message format: `<type>: <imperative summary>` using `docs`, `feat`, `fix`, `chore`, `refactor`, `test`.
- Update the documentation your change affects in the same branch as the change.
- **Do not push and do not merge unless explicitly authorized.** Branches stay local by default.
