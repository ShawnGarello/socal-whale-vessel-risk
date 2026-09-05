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

Execute the first profiled spatial candidate next. No spatial matrix,
new spatial verification, or final method selection has run.
M3 remains In progress. No session commit yet; no push or merge authorized.
