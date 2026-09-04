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
- NOAA's [AIS Track Builder user
  guide](https://coast.noaa.gov/data/marinecadastre/ais/AISTrackBuilder.pdf)
  documents a 30-minute default maximum time between sequential points and a
  separate one-statute-mile default maximum distance. These are defaults for a
  general track-building tool, not findings about this bounded extract or a
  rule selected for this project. Only the 30-minute value is exercised below;
  the evidence harness has no distance-gap rule.
- The Coast Guard's [AIS equipment-type
  documentation](https://www.navcen.uscg.gov/types-of-ais) states that Class A
  position reports are normally sent every 2--10 seconds while underway and
  every three minutes or less while anchored or moored. This supports treating
  multi-minute gaps as missing reception or reporting opportunities that need
  explicit handling. It does not establish how much straight-line
  interpolation is defensible after NOAA down-sampling or receiver loss.

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
- Coro et al. (2023), [Estimating hidden fishing activity hotspots from vessel
  transmitted data](https://doi.org/10.3389/fsufs.2023.1152226), derives gap
  regimes from its own AIS/VMS distributions: below 30 minutes, above 3.5
  hours, and an intervening reconstruction range. It explicitly says long-gap
  reconstruction is uncertain. Its fishing-vessel population and gap-filling
  objective differ from this project's passenger, cargo and tanker distance
  aggregation, so it supports distribution-led sensitivity rather than a
  transferable threshold.
- A 2026 peer-reviewed Tokyo Bay study, [High-Resolution Mapping of Port
  Dynamics from Open-Access AIS Data](https://doi.org/10.3390/geomatics6010010),
  iteratively removed inter-message speeds over 50 knots together with a
  separate acceleration rule. That 50-knot value is exercised only as a
  permissive comparison candidate. The study includes hydrofoil ferries and a
  port-movement objective, and its complete cleaning method is not reproduced
  here.

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

### Implemented bounded evidence and still unverified

- The bounded evidence harness now exercises the proposed code shape with
  synthetic cleaned bundles and exact synthetic grid geometry, including
  cached segment pieces, per-cell candidate aggregation, point/distinct-vessel
  context, and the separately named vessel-hours comparison. It also ran
  without candidate thresholds against the real bounded 2024-07-15 cleaned
  bundle and exact grid. This is one-day implementation evidence, not period
  evidence, and it selects no production parameter.
- The updated real baseline measured 113,799 observations, 113,620 structural
  segments, 77,887 cached in-support pieces, 1,303 touched grid cells, and
  passing distance, elapsed-time and no-double-allocation checks. Parent
  distance was 25,560.766048547 km: 24,096.858442602 km inside support and
  1,463.907605945 km outside. Parent vessel time was 3,672.903055556 hours:
  1,929.780498228 inside, 1,743.122557328 outside and zero unallocated. Point
  context classified 71,482 cleaned observations inside support, 42,316 outside
  and one as ambiguous. The maximum implied speed was 431,402.639804 knots. The
  extreme implied speed confirms that the unfiltered baseline is diagnostic
  only.
- The real gap distributions are concentrated near the source's down-sampled
  cadence but have long tails. For all commercial segments, the median was 70
  seconds, p95 183 seconds, p99 361 seconds, p99.9 1,079 seconds and maximum
  74,400 seconds. Counts above 300/1,800 seconds were 2,589/55 overall,
  comprising passenger 1,106/35, cargo 714/14 and tanker 769/6.
- Implied speed had commercial median 0.144447 knots, p95 13.981812, p99
  20.658558, p99.9 37.369922 and maximum 431,402.639804 knots. Counts above
  30/50 knots were 166/69 overall: passenger 84/9, cargo 70/49 and tanker
  12/11. The ten largest implied speeds ranged from 28,126 to 431,403 knots,
  despite endpoint reported SOG values of 5.2--20.0 knots where available;
  these are positional jumps, not credible vessel motion.
- Reported SOG was available on 113,755 of 113,799 observations (99.961%). Both
  endpoint values were available for 113,567 structural segments, exactly one
  was unavailable for 20, and both were unavailable for 33. Across the paired
  population, the impossible jumps reduce Pearson correlation between implied
  speed and mean endpoint SOG to 0.0104. Restricting this diagnostic comparison
  to implied speed at or below 50 knots gives 0.9842; the median absolute
  difference is 0.0547 knots and p95 is 0.4333 knots. This agreement supports
  using endpoint SOG as a cross-check, not as a substitute or as ground truth.
- All 113,620 consecutive pairs increased in time and retained one vessel
  group. There were zero non-increasing-time and zero group-change pairs.
  There were 9,053 zero-length pairs; they contribute zero vessel-kilometres
  and remain visible rather than receiving an invented movement rule.
- No maximum interpolation gap or implied-speed plausibility threshold has an
  accepted evidentiary basis.
- The current cleaner removes positions outside the map/context extent before
  track construction. It therefore cannot reconstruct the unobserved portion
  of a segment entering or leaving that extent. Whether retrieval and cleaning
  should retain boundary-support observations, or whether edge segments remain
  explicitly censored, is unresolved.
- EPSG:3310 is the accepted equal-area grid CRS, not an equidistant CRS. Across
  the structural baseline its 25,560.766049 km total was 2.935568 km lower than
  the WGS 84 geodesic total, a -0.011483% difference. Mean absolute pair
  difference was 0.074093 m, p95 was 0.340146 m and the maximum was 97.742585
  m. The candidate populations below differed by -0.010781% to -0.010899%.
  This one day gives no evidence that projected length is material at 5 km
  cell scale, but period-wide comparison remains required.
- The optional minimum-length decision remains unresolved. The current
  type-only commercial selection is not equivalent to the program's
  approximately 300 GT condition.

### Candidate-rule sensitivity on the bounded day

The matrix deliberately crosses only two gap and two implied-speed values. A
300-second gap is a project inference chosen just above the observed 183-second
p95/reporting cluster; it is not source-defined. The 1,800-second gap is NOAA
Track Builder's comparison default. A 30-knot ceiling is a project inference
just above this day's maximum available reported SOG of 26.6 knots. The
50-knot ceiling is the permissive peer-reviewed comparison above. No length
value was supplied because length is not gross tonnage and no defensible
mapping to the BWBS population was found.

Exclusions use the implemented precedence: maximum gap, then implied speed.
Vessel-hours remain an evidence-only comparison under constant progress. A
"materially changed" cell below means an absolute all-commercial difference of
at least 1 vessel-km from the unfiltered baseline; this is a transparent
reporting choice for this sensitivity review, not a production threshold.

| Maximum gap (s) | Speed ceiling (kn) | Retained / excluded segments | Parent vessel-km, passenger / cargo / tanker / all | In-support / outside-support vessel-km | Parent vessel-hours | Materially changed cells |
|---:|---:|---:|---:|---:|---:|---:|
| 300 | 30 | 110,865 / 2,755 (2.425%) | 4,872.170 / 6,664.394 / 3,550.756 / 15,087.320 | 13,794.137 / 1,293.183 | 3,098.637 | 392 (8.680% of 4,516; 30.084% of 1,303 baseline-touched) |
| 300 | 50 | 110,962 / 2,658 (2.339%) | 4,965.410 / 6,689.099 / 3,551.375 / 15,205.885 | 13,904.721 / 1,301.164 | 3,100.330 | 355 (7.861% of 4,516; 27.245% of 1,303 baseline-touched) |
| 1,800 | 30 | 113,399 / 221 (0.195%) | 4,920.097 / 6,763.482 / 3,572.958 / 15,256.537 | 13,951.683 / 1,304.854 | 3,413.416 | 369 (8.171% of 4,516; 28.319% of 1,303 baseline-touched) |
| 1,800 | 50 | 113,496 / 124 (0.109%) | 5,013.337 / 6,788.187 / 3,573.578 / 15,375.102 | 14,062.267 / 1,312.835 | 3,415.109 | 333 (7.374% of 4,516; 25.556% of 1,303 baseline-touched) |

All four scenarios passed distance, elapsed-time and no-double-allocation
conservation. Relative to the 25,560.766049 km baseline, they retain only
59.025%--60.151% of parent distance while excluding 0.109%--2.425% of
segments. Thus a very small number of implausible jumps dominates roughly 40%
of unfiltered distance. Every candidate removes the 431,402.639804-knot
maximum; the 30-knot cases remove 166 implied-speed exceedances after the gap
rule and the 50-knot cases remove 69. The 300-second gap additionally removes
2,589 segments before speed evaluation, versus 55 at 1,800 seconds.

The largest cell decrease was 101.744333 vessel-km in every scenario. Counting
any change above 1e-9 vessel-km, rather than the stated 1-km materiality rule,
gives 482, 420, 432 and 365 changed cells in table order. Candidate effects are
therefore spatially material even though the excluded segment share is small.
Outside-support distance also changes materially, from 1,463.907606 baseline
vessel-km to 1,293.182879--1,312.835239; these quantities mean only outside the
modeled-whale-support geometry.

The deterministic `vessel_activity_evidence_v2` / processing version `2.0.0`
candidate report has path-independent ID
`vessel-evidence-c3f562e751b10e6e4199f67f`, size 6,240,164 bytes and SHA-256
`0c33f2eedd612e976e476d687e6298b78bb86b06c7b9f87640bb0a2d46906c1b`.
Two clean output paths reproduced the exact ID, checksum and bytes. The CLI
reported 43.015664 and 35.236685 seconds from its documented internal runtime
protocol; these are run observations, not a benchmark. Inputs were cleaner run
`ais-362502c6a37b53e681b745f5`, cleaned-Parquet SHA-256
`efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`,
and water-grid SHA-256
`7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`.

### Edge support

The current map-scoped cleaner censors positions before track construction.
Consequently, the first and last retained point for each MMSI cannot reveal
whether an adjacent point was outside the map, outside the one-day window, or
simply absent. This bundle has 358 endpoint observations (two for each of 179
MMSIs) and no single-observation MMSI, but that count does not apportion causes
or estimate omitted distance.

Two treatments remain candidates. A bounded support ring retained through a
revised pre-segmentation contract could permit segments to be clipped at the
map boundary, but its width must be justified against the accepted maximum gap
and plausible travel distance, and retrieval/cleaning must preserve its
lineage. Keeping the current censoring avoids inventing boundary crossings but
systematically omits unknown entry/exit distance and must remain explicit in
outputs. This one bounded day contains no outside-ring observations, so it
cannot compare the alternatives or resolve the issue. Period-wide testing
needs a deliberately retrieved ring and a matched censored run.

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
diagnostic output, not in the vessel-activity surface. The evidence harness now
reports vessel-hours for comparison under explicit provisional semantics; that
does not include vessel-hours in the planned production grid or resolve its
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
| Offshore coverage boundary | **Accepted in ADR 0002 as `receivers_50_nautical_miles`.** | The system-performance-qualified receiver domain is not empirical 2024 coverage; vessel aggregation over the map extent does not upgrade its observational completeness. |
| Exposure weighting and high-exposure threshold | **Out of scope and unwritten.** | Wait for the final grid-aligned inputs and later M6 method decision. |

## Evidence harness implementation status

The read-only `vessel_activity_evidence` module and its isolated CLI implement
the bounded non-production evidence foundation. They require one explicit
current cleaner bundle,
verify its contract, cleaned-Parquet and quality-report checksums, and shared
sidecar cleaner run identity, reorder observations deterministically by MMSI and
UTC timestamp, and construct consecutive pairs without reading raw AIS. The
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
projects with explicit x/y order, and intersects each structural segment with
actual modeled-whale-support cell geometry once. Its reusable parent/piece
representation retains stable parent identity, group, elapsed time, parent and
piece distance, cell and piece order, outside-support distance, and explicit
zero-length/outside/ambiguous status. The unfiltered baseline and every explicit
candidate scenario filter and aggregate that same cache instead of repeating
Shapely intersection work.

Every population reports every target cell in stable order, including zeros,
with segment-piece count and passenger, cargo, tanker and additive commercial-
union vessel-kilometres and vessel-hours. Positive-length time uses the explicit
constant-progress assumption and piece/parent projected-length fraction.
Coincident zero-length time is assigned only for exactly one support cell; no
match is outside-support time and multiple matches remain unallocated. Distance
and time conservation are checked at parent and aggregate levels.

Separately, every cleaned observation is classified against exact support
geometry. Per-cell observation, distinct-MMSI and distinct-MMSI-date counts are
reported by group and with union-recomputed all-commercial distinct counts;
outside-support and ambiguous point counts remain separate. This cleaned-point
population is not candidate filtered. The per-cell values are diagnostics
inside the ignored JSON report, not a production vessel-activity dataset.
Outside-support portions are not interpreted as land, dry area, or absent AIS
coverage.

Synthetic tests pass for the implemented boundary, including bundle-sidecar
integrity; invalid grid CRS, contract and checksum; exact distance/time splits;
partial outside support; all zero-length placement states; group-additive and
union-distinct totals; candidate cache reuse without repeated intersections;
reordered observations and candidate values; path-independent report identity;
overwrite and raw-output refusal; atomic failure; and CLI exits. Local input
paths remain execution provenance but do not enter `report_id`.

The author exercised the updated harness against the real bounded 2024-07-15
cleaned bundle and exact grid on 2026-08-28 without any candidate threshold
arguments. It processed the counts and quantities recorded under "Still
unverified" above. The 2,166,881-byte report contains 4,516 stable allocation
rows and 4,516 stable point-context rows; 1,303 cells were touched by an
allocated segment piece. The unfiltered baseline cannot become a production
result without an evidence-supported plausibility rule.

The durable identity of that evidence run is:

| Identity field | Value |
|---|---|
| Report contract / processing version | `vessel_activity_evidence_v2` / `2.0.0` |
| Path-independent report ID | `vessel-evidence-8432d5193107b94d88873201` |
| Exact local report SHA-256 | `60e6a02be98d8cf5edd45af56a5adcfac001681a71e868dd438c4db0894a4d6e` |
| Cleaned input SHA-256 | `efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6` |
| Cleaner run ID | `ais-362502c6a37b53e681b745f5` |
| Exact water-grid SHA-256 | `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031` |
| Candidate thresholds | None supplied; this was the unfiltered structural baseline only. |

The report ID excludes local filesystem paths and identifies deterministic
evidence content. The report SHA-256 identifies the exact local JSON bytes,
including their non-identity local provenance metadata. A second clean output
reproduced both identities.

The harness-recorded processing interval inside `run_evidence` was 25.007583
seconds. It begins after Python imports, CLI parsing and configuration loading
and is not an end-to-end CLI runtime. A separate deterministic process-tree RSS
sampling protocol took 59.562371 seconds and observed an approximate 309.441
MiB peak. These observations used different protocols; sampling may have
contributed overhead, but the measurements do not isolate its effect.
Independent end-to-end CLI runs took approximately 64.4 and 66.4 seconds while
reproducing the exact report.

Against the prior aggregate-only implementation's 228.968-second observation,
the measurements provide directional evidence of improved runtime, not a
generally reproducible speedup factor. Against the earlier approximate 243 MiB
working-set measurement, memory regressed by about 66 MiB (27%); different
approximate sampling methods make that directional rather than exact. No
one-day measurement is extrapolated linearly to 153 days.

### Real two-day candidate-grid execution

On 2026-09-01, the focused multi-day boundary was exercised against the exact
author-supplied 2024-07-15 through 2024-07-16 AccessAIS delivery and exact water
grid. Fresh intake reproduced period ID
`multiday-ais-ddf23ba501bc834dbe5a2656` and the existing daily cleaner identities
and Parquet checksums. All 1,135,408 delivery rows were assigned, with zero
malformed/unassignable or out-of-request rows. The resulting 218,305 cleaned
observations formed 218,089 whole-period structural pairs, including 160
cross-date/cross-midnight candidates that daily-partitioned pairing would have
lost.

All runs explicitly used `allow-incomplete-candidate`,
`censor-at-cleaned-extent`, `exact-water-geometry-exclude-and-report`, a 2 GB
DuckDB limit, an isolated ignored spill directory, the verified grid checksum,
and no length filter:

| Maximum gap (s) | Speed ceiling (kn) | Retained / excluded segments | Gap / speed exclusions | Allocated vessel-km, passenger / cargo / tanker / all | Outside-support vessel-km | Positive-distance cells |
|---:|---:|---:|---:|---:|---:|---:|
| 300 | 30 | 211,622 / 6,467 | 5,457 / 1,010 | 7,891.472 / 10,576.066 / 6,656.298 / 25,123.836 | 2,450.085 | 1,659 |
| 300 | 50 | 211,803 / 6,286 | 5,457 / 829 | 8,048.168 / 10,615.410 / 6,662.404 / 25,325.982 | 2,466.442 | 1,660 |
| 1,800 | 30 | 216,694 / 1,395 | 352 / 1,043 | 8,132.621 / 11,052.656 / 6,871.961 / 26,057.238 | 2,524.340 | 1,679 |
| 1,800 | 50 | 216,877 / 1,212 | 352 / 860 | 8,289.317 / 11,126.251 / 6,878.068 / 26,293.635 | 2,540.696 | 1,680 |

Raising the speed ceiling changed 137 or 140 cells and added one
positive-distance cell within each gap case. Raising the gap changed 305 cells
and added 20 positive-distance cells within each speed case. All reports passed
their own validation and distance-conservation checks. Invalid intersection
geometry and positive-length boundary ambiguity were zero; each run retained
one ambiguous cleaned point. All four candidate executions were repeated, and
each reproduced its exact candidate ID, GeoParquet bytes, and deterministic
quality-report bytes. Time-bearing lineage metadata changed as intended.

The exact four GeoParquet outputs were inspected in QGIS 4.2.1 on 2026-09-01 at
the full domain, shipping-lane concentrations, support edges, zero/nonzero
cells, and contextual VSR boundary. Corrected renders placed the blue accepted-
domain and orange VSR outlines above the candidate grids; exact RGB checks and
manual review confirmed both outlines were visible in every image. Grid
geometry and corridor patterns aligned;
no projection shift, geometry gap, unexplained clipping, or anomalous band was
found. The longer-gap additions were more visible than the speed-ceiling
differences. This visual inspection establishes no analytical completeness or
policy conclusion.

This execution covers only 15--16 July 2024, through its own separate two-date
period manifest, which stood at two compatible and 151 missing dates. The
separate accumulation-gate manifest has since reached all 153 dates, but this
matrix was never rerun against it. Source-transfer
completeness and observational completeness remain `unverified`; no production
maximum-gap or implied-
speed rule was selected; and no final vessel-activity input or exposure
analysis was produced. The two-day matrix is candidate sensitivity evidence and
is not sufficient to settle this Proposed decision.

## Remaining decision evidence

The implemented foundation supports the remaining research without repeating
geometry cost. Before this decision can be accepted, later evidence must:

1. repeat the 300/1,800-second and 30/50-knot matrix across the accepted period,
   retaining daily and vessel-group distributions so seasonal or source-quality
   changes cannot be hidden in one total;
2. review projected-versus-geodesic differences and excluded populations
   period-wide; the bounded-day difference is immaterial, but it is not a
   period guarantee;
3. retain source-transfer and observational completeness as unverified unless
   independent evidence establishes otherwise; and
4. establish a threshold rationale and edge-support treatment, then validate
   exclusion rates, sensitivity, vessel-group distributions, and reported-SOG
   availability across the accepted period before producing a vessel grid.

The bounded one-day harness and two-day candidate-grid executions establish
that the implemented subset is executable. They do not complete the measure
comparison, select a rule, establish stability across 153 days, or validate a
production analytical input.

All four combinations deserve period-wide testing: the two gap values bracket
a locally inferred short-gap treatment and NOAA's tool default, while the two
speed values test a locally inferred ceiling against a permissive published
comparison. The 30/50-knot difference changes 97 retained segments and about
111--119 parent vessel-km within each gap case; the 300/1,800-second difference
changes vessel-hours much more strongly. The resulting per-cell changes are
large enough that this one day cannot justify dropping either axis. This is a
testing conclusion, not acceptance of any threshold.

## Consequences

- Point-count heatmaps cannot become the Version 1 vessel input. Point counts
  remain valuable QA for missing or anomalous dates.
- A deterministic, conservation-tested segment-to-grid evidence process is
  verified with synthetic inputs, exercised by the one-day evidence harness,
  and exercised by the multi-day candidate boundary on two real bounded dates
  while the numeric thresholds remain unresolved. Its candidate bundles stay
  under ignored derived storage and cannot become a production result using
  hidden defaults.
- The current cleaned files are sufficient for interior candidate segments but
  not for uncensored entry/exit portions. The future implementation must expose
  that limitation or revise the pre-segmentation boundary.
- ADR 0002 accepts the reporting domain but does not change construction of a
  vessel grid over the map extent. The full extent still must not be treated as
  uniformly observable: outside-domain cells are excluded from future headline
  statistics, not classified as low traffic.
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
