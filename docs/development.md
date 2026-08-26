# Development

**Owns:** the engineering workflow — how work is done, recorded, verified, and reviewed in this repository.

> No application or analysis package has been scaffolded yet. The one exception is [../tools/](../tools/README.md), which holds a verification utility for data discovery and is not the analysis package. Sections that would contain commands are marked **pending implementation** and must be filled in by the milestone that creates the thing they describe. Do not invent commands here for code that does not exist.

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

**Pending implementation.** This section fills in as each part is built.

Expected shape once the milestones that create them are complete:

- **Analysis (Python)** — a pinned, reproducible environment; a documented setup command; a documented way to run the processing path end to end. Created in the processing-workflow milestone.
- **Application (Next.js / TypeScript)** — a documented install, dev-server, build, and type-check command. Created in the application-foundation milestone.
- **ArcGIS Pro** — a documented project location and the version used, since Pro projects are version-sensitive.
- **Prerequisites** — the specific tool versions the project actually requires, recorded once they are known rather than guessed now.

Whoever creates each of these updates this section in the same branch.

## Environment variables and secrets

- Never commit a credential, API key, token, connection string, or account password. This includes example files, notebooks, screenshots, and test fixtures.
- Local configuration lives in an ignored `.env.local`. A committed `.env.example` lists required variable **names** with empty or placeholder values only.
- Deployment configuration is set in the hosting platform, not in the repository.
- Any key shipped to the browser is public. It must be scoped and origin-restricted, and must never carry publishing or account-management rights.
- ArcGIS Online publishing credentials stay on the author's machine. Publishing is a local, authenticated operation and is never automated from the repository in Version 1.
- A committed secret is treated as compromised. Rotate it first; clean history second. Do not reverse that order.
- Before every commit, check the diff for values that look like credentials. This is a habit, not a tool.

## Raw data

- **Raw source data is never committed.** It lives under a Git-ignored local data root — see the proposed layout in [architecture.md](architecture.md).
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

Test commands: **pending implementation.**

## Formatting and linting

**Pending implementation.** Tooling is chosen when the first code of each kind is written, and recorded here at that point. The expectations that will hold regardless:

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
