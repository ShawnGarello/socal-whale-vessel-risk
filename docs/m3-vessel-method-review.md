# M3 vessel-method review

2026-09-04. Supporting evidence for ADR 0018, which remains Proposed.
These observations concern the checksum-verified ready period
`multiday-ais-17e982f999f7093945193378`; they do not establish transfer or
observational completeness.

## Cleaner and flagged-date review

All 153 cleaner sidecar identities were rehashed and matched their manifest.
The retained period evidence has SHA-256
`1b90ebd4e8d340cdb09709557d154f5b55f7882cba8cbc08b548958edbb25ff4`.
The additional reproducible diagnostic script is
`analysis/scripts/m3_completion_diagnostics.py`; its exact profiled command
and output are recorded in the session handoff.

The 82,619,482 source rows include 15,465,734 selected commercial rows before
deduplication. Removing 4,776 conflicting rows and 2,391 exact duplicates leaves
15,458,567 cleaned observations. No source row was removed for invalid SOG or
outside-map position; the supplied requests were already map bounded.

| Flagged UTC date | Source rows | Selected commercial before deduplication | Cleaned | Conflicting / duplicate rows |
|---|---:|---:|---:|---:|
| 2024-09-24 | 456,715 | 81,528 | 81,404 | 102 / 22 |
| 2024-09-29 | 416,162 | 61,610 | 61,513 | 86 / 11 |
| 2024-10-14 | 537,230 | 86,769 | 86,689 | 78 / 2 |
| 2024-11-24 | 376,914 | 64,289 | 64,268 | 6 / 15 |
| 2024-11-25 | 400,295 | 75,084 | 75,021 | 16 / 47 |
| 2024-11-28 | 420,617 | 71,891 | 71,841 | 18 / 32 |

Deduplication does not explain the large daily differences. September 29 has
4,240 cleaned commercial observations at 18 UTC, then 1,128 / 36 / 23 / 0 / 308
at 19 through 23 UTC. Every other flagged date has observations in every hour
for all three vessel groups. These are facts about the retained population.
The September 29 pattern is consistent with a collection/feed interruption,
but this diagnostic cannot attribute a cause or quantify absent vessels.
It does not establish missing coverage from low row counts.

The [NOAA AIS FAQ](https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf),
rechecked 2026-09-04, identifies both vessel-traffic variation and sensor-network
interruptions as reasons for file-size differences; outage cause and duration
typically are not supplied with the feed. No date is removed or reweighted in
response to these counts. Such a correction would need unsupported knowledge
of what was not received.

## Gap and speed rationale under review

[USCG Class A documentation](https://www.navcen.uscg.gov/ais-class-a-reports),
rechecked 2026-09-04, describes 2–10-second underway transmissions and
three-minute anchored transmissions. NOAA describes minute downsampling.
Neither specifies a universally valid interpolation gap for this analysis.
The 300-second value remains a project choice limiting unobserved route
interpolation; 1,800 seconds remains the comparison default recorded in ADR 0018.
The Track Builder PDF could not be reopened through the web tool in this
session; its previously recorded source finding was not newly verified.

For gaps at most 300 seconds, the additional 30–50-knot band has 6,754
passenger, 5,886 cargo and 777 tanker segments. Both endpoint SOG values exist
for 6,751 / 5,886 / 777 respectively. Only 103 passenger segments and no cargo
or tanker segments agree with the endpoint mean within 5 knots; 101 passenger
segments agree within 2 knots. Fifty passenger segments have both SOG values
above 30 knots. With gaps above 300 and at most 1,800 seconds, none of the
142 / 164 / 70 additional 30–50-knot segments agrees within 5 knots.

Agreement bands of 2 and 5 knots are diagnostic choices, not accepted quality
filters. Reported SOG and implied speed share possible position/GPS errors;
agreement is not independent validation. Some passenger movement above 30 knots
may be credible. A universal 30-knot ceiling would knowingly exclude that small
population along with many discordant jumps. The 50-knot comparison admits
substantial discordant movement. Spatial comparison remains required before
choosing either tradeoff. Neither rule is preferred for retaining more distance.

## Common spatial-matrix treatment

Use `censor-at-cleaned-extent` and
`exact-water-geometry-exclude-and-report` for every candidate, on water-grid
SHA-256 `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`.

Explicit censoring is supportable for the stated observed-movement proxy:
there is no extrapolation before/after retained tracks or beyond the period.
An outside support ring would answer a different, uncensored boundary question
and require new retrieval and cleaner lineage. It is not necessary to compare
the four existing candidates on their common censored population. Its absent
observations cannot be recovered from the current inputs, so omitted entry/exit
distance remains unknown. Short unobserved exits and re-entries between retained
points are also possible; a straight segment cannot recover their path.
Production acceptance must carry these limitations explicitly, especially at
the northern and southern map edges. No ring is fabricated or requested here.

As a limited edge diagnostic, retained 300-second/30-knot parents starting
within 0.05 degrees of a map edge contribute 31,344.147 parent km of
2,257,826.775 parent km (about 1.39%). This geographic band is an analyst-chosen
proximity diagnostic, not a uniform metric-width buffer, allocated cell
distance, lost-distance bound, or proof that censoring is immaterial.

The receiver domain remains the system-performance-qualified domain from
ADR 0002, not observed coverage. It is applied downstream to headline statistics,
not substituted for modeled-whale support during vessel-grid construction.

## Type-only population treatment

Retain passenger 60–69, cargo 70–79 and tanker 80–89 without a length filter.
This explicitly describes selected commercial types, not BWBS eligibility,
participants, or vessels over 300 GT. A length threshold cannot implement a
tonnage condition and would disproportionately change the passenger population.

Of 6,399,537 passenger observations, 474,469 have length below 20 m,
5,552,611 have length 20–50 m, 73,813 have length 50–100 m, 298,637 have
length at least 100 m and seven are null. A 100 m filter would retain only
about 4.67% of passenger observations. Cargo has 5,281,507 observations at
least 100 m, 672,315 below 100 m and 21,419 null. Tanker has 3,056,812 at
least 100 m and 26,977 null. These are observation-weighted population
diagnostics; they are not distance sensitivity or vessel-size truth.
Length zero stays in its recorded band and is not represented as a measured
zero-length vessel. No rule maps these lengths to gross tonnage.

## Status

The diagnostic artifact is
`data/interim/m3-completion-diagnostics-second/run/diagnostics.json`, SHA-256
`aace97dd777e3b87350c1808e1d4ff00b66ab6e723d941d232fd493236265656`.
It is non-spatial and needs no QGIS inspection.

Updated 2026-09-05: the full-period spatial sensitivity evidence this review
called for **has since been produced**. The four-candidate matrix ran against the
ready 153-date period, each candidate reproduced its bytes exactly, all six
candidate pairs were compared per cell, and the outputs were inspected in QGIS.
See `analysis/README.md` and the [session handoff](m3-completion-handoff.md).

Still outstanding: threshold selection is **not** recorded, and a truthful
final-input boundary, speed summaries, their reproduction and their spatial
verification do not exist. ADR 0018 and M3 remain open.
