# Analysis

This directory is the Python package for the M3 offline-processing workflow. It
provides versioned spatial and source-input contracts, read-only validators,
traceable lineage metadata, a local AIS retrieval-verification boundary, a real
one-extract AIS cleaning command, and
construction of the exact EPSG:3310 analysis grid with actual per-cell water
geometry from an explicitly supplied polygon mask. It also transfers the
selected NOAA/SWFSC modeled blue-whale density surface to that water grid by
abundance-conserving area weighting. A separate read-only evidence harness
diagnoses consecutive observations from one explicitly supplied cleaned AIS
bundle and can optionally test segment allocation against the exact water-grid
contract. A further boundary assembles explicitly supplied one-date cleaner
bundles into a versioned multi-day period-input manifest and scans its verified
daily Parquet partitions through a bounded DuckDB relation. It does not submit
AccessAIS orders, download AIS, process a season implicitly, produce a
production vessel-activity grid, calculate relative exposure, or report
inside-versus-outside statistics.

Run all commands below from this directory.

## Prerequisites

- Python 3.13 (the package requires `>=3.13,<3.14`)
- uv 0.12 or later, available in this repository as `python -m uv`

## Setup and checks

```text
python -m uv sync --locked
python -m uv lock --check
python -m uv run ruff format .
python -m uv run ruff format --check .
python -m uv run ruff check .
python -m uv run mypy src/whale_vessel_analysis
python -m uv run pytest
python -m uv build
python -m uv run python -m whale_vessel_analysis --help
python -m uv run python -m whale_vessel_analysis.ais_retrieval_cli --help
python -m uv run python -m whale_vessel_analysis.vessel_activity_evidence_cli --help
python -m uv run python -m whale_vessel_analysis.multiday_ais_cli --help
python -m uv run python -m whale_vessel_analysis.whale_grid_cli --help
```

`uv.lock` is committed. `uv sync --locked` creates an ignored local virtual
environment from that lock and fails instead of changing it. Runtime packages
belong in `project.dependencies`; test, lint, and type-check tools belong in the
`dev` dependency group.

## Validation commands

Every input location is supplied at runtime. Omitting `--config` uses the
version-controlled `default_config.toml` packaged with the module.

```text
python -m uv run python -m whale_vessel_analysis validate-config
python -m uv run python -m whale_vessel_analysis validate-config --config <config.toml>
python -m uv run python -m whale_vessel_analysis validate-ais <ais.csv>
python -m uv run python -m whale_vessel_analysis validate-whale <model.gdb>
python -m uv run python -m whale_vessel_analysis validate-vsr <zone.geojson>
```

The validators print JSON and do not write analytical output. Exit status 0
means the supplied source satisfies the implemented contract; status 2 means a
schema, configuration, or value check failed. Source data is expected to need
later cleaning, so a non-zero raw-AIS result is an audit finding rather than a
request to edit the source.

The packaged configuration records the accepted 1 July–30 November 2024
analytical period, the proposed ADR 0002 map/context extent, EPSG:3310, and the
accepted 5,000 m grid. It deliberately represents the analytical domain only as
`unresolved`; this foundation contains no exposure,
inside-versus-outside statistics, exposure-layer, or application-results
contract.

## Verify one author-supplied AIS delivery

The focused `ais_retrieval_cli` boundary inspects one explicit local NOAA
artifact read-only and writes a versioned
`noaa_ais_retrieval_manifest_v1` JSON manifest to an explicit local path. It
does not access the network, submit an AccessAIS order, discover other files,
or retrieve a date range.

```text
python -m uv run python -m whale_vessel_analysis.ais_retrieval_cli --input <author-supplied-artifact> --manifest ../data/interim/ais-retrieval/manifest.json --expected-utc-date 2024-07-15 --route accessais --request-id <stable-local-token-free-id> --source-reference "author-supplied AccessAIS delivery" --requested-from 2024-07-15 --requested-through 2024-07-15 --lon-min -122 --lat-min 32 --lon-max -117 --lat-max 35 --source-filename <NOAA-supplied-filename> --retrieved-at-utc <actual-UTC-retrieval-timestamp>
```

Optional `--http-content-length`, `--http-etag`, and `--http-last-modified`
values record source metadata supplied by the author. The implementation hashes
every source byte and detects CSV or ZIP by content. ZIP inspection rejects
unsafe paths, requires exactly one unambiguous CSV member, streams every member
through CRC validation, checks the exact NOAA 17-column header, and requires all
valid parsed timestamps to belong to the expected UTC date. A plain CSV without
an independent source byte count can establish byte identity, header, and date,
but its byte-completeness state remains `unverified`; a complete ZIP structure
and CRC or a matching source `Content-Length` can verify that separate state.

The manifest keeps source availability, byte/archive verification, expected-
date verification, cleaning compatibility, and observational completeness as
different fields. Observational completeness always remains `unverified`.
Every new manifest starts with the complete accepted 153-date calendar from
2024-07-01 through 2024-11-30. Only a byte-complete current entry with status
`verified` removes its date from the missing set; analytical-period retrieval
becomes `verified` only when all 153 current entries are verified.
Repeated identical bytes append reusable attempt evidence without creating a
second current date entry. Different bytes put the date in `conflict` without
replacing the previously verified identity.

For a verified ZIP, `--csv-bundle-dir <data/interim/...>` extracts only the
selected safe member into an atomic `noaa_ais_retrieval_csv_bundle_v1` bundle.
The command refuses `data/raw`, arbitrary existing destinations, and replacement
of incompatible bundles. It rechecks the source byte size and SHA-256 before
extraction and before publishing, so a path swapped after inspection cannot be
attributed to the earlier artifact. `--clean-output-dir <data/interim/...>`
additionally runs the existing source validator and one-date cleaner; ZIP input
also requires `--csv-bundle-dir`. The attached cleaning reference records
checksums and row counts but verifies that the cleaner's completeness field is
still `unverified`. Successful attachment records
`observational_completeness_preserved: true`; a reference that reports any
other completeness state is rejected without changing the manifest.

The real bounded 2024-07-15 AccessAIS delivery exercised this boundary on
2026-08-28. NOAA delivered a direct CSV with the exact 17-column header:
59,497,346 bytes, SHA-256
`694ea3e8364de21467dea0affeb77e954d339e155d316dc4115b87ac01ffcca3`,
and 582,419 valid rows spanning only `2024-07-15T00:00:00Z` through
`2024-07-15T23:59:59Z`. No independent HTTP `Content-Length` or `ETag` was
retained, so byte completeness remains `unverified`; timestamp bounds do not
change observational completeness from `unverified`, and the 153-date period
remains not verified.

The cleaner produced 113,799 rows under
`noaa_marine_cadastre_ais_extract_v2`, with deterministic run ID
`ais-362502c6a37b53e681b745f5` and cleaned SHA-256
`efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`.
Two measured repeat runs reproduced both identities in 3.175186 and 3.094731
seconds. Their approximately 1.59 GiB peak RSS is a scaling concern: monthly
and full-period processing have not been shown safe and require optimization,
bounded date-sized processing, spilling or memory controls, or another measured
design before execution. The full evidence and removal accounting are in the
[source register](../docs/data-sources.md#retrieval-route). ADR 0017 remains
Proposed because independent transfer completeness and scaling are unresolved.

## Process one AIS extract

`process-ais` requires one explicit NOAA Marine Cadastre flat CSV extract and
one explicit output-bundle directory. It never discovers adjacent files,
expands a date range, downloads data, or writes into `data/raw/`. The extract
must contain at least one data row and one valid timestamp, and all valid
timestamps must fall on exactly one UTC calendar date.

A partial-day extract is valid input. The command does not infer that the CSV
covers every instant or record in that date: completeness is reported as
`unverified`; the retrieval boundary deliberately does not upgrade this
observational-completeness field. The processing contract is
`noaa_marine_cadastre_ais_extract_v2`, not a complete-day contract.

```text
python -m uv run whale-vessel-analysis process-ais --input <one-ais.csv> --output-dir <new-output-directory>
```

Omitting `--config` uses the packaged configuration. Supply an equivalent
versioned TOML file with `--config <config.toml>`. The command refuses any
existing output directory by default. `--overwrite` is narrowly limited to a
complete bundle previously marked with this command's contract; it will not
replace an arbitrary directory.

The output directory is published atomically only after all three files are
complete:

| File | Contract |
|---|---|
| `cleaned.parquet` | Deterministically ordered, map-extent-scoped commercial AIS rows. |
| `quality-report.json` | Stage counts, every removal and normalization count, earliest/latest valid timestamps, observed UTC date, unverified completeness, parameters, hashes, and the map-extent scope warning. |
| `run-metadata.json` | Existing `RunMetadata`, `ArtifactReference`, `ProcessingStep`, and `ValidationRecord` structures plus real UTC execution timestamps, runtime/package versions, the analytical period, and the full processing parameters. |

The Parquet columns, in order, are `mmsi`, `observed_at_utc`, `latitude`,
`longitude`, `sog_knots`, `cog_degrees`, `heading_degrees`,
`vessel_type_code`, `vessel_type_group`, and `length_m`. Timestamps are stored
as UTC. MMSI, timestamp, coordinates, vessel type, and vessel group are required
by the cleaning contract; speed, course, heading, and length can be null for a
documented reason.

The cleaning order is fixed and auditable:

1. require the exact inspected 17-column header and at least one data row;
2. parse the strict source timestamp as UTC, require at least one valid
   timestamp, and require all valid timestamps to share one UTC calendar date;
3. remove missing, non-finite, out-of-range, and outside-map-extent positions;
4. remove MMSI values that do not satisfy the existing nine-digit contract;
5. remove missing, malformed, non-finite, or negative reported SOG values, while
   converting the documented `102.3` unavailable sentinel to null;
6. remove missing, malformed, and unavailable vessel types, then retain the
   documented commercial groups: passenger 60–69, cargo 70–79, tanker 80–89;
7. retain one copy of an exact 17-field duplicate, then remove every row in any
   remaining repeated MMSI/UTC-timestamp conflict, per
   [ADR 0013](../docs/decisions/0013-remove-conflicting-ais-key-records.md); and
8. normalize documented COG/heading sentinels and invalid optional navigation or
   length values to null, with separate counts.

No universal speed ceiling or implied-position speed rule is enabled. Reported
SOG validity and position-to-position behavioral plausibility remain separate.
The optional length filter is also disabled: AIS has no gross tonnage, and the
project has not accepted a length proxy, threshold, or sensitivity plan.

The cleaned Parquet, quality report, output checksum, and run identifier are
deterministic for the same input bytes, configuration, and final paths. Run
metadata also records the real UTC time immediately before processing begins
and the real UTC completion time after the analytical files are prepared, so
that metadata file is intentionally not byte-identical across real executions.
Execution timestamps and the configured 2024 analytical period are separate
fields. The input CSV and every generated bundle remain local and Git-ignored.
The command records the supplied path and SHA-256 but does not invent a
publisher retrieval date; retrieval provenance remains something recorded when
retrieval occurs.

## Multi-day cleaned AIS period input

A separate command assembles independently verified one-date cleaner bundles
into one versioned `multiday_cleaned_ais_input_v1` period-input manifest. It
reads only the paths it is given, writes only the explicit manifest path under
the ignored `data/interim/` root, and publishes atomically. It downloads
nothing, selects no plausibility threshold, constructs no segment, and emits no
vessel-activity grid.

```text
python -m uv run python -m whale_vessel_analysis.multiday_ais_cli record --manifest ..\data\interim\m3-multiday-ais-foundation\period-manifest.json --cleaned-bundle <cleaner-output-directory> [--cleaned-bundle <another>] [--retrieval-manifest <retrieval-manifest.json>]
python -m uv run python -m whale_vessel_analysis.multiday_ais_cli status --manifest <period-manifest.json>
python -m uv run python -m whale_vessel_analysis.multiday_ais_cli scan --manifest <period-manifest.json> --memory-limit 2GB --temp-directory ..\data\interim\m3-multiday-ais-foundation\duckdb-temp [--threads <n>] [--batch-size <rows>] [--require-ready]
```

Exit codes are explicit: `0` succeeded, `2` refused an input, destination, or
contract check, `3` succeeded while the analytical period is not ready, and `4`
recorded a conflicting date entry. Every command prints JSON diagnostics.

### What the contract keeps separate

The manifest starts from all 153 accepted UTC dates in
[ADR 0005](../docs/decisions/0005-analytical-period.md) and keeps one current
entry per date. Each entry records these states independently, so none can be
mistaken for another:

| State | Meaning |
|---|---|
| `utc_date` | One expected accepted analytical-period date. Entries are unique and cover the complete period. |
| `retrieval_manifest_state` | What the optional read-only `noaa_ais_retrieval_manifest_v1` boundary recorded for that date, or `not_supplied`. |
| `independent_retention_state` | Retained-byte identity, independent byte completeness, and archive verification, taken only from the retrieval boundary. These stay `unverified` without it. |
| `retrieval_to_cleaner_linkage` | Whether the retrieval manifest's own `cleaning_reference` checksums bind to this recorded bundle. `not_supplied` without a retrieval manifest, `unverified` when no reference exists, `verified` when all three cleaner checksums match. A reference naming a different bundle is refused, not recorded. |
| `cleaner_bundle_compatibility` | The verified three-file bundle: cleaner contract, processing version, shared run identity, cleaned-Parquet, quality-report and run-metadata checksums, row count, exclusive UTC date, and the cleaner's own temporal coverage. |
| `status` | `missing`, `compatible`, or `conflict`, with a reason and append-only attempt history. |
| `observational_completeness` | Always `unverified`, per date and for the period. Retrieval and cleaning integrity cannot establish receiver coverage or records that were never observed. |

### What a supplied bundle must satisfy

Every supplied bundle is validated through the existing sidecar and checksum
boundary before it can occupy a date:

1. exactly `cleaned.parquet`, `quality-report.json`, and `run-metadata.json`;
2. the supported cleaner contract `noaa_marine_cadastre_ais_extract_v2` and its
   `clean-and-scope-ais-extract` processing version `2.0.0`;
3. one cleaner run identity shared by the quality report and the run metadata;
4. cleaned-Parquet and quality-report checksums matching both sidecars;
5. the exact cleaner output schema, including a timezone-aware timestamp;
6. exactly one UTC date, read from the Parquet through DuckDB and cross-checked
   against the quality report's observed date and row count;
7. that date inside the accepted period; and
8. an unchanged `unverified` completeness claim — an upgraded claim is refused.

When a retrieval manifest is supplied, its per-date `cleaning_reference` is
bound to the recorded bundle rather than merely sitting beside it. Every
checksum the reference carries — cleaned Parquet, quality report, run metadata —
must equal the recorded bundle's. A reference naming a different bundle is
refused and nothing is published, so a retrieval entry cannot be presented as
evidence for a cleaned input it did not produce. A reference that is absent, or
that carries only some of the three checksums, leaves the linkage `unverified`
with the reason recorded.

A date already holding a compatible entry accepts an identical bundle as
reusable retry evidence. Different bytes create a `conflict` that preserves the
recorded identity and the attempt history rather than replacing them; a further
bundle for a conflicting date is recorded as `conflict_pending_review`. A date
outside the accepted period, an incomplete bundle, tampered bytes, or mismatched
sidecar identities are refused without publishing anything.

### Readiness and identity

`period_input_readiness` is `ready` only when all 153 expected dates hold a
compatible verified current entry. One valid date produces an explicitly
incomplete manifest listing 152 missing dates. The manifest names what is
deliberately insufficient: observed timestamp bounds, a filename, and a
plausible row count are not evidence; retrieval transfer completeness is a
separate unverified state; and observational completeness remains unverified.

`period_input_id` is derived from the contracts, the expected dates, and the
per-date analytical identity: the deterministic cleaned-Parquet checksum, the
deterministic cleaner run identity, the row count, and the observed UTC date.

The quality-report and run-metadata checksums are **recorded and validated** on
every bundle, but they are deliberately **excluded from that identity**. The
cleaner writes local absolute paths and real UTC execution timestamps into those
two sidecars, so regenerating the same analytical data in another directory or
at another time changes their bytes while the cleaned Parquet and the cleaner
run ID stay identical. Including them would have made a supposedly stable
identifier depend on where and when the cleaner ran. Attempt timestamps and
local paths are likewise kept as provenance in `local_provenance` and in the
attempt history rather than in the identity.

Equivalent identity is not tolerance of different bytes: within one manifest, a
second bundle whose recorded checksums differ from the current entry still
creates a `conflict`. Loading a manifest recomputes both the readiness summary
and the identity and refuses a file whose recorded values disagree.

### Bounded DuckDB scanning

`scan` opens the manifest's compatible daily Parquet partitions as one DuckDB
relation. It re-verifies every recorded cleaned-Parquet checksum first, then
requires an explicit memory limit with a unit and an explicit temporary/spill
directory under ignored `data/interim/`; a uniquely named spill subdirectory is
created for the run and removed afterwards. Scanned per-date row counts must
match the manifest.

The full period is never concatenated in Python, Pandas, Polars, or PyArrow.
Aggregates are computed in SQL, and ordered results are streamed as bounded
Arrow record batches. The deterministic global order is `mmsi`,
`observed_at_utc`, `latitude`, `longitude`, `vessel_type_code`,
`vessel_type_group`, and it does not depend on the order bundles were recorded
in.

Continuity is preserved across midnight: consecutive pairs are formed over the
whole period per MMSI, so a vessel is not split solely because the UTC date
changed. The reported `continuity` summary compares that whole-period adjacency
with an artificially date-partitioned one and states how many pairs the daily
partitioning would have lost. This is a continuity diagnostic only. No maximum
interpolation gap, implied-speed rule, length threshold, or edge-support
treatment is applied, and no segment or vessel-activity grid is produced.

### Verified real read-only smoke run

On 2026-08-28 the command recorded the existing bounded 2024-07-15 cleaner
bundle read-only, together with the existing retrieval manifest for that date.
Neither source was modified; the cleaned Parquet, quality report, run metadata,
and retrieval manifest kept their prior checksums.

- One compatible date, `2024-07-15`, with 152 missing expected dates and
  `period_input_readiness: not_ready`.
- Cleaned Parquet SHA-256
  `efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`,
  quality report SHA-256
  `744d358759774072b34f62fdbc7e9e3c4d39fe2c537cc03ce4d37b05c72e92ea`,
  run metadata SHA-256
  `54cd72e719ba56e112ac146195d1df9e5bdda99ab588704897210cea35423637`,
  and cleaner run ID `ais-362502c6a37b53e681b745f5`.
- Path- and clock-independent `period_input_id`
  `multiday-ais-aeaf8f584d830ed98ef2b52d`. A repeat invocation with the same
  bundle is recorded as `identical_retry` and reproduces that identifier while
  appending a second attempt, so the manifest file bytes change and the content
  identity does not.
- The retrieval state was recorded separately and truthfully: entry status
  `retrieved`, retained byte identity `verified` for the 59,497,346-byte source
  with SHA-256
  `694ea3e8364de21467dea0affeb77e954d339e155d316dc4115b87ac01ffcca3`,
  and independent byte completeness `unverified`.
- `retrieval_to_cleaner_linkage` was `verified`: the retrieval manifest's own
  `cleaning_reference` named the same cleaned-Parquet, quality-report, and
  run-metadata checksums as the supplied bundle.
- Period `independent_transfer_completeness` and `observational_completeness`
  both remained `unverified`.
- `scan` with `--memory-limit 2GB` streamed 113,799 observations in three
  50,000-row Arrow batches and reported 113,620 whole-period consecutive pairs.
  That count equals the structural segment count the one-bundle evidence harness
  independently produced for the same input. With only one date present,
  `cross_utc_date_pairs` and `pairs_lost_to_date_partitioning` were both 0, as
  expected. Three end-to-end `scan` invocations took approximately 0.63, 0.68,
  and 0.78 seconds.

This is one date. It does not validate the analytical period, does not establish
transfer or observational completeness, and produces no analytical result. The
generated manifest and spill directory stay under ignored
`data/interim/m3-multiday-ais-foundation/`.

## Vessel-activity evidence harness

The isolated harness consumes the exact three-file bundle written by
`process-ais`; it verifies the cleaner contract, the cleaned-Parquet and
quality-report checksums recorded by the sidecars, and their shared cleaner run
identity. It never reads raw AIS, discovers adjacent files, or modifies an
input. The output must be an explicit JSON path under the ignored `data/interim/`
root:

```text
python -m uv run python -m whale_vessel_analysis.vessel_activity_evidence_cli --cleaned-bundle <cleaner-output-directory> --output ..\data\interim\vessel-activity-evidence\report.json
```

There is no default maximum gap, implied-speed ceiling, or vessel-length
threshold. Candidate evidence values are optional, repeatable command-line
arguments and remain labelled as candidates in the report:

```text
--candidate-maximum-gap-seconds <seconds>
--candidate-implied-speed-ceiling-knots <knots>
--candidate-minimum-vessel-length-m <metres>
```

The report deterministically reorders observations by MMSI and UTC timestamp,
constructs consecutive pairs, and records observation, distinct-MMSI,
distinct-MMSI-date, time-gap, zero-length, group-change, non-increasing-time,
endpoint-distance, implied-speed, and reported-SOG diagnostics by vessel group
and for the commercial union. Commercial observation totals are additive, but
commercial distinct counts are recomputed from the union rather than summed
across passenger, cargo, and tanker groups. EPSG:3310 endpoint distances are
compared with WGS 84 geodesic distances. Reported SOG availability remains a
point attribute and is not substituted for implied segment speed.

Supplying an exact grid is optional:

```text
--grid-input <projected-water-grid.parquet> [--expected-grid-sha256 <sha256>]
```

That path reuses the exact `projected_water_grid_v1` contract and optional
checksum validation, transforms longitude/latitude with explicit x/y ordering,
and intersects every structurally eligible segment with actual modeled-whale-
support cell geometry exactly once. The resulting deterministic parent/piece
representation carries parent identity, group, elapsed time and projected
distance; stable cell and piece order; piece distance; outside-support distance;
and explicit positive-length, zero-length, outside-support and ambiguous status.
The unfiltered structural baseline and every explicitly supplied candidate
scenario filter and aggregate that same cache; scenarios do not repeat Shapely
segment/grid intersections.

Each population reports every target cell in stable grid order, including zero-
valued cells. Per-cell evidence contains segment-piece count and passenger,
cargo, tanker and additive all-commercial vessel-kilometres and vessel-hours.
Vessel-hours are a separately named evidence-only comparison under an explicit
constant-progress assumption: positive-length elapsed time is proportional to
piece/parent projected length. A zero-length pair assigns all time only when its
coincident point belongs to exactly one support cell; no match is retained as
outside-support time and multiple matches remain unallocated. Parent distance
and elapsed time are conserved within recorded tolerances.

The report also classifies every cleaned observation against exact support
geometry and gives each target cell observation, distinct-MMSI and distinct-
MMSI-date counts by group and for the recomputed commercial union. Outside-
support and multiple-cell point counts remain separate. This point population
is not filtered by candidate segment rules. Outside support means only outside
the supplied biological model support; it is not labelled as land, dry area, or
absent AIS coverage. These per-cell values remain diagnostics inside the ignored
JSON report; no per-cell vessel-activity dataset is emitted.

The deterministic report contains no execution timestamp. Its `report_id` is
derived from stable checksums, contracts, cleaner run identity, observations,
parameters, and diagnostics. Local bundle, cleaned-Parquet, and grid paths are
retained as execution provenance but explicitly excluded from that identity, so
moving identical inputs between worktrees does not change `report_id`. The CLI
prints actual UTC start/completion time and elapsed time separately. Writing is
atomic, existing output requires `--overwrite`, an unrelated JSON file cannot be
overwritten, and any destination outside `data/interim/` or beneath `data/raw/`
is refused.

Synthetic verification covers exact distance/time splitting, partial outside
support, every zero-length placement state, group and union totals, point-union
distinct counts, intersection-cache reuse, deterministic ordering and identity,
and the existing input/output safeguards.

The updated harness was exercised read-only against the real bounded 2024-07-15
cleaned bundle and exact water grid on 2026-08-28, without any candidate
threshold arguments. `vessel_activity_evidence_v2` processing version `2.0.0`
processed 113,799 observations and 113,620 structural segments into 77,887
cached in-support pieces, touched 1,303 of 4,516 cells, and passed distance,
elapsed-time and no-double-allocation checks. The total parent distance was
25,560.766048547 km: 24,096.858442602 km inside support and 1,463.907605945 km
outside. Parent vessel time was 3,672.903055556 hours: 1,929.780498228 inside,
1,743.122557328 outside and 0 unallocated. Cleaned-point context classified
71,482 observations inside support, 42,316 outside and one as multiple-cell
ambiguous.

The 2,166,881-byte report has path-independent ID
`vessel-evidence-8432d5193107b94d88873201` and exact local SHA-256
`60e6a02be98d8cf5edd45af56a5adcfac001681a71e868dd438c4db0894a4d6e`.
A second clean output reproduced both identities. The cleaned input SHA-256 is
`efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`,
cleaner run ID is `ais-362502c6a37b53e681b745f5`, and exact grid SHA-256 is
`7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`.

The harness-recorded processing interval inside `run_evidence` was 25.007583
seconds. That interval begins after Python imports, CLI parsing and
configuration loading, so it is not an end-to-end CLI runtime. A separate
deterministic repeat under a process-tree RSS sampling protocol took 59.562371
seconds and observed an approximate 309.441 MiB peak. These timing observations
used different protocols; sampling may have contributed overhead, but the
measurements do not isolate its effect. Independent end-to-end CLI runs took
approximately 64.4 and 66.4 seconds while reproducing the exact report.

Compared with the prior aggregate-only harness's 228.968-second observation,
these measurements provide directional evidence of improved runtime, not a
generally reproducible speedup factor. Compared with the earlier approximate
243 MiB working-set measurement, memory regressed by about 66 MiB (27%); the
methods are both approximate, so this comparison is directional rather than
exact. No one-day performance figure is extrapolated to 153 days.

The maximum implied speed remained 431,402.639804 knots. That physically
implausible value confirms that the unfiltered baseline is diagnostic only and
that an explicit, evidence-supported plausibility rule remains necessary. No
production threshold was selected, and no real candidate threshold was
supplied, so real per-cell candidate effects remain unexercised. Source-transfer
and observational completeness remain unverified; one day does not validate the
analytical period; edge-support treatment remains unresolved; and no production
vessel grid or exposure result exists.

## Projected water-grid command

The spatial slice has a separate module entry point so it does not change the
shared AIS-oriented command surface:

```text
python -m uv run python -m whale_vessel_analysis.spatial_cli --input <mask-dataset> --layer <layer> --source-crs <crs> --output <water-grid.parquet> [--config <config.toml>] [--overwrite]
```

`--layer` may be omitted for a single-layer format. `--source-crs` is required
and is checked against the CRS embedded in the input; a missing or mismatched
CRS fails the run. Longitude/latitude inputs are transformed with explicit x/y
ordering. The command reads every polygon feature, rejects null, empty,
invalid, non-finite, or non-polygon geometry, unions the accepted mask, and
constructs the configured WGS84 map/context polygon with edges densified to at
most 0.01°. It projects that polygon to EPSG:3310 with explicit x/y ordering,
clips the mask to it, and only then intersects the clipped support with the
exact grid defined by configuration. The grid origin and indices are never
inferred from the input.

The output is GeoParquet 1.1.0 with WKB geometry and explicit EPSG:3310
PROJJSON. Rows are ordered by zero-based `row_index` south to north, then by
zero-based `column_index` west to east. Stable identifiers use
`r{row:03d}_c{column:03d}`. Dry cells are omitted; every retained row has:

- parent-cell indices and exact projected bounds;
- actual intersected `water_area_m2` and `water_area_km2`; and
- normalized Polygon or MultiPolygon WKB contained by that parent cell.

The Parquet schema metadata records the grid contract, ordering, dry-cell
behavior, source checksum, configuration digest, CRS transformation, feature
counts, and area totals. A sibling `<output>.lineage.json` uses the foundation
run-metadata structures and records the output checksum. Execution start is
captured before input loading and processing, completion after Parquet writing,
and the deterministic content-derived run ID excludes those nondeterministic
timestamps. Writes use temporary files, refuse any destination under
`data/raw/`, and replace neither an existing dataset nor its lineage unless
`--overwrite` is explicitly supplied.

[ADR 0014](../docs/decisions/0014-select-the-grid-water-mask.md) selects the
union of the land-clipped NOAA 2020b `Blue_whale_summer_fall` polygons as the
Version 1 **grid water mask**. That footprint is the biological model's support,
not an authoritative shoreline and not an AIS observability mask. The API stays
mask-agnostic and requires the selected geometry at runtime.

The local format has been read back and validated with PyArrow. ArcGIS
publishing compatibility has not been tested or claimed. On the current
machine, GDAL/Pyogrio could not open the Parquet because its driver attempted to
load a missing `duckdb.dll`; that local driver problem does not affect the
PyArrow processing boundary but remains a delivery check for a later milestone.

### Verified NOAA smoke run

The selected NOAA layer was read-only and the generated files were written only
under ignored `data/interim/m3-spatial-grid/`. The 2026-08-27 run produced:

| Check | Result |
|---|---|
| Source features | 12,257; 0 null, empty, invalid, or non-finite geometry values |
| Source checksum | Extracted File Geodatabase directory-tree SHA-256 `1bfdb2bc75b26a3a33aa81952f5fc6cc58bd8e8b73a93362017fa06f76ec94cf`; the registered source archive checksum remains in `docs/data-sources.md` |
| Configuration | Schema 1; SHA-256 `df60aa03796ca979eff5bdca4c620fbac809a797d40d320ea649276d6c889c06`; EPSG:4326 → EPSG:3310 with `always_xy=true` |
| Nominal grid | 95 columns × 68 rows = 6,460 cells |
| Processing extent | WGS84 −122° to −117°, 32° to 35°; edges densified to at most 0.01° before EPSG:3310 projection |
| Retained water cells | 4,516; 1,944 dry cells omitted; 25 fewer retained cells than the pre-correction smoke run |
| Water area | 107,728,695,924.005 m² = 107,728.695924 km²; 2,970.781272 km² less than the pre-correction smoke run |
| Output bounds | x −189,429.372 to 272,786.624 m; y −667,727.411 to −333,263.928 m |
| CRS and geometry | EPSG:3310; Polygon and MultiPolygon WKB; 0 null, empty, invalid, or out-of-extent outputs |
| Output | 437,466 bytes; SHA-256 `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031` |
| Rerun | Explicit-overwrite rerun reproduced the same output checksum and deterministic run ID; execution timestamps and lineage checksum changed |
| Visual inspection | **Passed 2026-08-27 in headless QGIS 4.2.1 (GDAL 3.13.2).** QGIS opened this exact GeoParquet directly through OGR; no conversion was used. Five QGIS-rendered images confirmed the correct Southern California location and axis order, NOAA-footprint alignment, context-boundary clipping, plausible coastline/island gaps, south-to-north rows, west-to-east columns, and no unexplained gaps, spikes, slivers, displacement, or projection artifacts. |

The generation-time lineage sidecar must not be manually edited. It records
`visual_inspection_status: not_completed` because generation finished before
QGIS inspection, so that value remains truthful for that generation. Under the
current implementation, an explicitly authorized overwrite replaces the output
and sidecar, and prior run evidence is not retained automatically. The later
QGIS report and documentation are separate verification evidence tied to the
output SHA-256 above. Future reusable verification evidence is planned to
record the checksum, date, GIS tool/version, inspected views/checks, result, and
relevant observations. No formal verification record or command and no
append-only/versioned lineage are implemented yet; [the roadmap](../docs/roadmap.md)
carries that follow-up.

QGIS is an inspection and visual-verification tool, not a production processing
path. Any result-changing transformation discovered during review must be
implemented in Python with configuration, tests, and lineage before a new
artifact is generated.

## Modeled blue-whale grid transfer

The whale-grid command takes both inputs explicitly. The optional expected grid
checksum is checked before source projection or transfer:

```text
python -m uv run python -m whale_vessel_analysis.whale_grid_cli --whale-input <model.gdb> --whale-layer Blue_whale_summer_fall --grid-input <water-grid.parquet> --expected-grid-sha256 <sha256> --output <whale-grid.parquet> [--config <config.toml>] [--overwrite]
```

The command first validates the target as exact `projected_water_grid_v1`
GeoParquet, including the expected checksum when supplied, and then runs the
`noaa_swfsc_blue_whale_2020b_v1` source contract before projection and
transfer. It projects source geometry from EPSG:4326 to EPSG:3310 with
`always_xy=true`, checks source-interior overlap, and intersects each source
polygon with each target cell's actual water geometry. Each intersection
contributes:

```text
source modeled density (animals/km²) × overlap area (km²)
```

Contributions are summed as a modeled abundance allocation in animals. Target
modeled density is that allocation divided by the full target-cell water area
in km². The transfer preserves the target geometry and stable identity fields
byte for byte and keeps its south-to-north, west-to-east row order.

The versioned `blue_whale_grid_transfer_v1` output columns, in order, are:

| Column | Meaning and unit |
|---|---|
| `cell_id`, `row_index`, `column_index` | Stable target-grid identity. |
| `cell_x_min_m`, `cell_y_min_m`, `cell_x_max_m`, `cell_y_max_m` | Parent-cell bounds in EPSG:3310 metres. |
| `water_area_m2`, `water_area_km2` | Actual target water geometry area. |
| `modeled_abundance_allocation_animals` | Sum of source density × overlap area, in modeled animals. |
| `modeled_density_animals_per_km2` | Allocation divided by full target water area, in animals/km². |
| `source_covered_water_area_m2`, `source_covered_water_area_km2` | Water area covered by the union of contributing source polygons. |
| `uncovered_water_area_m2`, `uncovered_water_area_km2` | Explicit source-support gap. |
| `source_coverage_fraction` | Covered water area divided by water area, from 0 to 1. |
| `coverage_status` | `complete`, `within_numerical_tolerance`, or `incomplete`. |
| `source_polygon_count` | Number of positive-area source contributors. |
| `geometry` | Target water geometry as WKB with EPSG:3310 GeoParquet metadata. |

Source-interior overlap larger than 1 m² fails the run. Smaller positive-area
residuals are reported by count and total area in metadata and lineage. The
real source contains three such pairs totaling 0.311235765 m²; none exceeds
1 m². Coverage uses an exact threshold of 0.000001 m² and a numerical threshold
of 0.1 m². Conservation independently intersects each source polygon with the
unioned target water domain, then compares that expected abundance with the
cell allocations. Its scale-aware `math.isclose` bound is the larger of `1e-9`
animals and `1e-10 × max(abs(expected), abs(allocated))`; the actual difference
is retained.

The output does not carry a propagated `UNCERTAINTY` value. The source field is
a coefficient of variation, and no scientifically supported aggregation rule
or covariance information has been established. The 5 km cells are a reporting
grid, not a new 5 km biological model: area-weighted transfer changes alignment
without improving the approximately 0.1° source-model resolution. The command
does not normalize values to 0–1 or define relative exposure.

Writes follow the spatial-grid pair boundary: deterministic GeoParquet and a
sibling `.lineage.json` are prepared as temporary files and published together.
Existing outputs are refused unless `--overwrite` explicitly authorizes
replacement of both. Outputs beneath `data/raw/` are rejected. Lineage records
input checksums, configuration, transformation and tolerance parameters,
software versions, counts, coverage and conservation diagnostics, and the
output checksum. Generation-time visual status remains `not_completed`; later
QGIS evidence is checksum-bound and separate.

### Verified NOAA transfer smoke run

The 2026-08-27 run used the selected NOAA layer and the previously verified
water grid read-only. Generated artifacts remain under ignored
`data/interim/m3-whale-grid-transfer/`.

| Check | Result |
|---|---|
| Source | 12,257 validated NOAA/SWFSC polygons in EPSG:4326; directory-tree SHA-256 `1bfdb2bc75b26a3a33aa81952f5fc6cc58bd8e8b73a93362017fa06f76ec94cf` |
| Target grid | 4,516 cells; supplied SHA-256 verified as `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031` |
| Intersections | 9,981 positive-area source/target intersections |
| Source overlap | Three numerical pairs totaling 0.311235765 m²; no pair over the 1 m² rejection tolerance |
| Coverage | 4,516 complete; 0 numerical-tolerance; 0 incomplete; 0.000000591 m² total uncovered residual |
| Conservation | Source contribution and target allocation both 344.1406562623342 modeled animals; difference 0.0 |
| Values | Modeled density 0.00083394–0.007648247 animals/km²; zero negative or non-finite density/allocation values |
| Identity and geometry | 4,516 unique ordered cells; target `cell_id` and WKB geometry preserved exactly; zero null, empty, invalid, or non-finite geometries |
| Output | 523,986 bytes; SHA-256 `421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62` |
| Determinism | Two clean output paths produced byte-identical GeoParquet and the same SHA-256; lineage timestamps and checksums differed truthfully |
| Visual inspection | **Passed 2026-08-27 in QGIS 4.2.1 (GDAL 3.13.2).** QGIS opened the exact `data/interim/m3-whale-grid-transfer/blue-whale-density-grid-a.parquet` directly through OGR as Parquet. Five ignored 2200×1400 renders showed correct Southern California placement and axis order, exact source/grid alignment, plausible coastline and island gaps, expected source-scale density blocks, clean context boundaries, and no unexplained holes, slivers, displacement, or projection artifacts. |

## Re-running the large-tabular benchmark

The benchmark supporting the primary-engine decision is parameterized; no
sample path or output path is built into it. Supply an AIS CSV with the exact
published header:

```text
python -m uv run python -m whale_vessel_analysis.benchmark --input <ais-csv> --runs 5
```

The command reads only the supplied file and writes a JSON report to standard
output. It runs DuckDB and Polars in separate processes, samples process RSS,
and fails unless their grouped results are equivalent. Measured elapsed time
includes each engine's module import; the separate warm-up process only warms
the operating-system file cache. Polars and psutil are benchmark-group
dependencies; Polars is not a production dependency.
