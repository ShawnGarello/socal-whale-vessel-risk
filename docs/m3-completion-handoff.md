# M3 completion session handoff

Session date: 2026-09-04. Branch: `feat/m3-vessel-processing-completion`.
This is execution history; the roadmap and ADRs own status and methodology.
`docs/delivery-assessment.md` belongs to another session and is excluded.

## Current status, 2026-09-05 (read this first)

This document is append-ordered execution history. Later sections supersede
earlier ones; the "Outstanding / next action" section below is **stale history
from the first session** and is retained only as a record of what was true then.

**M3 is In progress. ADR 0018 remains Proposed pending production validation.**
The 300-second/30-knot configuration is selected with explicit limitations;
selection does not complete the ADR's final validation criterion.

Done: the period, evidence, grid and lineage identities were re-verified; the
non-spatial evidence and flagged dates were reviewed; the edge treatment and
type-only population were resolved; a distance-accumulation defect was found,
measured and corrected; and the complete four-candidate spatial matrix was
executed, repeated byte-for-byte, compared across all six candidate pairs, and
inspected in QGIS.

Current implementation: the production vessel-input boundary and separate
movement-speed summary are implemented. ADR 0018 selects 300 seconds / 30 knots,
with type-only population, cleaned-extent censoring and exact water support.
ADR 0006 records distance weighting, endpoint SOG, the explicit exploratory
5-knot consistency screen and unavailable/zero semantics. Candidate artifacts
remain unchanged; production commands recompute from the ready period.

Remaining, in order:

1. **The first production run aborted on a resource gate at 11:15 on 2026-09-05
   and produced no output.** Its measured evidence is recorded under "First
   production run: resource abort" below. Rerun it in a **fresh** location once
   the machine has enough free memory; do not reuse
   `m3-production-vessel-first`, relax any gate, or retry blindly. Repeat in a
   second fresh location only after a successful first run. No final output
   exists yet.
2. Verify counts, identities, lineage, conservation and speed exclusions; inspect
   exact activity and speed fields in QGIS and record checksum-bound evidence.
3. Reconcile owner status and assess M3/ADR completion criteria. Required
   analysis gates passed below; rerun affected checks if subsequent code changes
   warrant it. No criterion is complete merely because code exists.

Documentation correction commit: `cf7439b`. Method selection: `5a8ae54`.
Production/speed implementation: `c977ed9`. Focused engine/speed tests passed
(38 tests, then four production tests after adding exact-piece/support cases).
The independent verifier's six known-answer checks passed after correcting its
test-only script import. Required analysis gates passed: lock check, formatting
(after correcting one formatting issue), lint, strict source mypy, **417 tests**
in 93.79 seconds, and sdist/wheel build. No web build was run.
The current branch began this continuation at author-confirmed `de6408c`.
The input identities and resource controls below remain authoritative for runs;
production command syntax is in `analysis/README.md`. Owner documents now
reflect the implementation and pending verification; historical sections below
retain the state at their recorded time.

Exposure calculation belongs to M6 and is out of scope. Nothing has been pushed
or merged.

### First production run: resource abort

Launched from `analysis/` on 2026-09-05, after a clean implementation commit.
Terminal session `63282`; target PID `7156`. Preflight passed; no cache was
cleared. **The run aborted after 1,029.935 seconds and wrote no bundle**;
`data/derived/m3-production-vessel-first/` was never created. The exact
invocation is:

```powershell
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.vessel_input_cli --output ../data/interim/m3-production-vessel-first/profile.json --label m3-production-vessel-first --disk-root ../data/derived/m3-production-vessel-first --spill-root ../data/interim/m3-production-vessel-first/spill --minimum-free-memory-gib 2 --minimum-free-disk-gib 20 --runtime-minimum-available-memory-gib 0.5 --runtime-minimum-free-disk-gib 12 --runtime-maximum-application-rss-gib 1.75 --runtime-maximum-spill-gib 12 -- --manifest ../data/interim/m3-accessais-july-month-gate/run/period.json --grid-input C:/Users/teche/socal-whale-vessel-risk-analytical-domain/data/interim/m2-domain-evidence/noaa-whale-footprint-water-grid.parquet --expected-grid-sha256 7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031 --output-dir ../data/derived/m3-production-vessel-first --memory-limit 1GB --threads 1 --batch-size 50000 --temp-directory ../data/interim/m3-production-vessel-first/spill
```

Measured outcome, from retained
`data/interim/m3-production-vessel-first/profile.json`:

| Measurement | Value |
|---|---|
| `exit_code` | 1 |
| `target_outcome` | `resource_abort` |
| `runtime_guard.termination_threshold` | `minimum_available_memory` |
| Available memory at termination | 527,904,768 B (0.4917 GiB) against the 536,870,912 B floor |
| Application peak RSS | 1,337,786,368 B (1.246 GiB) against the 1.75 GiB cap |
| Peak spill | 1,167,556,608 B (1.087 GiB) against the 12 GiB cap |
| Free disk at termination | 42,449,526,784 B (39.5 GiB) against the 12 GiB floor |
| Operation elapsed | 1,029.935 s |
| Target stdout / stderr | 13,327 B / **0 B** |

The guard terminated the process because **machine-wide** available memory fell
8,966,144 bytes (about 8.6 MB) below the runtime floor. The application stayed
well inside its own RSS, spill and disk limits and emitted no stderr, so this is
a host memory-pressure condition, not a defect in the production boundary. The
gate behaved as designed and **was not relaxed**.

Preflight available memory was 2,719,301,632 B (2.53 GiB), the least headroom of
any full-period run attempted so far. For comparison, all ten retained candidate
profiles recorded 3.17–5.70 GiB of preflight available memory, and their lowest
observed available memory during execution was 0.85–4.16 GiB. The application
needs roughly 1.25 GiB of RSS growth above its baseline, so a launch needs
materially more than the 2 GiB preflight minimum to stay above the 0.5 GiB
runtime floor for the whole run.

Retained failure evidence, not to be deleted or overwritten: the profile above
and the orphaned DuckDB spill under
`data/interim/m3-production-vessel-first/spill/`, about 1.1 GB, which the
profiler's termination prevented DuckDB from clearing. Its size is already
recorded in the profile, so the author may reclaim it; free disk was not a
factor in this failure. The next attempt must use a fresh output, profile and
spill path, for example `m3-production-vessel-first-attempt2`, because the
writer refuses existing destinations by design.

After successful first/repeat execution, use
`analysis/scripts/verify_production_vessel_input.py` with both fresh bundles,
the exact water grid, and retained
`data/derived/m3-full-period-matrix/g300-s30-first/vessel-grid.parquet`
(SHA-256 `be3dc74d1c07525ef2a74cba1d0062abd97496b4043b3dd26847f9c3a65ec860`).
This independently reconstructs production identity and checks every activity
column against the selected candidate, target geometry, lineage, counts, units,
speed categories and null/zero semantics. It does not replace QGIS inspection.

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

## Outstanding / next action (superseded, first session)

> **Stale.** Retained as history. The candidate described here later failed its
> own conservation check; see the sections below for what actually happened.

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

## Full-period spatial matrix execution

Processing version `1.1.0`. Every run used the same exact grid
(`7229098c...c087031`), the same ready period
`multiday-ais-17e982f999f7093945193378`, `require-ready`,
`censor-at-cleaned-extent`, `exact-water-geometry-exclude-and-report`, no length
filter, DuckDB `1GB`, one thread, Arrow batch 50000, and a fresh ignored
output/profile/spill path. Runs were strictly sequential; none ran beside another.

### 300 seconds / 30 knots

Completed on the third attempt, the first two having failed the conservation
check described above. Both earlier profiles are retained as evidence.

| Item | Value |
|---|---|
| Grid ID | `candidate-vessel-grid-197aebe346602981b79501fa` |
| `vessel-grid.parquet` | `be3dc74d1c07525ef2a74cba1d0062abd97496b4043b3dd26847f9c3a65ec860` |
| `quality-report.json` | `05260f8991e31fd1677b0f7b248dd0e96b97adbfabbd5d9240926d09aeac6faa` |
| Operation elapsed | 1,956.912 s |
| Peak application RSS | 1,418,575,872 of 1,879,048,192 bytes |
| Peak spill | 1,192,919,040 of 12,884,901,888 bytes; final zero |
| Minimum available memory | 2,712,629,248 of 536,870,912 bytes |
| `termination_threshold` | `null`; no resource abort |

The independent repeat reproduced **both checksums exactly**, so the candidate is
deterministic under the corrected accumulation.

Distance conservation passed with `difference_m` exactly `0.0` for passenger,
cargo, tanker and all-commercial; the maximum single-segment difference was
`1e-12` metres. Populations: 15,458,567 observations; 15,457,099 structural
segments; 14,946,183 retained; 510,916 excluded, all of them either
`maximum_gap` (461,769) or `implied_speed` (49,147), with zero
`invalid_coordinate_transform`, `non_increasing_time` and `vessel_group_change`.
Zero-length retained pairs 1,346,338; cross-midnight candidates 25,655 with
19,667 retained. Allocated 2,084,502,496.069 metres with 173,324,278.518 metres
of retained parent distance outside modeled-whale support. 5,847,760 observations
fell outside exact cell support and 20 were boundary-ambiguous; these are
reported, not reclassified as land or absent coverage.

The earlier 91.7-minute timings were cold-read cost. With the 153 daily Parquet
files in the operating-system page cache a run takes about 33 minutes.

### Remaining runs

`g300-s50`, `g1800-s30` and `g1800-s50`, each with its repeat, run sequentially
from `scratchpad/run_matrix.sh`, halting on the first failure. Results are
appended here as they complete.

### Visual verification inputs confirmed available

QGIS 4.2.1 is present at `C:\Program Files\QGIS 4.2.1\bin\python-qgis.bat`.
`domain-candidate-masks.parquet` matches
`4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77`. The
immutable VSR snapshot matching
`2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783` is read
read-only from the analytical-domain worktree; it is not copied, committed, or
derived from, per ADR 0019.

### Completed candidates and whole-period sensitivity

Each pair below reproduced **both** checksums exactly on an independent repeat.

| Candidate | Grid ID | `vessel-grid.parquet` | `quality-report.json` |
|---|---|---|---|
| 300 / 30 | `candidate-vessel-grid-197aebe346602981b79501fa` | `be3dc74d1c07525ef2a74cba1d0062abd97496b4043b3dd26847f9c3a65ec860` | `05260f8991e31fd1677b0f7b248dd0e96b97adbfabbd5d9240926d09aeac6faa` |
| 300 / 50 | recorded with results | `30209bb2b7195a77dedfef7082214315275c15f6d219d39d2f726d5c8d24c3b2` | `aefd2a939be61d97aa3ddc67493fbfb449d1b902e6d3b99a1dbd0ff2e1159cbb` |
| 1800 / 30 | recorded with results | `6e17b8b109e07e35a24c00531528bc8cce106055528212debc7b3578606e0aeb` | `be05a406f1536fee62a1105b1d2ce70c64d61fa7b08241ff1cf1676c72c105ac` |

| Candidate | Retained | Gap excluded | Speed excluded | Passenger km | Cargo km | Tanker km | All-commercial km | Outside support km |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 300 / 30 | 14,946,183 | 461,769 | 49,147 | 728,151.586 | 970,908.248 | 385,442.662 | 2,084,502.496 | 173,324.279 |
| 300 / 50 | 14,959,600 | 461,769 | 35,730 | 736,093.425 | 977,440.347 | 386,349.492 | 2,099,883.264 | 174,259.226 |
| 1800 / 30 | 15,380,549 | 24,935 | 51,615 | 756,460.744 | 1,006,386.386 | 399,080.095 | 2,161,927.225 | 180,439.603 |

Observations, not selection criteria:

- The gap change dominates the speed change. Relaxing the gap from 300 to 1,800
  seconds adds 77,424.729 allocated km (+3.71%); relaxing the ceiling from 30 to
  50 knots adds 15,380.768 km (+0.74%), roughly one fifth as much.
- Relaxing the gap **increases** implied-speed exclusions, 49,147 to 51,615,
  because longer admitted gaps then fail the plausibility test. The two rules are
  not independent and must not be described as separable filters.
- Outside-support share is stable at 7.677%, 7.663% and 7.703% of retained parent
  distance, so the exact-support treatment is not candidate-sensitive.
- Zero-length retained pairs rise from 1,346,338 to 1,413,123 with the longer gap.

Whole-period totals cannot show whether these differences are concentrated in
particular cells or change the relative pattern among them. Per-cell comparison
and visual inspection remain required, and retaining more distance is explicitly
not a reason to prefer a candidate.

### Execution note

The harness repeatedly terminated this session's background **shells** when free
physical memory fell to about 2.2 GiB of 16 GiB, largely because the 153 daily
Parquet files occupy the operating-system file cache. No profiled run was ever
affected: each detached run continued through those terminations, every profile
recorded `termination_threshold: null`, and the runtime guard consistently
reported about 2.3 GiB available against its 0.5 GiB floor. No gate was relaxed.
The remaining runs were therefore launched detached from the session shell, from
an idempotent script that skips any already-complete bundle and refuses to start
a second profiled job while one is running.

### Full matrix complete

All eight runs completed. Every candidate reproduced **both** checksums exactly on
an independent repeat, satisfying the ADR 0018 determinism requirement.

| Candidate | `vessel-grid.parquet` | `quality-report.json` |
|---|---|---|
| 300 / 30 | `be3dc74d1c07525ef2a74cba1d0062abd97496b4043b3dd26847f9c3a65ec860` | `05260f8991e31fd1677b0f7b248dd0e96b97adbfabbd5d9240926d09aeac6faa` |
| 300 / 50 | `30209bb2b7195a77dedfef7082214315275c15f6d219d39d2f726d5c8d24c3b2` | `aefd2a939be61d97aa3ddc67493fbfb449d1b902e6d3b99a1dbd0ff2e1159cbb` |
| 1800 / 30 | `6e17b8b109e07e35a24c00531528bc8cce106055528212debc7b3578606e0aeb` | `be05a406f1536fee62a1105b1d2ce70c64d61fa7b08241ff1cf1676c72c105ac` |
| 1800 / 50 | `5759fa1a22a4f7c5ecd2ea46c226a3c2bc5d6642f1780e3f56c25e12277c42ea` | `ad28904d0fc82963e529d86c33603e11498e9b4e121dd9b05230cd3742352ca4` |

Comparison artifact `data/interim/m3-full-period-matrix/candidate-comparison-v2.json`,
SHA-256 `db34cf842fe88558e2866d3168f6ffe2af3cd7fcbc71c99d11a8b20bcbddb0b6`. It
re-verified repeat bytes, lineage run IDs and output digests, grid checksum,
parameters, period identity, per-cell derived intensity, group summation, and
per-group conservation against the quality reports before comparing.

### Per-cell comparison

An earlier run of this comparison covered only the four axis-aligned pairs and
used ordinal ranks that broke ties by cell index. Both were corrected: all six
unordered pairs are now compared, and tied cells share a mean rank. The
superseded artifacts remain on disk. Corrected results, from
`candidate-comparison-v3.json`:

| Comparison | Cells changed | Net km | Spearman (tie-corrected) |
|---|---:|---:|---:|
| 300/30 to 300/50 | 2,482 | 15,380.768 | 0.999933 |
| 1800/30 to 1800/50 | 2,694 | 23,184.731 | 0.999900 |
| 300/50 to 1800/50 | 3,528 | 85,228.692 | 0.999194 |
| 300/30 to 1800/30 | 3,502 | 77,424.728 | 0.999255 |
| 300/50 to 1800/30 | 3,741 | 62,043.961 | 0.999209 |
| **300/30 to 1800/50** | **3,761** | **100,609.459** | **0.999122** |

The minimum across all six pairs is `0.999122`, between the two extremes. The
earlier claim that correlation was "at least 0.999192 between any two
candidates" was wrong on both counts: it omitted the two diagonal pairs and used
the uncorrected statistic.

- Net and absolute difference are equal in comparisons that only relax rules;
  those comparisons only add distance. The 300/50 to 1800/30 comparison relaxes
  the gap but tightens the speed ceiling: net change is 62,043.961 km and
  absolute change is 64,597.778 km, so some cells lose distance.
- Across all six all-commercial pairs, the top ten cells hold approximately
  9.35–14.17% of the absolute difference, so the changes
  are broadly distributed rather than concentrated in a few cells.
- The ten highest cells are **identical and identically ordered in all four
  candidates**, and the lowest tie-corrected rank correlation over all six pairs
  is 0.999122, so no candidate reorders the headline spatial pattern.
- Individual cells still move materially: maximum relative increase 330.09% for
  the gap change and 66.62% for the speed change, with 538-584 cells above 10%
  for the gap change.
- `distinct_mmsi` and `distinct_mmsi_dates` are identical across candidates, as
  expected for point-based descriptors.

### Where each rule adds distance

Quintiles of cells by their 300/30 baseline vessel-kilometres:

| Quintile | Median baseline km | Median distinct MMSI | Gain, gap 300 to 1800 | Gain, ceiling 30 to 50 |
|---|---:|---:|---:|---:|
| Q1 sparsest | 17.7 | 4 | 7.58% | 0.94% |
| Q2 | 68.5 | 14 | 5.74% | 1.16% |
| Q3 | 132.4 | 25 | 4.60% | 0.96% |
| Q4 | 235.6 | 32 | 4.45% | 1.01% |
| Q5 busiest | 789.2 | 72 | 4.13% | 0.75% |

The gap relaxation adds proportionally about 1.8 times more distance in the
sparsest cells than the busiest. The ceiling relaxation is essentially flat, and
falls mainly on passenger (1.09%) rather than cargo (0.67%) or tanker (0.24%).

### Visual verification, 2026-09-05

QGIS 4.2.1, offscreen rendering, common physical-unit class breaks for every
candidate rather than per-layer quantiles, with the accepted-domain outline in
blue and the VSR outline in orange drawn above the grid. Each render re-verified
the grid checksum, the mask checksum, and the immutable VSR snapshot checksum,
and reported 4,516 features, EPSG:3310, and zero invalid geometries. Images are
under `data/interim/m3-qgis-inspection/<candidate>/` and are ignored.

The renders were **examined**, not merely produced:

- Geography is correct: Point Conception, the northern Channel Islands, Santa
  Catalina, San Clemente, and the coast to San Diego all sit correctly, with land
  and islands excluded as holes and no cell over land.
- Cells are square and axis-aligned in EPSG:3310 with no shear, rotation, or
  offset, and the coastline registers against cell edges.
- Traffic structure is coherent: the Santa Barbara Channel approaches, the
  coastwise corridor, and the Los Angeles/Long Beach concentration all appear
  where commercial traffic is expected, with the darkest cells at the port.
- **A suspected artifact was investigated rather than accepted at face value.**
  Several straight one-cell-tall east-west bands appear, which grid-aligned
  artifacts often are. No row is anomalous: no grid row exceeds 1.8 times its
  neighbours' mean. Only three short high-contrast runs exist, of 5 to 10 cells.
  Their projected coordinates place the strongest at x -15,000 to 20,000,
  y -405,000, in the Santa Barbara Channel, and the other two on the approaches
  south of the Channel Islands. Established traffic separation in those waters
  runs broadly east-west, so a traffic explanation is **plausible**. That is an
  interpretation, not an established cause: coordinate agreement is not proof,
  the bands were not compared against published traffic-separation geometry, and
  no independent traffic product was consulted. What the numbers do establish is
  narrower — the banding is local, not a grid-wide row artifact.
- The northern and southern grid margins render paler than the interior. This is
  **consistent with** `censor-at-cleaned-extent` removing entry and exit distance
  where tracks cross the map boundary, but genuinely sparser boundary and
  offshore traffic would look the same, and these renders do not separate the two
  explanations. Neither reading is established here, and the pallor is not
  evidence about coverage in either direction.
- The 300/30 and 1800/50 extremes are visually near-identical, consistent with the
  rank correlation. The visible differences are additional fill in sparse offshore
  cells and slightly stronger east-west bands.

No projection shift, geometry gap, unexplained clipping, sliver, or displaced
feature was found in any candidate. This inspection establishes rendering and
spatial plausibility only. It is not evidence of observational completeness,
coverage, or any exposure or policy conclusion.
