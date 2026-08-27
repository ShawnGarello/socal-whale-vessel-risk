# Architecture Decision Records

**Owns:** the historical record of decisions that shape this project, and the reasoning behind them.

This directory holds Architecture Decision Records (ADRs). An ADR is a short note explaining a choice that constrains later work: what the situation was, what was decided, and what that decision costs.

## Records

| # | Decision | Status |
|---|---|---|
| [0001](0001-accept-initial-architecture.md) | Accept the initial project architecture | Accepted |
| [0002](0002-southern-california-study-area-extent.md) | Southern California study area extent | **Proposed** — map extent settled, analytical domain open |
| [0003](0003-projected-coordinate-system.md) | Use California Albers (EPSG:3310) as the analysis projection | Accepted |
| [0004](0004-analysis-grid-resolution.md) | Use a 5 km analysis grid with fractional VSR-boundary accounting | Accepted |
| [0005](0005-analytical-period.md) | Use 1 July to 30 November 2024 as the Version 1 analytical period | Accepted |
| [0006](0006-report-vessel-speed-separately.md) | Report vessel speed separately rather than inside the exposure index | Accepted |
| [0007](0007-use-npm-for-the-web-application.md) | Use npm as the web application's package manager | Accepted |
| [0008](0008-deliver-the-application-as-a-static-export.md) | Deliver the application as a static Next.js export | Accepted |
| [0009](0009-mount-arcgis-through-client-only-map-components.md) | Mount the ArcGIS SDK through client-only map components | Accepted |
| [0010](0010-use-vitest-for-typescript-tests.md) | Use Vitest for TypeScript tests | Accepted |
| [0011](0011-use-uv-for-the-python-analysis-toolchain.md) | Use uv for the Python analysis toolchain | Accepted |

## Why these exist

The most expensive question in a project six months old is "why is it like this?" Code shows what was decided; it rarely shows what else was considered or what was known at the time. An ADR captures the reasoning while it is still fresh, so a later reader can tell the difference between a deliberate choice and an accident — and so a decision can be revisited on its merits rather than re-argued from scratch.

This matters more than usual here, because [architecture.md](../architecture.md) deliberately defers a long list of decisions until real data has been inspected. Each of those, when resolved, is exactly the kind of thing an ADR exists to record.

## When to write one

Write an ADR when a choice:

- constrains later work or is expensive to reverse;
- resolves something listed as a deferred decision in [architecture.md](../architecture.md);
- shapes the analysis — study area, coordinate system, grid resolution, analytical period, exposure formula, thresholds, or normalization;
- adds, replaces, or rules out a dataset, tool, or platform;
- narrows Version 1 scope because the data cannot support what was planned;
- would surprise a reader who found it later without explanation.

Do not write one for routine implementation choices, formatting preferences, or anything a reasonable reader would take for granted.

An ADR is not the only place a decision appears. Scope changes still update [project-brief.md](../project-brief.md), verified dataset properties still update [data-sources.md](../data-sources.md), and resolved architecture questions still update [architecture.md](../architecture.md). The ADR records *why*; the owning document records *what is true now*.

## Format

One file per decision, named `NNNN-short-kebab-title.md`, numbered sequentially from `0001`. Numbers are never reused and files are never deleted.

A decision that is later reversed is not edited away. Its status becomes `Superseded by NNNN`, and the new record explains what changed. The record of a wrong decision is often more useful than the record of a right one.

Keep records short. One page is usually enough; if a record needs more, the decision probably contains more than one decision.

## Template

```markdown
# NNNN — <Short title stating the decision>

**Status:** Proposed | Accepted | Superseded by NNNN | Deprecated
**Date:** YYYY-MM-DD

## Context

What situation forced a choice. What was known at the time, what was not, and
what constraints applied — data properties, tooling, scope, time. Enough that a
reader who was not there can judge the decision on the information available
when it was made.

## Decision

What was decided, stated plainly and in the present tense.

## Consequences

What follows from this — what becomes possible, what becomes harder, what is now
ruled out, and what has to be revisited if the decision is reversed. Include the
costs honestly; a record listing only benefits is not a decision record.

## Alternatives considered

Each option that was genuinely weighed, and why it was not chosen. "Not
considered" is a valid entry if an obvious alternative was never evaluated —
that is useful information for whoever revisits this.
```
