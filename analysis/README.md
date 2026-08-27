# Analysis

This directory is the Python package for the M3 offline-processing workflow. It
provides versioned spatial and source-input contracts, read-only validators,
traceable lineage metadata, and a real one-extract AIS cleaning command. It does
not retrieve AIS, process a season implicitly, aggregate vessel activity onto
the analysis grid, calculate relative exposure, or report inside-versus-outside
statistics.

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

## Process one AIS extract

`process-ais` requires one explicit NOAA Marine Cadastre flat CSV extract and
one explicit output-bundle directory. It never discovers adjacent files,
expands a date range, downloads data, or writes into `data/raw/`. The extract
must contain at least one data row and one valid timestamp, and all valid
timestamps must fall on exactly one UTC calendar date.

A partial-day extract is valid input. The command does not infer that the CSV
covers every instant or record in that date: completeness is reported as
`unverified` unless a future retrieval boundary supplies retained metadata that
can prove otherwise. The processing contract is
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
