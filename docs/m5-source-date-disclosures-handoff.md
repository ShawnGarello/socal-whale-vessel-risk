# M5 vessel/domain source-date disclosure handoff

## Status

This branch closes the remaining local M5 source-date disclosure gap without
changing the analytical period, processing, display artifacts, layer geometry,
symbology, account state, release package, or deployment.

- Branch: `feat/m5-source-date-disclosures`
- Worktree:
  `C:\Users\teche\socal-whale-vessel-risk-m5-source-dates`
- Base: `origin/main` at
  `48e3a4094932f17be0e0c7ae76fd248953ad2806`
- Implementation commit: `be1d29b` (`feat: disclose vessel and domain processing dates`)
- On 2026-09-08 the branch was rebased cleanly onto the merge of M4 deployment
  verification, then the M5 status owner in `docs/roadmap.md` and the web
  component owner in `web/README.md` were updated sequentially. Architecture
  and development need no substantive change because no boundary or workflow
  changed; the public README remains unchanged because this branch is not
  deployed and does not complete M5.
- Nothing was published, deployed, pushed, or merged. M5 remains in progress.

## Date provenance and artifact binding

### Vessel activity

The disclosure now labels **5 September 2026** as the analytical processing
date. It is not the 1 July through 30 November 2024 analytical period and is not
the later display-export date.

The date is supported by the two retained
`production_vessel_input_lineage_v1` records:

| Run | Lineage SHA-256 | Started UTC | Completed UTC |
|---|---|---|---|
| First successful production | `799bc9c989fbdd4d06e5e675eb148c6cc422fae5461634ea36ae445503658fcb` | `2026-09-05T18:26:50.763923Z` | `2026-09-05T18:55:12.571695Z` |
| Independent repeat | `150dc573eca914ec14cc46cd2a37900d91c33ea1155e37b262b83cf722807626` | `2026-09-05T19:24:05.317140Z` | `2026-09-05T19:54:45.025434Z` |

Both lineage records name the exact deterministic artifacts used by the
display exporter:

- production vessel input:
  `5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0`;
- production quality report:
  `4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7`;
- displayed vessel GeoJSON:
  `3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288`.

The production date and both deterministic input identities are also recorded
together in ADR 0018 and the analysis README. Exact AccessAIS retrieval
timestamps were not retained for the monthly inputs, so none is invented or
substituted here.

### Accepted analytical domain

The disclosure now labels **29 August 2026** as the domain-evidence processing
date. It applies to the checksum-bound evidence mask/report pair, not to the
2024 station-product vintage, source retrieval, later author acceptance, or
display export.

ADR 0002 records the analytical-domain evidence correction on 29 August 2026.
The analytical-domain evidence record binds that corrected clean run and its
same-day checksum-bound QGIS verification to:

- evidence mask:
  `4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77`;
- evidence report:
  `eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98`;
- displayed domain GeoJSON:
  `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf`.

For distinction, the source register records retrieval of the NOAA AIS Base
Stations and CUSP archives on 28 August 2026, and retrieval of the USCG
qualification documents on 31 August 2026. The already-generated candidate
geometry did not change when the author accepted the supported
`receivers_50_nautical_miles` interpretation on 31 August.

### Display export

The exact public manifests inspected for this work bind the displayed vessel
and domain GeoJSON checksums to all four source/evidence checksums above. Their
`exported_at` value is `2026-09-07T05:13:46.764830Z` (6 September local time),
with manifest SHA-256 values:

- vessel manifest:
  `6d18aaf3e74038db0165884c0daaf99b5acf400dd42f5cccccb42da848ff995d`;
- domain manifest:
  `d340dc2703f3a891a62d4735dc442a7545a6330e9e3322b95f742f502b3b0de6`.

That representation-export timestamp remains distinct from the dates displayed
as analytical/evidence processing provenance.

## Implementation

- `web/lib/vessel-source.ts` owns the ISO and human-readable analytical
  processing date beside the exact vessel input and quality-report identities.
- `web/lib/domain-source.ts` owns the ISO and human-readable evidence-processing
  date beside the exact evidence mask and report identities.
- The existing vessel and domain disclosure components render accessible
  `<time>` elements and explicitly state which checksum-bound artifacts each
  date describes.
- The focused input-layer source tests assert the exact ISO dates, visible
  labels, human-readable dates, and co-rendering of their bound artifact
  identities.
- No local path, raw record, credential, private lineage detail, private
  identifier, or VSR geometry was added to browser-visible metadata.

## Verification

Committed web dependencies were installed with `npm ci`: 554 packages, zero
reported vulnerabilities. The initial tool-bounded install was interrupted and
left an incomplete ignored `node_modules`; the next attempt reported
`ENOTEMPTY`. That incomplete directory was isolated and removed, and the fresh
locked install completed successfully without changing tracked files.

Final automated results from `web/`:

| Check | Result |
|---|---|
| `npm run format:check` | Passed |
| `npm run lint` | Passed |
| `npm run typecheck` | Passed; Next route types generated and `tsc --noEmit` clean |
| `npm test` | Passed; 79 tests across 8 files |
| `npm run build` | Passed; `/` and `/_not-found` statically prerendered |
| Keyless integration build with `NEXT_PUBLIC_ARCGIS_BASEMAP=topo-vector` | Passed |
| `git diff --check` | Passed before the implementation commit |

After the clean rebase on 2026-09-08, `npm run verify:clean` completed
successfully from `web/`: `npm ci` installed the 554 locked packages with zero
reported vulnerabilities; route type generation, formatting, linting, generated
type checking, all 79 tests across 8 files, and the production static build
passed. The six intervening M4 commits changed only owner/handoff documentation,
not executable web source, tests, configuration, or displayed artifacts.

During development, one focused-test command used a root-prefixed filter from
inside `web/` and found no tests; the corrected filter ran the intended file.
The first new markup assertions expected a lower-case server-rendered React
attribute, and the initial formatting check found the new test unformatted.
Both were corrected; the focused file then passed all 9 tests and the final
format gate passed.

Chrome 152 loaded the actual production static export over local HTTP using the
documented keyless `topo-vector` integration configuration and the exact ignored
whale, vessel, and domain GeoJSON source copies. Their copied byte identities
were rechecked before the run. At exact 390 x 844, 820 x 1180, and 1440 x 900
CSS-pixel viewports:

- vessel activity reached `Activity grid loaded` with 2,793 cells;
- the accepted domain reached `Qualified boundary loaded`;
- both displayed-export labels reported checksum verification from loaded
  bytes;
- both processing-date labels and `<time datetime>` values were visible;
- vessel input/quality and domain mask/report checksums were present in the
  corresponding open disclosures;
- each date remained within the viewport width; and
- neither the document nor body had horizontal overflow.

This was local project-layer and disclosure verification. It did not test a
deployment origin, release key, account capability, release package, Toolbar
issue, or broader console/network failure matrix. No account setting or
deployment resource was accessed or changed.

## Owner-document integration

- `docs/roadmap.md` now records the source/date criterion as met locally for
  whale, vessel, and domain, names the two processing dates and artifact
  bindings, and keeps M5 in progress until the change reaches and is verified at
  the production origin.
- `web/README.md` now records the two processing dates, distinguishes them from
  analytical period, source vintage/retrieval, acceptance, and display export,
  and carries the focused responsive-browser result.
- `docs/architecture.md` and `docs/development.md` were reviewed after the M4
  merge and were not changed because this work introduces neither a new system
  boundary nor a new workflow.
- The public `README.md` was reviewed and left unchanged because the branch has
  not been deployed and does not complete M5.

## Remaining work

- Independent audit of this exact branch.
- Explicitly authorized push, pull request, both required CI jobs on the current
  PR head, and GitHub merge.
- Inclusion in a later reviewed and approved release package and deployment.
- Deployed-origin verification remains separate. This branch must not be
  treated as deployed or as completing M5.
