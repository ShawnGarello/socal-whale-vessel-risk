# M5 vessel-activity and analytical-domain display handoff

## Status

This handoff records the next M5 input-layer slice implemented on
`feat/m5-vessel-domain-display` in the dedicated worktree
`C:\Users\teche\socal-whale-vessel-risk-vessel-domain-display`.

- Base and merge-base with `main` at checkout:
  `c5061355c934d8dc39c6c3df9c4c31cee04953b6`.
- The branch had no commits beyond that base when the continued session began;
  the dirty files were the prior two sessions' unfinished version of this same
  slice and were preserved, reviewed, tested, and completed here.
- No AIS processing was rerun and no vessel rule was changed.
- No exposure formula, exposure output, speed display, analytical headline,
  login, authentication interface, backend, or database was added.
- No VSR geometry was copied, transformed, exported, or committed. The existing
  publisher-hosted `FID = 126` reference remains unchanged.
- Generated display files and verification evidence remain ignored. No
  publication, deployment, push, or merge was performed.

The slice is implementation-complete. Its shared-owner documentation has now
been integrated in a documentation-only follow-up that is ready for independent
audit. M5 as a whole is not complete: delivery-route confirmation, release-time
VSR verification, and public delivery remain separate work.

## Accepted source artifacts

The exporter requires exact checksums before it reads the accepted production
inputs. It does not discover a newer artifact or fall back to another file.

| Input                             | Local artifact                                                                                                                      |            Bytes | SHA-256                                                            |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------: | ------------------------------------------------------------------ |
| Production vessel grid            | `C:\Users\teche\socal-whale-vessel-risk-accessais-july-month\data\derived\m3-production-vessel-repeat-attempt2\vessel-grid.parquet` |        1,346,787 | `5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0` |
| Production vessel quality report  | `C:\Users\teche\socal-whale-vessel-risk-accessais-july-month\data\derived\m3-production-vessel-repeat-attempt2\quality-report.json` |           36,512 | `4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7` |
| Analytical-domain candidate masks | `C:\Users\teche\socal-whale-vessel-risk-analytical-domain\data\interim\m2-domain-evidence\domain-candidate-masks.parquet`           | retained locally | `4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77` |
| Analytical-domain evidence report | `C:\Users\teche\socal-whale-vessel-risk-analytical-domain\data\interim\m2-domain-evidence\domain-evidence-report.json`              | retained locally | `eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98` |

The vessel Parquet is `production_vessel_input_v1`, contains 4,516 grid rows in
EPSG:3310, and represents retained passenger, cargo, and tanker movement for 1
July through 30 November 2024. The exporter additionally requires the quality
sidecar to match the quality metadata embedded in that Parquet and verifies its
accepted 300-second gap, 30-knot implied-speed ceiling, type-only population,
153 ready dates, unverified observational completeness, target-grid identity,
exclusion precedence, allocation statuses, and distance conservation.

The accepted domain remains `receivers_50_nautical_miles`: exact
modeled-whale-support water within 50 nautical miles, exactly 92,600 metres,
of relevant NAIS reception stations. It is not measured from the coast and is
not verified empirical 2024 reception coverage. The broader map/context extent,
modeled-whale-support water, and this receiver-qualified domain remain distinct.

## Implementation

### Deterministic exporter

`analysis/src/whale_vessel_analysis/vessel_domain_display_export.py` and its
CLI implement two display-only GeoJSON exports plus sanitized manifests.

- Existing whale-export helpers own canonical JSON, RFC 7946 ring orientation,
  transformation diagnostics, software identities, checksums, and safe-output
  validation; this slice reuses them rather than introducing a generic export
  framework.
- The exporter verifies the full vessel schema and accepted metadata, source
  values, quality report, domain evidence/report pair, common target grid, and
  default reporting-domain contract.
- Vessel source-cell water geometry is intersected with the exact accepted
  domain in EPSG:3310 before transformation to WGS 84. No simplification,
  coordinate rounding, or densification is performed.
- Complete source-cell activity and support-water values are preserved in
  partial boundary cells. `analytical_domain_area_km2`,
  `analytical_domain_fraction`, and `analytical_domain_overlap` state what part
  of the cell is displayed; values are not rescaled across the clipped shape.
- Speed, distinct-MMSI descriptors, redundant grid internals, and private
  processing lineage are withheld from public GeoJSON.
- Output writes are atomic, restricted to approved ignored/static layer roots,
  refuse overwrite by default, and restore a complete prior bundle if an
  overwrite fails.
- `analysis/scripts/qgis_inspect_vessel_domain_display.py` checksum-gates the
  exact GeoJSON and manifests before QGIS inspection. It does not convert or
  republish the artifacts.

The production quality accounting carried into the sanitized vessel manifest
is:

| Accounting item             |                  Value |
| --------------------------- | ---------------------: |
| Candidate segments          |             15,457,099 |
| Retained segments           |             14,946,183 |
| Excluded segments           |                510,916 |
| Maximum-gap exclusions      |                461,769 |
| Implied-speed exclusions    |                 49,147 |
| Other primary exclusions    |                      0 |
| Retained parent distance    | 2,257,826,774.587173 m |
| Allocated-to-cells distance | 2,084,502,496.069414 m |
| Outside-support distance    |  173,324,278.5177591 m |
| Conservation difference     |           0 m (passed) |

These values describe processing accounting, not observational completeness.

### Application integration

The application uses the existing same-origin pattern. `web/lib/vessel-source.ts`
and `web/lib/domain-source.ts` bind exact output/source checksums, public fields,
units, renderer classes, provenance, method statements, and limitations.
`web/lib/use-verified-geojson-layer.ts` and the testable lifecycle controller in
`web/lib/verified-geojson-layer-lifecycle.ts` own fetch, byte checksum, Blob URL,
ArcGIS layer, count assertion, timeout, failure state, and cleanup independently
for each invocation. Every async continuation checks the execution's disposed
and abort state before updating checksum/readiness state, creating a Blob URL,
assigning the shared layer ref, adding a layer, or continuing to a feature-count
query. Cleanup clears only locally owned resources, so a stale rejection or
resolution cannot remove or overwrite a newer layer.

- Whale and domain start visible; vessel starts hidden so two opaque analytical
  fills do not obscure each other on first load.
- The live layer order is whale, vessel, analytical-domain outline, then the
  publisher VSR reference.
- Native checkboxes control all four layers without reconstructing or
  duplicating them.
- The vessel legend has a neutral `zero retained movement` class, then fixed
  intervals over 0–1, 1–5, 5–20, 20–100, and over 100
  vessel-km/km² modeled-whale-support water. The observed cell counts are
  137 / 381 / 674 / 1,019 / 381 / 201. These are display intervals, not
  analytical categories.
- The dashed cyan domain legend explicitly says outside water is excluded, not
  low activity. Zero retained movement is explicitly not verified absence of
  vessels.
- Expandable source/method disclosures carry the exact export, input, quality,
  domain-mask, and evidence-report identities plus the analytical limitations.
- Missing file, checksum mismatch/malformed file, and ArcGIS parse/load errors
  remove only the failed layer and retain an accessible layer-specific warning.
- Behavioral regression tests dispose during deferred checksum verification and
  resolve an old layer load after its replacement is ready. They assert no stale
  state update, Blob URL, ref assignment, layer addition, feature query, failure,
  or replacement cleanup; a separate failure test retains an unrelated layer.
- `NEXT_PUBLIC_VESSEL_LAYER_URL` and `NEXT_PUBLIC_DOMAIN_LAYER_URL` permit a
  release to select checksum-addressed URLs. No account or publishing access is
  inferred by those configuration hooks.

## Generated display identities

The generated production files are under the ignored
`web/public/layers/` directory.

| Artifact                             | Features |     Bytes | SHA-256                                                            | Manifest SHA-256                                                   |
| ------------------------------------ | -------: | --------: | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `commercial-vessel-activity.geojson` |    2,793 | 2,720,788 | `3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288` | `6d18aaf3e74038db0165884c0daaf99b5acf400dd42f5cccccb42da848ff995d` |
| `accepted-analytical-domain.geojson` |        1 |   867,910 | `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf` | `d340dc2703f3a891a62d4735dc442a7545a6330e9e3322b95f742f502b3b0de6` |

The vessel output has 2,641 full and 152 partial cells; 1,723 source cells are
wholly outside the accepted domain. It contains 137 zero-retained-movement
cells and 2,656 positive-activity cells. The activity-density range is 0 to
8,487.070237441523 vessel-km/km². Vessel and domain outputs describe
64,716.65982166733 km² of accepted modeled-whale-support water (the vessel sum
differs only at floating-point summation scale).

A fresh repeat at
`data/interim/m5-vessel-domain-display/repeat-quality-bound-20260906/`
reproduced both GeoJSON checksums and byte sizes exactly. Manifest hashes differ
between runs only because `exported_at` intentionally records generation time.
The repeat manifests are `e9cf0a22f67792c0f007f28df6fa063f563fb156a67e4324d9df3b5a02c1697d`
and `906e9ae6c49bb33480e4e171feaa01e41ffa7d753404a5babc55d91e2a2cc3e2`.

The first repeat command used the nonexistent filename
`vessel-quality-report.json`; checksum-bound loading stopped before creating an
output directory. The corrected command used the retained
`quality-report.json` and succeeded. No source or existing output was changed by
the refused attempt.

## Representation measurement

The existing same-origin GeoJSON route was measured before introducing another
representation. Measurements use raw file size, gzip level 9, and Node's default
Brotli compression; they are local measurements, not deployed transfer claims.

| Layer                  | Raw bytes | gzip bytes | Brotli bytes |
| ---------------------- | --------: | ---------: | -----------: |
| Vessel activity        | 2,720,788 |    541,477 |      385,764 |
| Accepted domain        |   867,910 |    265,035 |      199,834 |
| Existing whale density | 3,277,329 |    574,907 |      396,852 |

The two new files total 3,588,698 raw bytes and 585,598 Brotli bytes. They loaded
successfully with the established browser lifecycle at all required viewports,
so this slice does not introduce vector tiles, a feature service, or a new
provider. The completed static export contained 899 files and 35,862,761 bytes;
that includes the ArcGIS application bundle and all static layer assets.

## Spatial inspection evidence

QGIS 4.2.1-Belém do Pará with GDAL 3.13.2 opened the exact final GeoJSON files
directly through OGR in EPSG:4326. Retained evidence is under
`data/interim/m5-vessel-domain-display/qgis-final-quality-bound-20260906/`.

- Inspection report: `inspection-report.json`, SHA-256
  `2cfca5ca98e5de69b5feead7db6e5d8b9e3d276a6076f1a9c55e43bdce55a140`.
- It binds vessel manifest SHA-256
  `6d18aaf3e74038db0165884c0daaf99b5acf400dd42f5cccccb42da848ff995d`
  and domain manifest SHA-256
  `d340dc2703f3a891a62d4735dc442a7545a6330e9e3322b95f742f502b3b0de6`.
- It found 2,793 vessel features and one domain feature, no empty or invalid
  geometry, and no vessel geometry outside the accepted domain.
- Feature, polygon-part, interior-ring, and vertex counts all agree with the
  manifests. The domain has 47 interior rings and 21,888 vertices; the vessel
  layer has 2,839 polygon parts, 35 interior rings, and 35,598 vertices.
- The displayed values and full/partial/zero counts agree with the manifests.

Five exact renders were reviewed visually:

| View              | PNG SHA-256                                                        |
| ----------------- | ------------------------------------------------------------------ |
| Full extent       | `e89d060b161eed03eed55aaa00719e83e65f6f67171ca21f0b2be9f5f1572804` |
| Northern boundary | `43059f2a9d618efef4867929efaf6648a3741b4cf17ab4c398a12e9cc62ff98a` |
| Southern boundary | `e2903d18bb35ecc9ef76885d470fd625fadd1a2f9736fbee115ee2ce8b184243` |
| Coast and islands | `1f9b746b841aedb1382ddfea3bc9a9bb5924e2843689fa285f76dcd79ebc1dfd` |
| Boundary detail   | `37f6b1b861707ba6bb70e500f0757f239913c7f013897d956ba0cc8a0e5647f8` |

The receiver-qualified boundary, clipped boundary cells, holes/islands, and
traffic corridors were coherent in all five views. No visible displacement,
invalid sliver, unexpected gap, or geometry outside the outline was observed.
QGIS emitted its environment's known missing bundled-font-directory warning;
the render and geometry checks completed and the images contain no text labels.

## Browser evidence

Headless Chrome 152 loaded the actual local Next development application with
`topo-vector` and no API key at 390 × 844, 820 × 1180, and 1440 × 900 CSS pixels.
Retained evidence and screenshots are under
`data/interim/m5-vessel-domain-display/browser-verification/`.

- Browser report: `browser-report.json`, SHA-256
  `8e9e1395539ccb0d2cdf18dedbb815effb555bf915184abc4a1a3352ee45501a`.
- Each viewport loaded exactly one whale layer with 4,516 features, one vessel
  layer with 2,793 features, one analytical-domain layer with one feature, and
  the publisher VSR layer with one feature.
- The expected renderer types, class counts, object-id fields, polygon geometry,
  fields, and layer order were present. Toggling vessel on, whale off, and domain
  off/on changed the live layer properties without creating duplicates.
- All three source files' decoded sizes matched disk. Warm project-ready times
  were 2.30–3.34 seconds; individual local GeoJSON resource times were
  0.21–0.55 seconds. Post-toggle JavaScript heap samples were 159–168 MB.
- Document and body horizontal overflow were false at every viewport. The panel
  scrolls at constrained sizes, keyboard focus had a 3 px outline, and the SDK
  attribution was present and visible at every viewport.
- Normal runs had no console, SDK-log, or network errors.
- An intercepted 404 left whale/domain/VSR at one copy each, removed vessel,
  retained the accessible generic warning, and produced only the expected 404
  resource-log entry.
- Intercepted malformed bytes were refused by the checksum with the distinct
  identity warning and no console or SDK errors.
- With checksum support deliberately disabled, malformed bytes reached ArcGIS,
  produced the two expected parse/LayerView console errors, removed vessel, and
  left every other layer ready at one copy.

Because no browser key was supplied, the existing application configuration
notice remained visible. This check neither validates a release key nor infers
ArcGIS publishing access. The public basemap and its attribution were visible;
project layers and the publisher-hosted VSR loaded independently.

## Automated verification

Commands were run from their owning component directories on 2026-09-06 local
time.

### Analysis

```powershell
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest
```

Results: 98 files formatted, Ruff clean, 45 source files type-checked clean, and
623 tests passed in 74.56 seconds. The focused exporter/CLI subset contains 30
known-answer, contract, quality-accounting, checksum, geometry/CRS,
determinism, sanitation, and atomic-output tests.

An additional non-gate diagnostic, `mypy src tests`, reported 345 errors across
20 test files because this repository's tests are not included in the typed
surface and many pre-existing fixtures intentionally lack strict annotations.
It stopped before pytest; the documented `mypy src` gate and full pytest run
were then executed separately and passed. No source error was reported.

### Web

```powershell
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

Results: Prettier clean, ESLint clean, generated types and TypeScript clean, 75
tests passed across seven files, and the Next 16.3.3 static production build
completed with `/` and `/_not-found` prerendered.

`git diff --check` also passed. Generated layers, manifests, QGIS output,
browser output, Chrome profile, `.next`, and `out` remain ignored.

## Shared-owner integration

The implementation commits intentionally did not edit shared M5/M6 owner
documents while a parallel M6 session was active. The subsequent
documentation-only follow-up integrates the implemented behavior and
verification evidence into owners without duplicating this run history:

1. `docs/roadmap.md`: records this M5 input-layer slice as implemented and tested,
   without marking M5 complete or claiming public delivery.
2. `docs/architecture.md`: records the two display contracts, checksum-bound
   same-origin loading, measured local sizes, and independent layer lifecycle.
3. `analysis/README.md`: documents the exporter/CLI contract, exact required
   input identities, output identities, and QGIS evidence command/report.
4. `docs/development.md`: adds the reproducible export and browser-verification
   procedures, environment hooks, and current component gate counts.
5. `README.md`: updates the visible project status while retaining the local-only
   verification boundary.

Remaining M5 decision work is to revisit the publication boundary using these
measured sizes; do not infer hosting access, enable pay-as-you-go, or publish
from CI.

No changes were made to the accepted reporting-domain contract, vessel
method, VSR reference decision, or M6 exposure contract.
