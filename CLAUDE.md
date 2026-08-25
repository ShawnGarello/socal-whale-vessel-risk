# CLAUDE.md

Start with [AGENTS.md](AGENTS.md) and follow it. It is the operational instruction set for this repository, and it applies in full to Claude.

Then read the canonical documents for whatever you are working on, listed in the reading order at the top of AGENTS.md. [docs/project-brief.md](docs/project-brief.md) is required for every task, because it defines what Version 1 is and how results must be described.

A few things that are easy to get wrong here and are worth restating:

- **Respect the scientific constraints.** No strike prediction, no collision probability, no optimal boundaries, no policy recommendations. Use relative exposure, spatial overlap, exposure index, proxy, scenario. Assumptions stay labeled as assumptions.
- **Do not invent what is not there.** No field names, schemas, data or API contracts, resolutions, licensing terms, or exposure formulas until real datasets have been inspected. Anything marked *To be verified* is unverified.
- **Distinguish implemented from planned.** This repository is documentation only right now. Do not describe planned work as built.
- **Use the concurrent-session workflow.** One branch per session, prefer a separate worktree, never work on `main`, and never touch uncommitted changes you did not make.
- **Make focused commits** and update the documentation your change affects in the same branch.
- **Do not push and do not merge without explicit authorization.**
