# M6 exposure results delivery handoff

Status: implementation and branch-local verification complete on 2026-09-06
Pacific time (2026-09-07 UTC); independent audit, owner review, integration,
publication-route acceptance, and release verification remain.

This handoff owns the execution record for the downstream M6 exposure-display
and application-results contracts. It does not replace the project brief,
roadmap, architecture, data-source register, development workflow, ADR 0020, or
the M6 analytical-foundation handoff.

## Checkout and scope

- Branch: `feat/m6-exposure-results-delivery`
- Worktree:
  `C:\Users\teche\socal-whale-vessel-risk-exposure-results-delivery`
- Base and initial branch head:
  `c5061355c934d8dc39c6c3df9c4c31cee04953b6`
- Initial merge-base with `main`:
  `c5061355c934d8dc39c6c3df9c4c31cee04953b6`
- The checkout was clean before edits.
- Implementation commit: `3b149e8` (`feat: add exposure delivery contracts`).
- Generated-results commit: `9ec6abc` (`feat: add generated exposure
  application results`).
- Summary-reconciliation hardening commit: `c9daa16` (`fix: verify exposure
  summary values before export`).
- This handoff is committed separately so its final commit remains identifiable
  from branch history.
- The concurrent M5 vessel/domain-display session used the separate
  `C:\Users\teche\socal-whale-vessel-risk-vessel-domain-display` worktree.
- This branch does not modify web application code, `web/README.md`, the
  vessel/domain-display export, or shared owner documents.

The owner-selected presentation direction is implemented as a contract, not as
a scientific expansion: the proportional product is primary, log traffic is a
required sensitivity, and the intended conclusion concerns exploratory spatial
overlap. Nothing here estimates individual strike probability, causal effects,
VSR effectiveness, avoided collisions, or an optimal boundary, and nothing is
a policy recommendation.

## Delivered implementation

The branch adds:

- `analysis/src/whale_vessel_analysis/exposure_delivery.py`: strict source
  bundle validation, deterministic contract construction, WGS84 display export,
  results export, output guards, and coordinated publication of the three files;
- `analysis/src/whale_vessel_analysis/exposure_delivery_cli.py`: the command-line
  boundary for checksum-pinned export;
- `analysis/tests/test_exposure_delivery.py` and
  `analysis/tests/test_exposure_delivery_cli.py`: known-answer and contract tests;
- `analysis/scripts/qgis_inspect_exposure_display.py`: checksum-bound local QGIS
  inspection and comparison rendering;
- `results/exposure-results.v1.json`: the small, tracked, machine-readable
  application-results artifact; and
- the ignored generated pair
  `web/public/layers/relative-exposure.geojson` and
  `web/public/layers/relative-exposure.geojson.manifest.json` for local M7
  integration and route assessment.

The display file is deliberately ignored. Its manifest is generated next to it
and binds the display checksum to the application-results checksum and ID. The
small application-results JSON is tracked. No VSR geometry, raw or derived VSR
copy, credential, private input path, execution clock, or private upstream
lineage digest crosses either public contract.

## Contract names and versions

| Boundary | Contract | Schema/version |
|---|---|---|
| Display GeoJSON | `relative_exposure_display_v1` | dataset contract in the manifest |
| Display manifest | `relative_exposure_display_manifest_v1` | processing version `1.0.0` |
| Application results | `relative_exposure_application_results_v1` | schema version `1`; producer version `1.0.0` |

The exporter rejects a source bundle unless all three expected bytes are pinned,
the analytical run identity can be recomputed, both GeoParquet tables pass the
existing independent verifier, the sensitivity report agrees with both tables,
and the current ADR 0020 method contract and accepted input identities match.

The contract preserves these analytical distinctions:

- cell intensity divides whale-density/traffic product by the full cell-water
  support, including where only part of that water is receiver-qualified;
- inside/outside integration multiplies that intensity by the exact qualified
  water split on the two sides of the VSR boundary;
- water outside the accepted 50-nautical-mile (92,600 m) station-buffer domain is
  excluded, not assigned low or zero traffic;
- display geometry is qualified water only, while the public properties retain
  both full cell-water and qualified-water areas;
- primary product and log-traffic sensitivity remain separate scenarios;
- all-valid water-area thresholds at p80, p90, and p95 are the baseline family;
  the positive-only family remains visible sensitivity information; and
- speed remains a separate descriptive output and is not folded into the
  exposure formula.

The display contains 2,793 qualified 5 km cells. Each feature carries only:
`object_id`, `cell_id`, `water_area_km2`, `qualified_area_km2`, primary product
intensity/index/p90 membership, and log-traffic intensity/index/p90 membership.
It does not carry per-cell inside/outside VSR areas or integrated contributions.
Excluded cells are absent and must never be drawn as zero.

Geometry is transformed from EPSG:3310 to RFC 7946 longitude/latitude with
always-XY axis order. It is not rounded, simplified, or densified. Parts, holes,
vertices, coordinate round trips, configured map extent, and transformation
definition/accuracy are checked and recorded in the manifest.

The application-results contract carries exact numeric values plus generated
presentation strings. Exact values are authoritative. Shares use one decimal
place, sensitivity share changes use four decimal percentage points, integrated
total changes use six decimal percent, areas use one decimal square kilometre,
and thresholds use four decimals, all with decimal round-half-up.

Null meanings, denominator text, qualified/excluded counts, threshold tie area,
units, source vintages, accepted vessel parameters, source references,
limitations, and provenance hashes are explicit. The exporter does not invent a
metric to fill an interface.

## Summary reconciliation hardening

Follow-up review correctly identified that a matching supplied report checksum
identifies the submitted bytes but does not establish that every statistic in
those bytes is numerically correct. Commit `c9daa16` closes that gap before any
public object is built.

For each 5 km and 10 km table, the loader now reconstructs the analytical
summary inputs from the verified serialized rows and reruns the accepted
`analyze_grid` calculation. It compares the complete report tree against those
recomputed values with exact keys, strict primitive types, exact text/enumerated
values, and calculation-appropriate floating tolerances. This covers:

- qualified, excluded, water, and zero-product cell counts;
- qualified water area and both water/VSR conservation residuals;
- integrated qualified/inside/outside totals and derived inside/outside shares;
- normalization maxima;
- both all-valid and positive-only p80/p90/p95 thresholds, availability/reason,
  selected identities, total/inside/outside area, shares, domain share, and tie
  area;
- ranked top-outside cell identities, coordinates, contributions, individual
  shares, and top-ten share;
- product-versus-log rank correlation and maximum rank change; and
- both global normalization controls, including normalizers, invariant shares,
  and threshold-membership equality.

The results verifier also regenerates the entire typed public projection and
requires the serialized public tree to equal it. Recomputing a self-consistent
`results_id` after altering a public value is therefore insufficient to pass.

No upstream nested mapping is copied wholesale into results or the display
manifest. Source/input hash maps, analytical-domain limitations, vessel
length-filter details, source references, normalization controls, and display
diagnostics are projected through explicit field lists. Available and
unavailable normalization controls and display diagnostics use dedicated typed
public shapes. Unexpected fields are rejected; allowed text/enumerations and
primitive types are checked. Regression tests inject private paths, debug
objects, token-like fields, and unexpected diagnostics at both checksum-matched
load and post-validation projection boundaries and confirm that no public
artifact can be produced from them.

## Fresh analytical source bundles

The retained M6 bundles predated the corrected identity/provenance separation,
so two fresh current-code analytical runs were performed sequentially under the
documented direct resource profile. Existing inputs, caches, and historical
artifacts were preserved.

Both runs used the required preflight gates of 2 GiB available memory and 20 GiB
free disk, runtime stop gates of 0.5 GiB available memory and 12 GiB free disk,
and the 1.75 GiB maximum application RSS gate. This was a small-grid exposure
run, not raw AIS retrieval or five-month cleaning.

Accepted analytical input identities:

| Input | SHA-256 |
|---|---|
| Water grid | `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031` |
| Whale grid | `421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62` |
| Vessel grid, both independent productions | `5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0` |
| Vessel quality report | `4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7` |
| Domain masks | `4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77` |
| Immutable local VSR snapshot | `2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783` |

Fresh bundle outputs were byte-identical:

| Artifact | SHA-256 |
|---|---|
| `exposure-5km.parquet` | `a8e65b6d0019a24122f16feb7d847e5e5a31ce1670a2eaa9ebfbb64fe4835a29` |
| `exposure-10km.parquet` | `cff427ae54b3660389cc8abe7a547ea060ee39038b542b9ee819d00c53eaf194` |
| `sensitivity-report.json` | `520afde75f34a0293feef17376d44be12e9b96dcfe1b4dac9bee56747b0504ff` |
| Analytical run ID | `exposure-6dd927974fae959765c9b5c3` |

The first bundle is retained under ignored
`data/derived/m6-exposure-results-first/`; its run metadata SHA-256 is
`c26a538930e356a1f85d8e7851bd65cfb2c3dcceca37347bdc0642665cdec53c`.
The repeat is under ignored `data/derived/m6-exposure-results-repeat/`; its run
metadata SHA-256 is
`dc8b8ad93b87d9b20828f050558f14feaafa8901725ff4ccf6a5c125ad0d2338`.

The vessel lineage digests intentionally differ between these otherwise
identical analytical inputs:

- first: `799bc9c989fbdd4d06e5e675eb148c6cc422fae5461634ea36ae445503658fcb`;
- repeat: `150dc573eca914ec14cc46cd2a37900d91c33ea1155e37b262b83cf722807626`.

Both produce the same analytical run ID and identical analytical bytes. This is
the required evidence that timestamp-bearing execution lineage no longer
changes deterministic analytical identity. Run metadata remains private
generation lineage and is neither read by the delivery exporter nor copied into
the public outputs.

Resource evidence:

| Run | Profile SHA-256 | Exit/outcome | Operation | Peak application RSS | Minimum available memory | Minimum free disk | Output growth |
|---|---|---|---:|---:|---:|---:|---:|
| First | `c389fd6559146fc5fde08ea03ac0e80f158fa9c3d60a2ca1f91629888b1317d4` | 0 / `target_completed` | 37.592449 s | 163,241,984 B | 4,270,047,232 B | 45,540,061,184 B | 1,264,833 B |
| Repeat | `68821eea4ceb6b84dc4a8b78dbe8bf34f8b9281e06d620041210caf117d7e91f` | 0 / `target_completed` | 40.325231 s | 165,474,304 B | 4,313,333,760 B | 45,410,779,136 B | 1,264,834 B |

No resource threshold fired. The profile reports are retained under ignored
`data/interim/m6-exposure-results-first-profile/` and
`data/interim/m6-exposure-results-repeat-profile/`.

## Delivery artifacts and deterministic repetition

The canonical export records explicit generation time
`2026-09-07T00:24:32.351855Z` and used the first source bundle. An export from the
independent repeat bundle with the same explicit generation time is retained
under ignored `data/interim/m6-exposure-results-display-repeat-v3/`. All three
files are byte-identical between canonical and repeat exports.

| Artifact | Bytes | gzip -9 bytes | Brotli q11 bytes | SHA-256 |
|---|---:|---:|---:|---|
| `web/public/layers/relative-exposure.geojson` | 2,542,744 | 528,235 | 375,238 | `1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb` |
| `web/public/layers/relative-exposure.geojson.manifest.json` | 6,803 | 3,190 | 2,586 | `0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0` |
| `results/exposure-results.v1.json` | 31,381 | 7,699 | 5,986 | `ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60` |

Application results ID:
`exposure-results-8a0bf6c27e00fb40a13d6870`.

The results ID hashes the deterministic analytical/result content and excludes
`generated_at_utc`. A changed valid generation timestamp changes delivery bytes
but not this results identity. The same timestamp reproduces exact delivery
bytes. Tests also demonstrate that altering or adding private upstream run
metadata does not change public outputs.

The measured payload makes same-origin static delivery a credible candidate for
this exposure layer, but it is evidence for the later publication-route decision,
not authorization to deploy or a replacement for the required ADR/release
review.

After summary hardening, final-code exports from the independent analytical
bundles were written to fresh ignored locations:

- `data/interim/m6-exposure-results-reconciliation-first-v3/`; and
- `data/interim/m6-exposure-results-reconciliation-repeat-v3/`.

Each location reproduced the three canonical hashes and the results ID in the
table above. Thus stricter numerical reconciliation changed no public byte. The
existing QGIS evidence below remains bound to those exact display and manifest
bytes; no replacement geometry or visual claim was needed.

## QGIS and visual verification

QGIS 4.2.1 (GDAL 3.13.2) opened the exact final GeoJSON directly through OGR.
The final report is retained at ignored
`data/interim/m6-exposure-results-qgis-final-v2/render-report.json`:

- report SHA-256:
  `5c5eadc6d000c85981593d2ac53f004b9162a093acb944908447dff5736bd9c1`;
- display SHA-256:
  `1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb`;
- manifest SHA-256:
  `0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0`;
- VSR context SHA-256:
  `2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783`;
- CRS EPSG:4326, 2,793 features, 2,839 polygon parts, 35 interior
  rings, 35,598 vertices, no empty geometry, and no invalid geometry;
- qualified area 64,716.65982166733 km^2, matching the manifest;
- 281 primary-product p90 cells and 286 log-traffic p90 cells; and
- feature count, unique cells, parts, holes, vertices, area, and extent all
  agree with the manifest.

The reviewed overview sheet
`exposure-display-methods.png` has SHA-256
`80df7d3c2b5c8c9f244c0f07c2bf402c4570734d19a9f67b0c16484265929007`.
The reviewed detail sheet
`exposure-display-details.png` has SHA-256
`5e8f0b846918216ffc66f41c438cb6ac74f2d48a3f25a598af8f8e3080dfabe8`.

Human inspection found the export in the correct Southern California location
and axis order. Receiver arcs, the northern/southern cuts, coastline and island
holes, the shipping-corridor pattern, and crossings of the local VSR context are
plausible. No unexplained holes, spikes, slivers, displacement, or projection
artifact was visible. The product map is concentrated in narrow corridors; the
log-traffic sensitivity distributes influence more broadly, and its p90
membership visibly differs. Orange VSR geometry was loaded only as immutable
local inspection context and was not written as an output layer.

Failed/corrected checks were preserved rather than hidden:

- the first script run stopped before usable output because OGR exposes the
  GeoJSON feature identifier as `id`; the field check was corrected and tested;
- the first completed render under ignored
  `data/interim/m6-exposure-results-qgis/` exposed black legend swatches from
  comma-separated Qt colors; that failed visual evidence was retained and the
  color conversion was corrected;
- subsequent corrected renders passed; and
- the first final-v2 invocation used a nonexistent raw-data path and stopped
  before creating its output directory. The rerun used the checksum-verified
  immutable snapshot in its owning data worktree and produced the final evidence
  above.

## Proposed analytical interpretation

These are computed observations from the exact results contract, not yet final
website copy:

- At 5 km under the primary proportional product, 92.2185060789% of integrated
  qualified exposure lies inside the current VSR and 7.7814939211% lies outside.
  The denominator is integrated inside plus integrated outside exposure over
  exact receiver-qualified water; its total is 6,536.657810883277 modeled
  animals * vessel-km / km^2 for the period.
- The primary all-valid p90 threshold is 0.22859788468419606 modeled animals *
  vessel-km / km^4 for the period. The selected 6,473.820081391964 km^2 is
  10.0033285080% of qualified domain water; 98.5023814132% of that selected water
  is inside and 1.4976185868% is outside. Tied water area at the threshold is
  12.39240714173421 km^2.
- The primary all-valid p80 and p95 selected-water inside shares are
  93.6946606407% and 99.9400859781%, respectively. Their exact thresholds,
  selected areas, tie areas, and positive-only counterparts remain in the
  artifact and should stay available to review rather than being hidden behind
  the p90 default.
- Under the required 5 km log-traffic sensitivity, integrated inside share is
  74.9444347334% and outside share is 25.0555652666%. This is 17.2741 percentage
  points lower inside than the primary formula. Its p90 selected-water inside
  share is 94.9461124494%, compared with 98.5023814132% for the product.
- Product and log-traffic cell ranks are strongly but not perfectly associated
  (Spearman 0.9592536179); a cell can move as many as 918 ranks. Formula choice
  therefore changes both the inside/outside summary and spatial emphasis.
- Changing from 5 km to 10 km changes primary integrated inside share by only
  +0.0278 percentage points and primary integrated total by -0.006753%, but the
  primary p80 selected-water inside share changes by +4.1484 points. The primary
  p90 and p95 selected-water changes are -0.1473 and -0.1105 points.
- The 10 km log sensitivity changes integrated inside share by +1.1050 points,
  integrated total by +6.000890%, and p80/p90/p95 selected-water inside shares by
  +3.4734/+2.8319/+2.8978 points relative to 5 km.
- Global multiplicative rescaling checks leave integrated shares and every
  threshold membership unchanged to numerical tolerance at both resolutions.

Proposed conclusion for owner review:

> Under the proportional product, most modeled blue-whale-habitat and commercial-
> vessel-activity co-occurrence in receiver-qualified Southern California water
> is concentrated inside the current VSR zone. That concentration is not a
> formula-invariant result: compressing traffic with the required log sensitivity
> materially lowers the integrated inside share and broadens the spatial pattern.
> The analysis therefore supports a conclusion about relative spatial overlap,
> with method and grid sensitivity shown alongside it, not a collision-probability
> estimate or a claim that the VSR caused, prevents, or optimally manages strikes.

The website should also state that the product combines NOAA 2020b modeled
blue-whale density based on 1991–2018 survey data, July–November 2024 AccessAIS
commercial-vessel activity, and the 2026 VSR boundary. The mixed vintages and
uniform-within-cell assumptions limit interpretation. Counts or processing
readiness do not demonstrate observational completeness.

## M7 consumer instructions

M7 can consume these outputs without recomputing science or transcribing a
number:

1. Load committed `results/exposure-results.v1.json` and require the exact
   contract/schema expected by application code. Treat numeric fields as
   authoritative and use their colocated generated presentation strings for the
   agreed rounding.
2. Make `scenarios.5km_product` the primary narrative and default map. Present
   `scenarios.5km_log_traffic` as a required, plainly visible comparison rather
   than a footnote. Use `comparisons` for formula and grid-sensitivity copy.
3. Default high-exposure discussion to the all-valid p90 definition. Keep the
   p80/p95 and positive-only threshold families available for sensitivity review;
   do not substitute an invented class or percentile.
4. Serve `relative-exposure.geojson` from the selected provider-neutral route and
   verify the staged bytes against its colocated manifest before release. Pin the
   results contract, results ID, and results checksum recorded by that manifest.
5. Draw absent/excluded cells as no analytical coverage, never as low or zero
   traffic. Display indices as release-relative unit-interval indices, not
   absolute or cross-release quantities.
6. Keep speed in the vessel descriptive layer. Do not combine it with the
   exposure result.
7. Reference publisher-hosted VSR `FID = 126` directly for public context. Never
   publish the immutable local snapshot or a copied, clipped, simplified,
   converted, or derived VSR geometry.
8. Stage the ignored display/manifest pair in the application build or approved
   hosting route and ensure it remains paired with this exact committed results
   version. The generated file is reproducible from the pinned analytical
   artifacts; no hand editing is allowed.

If the concurrent vessel/domain branch introduces a shared display-geometry
helper, reconcile that work sequentially during integration. This implementation
owns its narrow exposure transformation and validation boundary; it should not
be silently rewritten during a concurrent merge.

## Verification commands and results

From `analysis/`:

```text
python -m uv lock --check
python -m uv run ruff format --check .
python -m uv run ruff check .
python -m uv run mypy src/whale_vessel_analysis
python -m uv run pytest
python -m uv build
```

Results:

- lock check: passed, 25 packages resolved;
- formatting: passed, 97 files already formatted;
- lint: passed;
- mypy: passed, 45 source files;
- pytest: passed, 617 tests in 81.47 seconds; and
- source distribution and wheel build: passed.

The 24 delivery-focused tests are included in that full count. They cover a
known-answer one-third inside share, the full-water/intensity versus qualified-
water/integration distinction, threshold ties and denominators, all-zero nulls,
decimal presentation, strict schemas/CRS/checksums/provenance, results tampering,
checksum-matched numerical inconsistencies across every consumed summary family,
strict text/enumeration and nested-field handling, upstream metadata exclusion,
post-validation private/debug injection, deterministic repetition,
timestamp-independent results identity, output guards, private-data sanitation,
RFC 7946 ring order, and CLI behavior.

Web checks were not run because this branch is prohibited from changing or
integrating web code. Both analysis and web CI jobs still must pass at the exact
future PR head before any authorized merge.

## Proposed shared-owner documentation updates

This session intentionally did not edit shared owners. At integration/review,
the following changes should be proposed against their current contents:

- `docs/architecture.md`: document the two public exposure contracts, their
  provider-neutral boundary, exact pairing, and measured static payload.
- `docs/roadmap.md`: record downstream M6 contract/export completion while
  leaving M6 incomplete pending independent audit and owner conclusion/map
  review; do not mark M7 complete.
- `docs/development.md`: add the checksum-pinned export/QGIS commands, generated
  output handling, current 608-test count, and release pairing check.
- `analysis/README.md`: add the exposure-delivery CLI, contract definitions,
  artifact identities, deterministic repeat, resource evidence, and QGIS record.
- `README.md`: update visible status only after integration and owner approval.
- `docs/decisions/README.md` and ADR 0020: register or update the accepted public
  delivery route only after route review; distinguish static-delivery evidence
  from authorization to deploy.
- `docs/data-sources.md`: no new source fact was introduced. Add a link to this
  delivery evidence only if the owner wants the validated downstream identity
  discoverable there.

## Remaining review, integration, and release gates

- An independent audit must review the implementation, exact artifact checksums,
  numerical contract, sanitation boundary, known-answer coverage, and this
  interpretation on the final branch head.
- The owner should review the two final QGIS sheets and the proposed conclusion,
  especially how prominently the 17.2741-point formula sensitivity and grid
  sensitivity are shown.
- Integrate with the M5 vessel/domain branch without overwriting either session's
  owned work; resolve any helper overlap explicitly after both branches settle.
- Decide and record the actual provider-neutral exposure publication route. The
  static payload is measured and plausible but not yet an accepted deployment
  decision.
- M7 must implement map/narrative consumption, responsive/browser behavior,
  accessibility, source copy, null/exclusion presentation, and contract/version
  failure handling without recalculation.
- Publication/account operations remain author-run. No account, basemap-key,
  hosting, pay-as-you-go, deployment, or spending action occurred here.
- Before release, perform the ADR 0019 anonymous/version comparison for the
  publisher-hosted VSR `FID = 126`, preserve the immutable local snapshot, and
  confirm attribution/disclaimer copy.
- Run both analysis and web checks on the exact integrated PR head, obtain the
  required independent review, and follow the authorized PR/CI workflow. Do not
  push or merge without explicit authorization.

No additional data retrieval or processing is needed for the next review. The
next useful owner contribution is reviewing the proposed conclusion and the two
maps so M7 presents the analysis the owner actually intends.
