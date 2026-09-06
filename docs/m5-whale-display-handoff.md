# M5 whale display slice — session handoff

Session date: **2026-09-06**. Branch: `feat/m5-whale-display-delivery`,
worktree `C:\Users\teche\socal-whale-vessel-risk-whale-display-delivery`,
created from verified `main` at `2e4de60` (equal to `origin/main`, clean tree).
Nothing has been pushed, merged, deployed, or published.

This document is execution history and a handoff. The
[roadmap](roadmap.md) owns milestone status, [architecture](architecture.md)
owns the publication boundary, [development](development.md) owns commands and
workflow, and the [ADRs](decisions/README.md) own decisions. Nothing here
supersedes them, and **no milestone status was changed by this session**.

---

## What this session delivered

A deterministic public-display representation of the validated whale grid, and
its rendering in the existing ArcGIS application, verified locally.

1. A versioned Python display-export boundary,
   `blue_whale_display_export_v1`, that turns the validated
   `blue_whale_grid_transfer_v1` GeoParquet into RFC 7946 WGS 84 GeoJSON plus a
   sanitized, publishable export manifest.
2. An ArcGIS `GeoJSONLayer` integration in the existing map, with a density
   legend in stated units, per-cell popups, a visibility control, and an
   accessible source-and-method disclosure.
3. Checksum-bound QGIS inspection of the exact exported file, and browser
   verification at the three documented viewports plus a failed-request case.
4. Measured local delivery size and loading behaviour.
5. A Vercel-oriented release-staging and deployment plan, with the constraints
   the author must resolve.

**M4 and M5 remain as they were.** Local rendering of one input layer does not
satisfy either milestone's criteria; see "What is still unverified" below.

---

## Exact artifact identities

### Input, read only and unmodified

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `blue-whale-density-grid.parquet` (`blue_whale_grid_transfer_v1`) | 523,986 | `421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62` |

Read from
`C:\Users\teche\socal-whale-vessel-risk-analytical-domain\data\interim\m2-domain-evidence\`.
The byte-identical copies under
`socal-whale-vessel-risk-whale-grid-transfer\data\interim\m3-whale-grid-transfer\`
(`blue-whale-density-grid-a/-b/-c.parquet`) were rehashed in this session and
all three match. The generation lineage sidecar records run
`whale-grid-1d27df77bf1da01155fd`, target grid
`7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`, and source
directory digest
`1bfdb2bc75b26a3a33aa81952f5fc6cc58bd8e8b73a93362017fa06f76ec94cf`. Its
`visual_inspection_status` is still `not_completed`, which remains truthful for
that generation; the separate 2026-08-27 QGIS evidence for the same output
checksum is recorded in `analysis/README.md`.

### Output, produced by this session

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `blue-whale-density.geojson` | 3,277,329 | `831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154` |
| `blue-whale-density.geojson.manifest.json` | 7,244 | recomputed per run; the manifest's `exported_at` and `generation_lineage_sha256` are the only fields that vary |

Both remain under the ignored local data root and under ignored
`web/public/layers/`. **No generated layer data is committed.**

---

## Public-content inventory

Everything below is intended to be publicly readable. Nothing else from this
project crosses the publication boundary in this slice.

| Public content | What it contains |
|---|---|
| `blue-whale-density.geojson` | 4,516 features. Geometry only from the validated whale grid, transformed to WGS 84. Seven properties: `object_id`, `cell_id`, `modeled_density_animals_per_km2`, `modeled_abundance_allocation_animals`, `water_area_km2`, `source_coverage_fraction`, `coverage_status`. |
| `blue-whale-density.geojson.manifest.json` | Contract and version identifiers, source checksums and run id, NOAA/SWFSC source references and citations, transformation parameters, published/withheld field lists with units and reasons, output identity and diagnostics, software versions, and the layer's scientific statements. |
| Application text | Layer title, legend, units, classification rationale, source, citations, method, artifact checksums, and the scientific statements. |

**Deliberately absent from every public artifact:** filesystem paths, account
identifiers, credentials, API keys, raw source data, private generation
lineage, and any VSR geometry or VSR-derived value. A test asserts the manifest
carries no local path, no credential-shaped term, and nothing VSR-related; a
second test asserts no withheld field name appears in the GeoJSON.

Twelve source columns are withheld with a recorded reason: `row_index` and
`column_index` (redundant — `cell_id` encodes both), the four `cell_*_m`
EPSG:3310 grid bounds (projected internals; the published geometry is WGS 84),
`water_area_m2` and the four `source_covered_*` / `uncovered_*` area columns
(redundant with `water_area_km2` and `source_coverage_fraction`), and
`source_polygon_count` (a generation diagnostic with no display meaning).

---

## Implementation

### Analysis — new, owned by this session

| File | Purpose |
|---|---|
| `analysis/src/whale_vessel_analysis/whale_display_export.py` | The `blue_whale_display_export_v1` boundary. |
| `analysis/src/whale_vessel_analysis/whale_display_export_cli.py` | Its CLI. |
| `analysis/tests/whale_display_fixtures.py` | Source fixtures built from scratch. |
| `analysis/tests/test_whale_display_export.py` | 52 known-answer tests. |
| `analysis/tests/test_whale_display_export_cli.py` | 6 CLI boundary tests. |
| `analysis/scripts/qgis_inspect_whale_display_export.py` | Checksum-bound QGIS inspection, following the existing `qgis_inspect_vessel_grid.py` pattern. |

The command, run from `analysis/`:

```text
python -m uv run python -m whale_vessel_analysis.whale_display_export_cli --source <whale-grid.parquet> --expected-source-sha256 <sha256> --output <name.geojson> [--overwrite]
```

`--expected-source-sha256` is **required**, so a public artifact can never be
produced from an unidentified input. The command validates the source against
the exact `blue_whale_grid_transfer_v1` contract before any transformation:
dataset contract, schema version, declared analysis CRS, GeoParquet primary
column, WKB encoding and EPSG:3310 geometry CRS, the exact 19-column schema
with types and non-nullability, absence of nulls, unique `cell_id` values that
agree with their row and column indices, the contract row order, finite and
non-negative values, positive water areas, coverage fractions inside [0, 1],
and Polygon/MultiPolygon geometry that is neither empty nor invalid. When the
generation lineage sidecar is present it must declare the whale-grid lineage
contract and the same output checksum; only the run id and the sidecar's own
checksum are lifted out of it, so no local path from that file can reach a
public artifact.

Transformation is EPSG:3310 to EPSG:4326 with `always_xy=True`. Rings are
oriented as RFC 7946 requires (exterior counterclockwise, interior clockwise).
**No geometry is simplified, densified, or rounded, and no value is
recomputed** — the manifest records each of those as `not_performed`. After
transformation the exporter re-checks that geometry type, part count, hole
count, and vertex count are unchanged, that coordinates lie inside valid
longitude/latitude ranges, and that the extent stays inside the configured map
extent within a documented tolerance.

Serialization is canonical JSON — sorted keys, compact separators, UTF-8, LF,
`allow_nan=False` — so repeated exports of the same source are byte-identical.
Feature identity is the analytical `cell_id`; `object_id` is a display-only
1-based position in the contract row order, derived deterministically because
`GeoJSONLayer` needs a numeric object-id field.

Destinations are constrained: the path must end in `.geojson`, must not be
under `data/raw/`, and — when it falls inside the repository — must be under
`data/derived/`, `data/interim/`, or `web/public/layers/`, all of which are
Git-ignored. The GeoJSON and manifest are written to temporary siblings and
published together; an existing pair is refused unless `--overwrite` is passed,
and a failure mid-publication restores what was there before.

### Web — owned by this session

New: `lib/whale-source.ts`, `lib/whale-source.test.ts`, `lib/map-layer-state.ts`,
`components/MapLayerPanel.tsx`, `components/MapLayerPanel.module.css`,
`components/WhaleLayerControl.tsx`.

Changed: `components/ArcgisMapFrame.tsx` (whale layer effect), `app/page.tsx`
(the header said no project-derived layer was shown, which is no longer true),
`lib/vsr-source.ts` (now owns its own status messages), `.env.example`,
`.gitignore`, `.prettierignore`, `README.md`.

Renamed, mechanically: `lib/vsr-layer-lifecycle.ts` → `lib/layer-lifecycle.ts`
(`releaseOwnedVsrLayer` → `releaseOwnedLayer`), and
`lib/vsr-layer-behavior.test.ts` → `lib/layer-behavior.test.ts`. Removed:
`lib/vsr-layer-state.ts` and `components/VsrLayerControl.module.css`, both
superseded by the shared modules. **The VSR slice's behaviour and its no-copy
posture are unchanged**: the same publisher service URL, the same `FID = 126`
filter, the same one-feature assertion, the same 15-second bound, the same
attribution and disclaimer, popups still disabled, and no geometry stored.

The whale layer is a `GeoJSONLayer` with `geometryType`, `spatialReference`,
`objectIdField`, and the full field schema declared explicitly rather than
inferred, so an altered export fails to load instead of rendering with a
silently different schema. It is added at index 0, so the VSR outline draws
above the fill whichever layer finishes first. Its load is bounded to 30
seconds — longer than VSR's 15, because the whole file is fetched and parsed
before the layer is usable — asserts the expected 4,516 features, and on
failure removes the layer and reports a warning naming the basemap and VSR
boundary as still available. Each layer owns only what it created, through the
shared `releaseOwnedLayer` helper.

`copyright` on the layer puts the NOAA/SWFSC credit into the SDK's own dynamic
attribution alongside the Esri and basemap-provider credits.

Symbology is five equal 0.001 animals/km² classes with an open lowest and
highest class, on a single-hue purple ramp chosen to stay clear of the blue
basemap and the orange VSR outline. Per-cell outlines are omitted deliberately:
4,516 stroked cells read as a mesh and compete with the VSR outline. **This is
a display choice and is labelled as one in the interface.** Against the export
the classes hold 1,103 / 1,388 / 765 / 527 / 733 cells (24.4 / 30.7 / 16.9 /
11.7 / 16.2 %), so no class is empty and none dominates.

The layer control panel now holds both layers so they cannot overlap each other
or the SDK's zoom controls and attribution. On viewports narrower than 34 rem
the panel's height is capped at 45 % of the map and it scrolls internally.

---

## Verification results

### Deterministic export

Two exports run from two byte-identical but separately generated source copies
(`m2-domain-evidence` and `m3-whale-grid-transfer/...-c.parquet`) produced
**byte-identical GeoJSON**, SHA-256
`831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154`. The
manifests differed in exactly one field, `generation_lineage_sha256`, because
the two source copies carry different generation-lineage sidecars — a truthful
difference, and the run id was the same because it is checksum-derived.

### Export contents

| Check | Result |
|---|---|
| Features / unique `cell_id` | 4,516 / 4,516 |
| Polygon parts / interior rings / positions | 4,561 / 35 / 44,773 |
| Geometry types | Polygon and MultiPolygon; 31 MultiPolygon features, 22 features with holes |
| Empty or invalid geometry | None |
| Bounds (lon, lat) | −122.0, 31.99999999999996 to −117.097556437, 35.000000108282464 |
| Modeled density | 0.00083394 to 0.007648247 animals/km² |
| Conserved totals | 344.1406562623342 modeled animals; 107,728.695924 km² water area |
| Maximum vertex round-trip error | 9.78 × 10⁻⁹ m |
| PROJ operation accuracy | 4 m (a datum-transformation property, not this export's precision) |

The 4,561 parts, 35 rings, 44,773 positions and both bounds independently match
the measurements recorded in `docs/delivery-assessment.md` from a different
session and a different script, and the maximum round-trip error matches its
9.78 × 10⁻⁹ m to three significant figures.

**The northern latitude overshoot was investigated rather than clipped.** The
export's maximum latitude is 35.000000108282464, about 1.08 × 10⁻⁷ degrees
(≈ 1.2 cm) north of the configured 35° extent. This is the sagitta of a
straight EPSG:3310 chord between two vertices 0.01° apart on the 35° N
parallel: reprojecting such a chord's midpoint gives 35.000000108313536,
matching the observed value. It is inherent in the accepted grid-generation
method (densify to 0.01°, project, clip in EPSG:3310), not an export defect,
and clipping it here would silently change the analytical geometry. The
exporter admits it through an explicit, documented 1 × 10⁻⁶-degree tolerance
against the configured map extent and rejects anything larger.

### Tests

`analysis`: **475 passing** (up from 417; 58 new). New coverage includes
longitude/latitude axis order anchored to EPSG:3310's own −120° central
meridian, eastward/northward cell placement, a polygon-with-a-hole fixture with
RFC 7946 signed-area orientation checks, MultiPolygon part preservation, exact
value preservation at full double precision, stable and deterministic
identifiers, byte-identical repetition, bbox agreement, extent rejection, and
rejection of a wrong checksum, foreign contract, wrong schema version, wrong
declared CRS, wrong geometry CRS, non-WKB encoding, missing GeoParquet
metadata, missing or retyped or nullable columns, duplicate or inconsistent
cell ids, out-of-order rows, an empty source, non-finite or negative values, a
zero water area, an out-of-range coverage fraction, an unsupported geometry
type, and invalid or empty geometry. Output-safety tests cover atomic
publication, refusal without `--overwrite`, refusal of raw-data and tracked
destinations, and restoration of the prior pair when publication fails partway.

`web`: **56 passing** (up from 23). New coverage includes the artifact binding,
URL resolution and release override, feature-count rejection, unit and
precision declarations, the assertion that no withheld field name appears in
the layer configuration or the map component, class-break continuity and
coverage of the exported range, break-value assignment, refusal to classify
negative or non-finite values, ramp distinctness and translucency, layer
ordering beneath the VSR outline, the bounded and isolated failure path, the
explicit schema declaration, the attribution credit, and the whale control's
legend, units, disclosure, and scientific statements.

Gates run at handoff: `uv lock --check`, `ruff format --check` (83 files),
`ruff check`, `mypy` over 39 source files in strict mode, `pytest` (475 in
142.95 s), `uv build`; and for `web`, `prettier --check`, `eslint`,
`tsc --noEmit`, `vitest` (56), and `next build`.

### QGIS — visual verification of the exact export

Passed on **2026-09-06** in **QGIS 4.2.1 (GDAL 3.13.2)**, bound to export
SHA-256 `831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154`.
QGIS opened `web/public/layers/blue-whale-density.geojson` directly through OGR;
no conversion was used. The command was
`analysis/scripts/qgis_inspect_whale_display_export.py`, which refuses to run if
the file's checksum or the manifest's declared checksum disagree.

QGIS confirmed EPSG:4326 geographic, 4,516 features, 4,561 polygon parts, 35
interior rings, 44,773 ring vertices, zero empty or invalid geometry, 4,516
unique cell ids, the same density range, and the same extent — every one
agreeing with the manifest. Five 2200 × 1400 renders were produced with the
same class breaks and ramp the application uses, so the QGIS and browser views
are directly comparable, and all five were inspected:

| Render | SHA-256 | Result |
|---|---|---|
| `full-extent.png` | `60832bbe847e4d2243c494938cebfb42a6d777000e586984849ae6e823790176` | Correct Southern California Bight placement and axis order. Highest modeled density at Point Conception and through the Santa Barbara Channel, a band down the shelf and slope, elevated values toward San Diego, low values in the deep southwest — consistent with the source register's point tests. Blocky ~0.1° source-model structure visible through the 5 km cells. |
| `northern-boundary.png` | `3f68bd617dac93a06b9ceacf322b16065968e504a62581bebcab18e5193ad246` | Clean straight cut at 35° N with a row of clipped partial cells; no spikes or slivers. |
| `southern-boundary.png` | `2720d95e9c7eea76c882c4176d39ce31d76b6aed7ae4453255b754be43de3180` | Clean southern clip and the expected Mexican-border cut. |
| `coast-and-islands.png` | `89171b5c2f4bdc1468b6833f06b7404203cb4dad7aa92c8859b66bf8bda30234` | Island holes (Anacapa, Santa Cruz, Santa Barbara, Santa Catalina, San Nicolas) correctly cut out; coastline followed by clipped partial cells. |
| `grid-detail.png` | `ace6cf35f4834c330f9fed989393eecde8650f537cd3011de2f7fb5fe02b3432` | 5 km cells resolve individually; values change at source-model boundaries; harbour and breakwater detail preserved; no gaps, slivers, or displaced cells. |

No unexplained hole, sliver, displacement, or projection artifact was visible in
any view. The renders and the report remain ignored local evidence.

### Browser — the application

Verified on **2026-09-06** in headless **Google Chrome**, driven by Playwright,
against the real keyed production/static export served over HTTP from the API
key's authorized `http://localhost:3000` origin, at exact **390 × 844**,
**820 × 1180**, and **1440 × 900** CSS-pixel viewports. Results are in
"Verified locally on 2026-09-06" in [`../web/README.md`](../web/README.md); the
substance:

- The whale layer loaded at every viewport with exactly 4,516 features, polygon
  geometry, WKID 4326, `object_id` as the object-id field, and a five-class
  breaks renderer.
- The map held exactly one whale layer and one VSR layer, whale at index 0 and
  VSR at index 1. **The orange VSR outline is clearly legible above the purple
  fill** in the settled render.
- Legend, unit, all five class labels and the cell count were readable without
  opening anything; the visibility control hid and restored the layer; keyboard
  traversal gave a visible three-pixel focus outline; the source-and-method
  disclosure opened and carried the NOAA credit, the Becker et al. citation and
  the no-exposure statement.
- A map click opened a popup whose values matched the export exactly at the
  declared precision. Cell `r036_c049` displayed 0.002042 animals/km² for a
  stored 0.00204152140435664, 0.051038 animals for 0.051038035108916, 25.000 km²
  for 25.0, and 1.0000 for 1.0. The popup carries the layer's scientific
  statements alongside the values. A click near a shared cell edge returns both
  neighbouring whale cells, which is the SDK's hit-test tolerance; the VSR layer
  contributes no popup feature.
- No document or body horizontal overflow; SDK attribution visible and inside
  the viewport at every size; the sanitized console recorded no console error,
  page error, HTTP error, or request failure.

**Failed whale request**, at 820 × 1180, blocking only the whale GeoJSON: the
application removed the failed layer, showed its accessible warning naming the
basemap and VSR boundary as still available, kept the VSR layer loaded and the
map ready, and produced no indefinite loading state and no sign-in prompt. The
only console output was the blocked request and the two expected ArcGIS SDK
errors identifying `GeoJSONLayer` load and LayerView creation failure — the same
shape as the VSR failure evidence recorded for the earlier slice.

Two behaviours were found and handled during this check rather than left
implicit:

1. **The SDK adds a layer's `copyright` to the attribution when the layer view
   is created, shortly after the layer itself reports loaded.** Sampling
   attribution at the moment the layer reports ready can miss the credit. The
   credit does appear; the check now waits for it.
2. **Rendering 4,516 polygons continues after the layer reports loaded.** An
   evidence screenshot taken at "loaded" catches a partly drawn surface. The
   check now waits for the view to stop updating before capturing evidence.

---

## Practical local delivery size and loading

Measured on this machine, on **2026-09-06**. Environment: Windows 11
(10.0.26200), Intel Core i7-1255U, 12 logical CPUs, 16 GB RAM, Node 22.16.0,
headless Chrome at 1440 × 900, served over loopback from a local static server
with **no HTTP compression and no network or CPU throttling**.

**These numbers are a local functional observation of this project's own static
asset. They are not a benchmark of ArcGIS platform services, and no ArcGIS
service timing is reported.** The delivery assessment flagged that the Location
Platform agreement restricts platform benchmarking and the public communication
of benchmark results; that question is untouched here and remains for the author
to resolve before any timing exercise that measures ArcGIS services.

| Measurement | Value |
|---|---|
| Whale GeoJSON, uncompressed | 3,277,329 bytes (3.126 MiB) |
| gzip level 9 | 574,907 bytes (0.548 MiB), 17.5 % of raw |
| Brotli quality 11 | 396,852 bytes (0.378 MiB), 12.1 % of raw |
| Export manifest | 7,244 bytes |
| Complete static export | 32,241,469 bytes (30.75 MiB) across 895 files |
| Largest single file | the whale GeoJSON, at 3.28 MB |
| Geometry and feature ids | 2,226,026 bytes, 67.9 % of the export |
| Seven properties | 1,051,303 bytes, roughly 150 KB per property |

Loading, three runs each, median reported. "Cold" is a fresh browser context;
"warm" is a second load in the same context. The local server sends
`cache-control: no-store`, so **both cases re-download the file** — the
difference is warm SDK and JavaScript code caching, not HTTP caching, and no
HTTP-cache benefit is claimed here.

| From navigation to | Cold (median) | Warm (median) |
|---|---:|---:|
| VSR boundary ready | 1,882 ms | 997 ms |
| Whale layer ready | 1,892 ms | 1,010 ms |
| View settled after first render | 2,278 ms | 1,531 ms |

Pan-and-zoom to a new centre and zoom settled in 710–896 ms across all runs.
Reported JavaScript heap after settling was 84–128 MB. The map stayed
interactive; no crash or sustained unresponsiveness occurred in any run.

**What this does and does not establish.** It establishes that the export is
small enough, and this machine fast enough, that the layer is usable locally
without tiling or geometry simplification. It does not establish deployed load
time, behaviour on a slow connection or a low-end device, or behaviour once the
vessel and exposure layers are added. The delivery assessment proposed a
project acceptance target of a median whale-ready within 5 seconds after map
readiness at 10 Mbps / 100 ms latency / 4× CPU slowdown; **that target has not
been agreed and was not tested here**, because agreeing it before measuring is
the point of proposing it.

---

## Vercel readiness

The author prefers Vercel and this plan is built for Vercel. Official
documentation was checked on **2026-09-06**; the pages carried their own
`last_updated` labels of 2026-09-03 (limits), 2026-08-31 (Hobby plan),
2026-07-29 (fair use), and 2026-08-25 (project configuration and the Next.js
static-export guide). Live pages change — recheck before release.

**No Vercel account, team, project, plan, or billing state was inspected or
created, and nothing was deployed.** Everything below is documentation plus
local measurement.

### The fit is good on the numbers

| Hobby limit (documented) | This project |
|---|---|
| CLI static-file upload: **100 MB** | 30.75 MiB export |
| Files per CLI deployment: **15,000** source files | 895 files |
| Build time per deployment: **45 minutes** | local `next build` well under this |
| Deployments per day / builds per hour: **100** | ample |
| Concurrent deployments: **1** | ample |
| Typical monthly Fast Data Transfer guideline: **up to 100 GB** | ~0.4 MB Brotli per whale-layer load, plus the SDK chunks the page actually fetches |

Vercel serves static assets compressed, so the Brotli figure of 396,852 bytes
is the realistic transfer for the whale layer, not the 3.28 MB on disk. Static
asset requests that invoke no function are documented as not classed as builds.

### The blocking design constraint

**The whale GeoJSON is Git-ignored, so a Git-connected Vercel build would
produce a site without the layer.** Any Vercel route for this project must
carry locally generated data into the deployment. Two documented paths do:

1. **`vercel build` then `vercel deploy --prebuilt`** (documented in Vercel's
   "Deploying a locally built Next.js app" guide). `vercel build` writes
   `.vercel/output`; `--prebuilt` uploads that instead of the source. This is
   the Vercel analogue of the Cloudflare Direct Upload route the delivery
   assessment proposed, and it keeps generated data out of Git.
2. **Uploading the finished `web/out/` directory** as a static deployment, with
   `outputDirectory` set and no build command.

Path 1 is the recommendation: it keeps Next.js's own output contract and needs
no hand-written routing. **Neither has been executed**, so whether
`vercel build` on this `output: "export"` project produces the expected static
Build Output is **unverified**; it needs one author-run trial.

### The eligibility question the author must answer

Vercel's Hobby plan is documented as restricted to **non-commercial personal
use only**, with commercial usage defined as *"any Deployment that is used for
the purpose of financial gain of anyone involved in any part of the production
of the project, including a paid employee or consultant writing the code."* The
enumerated examples are payment collection, advertising a product or service
for sale, being paid to create or host the site, affiliate linking as the site's
primary purpose, and advertisements; donations are also called out as
commercial. **None of those applies to this project.** The broader "financial
gain" clause is the open question for a portfolio piece whose audience is
internship reviewers, and Vercel's own guidance is to ask their support team
when unsure. This is the author's call, not this session's; it is recorded, not
resolved. If the answer is unfavourable, the decision is between a Pro plan
(paid — not authorized) and another host, and it belongs in a decision record.

Also documented and relevant: exceeding a Hobby usage limit generally pauses
the feature for 30 days rather than billing; and Vercel does not support
connecting a Hobby-team project to a Git repository owned by a Git
*organization*. The project repository is under a personal account, so the
latter does not bite — but it is another reason path 1 above is the safer route.

### Configuration this project would need

- `NEXT_PUBLIC_ARCGIS_API_KEY` set as a **build-time** environment variable, and
  the credential's referrer restrictions extended to the deployed origin. Both
  are author-run credential operations. Rebuild after any key change, because
  `NEXT_PUBLIC_` values are inlined at build time.
- `NEXT_PUBLIC_WHALE_LAYER_URL` set to a checksum-addressed filename for a
  release, so an immutable artifact URL is never confused with a mutable one.
- `trailingSlash` already matches the Next.js `trailingSlash: true` export, so
  directory URLs resolve. `vercel.json` supports `outputDirectory`,
  `buildCommand`, `framework`, `cleanUrls`, `trailingSlash`, and `headers` if
  overrides prove necessary; none is known to be necessary yet.
- Long-lived caching for checksum-addressed layer files; the entry point must
  revalidate so new application code can never pair with stale data.

### Proposed release staging

1. Regenerate the export from the exact validated source with its checksum.
2. Assemble an isolated, ignored release directory: the static export plus the
   checksum-addressed layer file and its manifest.
3. Verify the release directory — file count, total size, no source data, no
   VSR geometry, no private lineage, no credential — and record the application
   commit together with every data checksum.
4. Author runs the build and the prebuilt deploy, then verifies the public URL
   in a clean browser with no session: map renders, whale layer loads, fetched
   bytes match the pinned checksum, compression and cache headers are as
   expected, console clean, and the deployed commit is the intended one.
5. Keep the previous complete release available for rollback. Never replace
   different bytes at an immutable URL.

### Author actions needed

| # | Action |
|---|---|
| 1 | Decide the Hobby-plan commercial-use question, or ask Vercel support. |
| 2 | Confirm a Vercel account exists (or authorize creating a free one) and confirm the plan and that no paid resource is enabled. |
| 3 | Run one `vercel build` + `vercel deploy --prebuilt` trial to establish the prebuilt path works for this `output: "export"` project. |
| 4 | Extend the ArcGIS browser key's referrer restrictions to the deployed origin, privately. |
| 5 | Resolve the Location Platform agreement's benchmarking and benchmark-publication clauses before any timing exercise that measures ArcGIS services, and agree or amend the proposed loading target. |
| 6 | Complete the outstanding authenticated ArcGIS account capability checks that M4 still requires. |

---

## What works locally, and what is still unverified

**Works locally, with evidence above:** deterministic export and repetition;
source contract enforcement; transformation and geometry preservation; value
preservation through export, SDK query, and popup; checksum-bound QGIS
inspection; keyed browser rendering at all three required viewports; layer
ordering with the VSR outline legible above the fill; visibility control;
legend with units; popups; source and method disclosure; keyboard focus;
bounded loading; isolated failure; and local delivery size and loading.

**Unverified:**

- Any deployment. Nothing has been deployed anywhere, and there is no public
  URL. Deployed-origin service access, anonymous end-to-end access, real
  compression and cache headers, and clean-browser verification all remain
  outstanding.
- Vercel account state, plan, eligibility, and the prebuilt deploy path.
- Loading on a slow connection or a low-end device, and combined behaviour once
  the vessel and exposure layers exist.
- Non-Chrome browsers. Only headless Chrome was exercised.
- The M3 follow-up carried into M5: GDAL/Pyogrio read-back of the derived
  GeoParquet for ArcGIS publishing compatibility. **This slice does not close
  it**, but it does reduce its urgency: the display route reads GeoParquet with
  PyArrow and publishes GeoJSON, and QGIS read the exported GeoJSON through OGR
  without difficulty, so the local `duckdb.dll` driver problem does not block
  this delivery path.
- The authenticated ArcGIS account capability checks M4 requires.

**Not attempted, deliberately:** no deployment, no public upload, no GitHub App
installation, no account change, no publishing, no billing, no paid service, no
credential value displayed or committed, no VSR snapshot or derived VSR geometry
copied into any public asset, no heavy analytical processing, and no change to
the analytical grid, the whale-transfer method, or the vessel engine.

---

## Next vessel-layer integration slice

The final vessel artifact was inspected read-only for scoping. Identities, from
`socal-whale-vessel-risk-accessais-july-month\data\derived\m3-production-vessel-repeat-attempt2\`:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `vessel-grid.parquet` | 1,346,787 | `5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0` |
| `quality-report.json` | 36,512 | `4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7` |

Both match the identities recorded in `analysis/README.md` for the 2026-09-05
production run.

**Measured facts that shape the slice**

- Contract `production_vessel_input_v1`, schema version 1, EPSG:3310, 4,516
  rows, 46 columns.
- **Its `geometry`, `cell_id`, and `water_area_km2` columns are byte-identical
  to the whale grid's.** The vessel export can reuse the same transformation and
  will produce identical geometry, so a shared display-geometry helper is
  worthwhile and the incremental transfer cost is only the properties.
- Eight speed columns carry nulls — 140 to 1,408 cells depending on the vessel
  group. **The whale exporter's contract forbids nulls**; a vessel exporter
  needs an explicit nullable-value contract, GeoJSON `null` properties, and a
  renderer and popup that say "not available" rather than showing zero.
- `vessel_km_all_commercial` totals 2,084,502.496 km, with 140 cells at zero
  and a maximum of 39,889.733 km. Density per water km² is strongly skewed:
  median 5.20, p90 31.65, p99 271.77, maximum 8,487.07. **Equal intervals will
  not work**; quantile or log breaks with a documented rationale are needed, and
  the rationale matters more here than it did for whale density.
- On the size arithmetic measured above — geometry and ids 2.23 MB, roughly
  150 KB per property — a vessel export publishing about ten properties lands
  near 3.7 MB raw and, at the whale layer's Brotli ratio, near 0.45 MB
  transferred. Two layers together would be roughly 0.85 MB transferred. That
  is a projection from this session's measurements, not a measurement of a
  vessel export.

**Scope for the next slice**

1. Extend the display-export boundary to `production_vessel_input_v1` with its
   own versioned contract, an explicit nullable-value policy, and its own
   documented public field selection. Reuse the transformation and serialization;
   do not fork them.
2. **Apply the accepted `receivers_50_nautical_miles` analytical domain at the
   analytical boundary, not in the browser.** The vessel grid spans the whale
   support water grid, which is wider than the accepted AIS domain. Cells
   outside the domain must not look like observed low traffic, and must not
   enter any headline statistic. The domain geometry is in
   `domain-candidate-masks.parquet`
   (`4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77`). A
   browser-side clip is not acceptable; qualification must come from validated
   downstream work.
3. Keep speed separate from activity, per ADR 0006. Do not blend the speed
   summaries into the activity symbology.
4. Carry NOAA OCM / Marine Cadastre and USCG attribution and the July–November
   2024 analytical period, the type-only commercial population, and the gap,
   implied-speed, and edge assumptions into the layer's disclosure.
5. Repeat this slice's verification shape: deterministic repetition, known-answer
   transformation and null-handling fixtures, checksum-bound QGIS inspection,
   the three viewports, a failed-request case, and a combined two-layer
   measurement.

**Out of scope for that slice:** exposure calculation, the exposure layer, and
inside-versus-outside statistics. Those are M6 and M7 and depend on work this
session did not touch.

---

## Proposed changes to owner documents, not made here

These were not made because this session does not own those documents. Each
needs coordination with whoever holds them.

| Document | Proposed change |
|---|---|
| `docs/development.md` | Add the display-export command and its arguments to the analysis command table; add a "Reviewing the exact display export in QGIS" procedure alongside the existing GeoParquet one; record that `web/public/layers/` is an ignored staging destination; add the Vercel requirements and the prebuilt-deploy path to **Deploying the application**. |
| `docs/roadmap.md` | Record under M5 that the whale input layer now has a verified public representation and local rendering, with the identities and dates above, while leaving M4 and M5 status unchanged and the remaining criteria explicitly open. |
| `docs/architecture.md` | Record the display-export boundary as the implemented project-derived publication path, and reconcile the "no route is implemented" wording. Also carries a stale description of the VSR integration as unimplemented, and its toolchain inventory should distinguish Calcite 5.1.2 from Maps SDK 5.1.20 — both carried over from the delivery assessment. |
| `analysis/README.md` | Add a "Modeled blue-whale display export" section documenting the contract, the command, the published and withheld fields, the destination safeguards, and the verified run and QGIS results recorded above. |
| `docs/decisions/` | A narrow ADR for the static same-origin GeoJSON display route once there is enough evidence to accept it, and a separate host decision. This session recommends the route but does not accept it. |
| `docs/development.md`, `docs/roadmap.md`, `docs/architecture.md`, `README.md`, `AGENTS.md` | The delivery assessment's correction still stands: current product-specific documentation says Location Platform hosted services are not shared publicly, which contradicts the 2026-08-31 inventory's `Everyone` claim. Owners should reconcile that and distinguish a token-free service from a visitor using a scoped browser key. |
| `docs/data-sources.md` | The delivery assessment noted the live NOAA AIS FAQ now identifies itself as a June 2026 revision where the register describes May 2026. Owner review, without replacing the retained source evidence. |
| `analysis/pyproject.toml` | Optionally add a `whale-vessel-whale-display-export` console script alongside the existing entries. Not added here: it is shared package configuration. |

---

## Reproducing this session's checks

From `analysis/`, with the environment created by `python -m uv sync --locked`:

```text
python -m uv run python -m whale_vessel_analysis.whale_display_export_cli --source "C:\Users\teche\socal-whale-vessel-risk-analytical-domain\data\interim\m2-domain-evidence\blue-whale-density-grid.parquet" --expected-source-sha256 421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62 --output "..\web\public\layers\blue-whale-density.geojson"
```

QGIS inspection, with `QT_QPA_PLATFORM=offscreen`, using QGIS's own interpreter:

```text
"C:\Program Files\QGIS 4.2.1\bin\python-qgis.bat" scripts\qgis_inspect_whale_display_export.py --export "..\web\public\layers\blue-whale-density.geojson" --sha256 831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154 --output-dir "..\data\interim\m5-whale-display-export\qgis-verification"
```

The browser check follows the pattern the earlier keyed-map verification
established: a local static server for `web/out`, then Playwright driving
installed Chrome at the three viewports. The server, the Playwright spec and
configuration, the loading-measurement script, the report, and the screenshots
are retained under ignored
`data/interim/m5-whale-display-export/browser-verification/` and are not
committed, matching how the earlier browser evidence was handled.

---

## Handoff state

The branch is committed and not pushed. The working tree contains no
uncommitted change other than ignored generated evidence. `main` was not
modified, and no other session's work was touched.

The next useful action is either the vessel display slice scoped above, or the
author-run Vercel trial and account checks listed above. They are independent
and can proceed in either order.
