# M5–M7 closure audit handoff

**Audit date:** 2026-09-09

**Branch:** `docs/m5-m7-closure`

**Base:** `origin/main` at
`3a9d8028a670d2c06687c9839739dd3fdac7f0b3`

This is the execution handoff for the closure audit. The
[roadmap](roadmap.md) owns milestone status; the
[project brief](project-brief.md) owns scope; and the existing M5, M6, and M7
handoffs retain detailed run history. No analysis or application source, test,
data, deployment, account setting, or M8-owned file was changed by the initial
audit commit. At the author's follow-up request, this branch now also corrects
the results-panel acceptance sentence and adds one focused web regression test;
analysis, M8-owned files, data, and external state remain unchanged.
The M4 section's stale `In progress` label was also aligned with its already
`Complete` roadmap-table status; no M4 criterion was re-audited here.

## Verdict

| Milestone                    | Verdict         | Reason                                                                                                                                                       |
| ---------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| M5 — Core input layers       | **Complete**    | All six completion criteria have exact retained local and deployed evidence.                                                                                 |
| M6 — Exposure analysis       | **Complete**    | All seven criteria are supported by deterministic artifacts, known-answer tests, independent recomputation, review, acceptance, and deployed reconciliation. |
| M7 — Application integration | **In progress** | The whole-connection criterion now passes. Corrected review/acceptance wording passes locally but is not yet in a reviewed, authorized public release.       |

M8 and M9 remain unchanged. “Largest outside concentrations” is satisfied by a
reproducible ranking of contributing outside cells; those cells are **not**
claimed to be validated hotspot clusters.

## Exact release and evidence identity

The production candidate is retained at
`C:/Users/teche/socal-whale-vessel-risk-m7-production-candidate/data/interim/m4-releases/m7-production-candidate-20260909-01`.

| Identity                  | Verified value                                                     |
| ------------------------- | ------------------------------------------------------------------ |
| Application source commit | `3dfedc1faab1dd830a79ab5fa0efce3b07c9db25`                         |
| Release receipt           | `e6532385fd3641275f38d9f203e75aa64fed0a1739ff3c29799113208f958ede` |
| Receipt mode              | schema 2 / `release-candidate-awaiting-approval`                   |
| Upload boundary           | `deploy/.vercel/output/`, 903 files, 38,658,688 bytes              |
| Deployment                | `dpl_FBbvuGPotSTLnbs1sJ1SRqaxXbXw`                                 |
| Stable origin             | `https://socal-whale-vessel-overlap.vercel.app`                    |
| Public inventory          | 902 files, 38,657,035 decoded bytes; zero receipt mismatches       |

The documented `node scripts/stage-release.mjs --verify` command independently
re-read the retained package and returned the exact source commit, mode, file
count, byte count, and receipt above. A fresh anonymous read of the stable
origin returned HTTP 200 and `release.json` still identified application commit
`3dfedc1f…db25` and the same receipt mode.

The release contains these exact data identities:

| Input              | Data SHA-256                                                       | Manifest SHA-256                                                   |
| ------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Whale              | `831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154` | `404c53356be7d743cbc5e4bc1b5741e4938c84e206caf1d53468954e368c8108` |
| Vessel             | `3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288` | `6d18aaf3e74038db0165884c0daaf99b5acf400dd42f5cccccb42da848ff995d` |
| Domain             | `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf` | `d340dc2703f3a891a62d4735dc442a7545a6330e9e3322b95f742f502b3b0de6` |
| Exposure           | `1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb` | `0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0` |
| Build-only results | `ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60` | results ID `exposure-results-8a0bf6c27e00fb40a13d6870`             |

The build-only results file is not public. The application-source commit is an
ancestor of current `main`. Commits `d208bf0` (candidate evidence), `e3ba3a2`
(author confirmations), and `bde3b4d` (deployment evidence), plus their merge
commits, change documentation only; a direct source-to-current-main diff found
no later application-source change. This preserves the distinction between the
deployed source and later evidence-only records.

The following retained production reports were opened and rehashed directly,
not accepted only from handoff prose:

| Report                              | SHA-256                                                            |
| ----------------------------------- | ------------------------------------------------------------------ |
| Full public HTTP inventory          | `f33cb60e6d013c8a8a03e4c984d9fb211a0e484e5248e84c47ff78c5cec6c48b` |
| Deployed Chrome matrix              | `2a2373e7f04704bddf6934449b828cc64694ede43f8e762e506c747cab3efadb` |
| Keyboard/focus                      | `8ed4b9a514a99a0c73b38b2e4d47c51b2f0f71634ff91f71fa24a85fb717a34a` |
| Network-cancellation classification | `8a570434c8a2eb6546be054374b67c7ea48e622005082ba27101d9ed92db678f` |
| Partial mid-range model             | `4a1154e6935bb3bf49b54efe08281b9f5e8ec3df2a4d8b79abebfc569ed9ca76` |
| Public VSR comparison               | `fec03cdf37c533517b43b83844121c25ad5298c7726093919cc6ac65e97e66fa` |

## M5 criterion assessment

| Criterion                                                      | Exact evidence inspected                                                                                                                                                                                                                                                                                                                                                   | Result   |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| Layers render at study-area scale within acceptable load time  | Deployed Chrome report `2a2373…dadb` loaded the 4,516-cell whale, 2,793-cell vessel, one-feature domain, and publisher VSR layers once and in order at 390 × 844, 820 × 1180, and 1440 × 900. The recorded clean desktop context transferred 1,365,369 compressed bytes for the three project inputs and reached usable ready state.                                       | **Pass** |
| Public access works end to end, with access mode distinguished | HTTP report `f33cb6…c48b` matched every public byte and verified headers; Chrome report `2a2373…dadb` recorded no sign-in UI. Whale, vessel, and domain are token-free same-origin files; Oceans uses the scoped browser key; VSR is the publisher's anonymous service.                                                                                                    | **Pass** |
| Every legend states units and meaning                          | Deployed browser assertions and directly inspected phone/desktop screenshots show animals/km², vessel-km/km², accepted-domain exclusion semantics, and relative-exposure/index meanings. Renderer/class definitions match the manifests.                                                                                                                                   | **Pass** |
| Every layer names source and retrieval/processing date         | Deployed browser report records `hasM5Dates: true`. Reachable disclosures show NOAA/SWFSC and the 25 August 2026 whale retrieval, the AIS-derived vessel layer and 5 September 2026 processing, and the reception-station domain with 29 August 2026 evidence processing.                                                                                                  | **Pass** |
| Geometry aligns; no projection mismatch is visible             | Whale QGIS evidence is bound to `831a5412…e154`. Vessel/domain QGIS report `2cfca5ca98e5de69b5feead7db6e5d8b9e3d276a6076f1a9c55e43bdce55a140` binds the deployed hashes and finds no invalid/empty/outside geometry. The retained renders and deployed screenshots were inspected directly and show aligned coastline/islands, receiver arcs, corridors, VSR, and basemap. | **Pass** |
| VSR loads anonymously from publisher and is not copied         | Report `fec03c…6fa` verifies item `b400c7f418b04dc5a9d7ce5015adae32`, layer version 12 with Query, and exactly one `FID = 126`; live properties and geometry exactly match immutable snapshot `2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783`. No geometry was retained or packaged.                                                                    | **Pass** |

## M6 criterion assessment

The current-code first and repeat bundles under
`C:/Users/teche/socal-whale-vessel-risk-exposure-results-delivery/data/derived/`
were rehashed directly. Their 5 km table (`a8e65b6d…35a29`), 10 km table
(`cff427ae…ef194`), and sensitivity report (`520afde7…04ff`) are byte-identical;
only timestamp-bearing run metadata differs as designed. QGIS report
`5c5eadc6d000c85981593d2ac53f004b9162a093acb944908447dff5736bd9c1`
and its two exact renders (`80df7d3c…9007`, `5e8f0b84…abe8`) were also inspected.

| Criterion                                                 | Exact evidence inspected                                                                                                                                                                                                                                                                                                                                                     | Result   |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| Calculation is reproducible from derived inputs           | First/repeat source and delivery outputs match byte-for-byte from checksum-pinned water, whale, vessel, domain, and VSR inputs. The audit independently recomputed the product and log formulas over all 4,516 serialized 5 km rows with zero formula residual.                                                                                                              | **Pass** |
| Every statistic states basis and threshold                | Sensitivity report, results contract, and deployed panel distinguish integrated-exposure shares from qualified-water-area shares; p80/p90/p95 and positive-only definitions include basis and tie handling.                                                                                                                                                                  | **Pass** |
| Fractional boundary accounting and known-answer cases     | Existing synthetic tests cover 30/25/45% cells, centroid/majority failure, holes/slivers, dry/excluded cells, and conservation. Independent recomputation found maximum inside-plus-outside area residual `4.69e-14 km²` and fractional integrated-total residual `2.34e-13`. The uniform-within-water-cell assumption is visible.                                           | **Pass** |
| Accepted analytical domain applied exactly                | The audit found 2,793 qualified and 1,723 `excluded_domain` rows, qualified area 64,716.65982166733 km², and no excluded row in the public layer. Outside-domain water is described as excluded, never low traffic.                                                                                                                                                          | **Pass** |
| Vocabulary follows the brief                              | Retained report, results contract, screenshots, and public HTML consistently use relative exposure/spatial overlap/proxy language and disclaim collision probability, observed encounters, causal effectiveness, and policy conclusions.                                                                                                                                     | **Pass** |
| Sensitivity includes non-robust result                    | The deployed text and retained report identify the 5 km log-traffic inside share of 74.9444%, down 17.2741 percentage points from the 92.2185% product share, as materially non-robust; 10 km and threshold sensitivities remain reachable.                                                                                                                                  | **Pass** |
| Layer and statistics reconcile; live VSR matches snapshot | Independent arithmetic reproduced total `6536.657810883277`, inside `6028.008180683845`, outside `508.6496301994318`, and share `0.9221850607886265`; p90 threshold `0.22859788468419606`, 281 selected cells, and inside-area share `0.985023814132108`; all 2,793 deployed display rows matched six analytical fields. Pre/post-deployment VSR comparisons passed exactly. | **Pass** |

The product top ten outside contributors account for 9.4717% of outside
exposure; the first three are `r015_c079`, `r015_c078`, and `r016_c054`.
Independent numerical/content review covered all 24 threshold/area comparisons
and all 2,793 display cells. The separately recorded author acceptance covers
the bounded exploratory results and limitations wording, not collision risk or
VSR effectiveness.

## M7 criterion assessment

| Criterion                                      | Exact evidence inspected                                                                                                                                                                                                                                      | Result                   |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| Displayed statistics exactly match analysis    | The release receipt binds results ID `exposure-results-8a0b…`; direct recomputation and the all-row comparison above match the deployed values and layer.                                                                                                     | **Pass**                 |
| First-time visitor can understand the display  | Deployed three-viewport report and screenshots show an immediately visible results summary, layer names/legends, source/method disclosures, and responsive controls without requiring repository context.                                                     | **Pass**                 |
| Limitations are visible in the interface       | Mixed vintages, modeled habitat, receiver-qualified domain, fractional uniformity assumption, formula sensitivity, separate speed treatment, and excluded-cell meaning are visible in the panel; detailed sensitivity remains reachable in-page.              | **Pass**                 |
| Wording follows scientific-communication rules | Scientific proxy and limitation wording passes. The public build still has the factually stale review/acceptance sentence; corrected source passes locally but awaits release.                                                                                | **Gap at public origin** |
| Usable on a mid-range connection               | Whole-connection report `77ecd86b…509f` applied cache-disabled 4× CPU and 100 ms / 10 Mbps network emulation globally before navigation. HTML, 87 JavaScript, five project-layer, 96 basemap, and four VSR responses succeeded; all functional checks passed. | **Pass**                 |

The successful run used Chrome 152 at 820 × 1180. All five layers loaded once;
results, formula and visibility controls, pan/zoom, scrolling, horizontal
containment, keyboard toggling and 3 px focus passed. There were no non-empty
alerts, console/page errors, or unexpected failures. One superseded basemap tile
was cancelled during interaction while the map remained ready. The report and
harness hashes are:

- report: `77ecd86bfec9c34effac2d7150dd4a8ca80425df7f27cefebcbdd56b7ba9509f`;
- harness: `438a36c0b5e62d0d0c7cd3d164e98545a33e3fb6d674c5c9453f8850a1840c21`;
- screenshot: `2eff4e92d0ca2a340bd3e1c470997f641e123823ab3a3097ce3011d158a29c01`.

The ignored evidence is under
`data/interim/m7-whole-connection-20260909-01/`. Two failed reports are
preserved: attempt 1 exposed a focus-modality harness error, and attempt 2
exposed an empty `role="alert"` element that was not an application warning.
Neither report contains an application failure. The procedure is owned by
[development.md](development.md#m7-whole-connection-functional-check). No raw
HAR, URL, credential, key, or external-service timing was retained, and this is
not an ArcGIS benchmark or real-device claim.

The stale results-panel sentence is corrected in source to say that independent
numerical/scientific-content review passed and the author accepted the values for
exploratory public presentation. It also says those actions do not change the
limitations or turn the overlap proxy into a causal or policy result. A focused
regression and the complete clean web gate pass: formatting, lint, strict
TypeScript, 102 tests in 11 files, and the static build. The optimized HTML
contains the corrected sentence and no pending-review sentence.

Application-source commit `9831c6ea0a2a1344ec5e706e1d6117ecee298888`
also passed the existing isolated release packager as keyless rehearsal
`m7-acceptance-copy-rehearsal-20260909-01`: 903 files, 38,659,273 bytes,
receipt SHA-256
`b6d19fd8fc2641d2c9d85f9028df884519a1f50be0351d4d82d5e690819d7ee2`.
Independent receipt read-back returned the same commit, mode, file count and
bytes. The packaged HTML has two serialized corrected-text occurrences and zero
pending-review matches. Sanitized `verification.log` SHA-256 is
`3b7b6c9577698bd8a2a6bf600a2ce81eac287b504b88895dd1cff24c296b37ea`.
The package is `keyless-rehearsal-not-for-deployment`; it is not a production
candidate, review record, deployment authorization, or public verification.

## Verification and next steps

The initial documentation verification passed. Follow-up verification added the
complete clean web gate, direct optimized-HTML inspection, and isolated release
rehearsal described above. Final `git diff --check`, changed-document
link/anchor validation, staged secret-pattern/scope inspection, and staged-diff
review passed; the worktree was clean after the evidence commit.

Dependency-ordered next steps:

1. Review and merge this source correction through the normal PR and CI path.
2. From the merged clean `origin/main`, create a fresh keyed candidate, verify
   its receipt and browser behavior, obtain explicit authorization, deploy only
   that package, and verify the corrected public text plus release-time VSR.
3. Mark M7 complete only after the corrected public release passes.
4. Continue M8 and then M9 in roadmap dependency order. Do not infer M8/M9
   completion from this audit.
