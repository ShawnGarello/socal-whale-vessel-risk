# M8 verification handoff

## Status and branch

M8 is **partially addressed, not complete**. No shared milestone status was
changed. The separate M5–M7 closure session owns shared status documentation.

- Branch: `feat/m8-verification`.
- Base: fetched `origin/main`, `3a9d8028a670d2c06687c9839739dd3fdac7f0b3`.
- Worktree: `C:/Users/teche/socal-whale-vessel-risk-m8-verification`.
- Implementation and handoff commit: identified by this file's Git history;
  the final local commit IDs are supplied in the session handoff.
- Original checkout was clean; branch/path names were checked before creation.
  Other worktrees were inspected read-only, never repurposed. No push, PR,
  merge, publication, deployment, credential access, or dependency upgrade.

The [production handoff](m7-production-candidate-handoff.md) is the authority for
the deployed package and acceptance. Its application source is
`3dfedc1faab1dd830a79ab5fa0efce3b07c9db25`. Relevant analysis, application,
results and release code had no changes between that source and this branch's
base. This branch adds a later verifier, not a new analytical method or release.

## Implemented and reused

`analysis/src/whale_vessel_analysis/exposure_verification.py` adds the narrow
`exposure_delivery_verification_v1` record contract, schema 1, verifier 1.0.0.
It reuses `exposure_delivery.load_bundle` (table read-back and full numerical
report reconciliation), `build_delivery_export` (complete public projection),
canonical serialization, existing checksum helpers and output-overlap guards.
There is no duplicated formula/spatial algorithm or workflow framework.

Each valid invocation creates a fresh ignored directory, writes an exclusive
`request.json` before checks and an exclusive `result.json` on completion.
Records identify pins, observed hashes, UTC times, check outcomes, evidence
references, actual package-source hashes, Git HEAD, lock hash and tool versions.
Failures/interruption remain evidence; an incomplete request is not a pass.
No generation lineage is edited. References are fingerprints, not interpreted
approvals; the record explicitly disclaims visual/scientific/raw-rerun checks.

Twenty-seven focused synthetic tests reuse existing known-answer delivery
fixtures. They cover all six pin mismatches, checksum-matched corrupt content,
missing evidence, exceptions/interruption, prior-record preservation, input and
implementation changes, invalid/overlapping/existing outputs, Windows junction
escape, incomplete writes, version identity and CLI behavior. The
[analysis procedure](../analysis/README.md#post-generation-exposure-verification)
documents the command and gates. No accepted output or public pin changed.

Two ignored session-only audit scripts compose existing APIs: M3
`verify_production_vessel_input.verify_bundle`, cleaned sidecar/schema validators,
period loading, M6 input-lineage checks, M5 exporters, and native release
`verifyReceipt`. They are retained with hashes below, not a new supported API.

## Criterion/evidence matrix

| M8 boundary or criterion | Proven by retained evidence | Independently checked this session | Remaining check / unavailable evidence |
|---|---|---|---|
| Raw deliveries → canonical intake | Five monthly intake manifests, repeat/identical-retry histories; July overlap repeat | All five raw files and 153 canonical slices exist with recorded sizes; manifests rehashed | Raw/canonical bytes were not freshly rehashed; retries skip existing cleaned dates and are not a fresh five-month rerun |
| Canonical → cleaned period | Successful monthly processing and period readiness | All 459 cleaned Parquet/quality/lineage files rehashed; accepted sidecar/schema validators; source/date/run/row links checked; 153 dates, 15,458,567 rows | Fresh cleaner execution from all five deliveries remains required for end-to-end criterion |
| Raw spatial → water/whale/domain | Water byte-identical overwrite repeat; whale a/b/c repeat; retained domain run and QGIS checks | Current spatial artifact hashes and M6 compatibility; retained QGIS applicability where specified below | Raw archive/tree integrity not freshly checked; no independently retained fresh domain repeat identified; earlier overwritten generation lineage is not recoverable from current file |
| Period/grid → production vessel | Two accepted production runs and separate candidate-matrix evidence | Both production bundles pass existing M3 verifier; all 153 input partition hashes link to period; M6 join/lineage checks pass | Fresh production generation from fresh cleaned period remains required |
| Analytical inputs → exposure | Current first/repeat deterministic files match; retained numerical review | Both bundles' four files rehashed; first bundle tables and entire report reconciled by accepted validator | New verification starts at retained analytical tables; it is not exposure generation from raw |
| Analytical → display/results → deployed package | M5/M6 exporter and release evidence | M5 three GeoJSONs and complete manifests reproduced in memory; M6 display/manifest/results reproduced exactly; receipt inventory and ten anonymous public requests match | No new full compiled-asset HTTP sweep, browser/performance check, or live VSR check; use historical production evidence |
| Every published number traceable | Typed results and public manifests bind methods/input artifacts | Existing exporter reconstruction and application source tracing described below | Scientific validity/observational completeness are not established by reproducibility |
| Reusable later evidence | Earlier checksum-bound documentation/QGIS records | New versioned write-once command and successful real record; failure/preservation tests | No retrofit of every historical layer's inspection; author decides sufficiency for carried-forward milestone wording |
| Documentation reflects implementation | Owners, ADRs and retained handoffs available | Owned analysis procedures corrected and new command documented | Shared-owner corrections below remain sequential work; full cross-document criterion not closed |
| Retrieval dates / versions; centralized limitations | Source register and analytical/results limitation fields | Retained metadata distinguished from processing/export clocks | Exact AccessAIS historical retrieval UTC timestamps unavailable; no invented timestamps; source-model season and completeness caveats remain |
| End-to-end rerun | Successful component repeats | Targeted read-back and reproduction only | One coordinated fresh raw-to-public processing chain is still required; plan below |

## Exact retained chain

All hashes below are SHA-256. Local aliases are navigation, not portable inputs:

```text
R = C:/Users/teche/socal-whale-vessel-risk
T = C:/Users/teche/socal-whale-vessel-risk-m8-verification
D = C:/Users/teche/socal-whale-vessel-risk-analytical-domain/data
W = C:/Users/teche/socal-whale-vessel-risk-whale-grid-transfer/data/interim/m3-whale-grid-transfer
V = C:/Users/teche/socal-whale-vessel-risk-accessais-july-month/data
P = V/interim/m3-accessais-july-month-gate/run
E = C:/Users/teche/socal-whale-vessel-risk-exposure-results-delivery/data
S = T/data/interim/m8-verification
```

### AIS intake and period

Source: retained AccessAIS 2024 monthly commercial-vessel deliveries. Exact
request parameters and source facts remain in the source register and each
manifest; source counts/readiness do not establish observational completeness.
Each raw path is `R/data/raw/accessais/<period>/<filename>`:

| Period | Filename | Bytes | Recorded raw hash (not rehashed here) |
|---|---|---:|---|
| 2024-07-01_through_2024-07-31 | AIS_178840031620476771_233-1788400317272.csv | 1827867349 | `30b64b3733f391a614faab0311e419b8b5e7d2262d196d87606de57397c11169` |
| 2024-08-01_through_2024-08-31 | AIS_178847348862876793_703-1788473489035.csv | 1857171239 | `42cb9fbfa8623c64460c2cbfd3d878a5f4e035a746637a4bdb036657a57fc29e` |
| 2024-09-01_through_2024-09-30 | AIS_178847357228176794_855-1788473572641.csv | 1583433195 | `0f41e63ce1afa54f4a6372e79c71a523122975351120f82a435696e7394df334` |
| 2024-10-01_through_2024-10-31 | AIS_178847372251376795_871-1788473722940.csv | 1659529483 | `859d97845fb6f1eb8b61a26e3dd3105c0477b3cc0db60fc6cca9e1f1149a348c` |
| 2024-11-01_through_2024-11-30 | AIS_178849884757876802_1101-1788498847948.csv | 1461597110 | `4cecc4641cc83b14d08b5bd98392bdecfe68a638224dbd456b6e80ff76f508dc` |

Manifest hashes, freshly checked, identify every daily canonical slice and
attempt history without duplicating 153 records:

| Manifest under P | Hash |
|---|---|
| intake/delivery-manifest.json | `98b8ba3ccedfa64359522279419805129612633fe60e99bc79e2f12ae586deb4` |
| intake-2024-08/delivery-manifest.json | `9fc954405013c839cf919c9da28c9af0cb62c3524bb32cb5b107b433ee3a25e9` |
| intake-2024-09/delivery-manifest.json | `310ed56deb8bccd459303d87f93ebcbc693d069d4f370f0b27201dd7ea2af9e1` |
| intake-2024-10/delivery-manifest.json | `3b995090f64445083d6c8b91be9a0f317698d59aef8e1715b5345b9a6859a718` |
| intake-2024-11/delivery-manifest.json | `bae82bd73a9da081bd1791b21e3267d663e372f01280cf478a76c18f73c11d71` |
| period.json | `5967bf2840316a6fab1bd8206e953394f5a93f04b7c883a34449fccfbf95f13c` |

Intake contract `accessais_period_delivery_v2`, processing 2.0.1; cleaner
`noaa_marine_cadastre_ais_extract_v2`, processing 2.0.0; period
`multiday_cleaned_ais_input_v1`, version 1.0.0, ID
`multiday-ais-17e982f999f7093945193378`. The period pins all files beneath
`P/cleaned/YYYY-MM-DD/`. Canonical slices are each intake's `daily/YYYY-MM-DD.csv`.
Both `prepared` and `identical_retry` attempts are retained. Exact raw retrieval
UTC timestamps were not retained: filename numbers and generation clocks must
not be substituted. July 15–21 overlap checking is seven-day evidence only.

### Spatial and analytical artifacts

Raw source hashes below are retained history, not newly recomputed:

| Input beneath D/raw | Retained hash | Recorded source date/version |
|---|---|---|
| noaa-swfsc-becker-2020b/swfsc_cce_becker_et_al_2020b.gdb.zip | `5677b95178b507337d2bdf048c9ad69383b0b48f7c7a1cd829774eeecd8c7a5d` | Retrieved 2026-08-25; NOAA 2020b; Blue_whale_summer_fall model, 1991–2018 observations |
| same source, unpacked .gdb tree | `1bfdb2bc75b26a3a33aa81952f5fc6cc58bd8e8b73a93362017fa06f76ec94cf` | Lossless archive unpack; use spatial_grid.sha256_path |
| noaa-ngs-cusp-west/West.zip | `53da33c37f6385fb7b64c59d96371b91eaa73b6e6c837e1f18147a8354015b85` | Retrieved 2026-08-28; last modified 2026-08-05 |
| noaa-ais-base-stations/AISBaseStation.zip | `8b317017783fd654a918e6cbf78edfea0d9df9eb6630157c019de7ddfa513003` | Retrieved 2026-08-28; vintage 2024-08-01 |
| bwbs-vsr-2026/bwbs_ca_vsr_zone_2026.geojson | `2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783` | Retrieved 2026-08-25; immutable analytical snapshot; never redistributed |

Freshly checked outputs (the audit report also records sizes and sidecar hashes):

| Artifact | Contract / identity | Hash |
|---|---|---|
| D/interim/m2-domain-evidence/noaa-whale-footprint-water-grid.parquet | projected_water_grid_v1; 4516 cells | `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031` |
| W/blue-whale-density-grid-a.parquet | blue_whale_grid_transfer_v1 | `421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62` |
| V/derived/m3-production-vessel-{first,repeat}-attempt2/vessel-grid.parquet | production_vessel_input_v1; vessel-input-5e590ff3d85ee7acb16e2fd1 | `5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0` |
| Both production quality-report.json files | Same quality evidence | `4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7` |
| V/derived/m3-full-period-matrix/g300-s30-first/vessel-grid.parquet | Accepted 300 s / 30 knot candidate comparison | `be3dc74d1c07525ef2a74cba1d0062abd97496b4043b3dd26847f9c3a65ec860` |
| D/interim/m2-domain-evidence/domain-candidate-masks.parquet | Eight candidates; only receivers_50_nautical_miles accepted | `4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77` |
| Same directory/domain-evidence-report.json | domain-evidence-0b3b7aa4ce0c050303886751 | `eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98` |

M5 whale export uses `D/interim/m2-domain-evidence/blue-whale-density-grid.parquet`,
with the same whale data hash but distinct generation lineage from W. The full
deployed whale manifest was reproduced using that exact source, not an earlier
manifest from an older handoff. Configuration remains the committed spatial
defaults and `analysis/evidence/domain-candidates.toml`; no choices changed.

Both `E/derived/m6-exposure-results-{first,repeat}` have ID
`exposure-6dd927974fae959765c9b5c3`, contract
`exploratory_relative_exposure_v1`, method 1.0.0:

| File | SHA-256 |
|---|---|
| exposure-5km.parquet | `a8e65b6d0019a24122f16feb7d847e5e5a31ce1670a2eaa9ebfbb64fe4835a29` |
| exposure-10km.parquet | `cff427ae54b3660389cc8abe7a547ea060ee39038b542b9ee819d00c53eaf194` |
| sensitivity-report.json | `520afde75f34a0293feef17376d44be12e9b96dcfe1b4dac9bee56747b0504ff` |
| first/run-metadata.json | `c26a538930e356a1f85d8e7851bd65cfb2c3dcceca37347bdc0642665cdec53c` |
| repeat/run-metadata.json | `dc8b8ad93b87d9b20828f050558f14feaafa8901725ff4ccf6a5c125ad0d2338` |

The different lineage clocks/paths are truthful; deterministic analytical bytes
match. Older foundation `exposure-cc50...` identities predate the corrected
identity boundary and are not the deployed inputs. No old lineage was rewritten.

### Public and approved package

Anonymous reads from `https://socal-whale-vessel-overlap.vercel.app/` on
2026-09-10 UTC matched the local approved receipt. Exact layer URLs use
`layers/<data-hash>.geojson` and `layers/<manifest-hash>.manifest.json`.

| Representation | Data hash | Manifest hash |
|---|---|---|
| blue-whale-density | `831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154` | `404c53356be7d743cbc5e4bc1b5741e4938c84e206caf1d53468954e368c8108` |
| commercial-vessel-activity | `3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288` | `6d18aaf3e74038db0165884c0daaf99b5acf400dd42f5cccccb42da848ff995d` |
| accepted-analytical-domain | `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf` | `d340dc2703f3a891a62d4735dc442a7545a6330e9e3322b95f742f502b3b0de6` |
| relative-exposure | `1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb` | `0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0` |

`results/exposure-results.v1.json` is a build-only input, not a public JSON
endpoint: 31,381 bytes, hash
`ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60`,
contract `relative_exposure_application_results_v1`, ID
`exposure-results-8a0bf6c27e00fb40a13d6870`.

Receipt at the production-candidate worktree's
`data/interim/m4-releases/m7-production-candidate-20260909-01`:
`e6532385fd3641275f38d9f203e75aa64fed0a1739ff3c29799113208f958ede`.
Existing `verifyReceipt` passed the 903-file, 38,658,688-byte local upload
inventory and build-input binding. `release.json` hash
`d763144156682d4226f5d124a3cfd94822bbafb947f68bb785532ee2648d75aa`
and `index.html` hash
`83617aceeb3207d7662437cf8cf0f9ffac0f7eb5f8e7fb6cabd13fec38d41de6`
also matched remotely. Ten requests were made, not a fresh full-package sweep.
The receipt's original staging mode is not a new approval; author approval and
deployment remain separately recorded in the production handoff.

Numerical trace: `exposure_delivery._scenario`, `_high_result`, `_comparisons`
and `_build_results_base` project the reconciled report into every scenario,
threshold/grid comparison, normalization, limitation and presentation field.
`web/lib/load-exposure-results.ts` hashes/validates that exact build input;
`web/lib/exposure-results.ts` selects its view model; `ExposureResultsPanel.tsx`
renders generated presentation values, rather than recalculating exposure.
For example, product integrated exposure is 6536.657810883277 with about 92.2185%
inside; p90 high-water-area share inside is about 98.5024%, a different metric.
Sensitivity alternatives are not confidence intervals. M5 exporters preserve
source whale density/vessel activity/domain values and disclosure metadata.
Successful byte reproduction checks the full projections, not only those examples.

Retained QGIS exposure evidence is under
`E/interim/m6-exposure-results-qgis-final-v2`. Render report hash
`5c5eadc6d000c85981593d2ac53f004b9162a093acb944908447dff5736bd9c1`
names the exact deployed exposure and manifest, QGIS 4.2.1 / GDAL 3.13.2.
Sheet hashes were independently matched:
`exposure-display-methods.png` =
`80df7d3c2b5c8c9f244c0f07c2bf402c4570734d19a9f67b0c16484265929007`;
`exposure-display-details.png` =
`5e8f0b846918216ffc66f41c438cb6ac74f2d48a3f25a598af8f8e3080dfabe8`.
Relevant exporter/renderer code is unchanged from the final summary-hardening
implementation (merged commit `901e2d8`). Historical human inspection is in the
[M6 delivery handoff](m6-exposure-results-delivery-handoff.md); the render script
itself says it did not visually review. **No new visual inspection occurred.**

## Checks actually run and new evidence

Installed only the committed analysis environment with `python -m uv sync --locked`
(Python 3.13.7); no web install. These affected-component gates all passed:

```text
python -m uv lock --check
python -m uv run ruff format --check .
python -m uv run ruff check .
python -m uv run mypy src/whale_vessel_analysis
python -m uv run pytest tests/test_exposure_verification.py
python -m uv run pytest
python -m uv build
python -m uv run python -m whale_vessel_analysis.exposure_verification --help
```

Full suite: **674 passed in 100.76 s**. Focused suite: 27 passed. An earlier
focused run had 26 passes and one Windows symlink-privilege skip; a junction
fallback removed the skip and was included in both final passing suites.
Formatting checked 105 files; mypy checked 48 sources. Git diff/whitespace,
ownership, secrets/data and staged changes were reviewed before committing.

`node data/interim/m8-verification/public_audit.mjs` ran from T, using the
existing receipt checker and anonymous fetch only. The retained-chain audit ran
from `analysis/` with session-local `PYTHONPATH=S`:

```text
python -m uv run python -m whale_vessel_analysis.resource_profile --module session_audit --output ../data/interim/m8-verification/inventory-profile-03/profile.json --label m8-retained-chain --disk-root ../data/interim/m8-verification/inventory-output-03 --minimum-free-memory-gib 2 --minimum-free-disk-gib 20 --runtime-minimum-available-memory-gib 0.5 --runtime-minimum-free-disk-gib 12 --runtime-maximum-application-rss-gib 1.75 -- --output ../data/interim/m8-verification/inventory-output-03/inventory.json
```

It passed in 18.7253 operation seconds, peak sampled application RSS 186,028,032
bytes. Earlier inventory attempts 01/02 were refused before target execution
for memory below 2 GiB and then disk below 20 GiB. After author-reported storage
recovery, preflight observed 61,237,985,280 disk bytes and passed. No gates were
lowered, caches cleared or data deleted by this session.

The exact successful exposure invocation, from `analysis/`, was:

```text
python -m uv run python -m whale_vessel_analysis.resource_profile --module whale_vessel_analysis.exposure_verification --output ../data/interim/m8-verification/exposure-profile-02/profile.json --label m8-exposure-verification --disk-root ../data/interim/m8-verification/exposure-02 --minimum-free-memory-gib 2 --minimum-free-disk-gib 20 --runtime-minimum-available-memory-gib 0.5 --runtime-minimum-free-disk-gib 12 --runtime-maximum-application-rss-gib 1.75 -- --bundle C:/Users/teche/socal-whale-vessel-risk-exposure-results-delivery/data/derived/m6-exposure-results-first --expected-5km-sha256 a8e65b6d0019a24122f16feb7d847e5e5a31ce1670a2eaa9ebfbb64fe4835a29 --expected-10km-sha256 cff427ae54b3660389cc8abe7a547ea060ee39038b542b9ee819d00c53eaf194 --expected-report-sha256 520afde75f34a0293feef17376d44be12e9b96dcfe1b4dac9bee56747b0504ff --display ../data/interim/m8-verification/public-01/relative-exposure.geojson 1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb --manifest ../data/interim/m8-verification/public-01/relative-exposure.geojson.manifest.json 0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0 --results ../results/exposure-results.v1.json ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60 --evidence ../data/interim/m8-verification/public-01/report.json 3463243babc288949dbdfd5fd8b5f0020d32a2e72f0ab492ea46d775ccbffd33 --evidence C:/Users/teche/socal-whale-vessel-risk-exposure-results-delivery/data/interim/m6-exposure-results-qgis-final-v2/render-report.json 5c5eadc6d000c85981593d2ac53f004b9162a093acb944908447dff5736bd9c1 --output-dir ../data/interim/m8-verification/exposure-02
```

Exposure used the README profiler command with fresh `exposure-profile-02` and
`exposure-02`, bundle `E/derived/m6-exposure-results-first`, three analytical
pins above, fetched `S/public-01/relative-exposure.geojson` and its manifest,
tracked results and their pins. Evidence arguments were `S/public-01/report.json`
and the exact QGIS render report with the hashes below/above. All seven checks
passed, 4.2739 operation seconds, peak sampled application RSS 135,921,664 bytes.
An earlier separate `exposure-profile-01` invocation was refused for memory;
after memory recovered, attempt 02 passed unchanged gates. No request/result
was created for a profiler refusal: three retrospective refusal notes explicitly
distinguish note/observation time from unavailable exact refusal time.

All following evidence is ignored and must remain retained locally; a clone
does not contain it. Records made before commit correctly identify base HEAD
plus the actual uncommitted source fingerprint, not a fictitious commit.

| Path under S | SHA-256 |
|---|---|
| session_audit.py | `a13b43eb78ef76d5f9ad74563f1d2303c7b4df431f0568a496222cbceeebd60a` |
| public_audit.mjs | `3fd0da6e0672bbcbb3407f68321cc158da9e1ab281355d80db835bb47e410df4` |
| public-01/report.json | `3463243babc288949dbdfd5fd8b5f0020d32a2e72f0ab492ea46d775ccbffd33` |
| inventory-output-03/inventory.json | `b59820c717c72f9637249faab397c1e3872b084293190eac0a0b83acbe890e5f` |
| inventory-profile-03/profile.json | `de07db3234b3d7d5b6c42e4ddeda0f33fe73c85f3fea0fb1c49a81279e6b65c1` |
| exposure-02/request.json | `a5c97382a8d036871e1f3b67a80dd471e68a837af87e04f9a6bcf2c065099703` |
| exposure-02/result.json | `b5710e8922e7f2a9f85b98485bd7965a7695c765bbdcb18ed90e02a932dffb99` |
| exposure-profile-02/profile.json | `dc205b6d1494ce55ecf85514333a141dfc6166d7f19cb5124d718aad0725f7f0` |
| preflight-refusal-01.json | `f45adb3ac81a1b277f493cc7cdb919dd108a5cf8f89e1d6bcc40796e10742c31` |
| preflight-refusal-02.json | `75d8472f95b8ed96a302a34ec65ddf8bc8d858a921b46c8dcee952206cc9fe89` |
| preflight-refusal-03.json | `0824d4a6a0c29516d49420db68a62fcb733be6c4c4f0755c1bc9286cec236122` |

Verifier source SHA-256 at execution:
`8d14441056c1b7ecd0226a5d479a5b6f2a98dc442512a8b77ced20d281c3e66c`.
The request records every package-source hash and locked/geospatial version.

## Smallest justified later end-to-end run

**Not run or authorized by this handoff.** Coordinate through the author after
browser-performance measurement finishes. One fresh five-month chain, one
production-vessel generation and one exposure generation are sufficient to test
the missing uninterrupted path against the retained/public pins. Do not rerun
the four-candidate matrix or automatically do another five-month repeat.

Use the committed locked environment and a new ignored run root N under this
checkout. Do not reuse P or any accepted destination. Every command needs a
unique profiler/output/spill directory; never add `--overwrite`. Preserve
failed runs. Copying old cleaned bundles or accepting skip/retry outcomes does
not fulfill fresh execution. Historical acquisition is not repeated: no orders
or downloads are needed or authorized.

1. Before processing, hash the five exact raw files against the table; hash
   the spatial archives, snapshot and .gdb tree using existing `sha256_file` /
   `spatial_grid.sha256_path`. Verify lossless archive/tree correspondence.
   Stop on mismatch; do not repair raw inputs. Preserve an append-only inventory.
2. Fresh water/whale/domain generation, using the existing README and domain
   evidence procedures, unchanged defaults and config. Target arguments are:

   ```text
   spatial_cli --input <D/raw/.../swfsc_cce_becker_et_al_2020b.gdb> --layer Blue_whale_summer_fall --source-crs EPSG:4326 --output <N/water.parquet>
   whale_grid_cli --whale-input <same.gdb> --whale-layer Blue_whale_summer_fall --grid-input <N/water.parquet> --expected-grid-sha256 <water-pin-above> --output <N/whale.parquet>
   domain_evidence_cli --config evidence/domain-candidates.toml --grid <N/water.parquet> --shoreline-archive <D/raw/noaa-ngs-cusp-west/West.zip> --station-archive <D/raw/noaa-ais-base-stations/AISBaseStation.zip> --vsr <D/raw/bwbs-vsr-2026/bwbs_ca_vsr_zone_2026.geojson> --report <N/domain-evidence-report.json> --masks <N/domain-candidate-masks.parquet>
   ```

   Module names above are beneath `whale_vessel_analysis`; use the profiler
   small-grid wrapper from the new README procedure (preflight 2 GiB memory /
   20 GiB disk; runtime minimum 0.5 GiB memory / 12 GiB disk; maximum RSS 1.75 GiB).
   Compare water/whale/mask/report deterministic identities before downstream use.
3. Execute `accessais_period_intake_cli` through `resource_profile` sequentially
   for each table row, with that month's exact inclusive requested start/end:

   ```text
   run --input <exact-raw-month-path> --intake-dir <N/run/intake-YYYY-MM> --requested-start <YYYY-MM-01> --requested-end <month-last-day> --memory-limit 512MB --temp-directory <N/spill-YYYY-MM> --cleaned-root <N/run/cleaned> --period-manifest <N/run/period.json>
   ```

   Profiler settings: `--disk-root <N/run> --spill-root <N/spill-YYYY-MM>`;
   preflight memory 2 GiB/disk 8 GiB; runtime memory minimum 1 GiB/disk 4 GiB,
   maximum application RSS 1 GiB/spill 2 GiB. Set `--expected-exit-code 3`
   for July–October (incomplete target period), `0` for November. Use unique
   profiles. The existing intake controls its one-thread execution. Do not
   invent `--source-content-length` or retrieval metadata. Verify 153 canonical
   hashes, all cleaned hashes/run identities, row accounting, full calendar,
   compatible sidecars and period ID against retained P; completeness stays
   explicitly separate from readiness.
4. Run `vessel_input_cli` once with
   `--manifest <N/run/period.json> --grid-input <N/water.parquet>
   --expected-grid-sha256 <water-pin> --output-dir <N/production>
   --memory-limit 1GB --threads 1 --batch-size 50000
   --temp-directory <N/production-spill>`.
   Use 2/20 GiB preflight, 0.5/12 GiB runtime minimum, 1.75 GiB RSS maximum,
   12 GiB spill maximum, and separate disk/spill roots. Run the existing
   `scripts/verify_production_vessel_input.py` read-back procedure with
   `--first <N/production> --repeat <V/derived/m3-production-vessel-repeat-attempt2>
   --grid <N/water.parquet> --expected-grid-sha256 <water-pin>
   --candidate <V/derived/m3-full-period-matrix/g300-s30-first/vessel-grid.parquet>
   --expected-candidate-sha256 <candidate-pin> --output <N/production-check.json>`;
   compare
   deterministic grid/quality bytes and identity, not path/time sidecar bytes.
5. Run `exposure_run` with `--water <N/water.parquet> --whale <N/whale.parquet>
   --vessel <N/production/vessel-grid.parquet>
   --domain <N/domain-candidate-masks.parquet> --vsr <immutable-snapshot>
   --output <N/exposure>` under the small-grid gates. Compare all three
   deterministic files and the current exposure ID above. Preserve new lineage.
6. Run `exposure_delivery_cli --bundle <N/exposure>
   --expected-5km-sha256 <5km-pin> --expected-10km-sha256 <10km-pin>
   --expected-report-sha256 <report-pin>
   --display-output <N/delivery/relative-exposure.geojson>
   --results-output <N/delivery/exposure-results.v1.json> --generated-at-utc
   2026-09-07T00:24:32.351855Z` **only as an explicit historical byte-comparison
   parameter**, not as a claim of the new run's actual time. Compare all three
   public identities. Run M5 whale/vessel/domain exporters with the exact
   arguments/pins in their README procedures against fresh upstream outputs.
   Public GeoJSON must match. New real export times and generation-lineage
   references can differ in manifests; compare other fields explicitly, retaining
   those truthful new provenance fields. Do not hand-edit a manifest to match.
7. Run the new verification command in a fresh attempt directory, attaching
   raw-to-upstream audit and exact public/receipt references. Its own pass is
   still only the analytical-to-delivery boundary. Review the ordered evidence
   across all stages. Reuse exact historical QGIS evidence only after artifact,
   implementation and inspected-view applicability checks; obtain new actual
   inspection when needed. Finish with anonymous public/receipt comparison,
   not deployment. Independent reviewer and shared owner assess M8 criteria.

Historical resource evidence: five monthly first runs total about 47.6 minutes;
production about 28–31 minutes; exposure about 38–40 seconds. Allow roughly
80–100 minutes **plus** setup, hashing, spatial steps and inspection (not a
guarantee; separate spatial duration estimate unavailable). Historical accumulated
intake/clean output was about 11.42 GB, transient peak about 12.85 GB. Plan at
least roughly 33 GiB initially free plus margin to retain fresh intermediates
and still pass the downstream 20 GiB gate. Per-stage documented gates and
runtime stop conditions are authoritative. Do not free space by removing
accepted/failed/rollback evidence or clear caches to manufacture a result.

## Shared-owner proposals and next steps

- Roadmap: record M8 work in progress and this evidence, not completion. The
  end-to-end and full documentation criteria remain open despite component repeats.
- Development/architecture: replace broad statements that no reusable later
  evidence exists with this narrow M6 record boundary; keep actual GIS inspection
  separate. Update the analysis test count to 674 after sequential integration.
- Shared summaries still containing pre-deployment/no-exposure/pending-review
  wording should point to the exact production handoff and distinguish independent
  content review, author acceptance and M8 reproducibility. Coordinate with closure
  owner rather than editing those documents here.
- Application artifact-identity text still says independent audit/author acceptance
  are pending despite recorded production acceptance. Report to the application
  owner for a separately authorized change/release; no application edits here.
- Source register: retain the missing AccessAIS retrieval timestamps as unavailable
  unless independent contemporaneous records are supplied. Do not infer model
  temporal representativeness, transfer/observational completeness, collision risk
  or propagated CV uncertainty from successful runs. Keep limitations centralized
  in their owner and referenced by the application; sensitivity is not a CI.
- Ignored audit evidence is local-only. Preserve the exact files and scripts listed
  here for independent audit; a new reviewer without them must obtain the retained
  inputs, not infer verification from this prose alone.

Ready for independent local review of the scoped change, not a claim that M8 is
closed. No PR was opened. After author-directed sequential integration/review,
both analysis and web CI must pass on the eventual PR head before any separately
authorized merge. Next substantive M8 step is the coordinated fresh chain above;
neither unsafe preflight conditions nor parallel browser work justify relaxing it.
