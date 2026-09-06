# M6 exposure foundation handoff

**Date:** 2026-09-06. **Branch:** `feat/m6-exposure-foundation`.
**Worktree:** `C:/Users/teche/socal-whale-vessel-risk-exposure-foundation`.
This handoff accompanies the exposure branch; use
`git log -1 --format=%H` in this worktree to identify its exact committed head.
It is navigation and execution evidence, not the owner of milestone status.

## Current continuation — exploratory production authorized

The owner authorized the ADR 0020 method and documented sensitivity checks for
exploratory execution on 2026-09-06. Results must return for audit/review before
final headlines or M6 completion. Speed stays separate. M5 owns parallel
integration documentation; shared roadmap/architecture/development/README/index
files remain untouched. No push, merge or rebase is authorized.

Implementation adds `exposure_inputs.py` (exact retained input join), `exposure.py`
(formula, weighted thresholds, scaling controls and coarser-grid sensitivity),
and `exposure_run.py` (fresh local deterministic bundle with read-back verification).
Current focused suite: 50 tests passed, including the 23 foundation cases.
Production and repeat runs completed, with byte-identical numerical outputs.
The foundation-only statements below the history heading describe the earlier
commit, not the current implementation. **M6 remains incomplete.**

Predeclared run controls: process the small retained grid tables only, no AIS
regeneration and no cache clearing. Sequential first/repeat execution through
the existing resource profiler; preflight minimum 2 GiB available memory and
20 GiB free disk, runtime minimum 0.5 GiB available memory and 12 GiB free disk,
maximum application RSS 1.75 GiB. These retain the established M3 safeguard
values rather than weakening them for this run. A read-only preflight observed
2.56 GiB available RAM and 42.28 GiB free disk before execution. Stop at a failed
gate; preserve any failed profile, console and temporary output. Fresh output
names are `data/derived/m6-exposure-first` and `m6-exposure-repeat`, profiles under
`data/interim/m6-exposure-first-profile` and `m6-exposure-repeat-profile`.

The run is bounded grid-level work, not a memory-intensive five-month process.
Only one of this session's analytical processes runs at a time. Visual inspection
followed computation rather than running alongside it.

### Production results returned for audit

These are exploratory overlap results, not collision probabilities, predicted
strikes, or final headlines. Product intensity is modeled whale density times
period vessel distance per water area. Integration uses exact qualified water
and its joint intersection/difference with the immutable VSR snapshot, assuming
uniform intensity within each water cell. Speed is not part of either formula.

| Grid / method | Integrated exposure inside VSR | High-area inside, p80 | p90 | p95 |
| --- | ---: | ---: | ---: | ---: |
| 5 km product (primary) | 92.2185% | 93.6947% | 98.5024% | 99.9401% |
| 10 km product | 92.2463% | 97.8430% | 98.3551% | 99.8296% |
| 5 km log traffic | 74.9444% | 83.8098% | 94.9461% | 96.9418% |
| 10 km log traffic | 76.0494% | 87.2831% | 97.7780% | 99.8395% |

The first numeric column is an integrated-exposure share, while the last three
are fractions of selected high-exposure **water area**. Thresholds use the
qualified-area-weighted observed quantile, include zeros in the reference and
include all ties. They do not select an exact fixed percentage of cells or area.
Qualified area is 64,716.65982166734 km² at both resolutions. The 5-km layer has
4,516 rows: 2,793 qualified, 1,723 excluded and 137 qualified product zeros.
The 10-km layer has 1,155 rows: 738 qualified, 417 excluded and 18 zeros.

Primary integrated total is 6,536.657810883277 modeled animals·vessel-km/km²
for the fixed period: inside 6,028.008180683845, outside 508.6496301994318.
The 10-km product total is 6,536.21639950733, a change of -0.006753%; its inside
share changes +0.027805 percentage points. Coarsening sums abundance, distance
and water before recomputing intensity; it does not average fine-grid products.
Water, abundance and distance conservation passed. Maximum area residual was
1.258e-7 m², below declared tolerances.

Log compression reduces the 5-km inside share by **17.2741 percentage points**.
This is material dependence on the question/formula, not a confidence interval.
Its integrated magnitude has different units and must not be compared with the
product magnitude. Log-grid coarsening changes its total +6.0009% and inside share
+1.1050 points. Product integrated shares are stable to this grid comparison,
but the p80 high-area share changes about 4.15 points; do not generalize the
integrated stability to every statistic.

Positive-only threshold references were also run at all three percentiles.
For primary 5-km product, inside high-area shares become 94.4566%, 98.6146%,
99.9384%; high areas are 12,485.0303, 6,249.9212, 3,132.1006 km² respectively.
All-valid primary thresholds are 0.07199053772739933, 0.22859788468419606,
0.4978252635376552 in physical intensity units; selected areas are
12,959.502194504206, 6,473.820081391964, 3,254.939659778515 km². Threshold tie
areas are 25, 12.39240714173421, 22.83904883768595 km². Full positive-only and
all-valid results for every scenario, including cell membership, are retained
in `sensitivity-report.json`.

Both global positive scaling controls preserve every threshold membership and
integrated share (largest floating share difference 2.22e-16). This is an
algebraic check, not independent scientific robustness. Product/log cell-rank
Spearman correlation is 0.959254 at 5 km and 0.957982 at 10 km, with maximum
rank shifts 918 and 240. At 5 km their top-ten outside contributor lists share
only five cells. Product's leading outside cells are `r015_c079`, `r015_c078`,
`r016_c054`; together with the remaining seven the list contributes 9.4717% of
outside exposure. Log's leaders are `r016_c054`, `r015_c054`, `r010_c055`; its
top ten contribute 3.6375%. These are contribution rankings, not validated
hotspot clusters. Origins and all contributions are in the retained report.

### Exact outputs and reproducibility

Paths below are relative to this worktree. Run identity:
`exposure-cc50a1e9fb06ca3ae5b5e395`. First bundle:
`data/derived/m6-exposure-first`; repeat: `data/derived/m6-exposure-repeat`.
Both bundles have these identical SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `exposure-5km.parquet` | `5eb1c3ac085d80d27ac698258068be42e5f32d6533a752cf819269fcac81980c` |
| `exposure-10km.parquet` | `2b9fbd9dd92c2157568acb35846eb6bb5212f4a6ea9e6e221de78befab80f602` |
| `sensitivity-report.json` | `770cbf8a9f522d20745ebfe7e5ea36eb8715d09feaa9cedf6c846d4d41cceec9` |

Generation `run-metadata.json` hashes differ as expected for timestamps/paths:
first `5432605adaa6f8649c06c4b3688704587ef6b42e1b7d8840c61fde55d45114b9`,
repeat `631b84c0b3efa537255849d3dcc09d695d50356872d231a04ca4d997505c1865`.
Original input identities and their M3 verification are retained in the historical
input inventory below and pinned by `exposure_inputs.py`. No inputs or
generation-time sidecars were modified.

Reproduction, from `analysis`, with a new output/profile name for each run:

```powershell
$domainData = 'C:/Users/teche/socal-whale-vessel-risk-analytical-domain/data'
$whaleData = 'C:/Users/teche/socal-whale-vessel-risk-whale-grid-transfer/data/interim/m3-whale-grid-transfer'
$vesselData = 'C:/Users/teche/socal-whale-vessel-risk-accessais-july-month/data/derived/m3-production-vessel-first-attempt2'
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.exposure_run --output ../data/interim/m6-exposure-first-profile/profile.json --label m6-exposure-first --disk-root ../data/derived/m6-exposure-first --minimum-free-memory-gib 2 --minimum-free-disk-gib 20 --runtime-minimum-available-memory-gib 0.5 --runtime-minimum-free-disk-gib 12 --runtime-maximum-application-rss-gib 1.75 -- --water "$domainData/interim/m2-domain-evidence/noaa-whale-footprint-water-grid.parquet" --whale "$whaleData/blue-whale-density-grid-a.parquet" --vessel "$vesselData/vessel-grid.parquet" --domain "$domainData/interim/m2-domain-evidence/domain-candidate-masks.parquet" --vsr "$domainData/raw/bwbs-vsr-2026/bwbs_ca_vsr_zone_2026.geojson" --output ../data/derived/m6-exposure-first
```

First/repeat profiles report exit 0, target completed and no threshold
termination; elapsed 38.37/39.46 seconds, sampled application peak RSS
159,821,824/163,233,792 bytes, minimum available memory
2,702,569,472/2,698,735,616 bytes. Minimum free disk exceeded 44.86 billion bytes.
Profile hashes: first
`8055d083bb4b16e64e1b73f8e93036813d68a511bff0a8de9a29a1d484646754`,
repeat `a373670c06c9c6a4197916d557b1195e735be59ac3d931606dc887aa6abebe39`.
Serialized layers were read back and formula, integration, geometry, nulls,
indices, flags and summaries checked again; both passed. The repeat comparison
explicitly compared all three deterministic files byte-for-byte. These are
implementation verification, not the required independent external audit.

### Actual local spatial inspection

QGIS 4.2.1 rendered the exact first-bundle checksums with the pinned local VSR
and domain through `analysis/scripts/qgis_inspect_exposure.py`. All four corrected
sheets were actually viewed: methods and boundary/corridor details for both grids.
Local evidence: `data/interim/m6-exposure-qgis-font-corrected/render-report.json`.
No VSR-derived geometry or images were committed or publicly exported.

| Inspected sheet | SHA-256 |
| --- | --- |
| `5km-methods.png` | `6b8cfd9b2a7b760b11405869517a490cb78c9779d7f3277225d1b03e6d5dd08c` |
| `5km-details.png` | `2c47a39d2de5ad0b5b110a1d21b29bd5bcd2437aa8b88d997c4de76eccb87ef2` |
| `10km-methods.png` | `eb2e17d270d2ac0ae1ba5452682c9d0d554381ea9291d08a53ae6f3f1dc98e70` |
| `10km-details.png` | `8fa234fa708159f092402f4bbf37b68655e179823bd509490c5cd04e661da14d` |

Inspection found preserved coastline/island holes and exact curved receiver
clipping, northern/southern edges without visible offsets, no colored geometry
outside qualification, and VSR boundaries crossing cells without whole-cell
assignment. Coarser blocks and stronger corridor concentrations are visible;
log compression spreads relative intensity more broadly. Both EPSG:3310 layers
had zero invalid nonempty geometries. Excluded null geometries were not rendered.
Independent human scientific/cartographic review remains outstanding.

A small coastal cell (`r017_c091`, water 0.4850893118493652 km²) sets primary
maximum intensity 47.46002776351226, but contributes only 23.022352208153926
integrated units. The largest integrated cell is instead `r016_c091`,
164.90999158660753 units. Maximum scaling makes much of the 5-km map pale;
each resolution's own maximum differs, so normalized colors alone cannot compare
absolute intensities across grids. Raw panels use common physical breaks.

Initial sheets in `data/interim/m6-exposure-qgis-first` had unreadable font glyphs
and are preserved as failed visual evidence. The renderer was corrected to
register the existing `C:/Windows/Fonts/arial.ttf` explicitly, without copying it.
The corrected sheets have readable legends. Reproduce with QGIS's Python,
`QT_QPA_PLATFORM=offscreen`, script arguments `--bundle`, `--expected-5km`,
`--expected-10km`, `--domain`, `--vsr`, `--font` and a fresh ignored `--output`;
use the exact paths/hashes above. This verification is separate from unchanged
generation lineage.

### Review boundary and proposed shared-owner updates

Recommendation remains the proportional product as an exploratory overlap proxy,
with log results prominently accompanying it. Owner authorization permits the
chosen calculation; it does not settle final messaging. Independent audit must
review units, uniform-within-water allocation, complete-support admission,
fractional joint geometry, quantiles/ties, coarsening and retained source evidence.
Owner review must decide whether any integrated/high-area/ranking statements are
suitable final headlines given material formula sensitivity and temporal mismatch
(multi-year modeled whales, July–November 2024 traffic, 2026 VSR boundary).
Neither receiver qualification nor readiness establishes AIS completeness.
Uncertainty propagation, contemporaneous whale observations, collision validation
and speed-dependent risk remain absent; no scientific validation is inferred.

Before M6 completion: independent audit of this exact commit and artifacts;
owner review of results, sensitivity and maps; resolve findings with fresh
versioned outputs if needed; select and validate the downstream exposure
statistics/layer/publication contracts with M5, including nulls, units, labels,
denominators, provenance and release visual checks. The internal review bundle
does not authorize an application-results contract or VSR redistribution.

Proposed updates for M5/integration owners (not edited here): roadmap records
exploratory computation and sensitivity complete but audit/acceptance still open;
architecture describes the narrow ignored exposure bundle and exact geometry
accounting; development/analysis README add this guarded module invocation and
QGIS verification route; ADR index marks 0020 accepted for exploratory execution,
results pending review; public README must keep M6 incomplete and avoid adopting
these values as final headlines. Existing source-register facts remain unchanged.

### Current validation

Focused exposure tests: 50 passed. `uv lock --check`, Ruff format/check,
strict mypy (41 source files), and `uv build` passed. Full pytest: **467 passed
in 59.47 seconds**, no skips. `git diff --check` passed. No web code changed,
so web gates were not run.
No public export, browser application check, deployment, push, merge, rebase,
AIS regeneration or independent external audit was performed.

## History — foundation commit 4c81af9

## Outcome and review boundary

Implemented [exposure_geometry.py](../analysis/src/whale_vessel_analysis/exposure_geometry.py)
and [23 synthetic tests](../analysis/tests/test_exposure_geometry.py):
exact water/domain/VSR intersections, area conservation, and fractional splitting
of a caller-supplied **full-water integrated total**, under the accepted
uniform-within-water-cell assumption. The local loader verifies the retained
domain and VSR bytes, source/CRS semantics, receiver scenario and FID 126;
it applies the established 0.01° VSR densification before EPSG:3310 projection.
No live service, geometry repair, spatial writer or public VSR export exists.
Direct boundary construction is for synthetic cases; it is not an identity
verification boundary for real inputs.

[ADR 0020](decisions/0020-propose-area-integrated-relative-exposure.md) is
**Proposed**. Recommendation: multiply modeled whale density by vessel distance
per actual water area, then integrate over exact qualified water. Keep speed
separate. Use physical values for calculation and a maximum-scaled relative
index for display. Proposed high exposure is the qualified-area-weighted 90th
percentile, with 80/90/95, positive-only reference, nonlinear traffic scaling
and 10-km sensitivity comparisons. Every choice and its alternatives are
specified in the ADR. None of those formula/threshold calculations is implemented
or applied to real inputs here.

Owner acceptance still needed after independent review: proportional product
interpretation and weights, complete-support admission, display normalization,
the specified log-compressed sensitivity alternative, threshold reference
population/quantile/ties/zero handling, and coarser-grid comparison. The
already-accepted domain, separate speed treatment and fractional VSR geometry
are constraints, not new choices awaiting approval.

**M6 remains incomplete.** No exposure layer, production headline statistic,
high-exposure classification, outside concentration result, application-results
contract, public export, publication or deployment was produced. The parallel
session's exporter, web code and shared CLI/package configuration were untouched.
No push, merge, spending, account operation or new AIS processing occurred.

## Setup verification

Read AGENTS.md, project brief, roadmap status/M6 and relevant M3 completion
evidence, applicable development workflow/testing/resource sections, architecture,
analysis README contracts, source register, data policy and ADRs 0002, 0004,
0005, 0006, 0016, 0018 and 0019. Some large initial terminal reads truncated;
subsequent targeted reads recovered the applicable sections and current contracts.

Before branching, main was clean. These four independent references all returned
`2e4de6075bc79daf725d194ec174012d36cb6da9`:

```text
git rev-parse main origin/main
git ls-remote origin refs/heads/main
gh api repos/ShawnGarello/socal-whale-vessel-risk/branches/main --jq .commit.sha
```

No suitable exposure worktree existed. Created the requested worktree/branch
from that verified main, with no old historical SHA used as a base. Existing
historical worktrees were used only to read the retained ignored data. No
tracked file there or on main was modified. The new worktree was clean before
changes; its instructions had no diff from verified main.

From the new worktree's `analysis/`, `python -m uv sync --locked` installed the
25 locked packages using Python 3.13.7. It changed neither pyproject nor lockfile.
The work used only small grid tables and sequential read-only overlays; there
was no resource experiment, five-month stream, spill or cache clearing.

## Exact artifacts inspected

All paths below are local-only and were read without changing any input or
generation-time lineage. Path aliases are explicit conveniences, not assumed
relative paths in the new worktree:

```text
D = C:/Users/teche/socal-whale-vessel-risk-analytical-domain/data
W = C:/Users/teche/socal-whale-vessel-risk-whale-grid-transfer/data/interim/m3-whale-grid-transfer
V = C:/Users/teche/socal-whale-vessel-risk-accessais-july-month/data/derived/m3-production-vessel-first-attempt2
```

| Artifact | SHA-256 recomputed on 2026-09-06 |
|---|---|
| D/interim/m2-domain-evidence/noaa-whale-footprint-water-grid.parquet | `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031` |
| W/blue-whale-density-grid-a.parquet | `421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62` |
| W/blue-whale-density-grid-a.parquet.lineage.json | `a6584e612d1b185cbfc936322876078661dd0d01bd5aa74a342748dfd635a4d8` |
| V/vessel-grid.parquet | `5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0` |
| V/quality-report.json | `4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7` |
| V/run-metadata.json | `799bc9c989fbdd4d06e5e675eb148c6cc422fae5461634ea36ae445503658fcb` |
| D/interim/m2-domain-evidence/domain-candidate-masks.parquet | `4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77` |
| D/interim/m2-domain-evidence/domain-evidence-report.json | `eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98` |
| D/raw/bwbs-vsr-2026/bwbs_ca_vsr_zone_2026.geojson | `2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783` |

Water, whale, vessel, domain and VSR files were respectively 437,466; 523,986;
1,346,787; 887,833; and 1,591,003 bytes. The grid reader validated the water
contract against the packaged configuration. All original grid columns,
including WKB, IDs, bounds, areas and row order, were byte/value-equal in both
derived input tables. There are 4,516 rows, 19 whale columns and 46 vessel
columns. Explicit GeoParquet CRS is EPSG:3310. The domain file has eight
candidate rows; only `receivers_50_nautical_miles`, basis `receivers`, distance
92,600 m, was selected. It was not regenerated or replaced by a coastline mask.

Whale metadata binds source tree
`1bfdb2bc75b26a3a33aa81952f5fc6cc58bd8e8b73a93362017fa06f76ec94cf`,
configuration `df60aa03796ca979eff5bdca4c620fbac809a797d40d320ea649276d6c889c06`
and the exact water checksum. These metadata identities were read, **not** a
fresh checksum of the raw geodatabase. All 4,516 rows have `complete` coverage;
the recorded uncovered residual totals about 5.91e-7 m². Density equals
allocation divided by full water area. No null, negative or non-finite density
or abundance occurs. Density spans 0.00083394–0.007648247 animals/km², with
no zeros. The transfer carries no propagated uncertainty field; source CV
must not be treated as an exposure weight or a new grid-level confidence bound.

Vessel metadata identifies `production_vessel_input_v1`, version 1.0.0,
`vessel-input-5e590ff3d85ee7acb16e2fd1`, the same grid/configuration,
and `multiday-ais-17e982f999f7093945193378`. Its partition metadata has 153
dates, first 2024-07-01 and last 2024-11-30, readiness `ready`, observational
completeness `unverified`. The retained M3 verification establishes the exact
full period; this session did not rehash or rescan the daily AIS files.
The quality and lineage output digests match the retained input bytes.

All-commercial vessel-km spans 0–39,889.73271494817; per-water-km² intensity
spans 0–8,487.070237441523. Both have 140 zeros and no null, negative or
non-finite values. Physical-unit arithmetic was checked per cell. Group
distance sums agree under the existing verifier's rounding tolerance.
All-commercial reported speed is null exactly when usable SOG distance is
zero; speed availability remains separate from activity. Zero activity is
retained zero movement, not observed absence. Outside the accepted domain it
must not become a low-traffic class. Publisher-transfer and observational
completeness remain unverified regardless of period readiness.

Historical QGIS inspection and input reproducibility are retained in
[M3 completion evidence](m3-completion-handoff.md) and
[the whale-transfer record](../analysis/README.md#verified-noaa-transfer-smoke-run).
This session reverified their input checksums; it did not repeat those visual
inspections or claim a new scientific validation of their interpretations.

## Checks, failures and skipped work

- Focused tests: initially 22 passed; final suite 23 passed after the numerical
  nesting regression was added. Cases cover all ADR 0004 examples, the
  45%-inside/centroid-outside failure, joint domain/VSR intersections,
  full-water versus qualified denominators, dry/excluded distinction, holes,
  disconnected water, boundary contact, positive slivers, invalid CRS/geometry,
  invalid or missing totals, aggregate conservation and uniform-field refinement.
- Real loader/geometry smoke: passed all 4,516 cells, including 1,723 with
  exactly zero qualified area. Independent summed qualified area equals the
  retained union area within the declared tolerance. Full-water and VSR
  partitions conserve. Maximum per-cell water partition residual was
  `7.450580596923828e-09 m²`; VSR partition residual
  `4.6391505748033524e-08 m²`. No exposure values or new spatial file were made.
- Initial exploratory group-sum assertion omitted the existing absolute
  rounding tolerance and failed in two cells: `r054_c044` and `r067_c018`,
  each differing by about 1e-12 km. Source inspection confirmed that group and
  all-commercial values are independently rounded to 12 decimals. Rechecking
  with the existing verifier's `rel_tol=1e-12, abs_tol=1e-9 km` passed.
  Neither input nor aggregation engine was changed.
- Initial geometry smoke failed because nesting used a strict comparison while
  conservation already used numerical tolerance. Measurement found 22 strict
  overshoots, maximum `1.1175870895385742e-08 m²`. Applied the same declared
  tolerance consistently to nesting, added exact containment shortcuts and a
  synthetic regression. No positive area was dropped, repaired or snapped;
  the final smoke passed. These failures are part of the execution record.
- Required analysis gates all passed: locked-environment check; Ruff formatting
  across 80 files and lint; strict mypy over 38 source files; **440 tests passed
  in 75.39 seconds**; and sdist/wheel build. The new 23 tests are included in
  that full count. No executable changes followed those passing gates.
- Skipped: production formula execution, production sensitivity and new-layer
  QGIS inspection (no formula or spatial output produced); full-period AIS
  regeneration (unnecessary); web checks (no web/config change); remote VSR
  release comparison, publication and deployment (outside this task).
- Independent branch audit and owner method acceptance have **not** occurred.
  Both PR CI jobs remain required on the eventual PR head before an authorized
  merge. Nothing has been pushed or merged.

Required checks, from `analysis/`:

```text
python -m uv lock --check
python -m uv run ruff format --check .
python -m uv run ruff check .
python -m uv run mypy src/whale_vessel_analysis
python -m uv run pytest
python -m uv build
```

The geometry-only smoke can be repeated from `analysis/` by running this Python
through `python -m uv run python` (PowerShell can pipe a literal here-string to
`python -m uv run python -`). It reads the original inputs and writes nothing:

```python
from pathlib import Path
import math
from whale_vessel_analysis.config import load_default_config
from whale_vessel_analysis.whale_grid import load_target_grid
from whale_vessel_analysis.exposure_geometry import load_local_boundaries

root = Path("C:/Users/teche/socal-whale-vessel-risk-analytical-domain/data")
evidence = root / "interim/m2-domain-evidence"
grid = load_target_grid(
    evidence / "noaa-whale-footprint-water-grid.parquet",
    load_default_config(),
    expected_sha256="7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031",
)
boundaries = load_local_boundaries(
    evidence / "domain-candidate-masks.parquet",
    root / "raw/bwbs-vsr-2026/bwbs_ca_vsr_zone_2026.geojson",
)
areas = [boundaries.cell_areas(c.geometry, water_crs="EPSG:3310") for c in grid.cells]
assert all(a is not None for a in areas)
assert math.isclose(
    math.fsum(a.qualified_m2 for a in areas), boundaries.domain.area,
    rel_tol=1e-10, abs_tol=1e-6,
)
assert math.isclose(
    math.fsum(a.inside_vsr_m2 + a.outside_vsr_m2 + a.excluded_domain_m2 for a in areas),
    math.fsum(a.water_m2 for a in areas), rel_tol=1e-10, abs_tol=1e-6,
)
print("Geometry conservation passed; no exposure calculation or output file")
```

## Next production work, in dependency order

1. Independent audit of the exact foundation commit and scientific review of
   ADR 0020. Resolve its proposed choices with the owner. The high-threshold
   baseline remains provisional until the actual distribution and sensitivity
   can be reviewed; do not publish exploratory values as accepted headlines.
2. Implement a narrow versioned **exposure input join contract**. Require the
   exact input identities, sidecar integrity, accepted period/parameters,
   one-to-one complete grid keys, exact geometry/CRS/areas, physical units,
   range/null/support invariants and explicit completeness limitations. Do not
   accept candidate vessel files or changed support by field-name similarity.
   Keep upstream config/identities unchanged and bind the separate reporting
   domain contract downstream. The current geometry primitive does not do
   this join and must not be represented as a production input validator.
3. After method acceptance, implement the selected formula, normalization,
   threshold and summary contracts with known-answer tests for unequal water
   areas, zero/missing/outside states, ties, weighted quantiles, proportional
   scaling invariance, double-area errors, cross-cell conservation and 10-km
   recomputation. Specify headline denominators and units explicitly. Define
   outside concentrations reproducibly (e.g. ranked contiguous components with
   a reviewed adjacency/ordering rule), not through unrecorded map selection.
4. Define deterministic local exposure output, quality report and lineage
   contracts. Bind input/sidecar hashes, processing and reporting configuration,
   accepted ADR/version, units, formula, thresholds/reference values, support,
   numerical residuals and software versions. Separate clocks/paths from
   deterministic identity and later visual inspection from generation lineage.
   Use fresh ignored output bundles, atomic publication and no overwrite;
   retain failed evidence and originals. **Never serialize VSR intersection
   geometries into public exposure/export artifacts.** Agree any scalar summary
   and public layer contract with the exporter owner before integration.
5. Execute only the small validated grid-level combination; do not rerun the
   five-month AIS engine. Measure its resource need and use the documented
   preflight/runtime safeguards for any heavy run. Coordinate host availability
   before resource-intensive work. Run experiments sequentially, preserve
   artifacts, stop on gates, and never clear caches to force a pass.
6. Independently repeat production into a fresh location and reproduce
   deterministic data/quality bytes. Recompute headline statistics from the
   serialized analytical output. Check area/exposure conservation independently,
   including excluded support and zero denominators. Run the predeclared
   threshold/scaling/10-km sensitivity, retain non-robust outcomes, and obtain
   review/acceptance of final threshold and interpretation.
7. Inspect each resulting spatial layer in QGIS, tied to its exact SHA-256:
   full context, northern/southern context edges, partial receiver and VSR cells,
   shipping corridors, islands/holes, small water slivers, zero versus excluded
   rendering, source-scale whale blocks and outside concentrations. Inspect
   raw intensity and normalized display separately; compare sensitivity layers
   with common scales. Record actual visual findings, date/tool/version/images
   and failures separately from untouched generation lineage. Rendering alone
   does not count. M6 completion criteria still govern whether it is complete.
8. Later release work must compare the publisher's current anonymous FID 126
   geometry with this immutable analytical snapshot. Reconcile/rerun or omit
   the remote boundary if it differs. This is a release gate, not this task.

## Proposed shared-owner integration edits — not applied

Coordinate with the parallel exporter session; do not overwrite its files.

| Owner | Proposed change |
|---|---|
| Roadmap | Change M6 from Not started to In progress after integrating the foundation; record implemented geometry and proposed method separately. Keep every production/result/sensitivity/visual completion item open. |
| ADR index | Add ADR 0020 as Proposed. If the parallel branch independently allocated 0020, coordinate a sequential number and fix links before integration; do not overwrite either record. |
| ADR 0004 | Update its verification paragraph: fractional geometry/synthetic cases now exist, while exposure production/statistics remain unfinished. |
| Architecture | Record the narrow local geometry primitive and deferred production contracts; link the proposed method without treating it as accepted. Correct stale M3 production-pending wording against roadmap/ADR 0018. |
| Analysis README | Add the geometry API, exact full-water-total denominator, local-only loader, test command and handoff link. Do not advertise an exposure production CLI. |
| Development | Update component/test inventory after integration; reconcile stale M3 production-pending language with the owning completion evidence. Preserve required gates. |
| Data sources | Link this read-only reinspection and the method's primary sources if useful; preserve unresolved season/coverage facts. Do not infer new retrieval or scientific validation. |
| Public README | Describe an exposure-method foundation under review, with M6 unfinished and no headline results. |

No project-brief scope change is proposed. Hosting, including the author's
Vercel preference, remains outside this task.
