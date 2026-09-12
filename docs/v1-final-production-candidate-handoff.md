# Version 1 final production candidate handoff

## Current status and approval boundary

Session: 2026-09-12. Branch: `chore/v1-final-production-candidate`.
Worktree: `C:/Users/teche/socal-whale-vessel-risk-v1-final-production-candidate`.

**The exact keyed candidate is built and locally verified, and is available for
independent technical audit. It is not approved for upload or deployment.**
The author must still reconfirm current ArcGIS free allowance, disabled
pay-as-you-go and restricted/unexpired key-administration facts before the
deployment approval packet is complete. This request is pending; historical
confirmation and current successful access are not substitutes for those facts.

No source defect or material content change was required. No push, PR, merge,
upload, deployment, linking, alias operation, account/key/referrer change,
analytical processing, replacement data download, cache clearing or manual
deletion occurred. All candidates, inputs, rollback packages and failed
verification evidence remain preserved. M7 and M9 remain in progress.

## Exact application source and candidate

| Identity | Value |
|---|---|
| Application source | `c63559c863c74256e5292c81511afe3e77e702fb` |
| Release | `v1-final-production-20260912-01` |
| Candidate directory, relative to worktree | `data/interim/m4-releases/v1-final-production-20260912-01` |
| Only proposed upload boundary beneath candidate | `deploy/.vercel/output/` |
| Receipt | `receipt.json` |
| Receipt SHA-256 | `6b3ccf5ab712df84ccf88766ac51f06fd1ddf61c4bf082ec918761947896f8d9` |
| Receipt mode / schema | `release-candidate-awaiting-approval` / 2 |
| Package | 903 files / 38,659,578 bytes |
| Public subtree | 902 files / 38,657,925 bytes |
| Public self-inventory | 901 files; excludes `release.json` itself |
| Build configuration | Keyed `arcgis/oceans`; key value never recorded |
| Local tools | Node 22.16.0; Chrome 152.0.7977.83; cached Vercel CLI 59.11.7 for read-only checks |

The initial worktree and branch did not exist; original-checkout status was
clean. They were created from fetched main without repurposing another
worktree. GitHub reported PR #38 merged at the exact source above; its caption
correction head `61baedb3ee477c1a6d53c5bbf4c00b68fedb6c39` had successful
`analysis` and `web` checks and was verified as an ancestor of fetched main.
Main remained at that source on the resumed September 12 fetch.

The initial documentation checkpoint is commit
`42800722096a8e3d56b3dd92ed188fedfa66777e`. To preserve it while satisfying
the existing tool's HEAD-equals-main rule, this same clean worktree temporarily
checked out the source detached for staging, then returned to the named branch.
No commit was reset or rewritten. This handoff and subsequent evidence commits
are documentation only; they do not change the packaged application source.
**Do not rebuild merely because these documentation commits change branch HEAD.**
Resolve final branch HEAD with `git rev-parse chore/v1-final-production-candidate`;
the final session response records its immutable value.

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

The current-production rollback inventory was rechecked again during the
September 12 preparation. Read-only Vercel project/API checks still identify
production deployment `dpl_FBbvuGPotSTLnbs1sJ1SRqaxXbXw` on that project
and the stable alias. The current package, not just the older M4 package,
remains the proposed rollback source.

## Build and resource observations

The new ignored `web/.env.local` was supplied privately by the author.
Existence, Git ignore status and a nonempty required variable were checked
without printing its value. Node's env-file option supplied the invoking process
environment to the existing stage tool, which removes inherited public overrides
and explicitly selects Oceans. No other worktree was searched for credentials.

Executed from the candidate worktree root, on the clean detached source:

```text
node --env-file=web/.env.local web/scripts/stage-release.mjs v1-final-production-20260912-01 C:/Users/teche/socal-whale-vessel-risk-m7-release-integration/data/interim/m7-release-integration/retained-inputs-20260908
node web/scripts/stage-release.mjs --verify v1-final-production-20260912-01 6b3ccf5ab712df84ccf88766ac51f06fd1ddf61c4bf082ec918761947896f8d9
```

Destination nonexistence was checked before staging. The September 11 proposed
name was never used. The isolated `npm run verify:clean` installed only locked
dependencies: 554 added / 555 audited, zero reported vulnerabilities. Type
generation, Prettier, ESLint, strict TypeScript, all 102 tests in 11 files,
and the Next.js 16.3.3 static build passed. The no-build-cache advisory and
ESLint 9.39.5 support warning were non-failing. No cache was cleared.

Before installation at 16:35:16 UTC, available physical memory was
2,095,874,048 bytes and free C: space was 56,881,725,440 bytes. A sampled
installation-time observation fell to 502,091,776 available bytes; subsequent
observations recovered before browser work began. These are samples, not a
profiler-derived runtime minimum or a new numeric gate. Browser runs followed
the build sequentially. No analytical-processing threshold was borrowed or
weakened. The stage tool's 100,000,000-byte / 15,000-file output limits passed.

The complete inventory has 825 JS, four HTML, eight text, four CSS, 51 WOFF2,
one SVG, four GeoJSON and six JSON files, including configuration and release
identity. Compared with current production, file count is unchanged and size
increased by 890 bytes. The inspected application-source diff consists of the
acceptance correction and its regression test, plus web documentation/example
wording. Generated results and public inputs are unchanged; the small compiled
text/identity difference introduces no new asset family.

Receipt read-back passed after staging and again after verification.
The static-only boundary inspection found no functions/runtime, public results
file, raw data, private lineage, source/dependency directory, environment file,
source map, local user path or VSR geometry file. High-specificity credential
marker scanning found none. The intentional public browser key appears in one
compiled JS file only and is absent from receipt and build log. This inspection
is not a generalized secret-detector guarantee.

## Exact local browser and public-input verification

The retained local static test server served only the package's `static/`
directory at the approved `http://localhost:3000` origin. Its injected failure
responses did not modify package bytes. It is a local verification helper, not
an application backend or upload input. Existing retained browser harnesses were
adapted into this worktree's ignored evidence directory; no new browser
dependency was installed. The same pre-existing Playwright installation used by
the retained procedure drove Chrome.

Chrome passed at 390 × 844, 820 × 1180 and 1440 × 900:

- Oceans ready, visible SDK attribution and working pointer pan/wheel zoom.
  A focused delayed-JavaScript check at every size proved one visible,
  viewport-contained application fallback before readiness, then zero
  application fallbacks and one SDK attribution control after readiness.
- Five single-instance layers, ordered whale / vessel / exposure / domain /
  VSR, with exact counts 4,516 / 2,793 / 2,793 / 1 / 1. Initial visibility is
  off / off / on / on / on. All five toggles restore their state.
- Product/log switching changes the existing exposure renderer, retaining the
  exact layer order with no duplicate. The normal matrix and targeted follow-up
  cover both renderer directions.
- Generated 92.2/7.8, 98.5/1.5 and 74.9/25.1 shares, −17.2741 change, threshold
  and grid sensitivities, source dates, identities and limitations remain
  reachable. The corrected review/acceptance sentence and its non-causal,
  non-policy limitation are present; the stale pending-review sentence is absent.
- Keyboard Space/Enter toggles, formula choice and disclosures work; focus is
  3 px. Document/panel scrolling works without horizontal overflow. The desktop
  whale popup opens with visible title and values. No visitor sign-in appeared.
- Blocking each of the five layers independently removes only that layer,
  disables its control and leaves its warning, four other loaded layers,
  generated results and working pan/zoom. Missing exposure, malformed exposure
  and mismatched manifest cases are isolated. Malformed data was tested with
  checksum support deliberately unavailable to exercise the SDK parse failure.

All eight packaged layer/manifest responses were fetched locally and matched
their exact hashes and byte sizes. The served release identity matched the
receipt; `/results/exposure-results.v1.json` returned 404. The application
verifies its fetched project data separately.

Normal overview screenshots at all three sizes and selected expanded-text,
popup, exposure-failure and VSR-failure captures were visually inspected.
The map, scientific framing, distinct headline denominators, sensitivities,
attribution, focus and failure warnings were legible. No application source
change was needed. This is not a full WCAG audit or real-device benchmark.

Normal runs had no application request/HTTP or console errors. The first matrix
recorded one tablet and six desktop ArcGIS request failures during interaction,
without retaining their reasons. A targeted follow-up retained only categories
and reasons and identified basemap-tile `net::ERR_ABORTED` cancellations during
navigation, with the map ready and functional. It does not retroactively assign
a reason to every original request. Deliberate request blocking and malformed
exposure produced expected resource/SDK errors, isolated to their cases.

The historical whole-connection functional evidence in the
[M5–M7 closure handoff](m5-m7-closure-handoff.md) is retained, not newly executed.
No deployed header/compression/freshness check or public browser test of this
new candidate is claimed. Those remain post-deployment gates.

## Failures and evidence interpretation

Two failed harness reports are preserved unchanged:

1. `exposure-failures.json` expected the generic unavailable warning for a
   manifest mismatch. The application correctly showed the specific
   display/manifest/results mismatch warning. The screenshot was inspected and
   `interaction-followup.json` freshly passed the corrected exact assertion.
   Missing and malformed exposure checks had passed in the original report.
2. `interaction-followup.json` used a broad text locator that also found
   the SDK's shadow-DOM “Powered by Esri” credit after readiness. All toggle,
   renderer, failure pan/zoom and corrected manifest assertions passed.
   `attribution-followup.json` then used separate light-DOM and SDK selectors
   and passed the before/after check at all three sizes.

The initial normal-matrix attribution sampler incorrectly looked for an anchor
rather than the application's paragraph and is not used as fallback evidence.
The focused follow-up supplies that evidence. A consolidated verification
record checks the applicable successful assertions and binds all original and
corrected reports to the exact receipt; it does not edit failed reports.

Two Windows wildcard searches and one optional inline property-hash probe failed
locally because of shell path/quoting syntax. Exact-path searches and a
file-based probe replaced them. No source or analytical check failed. The Vercel
API help command returned 1 while printing help; actual read-only lookups passed.

Evidence directory: `data/interim/v1-final-verification-20260912-01/`.
Principal SHA-256 identities:

| Evidence | SHA-256 |
|---|---|
| Consolidated verification summary | `41f8686030d1f401c207b7852068b39f9c4fa9317cb366cd6adeba8c0fab1502` |
| Normal and five isolated-layer matrix | `245b2e0c430ec7be79eb5ec5fb5cfb5115c4fcb4905fd15fe7056b4d497bf572` |
| Exposure cases, preserved failed assertion | `e447f20f99c3abd25c3fd22af9bd07658d07cfd447229d0cf1643557d09c76ec` |
| Interaction follow-up, preserved locator failure | `8a6c8056d7c17614edb166de1f93d1751a97bc2f48f2be292ea36a5ffa38ae8c` |
| Corrected attribution follow-up | `4f47fecf848a33b9a34313e729a0791dc60f542780cb4fd9899ddd2f4ca4bc7d` |
| Package boundary | `355ed7eedae3ccc6a3c0018a957113d47965e4e8466b831edc8bc50781c87214` |
| Key referrers | `1b36c13c9637eadddb666a58eedf8d92b0f471b3973ae703dec6bf1cb2405956` |
| Anonymous VSR comparison | `cefb960e2b53e349de9d50f9bb3670a1a30c2cf00d435716c24e5bb6c4e63c5f` |
| Candidate `verification.log` | `df78362ceee97909671a7d901689dd2aa3c8f66a7673508a4d0c51099de56af6` |

The summary inventories 31 supporting report/harness/screenshot files by hash
and size. The build log remains beneath the candidate, outside its upload
boundary. No raw HAR, key-bearing URL, credential value or copied geometry is
retained in evidence. Harness commands, run sequentially from the worktree root:

```text
node data/interim/v1-final-verification-20260912-01/vsr.mjs
node --env-file=web/.env.local data/interim/v1-final-verification-20260912-01/key.mjs
node --env-file=web/.env.local data/interim/v1-final-verification-20260912-01/package.mjs
node data/interim/v1-final-verification-20260912-01/server.mjs data/interim/m4-releases/v1-final-production-20260912-01/deploy/.vercel/output/static 3000
node data/interim/v1-final-verification-20260912-01/browser.mjs
node data/interim/v1-final-verification-20260912-01/exposure-failures.mjs
node data/interim/v1-final-verification-20260912-01/interaction-followup.mjs
node data/interim/v1-final-verification-20260912-01/attribution-followup.mjs
node data/interim/v1-final-verification-20260912-01/consolidate.mjs
```

The server ran concurrently with sequential browser checks and was stopped
after verification. Do not rerun harnesses into these existing evidence filenames;
several intentionally refuse
overwrites and the earlier adapted harness also needs a new evidence directory.

The documentation handoff check verified the five-file documentation-only stage,
169 relative links/anchors, staged credential markers and absence of the actual
browser key from all 18 evidence text files. `git diff --cached --check` passed
and the staged diff was reviewed. Candidates, evidence and `web/.env.local`
remain ignored. No Python rerun or additional full web suite was needed for
these later Markdown-only edits; the clean web gates ran on the packaged source.
Both PR CI jobs remain required if a later PR is separately authorized.

## Release-time VSR and source-use posture

At 2026-09-12T16:36:57Z, anonymous HTTP 200 responses returned item
`b400c7f418b04dc5a9d7ce5015adae32`, `WhaleAtlas_2026`, owner
`danielle_cmsf`, modified `2026-06-01T19:24:22Z`; expected Feature Layer 0,
version 12, object ID `FID`, capability `Query`; and exactly one FID = 126.

Immutable snapshot SHA-256 remained
`2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783`.
Complete geometry objects, ordered coordinate arrays and sorted complete
properties compared in memory with zero tolerance. Both coordinate hashes were
`24c486e3f05e8e15a855ba98845893597edf6c25c64c56d396e6b8af09da2693`;
both geometry-object hashes were
`bf50488078ed558029d1ead6676b4f4d33e5ed20b2e560b4dc564f8e5615f196`.
Both compact, codepoint-key-sorted property hashes were
`2bb433f71ee6cb33de4fdf261e63035a0f7643d87779925ac0062bc4837961e1`.
This equality check does not depend on reproducing older reports' property
fingerprints; their serialization difference was not resolved here. The exact
snapshot byte hash and current live/snapshot property equality both passed.
No snapshot or fetched geometry was written.

The package retains NOAA whale/AIS and receiver-domain citations and scientific
limitations. VSR remains publisher-hosted with Danielle Alvarez/CMSF/BWBS credit
and the non-navigational disclaimer. Public access is not a redistribution
licence. The [source register](data-sources.md) and ADR 0019 own that posture.

## Account facts: observed versus author-confirmed

Current read-only Vercel CLI/API observations: scope `stemry`, plan `hobby`,
existing project `socal-whale-vessel-overlap`, Git integration absent, production
deployment and stable alias unchanged. Node 24.x is the remote project setting;
this candidate was built locally with Node 22.16.0 and proposes prebuilt static
upload, so no remote build or setting change is involved.

Current key behavior: authorization-header requests to Oceans styles returned
200 from `http://localhost:3000/` and
`https://socal-whale-vessel-overlap.vercel.app/`, and 401 from an unrelated
origin. Keyed browser rendering passed. These prove current access/referrer
behavior, not expiry policy, complete privileges, usage balance or billing UI.

Reuse author confirmations dated September 7 and September 9 for personal,
unpaid, non-monetized portfolio eligibility and accepted exploratory scientific
wording. September 9 also confirmed free-only account conditions and the
restricted valid key at that time. The September 12 message supplied the local
key but did not expressly reconfirm current allowance, disabled pay-as-you-go,
expiry or administrative scope. That question remains pending. No private
billing UI was observed and no account setting was changed.

Official [Vercel Hobby](https://vercel.com/docs/plans/hobby),
[limits](https://vercel.com/docs/limits),
[fair-use](https://vercel.com/docs/limits/fair-use-guidelines),
[Esri billing](https://location.arcgis.com/help/billing/),
[pricing](https://location.arcgis.com/pricing/),
[licensing/attribution](https://developers.arcgis.com/javascript/latest/licensing/)
and [API-key documentation](https://developers.arcgis.com/documentation/security-and-authentication/api-key-authentication/api-key-credentials/location-platform/)
were rechecked September 12. The selected personal Hobby/static route remains
subject to the 100 MB / 15,000-file limits; ArcGIS documents two million free
basemap tiles and restricted access once free capacity is exhausted with
pay-as-you-go disabled. Published allowance is not proof of this account's
remaining capacity. No paid fallback is authorized.

## Exact proposed action after audit and approval

Only target: `stemry/socal-whale-vessel-overlap`.
Stable origin: `https://socal-whale-vessel-overlap.vercel.app/`.

1. Independently audit this exact candidate, receipt and documentation branch.
   Resolve findings without silently changing the packaged source identity.
2. Obtain missing current account facts, then separate explicit author approval
   for this release name, application SHA, receipt and target. This handoff
   requests no upload authorization for an incomplete administrative packet.
3. Only after approval, privately authenticate if necessary, link only the
   candidate's `deploy/` directory to the existing project, read scope/project
   back, and run the exact receipt verification immediately before upload.
4. Proposed upload from that candidate's `deploy/` directory:
   `vercel deploy --prebuilt --prod --scope stemry`.
   Only `.vercel/output` is the payload. Keep Git integration disconnected;
   do not change `stemry-waitlist`, accounts, keys, billing or paid features.
5. Verify the resulting deployment and stable alias, every public receipt byte,
   media/compression/cache/HTML-freshness behavior, complete anonymous keyed
   three-viewport browser/failure matrix, corrected acceptance and generated
   content, whole-connection usability, and fresh VSR identity/snapshot match.
   Use [development](development.md#release-staging-and-approval-procedure).
6. Reassess the dated README screenshot against deployed content and record
   evidence. M7/M9 closure remains a separate owner-controlled decision after
   all criteria pass. Upload success alone closes neither milestone.

Rollback, if separately approved, re-uploads the retained current M7 package to
the same project, verifies its original source and receipt at the stable origin,
and requires its embedded key still valid. No paid rollback feature is needed.

## Checkpoint history

September 11 preparation stopped before staging because the required private
key was absent; nine input hashes and current rollback inventory had passed.
That state was committed in `4280072`. The September 12 author-supplied key
allowed the exact-source production build and local checks above. The earlier
checkpoint remains history, not the current candidate status.
