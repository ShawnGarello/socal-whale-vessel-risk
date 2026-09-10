# M8 verification handoff

## Status and branch

M8 is **In progress, not complete**. On 2026-09-10 the authorized fresh chain
reproduced source/spatial identities and the complete cleaned AIS period, then
stopped at the documented production-vessel runtime memory gate. No fresh
production output was accepted, so exposure, export, public comparison and final
verification remain open. Earlier integration after PR #36 remains included.

- Branch: `feat/m8-verification`.
- Current base: fetched `origin/main`,
  `65e12e7dc995339bfdaa4a9e41cf83c87ccab216` (merge of PR #36).
- Historical initial base: `3a9d8028a670d2c06687c9839739dd3fdac7f0b3`.
- Worktree: `C:/Users/teche/socal-whale-vessel-risk-m8-verification`.
- Historical audited head: `c4d3fba5450f97554c6b876502f3eb47449aa95e`;
  original implementation commit `00495356ab15d97f0e91720811f0a25baecce205`.
- Rebased implementation: `d642fdbad08002dba84793485ce51b719a3c7cd1`;
  identity documentation: `28a6ef32d8047805f9c4b8344c9029381c1268f3`;
  resource correction: `5ccd32773cf2420e5c407150e37c10c6bad6ab29`
  (original correction `de2574f186d2db125f447d23948df6ad0bd419e1`).
  The final integration commit is identified in Git history and the final handoff.
- Original checkout was clean; branch/path names were checked before creation.
  Other worktrees were inspected read-only, never repurposed. No push, PR,
  merge, publication, deployment, credential access, or dependency upgrade.

The [production handoff](m7-production-candidate-handoff.md) is the authority for
the deployed package and acceptance. Its application source is
`3dfedc1faab1dd830a79ab5fa0efce3b07c9db25`. Relevant analysis, application,
results and release code had no changes between that source and the historical
initial base. PR #36 subsequently merged a local acceptance-wording correction
and web regression test; its production release is still pending, as recorded
in the [closure handoff](m5-m7-closure-handoff.md). M5/M6 remain complete, and
M7's whole-connection check remains passed. This branch adds a later verifier
and documentation, not a new analytical method or release.

## Integration and audit preparation, 2026-09-10

Started from a clean `feat/m8-verification` at the audited head above. The
resource correction was committed before the explicitly authorized fetch/rebase.
Rebase onto the actual remote PR #36 merge replayed all three commits without
conflicts; no scientific decision or code conflict resolution was required.
Only this branch was rebased; primary `main` and other branches were not changed.
Analysis source/tests/lock/manifests are byte-identical across this rebase.

Roadmap now records M8 In progress, its narrow implemented record boundary and
the remaining fresh chain/documentation checks, without weakening criteria.
Development and architecture distinguish generation lineage from later records,
link to the workload-specific procedure, and retain actual GIS inspection as a
separate requirement. README and project-brief summaries reflect this status.
Historical test counts, M5/M6 completion, M7 whole-connection outcomes, production
identity and pending release of corrected local wording remain distinct.

All real-artifact records and commands in the matrix/tables below are **historical
pre-rebase evidence**, not new-head execution. The M8 request/inventory identify
initial base HEAD `3a9d802...` and the actual verifier source fingerprint later
committed in `0049535...`; older upstream and release evidence retain their own
recorded source identities.
No record, profile, refusal, accepted input/output or production/rollback package
was rewritten. No real-data processing or public check was repeated during that
documentation correction; the separately authorized fresh execution is recorded
in the next section.

Correction checks: profiler `--help` and 41 focused profiler/verifier tests
passed (9.50 s). Post-rebase `python -m uv run pytest -q` passed **674 tests in
105.08 s**. `python -m uv lock --check`, `ruff format --check .`, `ruff check .`,
`mypy src/whale_vessel_analysis` and `python -m uv build` also passed through
the documented uv environment (25 packages, 105 formatted files, 48 typed
sources). No web dependencies were installed or web suite rerun for this
documentation-only continuation; PR #36's 102-test web result remains its own
historical evidence, and both CI jobs are still required on an eventual PR head.

Final review checked 223 relative file/heading links in the seven affected
documents, whitespace, scoped diffs and secrets/data boundaries. All 11 retained
evidence hashes in the table below were rechecked unchanged. No new test/check
failures occurred in that continuation; earlier preflight refusals and test
attempts remain recorded as history. This was the pre-execution audit state; the
subsequent authorized fresh run and resource stop are recorded next.

## Fresh chain execution, 2026-09-10

This run started from clean branch `feat/m8-verification` at exact source commit
`c32e706e1e46d60cb9cbce04a8b1deba197b6819`. `python -m uv sync --locked` and
`python -m uv lock --check` passed, and every target CLI's `--help` loaded before
heavy execution. The new ignored root is
`T/data/interim/m8-fresh-chain-20260910-01`; the production CLI's owning output
guard required its unique bundle under
`T/data/derived/m8-fresh-chain-20260910-01/production-01`. The exact command
record is preserved at `N/commands.md`, SHA-256
`035a6aec6d8893e874348cedce49f39eb5bf0581c6cbf580a80365b5797102a2`.
No raw, retained, public, production-package or rollback artifact was modified.

Initial execution resources were 3,388,092,416 bytes available RAM and
73,436,286,976 bytes free disk. Every heavy stage performed its own immediate
preflight and ran sequentially. The source inventory passed all recorded sizes
and hashes for the five raw monthly files, the model archive and extracted GDB
tree, shoreline/station archives, and immutable VSR snapshot. ZIP CRC, member
set, and every member size/hash matched the extracted 124-file, 69,753,763-byte
tree. Inventory SHA-256:
`583d5e543ef633746c9208e2e904342e03449d342db5116073cfef66dcec318e`.

Fresh deterministic spatial outputs matched accepted bytes:

| Output | Rows/bytes | SHA-256 | Result |
|---|---:|---|---|
| Water grid | 4,516 rows / 437,466 bytes | `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031` | accepted pin matched |
| Whale grid | 4,516 rows / 523,986 bytes | `421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62` | accepted pin matched |
| Domain masks | 887,833 bytes | `4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77` | accepted pin matched |
| Domain report | 6,752 bytes | `eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98` | accepted pin matched |

New real generation paths/times correctly changed the water lineage to
`7f2b831bdab35ba7d352223e8bd4f88a76622a44bd89185e4a427170b992dd58`
and whale lineage to
`93e9db454b4b440e1cccfed2cd75dc2a3c78a7e54b641e48ab0ab1a795892182`;
those files were not edited to reproduce historical lineage. Domain evidence ID
`domain-evidence-0b3b7aa4ce0c050303886751` and accepted
`receivers_50_nautical_miles` facts matched. Because the deterministic spatial
bytes, relevant implementation and inspected views remain the exact accepted
ones, their historical checksum-bound QGIS inspection remains applicable; no
fresh visual inspection is claimed. No fresh M5/M6 display existed to inspect.

All five raw deliveries then ran sequentially into one new cleaned root. No
existing date was skipped and no old cleaned output was copied. July through
October returned the documented expected incomplete-period exit 3; November
returned 0 and made the period ready.

| Month | Raw rows, all assigned to requested dates | Fresh cleaned rows | Dates | Delivery ID | Comparison report SHA-256 |
|---|---:|---:|---:|---|---|
| July | 17,998,955 | 3,384,056 | 31 | `accessais-period-c718fbfe6a3eb2d200ace41e` | `cec75c5f56025328c9c90a041a3b7978d15f26b3b263924ce2f169eaeef52f51` |
| August | 18,284,354 | 3,501,843 | 31 | `accessais-period-9d5c80e7843e2ad9b8b2af2b` | `fa959a91d79dc163763d6bace36d0e6afb8c8b6dcc3e8c2908ea43395dc13cfc` |
| September | 15,638,516 | 2,861,837 | 30 | `accessais-period-1babd48139b3b00e3b9f6d43` | `51095f95fcd108e652faa5d50579ae760388783404a3e5f15b6daa55c3239014` |
| October | 16,355,292 | 2,889,605 | 31 | `accessais-period-bb0ffdedb948398fa753c3d2` | `2efa9c172cd2c776885627efd6ad9e2bf08fc2585c0fb40cc4386a73bfc5213d` |
| November | 14,342,365 | 2,821,226 | 30 | `accessais-period-bad86e685077a002810360e2` | `0239d45d71e481112bd4d712bc3e985d70769bba7e56b830ced857b13f6b8a1b` |

Every month had zero malformed/unassignable and zero valid out-of-request rows.
The final comparison validated all 153 fresh Parquet hashes, row counts, schemas,
cleaner IDs and sidecars and matched the retained stable period contract. Total
cleaned rows are 15,458,567, period ID is
`multiday-ais-17e982f999f7093945193378`, and readiness is `ready`. Report SHA-256:
`6391c7f8ef82fe48de5e084ddefec68b53af617b3f30a477f023bbb4af6c9e4e`.
Successful processing and readiness do not establish independent transfer or
observational completeness; both remain explicitly unverified.

| Profile | Target outcome / exit | Seconds | Minimum available RAM | Minimum free disk | Peak app RSS | Peak spill |
|---|---|---:|---:|---:|---:|---:|
| source inventory | completed / 0 | 14.44 | 3,280,363,520 | 73,436,274,688 | 90,558,464 | n/a |
| water | completed / 0 | 14.17 | 3,731,927,040 | 73,434,628,096 | 111,153,152 | n/a |
| whale | completed / 0 | 59.51 | 3,632,635,904 | 73,431,363,584 | 130,011,136 | n/a |
| domain | completed / 0 | 28.37 | 3,603,263,488 | 73,426,714,624 | 337,174,528 | n/a |
| July intake | completed / 3 expected | 987.73 | 2,634,870,784 | 67,595,907,072 | 617,353,216 | 781,549,568 |
| August intake | completed / 3 expected | 1,287.48 | 2,285,096,960 | 67,044,737,024 | 614,744,064 | 796,262,400 |
| September intake | completed / 3 expected | 709.66 | 2,788,536,320 | 66,057,814,016 | 635,355,136 | 764,346,368 |
| October intake | completed / 3 expected | 675.62 | 2,451,197,952 | 63,698,739,200 | 619,319,296 | 705,036,288 |
| November intake | completed / 0 | 710.75 | 1,742,209,024 | 61,028,192,256 | 623,935,488 | 677,806,080 |
| production vessel | **resource abort / 1** | 132.70 | **440,987,648** | 61,296,238,592 | 1,274,908,672 | 1,167,753,216 |

Profile SHA-256 values, in the same order through the successful November row,
are `504908515a7f345d31690472bcde9a3ca7c46775ca81a3794044e893a9d5deab`,
`08e346f75ccb471d9b62c0643d30d6a92aa59bc84951ee5cff096402965f0707`,
`a1e74fd299f43d02d22a55d15592c952b96431dc959c4371ab58644a4d8596b4`,
`4b36da6a53f0db82e46e16c8a2af29d08621ae61f3fc58f438c6561a8f9c398e`,
`83ccd3b286f9dd20cb0ae91fc9003f3207472fbe47eb2ed6ca57248be16ff145`,
`fdd393a305a9ce15c6e3e799634720bd83126e64e1694935fff93f4631f19478`,
`cce9698dbc4753dceadd68801e56171e22ead4d3208d23869949b4758af24adc`,
`4f0a465626f0faf453e172f70e50cf242aade8ce66521a2c950c484b412f1214`
and `4d52cc6018acb18e4a30ea8b55150bea96cc8325adc4f080cb7ad0359ac926e5`.

The production attempt passed preflight with 3,791,642,624 bytes available RAM
and 62,502,359,040 bytes free disk. The profiler stopped it when available RAM
fell below the 536,870,912-byte runtime minimum; application RSS remained below
the 1.75 GiB cap, spill below 12 GiB, and disk above 12 GiB. Profile SHA-256:
`d779b0fae35a73f57b424fb1243433c25abfcd21f93f13f75aa88f45197a9ac2`.
The output directory contains no accepted bundle. Five spill files totaling
1,167,753,216 bytes remain preserved. The failed attempt was not rerun.

Two non-heavy invocation errors are also retained accurately. An October
comparison launched from the repository root lacked the analysis environment
and exited before reading/writing comparison data; its corrected invocation
passed. The first November launch omitted the `run` subcommand and exited during
argument parsing; profile SHA-256
`9eb47418fb344b94ff9ffc99726be710e580a43dff0ded6817eadba8e21cd49b`.
The successful launch used a new profile and did not overwrite evidence.

The production read-back, exposure generation, M5/M6 fresh exports, public-byte
comparison and reusable final verification were not run because each depends on
an accepted fresh production vessel input. Historical export timestamps were not
used. Accepted domain/rules/formulas/sensitivities and public artifacts were not
changed, and no VSR geometry was copied into a public output.

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
| Raw deliveries → canonical intake | Five monthly intake manifests, repeat/identical-retry histories; July overlap repeat | Fresh inventory matched five raw identities; fresh sequential intake reproduced all 153 canonical slices and row accounting without skips | Independent transfer and observational completeness remain unverified |
| Canonical → cleaned period | Successful monthly processing and period readiness | Fresh cleaning reproduced all 153 deterministic Parquet files, cleaner IDs and 15,458,567 rows; schemas/sidecars and final period identity validate | No remaining generation gap at this boundary; independent audit remains |
| Raw spatial → water/whale/domain | Water byte-identical overwrite repeat; whale a/b/c repeat; retained domain run and QGIS checks | Fresh archive/tree correspondence passed; fresh deterministic water, whale, domain masks/report match accepted bytes; exact historical QGIS evidence remains applicable | No new visual inspection claimed; independent audit must confirm reuse applicability |
| Period/grid → production vessel | Two accepted production runs and separate candidate-matrix evidence | Fresh command used the fresh ready period/grid and passed preflight | Runtime memory guard stopped the attempt; no accepted fresh production bundle or read-back comparison |
| Analytical inputs → exposure | Current first/repeat deterministic files match; retained numerical review | Both bundles' four files rehashed; first bundle tables and entire report reconciled by accepted validator | New verification starts at retained analytical tables; it is not exposure generation from raw |
| Analytical → display/results → deployed package | M5/M6 exporter and release evidence | M5 three GeoJSONs and complete manifests reproduced in memory; M6 display/manifest/results reproduced exactly; receipt inventory and ten anonymous public requests match | No new full compiled-asset HTTP sweep, browser/performance check, or live VSR check; use historical production evidence |
| Every published number traceable | Typed results and public manifests bind methods/input artifacts | Existing exporter reconstruction and application source tracing described below | Scientific validity/observational completeness are not established by reproducibility |
| Reusable later evidence | Earlier checksum-bound documentation/QGIS records | New versioned write-once command and successful real record; failure/preservation tests | No retrofit of every historical layer's inspection; author decides sufficiency for carried-forward milestone wording |
| Documentation reflects implementation | Owners, ADRs and retained handoffs available | Analysis procedures corrected; shared M8 summaries integrated after rebase | Independent cross-document verification remains; full criterion not closed |
| Retrieval dates / versions; centralized limitations | Source register and analytical/results limitation fields | Retained metadata distinguished from processing/export clocks | Exact AccessAIS historical retrieval UTC timestamps unavailable; no invented timestamps; source-model season and completeness caveats remain |
| End-to-end rerun | Successful component repeats | Fresh raw/spatial processing through the complete cleaned period passed | Production resource stop leaves vessel, exposure, export, public comparison and final verifier open |

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

Historically, exposure used the initial 20/12 GiB disk profiler command above
with fresh `exposure-profile-02` and
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

## Resource-guidance correction, 2026-09-10

The initial verifier procedure inherited generation-sized disk gates without
workload-specific rationale. Inspection of the verifier, its in-memory loader/
export builder and profiler publication, plus the unchanged retained profile,
supports the [verifier-specific resource profile](../analysis/README.md#verifier-specific-resource-profile).
It documents the six inputs (3,843,772 bytes), two evidence references (8,520
bytes), 8,808 record bytes and separate 3,776-byte profiler report. There is no
verifier spill workflow; null profiler spill fields are not a measured zero.

For these exact pins, the corrected prospective disk reserves are 1 GiB
preflight / 0.5 GiB runtime. They are explicit operational headroom for tiny
record writes, atomic profiler publication and filesystem activity, not measured
demand or a forecast for arbitrary inputs. All memory gates remain unchanged.
No command has been executed under the corrected thresholds in this correction;
the supporting real run is historical and used 20/12 GiB. Historical files,
commands, hashes and refusal outcomes above remain unchanged. Do not apply this
profile to the session-wide retained-chain audit or any generation stage.

## Continuation procedure after the stopped fresh run

Steps 1 through 3 below completed in `m8-fresh-chain-20260910-01`; step 4 stopped
at its runtime memory gate. Preserve and reuse the successful fresh upstream
artifacts after identity checks. Do not repeat five-month cleaning blindly, rerun
the four-candidate matrix, overwrite the stopped attempt, or remove its spill and
profile. When resources again satisfy the documented conditions, resume at step
4 with new production output/profile/spill destinations, then continue only if
the fresh production comparison passes.

Use the committed locked environment and existing ignored run root N under this
checkout. Do not reuse P or any accepted destination. Every resumed command needs
a unique profiler/output/spill directory; never add `--overwrite`. Preserve
failed runs. Historical acquisition is not repeated: no orders or downloads are
needed or authorized. The production and exposure CLIs require derived bundles
under ignored `data/derived`; use
`Q = T/data/derived/m8-fresh-chain-20260910-01` for those outputs while keeping
profiles, spill and comparison evidence under N.

1. Before processing, hash the five exact raw files against the table; hash
   the spatial archives, snapshot and .gdb tree using existing `sha256_file` /
   `spatial_grid.sha256_path`. Verify lossless archive/tree correspondence.
   Stop on mismatch; do not repair raw inputs. Preserve an append-only inventory.
2. Fresh water/whale/domain generation, using the existing README and domain
   evidence procedures, unchanged defaults and config. Target arguments are:

   ```text
   spatial_cli --input <D/raw/.../swfsc_cce_becker_et_al_2020b.gdb> --layer Blue_whale_summer_fall --source-crs EPSG:4326 --output <N/water-01/water.parquet>
   whale_grid_cli --whale-input <same.gdb> --whale-layer Blue_whale_summer_fall --grid-input <N/water-01/water.parquet> --expected-grid-sha256 <water-pin-above> --output <N/whale-01/whale.parquet>
   domain_evidence_cli --config evidence/domain-candidates.toml --grid <N/water-01/water.parquet> --shoreline-archive <D/raw/noaa-ngs-cusp-west/West.zip> --station-archive <D/raw/noaa-ais-base-stations/AISBaseStation.zip> --vsr <D/raw/bwbs-vsr-2026/bwbs_ca_vsr_zone_2026.geojson> --report <N/domain-01/domain-evidence-report.json> --masks <N/domain-01/domain-candidate-masks.parquet>
   ```

   Module names above are beneath `whale_vessel_analysis`. These are generation
   stages, not the verifier. Their full-chain wrapper remains explicit:
   preflight 2 GiB memory / 20 GiB disk; runtime minimum 0.5 GiB memory /
   12 GiB disk; maximum RSS 1.75 GiB. Use `resource_profile` with each module,
   a fresh profile and that stage's output disk root; do not use the new
   verifier-specific disk reserves.
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
   `--manifest <N/run/period.json> --grid-input <N/water-01/water.parquet>
   --expected-grid-sha256 <water-pin> --output-dir <Q/production-02>
   --memory-limit 1GB --threads 1 --batch-size 50000
   --temp-directory <N/production-spill-02>`.
   Use 2/20 GiB preflight, 0.5/12 GiB runtime minimum, 1.75 GiB RSS maximum,
   12 GiB spill maximum, and separate disk/spill roots. Run the existing
   `scripts/verify_production_vessel_input.py` read-back procedure with
   `--first <Q/production-02> --repeat <V/derived/m3-production-vessel-repeat-attempt2>
   --grid <N/water-01/water.parquet> --expected-grid-sha256 <water-pin>
   --candidate <V/derived/m3-full-period-matrix/g300-s30-first/vessel-grid.parquet>
   --expected-candidate-sha256 <candidate-pin>
   --output <N/production-check-02/report.json>`;
   compare
   deterministic grid/quality bytes and identity, not path/time sidecar bytes.
5. Run `exposure_run` with `--water <N/water-01/water.parquet>
   --whale <N/whale-01/whale.parquet>
   --vessel <Q/production-02/vessel-grid.parquet>
   --domain <N/domain-01/domain-candidate-masks.parquet>
   --vsr <immutable-snapshot>
   --output <Q/exposure-01>` under generation gates: preflight 2 GiB memory /
   20 GiB disk; runtime minimum 0.5 GiB memory / 12 GiB disk; maximum RSS
   1.75 GiB, with a fresh profile and exposure output disk root. Compare all three
   deterministic files and the current exposure ID above. Preserve new lineage.
6. Run `exposure_delivery_cli --bundle <Q/exposure-01>
   --expected-5km-sha256 <5km-pin> --expected-10km-sha256 <10km-pin>
   --expected-report-sha256 <report-pin>
   --display-output <N/delivery/relative-exposure.geojson>
   --results-output <N/delivery/exposure-results.v1.json> --generated-at-utc
   2026-09-07T00:24:32.351855Z` **only as an explicit historical byte-comparison
   parameter**, not as a claim of the new run's actual time. Compare all three
   public identities. Retain the generation/export 2/20 GiB preflight,
   0.5/12 GiB runtime minima and 1.75 GiB RSS maximum, not verifier reserves.
   Run M5 whale/vessel/domain exporters with the exact
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

## Integration outcomes and remaining next steps

- Roadmap now records M8 work in progress and the fresh upstream evidence plus
  production resource stop, not completion. The raw-to-cleaned and spatial
  boundaries passed; the production-to-public chain and independent audit remain.
- Development/architecture now describe the narrow M6 record boundary and keep
  actual GIS inspection separate. The current analysis count is 674; historical
  counts remain historical. Shared summaries preserve PR #36's completed review
  and acceptance, rather than restoring obsolete pre-deployment claims.
- Application artifact-identity wording is corrected locally by merged PR #36,
  with 102 web tests recorded by that work. The deployed package still has the
  old sentence. A separately reviewed, authorized release is still required;
  no application edit or deployment was performed in this M8 continuation.
- Source register: retain the missing AccessAIS retrieval timestamps as unavailable
  unless independent contemporaneous records are supplied. Do not infer model
  temporal representativeness, transfer/observational completeness, collision risk
  or propagated CV uncertainty from successful runs. Keep limitations centralized
  in their owner and referenced by the application; sensitivity is not a CI.
- Ignored audit evidence is local-only. Preserve the exact files and scripts listed
  here for independent audit; a new reviewer without them must obtain the retained
  inputs, not infer verification from this prose alone.

Ready for independent local review of the documented partial execution, not a
claim that M8 is closed or execution-complete. No PR was opened. The next
substantive M8 step is a new production attempt only when the documented resource
conditions can be satisfied, followed on success by the dependent comparisons
above. After full execution and independent review, both analysis and web CI must
pass on the eventual PR head before any separately authorized merge.
