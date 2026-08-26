# 0006 — Report vessel speed separately rather than inside the exposure index

**Status:** Accepted
**Date:** 2026-08-25

## Context

[Architecture](../architecture.md) deferred two questions about vessel speed: whether AIS speed can be derived reliably at all, and — if so — whether it belongs in the exposure index or is reported separately. The project brief also flagged speed as a scope item that might have to be reduced in ambition if the data could not support it.

**On the first question, the evidence is encouraging but limited.** Speed over ground is directly present and does not need reconstructing from consecutive positions. In the inspected sample — five 34-minute windows in 2024, all at the same time of day, detailed in [../data-sources.md](../data-sources.md):

- `SOG` is in **knots**, per NOAA's own AIS FAQ. This is documentation, not inference.
- It has exactly **one documented sentinel**, 102.3 for "not available".
- In the 15 July retained window, Southern California commercial vessels — 2,448 rows — had **no missing `SOG`**, the sentinel in **22 rows (0.90%)**, no negative values, and nothing above 40 knots outside the sentinel. Non-sentinel values ran 0.0 to 24.1 knots.
- Moving commercial vessels reported roughly **once per minute**, so speed is well sampled along a transit.

The honest summary is that **`SOG` is present, documented, and appears usable in the inspected sample.** It is not established as reliable across the full analytical period — 2,448 rows from one half-hour cannot establish that about an estimated 10⁸ records, and the sample says nothing about night or midday behaviour. What the sample does show is that there is no structural obstacle: the field exists, its units are documented, and its one failure mode is a named sentinel rather than silent corruption.

That is enough to justify keeping the scope item rather than reducing it. It is not enough to describe the input as validated, and this record should not be cited as if it did. The remaining question is what to do with the speed data.

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
- The speed result inherits the vessel input's coverage problem. Where AIS reception is sparse, a speed summary is computed from few and possibly unrepresentative transits, so the speed layer is subject to the same analytical-domain limits as the exposure layer — see [0002](0002-southern-california-study-area-extent.md).
- Processing must exclude the 102.3 sentinel explicitly rather than relying on a range filter, and must still apply behavioural plausibility checks. Neither is discharged by this record.
- Two outputs mean two things to explain in the interface, which is a real cost in a project whose main risk is overinterpretation. The explanatory text has to make clear that the exposure layer and the speed layer are separate results and that neither is a strike risk.
- If a later version does adopt a published speed–lethality methodology, it would produce a **different, additional** layer with its own citation, superseding this record rather than quietly extending the index. That is listed in the project brief as a Beyond-Version-1 direction.

## Alternatives considered

**Weight vessel activity by a published speed–lethality function.** Rejected for Version 1. It is the scientifically richest option and there is real literature behind it, but adopting it converts the exposure index into a strike-risk estimate, which the project brief explicitly excludes and which would require citing and defending a methodology this project has not validated. Available later, with its own decision record.

**Weight vessel activity by raw speed, without a lethality function.** Rejected, and it is the worst of the options. A raw speed weight has no physical meaning — it implies faster traffic matters proportionally more, which is a lethality claim made without saying so. It would smuggle in exactly the assumption the previous alternative at least makes explicitly.

**Filter the vessel input to transits above 10 knots and build the index from those alone.** Rejected. It embeds the program's threshold in the index, so the index could no longer be compared against the zone without circularity, and it discards the slower traffic that still contributes to overlap.

**Drop speed from Version 1 entirely.** Rejected. The brief allowed for reducing this scope item if the data could not support it, and nothing inspected so far suggests it cannot: `SOG` is present in known units with a single documented sentinel, at a rate under 1% in the commercial rows sampled. Dropping an apparently usable input on the strength of an unexamined worry would be an unnecessary reduction, and the brief requires reductions to be justified rather than convenient. **If processing later finds the field unusable over the full period, that is a reduction to record then** — this record does not foreclose it.
