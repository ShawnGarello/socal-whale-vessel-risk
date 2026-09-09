# M7 exposure interface handoff

Current as of 2026-09-08. This is the owning handoff for the local M7 exposure
interface slice. It records implementation and verification, not deployment,
milestone completion, independent scientific audit, or author acceptance of a
final public headline.

The release-staging gap recorded here was implemented and locally verified on
2026-09-09. Current release evidence and remaining gates are in the
[M7 release-integration handoff](m7-release-integration-handoff.md); the records
below remain historical evidence for the interface slice.

## Checkout, base, and scope

- Branch: `feat/m7-exposure-interface`
- Worktree:
  `C:\Users\teche\socal-whale-vessel-risk-m7-exposure-interface`
- Original base:
  `8b1f65c8556955d6f28ee86426c09d55b7ea71fa`
- Current base after the author-requested clean rebase onto `origin/main`:
  `c524dfc231e28a69f3c58dc39584327e6151d70d`
- Initial implementation commit:
  `d6920239f85e916df4501d80065ac0e627e425bb`
  (`feat: add verified exposure results interface`)
- Initial handoff commit:
  `585105ef4ff7bd49cf7b47a20888ac105686e43e`
  (`docs: record M7 exposure interface handoff`)
- Approval-correction commit:
  `5115ce3f846e9ab243175e33b1faa0dad37f8612`
  (`fix: harden exposure results disclosure`)
- Approval-evidence commit:
  `a89378d9993689d793dcc904c6fa91c7aa9c7c98`
  (`docs: update M7 approval evidence`)
- The current handoff update is committed separately in the commit containing
  this revision.
- No push, merge, deployment, account operation, or key/referrer change was
  performed. M7's owner status is now **In progress**, not complete.

The session inspected `origin/main` and all worktrees before creating this
worktree. The original checkout and the retained M6 worktree were clean. No
suitable unused M7 worktree existed. The branch was created from the then-current
`origin/main`; no work was performed on `main`. After M4 and M5 merged, the
author requested a rebase and owner-document integration. The branch rebased
without conflicts onto current `origin/main`; all inspected worktrees were clean
before that operation.

M5-owned vessel/domain modules, controls, focused tests, and shared input-layer
tests were not edited. M4-owned deployment files, accounts, packages, settings,
and release evidence were not edited. No shared utility, dependency,
configuration, shared panel style, release script, or existing M4/M5/M6 handoff
was changed. After their merges, the author-requested documentation pass updated
the owning shared documents listed below.

## Implemented behavior

The interface now consumes the committed M6 results through a deliberately
narrow static-build boundary:

- It reads `results/exposure-results.v1.json` during static generation, verifies
  the exact byte checksum, then validates the supported
  `relative_exposure_application_results_v1` schema version, identity, required
  scenarios, threshold families, comparisons, methods, null/exclusion fields,
  scope, sources, and limitations.
- An incompatible, changed, missing, or malformed results file produces an
  isolated **Results unavailable** panel. It does not fall back to hardcoded
  statistics and does not disable the independent map inputs.
- Results-file exceptions, including absolute missing/unreadable paths, are
  reported only to the static-build diagnostic channel. The rendered panel
  receives a fixed public message with no exception text or filesystem path.
- Display values come from the generated presentation strings. The view model
  does not derive or reformat the scientific percentages in the browser.
- Exact zero shares remain visible as generated zero strings. Null shares remain
  unavailable and are not converted to zero. Water outside the accepted domain
  is described as no analytical coverage, not zero exposure or low traffic.

The existing verified-GeoJSON lifecycle is reused unchanged for the analytical
surface:

- Before creating an ArcGIS layer, M7 fetches and validates the paired public
  manifest, its exact checksum when Web Crypto is available, its results
  identity/checksum binding, display checksum, display contract, geometry
  meaning, all-valid p90 definitions, and expected feature count.
- Pairing/checksum errors receive a distinct message. Missing or malformed
  display data receives a general isolated load message. In either case, the
  basemap, whale, vessel, domain, VSR, and generated results remain independently
  usable.
- The layer contains only the 2,793 receiver-qualified cells supplied by M6.
  No interpolation or values are introduced outside that geometry.
- The default renderer uses `product_index`. A visible radio choice switches the
  same layer to `log_traffic_index`; it does not add a duplicate layer.
- Six sequential classes include a distinct zero class. Product-index breaks are
  log-spaced to expose its skew; log-traffic breaks span its broader range. Copy
  explicitly distinguishes these display classes from the analytical all-valid
  p90 threshold.
- Default visibility is relative exposure on, analytical-domain and VSR outlines
  on, and whale/vessel fills off. Users can turn either input on. Layer order is
  whale, vessel, relative exposure, domain, then VSR, keeping both outlines above
  filled surfaces.
- The control exposes units, sources, method cautions, exact identities, loading
  state, a keyboard-visible focus indicator, and a checksum/pairing status.

The results panel makes the two headline measures visibly distinct:

- Primary 5 km proportional-product integrated relative exposure: **92.2%**
  inside and **7.8%** outside the VSR.
- Primary 5 km all-valid p90 high-exposure water area: **98.5%** inside and
  **1.5%** outside, using generated threshold **0.2286** and selected-water
  presentation **6473.8 km^2**.
- Required 5 km log-traffic sensitivity: **74.9%** inside and **25.1%** outside,
  with generated change **-17.2741** percentage points from the primary formula.
- P80/p90/p95 all-valid, positive-only, and complete 5 km-to-10 km grid
  sensitivities remain directly reachable in an expandable,
  keyboard-scrollable section. The grid table uses the generated presentation
  strings for both product and log-traffic integrated-share changes, integrated
  total changes, and p80/p90/p95 high-area inside-share changes.

The main copy consistently calls the output **Relative exposure** or modeled
whale–vessel overlap. It does not present collision zones, collision probability,
predicted strikes, VSR effectiveness, or an optimal boundary. The initial view
prominently states the modeled-habitat, non-contemporaneous input, receiver-domain,
uniform-within-water-cell, formula-dependence, excluded-area, and separate-speed
limitations. No outside-area cells are labeled as hotspot clusters or collision
locations.

The page retains the existing visual system. It uses a stacked map/results flow
below 1,024 px and a scrollable results column beside the map at desktop width.
The map remains first on smaller screens, with an explicit 32 rem viewport so it
does not collapse in the document flow.

## Exact consumed artifacts

No artifact was regenerated or hand-edited. The two ignored M6 display files were
copied byte-for-byte from
`C:\Users\teche\socal-whale-vessel-risk-exposure-results-delivery\web\public\layers`
into this worktree's ignored `web/public/layers/` directory. Originals were not
modified.

| Artifact                                                            |     Bytes | SHA-256                                                            |
| ------------------------------------------------------------------- | --------: | ------------------------------------------------------------------ |
| Tracked `results/exposure-results.v1.json`                          |    31,381 | `ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60` |
| Ignored `web/public/layers/relative-exposure.geojson`               | 2,542,744 | `1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb` |
| Ignored `web/public/layers/relative-exposure.geojson.manifest.json` |     6,803 | `0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0` |

The exact pairing is:

- Results contract/version:
  `relative_exposure_application_results_v1` / `1`
- Results ID: `exposure-results-8a0bf6c27e00fb40a13d6870`
- Display-manifest contract: `relative_exposure_display_manifest_v1`
- Display dataset contract: `relative_exposure_display_v1`
- Processing version: `1.0.0`
- Analytical run ID: `exposure-6dd927974fae959765c9b5c3`
- 5 km analytical source SHA-256:
  `a8e65b6d0019a24122f16feb7d847e5e5a31ce1670a2eaa9ebfbb64fe4835a29`
- 10 km analytical source SHA-256:
  `cff427ae54b3660389cc8abe7a547ea060ee39038b542b9ee819d00c53eaf194`
- Sensitivity report SHA-256:
  `520afde75f34a0293feef17376d44be12e9b96dcfe1b4dac9bee56747b0504ff`

The manifest records exact receiver-domain-qualified 5 km water geometry in
EPSG:4326, no simplification or densification, and no VSR geometry. Both ignored
files remain covered by `web/.gitignore`; no spatial artifact was staged or
committed.

For complete local browser composition only, the already retained ignored whale,
vessel, and domain display pairs were copied from the M5 worktree into the same
ignored staging directory. Their displayed GeoJSON checksums were respectively
`831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154`,
`3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288`,
and `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf`.

## Automated verification

From `web/`, committed dependencies were installed with Node 22.16.0 and npm
10.9.2. The required affected-component gates produced:

- Initial focused M7 run: 3 files, 10 tests passed.
- Approval-correction focused run: 1 file, 7 tests passed.
- Final full `npm test`: 11 files, 91 tests passed.
- `npm run typegen`: passed.
- `npm run typecheck:generated`: passed.
- `npm run format:check`: passed.
- `npm run lint`: passed.
- `NEXT_PUBLIC_ARCGIS_BASEMAP=topo-vector npm run build`: passed; `/` and
  `/_not-found` were statically generated.
- `git diff --check`: passed before the implementation commit.

The M7 tests cover supported contract/version/identity and required-field
rejection; exact generated-string selection; null, all-zero, exact-zero, and
excluded-area semantics; separation of integrated shares from high-area shares;
fixed public results-file errors for simulated missing and unreadable files while
retaining their path-bearing exceptions build-side; complete generated product
and log-traffic grid-sensitivity selection and rendering; required sensitivity
and limitation copy; exact display/manifest/results pins; malformed and
mismatched manifest rejection; feature-count rejection; accessible default
controls; and pairing-failure lifecycle isolation without disturbing unrelated
layers.

The final repository-wide `npm run verify:clean` passed dependency installation,
type-generation, formatting, lint, generated-type checking, all 91 tests, and the
static production build in one run. The same complete gate passed again after
the clean rebase onto `c524dfc231e28a69f3c58dc39584327e6151d70d`; `npm ci`
reported two high-severity audit findings in the committed dependency graph, but
installation and every required gate passed, and this documentation integration
did not change dependencies. Historically, the initial implementation's
first clean-gate build compiled and generated every page but ended with Windows
`EBUSY` while removing `web/out`, because the local browser-verification server
still held that directory as its working directory. After stopping that server,
the same production build passed. This was an environmental output-lock failure,
not an application or test failure.

Analysis gates were not rerun because no analysis code, contract, fixture, or
artifact was changed. AIS processing and scientific-result generation were
intentionally not rerun. Deployment checks were not run because deployment is
outside this branch's authority.

## Live browser evidence

Final local verification after the rebase used the production static export
served on localhost and headless Chrome 152.0.7977.76. The fresh report is
retained, ignored, at
`data/interim/m7-exposure-interface/browser-verification-rebase/browser-report.json`:

- Checked at: `2026-09-08T22:29:19.097Z`
- Bytes: 155,398
- SHA-256:
  `aaa5e0bde72d91019d18f350cfbf21c927360f670e47ceed942c1ea6b4c679d2`

At 390×844, 820×1180, and 1440×900, the browser independently confirmed:

- exactly one whale, vessel, exposure, domain, and VSR layer;
- exactly 2,793 exposure features;
- initial `product_index` renderer with six classes;
- exposure on, whale/vessel off, and domain/VSR on;
- exact order whale → vessel → exposure → domain → VSR;
- exposure, vessel, and domain bounds all equal
  `[-121.85726659994603, 32.05514455657572, -117.097556437, 35.000000108282464]`;
- exposure off/on and product/log renderer changes without duplicate layers;
- whale/vessel on and domain off/on without duplicate layers;
- all expected generated result strings visible, including both methods'
  integrated and p80/p90/p95 high-area grid changes;
- the verified display/manifest/results-pairing disclosure present;
- 3 px visible focus outline on the log-traffic radio control;
- usable document/panel scrolling, expandable sensitivity content, and no body
  or document horizontal overflow; and
- no visitor sign-in prompt, console error, log error, or network failure in the
  standard cases.

Three request-interception cases were also inspected at 820×1180:

- Missing exposure display: exposure count 0; all four independent layers count
  1; results remain visible; clear generic warning; no console error.
- Results-ID mismatch in the manifest: exposure count 0; all four independent
  layers count 1; results remain visible; clear pairing warning; no console
  error.
- Malformed GeoJSON with Web Crypto deliberately unavailable so parsing is
  reached: exposure count 0; all four independent layers count 1; results remain
  visible; clear generic warning. ArcGIS emitted two expected parse/layer-view
  console errors for the intentionally malformed blob.

Map/results and all three failure screenshots are retained beside the report.
Their final SHA-256 values are:

| Screenshot                      | SHA-256                                                            |
| ------------------------------- | ------------------------------------------------------------------ |
| `390x844-map.png`               | `02061acaccd71a0fab4a2d9e929185af240626be4e50804f6f891882c77ae96d` |
| `390x844-results.png`           | `0634cfd99d5b096cb7609f7deb57d9153f21d5fc35686a1ea83cc5a3b7e6360b` |
| `820x1180-map.png`              | `fd446d80cd6fb447f7a77017e5e48ab50bdbf9b8079229f78b60a221740e9e25` |
| `820x1180-results.png`          | `6a2d07e8332ae0657de82571093b488ed395892b6c0c1b2a2a4005ae49ea70fa` |
| `1440x900-map.png`              | `569a981af9172004340ddf3551e1784da232af60910aee31da190a436740f04a` |
| `1440x900-results.png`          | `8a65375e4aa0f289892830eb5d4d3db5e5c9e416c03c4673d58301acbb3f6c16` |
| `failure-missing.png`           | `ef892db68308326c274886bca5f9eda1c0075b419d8b030ae1aea26cdb9310f4` |
| `failure-manifest-mismatch.png` | `33f985485659c97c659adf33adc28ecc5700ea339862a02cbfdbf5d33741aa59` |
| `failure-malformed.png`         | `1042d3dc41660a7ebbe2b6a7120695edb704228dd287a57227c6aca7593c2086` |

The pre-rebase approval-correction evidence remains preserved separately under
`browser-verification/`; its report SHA-256 is
`5d364fd729f70c9b89f9000941a46ba9df7782cad7461c0e0d2f223f2fce21e6`.

The first development browser pass exposed a collapsed small-screen map caused
by a percentage-height flex chain; the map now has a tested small-screen height.
A later diagnostic pass loaded zero exposure features because ArcGIS rejected
explicitly declared boolean p90 fields as `small-integer`; those unused field
declarations were removed without changing the GeoJSON, after which all 2,793
features loaded. Temporary diagnostics were removed before final gates and final
browser capture.

No private browser key was available or requested. Verification therefore used
the public `topo-vector` basemap setting. The basemap and analytical layers did
render, but the application correctly retained its visible warning that
`NEXT_PUBLIC_ARCGIS_API_KEY` was not set. This evidence does not validate the
keyed `arcgis/oceans` production basemap, origin restrictions, or a deployed
anonymous session. Those remain M4/release-owner checks; no account, referrer, or
key was accessed or changed.

## Ownership dependencies and remaining work

There is no code-level ownership dependency requiring an overlapping change in
this branch. M4's deployment/Toolbar work and M5's source-date disclosures are
now present through the rebased `origin/main`. Remaining work is:

1. Independent scientific/content audit of the generated values and cautious
   interpretation.
2. Author acceptance of the public wording and headline hierarchy.
3. Authorized release-staging integration and a fresh configured-browser check.

The branch is not deployable through the unchanged approved three-input release
package. `web/scripts/stage-release.mjs` and
`web/scripts/release-inputs.json` were deliberately left unchanged.

## Required later release-staging integration

After M4 and M5 are integrated and the result is approved, the release owner must
extend the release staging as one audited change:

1. Add the exact exposure GeoJSON and paired manifest to the release input
   allowlist with the hashes above.
2. Provide build-time resolved URLs for both the content-addressed exposure
   display and its content-addressed manifest. The current M7 defaults are
   `/layers/relative-exposure.geojson` and
   `/layers/relative-exposure.geojson.manifest.json`; the current release script
   renames allowlisted files by checksum and exposes only one environment URL per
   input.
3. Teach the release binding check about M7's `displaySha256` and
   `manifestSha256` pins, or adopt an explicitly reviewed equivalent. The current
   script recognizes only an `exportSha256` source-module property.
4. Copy the tracked, checksum-verified
   `results/exposure-results.v1.json` into the isolated staged source before
   building. The current staging script copies only the tracked `web/` subtree,
   while the static results loader reads `../results/exposure-results.v1.json`.
   The file is a build input baked into static HTML; it need not become a public
   runtime JSON endpoint.
5. Include the exposure display and manifest in the output allowlist, content
   types, immutable cache policy, receipt, and post-build checksum verification.
6. Re-run the clean isolated build, receipt/inventory checks, anonymous browser
   checks, exact layer count/order/feature-count checks, and missing/mismatch
   isolation against the release candidate before any authorized deployment.

Do not infer readiness from a normal worktree build: without these changes the
three-input stage omits the exposure files and staged results input, so the
release cannot faithfully reproduce this interface.

## Shared-owner documentation integration

After M4 and M5 merged and the author requested sequential integration, this
branch updated each owning document rather than leaving proposed copies here:

- `README.md` describes M7 as locally implemented and verified, while keeping
  the current demo and release explicitly input-only and the results unaccepted.
- `docs/roadmap.md` marks M7 **In progress**, records the local behavior and
  evidence, and keeps public delivery, mid-range performance, independent audit,
  and author acceptance open.
- `docs/architecture.md` records the static results boundary, exact
  display/manifest verification, isolated lifecycle, presentation defaults and
  ordering, plus the distinction between local integration and deployment.
- `docs/development.md` records the 91-test M7 coverage and the exact later
  release-stage work needed for the exposure pair and repository-level results
  build input. It does not authorize or implement that release change.
- `analysis/README.md` links the downstream local consumer while preserving the
  analysis-owned contracts and unaccepted interpretation.
- `web/README.md` records the local artifact identities, formula switch,
  generated results/sensitivities, limitations, defaults, failure behavior, and
  browser evidence.

## Interpretation choices requiring author review

- Retain `scenarios.5km_product` as the first exploratory measure and present the
  5 km log-traffic result immediately as a material formula sensitivity.
- Keep all-valid p90 as the initial descriptive high-exposure-area cutoff while
  making p80/p95, positive-only, and 10 km results reachable but secondary.
- Describe 92.2%/7.8% only as the distribution of integrated relative exposure,
  and 98.5%/1.5% only as the distribution of selected high-exposure water area.
- Retain the explicit statement that the 2024 vessel period and 2026 boundary do
  not represent contemporaneous encounters.
- Keep speed separate from this exposure result and avoid effectiveness,
  collision, strike, hotspot-cluster, optimization, or policy claims.

These are cautious interface choices based on the existing M6 interpretation;
implementation does not constitute final scientific or author acceptance.
