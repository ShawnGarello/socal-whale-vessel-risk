# 0020 — Propose area-integrated relative exposure

**Status:** Accepted for exploratory execution — results pending independent audit
and owner review before final headlines
**Date:** 2026-09-06

## Owner authorization, 2026-09-06

The owner authorized proceeding with this method as an exploratory overlap proxy,
including its documented sensitivity checks, with speed separate and no collision
probability claim. Production results and sensitivity findings must return for
audit/review before final headlines or M6 completion. This authorizes implementation
and local execution; it does not assert scientific validation or authorize public
publication, pushing, merging, rebasing or shared-owner documentation edits.

The choices below were proposed in the foundation commit and are now selected
for that bounded exploratory execution. The threshold family is run as written;
no cutoff is tuned to a preferred inside/outside result.

## Context and verified inputs

M3 supplies two validated inputs on the same 4,516-cell EPSG:3310 water grid.
Exact local paths, checksums, inspected contracts and checks are in the
[foundation handoff](../m6-exposure-foundation-handoff.md). The subsequent
implementation generates local exploratory layers and sensitivity reports;
scientific conclusions remain subject to review.

- `blue_whale_grid_transfer_v1`: `modeled_density_animals_per_km2` is modeled
  density, not occurrence probability. Its numerator is
  `modeled_abundance_allocation_animals`; its denominator is actual cell water
  area. Support fields must accompany it. All inspected cells have complete
  source support. The approximately 0.1° source has been area-transferred under
  [ADR 0016](0016-transfer-whale-density-by-area-weighted-abundance.md).
- `production_vessel_input_v1`, identity
  `vessel-input-5e590ff3d85ee7acb16e2fd1`: use
  `vessel_km_all_commercial` and `vessel_km_per_water_km2_all_commercial`.
  These describe retained passenger/cargo/tanker movement, July 1 through
  November 30, 2024 UTC, with the accepted 300-second/30-knot rules, no length
  filter, cleaned-extent censoring and exact water allocation. Speed means,
  SOG availability and point-based distinct-vessel counts are separate
  descriptors. They do not change exposure weights.

[NOAA's attribute definitions](https://www.fisheries.noaa.gov/inport/item/64350)
identify density in animals/km², abundance as density times area, and uncertainty
as a CV; the monthly fields are unused because density is averaged across
months. [NOAA's product metadata](https://www.fisheries.noaa.gov/inport/item/64349)
describes summer/fall survey data from nine years during 1991–2018. Both were
consulted on 2026-09-06. The exact prediction-season limits remain unresolved
in the source register; July–November is the accepted traffic window, not a new
claim about the model's exact prediction window.

[Leaper and Panigada, IWC SC/63/BC4](https://iwc.int/public/documents/1Y-Rv/SC-63-BC4.pdf),
page 2, distinguishes vessel counts, transit rates, and distance travelled per
area per time, and describes reconstructing within-cell distance from successive
AIS positions. Consulted on 2026-09-06, it supports the traffic measure's
interpretation. It does **not** validate this project's product formula,
thresholds, or within-cell uniformity. Its collision modelling is not adopted.
The Becker technical-memorandum DOI failed to open in this session; no new
claim is based on a reading of that report.

## Proposed calculation and area basis

For cell i, let W_i be modeled animals/km², L_i retained vessel-km over the
single analytical period, G_i its exact water geometry, and A_i its area in km².
Let D be the accepted `receivers_50_nautical_miles` geometry and Z the immutable
local VSR snapshot after the established geographic densification/projection.

```text
T_i       = L_i / A_i                       vessel-km per water km², period total
X_i       = W_i * T_i                       exposure intensity
Q_i       = area(G_i ∩ D)                   qualified water km²
I_i       = area(G_i ∩ D ∩ Z)               qualified water inside VSR, km²
O_i       = area((G_i ∩ D) \ Z)             qualified water outside VSR, km²
E_i       = X_i * Q_i                       integrated qualified exposure
E_inside  = sum(X_i * I_i)
E_outside = sum(X_i * O_i)
share_in  = E_inside / (E_inside + E_outside)
```

X has units modeled animals × vessel-km / km⁴; E has units modeled animals ×
vessel-km / km². These awkward units are deliberate: neither quantity is animals
struck, encounters, collision probability, or expected strikes. The product is
a proposed spatial co-occurrence proxy, with greater whale density and greater
movement intensity each contributing proportionally. There is no calibrated
biological interaction width, surface availability, avoidance, or lethality term.

Full-water integrated exposure would be X_i A_i = W_i L_i. Multiplying abundance
by vessel-km without the area denominator introduces an extra area weight.
Summing X_i alone implicitly weights cells equally despite different water
areas. Dividing L_i by Q_i while retaining all full-water distance would
artificially inflate intensity in receiver-boundary cells; do not do that.

Applying X uniformly on G_i is an additional assumption at a receiver boundary:
the accepted upstream vessel input has full-water-cell totals, not the exact
distance inside D. Fractional allocation estimates their qualified share; it
does not reconstruct exact track distance there. Likewise, W_i is a cell mean,
not a new prediction on each clipped piece. The method cannot recover
subcell whale/traffic covariance from these means. Label **uniform exposure
within each cell's water geometry** wherever boundary-derived statistics appear.

## Proposed normalization and weights

Recommend preserving physical inputs and using X for calculation. For a
dimensionless map index only, propose `R_i = X_i / max(X_j)` over valid cells
with positive qualified water area. Its reference population, maximum, period,
and run identity must be recorded. R is relative to this dataset, not comparable
between releases without the recorded scaling reference. Do not winsorize or
clip the analytical values. The permitted range is 0–1; unavailable remains null.

Summaries may equivalently use `R_i * Q_i`, in index-km², because one positive
global multiplier cancels in shares. Scaling W and T separately by their positive
domain maxima also multiplies every X by the same constant, so it cannot alter
rank, exposure shares or quantile membership. This is an algebraic control for
sensitivity, not independent evidence of robustness. No sum-to-one normalization
is called a probability. No mean subtraction or z-score is used: negative
exposure and turning a positive density minimum into zero obscure the meaning.

Use first powers of both inputs, equal weight per retained vessel-km across
the accepted commercial types, and no speed, ship size, participation or CV
weight. This does not mean each vessel or vessel class contributes equally:
repeated distance remains additive. [ADR 0006](0006-report-vessel-speed-separately.md)
already excludes speed from exposure.

As a deliberately non-proportional sensitivity alternative, evaluate
`Y_i = (W_i / w0) * log1p(T_i / t0)`, with fixed references
`w0 = 1 animal/km²` and `t0 = 1 vessel-km/km² over this period`, then divide by
its qualified-domain maximum for display. This tests compression of high traffic
values; it changes the question and has no preferred scientific status. Keep
it separate from the primary method, including its own integrated shares.
Ranks/geometric means are further alternatives, not implemented methods; they
discard magnitude or impose different tradeoffs. A weighted sum is unsuitable
for the proposed co-occurrence meaning because either input alone could make it
large when the other is zero.

## Zero, missing and excluded support

Propose requiring a one-to-one join against the exact water grid, with matching
CRS, WKB, IDs, bounds, areas, source identities and accepted period. Reject
duplicate or missing rows, non-finite/negative inputs, inconsistent units and
material support gaps; never silently drop them or fill them with zero. For
this first production run, require the inspected `complete` whale support
status (uncovered area at most the existing 1e-6 m² exact-support tolerance).
Other statuses need explicit review before admitting a changed input.

Valid zero L or W yields zero X. Zero movement means no retained movement under
these AIS rules, not verified vessel absence: stationary-only cells can have
positive distinct counts and zero km. Missing speed does not make exposure
missing. Dry cells are skipped. A cell wholly outside D is excluded, with no
headline exposure value or low-traffic class; a partially qualified cell uses
only Q, I and O. No result normalizer includes wholly excluded cells.

If every valid X is zero, report zero integrated proxy totals but null exposure
shares, null max-normalized indices and unavailable high-exposure statistics,
with the reason. An empty qualified domain is a failed input, not an all-zero
result. Do not interpret any of these states as complete AIS observation.

D is exactly the retained union of 92,600-m station buffers intersected with
modeled support, selected under [ADR 0002](0002-southern-california-study-area-extent.md).
It is system-performance-qualified, not empirical 2024 coverage and not distance
from the coast. Receiver uptime, completeness, outages and feed losses remain
unverified. No exposure normalization repairs them.

## Fractional VSR accounting — already accepted, now a tested primitive

Use actual joint intersections in EPSG:3310, preserving holes and multipart
water. `I_i + O_i = Q_i`. Fractions are conditional on the qualified water, so
`E_i * I_i/Q_i = X_i I_i` when Q_i > 0. Equivalently, split a **full-water**
total X_i A_i using I_i/A_i and O_i/A_i, retaining the excluded remainder.
Never apply both reductions twice or multiply separately calculated domain
and VSR fractions. [ADR 0004](0004-analysis-grid-resolution.md) excludes
centroid, majority and whole-cell assignment.

The geometry foundation provides areas and splitting of a supplied full-water
total; the separate exposure module now implements this method. Geometry checks
area conservation with `rel_tol=1e-10`
and `abs_tol=1e-6 m²`, including nested-area comparisons. This is a numerical
check, not a minimum included area: positive slivers are retained, and raw
overlay residuals remain measurable. Fractions can differ from mathematical
limits by floating-point residuals; the production contract must retain and
bound these diagnostics before serializing display values.

The local loader pins the accepted mask and VSR checksums, validates CRS and the
selected receiver scenario, and checks the VSR source contract and FID 126.
It densifies source VSR edges to at most 0.01° before always-xy EPSG:3310
projection, matching the retained evidence. It does not repair invalid geometry.
[ADR 0019](0019-reference-the-publisher-hosted-vsr-service.md) requires all VSR
geometry and derivatives to remain local. The browser service is never an
analytical input. The exposure writer stores only domain-qualified water geometry,
never VSR intersection geometry. Wholly excluded cells retain rows with null
geometry and exposure fields; they cannot render as low traffic.

## Proposed high-exposure definition and sensitivity

Propose a baseline **90th percentile of exposure intensity, weighted by qualified
water area**, over all valid cells with Q_i > 0, including valid zeros. Define
the weighted quantile as the smallest observed X whose cumulative ascending Q
reaches at least p times total Q. Use X >= threshold, include every tied value,
and report the actual selected area; it need not equal exactly 10% of the domain.
Never break ties by cell ID or split a tied cell merely to obtain 10%.

For high set H, report `sum(I_i for H) / sum(Q_i for H)` and its outside
complement, in addition to actual inside/outside km². This is **share of
high-exposure water area**, not share of exposure or cell counts, and not the
fraction of the entire statewide VSR zone that is high. If the threshold is zero
or the selected positive-exposure area is empty, mark this statistic unavailable
as a discriminating high-exposure measure. Do not label all zero water high.

Predeclare p = 0.80, 0.90, 0.95 and additionally compare the positive-X-only
reference population, clearly labelled. Repeat threshold/area statistics for
the log-compressed alternative and verify the global-scaling invariants above.
Report thresholds, tied areas, exposure shares, high-area shares, rank changes
and changes in outside concentrations; retain unstable findings. The baseline
threshold remains a proposal until the real distribution and sensitivity have
been reviewed. It is a descriptive cutoff, not an ecological danger threshold.

Retain ADR 0004's 5-versus-10-km sensitivity requirement. It can use existing
input sufficient statistics: form whole-10,000-m-aligned parent water unions,
sum whale abundance and vessel distance, divide each by actual parent water
area, then recompute X before exact domain/VSR clipping. Merely summing existing
5-km exposure totals tests conservation, not the coarser uniformity assumption.
No new five-month AIS processing is needed for that aggregation comparison.

## Limitations and acceptance boundary

The inputs describe three different times: multi-year modeled summer/fall
whales, July–November 2024 traffic, and the zone retrieved in August 2026.
This is retrospective overlap against the current zone, not contemporaneous
whale–vessel encounters, 2026 traffic, program effectiveness or compliance.
Native whale uncertainty is substantial and spatially dependent; CV is not
propagated and no confidence interval is claimed. Sensitivity ranges are not
statistical uncertainty intervals.

The 5-km grid creates no new biological resolution. Model support is not an
independent coastline. Short straight-line interpolation, gap/speed exclusions,
type classification, reception losses, omitted boundary entry/exit paths and
the 35°N context truncation constrain interpretation. Uniform allocation may be
especially poor along shipping lanes and on small water slivers. Do not remove
small cells or anomalous dates without a separately justified decision.

The owner's authorization above selects these choices for exploratory execution.
Independent audit and owner review of the actual findings remain required before
final headlines. M6 remains incomplete; the handoff records execution, exact
output identities, validation, sensitivity and visual evidence. No application
integration, publication route, deployment, or final headline is selected here.

## Downstream delivery implementation, 2026-09-06

Subsequent implementation adds distinct
`relative_exposure_display_v1` and
`relative_exposure_application_results_v1` contracts without changing this
method. The exporter consumes an exact checksum-pinned current-code analytical
bundle, re-verifies both spatial tables, recomputes the accepted summaries from
their serialized values, and reconciles every consumed report field. A supplied
report checksum establishes byte identity only; it does not substitute for
numerical verification.

Public nested structures are constructed through explicit typed allowlists.
Unexpected mappings, invalid controlled text or enumeration values, private
paths, credentials, debug metadata, execution clocks, and private upstream
generation lineage are rejected or excluded. The display contains qualified
domain-water geometry only and omits VSR geometry, per-cell VSR splits, and
wholly excluded cells. Its paired manifest binds the display checksum to the
small results checksum and deterministic results ID.

Fresh first/repeat bundles preserve run ID
`exposure-6dd927974fae959765c9b5c3` and deterministic analytical bytes despite
different timestamp-bearing upstream lineage. Canonical and repeat exports also
reproduce exact bytes. The 2,793-feature display is 2,542,744 bytes raw,
528,235 bytes gzip, and 375,238 bytes Brotli and passed checksum-bound QGIS
inspection. This makes static same-origin delivery a measured candidate; it does
not accept that publication route, publish an artifact, integrate M7, approve a
headline, or complete M6. Exact identities, validation, and remaining gates are
recorded in the
[exposure-results delivery handoff](../m6-exposure-results-delivery-handoff.md).

## Execution contracts

`exposure_inputs.py` accepts the exact M3 analytical artifacts and deterministic
quality report identified in the handoff. Regenerated generation lineage is
accepted when its contract, configuration, method, source/output references and
successful validation records reconcile with checksum-verified dataset metadata.
The join enforces complete row identity/order/geometry/bounds,
water areas, complete whale support, finite nonnegative physical inputs, units,
group-distance reconciliation, metadata contracts, accepted period and method,
and sidecar links. Different analytical source bytes require a reviewed contract
update. Execution clocks and locators may vary; the period manifest may regenerate
while every dated cleaned partition remains identical. Actual whale/vessel
lineage hashes are retained in execution `input_lineage_sha256`, excluded from
analytical identity, layer metadata and deterministic sensitivity reports.
Synthetic tests exercise bad support and join cases independently
of the real checksums.

`exposure_run.py` writes a fresh ignored atomic local bundle under
`exploratory_relative_exposure_v1`, method version `1.0.0`, containing 5-km and
10-km GeoParquet, a deterministic sensitivity report and timestamp-bearing
generation lineage. Both layers carry product/log intensity, maximum-scaled
indices, qualified/inside/outside integrated values and all-valid p80/p90/p95
flags. Full-water input scalars are retained for reproducibility; result geometry
is exact qualified water, unrelated to VSR clipping. VSR areas are scalar
accounting fields only. Metadata states units, period, vintages, qualification,
assumptions and the review-pending status. Input checksums, method/reporting
contracts and relevant software versions bind deterministic identity; paths and
clocks stay in lineage. Failed temporary bundles are preserved; outputs are never
overwritten. A separate read-back verifier checks serialized formula, integration,
geometry area, exclusion, index, flags and summary consistency.

Outside concentrations are reported conservatively as the ten cells contributing
the most integrated exposure outside the zone, with their fraction of the outside
total and parent-cell origin. Exact contribution ties are ordered by cell ID.
This is a ranked contribution list, not a newly assumed connected hotspot cluster,
and the cell origin is a locator, never a boundary assignment rule. The log
comparison includes tie-aware Spearman cell-rank changes; grid-size sensitivity
compares integrated shares and qualified high-area shares, without pretending
that 5-km and 10-km cells are the same ranking population.
