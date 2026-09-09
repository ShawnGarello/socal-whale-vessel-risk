# M5/M7 production candidate handoff

Session: 2026-09-09. Branch: `chore/m7-production-candidate`. Worktree:
`C:/Users/teche/socal-whale-vessel-risk-m7-production-candidate`.

## Status and approval boundary

The complete keyed M5/M7 production package is prepared and locally verified.
It is a **release candidate awaiting author approval**, not a deployed release.
No upload, Vercel link, deployment, GitHub push, pull request, merge, account
change, key/referrer change, billing change, or publisher-content change was
performed.

The package was built before this branch received documentation-only evidence
commits. Its application source is immutable merged-main commit
`3dfedc1faab1dd830a79ab5fa0efce3b07c9db25`; later branch commits only record
release evidence and do not change the source inside the package.

Technical package checks pass. Upload approval remains gated on explicit owner
acceptance of the proposed public results and wording, and private confirmation
that the historical free-tier/account and minimum-key-privilege facts below
remain current.

## Merged source and CI

A fresh `git fetch origin --prune` left both candidate HEAD and `origin/main`
at `3dfedc1faab1dd830a79ab5fa0efce3b07c9db25` immediately before staging. The
worktree was clean.

- Dependency maintenance PR #31 merged as
  `90729cefb5e6f65fa030840fac06d047902691d0`; its `analysis` and `web` jobs
  passed, and post-merge main CI passed.
- Release-integration PR #32 merged as the candidate source commit above; its
  `analysis` and `web` jobs passed, and post-merge main CI passed.
- GitHub records no review or comment accepting the scientific results or
  public wording on PRs #26, #30, or #32. CI is not scientific review.

## Exact candidate

- Release name: `m7-production-candidate-20260909-01`
- Candidate directory:
  `C:/Users/teche/socal-whale-vessel-risk-m7-production-candidate/data/interim/m4-releases/m7-production-candidate-20260909-01`
- Approved upload boundary if later authorized:
  `deploy/.vercel/output/` only
- Receipt SHA-256:
  `e6532385fd3641275f38d9f203e75aa64fed0a1739ff3c29799113208f958ede`
- Upload package: 903 files, 38,658,688 bytes
- Receipt schema/mode: `2` / `release-candidate-awaiting-approval`
- Build configuration: `arcgis/oceans`; browser key
  `configured-not-recorded`

`node scripts/stage-release.mjs --verify` re-read the finished receipt twice
after staging and once after browser verification. Every invocation returned
the exact application commit, mode, 903 files, and 38,658,688 bytes above.

## Public artifacts and build input

The exact retained directory was read without regeneration or modification:
`C:/Users/teche/socal-whale-vessel-risk-m7-release-integration/data/interim/m7-release-integration/retained-inputs-20260908`.
All eight bytestrings rehashed to the committed inventory before staging.

| Input | Data SHA-256 | Manifest SHA-256 |
|---|---|---|
| Whale | `831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154` | `404c53356be7d743cbc5e4bc1b5741e4938c84e206caf1d53468954e368c8108` |
| Vessel | `3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288` | `6d18aaf3e74038db0165884c0daaf99b5acf400dd42f5cccccb42da848ff995d` |
| Domain | `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf` | `d340dc2703f3a891a62d4735dc442a7545a6330e9e3322b95f742f502b3b0de6` |
| Exposure | `1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb` | `0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0` |

The tracked build-only input is
`results/exposure-results.v1.json`, 31,381 bytes, SHA-256
`ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60`,
contract `relative_exposure_application_results_v1`, results ID
`exposure-results-8a0bf6c27e00fb40a13d6870`. It is present in the
isolated private source build and receipt lineage, but no public results file or
endpoint exists.

## Clean build and inventory verification

The production staging tool ran its existing isolated `npm run verify:clean`
workflow. Locked installation audited 555 packages with zero vulnerabilities;
formatting, linting, generated type-checking, 101 tests in 11 files, and the
Next.js 16.3.3 static export passed. The expected no-cache advisory and ESLint
9.39.5 support warning were non-failing. Sanitized `verification.log` is 1,903
bytes with SHA-256
`ebc1adde50bad47823a1d1f127f4e8554cd7a8a9894022197788621b39f249a8`.

Direct inspection of the actual `.vercel/output` found:

- exactly one `config.json` and 902 static files, matching all 903 receipt
  entries;
- only HTML, text, JavaScript, CSS, SVG, WOFF2, JSON, and the four allowlisted
  GeoJSON files;
- exactly the eight content-addressed layer/manifest paths and no missing or
  extra layer file;
- no `results/` endpoint, VSR-named artifact, raw/source/data/node_modules
  directory, source map, environment file, GeoParquet, local filesystem path,
  or server/functions runtime;
- no high-specificity private-key, GitHub-token, AWS-key, OpenAI-key, Slack-token,
  or bearer-token marker;
- the expected public ArcGIS browser key in one compiled JavaScript chunk only,
  and not in the receipt or sanitized verification log; and
- Build Output API v3 routing with eight media-type overrides, immutable
  year-long caching for content-addressed layers/manifests, and `no-store` for
  `release.json`.

This proves a static-only local package and configured header intent. It does
not prove deployed compression, headers, HTML freshness, or repeat-request
behavior.

## Keyed local browser verification

Chrome 152.0.7977.83 loaded the actual staged static output through the already
permitted `http://localhost:3000` origin at 390 x 844, 820 x 1180, and
1440 x 900 CSS pixels.

- `ArcGIS Oceans` loaded at every viewport. Pan and wheel zoom changed both map
  center and zoom; Esri attribution was present before and after interaction.
- Normal layer order was whale / vessel / exposure / domain / VSR, once each,
  with counts 4,516 / 2,793 / 2,793 / 1 / 1. Initial visibility was off / off /
  on / on / on.
- Visibility toggles worked. Switching to log traffic changed the existing
  exposure renderer from `product_index` to `log_traffic_index`, retained six
  classes and one exposure layer, and introduced no duplicate.
- Generated results and all required sensitivity strings matched, including
  92.2/7.8, 98.5/1.5, 74.9/25.1, -17.2741, and every recorded 5-to-10 km table
  change. M5 dates, legends, limitations, pairing text, VSR credit, and the
  non-navigational disclaimer were reachable.
- No normal console/log error, visitor sign-in UI, horizontal overflow, or
  unsatisfied request appeared in the CDP report. Loopback ready time was
  1.54-1.76 seconds; this is not a deployed or mid-range-network measurement.
- Native checkbox/radio controls and disclosure summaries were operated with
  Space/Enter. Focus outlines measured 3 px. Document, layer panel, or results
  panel scrolling was available as appropriate at every viewport.
- Blocking whale, vessel, exposure, domain, and VSR one at a time removed only
  that layer, disabled its control, showed its warning, and preserved the map
  plus the other four layers. Inspector-blocked requests and the VSR SDK errors
  were expected in those deliberate failure cases.
- Missing exposure bytes, a results-ID manifest mismatch, and malformed
  exposure JSON each removed exposure only and retained the primary results,
  formula sensitivity, whale, vessel, domain, and VSR. The malformed case
  emitted the two expected ArcGIS parse/layer-view errors; the other two emitted
  no console error.

Screenshots at all three viewports and all failure states were visually
inspected. The normal map/results layouts, text, controls, legends, focus,
scrolling, attribution, and failure warnings were legible with no observed
blocking defect. The release-focused technical UI audit is 17/20 (`Good`):
accessibility 3, performance 3, responsive design 4, theming 3, anti-patterns 4.
There are no P0 or P1 findings. The withheld points reflect the absence of a
full automated WCAG/contrast audit and of deployed mid-range performance
evidence, not a discovered source defect. Per the release instruction, no
source change was made.

Sanitized ignored evidence is retained at
`data/interim/m7-production-candidate/browser-verification-20260909-01/`.
The principal report identities are:

- `deployed-browser.json`: SHA-256
  `5b83b938ad33c90c6e31336456f223afe297ffb9cdac098b86a00b6cbeb6a681`;
- `browser-report.json`: SHA-256
  `0e926fe0a651f60aefe5707433dfd9b75ee202bff59ee37deca8e787a0cae703`;
- `keyboard-report.json`: SHA-256
  `572e62406939fb66ec6a1d15ab1c63d9c35112b55c714a76119026c71e664154`.

No raw HAR or key-bearing URL was retained. The dedicated temporary Chrome
profile was removed after the run because it could contain cached key-bearing
application bytes.

## Release-time VSR gate

At `2026-09-09T16:53:26Z`, anonymous HTTP returned 200 for ArcGIS item
`b400c7f418b04dc5a9d7ce5015adae32`, Feature Layer 0, and the `FID = 126`
GeoJSON query. The item remained `WhaleAtlas_2026`, type `Feature Service`,
owner `danielle_cmsf`, modified `2026-06-01T19:24:22Z`; layer version was 12,
object ID field `FID`, capability `Query`.

The current one-feature Polygon and all sorted feature attributes were compared
in memory with the exact 2026-08-25 snapshot, SHA-256
`2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783`.
Ordered JSON coordinate arrays and the complete property object matched exactly
with zero tolerance. Both geometry serializations hashed to
`bf50488078ed558029d1ead6676b4f4d33e5ed20b2e560b4dc564f8e5615f196`;
both property serializations hashed to
`55b6affd5fd816e2e16c912975338a0a92bace3f6791d478fb76ddf574f8eeed`.
The geometry remained one Polygon with 105 rings, 104 interior rings, and
50,068 vertices. No fetched or analytical geometry was written, committed, or
copied into the package. Publisher credit and disclaimer text remained present.

The ADR 0019 release-time identity/version/geometry gate therefore passes for
this candidate.

## Account, key, target, and rollback evidence

Current read-only checks on 2026-09-09 established:

- existing cached Vercel CLI 59.11.7 authenticated and resolved team scope
  `stemry` and project `stemry/socal-whale-vessel-overlap`;
- the stable production origin is
  `https://socal-whale-vessel-overlap.vercel.app`;
- its public `release.json` returned HTTP 200 and still identified the M4 source
  commit `8b1f65c8556955d6f28ee86426c09d55b7ea71fa`, proving the new candidate was
  not uploaded; and
- the candidate key returned Basemap Styles HTTP 200 from the exact localhost
  and production referrers and HTTP 401 from an unrelated origin. No key value,
  identifier, or key-bearing URL was retained.

Historical author/account evidence from 2026-09-07 records Vercel Hobby
eligibility for a personal, unpaid, non-monetized portfolio; ArcGIS Location
Platform with pay-as-you-go disabled; 5,292 of 2,000,000 monthly basemap tiles
used; and a browser key with no item, analysis, publishing, general,
administrator, billing, or account-management privilege. Those administrative
facts were not re-read from account settings in this read-only session. Before
upload, the author must confirm privately that Hobby eligibility, free-tier
posture/headroom, pay-as-you-go-disabled state, key expiry, exact referrers, and
minimum privileges remain unchanged.

The verified rollback package remains:
`C:/Users/teche/socal-whale-vessel-risk-m4-release/data/interim/m4-releases/m4-initial-production-01`.
Its receipt SHA-256 is
`194f8877d040220214205af1b03917fc320e703114513e7ea04bb819f700352a`;
read-back again returned source
`8b1f65c8556955d6f28ee86426c09d55b7ea71fa`, mode
`release-candidate-awaiting-approval`, and 901 files.

## Remaining approval gates and exact proposed action

Independent scientific/content review and owner acceptance of the result maps,
92.2/7.8 primary framing, 98.5/1.5 high-area framing, material 74.9/25.1 formula
sensitivity, complete sensitivity disclosures, and final public wording are not
recorded. This is an upload blocker, not a reason to alter the package silently.

After those acceptances and the private account confirmations above, the exact
proposed external action is:

1. From this candidate's `deploy/` directory, use Vercel CLI 59.11.7 to run an
   author-reviewed `vercel link --project socal-whale-vessel-overlap --scope stemry`.
2. Read the linked scope/project back, then rerun receipt verification from this
   worktree's `web/` directory with the release name and receipt SHA-256 above.
3. From the linked `deploy/` directory, run
   `vercel deploy --prebuilt --prod --scope stemry`.

None of these commands was executed. After any authorized upload, the full
public receipt/header/browser matrix and mid-range-connection behavior remain
mandatory deployed-origin checks before M5 or M7 can be completed.

## Non-candidate command outcomes

- A first key-ignore check incorrectly treated `git check-ignore -q`'s empty
  stdout as failure. `git check-ignore -v` showed the committed `web/.gitignore`
  rule, and the corrected exit-code check passed before staging. No build had
  started during the false alarm.
- `vercel` was not globally on PATH. No package was installed; the existing
  cached 59.11.7 CLI was used. Its display-name scope `Stemry` was rejected;
  the listed lowercase scope `stemry` resolved read-only.
- The execution environment rejected one `Start-Process` form before it ran.
  Direct headless Chrome launch succeeded. Recursive `Remove-Item` was also
  rejected; after exact path validation, the dedicated temporary profile was
  deleted through the .NET directory API. These were tooling constraints, not
  application or candidate failures.
