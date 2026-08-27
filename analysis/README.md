# Analysis

This directory is the Python package for the M3 offline-processing workflow. It
provides versioned spatial and source-input contracts, read-only validators,
traceable lineage metadata, a real one-extract AIS cleaning command, and
construction of the exact EPSG:3310 analysis grid with actual per-cell water
geometry from an explicitly supplied polygon mask. It does not retrieve AIS or
process a season implicitly, transfer whale values, aggregate vessel activity
onto the grid, calculate relative exposure, or report inside-versus-outside
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

The generated lineage sidecar remains immutable evidence of the generation run
and records `visual_inspection_status: not_completed` because generation
finished before QGIS inspection. The later QGIS report and documentation are
separate verification evidence tied to the output SHA-256 above; they do not
require manually editing the sidecar. Future reusable verification evidence is
planned to record the checksum, date, GIS tool/version, inspected views/checks,
result, and relevant observations. No formal verification record or command is
implemented yet; [the roadmap](../docs/roadmap.md) carries that follow-up.

QGIS is an inspection and visual-verification tool, not a production processing
path. Any result-changing transformation discovered during review must be
implemented in Python with configuration, tests, and lineage before a new
artifact is generated.

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
