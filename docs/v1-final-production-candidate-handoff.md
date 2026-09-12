# Version 1 final production candidate handoff

## Status: preparation paused before staging

Session: 2026-09-11 Pacific / 2026-09-12 UTC. Branch:
`chore/v1-final-production-candidate`. Worktree:
`C:/Users/teche/socal-whale-vessel-risk-v1-final-production-candidate`.

**No final candidate exists yet; it is not ready for independent candidate
audit or deployment approval.** The required browser key was absent from the
process environment and this worktree's `web/.env.local`. The author was asked
to populate that ignored file privately with `NEXT_PUBLIC_ARCGIS_API_KEY` and
confirm current free-only account/key conditions. No credential was searched
for in another worktree, read into output, or copied.

The [roadmap](roadmap.md) remains authoritative: M1–M6 and M8 are complete;
M7 and M9 remain in progress. No upload, deployment, linking, alias operation,
account change, push, PR, merge, installation, analytical processing, download
of replacement data, cache clearing, or deletion occurred.

## Source and workspace verification

`git status --short` was empty in the original checkout. `git worktree list
--porcelain`, branch lookup, and exact destination existence checks found no
existing requested branch/worktree. Created the requested worktree from freshly
fetched `origin/main`, without modifying other worktrees.

Exact selected merged-main application source:
`c63559c863c74256e5292c81511afe3e77e702fb`.

`gh pr view 38 --json state,mergeCommit,headRefOid,statusCheckRollup` confirmed
PR #38 is merged at that SHA. Its head
`61baedb3ee477c1a6d53c5bbf4c00b68fedb6c39` includes the screenshot-caption
correction and has successful `analysis` and `web` checks. An ancestry check
against fetched `origin/main` returned 0. The application diff from production
contains the corrected review/acceptance sentence and its regression test;
the generated results are unchanged.

Later commits on this branch record documentation only. They are not the
application source and must not be substituted for it. Because staging requires
HEAD equal to freshly fetched `origin/main`, resume from a clean detached
checkout of the verified merged source in this same worktree, retaining this
documentation branch and its commits. Return to the branch to record evidence.
Do not reset or rewrite its documentation commits. If main changes, inspect the
new source and update this identity before staging.

## Accepted inputs rehashed

Read-only retained input directory:
`C:/Users/teche/socal-whale-vessel-risk-m7-release-integration/data/interim/m7-release-integration/retained-inputs-20260908`.

All eight files matched `web/scripts/release-inputs.json` using
`Get-FileHash -Algorithm SHA256`; none was regenerated or copied. These are the
accepted generation manifests, not M8 reproduction manifests.

| Input | Bytes | SHA-256 |
|---|---:|---|
| Whale GeoJSON | 3,277,329 | `831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154` |
| Whale manifest | 7,244 | `404c53356be7d743cbc5e4bc1b5741e4938c84e206caf1d53468954e368c8108` |
| Vessel GeoJSON | 2,720,788 | `3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288` |
| Vessel manifest | 9,302 | `6d18aaf3e74038db0165884c0daaf99b5acf400dd42f5cccccb42da848ff995d` |
| Domain GeoJSON | 867,910 | `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf` |
| Domain manifest | 5,860 | `d340dc2703f3a891a62d4735dc442a7545a6330e9e3322b95f742f502b3b0de6` |
| Exposure GeoJSON | 2,542,744 | `1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb` |
| Exposure manifest | 6,803 | `0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0` |
| Build-only results JSON | 31,381 | `ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60` |

Results path: `results/exposure-results.v1.json`; results ID:
`exposure-results-8a0bf6c27e00fb40a13d6870`. Its hash was explicitly compared
with the committed pin and passed.

## Current-production rollback verified

Release: `m7-production-candidate-20260909-01`.
Application source: `3dfedc1faab1dd830a79ab5fa0efce3b07c9db25`.
Retained directory:
`C:/Users/teche/socal-whale-vessel-risk-m7-production-candidate/data/interim/m4-releases/m7-production-candidate-20260909-01`.
Receipt: `receipt.json`, SHA-256
`e6532385fd3641275f38d9f203e75aa64fed0a1739ff3c29799113208f958ede`.

Executed the existing command from that worktree's release script:

```text
node C:/Users/teche/socal-whale-vessel-risk-m7-production-candidate/web/scripts/stage-release.mjs --verify m7-production-candidate-20260909-01 e6532385fd3641275f38d9f203e75aa64fed0a1739ff3c29799113208f958ede
```

Passed full receipt/inventory read-back: 903 package files, 38,658,688 bytes,
schema-2 candidate mode, exact source above. The historical public inventory is
902 files / 38,657,035 bytes. A fresh anonymous HTTP request to the stable
origin's `release.json` returned 200 and the same application source, with
901 self-inventoried files. This session did not repeat the complete public
asset/browser matrix. The current M7 package is the rollback candidate; the
older M4 package and all prior evidence remain preserved. Future rollback still
requires explicit approval and a valid embedded key.

## Outstanding candidate and account gates

Proposed unused name: `v1-final-production-20260911-01`; exact destination
nonexistence was verified. Intended candidate directory, relative to this
worktree: `data/interim/m4-releases/v1-final-production-20260911-01`.
Intended upload directory beneath it: `deploy/.vercel/output`.
No candidate receipt, file count, byte count, or verification report exists.

At `2026-09-12T06:43:24Z`, available physical memory was 2,682,490,880 bytes
and C: free space was 56,760,664,064 bytes. This is an observation, not a passed
installation/build gate. Recheck immediately before execution. The release
tool enforces 100,000,000 package bytes and 15,000 files; do not substitute
unrelated analytical-processing memory thresholds. No installation was needed
for the read-only verification performed here.

Historical author confirmations on 2026-09-07 cover personal, unpaid,
non-monetized Hobby eligibility, Location Platform, disabled pay-as-you-go,
available free basemap capacity, and basemap-only privileges. On 2026-09-09
the author reconfirmed the free-only conditions, allowance, restricted valid
key, and accepted exploratory scientific wording. Reuse that scientific
acceptance; current allowance, validity/expiry, referrer behavior, and account
state still require the release procedure's recheck. No private billing UI was
observed in this session. No new provider-policy, authenticated project, or key
access verification is claimed.

Remaining work, in order:

1. Receive private key setup and missing current account facts. Recheck the
   applicable provider rules and exact allowed/disallowed referrer behavior,
   without retaining credentials or key-bearing URLs.
2. Refresh clean merged-main identity, resource availability, and destination
   nonexistence. Use existing `stage-release.mjs` in production mode with the
   retained input directory above; its isolated `npm run verify:clean` installs
   locked dependencies and runs all web gates. No keyless substitute.
3. Re-read the exact new receipt with `stage-release.mjs --verify`, inspect the
   actual static/public boundary, record counts/bytes, corrected wording, all
   pins, and sanitized evidence. No results endpoint or copied VSR geometry.
4. Execute the keyed packaged-output Chrome matrix at 390 × 844, 820 × 1180,
   and 1440 × 900, including Oceans/attribution, five independent layers and
   counts/order, controls/product-log switching, generated results/sensitivities,
   dates/limitations/corrected acceptance, pan/zoom, focus/keyboard/scrolling,
   overflow, and isolated failures. Distinguish retained evidence from new runs.
5. Perform the anonymous publisher item/layer/FID = 126 identity/version and
   zero-tolerance snapshot comparison required by ADR 0019. Not executed this
   session; M9's earlier check is history, not a final-candidate gate. Do not
   retain fetched geometry. Stop on any mismatch or source defect.
6. Complete this packet and owning status records, commit documentation only,
   and stop for independent audit and separate exact-deployment approval.

No check has been waived. The build, browser, VSR, package boundary and current
account/provider gates above are pending, not passed or failed. Initial broad
documentation output was truncated; focused section reads recovered the
relevant release instructions. No release command failed or created a partial
candidate.

## Proposed upload and mandatory later checks

Only target: `stemry/socal-whale-vessel-overlap`, stable origin
`https://socal-whale-vessel-overlap.vercel.app/`. No account settings, Git
integration, other project, paid feature, or alias change is authorized here.

After completed candidate audit and separate explicit approval, the existing
procedure proposes linking only its `deploy/` directory to that existing
project, reading the target back, re-verifying the approved receipt immediately
before upload, and running `vercel deploy --prebuilt --prod --scope stemry`
from that directory. This is a future proposal, not an executed action or a
request to approve an unfinished package.

Mandatory post-deployment checks remain those in
[development](development.md#release-staging-and-approval-procedure): exact
deployment/stable-origin identity and every public receipt byte; media,
compression, immutable layer caching, no-store release identity and HTML
freshness; complete anonymous three-viewport keyed browser and isolated-failure
matrix; corrected acceptance and generated values/limitations; whole-connection
usability; and publisher VSR snapshot consistency. Reassess the dated README
screenshot and record evidence before any M7/M9 closure decision. Upload
success alone closes neither milestone.
