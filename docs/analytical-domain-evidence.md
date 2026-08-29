# Analytical-domain evidence

**Scope:** reproducible evidence for proposed [ADR 0002](decisions/0002-southern-california-study-area-extent.md). This is not a production domain contract and does not produce exposure or inside/outside exposure statistics.

## Outcome

The evidence materially narrows the decision but does not support accepting one analytical domain.

- NOAA's current AIS FAQ says public NAIS coverage is generally unavailable beyond "40 to 50 miles" from the coast, but it does not identify statute or nautical miles and does not say that all water inside the stated distance was observed.
- Older official NAIS material describes the planned offshore extent as about 50 nautical miles, while the current source deliberately remains unitless. The calculation therefore retains the ambiguity rather than silently resolving it.
- NOAA's 2024 AIS Base Stations source places nine NAIS stations in the expanded Southern California processing filter, including Catalina, San Nicolas, and San Clemente Islands. Its metadata says completeness is untested and provides no antenna height, operational interval, outage history, terrain, or reception footprint.
- A coastline buffer is reproducible but not receiver geometry. A receiver buffer is physically closer to the collection system but requires an unsupported reception radius and assumes the published station inventory was complete and operating during the 2024 analytical period.

Consequently, none of the eight masks below is called an observed or reliable-coverage domain. They are sensitivity scenarios only. ADR 0002 remains Proposed.

## Authoritative inputs

### NOAA NGS Continually Updated Shoreline Product

The selected coastline is NOAA National Geodetic Survey's Continually Updated Shoreline Product (CUSP), West region. NOAA describes CUSP as its available contemporary high-resolution national shoreline and requests NOAA credit. The source has no access restriction; its limitations include that shoreline is a time-specific representation and source completeness may vary.

- Metadata: <https://www.fisheries.noaa.gov/inport/item/60812>
- Download: <https://geodesy.noaa.gov/dist_shoreline/West.zip>
- Retrieved: 2026-08-28
- Local ignored file: `data/raw/noaa-ngs-cusp-west/West.zip`
- Bytes: 42,501,564
- SHA-256: `53da33c37f6385fb7b64c59d96371b91eaa73b6e6c837e1f18147a8354015b85`
- HTTP metadata: `Last-Modified: Wed, 05 Aug 2026 16:46:26 GMT`; `Content-Type: application/zip`
- Format and CRS: Shapefile, 82,963 LineStrings, EPSG:4269 (NAD83)
- Evidence subset: 13,435 lines touching the explicit expanded filter
- Transformation: EPSG:4269 to EPSG:3310 with fixed x/y order; lines simplified by at most 25 m before buffering. The parameter is explicit and below one percent of a 5 km cell.

CUSP replaces the whale-model edge for distance-from-coast evidence. It does not replace the accepted whale-model support mask used to construct the grid.

### NOAA Office for Coastal Management AIS Base Stations

NOAA states that this source derives NAIS and LOMA station identity and location from U.S. Coast Guard Light Lists. The dataset date is 2024-08-01, matching the analytical year. NOAA reports 10 m horizontal accuracy at 95% confidence, logical consistency, and untested completeness. Use is constrained to coastal and ocean planning.

- Metadata: <https://www.fisheries.noaa.gov/inport/item/73206>
- Download: <https://marinecadastre.gov/downloads/data/mc/AISBaseStation.zip>
- Retrieved: 2026-08-28
- Local ignored file: `data/raw/noaa-ais-base-stations/AISBaseStation.zip`
- Bytes: 21,061
- SHA-256: `8b317017783fd654a918e6cbf78edfea0d9df9eb6630157c019de7ddfa513003`
- HTTP metadata: `Last-Modified: Thu, 01 Aug 2024 16:25:30 GMT`; `Content-Type: application/x-zip-compressed`
- Format and CRS: GeoPackage, 290 valid points, EPSG:4269; 136 `NAIS` and 154 `LOMA`
- Expanded-filter NAIS sites: Cambria, Catalina Island, Honda Ridge, Laguna Peak, Point Loma, Post Ranch, San Clemente Island, San Nicolas Island, and San Onofre Peak
- Transformation: EPSG:4269 to EPSG:3310 with fixed x/y order

The current [NOAA AIS FAQ](https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf) points users to this dataset for station locations. The [USCG explanation of AIS range](https://www.navcen.uscg.gov/how-ais-works) says range depends principally on antenna height and gives a nominal 20 nautical miles at sea; it does not define a NAIS receiver footprint. Station points therefore support a geometry sensitivity test, not an empirical coverage surface.

## Reproducible calculation

Run from `analysis/` after obtaining the four ignored source artifacts:

```text
python -m uv run --locked python -m whale_vessel_analysis.domain_evidence_cli --config evidence/domain-candidates.toml --grid ..\data\interim\m2-domain-evidence\noaa-whale-footprint-water-grid.parquet --shoreline-archive ..\data\raw\noaa-ngs-cusp-west\West.zip --station-archive ..\data\raw\noaa-ais-base-stations\AISBaseStation.zip --vsr ..\data\raw\bwbs-vsr-2026\bwbs_ca_vsr_zone_2026.geojson --report ..\data\interim\m2-domain-evidence\domain-evidence-report.json --masks ..\data\interim\m2-domain-evidence\domain-candidate-masks.parquet
```

The evidence-only configuration is [`../analysis/evidence/domain-candidates.toml`](../analysis/evidence/domain-candidates.toml). It checksum-gates every input, states both mile conversions, records the 25 m shoreline simplification, densifies VSR edges to at most 0.01 degrees before projection, and approximates buffer quadrants with 32 segments. Each candidate is intersected with every exact EPSG:3310 grid-water geometry. Cell counts and areas come from polygon intersections; no centroid, majority, or whole-cell assignment is used.

VSR densification is necessary. Projecting only stored vertices turns long geographic segments into projected chords and produced an invalid polygon. Densification at 0.01 degrees yields a valid polygon; limits of 0.005 and 0.001 degrees change statewide projected area by only 0.007 and 0.009 km². Within the accepted grid, the densified VSR intersection is 56,506.330 km².

Evidence identity from the clean run:

- Evidence ID: `domain-evidence-0b3b7aa4ce0c050303886751`
- Report: 6,752 bytes; SHA-256 `74f4caecf392f7c6df8cd162566f4c7b494bddfb58f45acd27ccc22faad91f10`
- Eight-feature EPSG:3310 mask GeoParquet: 887,811 bytes; SHA-256 `b521fed1378e6b946ec3c1b114f941583c16d683d2b5c0f9ba3444601131daf5`
- Exact water-grid SHA-256: `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`
- Configuration SHA-256: `ce408896a0f2c86e50f895aa120e3e2a1538695a9a67e5adda58e5a9669a7fee`

Both outputs remain under ignored `data/interim/`; neither is a production dataset.

### Visual verification

On 2026-08-28, QGIS 4.2.1 (Belém do Pará) opened the exact mask GeoParquet with SHA-256 `b521fed1378e6b946ec3c1b114f941583c16d683d2b5c0f9ba3444601131daf5` directly through OGR. QGIS reported eight valid EPSG:3310 features and aligned them with the exact 4,516-cell EPSG:3310 water grid and the source VSR polygon. A 2,200 × 1,400 ignored render (SHA-256 `7d2f2da26410440908471ec4b3c78e50bab4dbcfdce892c7d25717fc8147f67f`) was inspected at full extent. It showed the expected nested coast- and receiver-distance boundaries, circular receiver influence around offshore-island sites, coastline and island gaps, exact truncation by biological support/map edges, and alignment with the VSR boundary. No unexplained displacement, axis reversal, hole filling, spike, or projection artifact was visible. The render and script remain ignored verification evidence and do not modify generation lineage.

## Candidate measurements

The common denominator is 107,728.696 km² of whale-model-support water in the map extent, including 56,506.330 km² inside and 51,222.366 km² outside the Southern California portion of the VSR zone represented by that grid. "VSR represented" below means the share of that 56,506.330 km² retained by the candidate, not the statewide zone.

| Candidate | Included water km² | VSR km² | Outside-VSR km² | Inside / outside | VSR represented | Cells full / partial / outside |
|---|---:|---:|---:|---:|---:|---:|
| Coast, 40 statute mi | 57,027.326 | 46,866.769 | 10,160.556 | 82.18% / 17.82% | 82.94% | 2,333 / 137 / 2,046 |
| Coast, 40 nautical mi | 62,159.964 | 49,397.447 | 12,762.517 | 79.47% / 20.53% | 87.42% | 2,544 / 137 / 1,835 |
| Coast, 50 statute mi | 65,556.990 | 51,038.053 | 14,518.938 | 77.85% / 22.15% | 90.32% | 2,682 / 137 / 1,697 |
| Coast, 50 nautical mi | 71,940.055 | 54,087.184 | 17,852.871 | 75.18% / 24.82% | 95.72% | 2,954 / 128 / 1,434 |
| Receivers, 40 statute mi | 46,098.438 | 37,649.490 | 8,448.948 | 81.67% / 18.33% | 66.63% | 1,854 / 177 / 2,485 |
| Receivers, 40 nautical mi | 52,781.264 | 41,652.696 | 11,128.568 | 78.92% / 21.08% | 73.71% | 2,132 / 177 / 2,207 |
| Receivers, 50 statute mi | 57,054.356 | 44,153.217 | 12,901.139 | 77.39% / 22.61% | 78.14% | 2,324 / 164 / 2,028 |
| Receivers, 50 nautical mi | 64,716.660 | 48,379.720 | 16,336.940 | 74.76% / 25.24% | 85.62% | 2,641 / 152 / 1,723 |

The range is analytically material. Coastline scenarios vary by 14,913 km² of water and 12.78 percentage points of represented in-grid VSR area. Receiver scenarios vary by 18,618 km² and 18.99 percentage points.

## Feasibility findings

### Conservative nearshore domain

Technically feasible and reproducible from CUSP. It would exclude 33,642 to 50,701 km² of map-grid water. It is not yet defensible as an observed domain because NOAA's statement describes where data are generally unavailable, not guaranteed completeness inside the line.

### Coverage-qualified mask in the broader map

Technically feasible and the clearest eventual treatment. Cells beyond an accepted boundary can remain visible for whale and VSR context but must be marked `outside defensible AIS observability`, excluded from headline statistics, and never symbolized as observed low traffic. Boundary cells retain their exact qualified geometry and fraction.

The UI should show one headline population only: the accepted qualified domain. It may state how much map and VSR area was excluded, but must not publish an unqualified full-map exposure statistic beside it.

### Receiver/base-station geometry

Useful as sensitivity evidence, not sufficient as the Version 1 boundary. The source is authoritative for published station locations and matches the analytical year, but its completeness is untested. A circular radius ignores antenna height, terrain and island shadowing, transmitter height and power, station outages, and anomalous propagation. No source field converts a point to a defensible 2024 reception polygon.

## Smallest evidence still required

Acceptance requires one of the following from NOAA OCM or USCG:

1. a statement that a specific distance and unit from a named coast representation is the intended conservative analytical limit, together with whether water inside that limit may be treated as coverage-qualified despite station outages; or
2. a 2024 Southern California receiver-coverage or station-operational product defining reception geometry or supplying station completeness, antenna height/range, and operating intervals sufficiently to construct it.

Absent either, the project cannot choose one merely because it is the most conservative. A deadline is not coverage evidence.

## Reporting consequences

- Map/context extent remains longitude −122 to −117 and latitude 32 to 35. It is not the statistical domain.
- Every future statistic describes only the Southern California portion of the statewide VSR zone within the accepted qualified domain.
- The map truncates the continuing statewide VSR zone at 35°N; this must be stated beside the result.
- VSR redistribution rights are a separate publication question and do not determine this decision.
- No cell outside defensible AIS observability is interpreted as observed low traffic. Such cells are excluded from headline statistics and explicitly masked or qualified in the map and accessible text.
