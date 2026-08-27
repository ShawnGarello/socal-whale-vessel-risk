# Analysis

This directory is the Python package for the M3 offline-processing foundation.
It provides versioned spatial and source-input contracts, deterministic lineage
metadata, read-only input validation commands, and the reproducible toolchain
that later retrieval, whale-processing, grid/water, and vessel-aggregation work
will use. It does not retrieve data, clean or aggregate AIS, produce derived
datasets, calculate relative exposure, or report inside-versus-outside
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
