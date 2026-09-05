# M3 completion session handoff

Session date: 2026-09-04. Branch: `feat/m3-vessel-processing-completion`.
This is execution history; the roadmap and ADRs own status and methodology.
`docs/delivery-assessment.md` belongs to another session and is excluded.

## Execution plan

1. Verify retained period, evidence, grid and lineage identities against committed
   records; review flagged dates using cleaner reports and bounded diagnostics.
2. Resolve type-only population and cleaned-extent censoring with explicit
   limitations. Review authoritative gap/speed sources and boundary sensitivity.
3. Run the four 300/1800-second by 30/50-knot spatial candidates sequentially
   using the existing candidate boundary and identical exact support geometry.
   Repeat deterministic artifacts, compare cells/groups and conservation, and
   inspect checksum-bound outputs rendered by QGIS 4.2.1.
4. Select supported rules only after that evidence; implement a narrow truthful
   final-input and descriptive speed boundary with synthetic analytical tests.
5. Generate/reproduce final outputs, inspect them, run required analysis checks,
   and audit M3 criteria. Exposure calculation remains M6 and out of scope.

## Completed

- `git status --short` returned no changes; `git branch --show-current` matched
  the expected branch before work. Read AGENTS.md and its required documents.
- The committed roadmap and ADR 0018 record water-grid SHA-256
  `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`.
  The earlier copied prompt checksum is not authoritative.

## Verified inputs

- `data/interim/m3-accessais-july-month-gate/run/period.json`:
  recorded `multiday-ais-17e982f999f7093945193378`, 153 compatible dates,
  no missing/conflicts, 15,458,567 cleaned observations.
- `data/interim/m3-period-vessel-rule-evidence-run/evidence-first/evidence.json`:
  verified `period-vessel-rule-evidence-cb2525fab34c4b8848146365`, SHA-256
  `1b90ebd4e8d340cdb09709557d154f5b55f7882cba8cbc08b548958edbb25ff4`.
- Read-only spatial root:
  `C:\Users\teche\socal-whale-vessel-risk-analytical-domain\data\interim\m2-domain-evidence`.
  `Get-FileHash -Algorithm SHA256` verified the water grid against the committed
  checksum above. Period row total was independently summed from all date entries.

## Diagnostic execution

`analysis/scripts/m3_completion_diagnostics.py` reuses the verified period
relation, checks cleaner sidecar hashes, summarizes hourly and length populations
in SQL, and streams one adjacency pass for gap/speed/SOG and edge diagnostics.
Its 2/5-knot SOG-agreement bands and 0.05-degree edge band are diagnostic choices.

The first invocation in `m3-completion-diagnostics-first` passed preflight but
failed before analysis because the script's `main` did not accept the profiler's
argument list. The signature was corrected. This was a code error, not a resource
abort; its profile is retained. The second invocation completed successfully. Exact command
from `analysis/`:

```powershell
python -m uv run python -m whale_vessel_analysis.resource_profile --module scripts.m3_completion_diagnostics --output ../data/interim/m3-completion-diagnostics-second/profile.json --label m3-completion-diagnostics-second --disk-root ../data/interim/m3-completion-diagnostics-second/run --spill-root ../data/interim/m3-completion-diagnostics-second/spill --minimum-free-memory-gib 2 --minimum-free-disk-gib 20 --runtime-minimum-available-memory-gib 0.5 --runtime-minimum-free-disk-gib 12 --runtime-maximum-application-rss-gib 1.75 --runtime-maximum-spill-gib 12 -- --manifest ../data/interim/m3-accessais-july-month-gate/run/period.json --output ../data/interim/m3-completion-diagnostics-second/run/diagnostics.json --temp-directory ../data/interim/m3-completion-diagnostics-second/spill
```

Read-only inspection of all 153 cleaner reports reconciled 82,619,482 source
rows, 15,465,734 selected commercial rows before deduplication, 4,776 conflicting
rows, 2,391 exact duplicates and 15,458,567 cleaned rows. No row was removed for
invalid reported SOG or being outside the already bounded request extent.
Flagged-date commercial counts are already low before deduplication; this does
not establish a reception outage, missing delivery, or its cause.

The successful diagnostic SHA-256 is
`aace97dd777e3b87350c1808e1d4ff00b66ab6e723d941d232fd493236265656`.
Operation elapsed 98.859971 seconds; peak sampled application RSS 1,223,716,864
bytes; peak spill 1,158,676,480 bytes, final zero; minimum available memory
3,179,913,216 bytes; minimum free disk 59,838,226,432 bytes. All gates passed.
The [method review](m3-vessel-method-review.md) records interpretation and the
common type-only, censored, exact-support matrix treatment. Threshold selection
still waits for spatial evidence.

## Operational controls

Heavy work runs sequentially through the existing resource profiler, with fresh
ignored output/profile/spill paths: DuckDB `1GB`, one thread, Arrow batch 50000;
preflight 2 GiB available memory and 20 GiB free disk; runtime minimum memory
0.5 GiB and disk 12 GiB; maximum application RSS 1.75 GiB and spill 12 GiB.
Stop on failed preflight or resource abort without relaxing gates. Caches are
not cleared. Inputs and historical evidence remain unchanged.

## Outstanding / next action

Commit `96274f9` records the methodological review. The first spatial candidate
is running in terminal session 39087. No completed spatial artifact, new visual
verification, or final method selection is established yet. M3 remains In
progress. No push or merge is authorized.

Exact first matrix invocation from `analysis/` (fresh destinations, no overwrite):

```powershell
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.vessel_grid_cli --output ../data/interim/m3-full-period-matrix/g300-s30-first/profile.json --label m3-g300-s30-first --disk-root ../data/derived/m3-full-period-matrix/g300-s30-first --spill-root ../data/interim/m3-full-period-matrix/g300-s30-first/spill --minimum-free-memory-gib 2 --minimum-free-disk-gib 20 --runtime-minimum-available-memory-gib 0.5 --runtime-minimum-free-disk-gib 12 --runtime-maximum-application-rss-gib 1.75 --runtime-maximum-spill-gib 12 -- --manifest ../data/interim/m3-accessais-july-month-gate/run/period.json --grid-input C:/Users/teche/socal-whale-vessel-risk-analytical-domain/data/interim/m2-domain-evidence/noaa-whale-footprint-water-grid.parquet --expected-grid-sha256 7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031 --output-dir ../data/derived/m3-full-period-matrix/g300-s30-first --maximum-gap-seconds 300 --implied-speed-ceiling-knots 30 --period-readiness-treatment require-ready --edge-treatment censor-at-cleaned-extent --support-treatment exact-water-geometry-exclude-and-report --memory-limit 1GB --temp-directory ../data/interim/m3-full-period-matrix/g300-s30-first/spill --threads 1 --batch-size 50000
```

Local uncommitted tooling: diagnostic script and its passing synthetic test;
QGIS inspection script prepared but not exercised; analysis README entry.
Full analysis quality gates have not yet run. Poll the current job first and
stop on a resource abort; otherwise review it before the next sequential job.

## Session continuation, 2026-09-04

A second session resumed this branch after the first reached its usage limit.
No committed history, retained artifact, or in-flight process was altered.

Independently re-verified before continuing, without trusting this document:

| Input | Recorded expectation | Independent result |
|---|---|---|
| Water grid | committed roadmap/ADR 0014/0018 checksum | `sha256sum` returned `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`; matches the committed records, not the earlier copied prompt value |
| Period manifest | `multiday-ais-17e982f999f7093945193378` | identical; 153 expected and 153 compatible dates, zero conflicting, every entry `compatible` |
| Period observations | 15,458,567 | 15,458,567 summed independently from all 153 date entries |
| Period evidence | `period-vessel-rule-evidence-cb2525fab34c4b8848146365` | identical; file SHA-256 `1b90ebd4e8d340cdb09709557d154f5b55f7882cba8cbc08b548958edbb25ff4` |

The first matrix candidate `g300-s30-first` was found **still executing**, not
abandoned: PID 20952, started 20:58:31 local, about 1.24 GiB sampled RSS against
the 1.75 GiB gate, with its isolated spill directory at about 1.1 GiB against the
12 GiB gate and still being written. It was left running rather than restarted,
and no second heavy job was started beside it. `data/derived/` still holds no
candidate bundle, so no spatial result exists yet.

Remaining sequence is unchanged: finish this candidate, then run the other three
candidates and all four repeats sequentially, compare, inspect in QGIS, select
rules, implement the final input and speed-summary boundary, produce and
reproduce the final artifacts, and audit M3.

## First full-period candidate failed its own conservation check

The `g300-s30-first` execution completed its work and then **failed**, so no
spatial artifact exists. This was **not** a resource abort. Its retained profile
`data/interim/m3-full-period-matrix/g300-s30-first/profile.json` records
`exit_code: 2`, `target_outcome: target_completed`, `termination_threshold: null`,
and every gate satisfied: operation elapsed 5,502.201 seconds (91.7 minutes);
peak sampled application RSS 1,343,270,912 bytes against the 1,879,048,192-byte
ceiling; peak spill 1,162,018,816 bytes against the 12,884,901,888-byte ceiling,
final zero; minimum available memory 911,093,760 bytes against the 536,870,912-byte
floor; minimum free disk 58,376,646,656 bytes.

The profiler records only hashes of the target's output, and the text went to the
first session's console. The failing message was recovered exactly by matching the
recorded stderr SHA-256
`dd5fc1179f13de8f676c5c6275c063d96c9687dc1791b11e938fe2700cffae37`
against candidate messages: it is `error: retained distance is not conserved for
passenger`, and no other candidate string produces that digest.

### What the evidence does and does not establish

`_Accumulator._quality` compares each group's retained `parent_m` against the sum
of `allocated_m`, `outside_support_m`, `ambiguous_boundary_m` and
`invalid_geometry_m`, at `abs_tol = max(1e-6, parent_m x 1e-12)`. The five running
totals accumulate by naive `+=` over roughly 15.4 million segments.

The recorded two-day run is the calibration point: maximum per-segment difference
`2e-12` metres and aggregate differences between `-4.02331e-7` and `-4.39584e-7`
metres, passing comfortably. A simulation of the same naive accumulation over
218,089 segments reproduces `+4.8e-7` metres, matching that observation, but over
6.4 million passenger-scale segments predicts only about `0.08` of the tolerance.
**Floating-point accumulation alone therefore does not explain the failure**, and
the earlier assumption that it would has been discarded.

The remaining structural candidate is that the global tolerance is inconsistent
with the per-segment tolerance the same code grants. `_allocate_positive_segment`
accepts `piece_sum` against `union_length` at `max(1e-6, parent x 1e-12)` per
segment, and clamps `outside = max(0.0, parent - union_length)`. Each affected
segment can contribute up to `1e-6` metres of residual, while the whole-group
allowance is only about `parent_m x 1e-12`. Roughly 830 such segments would
exhaust a passenger allowance of about `8e-4` metres. The two-day run never
exercised this: its positive-length ambiguous count was zero. Whether the
full-period run does is **unmeasured**, so no correction is being applied yet.

### Action taken

Commit `3b050dd` makes the failure report what it already measured: the residual,
the tolerance, the five component distances, the retained segment count, the
maximum per-segment difference, and the invalid-geometry and ambiguous-boundary
counts. The check, its tolerance, and every success-path value are unchanged, so
existing candidate identities and artifact bytes still reproduce; only the raised
message differs. `quality` is embedded in the Parquet metadata and the grid ID,
which is why the accumulator numerics were deliberately **not** touched.

Required checks passed on that commit: `uv lock --check`, `ruff format --check`,
`ruff check`, `mypy` (34 files), `pytest` (379 passed), `uv build`.

### Re-run in progress

The candidate is running again with the identical parameters, a fresh profile and
spill path that preserves the failed attempt, and console capture so the
measurement cannot be lost a second time. Exact command from `analysis/`:

```powershell
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.vessel_grid_cli --output ../data/interim/m3-full-period-matrix/g300-s30-first-attempt2/profile.json --label m3-g300-s30-first-attempt2 --disk-root ../data/derived/m3-full-period-matrix/g300-s30-first --spill-root ../data/interim/m3-full-period-matrix/g300-s30-first-attempt2/spill --minimum-free-memory-gib 2 --minimum-free-disk-gib 20 --runtime-minimum-available-memory-gib 0.5 --runtime-minimum-free-disk-gib 12 --runtime-maximum-application-rss-gib 1.75 --runtime-maximum-spill-gib 12 -- --manifest ../data/interim/m3-accessais-july-month-gate/run/period.json --grid-input C:/Users/teche/socal-whale-vessel-risk-analytical-domain/data/interim/m2-domain-evidence/noaa-whale-footprint-water-grid.parquet --expected-grid-sha256 7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031 --output-dir ../data/derived/m3-full-period-matrix/g300-s30-first --maximum-gap-seconds 300 --implied-speed-ceiling-knots 30 --period-readiness-treatment require-ready --edge-treatment censor-at-cleaned-extent --support-treatment exact-water-geometry-exclude-and-report --memory-limit 1GB --temp-directory ../data/interim/m3-full-period-matrix/g300-s30-first-attempt2/spill --threads 1 --batch-size 50000 > ../data/interim/m3-full-period-matrix/g300-s30-first-attempt2/console.log 2>&1
```

If it succeeds, the matrix continues as planned. If it fails again, the captured
message supplies the residual and the branch counts, and the correction is then
chosen from that measurement rather than assumed. Any change to the conservation
criterion itself is a methodological decision for the author, not a silent edit:
the criterion must not be loosened to make a run pass.

## Measured cause and correction

The instrumented re-run `g300-s30-first-attempt2` failed the same check and
reported the measurement. Console output is retained at
`data/interim/m3-full-period-matrix/g300-s30-first-attempt2/console.log`:

```
error: retained distance is not conserved for passenger:
difference_m=-0.001280069351196289, tolerance_m=0.0008055719096036832,
parent_m=805571909.6036832, allocated_m=728151586.1838942,
outside_support_m=77420323.42106912, ambiguous_boundary_m=0.0,
invalid_geometry_m=0.0, retained_segments=6191714,
maximum_segment_difference_m=9.094947017729282e-13,
invalid_intersection_geometry=0, positive_length_ambiguous_boundary=0
```

This **refutes** the per-segment-slack hypothesis recorded above. Both the
ambiguous-boundary and invalid-geometry branches contributed exactly zero
distance and zero segments, so neither produced the residual.

The decisive argument is a bound, not a simulation. The largest single-segment
residual was `9.094947017729282e-13` metres. Across all 6,191,714 retained
passenger segments the greatest possible geometric residual is therefore about
`5.6e-6` metres, which is roughly 229 times smaller than the observed
`1.28e-3` metres. The geometry cannot account for the difference. What remains
is the rounding of the additions themselves: five naive `+=` running totals
reaching about `8.06e8` metres over 6.19 million steps, against a tolerance of
`parent_m x 1e-12 = 8.06e-4` metres.

An idealized i.i.d. simulation at these magnitudes produces only about `5e-5`
metres, so it demonstrates the mechanism but understates the real drift; the
actual segment-length distribution and summation order are less favourable.
The same simulation with Neumaier compensation returns `-1.19e-7` metres,
about `1.5e-4` of the tolerance.

### Correction

Commit `bb3409f` replaces the five per-group distance accumulators with a
Neumaier `_CompensatedTotal`. **The conservation criterion, its tolerance, and
the geometry are unchanged**; only the accuracy of the running totals improves.
This is deliberately not a tolerance relaxation, which would have widened an
acceptance band to admit a known numerical error.

Two synthetic tests pin the defect: one accumulates the measured passenger
shape and asserts that the naive sum exceeds the tolerance while the
compensated sum does not, and one checks known values including a
catastrophic-cancellation case.

### Consequence for recorded identities

`processing_version` and `quality` both enter `_identity_material`, so candidate
IDs and artifact bytes depend on them. `VESSEL_GRID_PROCESSING_VERSION` is
therefore raised from `1.0.0` to `1.1.0`. The two-day candidate checksums
recorded in ADR 0018 and `analysis/README.md` were produced under `1.0.0` and
**will not** reproduce byte-for-byte under `1.1.0`. Those records remain valid
history and must be labelled with the processing version that produced them
rather than silently re-run. The change is unavoidable: under `1.0.0` the
full-period aggregation cannot complete at all.
