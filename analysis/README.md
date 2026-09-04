# Analysis

This directory is the Python package for the M3 offline-processing workflow. It
provides versioned spatial and source-input contracts, read-only validators,
traceable lineage metadata, a local AIS retrieval-verification boundary, a real
one-extract AIS cleaning command, bounded local intake of explicitly supplied
multi-date AccessAIS CSV or ZIP deliveries one at a time, safe accumulation of
their compatible daily outputs into one 153-date period manifest, and
construction of the exact EPSG:3310 analysis grid with actual per-cell water
geometry from an explicitly supplied polygon mask. It also transfers the
selected NOAA/SWFSC modeled blue-whale density surface to that water grid by
abundance-conserving area weighting. A separate read-only evidence harness
diagnoses consecutive observations from one explicitly supplied cleaned AIS
bundle and can optionally test segment allocation against the exact water-grid
contract. A further boundary assembles explicitly supplied one-date cleaner
bundles into a versioned multi-day period-input manifest and scans its verified
daily Parquet partitions through a bounded DuckDB relation. A focused candidate
vessel-grid boundary streams that relation, forms whole-period consecutive
pairs, applies explicitly supplied gap and implied-speed rules, and allocates
retained segment distance to the exact projected water grid. It writes
candidate per-cell vessel-kilometres and union-recomputed distinct-vessel
descriptors under ignored `data/derived/`. It does not submit AccessAIS orders,
download AIS, process a season implicitly, accept final vessel rules, calculate
relative exposure, or report inside-versus-outside statistics.

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
python -m uv run python -m whale_vessel_analysis.accessais_period_intake_cli --help
python -m uv run python -m whale_vessel_analysis.vessel_activity_evidence_cli --help
python -m uv run python -m whale_vessel_analysis.multiday_ais_cli --help
python -m uv run python -m whale_vessel_analysis.vessel_grid_cli --help
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

The packaged [`default_config.toml`](src/whale_vessel_analysis/default_config.toml)
is the frozen schema-1 upstream processing contract used by AIS cleaning,
projected water-grid generation, whale-grid transfer, and map-extent vessel
aggregation. Its deterministic SHA-256 remains
`df60aa03796ca979eff5bdca4c620fbac809a797d40d320ea649276d6c889c06`,
so the previously verified schema-1 water grid and dependent artifacts remain
valid. Its legacy `spatial.analytical_domain_status = "unresolved"` value is a
frozen compatibility sentinel, not the authority for the reporting-domain
decision and not a claim that ADR 0002 remains unresolved.

The separate, packaged schema-1
[`default_reporting_domain.toml`](src/whale_vessel_analysis/default_reporting_domain.toml)
is the authoritative downstream reporting/analytical-domain contract. It
separately identifies the map/context extent, modeled-whale-support water
geometry, and accepted `receivers_50_nautical_miles` scope-reduced,
system-performance-qualified AIS analytical domain. The domain is 50 nautical
miles (92,600 metres) from the relevant NAIS reception stations, not from the
coast and not empirical 2024 coverage. It requires exact fractional boundary
geometry; outside cells are excluded from future headline statistics, not
classified as low traffic. Unknown receiver uptime, station completeness, feed
interruptions, antenna and terrain effects, and unverified observational
completeness remain explicit. Loading this contract cannot alter the upstream
processing configuration or its digest. No exposure, inside-versus-outside
statistics, exposure-layer, or application-results contract is implemented.

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

The cleaner bridge has no hidden memory or spill default. When
`--clean-output-dir` is present, `--memory-limit` and `--temp-directory` are
also required; `--threads` is optional and its documented default is one.
Cleaner resource arguments are rejected on inspection-only invocations. For
example, append the following to the inspection command above:

```text
--clean-output-dir ../data/interim/ais-retrieval/cleaned --memory-limit 512MB --temp-directory ../data/interim/ais-retrieval/duckdb-spill [--threads 1]
```

The resulting cleaner metadata preserves the human-readable requested and
DuckDB-normalized effective memory values, verifies their byte-equivalence
within the effective display unit's rounding precision, and records the
effective thread count and isolated spill-directory check.

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
seconds. At that stage, their approximately 1.59 GiB peak RSS was a scaling
concern: monthly and full-period processing had not been shown safe and required
a measured bounded design before execution. The subsequent explicit resource
controls supported successful seven-day, exact July monthly, exact August
monthly, and exact September monthly operational gates; October--November and
complete 153-day processing remain untested. The
full evidence and removal accounting are in the
[source register](../docs/data-sources.md#retrieval-route). The audited July
gate satisfied ADR 0017's acceptance condition. ADR 0017 is Accepted and
authorizes sequential author-submitted August--November calendar-month extracts
under the same controls, while independent transfer completeness and later-
month/full-period safety remain unresolved.

## Prepare one author-supplied multi-date AccessAIS delivery

The separate `accessais_period_intake_cli` accepts one explicit local AccessAIS
delivery and exact inclusive requested dates. It performs no network action: it
does not submit an order, scrape the AccessAIS application, send or retain an
email address, save cookies, or record an expiring/tokenized delivery URL. The
supplied file remains read-only and may be either direct CSV or ZIP when the
existing content-detection, safe-member, unambiguous-CSV, and ZIP CRC rules
pass.

Prepare deterministic one-date interim CSVs without cleaning them. Both
resource arguments are required: DuckDB sorts under the explicit memory limit
and uses a unique spill directory below the supplied ignored interim parent.

```text
python -m uv run python -m whale_vessel_analysis.accessais_period_intake_cli prepare --input <author-supplied-delivery.csv-or-zip> --intake-dir ..\data\interim\accessais-period-intake\delivery --requested-start 2024-07-01 --requested-end 2024-07-31 --memory-limit 512MB --temp-directory ..\data\interim\accessais-period-intake\duckdb-spill [--source-content-length <independently-retained-byte-count>]
```

Run the ordered resumable path through the existing one-date cleaner and
`multiday_cleaned_ais_input_v1` manifest:

```text
python -m uv run python -m whale_vessel_analysis.accessais_period_intake_cli run --input <author-supplied-delivery.csv-or-zip> --intake-dir ..\data\interim\accessais-period-intake\delivery --requested-start 2024-07-01 --requested-end 2024-07-31 --memory-limit 512MB --temp-directory ..\data\interim\accessais-period-intake\duckdb-spill --cleaned-root ..\data\interim\accessais-period-intake\cleaned --period-manifest ..\data\interim\accessais-period-intake\period-manifest.json [--source-content-length <independently-retained-byte-count>] [--config <config.toml>]
```

Validate an established intake bundle and report its current status:

```text
python -m uv run python -m whale_vessel_analysis.accessais_period_intake_cli status --intake-dir ..\data\interim\accessais-period-intake\delivery
```

Exit codes are `0` for a successful prepare/status or a run whose full 153-date
period is ready, `2` for a refused input/destination/contract, `3` for a
successful run whose period remains not ready, and `4` after a delivery or
cleaner-identity conflict is recorded without replacement.

The versioned `accessais_period_delivery_v2` manifest records source size and
SHA-256; content type detected from bytes; archive/member/CRC evidence; the
exact published header; requested start/end dates; every observed valid UTC
date and its row count; missing requested dates; valid out-of-request rows; and
malformed or otherwise unassignable timestamp rows. Its conservation equation
requires every source data row to be either assigned to one requested-date
slice or counted in one of the latter two exception populations. A malformed
timestamp is never silently dropped. Manifest validation accepts only
non-boolean integer row counts, requires slice dates to equal the reported
present requested dates, and binds each slice row count to the same date in
`rows_by_utc_date`; conserving only the overall total is insufficient.

Partitioning is a standard-library streaming scan. It holds one parsed
17-field row at a time and keeps at most eight date-staging writers open; it
does not load the delivery into Python, Pandas, Polars, or PyArrow.
Noncontiguous and unsorted date rows are supported. DuckDB then sorts each
date's parsed rows lexicographically by all 17 fields under the explicit memory
limit and isolated spill directory. Parsed blank fields are normalized from
DuckDB `NULL` back to empty strings before both sorting and export, so SQL
ordering matches manifest validation and every field remains quoted. Duplicate
multiplicity is preserved.
Every canonical daily CSV has the exact unquoted published header, UTF-8
encoding, LF record endings, and stable all-field quoting. Its content identity
and artifact SHA-256 are independent of source row order and delivery identity.
The manifest separately preserves the immutable whole-delivery byte size,
SHA-256, and delivery ID, and its generated-artifact lineage maps that source
identity to the canonical daily identities. The complete intake directory is
first built at a unique
temporary path and published by directory rename. Existing arbitrary output is
refused; an identical retry revalidates and reuses the bundle; different bytes
or requested dates append a conflict attempt without replacing established
slices or identity. Manifest validation requires every slice path to be exactly
`daily/<UTC-date>.csv`; absolute paths, parent traversal, backslashes, alternate
spellings, and paths escaping the intake directory are refused.

Version 1 manifests remain explicitly recognizable and read-only valid through
`status`. A Version 2 prepare/run refuses an established
`accessais_period_delivery_v1` intake directory and requires a fresh directory;
the two contracts are never silently mixed.

The spill parent must be disjoint from the intake directory and, for `run`, the
cleaned root and period-manifest destination. Unsafe equality, ancestor, or
descendant relationships are rejected before any destination is created.

`run` cleans slices sequentially and records each successful cleaner bundle
immediately through the existing period-manifest validator. On resume, a date
already recorded with the exact compatible cleaner identity and daily-slice
input SHA-256 is skipped. A cleaner bundle completed before an interruption but
not yet recorded is validated and recorded without rerunning the cleaner. This
bounds transient work to the delivery stream, at most eight open slice writers,
and one daily cleaner execution; accumulated daily and cleaned artifacts remain
under ignored `data/interim/`. The intake and cleaned roots must be disjoint,
and the period manifest cannot be inside either root. A newly created cleaner
bundle is not recorded until its input SHA-256 matches the established daily
slice.

The same explicit resource request now applies to canonical sorting and to
each sequential cleaner invocation. Both operations verify DuckDB's effective
memory limit, isolated temporary directory, and one-thread setting with
`current_setting()` after configuration. Each cleaner run records the requested
and effective values without recording its local spill path, and removes its
unique spill directory on success or handled failure. The memory limit governs
DuckDB's buffer manager, not total operating-system RSS; DuckDB's official
[memory guidance](https://duckdb.org/docs/stable/guides/performance/how_to_tune_workloads.html#memory-management)
documents allocations outside that limit. Therefore an RSS reading greater than
the effective limit is not, by itself, evidence that the setting failed.

Requested-date presence is inventory evidence, not completeness evidence. The
delivery manifest keeps independent transfer completeness separate and marks a
direct CSV `unverified` unless an independently retained matching source
`Content-Length` is supplied; a safe complete ZIP with passing CRC follows the
existing archive-integrity rule. Observational completeness always remains
`unverified`. The existing period manifest remains the sole readiness boundary
and becomes ready only with all 153 accepted dates.

### Accumulate separate deliveries safely

Repeat `run` once per explicit author-supplied delivery. Give every delivery a
unique intake directory, while reusing the same cleaned root and period
manifest:

```text
python -m uv run python -m whale_vessel_analysis.accessais_period_intake_cli run --input <delivery-a.csv-or-zip> --intake-dir ..\data\interim\accessais-period-intake\deliveries\<delivery-a-id> --requested-start <YYYY-MM-DD> --requested-end <YYYY-MM-DD> --memory-limit 512MB --temp-directory ..\data\interim\accessais-period-intake\duckdb-spill --cleaned-root ..\data\interim\accessais-period-intake\cleaned --period-manifest ..\data\interim\accessais-period-intake\period-manifest.json [--source-content-length <independently-retained-byte-count>]
python -m uv run python -m whale_vessel_analysis.accessais_period_intake_cli run --input <delivery-b.csv-or-zip> --intake-dir ..\data\interim\accessais-period-intake\deliveries\<delivery-b-id> --requested-start <YYYY-MM-DD> --requested-end <YYYY-MM-DD> --memory-limit 512MB --temp-directory ..\data\interim\accessais-period-intake\duckdb-spill --cleaned-root ..\data\interim\accessais-period-intake\cleaned --period-manifest ..\data\interim\accessais-period-intake\period-manifest.json [--source-content-length <independently-retained-byte-count>]
```

The intake and cleaned roots remain disjoint. Reusing the cleaned root lets an
overlapping date skip only when its established daily-slice checksum and exact
compatible cleaner identity still match. If an overlapping slice differs, the
prescribed shared-root workflow refuses it with exit code `2` before replacing
or recording against the established cleaner bundle. Exit code `4` is reserved
for a delivery conflict at an already-owned intake directory or a period
conflict recorded from an explicitly supplied, independently produced
incompatible cleaner bundle. The normal shared-root workflow does not stage
such a candidate beside the canonical date bundle. Previously compatible dates
remain recorded. Do not reuse an intake directory for a different delivery,
and do not create separate period manifests for deliveries intended to form
one analytical-period input.

Synthetic integration tests establish this composition boundary with two
disjoint deliveries, an overlapping identical established identity, and a
conflicting later cleaner identity. Existing tests separately cover identical
delivery retry, interruption and resume, immediate preservation of successful
dates, exact delivery and per-date row accounting, path separation, all 153
dates being required for readiness, and refusal to upgrade transfer or
observational completeness. These synthetic contract tests are broader than the
bounded two-date pilot below and do not establish larger-scale execution.

### Verified two-day canonical-content pilot

On 2026-09-01 the corrected Version 2 processing version `2.0.1` path processed
immutable author-supplied direct CSV deliveries under a fresh ignored root with
a `1GB` DuckDB memory limit and an isolated spill parent. This fresh rerun
supersedes the earlier pilot identities and measurements produced before blank
fields were normalized. The old one-day delivery was run first for 2024-07-15.
It contained 582,419 rows and produced a 79,299,592-byte canonical daily CSV
with SHA-256
`bf5a46c6196cf8a51ebfd62907f085a093afa64e2d4474c71ab7f441e68cf5cd`
and content ID `accessais-day-content-ae090a6e387fe79ec2f64c6e`.

The separate two-day intake then processed 1,135,408 rows for 2024-07-15
through 2024-07-16 over WGS 84 longitude -122 to -117 and latitude 32 to 35.
Its 582,419-row 15 July partition produced the same canonical bytes and content
ID despite different source order, so the established 113,799-row cleaner
bundle was skipped and reused. The 552,989-row 16 July partition produced a
75,095,691-byte canonical CSV with SHA-256
`3727a12f607dfd4194159b34a291e59374660b95b3e59a45b3d349bb4bfaf49f`
and content ID `accessais-day-content-065631b951a94d6c58165859`; cleaning retained
104,506 rows with Parquet SHA-256
`cb37b96a9f3e56838ca492a33dffc57a174fc92c1d385d3f3a1e848d2f7fbc5c`.
The one-day/two-day delivery IDs were
`accessais-period-aaadf6ed784700e1c7a2ee4d` and
`accessais-period-e00d27730a3b5541a37a9073`; their cleaner run IDs were
`ais-9fc49e14601edea30064df97` and `ais-e1ea93fe9ab4b4d068364a0c`.
The unchanged cleaned Parquet SHA-256 for 15 July remained
`efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`.
The period ID became `multiday-ais-ddf23ba501bc834dbe5a2656`, with two
compatible dates, 151 missing dates, and `not_ready` state. A repeated identical
two-day run reused both dates without regeneration.
Direct invocation confirmed exit code `3`, the documented incomplete-period
outcome. Transfer and observational completeness remained `unverified`.

Measurement used a PowerShell stopwatch plus a 10 ms recursive
`Win32_Process` process-tree sampler, summing each live process's working set.
Disk use was the recursive sum of file sizes beneath the fresh pilot root; raw
inputs were excluded. The one-day run took 12.1394198 seconds, peaked at
1,593,458,688 bytes process-tree RSS, peaked at 138,796,812 bytes pilot-root
disk, and ended at 81,137,722 bytes. The first two-day run took 19.2814239
seconds, peaked at 1,514,594,304 bytes RSS, added at most 270,186,694 bytes of
pilot-root disk, and ended 155,917,250 bytes above its baseline. The identical
retry took 10.1271792 seconds, peaked at 102,436,864 bytes RSS, and added 436
bytes of attempt-history output. OS file caches were not cleared. A sampled
peak can be missed, and wrapper
overhead is included. None of these measurements is extrapolated to a month or
five months. At that stage, the pilot authorized no additional order, did not
establish complete reception, and did not accept ADR 0017 or ADR 0018.

### AccessAIS intake resource investigation and seven-day gate

On 2026-09-02 a fresh read-only investigation used the immutable 115,791,285-
byte two-day CSV above. Normal long-running work was sampled every 100 ms after
a post-import barrier; the subsecond fingerprint check used 10 ms. The method
identified the actual Python application separately from its Windows virtual-
environment launcher, excluded the profiler, and reported application RSS,
Windows private bytes, the operating system's peak-working-set counter, and
process-tree RSS separately. The approximately 4 MiB launcher was the only
descendant overhead. Process-tree RSS can double-count shared pages, so it is
reported as a diagnostic rather than treated as application memory. OS caches
were not cleared, and elapsed-time differences are not cold-cache comparisons.

Stage isolation found the peak in the daily cleaner:

| Isolated work | Application baseline/peak RSS | Peak private bytes | Observation |
|---|---:|---:|---|
| Source fingerprint | 57.3/59.3 MiB | 390.9 MiB | 2.0 MiB RSS increase. |
| Streaming partition, 100 ms repeat | 57.5/57.8 MiB | 389.3 MiB | 0.3 MiB RSS increase; 23.796 s. A 10 ms sampler stretched the same work to 71.642 s without changing its near-baseline peak. |
| Per-date canonical sort/export, two repeats | 57.2--57.4/403.7--404.5 MiB | 745.8--746.7 MiB | Effective `953.6 MiB`, one thread, and requested spill directory verified; 8.350--11.256 s. |
| Existing default cleaner, 15 July, three repeats | 57.3--57.4/1,102.7--1,365.5 MiB | 2,152.7--2,156.4 MiB | DuckDB actually used its machine defaults: `12.5 GiB`, 12 threads, and its default temporary directory. |
| Existing default cleaner, 16 July | 57.2/1,396.5 MiB | 2,069.4 MiB | The approximately 5% smaller daily CSV used approximately 4% fewer private bytes even though RSS was higher. |
| Intake validation | 57.5/58.7 MiB | 390.2 MiB | 1.3 MiB RSS increase. |
| One-date manifest record | 57.4/57.5 MiB | 389.2 MiB | 0.1 MiB RSS increase. |

The old peak was therefore genuine cleaner allocation combined with noisy
Windows working-set residency, not an accumulating process tree and not a
failure of the bounded canonical sorter. The default cleaner's stable private-
byte peak and the smaller second date show an input-scaled component. Sequential
date cleaning, a low-memory compatible retry, and the absence of growth between
one-date and two-date corrected peaks provide no evidence of unbounded cross-
date accumulation. This does not establish the behavior of a larger individual
date or authorize a linear extrapolation.

Three 15 July cleaner repeats with `512MB` and one thread used an effective
DuckDB limit of `488.2 MiB`. Their sampled application RSS peaks were
550.410--551.098 MiB, increases over baseline were 492.848--493.723 MiB, and
private-byte peaks were 936.379--936.746 MiB. All reproduced the established
run ID and cleaned checksum. A `256MB` technical comparison also reproduced the
output at 308.227 MiB peak RSS, but took 25.974 seconds and used more temporary
disk; `512MB` was retained as the measured balance, not as a universal optimum.

With that correction in the real end-to-end path, two fresh two-day runs peaked
at 556.922 and 558.699 MiB application RSS (501.062 and 502.824 MiB over
baseline), 560.902 and 562.668 MiB process-tree RSS, and 949.652 and 952.223 MiB
private bytes. A date-restricted 15 July run peaked at 552.910 MiB RSS and
938.289 MiB private bytes. The two-day run therefore remained approximately
per-date bounded. Its separate spill parent peaked at 678.594/666.000 MiB in
the repeats, versus 625.469 MiB for the one-date run, and ended at zero every
time. Generated output roots peaked at 275.670/288.670 MiB and ended at
150.444 MiB; the one-date root peaked at 207.993 MiB and ended at 77.380 MiB.
All unique canonical and cleaner spill directories were removed. A compatible
two-day retry skipped both dates, peaked at 65.918 MiB application RSS, created
no spill bytes, and left all identities unchanged. Corrected end-to-end times
were 28.014 and 42.669 seconds; the one-date run took 34.492 seconds and the
retry 14.463 seconds. Cache state and profiling interference were uncontrolled,
so those times describe these runs only.

A third fresh two-day verification used the final profiler's gates. It recorded
2,982,256,640 bytes available memory and 40,857,993,216 bytes free disk before
starting, above the required 2/8 GiB thresholds. It took 45.110 seconds, peaked
at 558.859 MiB application RSS (502.949 MiB over its 55.910 MiB baseline),
562.828 MiB process-tree RSS, 952.691 MiB private bytes, 322.670 MiB generated-
root disk, and 618.188 MiB isolated spill; final generated-root disk was
150.444 MiB and final spill was zero. It reproduced the same identities.

The corrected runs reproduced delivery ID
`accessais-period-e00d27730a3b5541a37a9073`, period ID
`multiday-ais-ddf23ba501bc834dbe5a2656`, both canonical daily identities and
checksums, both cleaner run IDs, and cleaned checksums
`efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`
and `cb37b96a9f3e56838ca492a33dffc57a174fc92c1d385d3f3a1e848d2f7fbc5c`.
No processing-version or deterministic-content identity changed.

The next permitted real-data gate is exactly one continuous AccessAIS delivery
for **2024-07-15 through 2024-07-21**, using the already accepted WGS 84 request
bounds longitude **-122 to -117** and latitude **32 to 35**. The overlap with
15--16 July must reproduce those established canonical identities. This is a
seven-day scaling test, not evidence that a monthly delivery is safe.

Before requesting it, the author should use browser developer tools or
equivalent download evidence to retain any available response status,
`Content-Length`, `Content-Type`, `ETag`, and `Last-Modified` value without
retaining or committing an email address, cookie, authorization header, or
signed URL. After download, record the retrieval UTC timestamp, NOAA filename,
local byte size, and SHA-256. Supply `--source-content-length` only when an
independently retained HTTP value equals the local byte size. Without that value,
publisher-side independent byte completeness remains `unverified`; for this
portfolio MVP, that state no longer independently blocks the next scale test
when the repeat-transfer and processing evidence below passes.

The profiler CLI publishes each report only to a fresh path beneath ignored
`data/interim/`; it rejects `data/raw/`, outside report paths, and obviously
broad recursive disk/spill roots such as the drive or repository root. Reports
record Python, psutil, and detailed platform versions, plus the sampled minimum
available memory and free disk and maximum application RSS and spill bytes.
These CLI restrictions do not apply to the internal test boundary, which can
use pytest temporary directories.

Run from `analysis/`, substituting a new ignored gate directory and the actual
author-supplied path. Omit the bracketed content-length argument unless a
matching independently retained value exists:

```text
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.accessais_period_intake_cli --output ..\data\interim\m3-accessais-seven-day-gate\profile-first.json --label accessais-seven-day-first --disk-root ..\data\interim\m3-accessais-seven-day-gate\run --spill-root ..\data\interim\m3-accessais-seven-day-gate\spill --minimum-free-memory-gib 2 --minimum-free-disk-gib 8 --runtime-minimum-available-memory-gib 1 --runtime-minimum-free-disk-gib 4 --runtime-maximum-application-rss-gib 1 --runtime-maximum-spill-gib 2 --expected-exit-code 3 -- run --input <author-supplied-seven-day.csv-or-zip> --intake-dir ..\data\interim\m3-accessais-seven-day-gate\run\intake --requested-start 2024-07-15 --requested-end 2024-07-21 [--source-content-length <retained-Content-Length>] --memory-limit 512MB --temp-directory ..\data\interim\m3-accessais-seven-day-gate\spill --cleaned-root ..\data\interim\m3-accessais-seven-day-gate\run\cleaned --period-manifest ..\data\interim\m3-accessais-seven-day-gate\run\period.json
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.accessais_period_intake_cli --output ..\data\interim\m3-accessais-seven-day-gate\profile-retry.json --label accessais-seven-day-retry --disk-root ..\data\interim\m3-accessais-seven-day-gate\run --spill-root ..\data\interim\m3-accessais-seven-day-gate\spill --minimum-free-memory-gib 2 --minimum-free-disk-gib 8 --runtime-minimum-available-memory-gib 1 --runtime-minimum-free-disk-gib 4 --runtime-maximum-application-rss-gib 1 --runtime-maximum-spill-gib 2 --expected-exit-code 3 -- run --input <same-author-supplied-seven-day.csv-or-zip> --intake-dir ..\data\interim\m3-accessais-seven-day-gate\run\intake --requested-start 2024-07-15 --requested-end 2024-07-21 [--source-content-length <same-retained-Content-Length>] --memory-limit 512MB --temp-directory ..\data\interim\m3-accessais-seven-day-gate\spill --cleaned-root ..\data\interim\m3-accessais-seven-day-gate\run\cleaned --period-manifest ..\data\interim\m3-accessais-seven-day-gate\run\period.json
```

On 2026-09-02 the author supplied the requested direct CSV. Read-only local
inspection recorded 399,148,173 bytes and SHA-256
`0cc4ede8dc16504641f91e4ba44c1ce128933958abec1f855dc91196ae58dbd2`.
No separately retained HTTP `Content-Length` was supplied, so the first-run
command correctly omitted `--source-content-length` and transfer completeness
remained `unverified`.

The documented first-run profile above was attempted with the source path
substituted, `--source-content-length` omitted, and the documented dates,
`512MB`, one effective thread, isolated ignored spill path, preflight gates,
runtime abort limits, and expected target exit code. The profiler returned exit
code `1` and refused to launch the intake because available memory was below the
required 2 GiB preflight threshold. The preflight exception did not publish the
instantaneous byte count or a JSON report. It created no gate directory, intake,
cleaned bundle, manifest, or spill. Per the stop rule, the retry was not
attempted and no threshold was weakened. Row/date reconciliation, daily
cleaning, 15--16 July identity comparison, effective DuckDB settings, first-run
runtime extrema, post-run spill cleanup, and seven-date retry reuse therefore
had no new measurements at that point. The processing portion of the seven-day
gate remained unexercised and did not authorize a monthly request.

The same session resumed separately after available memory recovered. A direct
check immediately before launch reported 4,325,081,088 bytes (4.028 GiB)
available. The profiler then recorded 4,311,605,248 bytes (4.015 GiB) available
memory and 34,392,182,784 bytes (32.030 GiB) free disk at first-run preflight.
The unchanged command again omitted `--source-content-length`.

The resumed first run reconciled all 3,928,736 source rows: 3,928,736 valid
in-request rows were assigned, with zero malformed or unassignable timestamps
and zero valid out-of-request rows. Exactly the requested seven UTC dates were
present, with daily counts 582,419; 552,989; 553,094; 588,660; 465,342;
592,794; and 593,438 for 15 through 21 July respectively. All seven dates were
cleaned sequentially and recorded without conflict. The delivery ID was
`accessais-period-6fb3cac947cd5671da899f80` and the seven-date period input ID
was `multiday-ais-8ab9e2347a39f8844884bc24`.

The intentional overlap reproduced the established identities. The 15 July
canonical content ID, canonical SHA-256, cleaner run ID, and cleaned SHA-256
were `accessais-day-content-ae090a6e387fe79ec2f64c6e`,
`bf5a46c6196cf8a51ebfd62907f085a093afa64e2d4474c71ab7f441e68cf5cd`,
`ais-9fc49e14601edea30064df97`, and
`efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`.
The corresponding 16 July identities were
`accessais-day-content-065631b951a94d6c58165859`,
`3727a12f607dfd4194159b34a291e59374660b95b3e59a45b3d349bb4bfaf49f`,
`ais-e1ea93fe9ab4b4d068364a0c`, and
`cb37b96a9f3e56838ca492a33dffc57a174fc92c1d385d3f3a1e848d2f7fbc5c`.

The first run took 208.504 seconds excluding imports and the baseline barrier.
It recorded effective `488.2 MiB`, one thread, the isolated spill directory,
581.512 MiB peak application RSS, 970.613 MiB peak private bytes, 585.477 MiB
peak process-tree RSS, 1.801 GiB minimum available memory, 30.809 GiB minimum
free disk, 965.122 MiB peak generated-root disk, and 710.594 MiB peak spill.
The final generated root was 518.530 MiB and spill returned to zero. No runtime
threshold terminated the target.

The unchanged retry passed preflight with 2.739 GiB available memory and 31.443
GiB free disk, then skipped all seven dates with unchanged delivery, daily,
cleaner, cleaned-Parquet, and period identities. It took 148.744 seconds,
peaked at 70.367 MiB application RSS, 403.863 MiB private bytes, and 74.328 MiB
process-tree RSS, created no spill, and increased the generated root by only 501
bytes of retry provenance. Both resource reports contain no absolute path,
email address, URL, cookie, authorization value, or credential.

A subsequent author audit repeated the completed browser download separately.
Both downloads produced a 399,148,173-byte file with SHA-256
`0cc4ede8dc16504641f91e4ba44c1ce128933958abec1f855dc91196ae58dbd2`,
exactly matching the processed artifact. No HTTP `Content-Length` was retained,
so publisher-side independent byte completeness remains `unverified`.

For this portfolio MVP, the two byte-identical completed browser downloads,
successful complete parsing of each delivered row, exact seven-date coverage,
full row reconciliation, deterministic 15--16 July overlap identities, bounded
first run, and successful all-date reuse retry were accepted at that stage as
sufficient operational evidence to authorize only the **2024-07-01 through
2024-07-31** AccessAIS monthly scale test over the same bounds. This did not
establish observational completeness or prove that NOAA's server-side extract
contained every possible AIS record. It did not authorize the other four
monthly requests or establish full-period safety.

The profiler refuses to start below the deliberately conservative 2 GiB
available-memory or 8 GiB free-disk gates. During execution it displays live
threshold state and automatically terminates and reaps the target process tree
if available memory falls below 1 GiB, free disk below 4 GiB, application RSS
reaches 1 GiB, or isolated spill use reaches 2 GiB. A resource abort writes a
report when safely possible, names the terminating threshold, cannot be counted
as target success, and returns profiler exit code `5`. Also stop on a DuckDB out-
of-memory/disk error, unexpected date, malformed/unassignable timestamp,
unreconciled row accounting, canonical/checksum conflict, failure to record a
successful date, or an unresponsive process. These thresholds are operational
choices with headroom over the two-day observations, not predictions of seven-
day requirements. After an abort, do not reuse its intake directory; verify
that no published partial bundle exists and remove any abandoned ignored
staging/spill directory only after inspecting its exact resolved path.

The July monthly scale test was authorized only after two separate completed
browser downloads had the same local byte size and SHA-256; all seven requested
dates were present with reconciled row accounting and no exceptions; 15--16 July
matched the established canonical identities; every date cleaned and recorded
sequentially; effective `488.2 MiB`, one thread, and isolated spill use were
recorded; both profiles stayed below all abort thresholds; spill returned to
zero; and the retry skipped all seven dates with unchanged identities. A retained
matching HTTP `Content-Length` may verify publisher-side byte completeness but
was not required for that portfolio-MVP operational gate. Observational and
publisher-side independent byte completeness remain `unverified` without their
separate evidence. That pass authorized only the **2024-07-01 through
2024-07-31** scaling test, not the other four months or full-period safety.

### July monthly scaling gate

On 2026-09-03 the authorized monthly gate used the immutable author-supplied
direct CSV for **2024-07-01 through 2024-07-31** over WGS 84 longitude -122 to
-117 and latitude 32 to 35. The source was read in place and not changed. It
contained 1,827,867,349 bytes and had SHA-256
`30b64b3733f391a614faab0311e419b8b5e7d2262d196d87606de57397c11169`.
No independently retained HTTP `Content-Length` was available, so the command
omitted `--source-content-length` and publisher-side transfer completeness
remains `unverified`.

Run the gate from `analysis/` with a completely fresh ignored root. The retry
uses the same immutable input and managed paths. These are the exact operational
arguments, with only the private source path represented by a placeholder:

```text
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.accessais_period_intake_cli --output ..\data\interim\m3-accessais-july-month-gate\profile-first.json --label accessais-july-month-first --disk-root ..\data\interim\m3-accessais-july-month-gate\run --spill-root ..\data\interim\m3-accessais-july-month-gate\spill --minimum-free-memory-gib 2 --minimum-free-disk-gib 8 --runtime-minimum-available-memory-gib 1 --runtime-minimum-free-disk-gib 4 --runtime-maximum-application-rss-gib 1 --runtime-maximum-spill-gib 2 --expected-exit-code 3 -- run --input <author-supplied-july.csv> --intake-dir ..\data\interim\m3-accessais-july-month-gate\run\intake --requested-start 2024-07-01 --requested-end 2024-07-31 --memory-limit 512MB --temp-directory ..\data\interim\m3-accessais-july-month-gate\spill --cleaned-root ..\data\interim\m3-accessais-july-month-gate\run\cleaned --period-manifest ..\data\interim\m3-accessais-july-month-gate\run\period.json
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.accessais_period_intake_cli --output ..\data\interim\m3-accessais-july-month-gate\profile-retry.json --label accessais-july-month-retry --disk-root ..\data\interim\m3-accessais-july-month-gate\run --spill-root ..\data\interim\m3-accessais-july-month-gate\spill --minimum-free-memory-gib 2 --minimum-free-disk-gib 8 --runtime-minimum-available-memory-gib 1 --runtime-minimum-free-disk-gib 4 --runtime-maximum-application-rss-gib 1 --runtime-maximum-spill-gib 2 --expected-exit-code 3 -- run --input <same-author-supplied-july.csv> --intake-dir ..\data\interim\m3-accessais-july-month-gate\run\intake --requested-start 2024-07-01 --requested-end 2024-07-31 --memory-limit 512MB --temp-directory ..\data\interim\m3-accessais-july-month-gate\spill --cleaned-root ..\data\interim\m3-accessais-july-month-gate\run\cleaned --period-manifest ..\data\interim\m3-accessais-july-month-gate\run\period.json
```

The first profile passed its 2 GiB memory and 8 GiB disk preflight with
3,785,539,584 bytes (3.526 GiB) available memory and 27,559,759,872 bytes
(25.667 GiB) free disk. The target returned the expected exit code `3`, meaning
the 153-day input remained incomplete, while the profiler reported
`target_completed` and returned success. It reconciled all 17,998,955 source
rows: all 17,998,955 had valid in-request timestamps and were assigned, with
zero malformed or unassignable timestamps and zero valid out-of-request rows.
Exactly all 31 requested UTC dates were present and cleaned sequentially into
3,384,056 commercial observations:

| UTC date | Source rows | Cleaned rows |
|---|---:|---:|
| 2024-07-01 | 546,823 | 91,921 |
| 2024-07-02 | 558,710 | 98,983 |
| 2024-07-03 | 594,625 | 109,650 |
| 2024-07-04 | 595,814 | 104,633 |
| 2024-07-05 | 623,726 | 107,768 |
| 2024-07-06 | 593,767 | 105,188 |
| 2024-07-07 | 594,831 | 103,108 |
| 2024-07-08 | 566,737 | 110,377 |
| 2024-07-09 | 567,736 | 123,095 |
| 2024-07-10 | 578,201 | 119,854 |
| 2024-07-11 | 564,069 | 109,703 |
| 2024-07-12 | 590,516 | 114,411 |
| 2024-07-13 | 610,775 | 115,070 |
| 2024-07-14 | 619,172 | 119,503 |
| 2024-07-15 | 582,419 | 113,799 |
| 2024-07-16 | 552,989 | 104,506 |
| 2024-07-17 | 553,094 | 106,155 |
| 2024-07-18 | 588,660 | 121,005 |
| 2024-07-19 | 465,342 | 84,707 |
| 2024-07-20 | 592,794 | 107,184 |
| 2024-07-21 | 593,438 | 103,044 |
| 2024-07-22 | 584,345 | 110,710 |
| 2024-07-23 | 598,310 | 126,090 |
| 2024-07-24 | 589,749 | 117,776 |
| 2024-07-25 | 597,705 | 108,789 |
| 2024-07-26 | 598,708 | 108,608 |
| 2024-07-27 | 615,032 | 114,002 |
| 2024-07-28 | 593,193 | 106,897 |
| 2024-07-29 | 594,239 | 116,239 |
| 2024-07-30 | 544,404 | 103,676 |
| 2024-07-31 | 549,032 | 97,605 |
| **Total** | **17,998,955** | **3,384,056** |

All 31 cleaner bundles recorded effective `488.2 MiB`, one effective thread,
the isolated spill directory, and successful spill-directory removal. The
delivery ID is `accessais-period-c718fbfe6a3eb2d200ace41e`; the period input ID
is `multiday-ais-d66b0637fb841469f4d585a5`. The period remained `not_ready`
only because the 122 expected dates from August through November were missing;
there were 31 compatible dates and no conflicts.

Comparison of the monthly delivery and the prior seven-day evidence used their
actual delivery and period manifests. Every 15--21 July source-row count,
canonical content ID and SHA-256, cleaner run ID, cleaned-row count, and cleaned
Parquet SHA-256 matched. This includes the previously established 15--16 July
identities and proves that the entire seven-day overlap reproduced without
relying on filenames.

The first target operation took 848.101 seconds; elapsed time including imports
and the profiler barrier was 849.649 seconds. Peak sampled application RSS was
616,493,056 bytes (587.934 MiB), peak process-tree RSS was 620,728,320 bytes
(591.973 MiB), and peak private bytes were 1,051,541,504 bytes (1,002.828 MiB).
Minimum available memory was 1,774,354,432 bytes (1.652 GiB) and minimum free
disk was 17,336,774,656 bytes (16.146 GiB). The generated root peaked at
4,341,894,197 bytes (4.044 GiB) and ended at 2,489,388,135 bytes (2.318 GiB).
Isolated spill peaked at 780,500,992 bytes (744.344 MiB) and returned to zero.
No runtime threshold terminated the target.

The identical retry also returned target exit code `3` with profiler outcome
`target_completed`. It cleaned zero dates and skipped all 31 compatible July
dates. Every deterministic daily, cleaner, cleaned-Parquet, delivery, and period
identity remained unchanged; no per-date period attempt was added. The delivery
manifest alone added the expected second attempt with outcome
`identical_retry`. Final generated-root size increased by 814 bytes of retry
provenance, while the sampled transient increase was 25,774 bytes. This was not
a cold-cache run: no operating-system or application cache was cleared.

The retry target operation took 179.454 seconds; elapsed time including imports
and the profiler barrier was 181.048 seconds. Peak sampled application RSS was
74,846,208 bytes (71.379 MiB), peak process-tree RSS was 78,761,984 bytes
(75.113 MiB), and peak private bytes were 428,523,520 bytes (408.672 MiB).
Minimum available memory was 4,046,598,144 bytes (3.769 GiB), minimum free disk
was 26,424,954,880 bytes (24.610 GiB), and spill remained zero.

This successful month is bounded operational evidence for this exact July
delivery and the current resource-controlled implementation. It is not a
production vessel input, does not establish publisher-side transfer
completeness or observational completeness, and does not prove that the other
four months or the full 153-day period are safe. The evidence passed independent
audit and satisfied ADR 0017's acceptance condition. ADR 0017 now authorizes
sequential author-submitted August--November calendar-month extracts under the
same controls; it does not authorize one combined later-period request. This
outcome does not accept ADR 0018, select vessel rules, or begin exposure
analysis.

### August monthly accumulation

On 2026-09-04 the first ADR 0017-authorized later month was accumulated into the
existing July analytical-period state. The immutable author-supplied direct CSV
for **2024-08-01 through 2024-08-31** was read in place and not changed. It
contained 1,857,171,239 bytes and had SHA-256
`42cb9fbfa8623c64460c2cbfd3d878a5f4e035a746637a4bdb036657a57fc29e`,
independently confirmed before and after processing. No independently retained
HTTP `Content-Length` was available, so the command omitted
`--source-content-length` and publisher-side transfer completeness remains
`unverified`.

The run used a fresh month-specific intake directory
(`run\intake-2024-08`), a fresh isolated spill directory (`spill-2024-08`), and
fresh profile paths, while sharing the established `run\cleaned` root and
`run\period.json` manifest. Every documented control was unchanged: `512MB`, one
effective thread, the 2 GiB/8 GiB preflight, the 1 GiB/4 GiB/1 GiB/2 GiB runtime
limits, and expected target exit code `3`:

```text
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.accessais_period_intake_cli --output ..\data\interim\m3-accessais-july-month-gate\profile-2024-08-first.json --label accessais-august-month-first --disk-root ..\data\interim\m3-accessais-july-month-gate\run --spill-root ..\data\interim\m3-accessais-july-month-gate\spill-2024-08 --minimum-free-memory-gib 2 --minimum-free-disk-gib 8 --runtime-minimum-available-memory-gib 1 --runtime-minimum-free-disk-gib 4 --runtime-maximum-application-rss-gib 1 --runtime-maximum-spill-gib 2 --expected-exit-code 3 -- run --input <author-supplied-august.csv> --intake-dir ..\data\interim\m3-accessais-july-month-gate\run\intake-2024-08 --requested-start 2024-08-01 --requested-end 2024-08-31 --memory-limit 512MB --temp-directory ..\data\interim\m3-accessais-july-month-gate\spill-2024-08 --cleaned-root ..\data\interim\m3-accessais-july-month-gate\run\cleaned --period-manifest ..\data\interim\m3-accessais-july-month-gate\run\period.json
```

The retry repeated that command with the same immutable input and managed paths,
changing only the report path and label to `profile-2024-08-retry.json` and
`accessais-august-month-retry`.

The first profile passed preflight with 3,152,637,952 bytes (2.936 GiB)
available memory and 74,810,933,248 bytes (69.673 GiB) free disk. The target
returned the expected exit code `3` because the 153-date input remained
incomplete, while the profiler reported `target_completed`. It reconciled all
18,284,354 source rows: all 18,284,354 had valid in-request timestamps and were
assigned, with zero malformed or unassignable timestamps and zero valid
out-of-request rows. Exactly all 31 requested UTC dates were present and cleaned
sequentially into 3,501,843 commercial observations:

| UTC date | Source rows | Cleaned rows |
|---|---:|---:|
| 2024-08-01 | 579,387 | 104,572 |
| 2024-08-02 | 621,571 | 111,236 |
| 2024-08-03 | 631,089 | 122,224 |
| 2024-08-04 | 613,770 | 116,894 |
| 2024-08-05 | 577,247 | 113,071 |
| 2024-08-06 | 590,893 | 114,846 |
| 2024-08-07 | 585,280 | 105,986 |
| 2024-08-08 | 583,956 | 106,012 |
| 2024-08-09 | 589,442 | 103,655 |
| 2024-08-10 | 607,980 | 109,275 |
| 2024-08-11 | 617,025 | 110,457 |
| 2024-08-12 | 587,678 | 114,805 |
| 2024-08-13 | 576,143 | 117,465 |
| 2024-08-14 | 581,443 | 125,128 |
| 2024-08-15 | 584,788 | 115,260 |
| 2024-08-16 | 604,626 | 112,522 |
| 2024-08-17 | 609,416 | 120,883 |
| 2024-08-18 | 596,393 | 114,720 |
| 2024-08-19 | 581,877 | 117,333 |
| 2024-08-20 | 547,100 | 100,672 |
| 2024-08-21 | 576,130 | 108,843 |
| 2024-08-22 | 595,731 | 121,608 |
| 2024-08-23 | 580,473 | 112,517 |
| 2024-08-24 | 566,138 | 110,804 |
| 2024-08-25 | 626,142 | 118,783 |
| 2024-08-26 | 585,866 | 115,769 |
| 2024-08-27 | 568,160 | 120,056 |
| 2024-08-28 | 570,374 | 120,183 |
| 2024-08-29 | 533,538 | 95,104 |
| 2024-08-30 | 600,377 | 111,268 |
| 2024-08-31 | 614,321 | 109,892 |
| **Total** | **18,284,354** | **3,501,843** |

All 31 new cleaner bundles recorded effective `488.2 MiB`, one effective thread,
the isolated spill directory, and successful spill-directory removal. The
delivery ID is `accessais-period-9d5c80e7843e2ad9b8b2af2b`. The period input ID
moved from `multiday-ais-d66b0637fb841469f4d585a5` to
`multiday-ais-d600bc7730f03ef82658a561` because the identity derives from the
recorded per-date analytical identities and 31 dates were added. The period
remained `not_ready` with 62 compatible dates, no conflicts, and 91 missing
September--November dates.

The first target operation took 567.190 seconds; elapsed time including imports
and the profiler barrier was 568.991 seconds. Peak sampled application RSS was
607,567,872 bytes (579.422 MiB), peak process-tree RSS was 611,569,664 bytes
(583.238 MiB), and peak private bytes were 1,047,658,496 bytes (999.125 MiB).
Minimum available memory was 2,524,327,936 bytes (2.351 GiB) and minimum free
disk was 70,033,879,040 bytes (65.224 GiB). The shared generated root peaked at
6,908,288,059 bytes (6.434 GiB) and ended at 5,019,308,918 bytes (4.675 GiB);
those totals include the retained July artifacts. Isolated spill peaked at
801,865,728 bytes (764.719 MiB) and returned to zero. No runtime threshold
terminated the target.

The identical retry passed preflight with 3,461,558,272 bytes (3.224 GiB)
available memory and 71,786,319,872 bytes (66.856 GiB) free disk, and also
returned target exit code `3` with profiler outcome `target_completed`. It
cleaned zero dates and skipped all 31 compatible August dates. Every
deterministic canonical daily identity, cleaner run ID, cleaned-Parquet
checksum, delivery ID, and period input ID remained unchanged, and no per-date
period attempt was added; the delivery manifest alone recorded a second attempt
with outcome `identical_retry`. The retry operation took 171.885 seconds, peaked
at 77,766,656 bytes (74.164 MiB) application RSS, 81,920,000 bytes (78.125 MiB)
process-tree RSS, and 428,371,968 bytes (408.527 MiB) private bytes, used zero
spill, and increased the generated root by 814 bytes of retry provenance. This
was not a cold-cache run: no operating-system or application cache was cleared.

An independent read-only audit then recomputed every checksum the manifests
reference. All 31 canonical daily slice SHA-256 values matched, and all 62
recorded bundles' cleaned-Parquet, quality-report, and run-metadata checksums
matched — 186 bundle files with zero mismatches. Every one of the 31 previously
established July identities was byte-for-byte unchanged, no date was processed
twice or replaced, and the source rehash reproduced the original byte size and
SHA-256.

This successful month is bounded operational evidence for this exact August
delivery. It does not establish publisher-side transfer completeness,
observational completeness, or safe processing of September, October, November,
or the complete 153-day period. It produces no final vessel-activity input, does
not accept ADR 0018, selects no vessel rule, and begins no exposure analysis.

### September monthly accumulation

On 2026-09-04 the second authorized later month was accumulated into the same
analytical-period state. The immutable author-supplied direct CSV for
**2024-09-01 through 2024-09-30** was read in place and not changed. It
contained 1,583,433,195 bytes and had SHA-256
`0f41e63ce1afa54f4a6372e79c71a523122975351120f82a435696e7394df334`,
independently confirmed before and after processing. No independently retained
HTTP `Content-Length` was available, so the command omitted
`--source-content-length` and publisher-side transfer completeness remains
`unverified`.

The run again used a fresh month-specific intake directory
(`run\intake-2024-09`), a fresh isolated spill directory (`spill-2024-09`), and
fresh profile paths, while sharing the established `run\cleaned` root and
`run\period.json` manifest. Every documented control was unchanged. The
commands were the August pair with the month-specific paths, labels, and
`--requested-start 2024-09-01 --requested-end 2024-09-30` substituted.

The first profile passed preflight with 3,432,910,848 bytes (3.197 GiB)
available memory and 70,632,796,160 bytes (65.782 GiB) free disk. The target
returned the expected exit code `3` while the profiler reported
`target_completed`. It reconciled all 15,638,516 source rows: all 15,638,516 had
valid in-request timestamps and were assigned, with zero malformed or
unassignable timestamps and zero valid out-of-request rows. Exactly all 30
requested UTC dates were present and cleaned sequentially into 2,861,837
commercial observations:

| UTC date | Source rows | Cleaned rows |
|---|---:|---:|
| 2024-09-01 | 584,696 | 107,020 |
| 2024-09-02 | 628,250 | 108,969 |
| 2024-09-03 | 581,396 | 109,309 |
| 2024-09-04 | 564,191 | 106,717 |
| 2024-09-05 | 556,030 | 106,161 |
| 2024-09-06 | 550,292 | 94,390 |
| 2024-09-07 | 601,136 | 115,270 |
| 2024-09-08 | 602,716 | 112,037 |
| 2024-09-09 | 508,754 | 95,443 |
| 2024-09-10 | 461,596 | 87,154 |
| 2024-09-11 | 470,057 | 87,030 |
| 2024-09-12 | 532,159 | 100,889 |
| 2024-09-13 | 517,060 | 100,399 |
| 2024-09-14 | 574,050 | 101,958 |
| 2024-09-15 | 490,671 | 87,319 |
| 2024-09-16 | 462,801 | 92,408 |
| 2024-09-17 | 522,137 | 106,367 |
| 2024-09-18 | 478,445 | 96,040 |
| 2024-09-19 | 490,577 | 84,863 |
| 2024-09-20 | 503,009 | 88,778 |
| 2024-09-21 | 558,895 | 97,739 |
| 2024-09-22 | 521,021 | 96,011 |
| 2024-09-23 | 410,179 | 82,350 |
| 2024-09-24 | 456,715 | 81,404 |
| 2024-09-25 | 485,601 | 85,382 |
| 2024-09-26 | 532,488 | 96,784 |
| 2024-09-27 | 525,056 | 98,059 |
| 2024-09-28 | 573,522 | 94,126 |
| 2024-09-29 | 416,162 | 61,513 |
| 2024-09-30 | 478,854 | 79,948 |
| **Total** | **15,638,516** | **2,861,837** |

All 30 new cleaner bundles recorded effective `488.2 MiB`, one effective thread,
the isolated spill directory, and successful spill-directory removal. The
delivery ID is `accessais-period-1babd48139b3b00e3b9f6d43`, and the period input
ID moved to `multiday-ais-b4ba6bd6c418c81d6ace430c`. The period remained
`not_ready` with 92 compatible dates, no conflicts, and 61 missing October and
November dates.

The first target operation took 442.139 seconds; elapsed time including imports
and the profiler barrier was 444.190 seconds. Peak sampled application RSS was
624,009,216 bytes (595.102 MiB), peak process-tree RSS was 628,285,440 bytes
(599.180 MiB), and peak private bytes were 1,041,117,184 bytes (992.887 MiB).
Minimum available memory was 2,770,632,704 bytes (2.580 GiB) and minimum free
disk was 65,297,661,952 bytes (60.813 GiB). The shared generated root peaked at
8,782,361,709 bytes (8.179 GiB) and ended at 7,176,394,488 bytes (6.684 GiB);
those totals include the retained July and August artifacts. Isolated spill
peaked at 788,987,904 bytes (752.438 MiB) and returned to zero. No runtime
threshold terminated the target.

The identical retry passed preflight with 3,754,618,880 bytes (3.497 GiB)
available memory and 66,118,438,912 bytes (61.578 GiB) free disk, and also
returned target exit code `3` with profiler outcome `target_completed`. It
cleaned zero dates and skipped all 30 compatible September dates. Every
deterministic canonical daily identity, cleaner run ID, cleaned-Parquet
checksum, delivery ID, and period input ID remained unchanged, and no per-date
period attempt was added; the delivery manifest alone recorded a second attempt
with outcome `identical_retry`. The retry operation took 136.475 seconds, peaked
at 77,262,848 bytes (73.684 MiB) application RSS, 81,416,192 bytes (77.644 MiB)
process-tree RSS, and 425,447,424 bytes (405.738 MiB) private bytes, used zero
spill, and increased the generated root by 801 bytes of retry provenance. This
was not a cold-cache run: no operating-system or application cache was cleared.

An independent read-only audit recomputed all 30 canonical daily slice SHA-256
values and all 276 recorded cleaned-bundle file checksums with zero mismatches.
Every previously established July and August identity was unchanged, no date was
processed twice or replaced, and the source rehash reproduced the original byte
size and SHA-256.

This successful month is bounded operational evidence for this exact September
delivery. It does not establish publisher-side transfer completeness,
observational completeness, or safe processing of October, November, or the
complete 153-day period. It produces no final vessel-activity input, does not
accept ADR 0018, selects no vessel rule, and begins no exposure analysis.

### Verified one-day compatibility exercise

On 2026-08-28 the new `run` path read the permitted 2024-07-15 AccessAIS CSV
without modifying it. The 59,497,346-byte source still had SHA-256
`694ea3e8364de21467dea0affeb77e954d339e155d316dc4115b87ac01ffcca3`.
Streaming intake reconciled all 582,419 rows to that requested date, with zero
malformed/unassignable timestamps and zero out-of-request rows. The generated
daily slice was byte-identical to the direct CSV and had the same checksum.

The orchestration reproduced cleaner run ID `ais-362502c6a37b53e681b745f5`,
113,799 cleaned rows, and cleaned-Parquet SHA-256
`efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`.
It recorded delivery ID `accessais-period-71ac80a3b7ff60cbc8748b8c` and the
existing path/clock-independent period input ID
`multiday-ais-aeaf8f584d830ed98ef2b52d`. The period correctly remained
`not_ready` with one compatible and 152 missing dates. Independent transfer and
observational completeness both remained `unverified`.

A directly spawned end-to-end CLI process took 83.735669 seconds under a
0.01-second process-tree RSS sampling protocol and showed an approximate
990.379 MiB peak across 1,669 samples. The interval includes direct-CSV
fingerprinting, streaming partitioning, generated-slice validation, the daily
cleaner, and period recording; it excludes the outer uv measurement-wrapper
startup. Sampling adds overhead and can miss a peak. Its method differs from
the earlier approximately 1.59 GiB one-day cleaner observation, so the numbers
are not directly comparable. This is one direct-CSV date, not a monthly or
multi-date scaling result, and no value is extrapolated to 153 dates.

The same immutable source was rerun read-only through the updated accumulation
gate on 2026-08-30 under ignored `data/interim/`. It retained the same
59,497,346-byte source SHA-256, reconciled all 582,419 rows to 2024-07-15,
emitted the same byte-identical daily slice, and reproduced the 113,799-row
cleaner run ID and cleaned-Parquet SHA-256 above. A second invocation was an
identical delivery retry and skipped the already compatible date. The period
remained `not_ready` with one compatible and 152 missing dates; transfer and
observational completeness remained `unverified`. This repeated one-day
regression is not real multi-date evidence and includes no new runtime or
memory claim.

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
python -m uv run whale-vessel-analysis process-ais --input <one-ais.csv> --memory-limit 512MB --temp-directory ..\data\interim\ais-cleaner-spill --output-dir <new-output-directory> [--threads 1]
```

The explicit memory limit and spill parent are required; the default thread
count is one. Omitting `--config` uses the packaged configuration. Supply an
equivalent versioned TOML file with `--config <config.toml>`. The command refuses any
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
production threshold was selected. Four candidate combinations crossing
300/1,800-second maximum gaps with 30/50-knot implied-speed ceilings were
exercised on this one bounded day, including real per-cell effects. Period-wide
stability and production thresholds remain unresolved. Source-transfer and
observational completeness remain unverified; one day does not validate the
analytical period; edge-support treatment remains unresolved; and no production
vessel grid or exposure result exists.

## Candidate multi-day vessel-grid aggregation

The focused `vessel_grid_cli` promotes the reusable consecutive-pair,
plausibility-filter, exact-intersection, conservation, and distinct-union logic
from the evidence harness into a bounded multi-day processing boundary. It
consumes one existing `multiday_cleaned_ais_input_v1` manifest through the
bounded DuckDB relation and one exact `projected_water_grid_v1` GeoParquet. It
does not read raw AIS, discover adjacent files, or concatenate the period in
Python.

Every methodological choice needed by the command is required at runtime; none
has an analytical default:

```text
python -m uv run python -m whale_vessel_analysis.vessel_grid_cli --manifest <period-manifest.json> --grid-input <water-grid.parquet> --output-dir ..\data\derived\<candidate-bundle> --maximum-gap-seconds <candidate-seconds> --implied-speed-ceiling-knots <candidate-knots> --period-readiness-treatment <require-ready|allow-incomplete-candidate> --edge-treatment censor-at-cleaned-extent --support-treatment exact-water-geometry-exclude-and-report --memory-limit <size-with-unit> --temp-directory ..\data\interim\<duckdb-spill> [--expected-grid-sha256 <sha256>] [--threads <n>] [--batch-size <rows>] [--config <config.toml>] [--overwrite]
```

`--maximum-gap-seconds` and `--implied-speed-ceiling-knots` are explicit
candidate assumptions, not accepted rules. The exclusion precedence is invalid
coordinate transformation, non-increasing time, vessel-group change, maximum
gap, then implied speed. The implied speed is EPSG:3310 projected endpoint
distance divided by elapsed time; reported SOG is not substituted for it. The
command has no vessel-length option: length filtering remains disabled and
unresolved because AIS length is not gross tonnage and no defensible mapping to
the program's approximately 300 GT population has been accepted.

The two single-choice treatment arguments are deliberately still required:

- `censor-at-cleaned-extent` records that the upstream cleaner removed points
  outside the map/context extent. The command does not invent entry or exit
  paths before the first or after the last retained observation.
- `exact-water-geometry-exclude-and-report` allocates only line length inside
  the exact modeled-whale-support water geometry. Outside-support portions are
  reported separately and are not called land or absent AIS coverage.

`require-ready` refuses a period manifest unless all 153 accepted dates are
compatible. `allow-incomplete-candidate` permits an explicitly partial
candidate run while retaining the manifest's missing-date inventory and
unverified observational-completeness state in output metadata. It does not
upgrade or imply analytical-period completeness.

### Pairing, allocation, and ambiguity

DuckDB forms `lead` pairs per MMSI in the deterministic whole-period order
`mmsi`, UTC timestamp, latitude, longitude, vessel type code, vessel group.
UTC dates do not partition the window, so a valid cross-midnight pair is
treated like any other pair. Ordered rows stream to Python in bounded Arrow
batches under the explicit DuckDB memory and spill settings.

For each retained positive-length pair, the command constructs one straight
segment in EPSG:3310 and splits it across intersected exact water geometries.
Each segment's allocated, outside-support, ambiguous-boundary, and invalid-
geometry distances must reconcile to its parent length within an absolute
`1e-6` metre and relative `1e-12` tolerance. Per-cell output totals must also
reconcile with allocated piece distance.

Zero-length pairs are retained as valid candidate segments and contribute zero
vessel-kilometres. Their location is reported as unambiguous in-support,
outside-support, or multiple-cell boundary ambiguity. A positive-length segment
coincident with overlapping cell boundaries is not assigned arbitrarily: its
in-support union length is reported as ambiguous-boundary distance and excluded
from cell totals. Invalid source values fail the verified input boundary;
unexpected intersection failures are separately counted and their parent
distance stays visible in conservation accounting.

Every cleaned point is independently classified against exact cell support for
descriptive vessel counts. A point is assigned only when exactly one cell
covers it; no match is outside support and multiple matches are ambiguous.
`distinct_mmsi_all_commercial` and `distinct_mmsi_dates_all_commercial` are
recomputed from the underlying union of commercial identities in that cell.
They are never sums of passenger, cargo, and tanker distinct counts.

### Candidate output bundle

The output is one named atomic directory beneath ignored `data/derived/`:

| File | Contract and purpose |
|---|---|
| `vessel-grid.parquet` | Deterministic GeoParquet 1.1.0 under `candidate_vessel_grid_v1`, in exact water-grid row order with target geometry preserved byte for byte. |
| `quality-report.json` | Deterministic `candidate_vessel_grid_quality_v1` metadata: source identities, explicit parameters, observation and segment populations, exclusions, support/ambiguity counts, and conservation checks. |
| `run-metadata.json` | `candidate_vessel_grid_lineage_v1` execution lineage with actual UTC timestamps, local source locators, input/output checksums, software versions, processing steps, and validation records. |

The GeoParquet preserves the target identity, parent bounds, actual water area,
and geometry fields. For passenger, cargo, tanker, and all commercial vessels,
it adds:

- `vessel_km_<group>`;
- `vessel_km_per_water_km2_<group>`, using the stored modeled-support water area;
- `distinct_mmsi_<group>`; and
- `distinct_mmsi_dates_<group>`.

All target cells are present, including zero-activity cells. The grid and
quality-report bytes are deterministic for unchanged verified inputs,
configuration, parameters, and code. Real execution timestamps occur only in
run metadata and do not affect the content-derived candidate grid ID.

Deterministic identity and output metadata use the path- and clock-independent
`period_input_id`, stable readiness and observational-completeness states, and
the recorded cleaned-partition identities. The exact period-manifest SHA-256 is
execution provenance: it is retained in `run-metadata.json` but excluded from
the candidate ID, GeoParquet metadata, and deterministic quality report. Thus
an identical retry or equivalent regeneration in another worktree does not
change the analytical output identity merely because manifest paths,
timestamps, or attempt history changed.

`run-metadata.json` also records the requested and effective DuckDB memory
limit and thread count, the Arrow batch size, and that an isolated spill
directory was configured beneath ignored `data/interim/`. The local spill path
is omitted. These operational settings support execution diagnosis but do not
participate in deterministic analytical identity.

The writer refuses `data/raw/`, any destination outside `data/derived/`, the
derived root itself, input/output overlap, an existing destination without
`--overwrite`, and overwrite of anything except a complete bundle carrying its
own lineage contract. It builds all three files in a unique sibling temporary
directory and publishes the bundle by directory rename; a failed publication
leaves no partial target.

Synthetic tests cover cross-midnight continuity, multi-cell splitting, gap and
implied-speed exclusions, distance conservation, zero-length and outside-
support handling, boundary ambiguity, group/additive vessel-kilometres,
union-recomputed distinct counts, deterministic Parquet and JSON bytes, invalid
parameters and inputs, atomic failure, overwrite, raw-output refusal, and the
CLI's lack of hidden methodological defaults. Regression coverage also proves
that volatile manifest provenance cannot change deterministic candidate output,
and that the evidence and candidate paths agree on retained populations,
gap/implied-speed exclusions, per-cell vessel-kilometres, and commercial totals
for a shared nonambiguous synthetic population.

That parity claim is deliberately limited. The evidence path materializes one
cleaner bundle and additionally reports geodesic comparisons and evidence-only
vessel-hours; the candidate path streams the bounded multi-day relation,
classifies ambiguous intersections without publishing them to cells, and writes
the versioned candidate bundle. Those intentional boundary-specific behaviors
are not asserted to be identical.

### Verified two-day candidate exercise

On 2026-09-01, a fresh ignored root was used to reproduce the author-supplied
2024-07-15 through 2024-07-16 AccessAIS delivery and run the four candidate
combinations in [ADR 0018](../docs/decisions/0018-use-vessel-kilometres-for-grid-activity.md).
This is two-day candidate vessel-activity evidence, not an analytical-period or
production input. The source CSV was 115,791,285 bytes with SHA-256
`a6c673f37ccd01d30067c400452275b13f8c5299200777384a513bc46d6842a0`.
The exact 437,466-byte water grid had SHA-256
`7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`.
Both inputs were used read-only.

The fresh intake command used the full accepted requested period and explicit
bounded DuckDB resources:

```text
python -m uv run python -m whale_vessel_analysis.accessais_period_intake_cli run --input <2024-07-15-through-2024-07-16.csv> --intake-dir ..\data\interim\m3-two-day-vessel-candidate-evidence\period\delivery-two-day --requested-start 2024-07-01 --requested-end 2024-11-30 --memory-limit 1GB --temp-directory ..\data\interim\m3-two-day-vessel-candidate-evidence\period\duckdb-spill --cleaned-root ..\data\interim\m3-two-day-vessel-candidate-evidence\period\cleaned --period-manifest ..\data\interim\m3-two-day-vessel-candidate-evidence\period\period-manifest.json
```

All 1,135,408 rows were assigned: 582,419 to 15 July and 552,989 to 16
July. Malformed/unassignable and out-of-request row counts were both zero. The
regenerated identities matched the existing canonical evidence:

| Date | Cleaner run ID | Cleaned observations | Cleaned-Parquet SHA-256 |
|---|---|---:|---|
| 2024-07-15 | `ais-9fc49e14601edea30064df97` | 113,799 | `efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6` |
| 2024-07-16 | `ais-e1ea93fe9ab4b4d068364a0c` | 104,506 | `cb37b96a9f3e56838ca492a33dffc57a174fc92c1d385d3f3a1e848d2f7fbc5c` |

The period ID was `multiday-ais-ddf23ba501bc834dbe5a2656`. It contained only
15 and 16 July, retained all other 151 accepted dates as missing, and remained
`not_ready`. Transfer completeness and observational completeness both remained
`unverified`. The first end-to-end intake took 23.5578823 seconds with an
approximate sampled process-tree RSS peak of 1,385,132,032 bytes. Recursive disk
use under the fresh root rose from zero to a sampled peak of 270,186,568 bytes
and ended at 157,756,801 bytes. An identical retry took 11.453405 seconds,
sampled 107,479,040 bytes peak RSS, skipped both compatible dates, returned the
same period ID and `not_ready` state, and added only 2,399 bytes of retry
lineage. The profiler sampled the process tree and recursive output size while
the commands ran; WMI sampling overhead makes the peak RSS values approximate.

The bounded scan command was:

```text
python -m uv run python -m whale_vessel_analysis.multiday_ais_cli scan --manifest ..\data\interim\m3-two-day-vessel-candidate-evidence\period\period-manifest.json --memory-limit 2GB --temp-directory ..\data\interim\m3-two-day-vessel-candidate-evidence\scan-spill --threads 4 --batch-size 50000
```

It read 218,305 cleaned observations from the two verified partitions, found
216 distinct MMSIs and 376 distinct MMSI-date combinations, and reported
218,089 whole-period consecutive pairs. Artificially partitioning pairing by
UTC date would lose 160 pairs for 160 MMSIs; these are the cross-date and
cross-midnight candidates retained by the whole-period boundary. Timestamp
bounds do not establish continuous coverage.

Each matrix run used this explicit command shape, a distinct ignored output and
spill directory, and no vessel-length filter:

```text
python -m uv run python -m whale_vessel_analysis.vessel_grid_cli --manifest ..\data\interim\m3-two-day-vessel-candidate-evidence\period\period-manifest.json --grid-input <water-grid.parquet> --expected-grid-sha256 7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031 --output-dir ..\data\derived\m3-two-day-vessel-candidate-evidence\<candidate-run> --maximum-gap-seconds <300|1800> --implied-speed-ceiling-knots <30|50> --period-readiness-treatment allow-incomplete-candidate --edge-treatment censor-at-cleaned-extent --support-treatment exact-water-geometry-exclude-and-report --memory-limit 2GB --temp-directory ..\data\interim\m3-two-day-vessel-candidate-evidence\<candidate-spill> --threads 4 --batch-size 50000
```

| Gap (s) / speed (kn) | Candidate ID | GeoParquet SHA-256 | Quality-report SHA-256 |
|---|---|---|---|
| 300 / 30 | `candidate-vessel-grid-38a2981d2ffe9800a19c9128` | `93e7b3ce9266e9440ce353918b836851a9049c8c956f587e206d761dd79daef4` | `0f9c5d612396fef6a3eac90a4f7684eb50697497a96ae8c25d99918de8054008` |
| 300 / 50 | `candidate-vessel-grid-fb0e0545c33c15e0b813e540` | `2995b498b611344afc248ff42e4574d8de740e74eb76477aea6df69159fe5dea` | `ad4d075e8b4c8d58b913d2491ade3156ce0ac001c51fbffc29095f9c0ee8e8ca` |
| 1,800 / 30 | `candidate-vessel-grid-728edacffd6828d4eaca073c` | `f9be10e3b66d2f6f5fea561165ea554492e0c74ef827b2cfba39cc88f0451226` | `6005b7fe6040742cc286589eab75d686569a57c9de4e4c6dbaf3d357e03f22bb` |
| 1,800 / 50 | `candidate-vessel-grid-2995c7fe4a19811136b13864` | `9173ae5f41e64597bfa9e51309f03bb07f1906d41aef99c83ede778c1d98f209` | `f8bfdc0d6f737f4802816a857e662997b2d85afa10bc76bf2801c5d5bee68be8` |

All runs had 218,305 input observations and 218,089 structural segments. The
candidate-specific populations and allocated distance were:

| Gap / speed | Retained | Gap excluded | Speed excluded | Zero length | Cross-midnight retained | Vessel-km passenger / cargo / tanker / commercial | Outside support (km) | Distance-touched cells |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 300 / 30 | 211,622 | 5,457 | 1,010 | 17,968 | 130 | 7,891.472333 / 10,576.065554 / 6,656.297745 / 25,123.835632 | 2,450.085067 | 1,659 |
| 300 / 50 | 211,803 | 5,457 | 829 | 17,968 | 130 | 8,048.168251 / 10,615.409865 / 6,662.404240 / 25,325.982357 | 2,466.441784 | 1,660 |
| 1,800 / 30 | 216,694 | 352 | 1,043 | 18,566 | 150 | 8,132.620627 / 11,052.655987 / 6,871.961152 / 26,057.237766 | 2,524.339706 | 1,679 |
| 1,800 / 50 | 216,877 | 352 | 860 | 18,566 | 150 | 8,289.316545 / 11,126.251145 / 6,878.067647 / 26,293.635337 | 2,540.696423 | 1,680 |

All four reports passed their own validation and distance-conservation checks
at the recorded `1e-6` metre absolute and `1e-12` relative tolerances. Invalid
intersection geometry and positive-length boundary-ambiguity counts were zero;
one cleaned point was a multiple-cell boundary ambiguity in every run. Maximum
per-segment distance differences were zero or `2e-12` metres, and aggregate
differences were between `-4.02331e-7` and `-4.39584e-7` metres. The independent
point context was candidate-invariant: 1,652 cells were touched by points.

Raising the speed ceiling from 30 to 50 knots changed 137 cells at the
300-second gap and 140 at the 1,800-second gap, adding one positive-distance
cell in each comparison. Raising the gap from 300 to 1,800 seconds changed 305
cells and added 20 positive-distance cells at either speed ceiling. These are
sensitivity observations for two dates, not evidence that either value is a
production rule.

The 15 July cleaner retained 113,799 observations, while 16 July retained
104,506, 9,293 fewer. The second date nevertheless had more distinct MMSIs in
each group: passenger 72 versus 67, cargo 75 versus 67, and tanker 50 versus 45.
These are observed differences between the two cleaned partitions; they do not
establish continuous coverage or explain the difference.

All four candidates were repeated to distinct output directories. Each repeat
reproduced the exact candidate ID, GeoParquet bytes/checksum, and deterministic
quality-report bytes/checksum. Time-bearing `run-metadata.json` checksums
differed, as intended. The shared synthetic parity tests passed as the contract
comparison. The real evidence harness and multi-day candidate outputs cover
different populations, so no additional real-output byte-parity claim is made.

Profiled candidate runs took 28.0991472 to 32.2055495 seconds. Approximate
sampled process-tree RSS peaks ranged from 271,245,312 to 289,746,944 bytes.
Each completed bundle occupied 565,696 to 566,404 bytes, and no persistent spill
files remained. These bounded observations include profiler overhead and are
not monthly or full-period scaling evidence.

The exact four candidate GeoParquet files were opened directly in QGIS
4.2.1-Belém do Pará on 2026-09-01. Each loaded as 4,516 EPSG:3310 MultiPolygon
features with zero null, empty, or invalid geometries. Full-domain,
Southern-California shipping-lane, northern support-edge, southern support-edge,
and contextual 2026 VSR-boundary views were inspected after correcting the
render order and context rule styling so the blue accepted-domain and orange
VSR outlines appeared above the opaque candidate grid. Every corrected image
contained both configured exact RGB colors: 23,306--29,307 blue pixels and
4,650--8,400 orange pixels. Manual review confirmed both outlines were visibly
present. The broad coastal and shipping-corridor concentrations, zero/nonzero
cells, grid alignment, support
clipping, and isolated route cells were plausible and consistent across the
matrix; no projection shift, geometry gap, unexplained clipping, or anomalous
band was found. Positive/zero cell counts in table order were 1,659/2,857,
1,660/2,856, 1,679/2,837, and 1,680/2,836. The longer gap produced the clearest
visible additions; speed-ceiling differences were subtle. The corrected ignored
render report has SHA-256
`8b4f079da39e3aecff018eb3c2a625259005a015028ce9a8275e6e06c41a2da0`.
The rendered views and render report were not committed. The VSR boundary was
context only and was not used in candidate construction or exposure analysis.

Only 15--16 July 2024 were processed through this candidate vessel-grid
exercise. Its full 2024-07-01 through 2024-11-30 analytical input is still
missing 151 dates. Independent transfer completeness, observational completeness,
later-month and full-period candidate-processing safety, alternative edge
support, accepted thresholds, and a final vessel-activity input remain
unverified. No production maximum-gap or implied-speed threshold was selected,
no absent traffic outside the qualified receiver domain was interpreted as
zero, and no exposure analysis was performed. ADR 0018 remains Proposed.

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
