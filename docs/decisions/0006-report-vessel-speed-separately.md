# 0006 — Report vessel speed separately rather than inside the exposure index

**Status:** Accepted
**Date:** 2026-08-25

## Context

[Architecture](../architecture.md) deferred two questions about vessel speed: whether AIS speed can be derived reliably at all, and — if so — whether it belongs in the exposure index or is reported separately. The project brief also flagged speed as a scope item that might have to be reduced in ambition if the data could not support it.

**Discovery answered the first question: yes.** Speed over ground is directly present and does not need reconstructing from consecutive positions. From the inspected records:

- `SOG` is populated in **100%** of records — it is never missing.
- It is in **knots**, confirmed by NOAA's own AIS FAQ.
- It has exactly **one documented sentinel**, 102.3 for "not available", which occurred in 66 of 13,483 Southern California records — **0.5%**.
- Outside that sentinel the Southern California values are plausible: no negatives, nothing above 40 knots, a maximum of 24.1 knots among commercial vessels.
- Moving commercial vessels report roughly **once per minute**, so speed is well sampled along a transit.

So the scope item does not need reducing, and that reduction does not have to be recorded. The remaining question is what to do with the speed data.

The second question is not really a data question. It is a question about what the exposure index is allowed to mean. Speed matters to whales through **strike lethality** — the published relationship is between vessel speed and the probability that a struck whale dies. Putting speed into the index as a weight would therefore require adopting a speed–lethality function, and the result would no longer be a measure of spatial overlap. It would be a strike-risk proxy.

The project brief forbids exactly that: no claim of collision probability without cited supporting methodology, no predicted strikes, and the preferred vocabulary is relative exposure and spatial overlap.

## Decision

**Vessel speed is not a term in the Version 1 exposure index.** The index combines modeled blue-whale density and commercial vessel activity only.

Speed is instead carried as its own derived output, reported and mapped alongside the exposure layer — for example the distribution of commercial transit speeds, and how the share of transits at or below the program's requested 10 knots differs inside and outside the zone.

This record does **not** define the exposure formula, the normalization, or the weighting. Those remain deferred until the discovery findings have been audited. It settles one thing only: speed is not an input to that formula.

## Consequences

- The exposure index keeps a statement of meaning that the method actually supports: **where modeled whale density and commercial vessel activity coincide.** Nothing in it has to be defended as a lethality assumption.
- Speed becomes a **more** visible part of the deliverable, not a less visible one. It is the quantity the VSR program actually asks about, and a descriptive speed result answers a question a reader will have — are ships slowing down in the zone? — that a composite index would bury.
- The speed result is descriptive and must be worded as such. Observing speeds inside and outside the zone is not a measurement of program compliance: the program's own map states that vessels under a licensed pilot are exempt, and the analysis cannot identify which vessels are enrolled in the program. **Any comparison is between waters, not between participants.**
- Two outputs mean two things to explain in the interface, which is a real cost in a project whose main risk is overinterpretation. The explanatory text has to make clear that the exposure layer and the speed layer are separate results and that neither is a strike risk.
- If a later version does adopt a published speed–lethality methodology, it would produce a **different, additional** layer with its own citation, superseding this record rather than quietly extending the index. That is listed in the project brief as a Beyond-Version-1 direction.

## Alternatives considered

**Weight vessel activity by a published speed–lethality function.** Rejected for Version 1. It is the scientifically richest option and there is real literature behind it, but adopting it converts the exposure index into a strike-risk estimate, which the project brief explicitly excludes and which would require citing and defending a methodology this project has not validated. Available later, with its own decision record.

**Weight vessel activity by raw speed, without a lethality function.** Rejected, and it is the worst of the options. A raw speed weight has no physical meaning — it implies faster traffic matters proportionally more, which is a lethality claim made without saying so. It would smuggle in exactly the assumption the previous alternative at least makes explicitly.

**Filter the vessel input to transits above 10 knots and build the index from those alone.** Rejected. It embeds the program's threshold in the index, so the index could no longer be compared against the zone without circularity, and it discards the slower traffic that still contributes to overlap.

**Drop speed from Version 1 entirely.** Rejected. The brief allowed for reducing this scope item if the data could not support it, but the data supports it well — `SOG` is complete, in known units, with a 0.5% sentinel rate. Dropping a usable input would be an unnecessary reduction, and the brief requires reductions to be justified rather than convenient.
