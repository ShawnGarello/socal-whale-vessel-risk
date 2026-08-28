# 0018 — Use vessel-kilometres as the primary grid activity measure

**Status:** Proposed
**Date:** 2026-08-27

## Context

M3 needs to convert cleaned commercial AIS observations into a vessel-activity
input on the accepted 5 km water grid. The choice is not cosmetic. Counts of
messages, vessels, time and distance answer different questions, react
differently to missing reports, and would give the later relative-exposure
analysis different meanings.

The current cleaner supplies deterministically ordered observations with MMSI,
UTC timestamp, WGS 84 position, reported SOG and vessel group. It has already
removed exact duplicates and every conflicting `(MMSI, UTC timestamp)` group
under [ADR 0013](0013-remove-conflicting-ais-key-records.md). It does not select
a maximum interpolation gap, implied-speed threshold, length threshold or
behavioral plausibility rule. Those omissions are explicit and must not be
filled silently by aggregation.

This record does not define the relative-exposure formula, a reporting domain,
inside-versus-outside statistics or a high-exposure threshold. Speed remains a
separate descriptive output under
[ADR 0006](0006-report-vessel-speed-separately.md).

## Evidence

### Verified from official documentation

- The [NOAA AIS FAQ](https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf)
  says the public NMEA records are down-sampled to the nearest whole minute,
  identifies short collection interruptions, and warns that some outage causes
  and durations are unknown. It also documents occasional extreme SOG outliers
  and land-based coverage limits.
- U.S. Coast Guard [Class A reporting
  documentation](https://www.navcen.uscg.gov/ais-class-a-reports) states that
  underway position reports are normally transmitted every 2–10 seconds and
  anchored reports every 3 minutes. The Coast Guard's
  [Class A/Class B comparison](https://www.navcen.uscg.gov/sites/default/files/pdf/AIS_Comparison_By_Class.pdf)
  gives additional speed- and equipment-dependent intervals. NOAA's one-minute
  down-sampling reduces the raw frequency but does not make every vessel or
  receiver produce one equally spaced observation per minute.
- The [NOAA AIS FAQ](https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf)
  says NOAA track products are defined by MMSI, start/stop times and distance
  gaps. This establishes that track breaks require explicit choices; it does
  not select a gap that fits this source, grid or question.
- The [NOAA AIS FAQ](https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf)
  defines its annual transit-count grid as the number of unique tracks passing
  through a cell, not the number of AIS messages. Because the track definition
  uses break rules, sensitivity of a transit count to track segmentation is an
  inference rather than a source-defined invariant.

### Verified from authoritative or peer-reviewed methods

- An [International Whaling Commission technical
  paper](https://iwc.int/public/documents/1Y-Rv/SC-63-BC4.pdf) distinguishes
  vessel count per area, transit rate and distance travelled per area per time.
  It identifies calculating the actual distance travelled by each vessel in
  each grid square from successive AIS positions as the more precise track
  method. This supports the traffic-measure definition only; this project does
  not adopt that paper's collision model or make a probability claim.
- Kim et al. (2022), [Maritime Traffic Evaluation Using Spatial-Temporal
  Density Analysis Based on Big AIS
  Data](https://doi.org/10.3390/app122111246), explains that message-count
  methods are affected by irregular AIS intervals. It constructs consecutive
  point segments, splits them across cells, and allocates segment time by the
  fraction of segment length in each cell. That method supports vessel-hours as
  a coherent presence measure when its interpolation assumptions are accepted.
- Kapsar et al. (2022), [North Pacific and Arctic marine traffic dataset
  (2015–2020)](https://doi.org/10.1016/j.dib.2022.108531), reports both unique
  vessels and total track length by cell. The authors explain that unique-vessel
  counts do not represent residency or repeated activity, then construct daily
  tracks and intersect them with grids to obtain distance travelled. Their
  thresholds and daily segmentation belong to their data and are not imported
  into this project.

### Observed in the existing partial sample

The retained 15 July M2 window had median consecutive-observation gaps of 175
seconds for all Southern California vessels, 71 seconds for the selected
commercial types, and 70 seconds for selected commercial observations with
reported SOG at least 1 knot. The current cleaner smoke run found one additional
exact duplicate and four conflicting-key rows among 2,495 selected commercial
rows before deduplication.

Those observations demonstrate variable gaps and exercise the duplicate
policy. They describe an approximately half-hour source prefix at one time of
day, not a complete day or the analytical period. They do not select a maximum
gap or plausibility threshold.

### Inferred

- Raw point counts would partly measure reporting opportunity and reception,
  not only vessel activity. Applying a correction would require an unsupported
  reporting-rate and receiver-coverage model.
- Distance travelled is the clearest primary measure of commercial movement.
  It counts repeated visits, gives stationary observations zero movement, and
  has physical units that can be conserved when a track crosses cells.
- Distinct MMSI and MMSI-date counts remain useful descriptive context because
  they distinguish many vessels from repeated use by fewer vessels, but they do
  not replace a movement measure.

### Still unverified

- An isolated evidence harness now exercises the proposed code shape with
  synthetic cleaned bundles and exact synthetic grid geometry. That verifies
  deterministic pairing, diagnostic arithmetic, candidate-value plumbing,
  projected/geodesic comparison, and segment-piece conservation; it is not
  complete-day or period evidence and selects no production parameter.
- No complete scoped day has been used to measure consecutive gaps, implied
  speeds, edge-censored tracks, excluded-segment rates or the sensitivity of
  vessel-kilometres to candidate rules.
- No maximum interpolation gap or implied-speed plausibility threshold has an
  accepted evidentiary basis.
- The current cleaner removes positions outside the map/context extent before
  track construction. It therefore cannot reconstruct the unobserved portion
  of a segment entering or leaving that extent. Whether retrieval and cleaning
  should retain boundary-support observations, or whether edge segments remain
  explicitly censored, is unresolved.
- EPSG:3310 is the accepted equal-area grid CRS, not an equidistant CRS. The
  difference between its line lengths and WGS 84 geodesic lengths has not been
  quantified for complete-day segments.
- The optional minimum-length decision remains unresolved. The current
  type-only commercial selection is not equivalent to the program's
  approximately 300 GT condition.

## Candidate measures

| Measure | What it represents | Behavior and decision |
|---|---|---|
| Raw AIS point count | Received and retained messages in a cell | **Rejected as the primary measure.** It changes with reporting interval, receiver opportunity, gaps and down-sampling. Retain only as a processing diagnostic with its exact population. |
| Distinct MMSI count | Unique identified vessels observed in a cell during the period | **Supporting descriptive metric.** Less sensitive to repeated messages, but counts one brief crossing and repeated visits by the same vessel equally. Receiver non-detection still causes under-counting. |
| Distinct MMSI-date count | Unique vessel-days observed in a cell | **Supporting descriptive metric.** Captures repeated daily use better than period-wide MMSI, but not within-day revisits, distance or residency. |
| Vessel-hours | Interpolated presence time in a cell | **Not the primary measure.** It handles irregular reporting more coherently than point counts but emphasizes anchored, moored and slow presence. It also requires the same gap rule and a constant-progress assumption for cell allocation. Consider later as a separately named descriptive measure. |
| Transit count | Track entries or passages through a cell | **Not the primary measure.** Repeated visits are visible, but starts, stops and track breaks make counts sensitive to segmentation and cell geometry. NOAA's annual product remains a useful same-source arithmetic cross-check, not coverage evidence. |
| Vessel-kilometres | Sum of valid observed-track distance allocated inside a cell | **Proposed primary measure.** It measures movement, handles repeated visits additively, is less sensitive to message frequency than point counts, and can be split without assigning a whole crossing to one cell. |

The planned vessel-grid input carries both additive `vessel_km` and the derived
intensity `vessel_km_per_water_km2` for the fixed 153-day period, by vessel group
and for all selected groups combined. The latter divides by the grid's stored
`water_area_km2`, not the nominal 25 km² cell area. Despite the existing field
name, that area represents modeled-blue-whale support in the accepted source
mask; it is not an authoritative shoreline or AIS-coverage boundary. The
intensity's units are kilometres travelled per square kilometre of modeled
whale support, equivalent to km⁻¹ for this fixed period. Neither field is an
exposure value or a speed weight.

The same grid may carry `distinct_mmsi` and `distinct_mmsi_dates` as clearly
separate descriptive fields. A raw observation count belongs in quality and
diagnostic output, not in the vessel-activity surface. Vessel-hours are not
included unless a later decision gives that output a purpose and resolves its
stationary and gap treatment.

## Proposed decision

Use **vessel-kilometres from valid consecutive-observation segments** as the
primary commercial vessel-activity measure. Split every valid segment across
the exact EPSG:3310 modeled-whale-support geometries and allocate only the
length within each support geometry. Preserve passenger, cargo and tanker
groups. Retain distinct-vessel descriptors and reported-SOG data separately.

This record remains **Proposed** because track distance cannot be implemented
without a maximum interpolation gap, an implied-speed plausibility rule and an
explicit edge-support treatment. Choosing numeric values merely to make the
pipeline run would turn assumptions into facts.

## Future segment-construction design

### Ordering and identity

1. Read every verified daily cleaned Parquet for the accepted period into one
   bounded DuckDB relation. Validate the complete expected-date manifest first.
2. Sort deterministically by `mmsi`, `observed_at_utc`, `latitude`,
   `longitude`, `vessel_type_code` and `vessel_type_group`. ADR 0013 guarantees
   no repeated MMSI/timestamp key reaches this stage; assert that invariant
   again.
3. Within each MMSI, pair each observation with the chronologically next one
   across the whole period. Do not partition tracks at a UTC day boundary.
4. Give each candidate segment a deterministic identifier derived from MMSI,
   both timestamps, both coordinates and both vessel-group values. A segment is
   eligible to be allocated once and only once, regardless of output
   partitioning or reruns.

### Valid and excluded segments

A candidate is valid only when:

- timestamps increase strictly;
- both positions and the coordinate transformation are valid;
- both endpoints retain the same documented vessel group;
- elapsed time does not exceed the future accepted maximum gap; and
- implied endpoint-to-endpoint speed does not exceed the future accepted
  plausibility threshold.

The implementation must not substitute reported SOG for implied speed or vice
versa. Reported SOG is an endpoint attribute; implied speed is a track-quality
check derived from distance and elapsed time.

Each exclusion receives exactly one primary reason under a stable precedence,
with counts and candidate distance/time retained in the quality report:
non-increasing time, vessel-group change, invalid transformation, excessive
gap, implausible jump, or outside-period support. Counts must reconcile with all
candidate segments. Source-point removals remain in the upstream cleaning
report rather than being counted again.

Identical consecutive coordinates produce a valid zero-length segment and zero
vessel-kilometres. Record their count and elapsed time; do not invent a minimum
SOG or movement threshold. Near-stationary observations contribute their small
geometric distance unless a later accepted positional-jitter method says
otherwise. An implausible jump is excluded by the explicit future rule and is
never repaired by drawing a shorter invented path.

### Day and extent boundaries

- A segment spanning midnight inside 1 July–30 November is treated exactly like
  any other consecutive pair. Unioning dates before `lead` construction avoids
  both a false break and double-counting.
- No track is extrapolated before the first in-period observation or after the
  last. Those endpoints are period-censored and reported.
- With the current map-scoped cleaner, no line is extrapolated to the spatial
  boundary from the first or last retained point. Track starts and ends without
  an adjacent retained observation are edge-censored and reported. Their
  omitted distance is unknown.
- Before acceptance, choose between retaining a bounded ring of support
  observations through a revised pre-segmentation contract and keeping the
  explicit edge censoring. Any support extent is a processing aid, not an
  analytical or offshore-coverage boundary, and needs its own stated basis.

### Splitting across modeled-whale-support geometry

1. Construct a straight segment between each valid consecutive pair and
   transform it with explicit x/y ordering to EPSG:3310. The straight-line
   assumption applies only within the accepted maximum gap.
2. Intersect that line with each crossed grid row's exact modeled-whale-support
   geometry, not its nominal square or centroid. Allocate only the segment
   portion inside that support geometry. Report portions outside it separately;
   do not interpret them automatically as land, dry area or absent AIS
   coverage.
3. Emit one or more pieces keyed by `segment_id`, `cell_id` and deterministic
   piece order. Carry vessel group, parent elapsed time, endpoint reported SOG,
   parent projected length and piece projected length.
4. Sum piece metres by `cell_id` and vessel group, then divide by 1,000 for
   `vessel_km`. Derive `vessel_km_per_water_km2` only from the modeled-support
   area stored in `water_area_km2`. State the fixed period with the units.
5. Validate that pieces from one segment do not overlap each other and that
   their summed length equals the parent segment's intersection with the union
   of modeled-whale-support geometries within numerical precision. Report the
   parent length outside modeled-whale support separately. This conservation
   check prevents whole-segment and per-cell double-counting.

EPSG:3310 projected metres are the proposed recorded distance basis because
they are the coordinates used for the actual split. The complete-day evidence
run must compare them with WGS 84 geodesic distances and report the relative
difference. If the difference is material to a 5 km cell result, the record is
revised to calculate geodesic length for the split-piece vertices while keeping
the overlay in EPSG:3310.

### Descriptive metrics kept separate

- `distinct_mmsi` is the count of unique MMSIs with at least one retained
  cleaned point inside the cell's modeled-whale-support geometry during the
  period. `distinct_mmsi_dates` is the count of unique `(MMSI, UTC date)` pairs
  with at least one such retained point. Points outside the support geometry are
  counted and reported, not silently snapped or classified as land.
- The segment table retains endpoint `sog_knots` and the point-to-cell relation
  retains valid and unavailable reported-SOG counts. A later speed-summary
  contract must state whether its summaries are observation-, segment-, time-
  or vessel-weighted. This record selects none of those and never multiplies
  vessel-kilometres by SOG.
- Results remain split by `vessel_type_group`. Additive measures such as
  `vessel_km` produce an all-commercial value by exact summation of passenger,
  cargo and tanker values. All-commercial `distinct_mmsi` and
  `distinct_mmsi_dates` are recomputed from the union of retained commercial
  points; they are not sums of group counts because one MMSI may appear in more
  than one group.

## Threshold and evidence register

| Choice | Status after this record | Evidence needed |
|---|---|---|
| Maximum interpolation gap | **Unresolved; required before production segments.** | Complete-day and then period-wide consecutive-gap distributions by vessel group; sensitivity of total and per-cell vessel-km; a rationale tied to source sampling and route geometry. NOAA tool defaults are comparison values, not the answer. |
| Implied-speed plausibility threshold | **Unresolved; required before production segments.** | Complete-day outlier inspection, authoritative vessel-performance or AIS-quality literature appropriate to these commercial groups, and period-wide sensitivity. Reported SOG is a cross-check, not ground truth. |
| Minimum vessel length | **Unresolved in the upstream population.** | A defensible relationship to the program population or a documented type-only scope plus sensitivity. No length is treated as 300 GT. |
| Reporting-rate correction | **Not applied.** | Vessel-km does not require message counts to be proportional to activity. Any future correction would require an explicit receiver/reporting model and a new decision. |
| Minimum movement/SOG | **Not selected.** | Zero distance naturally contributes zero; no speed filter is needed for the primary measure. Positional-jitter treatment would require separate evidence. |
| Offshore coverage boundary | **Unresolved in ADR 0002.** | Independent coverage evidence. Vessel aggregation over the map extent does not settle observability or authorize statistics there. |
| Exposure weighting and high-exposure threshold | **Out of scope and unwritten.** | Wait for the grid-aligned inputs and accepted reporting domain in later milestones. |

## Evidence harness implementation status

The read-only `vessel_activity_evidence` module and its isolated CLI are
implemented. They require one explicit current cleaner bundle, verify its
contract and checksums, reorder observations deterministically by MMSI and UTC
timestamp, and construct consecutive pairs without reading raw AIS. The
deterministic ignored JSON report includes group and commercial-union
observation counts; union-recomputed distinct MMSI and MMSI-date counts; gap,
zero-length, group-change and non-increasing-time diagnostics; EPSG:3310 and
WGS 84 geodesic endpoint-distance comparisons; implied-speed distributions;
and separately named reported-SOG availability.

Maximum-gap, implied-speed-ceiling, and minimum-length candidate values have no
defaults and enter only through explicit repeatable runtime arguments. Their
sensitivity scenarios are labelled as candidate evidence, and the unfiltered
structural baseline remains visible. The harness does not accept or recommend a
numeric rule.

When an exact `projected_water_grid_v1` input is supplied, the optional
non-production path reuses the versioned grid and optional checksum validation,
projects with explicit x/y order, intersects lines with actual
modeled-whale-support cell geometry, reports in-support and outside-support
vessel-kilometres separately, and verifies conservation and no duplicate
allocation. It retains the unfiltered structural allocation as a baseline and
performs a separate allocation for every explicitly supplied candidate
scenario, using exactly that scenario's retained segment population. It does
not emit a per-cell vessel-activity dataset. Outside-support portions are not
interpreted as land, dry area, or absent AIS coverage.

Synthetic tests pass for the implemented boundary, including invalid grid CRS,
contract and checksum, candidate-scenario allocation, deterministic report
identity, overwrite and raw-output refusal, atomic failure, and CLI exits. This
implementation evidence does not resolve the items below. In particular, no
complete-day bundle was available on this branch, the real 15 July run did not
occur, vessel-hours and peak-memory comparison remain part of the bounded
evidence step, and the full-period gates remain open.

## Bounded next evidence step

After the user-authorized retrieval gate in
[ADR 0017](0017-prefer-accessais-with-guarded-bulk-fallback.md), use the
complete scoped **2024-07-15** artifact. AccessAIS currently estimates that
request at 582,454 rows and 59,895,276 bytes for the map/context bounds. If the
fallback is required, the complete national archive was reported as
395,954,655 compressed bytes during M2. Do not retrieve either in this decision
session.

The implemented harness is ready for this run after retrieval is merged. The
evidence run produces an ignored, checksum-bound report rather than a
production vessel grid. The complete bounded step must:

1. run the existing validator and one-date cleaner unchanged;
2. calculate candidate consecutive pairs after ADR 0013 cleaning;
3. report gap and implied-speed distributions by vessel group, including
   zero-length, group-change and edge-censored counts;
4. evaluate a clearly labelled range of candidate gap and plausibility rules
   without selecting one merely from that day;
5. compare raw point counts, distinct MMSI, MMSI-date, vessel-hours and
   vessel-kilometres on synthetic cells and the complete day;
6. split candidate valid segments over the exact modeled-whale-support
   geometries in a non-production evidence run and verify segment-length
   conservation and no duplicate segment allocation;
7. compare EPSG:3310 and WGS 84 geodesic segment lengths; and
8. record runtime, peak memory, excluded counts and sensitivity of per-cell and
   total vessel-kilometres.

The complete day resolves whether the proposed measure and code shape are
practical and identifies defensible candidate rules. It does **not** establish
their stability across 153 days. Acceptance also requires a stated threshold
rationale and edge-support treatment. The full period is required to validate
daily coverage, exclusion rates, threshold sensitivity, final vessel-group
distributions and reported-SOG availability before the vessel grid is called a
validated analytical input.

## Consequences

- Point-count heatmaps cannot become the Version 1 vessel input. Point counts
  remain valuable QA for missing or anomalous dates.
- A deterministic, conservation-tested segment-to-grid evidence process is now
  implemented with synthetic inputs while the numeric thresholds remain
  unresolved. It emits diagnostics only and cannot produce a production result
  using hidden defaults.
- The current cleaned files are sufficient for interior candidate segments but
  not for uncensored entry/exit portions. The future implementation must expose
  that limitation or revise the pre-segmentation boundary.
- ADR 0002 does not block construction of a vessel grid over the map extent. It
  still blocks treating the full extent as uniformly observable, combining it
  into a reportable exposure surface, or publishing inside-versus-outside
  statistics.
- The future output has physical traffic units and retained group detail. It is
  still a proxy for observed commercial movement, not collision probability,
  predicted strikes or a policy recommendation.

## Alternatives considered

**Raw point density or kernel density.** Rejected as the primary measure because
message opportunity and receiver coverage affect the result. A smoother map
would not remove that bias.

**Period-wide distinct vessels only.** Rejected as the primary measure because
one brief crossing and many repeated visits by one MMSI have the same count.
Retained as descriptive context.

**Vessel-hours as the primary measure.** Rejected for Version 1 because it
answers presence rather than movement and can emphasize anchorage or port
residence. It remains a legitimate separately named measure if a later question
needs it and the gap/stationary rules are accepted.

**Transit counts as the primary measure.** Rejected because starts, stops,
re-entry and track breaks make a transit definition more topology-dependent
than distance. NOAA's published transit surface remains a same-source
cross-check on route placement and aggregation arithmetic.

**Weight distance by reported SOG.** Rejected under ADR 0006. It would put speed
inside the activity input and silently change the meaning of the later overlap
measure.
