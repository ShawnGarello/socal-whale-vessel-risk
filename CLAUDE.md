# CLAUDE.md

Start with [AGENTS.md](AGENTS.md) and follow it. It is the operational instruction set for this repository, and it applies in full to Claude.

Then read the canonical documents for whatever you are working on, listed in the reading order at the top of AGENTS.md. [docs/project-brief.md](docs/project-brief.md) is required for every task, because it defines what Version 1 is and how results must be described.

A few things that are easy to get wrong here and are worth restating:

- **Respect the scientific constraints.** No strike prediction, no collision probability, no optimal boundaries, no policy recommendations. Use relative exposure, spatial overlap, exposure index, proxy, scenario. Assumptions stay labeled as assumptions.
- **Do not invent what is not there.** Dataset properties are recorded in [docs/data-sources.md](docs/data-sources.md) only where they were read from the data or from the publisher's own documentation. Do not add a field name, resolution, or licensing term that is not. Anything marked *To be verified* is unverified, and no data contract, API contract, layer contract, or exposure formula is written yet.
- **Distinguish implemented from planned.** This repository is documentation plus one verification utility in [tools/](tools/README.md). There is no application and no analysis package. Do not describe planned work as built.
- **Use the concurrent-session workflow.** One branch per session, prefer a separate worktree, never work on `main`, and never touch uncommitted changes you did not make.
- **Make focused commits** and update the documentation your change affects in the same branch.
- **Do not push and do not merge without explicit authorization.**
