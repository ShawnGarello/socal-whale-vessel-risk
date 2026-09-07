# M4 release staging handoff

Session: 2026-09-07. Branch: `feat/m4-release-staging`. Worktree:
`C:/Users/teche/socal-whale-vessel-risk-m4-release`.
Implementation commit: `4f9b2c24cf2819afb6e636931d4c9c58e78c77ae`.
Correction/evidence commit: `5c9d58d16661cde6029121cbe2a5f8122c04df00`.
It changes ignore rules and documentation only. The audit documentation commit
records the completed independent audit; `git log --oneline origin/main..HEAD`
lists the complete branch history, including the later ADR acceptance update.

This is execution evidence and navigation. Roadmap owns M4 status; development
owns the procedure; accepted ADR 0021 owns the static delivery decision and its
route-specific capability checks.

## Initial deployment setup continuation

Session: 2026-09-07. Branch: `chore/m4-initial-vercel-setup`. The clean M4
worktree was reused and the branch was created from freshly fetched
`origin/main` commit `8b1f65c8556955d6f28ee86426c09d55b7ea71fa`, the merge of PR #27.

- Authenticated Vercel CLI 59.11.7 confirmed the `Stemry` scope and found only
  the existing `stemry-waitlist` project. The separately authorized
  `socal-whale-vessel-overlap` project was created without Git integration or a
  deployment. Its verified reserved production hostname is
  `https://socal-whale-vessel-overlap.vercel.app`. The existing project was not
  changed.
- The author confirmed Vercel Hobby eligibility for this personal, unpaid,
  non-monetized portfolio and ArcGIS Location Platform with pay-as-you-go
  disabled. Current use was 5,292 of 2,000,000 monthly basemap tiles. The
  replacement key has no item access and no analysis, general or administrator
  privilege. It allowed Basemap Styles from the exact localhost and production
  referrers, refused an unrelated origin, and refused Static Basemap Tiles. No
  credential value, credential identifier or key-bearing URL was retained.
- `m4-initial-production-01` is a fresh keyed candidate from that exact merged
  main commit and the same six pins in `web/scripts/release-inputs.json`. Its
  isolated locked build passed formatting, linting, generated-type checking,
  all 79 tests and Next.js 16.3.3 static export. The upload contains 901 files,
  36,021,531 bytes, and has receipt SHA-256
  `194f8877d040220214205af1b03917fc320e703114513e7ea04bb819f700352a`.
  Receipt read-back passed before and after linking.
- Only the ignored candidate directory
  `data/interim/m4-releases/m4-initial-production-01/deploy/` is linked to the
  new project. CLI-created project/OIDC metadata is outside `.vercel/output`
  and outside the receipt. At the setup checkpoint no upload command had run.

## Initial production deployment

The author explicitly approved exact release `m4-initial-production-01`, receipt
SHA-256 `194f8877d040220214205af1b03917fc320e703114513e7ea04bb819f700352a`,
for the proposed prebuilt production upload. Immediately before upload, receipt
read-back, the linked `Stemry/socal-whale-vessel-overlap` target and fresh
`origin/main` commit `8b1f65c8556955d6f28ee86426c09d55b7ea71fa` all matched. Vercel CLI
59.11.7 accepted the package and reported the stable production origin Ready:

`https://socal-whale-vessel-overlap.vercel.app`

The isolated project remains disconnected from GitHub. The existing
`stemry-waitlist` project remained separate and unchanged. No paid Vercel or
ArcGIS feature was enabled and no account or key setting changed during upload
or verification.

Sanitized ignored evidence under the release's `verification/` directory records
clean Chrome 152.0.7977.76 checks at 390 x 844, 820 x 1180 and 1440 x 900. The
Oceans basemap, pan/zoom, attribution handoff, all four layer lifecycles, counts
4,516 / 2,793 / 1, toggles, legends, disclosures, VSR credit/disclaimer and a
desktop popup passed without sign-in or horizontal overflow. Normal contexts had
no console warnings or errors. Separate blocked whale, vessel, domain and VSR
requests each removed only that layer while preserving the other layers and map.
Anonymous HTTP reverified the expected public item, Feature Layer 0 and exactly
`FID = 126` without requesting geometry. Project-layer transfer, decoded hashes,
headers and repeat behavior were recorded without key-bearing URLs or raw HAR.

The six pinned inputs, deployed release identity and 899 of 900 public receipt
files matched byte-for-byte. The sole exception is a generated Turbopack runtime
chunk: its first 9,689 bytes exactly equal the staged file, after which Vercel
appended a 439-byte cookie-gated Toolbar loader. The public response is therefore
10,128 bytes and does not match the approved receipt hash. The loader is inactive
without a Vercel Toolbar cookie, but the documented whole-receipt criterion is
strict. No project setting was changed. M4 remains in progress pending author
direction and an exact recheck after any authorized resolution.

## Completed preparation

- Fetched origin; clean local main matched `origin/main` at
  `c8bf3977b4a43f7b2e691e87011bdda34300fbf7`. Inspected existing M4 branches:
  deployment-capability-verification and deployment-verification were 129 and
  154 commits behind main, with no unique commits. Existing delivery-assessment
  and keyed-map worktrees were clean and historical. Created this dedicated
  branch from current origin/main. Source-data worktrees were checked clean
  before inspecting their retained files.
- Rehashed the three GeoJSON inputs and their sanitized generation manifests.
  All six exact identities are pinned in `web/scripts/release-inputs.json`.
  Read the manifests and retained spatial/browser evidence. The whale full-view
  PNG matches `60832bbe847e4d2243c494938cebfb42a6d777000e586984849ae6e823790176`.
  The vessel/domain inspection and browser reports match
  `2cfca5ca98e5de69b5feead7db6e5d8b9e3d276a6076f1a9c55e43bdce55a140` and
  `8e9e1395539ccb0d2cdf18dedbb815effb555bf915184abc4a1a3352ee45501a`.
  This was evidence read-back, not a fresh GIS inspection.
- Rechecked current provider documentation and source-use records. Anonymous
  HTTP confirmed the expected publisher VSR item/service and feature attributes.
  No geometry was requested or compared. No account, credential settings,
  service, GitHub integration or public deployment was created or changed.
- Implemented isolated committed-source staging, six-file input allowlisting,
  checksum-addressed layer URLs, public release identity, full upload receipt
  and receipt verification. Only the existing application is built. No AIS
  processing, M7 implementation or exposure integration occurred.

## Exact rehearsal and checks

From this worktree's `web/` directory:

```powershell
node scripts/stage-release.mjs --rehearsal m4-rehearsal-01 C:/Users/teche/socal-whale-vessel-risk-vessel-domain-display/web/public/layers
node scripts/stage-release.mjs --verify m4-rehearsal-01 7cf829418f808bd1092547ebe0e2790eec5220616cc1e4ee353d518d5ef0d815
```

Both completed successfully. Retained beneath this worktree's ignored
`data/interim/m4-releases/m4-rehearsal-01/`:

| Artifact                                    | Identity or purpose                                                                                                                    |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `receipt.json`                              | SHA-256 `7cf829418f808bd1092547ebe0e2790eec5220616cc1e4ee353d518d5ef0d815`                                                             |
| `deploy/.vercel/output/`                    | 901 files, 36,021,239 bytes, exact inventory in receipt                                                                                |
| `deploy/.vercel/output/static/release.json` | Application commit `4f9b2c24cf2819afb6e636931d4c9c58e78c77ae`; static-file inventory                                                   |
| `verification.log`                          | Locked install, type generation, Prettier, ESLint, TypeScript, 79 passing tests in eight files, successful Next.js 16.3.3 static build |
| `source/`                                   | Isolated committed source, installed dependencies and build output; never upload                                                       |

The package mode is `keyless-rehearsal-not-for-deployment`. It contains no
release key. All three configured `/layers/<sha256>.geojson` URLs are present
in the compiled JavaScript. The exposure-results contract is absent from it.
The six public input bytes match their pins in the completed export. No source
or environment files or VSR geometry are in the upload inventory.

Node was 22.16.0, npm 10.9.2. Locked installation reported zero vulnerabilities.
The package follows documented Vercel Build Output API v3 structure, but Vercel
has not accepted or served it. Compression, caching, stable HTTPS origin,
deployed map rendering and fresh visitor access remain unverified.

## Failures, audit and corrections

- Initial focused Vitest invocation found no tests because its explicit include
  covered only `lib/`. Added `scripts/**/*.test.mjs`; four safeguard tests then
  passed, and the isolated complete suite passed all 79 tests.
- General data ignore rules re-included the copied source `README.md`. Added
  explicit `/data/interim/m4-releases/` ignore and verified it with
  `git check-ignore`; all generated releases remain outside Git.
- Local dependency installation emitted an optional-package Windows cleanup
  warning but exited successfully. The isolated locked install succeeded.
  Both reported the existing ESLint deprecation warning; no dependency upgrade
  was made. The clean build reported the expected absent build cache.
- Initial file-reading commands used wrong relative paths, and one optional
  inline Node diagnostic lost quoting through Windows PowerShell. Corrected
  reads and a PowerShell diagnostic succeeded. These did not change data.
- Web browsing could not open the parameterized VSR REST URLs; direct anonymous
  PowerShell HTTP requests succeeded. Neither method used an account session.
- Independent read-only audit of `c8bf397..4f9b2c2` verified the six input hashes
  and found the ignore gap and old test-count text. Both are corrected. No
  further blocking finding was reported. No duplicate full build was requested.
- Final independent audit passed exact head `5c9d58d` with no unresolved blocking
  finding. The auditor re-ran receipt verification and confirmed the 901 files,
  36,021,239 bytes, retained web-gate log, ignore correction and clean tree.
  The web source is unchanged since the rehearsal commit. Final fetch still
  found local main equal to origin/main. Relative documentation file links and
  `git diff --check` passed.

No Python code changed and no analytical run was required. Both `analysis` and
`web` CI jobs remain mandatory on a future PR head before an authorized merge.

## Remaining work

M4 is **in progress, not complete**. The approved upload and documented browser
checks ran, but the one platform-appended runtime response prevents strict
whole-receipt acceptance. Nothing was pushed or merged.

1. Obtain author direction before changing any new-project Toolbar setting or
   preparing a reviewed correction. Do not alter the existing Stemry project.
2. After an authorized resolution, repeat the full receipt and clean-browser
   checks at the stable origin. Mark M4 complete only if every applicable
   criterion passes.
3. Keep the final-results VSR geometry snapshot comparison separately open; the
   initial application has no exposure statistics.

The key permits only the approved exact localhost/production origins, with no
item, publishing or account rights and no wildcard.
Current source-use interpretation remains the one in the source register:
attributed NOAA derivatives and direct publisher VSR access with no copied
geometry; neither public service access nor a staged candidate grants
redistribution permission. Keep prior verified release packages for the documented re-upload
rollback; this initial rehearsal has no previous public release to restore.

Next scoped M5 step: add the missing retrieval/processing dates to the vessel
and domain source disclosures, then verify the existing input layers against
the approved deployed route. Do not start M7 or alter analytical methods.
