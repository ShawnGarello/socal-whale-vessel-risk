# M6 exposure foundation handoff

**Date:** 2026-09-06. **Branch:** `feat/m6-exposure-foundation`.
**Worktree:** `C:/Users/teche/socal-whale-vessel-risk-exposure-foundation`.
This handoff accompanies the foundation implementation commit; use
`git log -1 --format=%H` in this worktree to identify its exact committed head.
It is navigation and execution evidence, not the owner of milestone status.

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
