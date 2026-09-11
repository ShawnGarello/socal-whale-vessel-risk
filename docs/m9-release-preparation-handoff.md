# M9 release-preparation handoff

**Session date:** 2026-09-11

**Branch:** `docs/m9-release-preparation`

**Base:** fetched `origin/main` at
`ecd81d0097caa2f61449327ed34329099b08b12d` (merged PR #37, M8 verification)

**Final HEAD:** the commit containing this handoff on the branch above; resolve
the immutable value with `git rev-parse HEAD`. A commit cannot embed its own
hash, so the session's final response must record that value.

The [roadmap](roadmap.md) owns milestone status. This branch marks M9 **In
progress** and prepares documentation and release evidence only. It does not
close M7 or M9, declare Version 1 fully released, create a production candidate,
access credentials, change an account, push, open a PR, merge, or deploy.

## What this session changed

- Replaced the public README's long chronological status lead with a
  ten-minute-reviewer path: question, prominent demo, implemented behavior,
  accepted method and architecture, verified results and limitations, one
  screenshot, practical setup/reproduction boundaries, evidence links, and a
  short current-status section.
- Added one 1422 × 904 screenshot captured read-only from the existing public
  deployment after all map layers loaded. Its caption identifies the current
  deployed build, capture date, results-as-of date, mixed source vintages, and
  the not-yet-deployed M7 wording correction.
- Corrected current-owner documentation that still described exposure delivery
  as local-only or unfinished: architecture, development setup, source register,
  data policy, ADR 0021 status/index, and the browser-key example. Dated run
  records remain history.
- Recorded a fresh current-source check for the publisher-hosted VSR layer and
  resolved the source register's earlier unverified AIS FAQ revision report.
- Reviewed tracked contents for dead files and unused scaffolding. No small,
  clearly obsolete tracked file was found, so nothing was deleted. The three
  `.gitkeep` files preserve the documented ignored-data layout; historical
  handoffs and diagnostics remain retained evidence; loading placeholders and
  failure paths are active implementation, not scaffolding.

No analytical result, application implementation, test, raw or derived data,
ignored evidence, release/rollback package, cache, worktree, branch, or backup
was changed or removed.

## Screenshot identity and source-use review

| Field | Value |
|---|---|
| Repository path | `docs/assets/exposure-results-overview-2026-09-11.png` |
| SHA-256 | `fae1629e6c459826c66ded64b5c467c6f1d0400d30bedeaf9dd47f74bc132a95` |
| Dimensions / size | 1422 × 904 pixels / 875,440 bytes / 24-bit RGB PNG |
| Source | Existing public application at `https://socal-whale-vessel-overlap.vercel.app/` |
| Build shown | Current deployed package, application commit `3dfedc1faab1dd830a79ab5fa0efce3b07c9db25` |
| Capture | 2026-09-11, loaded desktop exposure/results overview |
| Results as of | Generated 2026-09-07; accepted July–November 2024 AIS, NOAA/SWFSC 2020b multi-year summer–fall whale model, and 2026 VSR context |

The image was visually inspected at original resolution. It shows the primary
map, both distinct primary headline shares, the materially different
log-traffic result, loaded-layer state, VSR outline, and visible Esri/data
attribution. It contains no credential, account interface, local path, or
unrelated personal information. Alt text and a caption carry the analytical
meaning, build/date identity, and correction caveat.

This is an application screenshot of the publisher-hosted `FID = 126`, not an
export or render of the local analytical snapshot. No VSR feature bytes,
project-hosted copy, clipped/simplified geometry, or derived VSR image was added.
The screenshot retains the application's Danielle Alvarez/CMSF/BWBS disclosure
path and visible dynamic Esri/data attribution. That follows ADR 0019's direct-
service/no-copy route and the application's existing attribution controls; it
does not claim a redistribution licence for the underlying geometry.

The first automatic capture occurred before the asynchronous project layers had
loaded and was discarded. The selected capture was taken only after the page
reported the exposure, whale, vessel, domain, and VSR layers loaded. No generated
or AI-created analytical map was used.

## Verified headline claims used in the README

All numbers below come from the tracked
`results/exposure-results.v1.json`, results ID
`exposure-results-8a0bf6c27e00fb40a13d6870`, SHA-256
`ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60`.
The M6/M7/M8 evidence owns their analytical reconciliation and reproduction.

| Result | Inside | Outside | Meaning |
|---|---:|---:|---|
| 5 km product integrated relative exposure | 92.2% | 7.8% | Integrated proxy share across exact receiver-qualified water |
| 5 km product all-valid p90 high-exposure water area | 98.5% | 1.5% | Area share of the selected 6,473.8 km², not exposure share |
| 5 km log-traffic integrated sensitivity | 74.9% | 25.1% | Materially different formula; inside change is −17.2741 percentage points, not a confidence interval |

The README separately identifies modeled density rather than observed whales;
the 2024 traffic, multi-year whale model, and 2026 VSR vintages; integrated
exposure versus selected-area shares; the receiver-qualified domain rather than
empirical coverage; and relative overlap rather than collision probability,
causal VSR effectiveness, or a policy recommendation.

## M9 criteria status

| Criterion | Status at this handoff | Remaining gate |
|---|---|---|
| Stable public application works in a clean browser | **Existing build evidenced; final release open.** The current HTTPS application loaded anonymously for the screenshot. Retained 2026-09-09 receipt/browser checks and the later whole-connection check passed. | Repeat the complete required matrix against the newly authorized deployment from merged `main`, including the corrected M7 wording. |
| README communicates question, method, result, and limitations | **Prepared, not final.** The branch README does so without requiring another document for first-pass interpretation. | Independent audit, PR review, merge, and post-deployment screenshot review. |
| Every documentation link resolves | **Prepared.** Repository-wide relative file/heading checks pass after this handoff is present; 19 important public/source/release URLs returned HTTP 200. | Repeat on the final PR head and recheck links that can change before release. |
| Repository claims only implemented capabilities | **Prepared, pending independent audit.** Current-owner stale statements found in architecture, development, data, and ADR summaries were corrected; historical records remain labelled by date/context. | Independent audit and both CI jobs on the exact PR head. |
| Version 1 scope is satisfied or explicitly reduced | **Not yet releasable.** M1–M6 and M8 are complete. The documented M7 wording correction still requires public release verification; M9 release gates remain. | Complete the sequence below, then make the owner-controlled closure decision. |
| Displayed VSR matches the analytical snapshot | **Current readiness check passed; final release check open.** The 2026-09-11 anonymous item/layer/`FID = 126` and zero-tolerance comparison matched the ignored snapshot. | Repeat immediately for the fresh merged-main candidate and again as required around deployment. A mismatch blocks release. |

M9 therefore remains **In progress**. Version 1 is not declared complete by this
handoff.

## Checks performed

- Fetched and pruned origin. PR #37 was `MERGED` at
  `ecd81d0097caa2f61449327ed34329099b08b12d`, which was also current
  `origin/main` when this worktree was created.
- Read the project brief, complete M7–M9 roadmap context, publication/secrets/
  release/testing/PR rules, architecture and component contracts, source/data
  policies, ADRs 0019 and 0021, and the current M7/M8 handoffs.
- Compared every README numerical statement with the generated results artifact
  and accepted M6/M7/M8 evidence; no new calculation or analytical choice was
  introduced.
- Verified the current public `release.json`: schema 2, application commit
  `3dfedc1faab1dd830a79ab5fa0efce3b07c9db25`, keyed `arcgis/oceans`, and 901
  self-inventoried public files. This read-only check is not a fresh receipt or
  full browser matrix.
- Anonymous VSR readiness check returned HTTP 200 for ArcGIS item
  `b400c7f418b04dc5a9d7ce5015adae32`, Feature Layer 0, and exactly one
  `FID = 126`. Item title/owner/modified time remained
  `WhaleAtlas_2026` / `danielle_cmsf` / `2026-06-01T19:24:22Z`; layer version
  remained 12 with `Query`. The exact ignored snapshot retained SHA-256
  `2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783`.
  In-memory zero-tolerance geometry, coordinate, and sorted-property comparison
  passed; the known geometry and coordinate hashes remained
  `bf50488078ed558029d1ead6676b4f4d33e5ed20b2e560b4dc564f8e5615f196`
  and `24c486e3f05e8e15a855ba98845893597edf6c25c64c56d396e6b8af09da2693`.
  No remote or local geometry was written.
- Downloaded the current NOAA Marine Cadastre AIS FAQ to a temporary path. It
  identified itself as May 2026 and exactly matched the retained file: 506,349
  bytes and SHA-256
  `1dcd64e439618d482878435d6c5ce0bcbf0791f99006a3974dd0757b467691c3`.
  The prior unmerged June-revision report was not reproduced.
- Important links checked with anonymous HTTP and returned 200: the public app;
  NOAA whale-model, InPort and AIS pages/FAQ; BWBS and California OPC context;
  ArcGIS item/layer/query endpoints; Vercel Hobby, limits, Build Output API and
  prebuilt-deploy documentation; and Esri licensing, billing, pricing, sharing,
  and API-key documentation.
- Reviewed the complete tracked-path inventory, zero-byte tracked placeholders,
  and stale/scaffold markers. No safe deletion was identified. Reviewed the
  current GitHub repository description, topics, homepage, visibility, and
  detected licence.
- Inspected the screenshot visually and checked its dimensions, pixel format,
  byte size, and SHA-256.
- Reviewed the scoped diff, whitespace, relative file/heading links, and
  credential/data boundaries before commit. No dependency was installed and no
  Python/web suite or analytical processing was run, as required for this
  documentation/assets-only change. Both PR CI jobs remain mandatory.

Initial screenshot timing produced one incomplete loading-state image; it was
discarded and is not tracked. No documentation/link/source check remains failed.
The final release gates below remain intentionally unperformed.

## Exact author decisions and repository metadata

Current GitHub state is public visibility, no homepage, no topics, description:

> An ArcGIS-based spatial analysis examining how California's Vessel Speed
> Reduction zones align with blue-whale habitat and large commercial vessel
> activity off Southern California.

Current detected project licence is **none**. This session made no GitHub setting
or licence change. Proposed exact metadata for author approval:

- **Description:** `Reproducible GIS analysis and interactive map of modeled blue-whale habitat, 2024 commercial vessel activity, and relative exposure inside/outside Southern California's 2026 VSR zone.`
- **Homepage:** `https://socal-whale-vessel-overlap.vercel.app/`
- **Topics:** `gis`, `spatial-analysis`, `arcgis`, `qgis`, `python`, `nextjs`,
  `ais`, `marine-conservation`, `data-visualization`
- **Licence:** leave GitHub's detected licence unset unless the author separately
  chooses and approves a project-code/documentation licence after considering
  ownership and third-party terms. The README now states the current no-licence
  posture; this branch does not select one or alter source-data/service terms.

The remaining author actions are: approve or revise those metadata values;
decide whether the present no-licence posture remains intentional; authorize any
push/PR actions; and, only after the audited merged-main candidate packet exists,
provide a separate explicit approval for that exact deployment. No scientific
choice remains for this documentation branch.

## Required release sequence using existing tooling

1. Independently audit this exact branch and its screenshot. Address findings in
   new commits. After author authorization, push and open a PR to `main`; require
   both `analysis` and `web` CI jobs on the current PR head. Merge only through
   the protected GitHub workflow after review.
2. Fetch the resulting `origin/main` and use a fresh clean dedicated checkout.
   Rehash the eight pinned public layer/manifest artifacts and the tracked
   build-only results input against `web/scripts/release-inputs.json`; do not
   regenerate AIS or exposure merely for deployment.
3. Recheck the selected free-only route: Vercel Hobby personal/non-commercial
   eligibility and capacity, ArcGIS Location Platform pay-as-you-go disabled,
   available basemap allowance, and the browser key's basemap-only privilege,
   validity/expiry, and exact localhost/production referrers. Do not enable a
   paid plan, trial, add-on, pay-as-you-go, Git integration, or new project.
4. Privately set `NEXT_PUBLIC_ARCGIS_API_KEY` in the invoking process and run the
   existing production staging command from `web/`:

   ```text
   node scripts/stage-release.mjs <fresh-release-name> <retained-layer-directory>
   ```

   It must run the locked clean web gate, build from merged `main`, and create a
   new ignored content-addressed Build Output API package and receipt. Do not use
   `--rehearsal` as a deployable candidate.
5. Verify exact package/read-back identity with the existing command:

   ```text
   node scripts/stage-release.mjs --verify <fresh-release-name> <receipt-sha256>
   ```

   Record the main commit, receipt, 903-package-file expectation or its truthful
   current replacement, all eight public inputs, build-only results identity,
   static-only inventory, absence of a public results endpoint and VSR copy, and
   the preserved rollback package.
6. Run the keyed local three-viewport browser matrix against that exact package.
   Verify five layers once each, exact counts and ordering, product/log switching,
   results strings, source dates, responsive/keyboard behavior, attribution,
   isolated failures, and the corrected M7 review/acceptance sentence.
7. Anonymously verify the current ArcGIS item, layer, and exactly one `FID = 126`;
   compare complete properties and geometry with the immutable snapshot at zero
   tolerance. Record source/version/check date without retaining remote geometry.
   Any mismatch blocks release until analysis/display are reconciled or the
   mismatched remote boundary is omitted under ADR 0019.
8. Present the exact source commit, receipt, artifact identities, browser/VSR
   outcomes, actual free-only account/key conditions, intended existing
   `stemry/socal-whale-vessel-overlap` project and stable origin, rollback
   package, source-use posture, and requested action. Obtain a **separate explicit
   author approval** for that exact upload.
9. After approval and private Vercel CLI authentication, link only the approved
   candidate's `deploy/` directory to the existing project, re-run receipt
   verification immediately before upload, and use the existing command from
   that directory:

   ```text
   vercel deploy --prebuilt --prod
   ```

   Upload only `.vercel/output`; do not enable GitHub/Vercel integration or
   deploy source, the checkout, private build inputs, evidence, or credentials.
10. At the stable public origin, verify the exact deployment/alias and complete
    receipt bytes; media, compression, immutable/no-store/freshness headers;
    anonymous clean-browser behavior at all three viewports; Oceans and visible
    attribution; all five layer identities/counts/order; product/log results and
    limitations; keyboard/focus/scrolling; isolated failures; whole-connection
    usability; publisher VSR identity and snapshot consistency; and the corrected
    M7 wording. Retain only sanitized evidence.
11. Recheck the README screenshot against the final deployed UI and replace it
    only if the release materially changes what it communicates. Preserve its
    build/capture/results dates and attribution. Apply approved repository
    metadata separately; do not imply metadata changes came from deployment.
12. Record the exact release and public evidence in the owning documents. Close
    M7 only when its corrected public wording passes. Close M9 and declare
    Version 1 released only when every M9 criterion and remaining Version 1 scope
    item passes. Preserve all prior release and rollback packages.

## PR readiness

The change is documentation and one inspected image only. It is ready for
independent audit after the final commit/diff/clean-tree checks. It is not ready
to push, merge, stage a production candidate, or deploy without the separate
author actions above. Both CI jobs are still required on the eventual PR head.
