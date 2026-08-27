# Analysis

This directory is the Python package for the M3 offline-processing foundation.
It currently provides a runnable command-line boundary and the reproducible
toolchain that later retrieval, whale-processing, grid/water, and
vessel-aggregation work will use. It does not yet retrieve data, produce
derived datasets, calculate relative exposure, or report inside-versus-outside
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
