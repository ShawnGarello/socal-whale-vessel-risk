# 0012 — Use DuckDB for large-tabular processing

**Status:** Accepted
**Date:** 2026-08-26

## Context

The AIS input cannot be designed around an in-memory pandas or GeoPandas
workflow. M2 estimates 60–90 million study-area records over the analytical
period, and the confirmed bulk route would transfer roughly 56 GB of compressed
national daily files. M3 therefore needs one primary engine that can select,
parse, filter, and aggregate tabular files without first materializing the full
period as Python objects.

DuckDB 1.5.5 and Polars 1.44.1 were compared with the committed, parameterized
command in `analysis/src/whale_vessel_analysis/benchmark.py`. The benchmark was
run on 2026-08-26 with Python 3.13.7 on Windows 11, using psutil 7.2.2.

### Input

- `AIS_2024_07_15.head_sample.csv`, the M2 inspection artifact generated from
  the first 8 MiB of that day's zip stream;
- 22,723,368 bytes and 207,849 data rows; and
- SHA-256
  `228247d2d6ede6c9d38602f388577b78c59697a19059918bcbcf69495b309e6d`.

The file remains outside this worktree under the ignored data-discovery root.
The benchmark received its path as a command argument and did not write to or
modify it.

### Operation

Both candidates performed the same operation:

1. scan the CSV and project `MMSI`, `BaseDateTime`, `LAT`, `LON`, `SOG`,
   `VesselType`, and `Length`;
2. parse `BaseDateTime` as the documented UTC timestamp and parse the numeric
   fields;
3. filter to the map extent from then-proposed ADR 0002 — longitude −122.0 to −117.0
   and latitude 32.0 to 35.0 — while excluding invalid timestamps;
4. treat the documented `SOG` value 102.3 as unavailable; and
5. group by vessel-type code, returning row count, distinct MMSI, valid-speed
   count, mean valid SOG, and mean available length.

Each engine ran in a fresh child process. One unreported run per engine warmed
the operating-system file cache, followed by five measured runs in alternating
engine order. The measured child imports its engine inside the timed operation,
so elapsed time explicitly includes module import as well as the
scan-through-aggregation operation. The warm-up child is separate and therefore
does not warm Python imports for measured runs. A 5 ms sampler recorded
approximate process resident memory; the initial RSS is sampled immediately
before the timed operation, the total peak includes the imported engine, and
the increase includes import and operation. RSS is an approximation rather than
an allocation profile.

### Results

Both engines returned 13,800 filtered rows in 35 vessel-type groups. Counts,
distinct-MMSI counts, sentinel-aware speed counts, and means were equivalent;
the command would have exited non-zero if they were not.

| Engine | Elapsed, five runs (s) | Median elapsed (s) | Peak RSS, five runs (MiB) | Median peak RSS (MiB) | Median RSS increase (MiB) |
|---|---|---:|---|---:|---:|
| DuckDB 1.5.5 | 0.299, 0.316, 0.265, 0.268, 0.255 | **0.268** | 79.9, 75.6, 74.6, 77.8, 79.2 | **77.8** | **53.5** |
| Polars 1.44.1 | 0.424, 0.304, 0.433, 0.332, 0.298 | **0.332** | 124.9, 120.8, 122.1, 119.4, 117.0 | **120.8** | **96.7** |

DuckDB was about 19% faster by the median elapsed measurement and used about
36% less total peak RSS in this run. Those percentages describe this input,
operation, machine, and warm-cache protocol only.

## Decision

DuckDB is the primary production engine for M3 large-tabular AIS work. Runtime
code uses DuckDB's file scans and SQL projection, parsing, filtering, and
aggregation as the common pipeline boundary. A later slice does not introduce
a separate Polars production path without a concrete operation DuckDB cannot
serve and a decision superseding this one.

`duckdb` is a runtime dependency. `polars`, `psutil`, and the psutil typing stubs
remain in a separate benchmark dependency group solely so the evidence can be
re-run. Polars is not a production dependency.

## Consequences

- Retrieval and vessel-aggregation slices share one query model and do not
  build competing dataframe pipelines.
- The foundation's AIS validation surface uses the same engine selected for
  later bulk processing, giving the dependency an implemented runtime purpose.
- File projection and aggregation stay inside the engine rather than loading a
  whole season into pandas or GeoPandas. Later work must still prove the actual
  daily and full-period query plans and memory behavior; selecting DuckDB does
  not make those checks optional.
- The benchmark remains reproducible without committing its input or generated
  output. It prints JSON to standard output from a supplied path.
- The environment carries extra benchmark-only packages locally because the
  default development sync includes that group. They are absent from the built
  package's runtime requirements.

### Limits of the evidence

This benchmark does **not** prove full-season performance. The input is one
22.7 MB prefix covering roughly half an hour, its pages were warm in the
operating-system cache, and neither candidate had to spill or combine many
files. Startup cost is large relative to the measured operation. The result
supports choosing one foundation engine; it does not support extrapolating the
elapsed times or memory figures to 60–90 million rows.

The production route must be measured again on at least one complete scoped
day before its resource behavior is described as established, and the
full-period workflow must keep processing bounded rather than assume the
benchmark scales linearly.

## Alternatives considered

**Polars as the primary engine.** It produced equivalent results and is a
credible streaming dataframe engine. It was not selected because DuckDB was
both faster and lower-memory for the tested operation, while SQL is a direct fit
for the projection, filtering, grouping, and multi-file scans M3 needs. Polars
remains in the reproducible benchmark group so the evidence can be challenged.

**Retaining both in production.** Rejected. Two implementations of each AIS
step would double the validation surface and allow later slices to diverge. The
sample showed no concrete operation that required both.

**pandas or GeoPandas for the AIS table.** Rejected for the bulk path because
the planning estimate makes an all-records-in-memory design unacceptable.
GeoPandas may still be appropriate for small spatial products, but it is not a
large-tabular AIS engine.

**PyArrow alone.** Not benchmarked as a candidate. It is a lower-level columnar
foundation rather than the query boundary this task needs; selecting it would
require the project to assemble more scanning and aggregation behavior itself.

**A distributed engine.** Not evaluated. The project has one local analytical
period, no cluster, and no evidence that distributed operational surface is
needed. A complete-day measurement is the next evidence gate before considering
one.
