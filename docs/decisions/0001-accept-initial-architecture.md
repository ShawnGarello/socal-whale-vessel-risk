# 0001 — Accept the initial project architecture

**Status:** Accepted
**Date:** 2026-08-25

## Context

The documentation foundation for this project produced a proposed architecture in [../architecture.md](../architecture.md): offline processing in ArcGIS Pro and Python, validated derived datasets published as ArcGIS Online hosted layers, and a Next.js and TypeScript application using the ArcGIS Maps SDK for JavaScript, deployed statically.

That proposal was reviewed. The review raised four findings, all addressed before this record: an overstated novelty claim, an unstated ArcGIS Online feasibility gate, an incorrect assertion that coded steps are self-documenting, and AIS limitations presented as verified when the data has not been inspected.

Nothing has been built, and data discovery has not started. Most specifics — study area, grid resolution, analytical period, exposure formula, layer representation — are therefore still unknown and are recorded as deferred decisions. But the application-foundation milestone does not depend on the data, and it cannot start against a direction that is still labelled provisional. A choice was needed: keep the architecture open until the data is understood, or accept it now as the direction to build against while leaving the data-dependent specifics deferred.

## Decision

The architecture in [../architecture.md](../architecture.md) is accepted as the **initial** architecture. Specifically:

- Analysis happens offline in ArcGIS Pro and Python. The browser presents and filters; it never computes exposure or any reported statistic.
- Validated derived datasets are published to ArcGIS Online as hosted layers and web maps. ArcGIS Online is a hosting target, not a processing tier.
- The application is Next.js and TypeScript with the ArcGIS Maps SDK for JavaScript, deployed as a static build over HTTPS.
- Version 1 introduces no custom backend, microservices, PostGIS or self-hosted database, job queue, container orchestration, or AI feature.

Acceptance does not resolve the deferred decisions listed at the end of that document, and does not clear the ArcGIS Online capability gate. Those remain open, and the layer representation and hosting approach still depend on verifying what the available ArcGIS Online account can actually publish and share.

## Consequences

- The application-foundation milestone is unblocked and may begin against this direction.
- Structural changes to the architecture now require a decision record superseding this one, rather than an unannounced edit. Filling in a deferred decision is not a change to this record — it is the deferral resolving as intended.
- Because there is no server-side compute, every analytical step must be reproducible offline and published as a result. This is a constraint the processing workflow has to satisfy, not an optimisation.
- If the ArcGIS Online capability check fails — no public sharing, no imagery or tile publishing, insufficient credits or storage — the hosting half of this architecture does not hold, and this record is superseded rather than patched. That check is a deliverable of the application-foundation milestone for exactly this reason.
- Data contracts, API contracts, layer contracts, analytical schemas, and the exposure formula are still not written. Accepting the architecture does not license writing them ahead of inspecting real datasets.
- Accepting early carries a real risk: data discovery may reveal that the volumes or formats involved do not suit this pipeline. That risk is taken knowingly, and is cheaper than leaving the application milestone blocked on data work it does not depend on.

## Alternatives considered

**Leave the architecture proposed until after data discovery.** Rejected. The application-foundation milestone is explicitly independent of the data milestones, and blocking it on data work would serialise two tracks that can run in parallel — against a target date that does not have room for it. The genuine data risk is contained by keeping every data-dependent decision deferred.

**Add a custom backend, a database such as PostGIS, or a processing service.** Rejected. There is no demonstrated need. Version 1 publishes precomputed results; a server tier would add operational surface, cost, and failure modes without answering the research question any better. This stays available if a concrete need appears, and would need its own record.

**Deliver entirely within ArcGIS Online, with no custom application.** Rejected. A configured web map would show the layers, but the interactive application is part of the Version 1 deliverable and is where the software engineering side of the project is visible. It also gives control over how assumptions and limitations are presented, which a stock viewer does not.

**Non-Esri stacks for mapping and hosting.** Not considered. Working in the ArcGIS ecosystem is a deliberate goal of the project, not an implementation detail chosen on technical merit alone.
