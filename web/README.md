# web

The Next.js and TypeScript application for the SoCal whale–vessel spatial
overlap project. It is a presentation layer only: no backend, no database, and
no analysis runs here.

The map client uses the ArcGIS Maps SDK for JavaScript and is designed to read
ArcGIS platform services and authorized items through a scoped browser API key.
Local API-key-backed access to the `arcgis/oceans` basemap, pan/zoom, and the
ready-map attribution handoff were verified in Chrome at the three required
viewports on 2026-08-31. That historical credential returned `Token Invalid`
during the 2026-09-06 vessel/domain check, so the current integration check used
the unkeyed public `topo-vector` basemap and retained the application's visible
missing-key warning. Deployed-origin access remains unverified, and neither
local result establishes account or project-layer hosting capabilities. The
author's real account controls, billing state, usage, and free-tier headroom
remain unverified because no authenticated session was available for the
read-only inventory, and no hosted-feature test has been performed. Paid usage
is not authorized.

Project-derived layers are delivered here as static same-origin files served
alongside the export, so they need no layer credential and no hosted service.
That is what this application implements and what has been verified locally; it
is **not** an accepted hosting decision. The public host for those files, and
whether an ArcGIS Location Platform or ArcGIS Online service is preferable to
static delivery for the remaining layers, are still open decisions that belong
to the roadmap and to a decision record.

## Modeled blue-whale density layer

The map draws this project's own modeled blue-whale density grid from a
deterministic WGS 84 GeoJSON export of the validated
`blue_whale_grid_transfer_v1` analysis output. The Python
`blue_whale_display_export_v1` boundary produces that file; this application
only displays it. No value is recomputed, rescaled, rounded, or reclassified in
the browser.

The layer is an ArcGIS `GeoJSONLayer` whose geometry type, spatial reference,
object-id field, and field schema are declared explicitly rather than inferred
from the file, so an altered or truncated export fails to load instead of
rendering with a silently different schema. Loading is independent of the
basemap and every other operational layer, is bounded to 30 seconds, verifies
the expected 4,516 grid cells before the layer is called ready, and removes a
failed layer while leaving an accessible warning. One shared project-GeoJSON
lifecycle applies those controls to the whale, vessel, and domain files without
merging their state. Each async continuation proves that its effect execution is
still active before updating state, creating a Blob URL, assigning a layer ref,
or adding a layer. Cleanup aborts pending work and releases only its own URL and
layer, so an older request cannot interfere with a replacement. A deterministic
reorder keeps the whale and vessel fills below the domain and publisher VSR
outlines, regardless of asynchronous completion order.

`web/lib/whale-source.ts` binds this build to one exact artifact: export
SHA-256 `831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154`,
derived from analysis output
`421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62`. If the
export changes, that file changes with it in the same release.

**That identity is verified, not merely recorded.** The layer URL is build-time
configurable and a feature count is not an identity, so a different file with
4,516 features would otherwise be displayed under this build's checksum. The
application therefore fetches the file itself, hashes the bytes with
`SubtleCrypto`, and creates the layer from a blob built from those exact bytes
— one download, and the file that was hashed is necessarily the file that is
drawn. A mismatch fails the layer with its own message rather than rendering
unknown bytes. `SubtleCrypto` needs a secure context, which HTTPS and localhost
both provide; anywhere else the interface says the identity is unverified
instead of claiming otherwise.

**Symbology is a stated display choice, not a result.** Five equal
0.001 animals/km² classes with an open lowest and highest class, on a
single-hue purple ramp kept clear of the blue basemap and the orange VSR
outline. Against the exported surface (0.000834 to 0.007648 animals/km²) the
classes hold 1,103 / 1,388 / 765 / 527 / 733 of the 4,516 cells, so no class is
empty and none dominates. The legend states the unit; the panel's disclosure
carries the NOAA/SWFSC source, the requested Becker et al. and InPort
citations, the transfer method, the retrieval date, and the artifact
checksums. Per-cell popups report modeled density, allocated modeled abundance,
supporting water area, and source-model support, each with its unit, alongside
the statements that the values are modeled rather than observed and that the
layer asserts no exposure, collision probability, or strike risk.

Generated layer data is never committed. The exporter stages its GeoJSON and
sanitized manifest into the Git-ignored `public/layers/` directory, which
`next dev` and `next build` then serve from the same origin.
`NEXT_PUBLIC_WHALE_LAYER_URL` overrides that location at build time for a
release that publishes a checksum-addressed filename. The vessel and domain
sections below document their corresponding URL settings.

### Verified locally on 2026-09-06

The keyed production/static export was served from the authorized
`http://localhost:3000` origin and checked in headless Google Chrome at exact
390 × 844, 820 × 1180, and 1440 × 900 CSS-pixel viewports. At every size the
whale layer loaded with exactly 4,516 features, polygon geometry, WKID 4326,
the declared `object_id` object-id field, and a five-class breaks renderer; the
map held exactly one whale layer and one VSR layer, whale at index 0 and VSR at
index 1; the density legend, its unit, and all five class labels were readable
without opening anything; the visibility control hid and restored the layer;
keyboard traversal gave the control a visible three-pixel focus outline; the
source-and-method disclosure was reachable; a map click opened a popup whose
displayed values matched the exported analytical values exactly at the declared
precision; and the disclosure reported the export checksum as verified against
the bytes the browser had loaded. Neither the document nor the body overflowed
horizontally, the SDK attribution stayed visible and inside the viewport, and
the sanitized console recorded no console error, page error, HTTP error, or
request failure.

The SDK's dynamic attribution carried the whale layer's own credit alongside
the Esri and basemap provider credits. It appears once the layer view is
created, shortly after the layer itself reports loaded.

A separate 820 × 1180 check blocked only the whale GeoJSON request. The
application removed the failed layer, showed its concise accessible warning
naming the basemap and VSR boundary as still available, kept the VSR layer
loaded and the map ready, and produced no indefinite loading state and no
sign-in prompt. The only console output was the blocked request itself: because
the application fetches and verifies the file before creating the layer, the
SDK never attempts a load that could fail.

A further 1440 × 900 check served a _different_ file that still contained 4,516
features. The checksum did not match, so the layer was refused with its own
distinct message, the VSR boundary and basemap stayed usable, and the interface
did not claim a verified identity. The console was clean — the refusal is
deliberate, not an error.

Verification screenshots, browser evidence, and QGIS renders remain under the
ignored local data root and are not committed.

## Commercial vessel activity and accepted analytical domain

The vessel surface is a deterministic WGS 84 GeoJSON presentation of the
accepted `production_vessel_input_v1` artifact. It displays retained passenger,
cargo, and tanker movement from 1 July through 30 November 2024 as
vessel-kilometres per km² of complete source-cell modeled-whale-support water.
It does not display speed and does not calculate exposure. Activity values are
copied unchanged; where the receiver-qualified boundary crosses a cell, the
geometry is clipped exactly in EPSG:3310 and the complete source-cell value is
retained with its displayed fraction. That avoids implying an unsupported
within-cell redistribution.

The companion boundary is the exact accepted
`receivers_50_nautical_miles` feature: modeled-whale-support water within 50
nautical miles, exactly 92,600 metres, of the relevant NAIS reception stations.
It is not measured from the coast and is not empirical 2024 reception coverage.
The dashed cyan boundary and explicit legend note make water outside it an
excluded area, not low or zero vessel activity. The broader map/context extent,
modeled-whale-support water, and accepted analytical domain remain separate
spatial roles.

`web/lib/vessel-source.ts` and `web/lib/domain-source.ts` bind the application
to these exact files and inputs:

| Identity                       | SHA-256                                                            |
| ------------------------------ | ------------------------------------------------------------------ |
| Vessel GeoJSON, 2,793 features | `3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288` |
| Production vessel input        | `5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0` |
| Vessel quality report          | `4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7` |
| Domain GeoJSON, one feature    | `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf` |
| Domain candidate-mask artifact | `4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77` |
| Domain evidence report         | `eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98` |

The vessel legend uses a separate neutral zero class followed by fixed
intervals over 0–1, 1–5, 5–20, 20–100, and over 100 vessel-km/km². The
classes contain 137 / 381 / 674 / 1,019 / 381 / 201 cells respectively. These
are stated display intervals, not analytical categories. The zero label says
"zero retained movement" because successful processing and a zero value do not
verify vessel absence or AIS observational completeness.

The initial same-origin representation was measured before considering another
delivery route. The vessel file is 2,720,788 bytes (541,477 gzip; 385,764
Brotli) and the domain file is 867,910 bytes (265,035 gzip; 199,834 Brotli).
The existing whale file is 3,277,329 bytes (574,907 gzip; 396,852 Brotli).
Those are local file/compression measurements, not deployed transfer claims.
`NEXT_PUBLIC_VESSEL_LAYER_URL` and `NEXT_PUBLIC_DOMAIN_LAYER_URL` can bind a
release to checksum-addressed URLs; the defaults remain the generated ignored
same-origin `public/layers/` files.

### Verified locally on 2026-09-06

QGIS 4.2.1 opened both exact GeoJSON files directly through OGR in EPSG:4326.
It found 2,793 vessel features (2,641 full cells, 152 partial cells, 137 with
zero retained movement), one domain feature, no empty or invalid geometry, and
no vessel geometry outside the accepted domain. All feature, polygon-part,
interior-ring, and vertex counts agreed with the manifests. Five
checksum-recorded views were visually reviewed at full, northern, southern,
coast/islands, and boundary-detail extents; the receiver-qualified boundary,
clipped cells, holes and islands, and vessel-activity corridors were spatially
coherent. The ignored QGIS report SHA-256 is
`2cfca5ca98e5de69b5feead7db6e5d8b9e3d276a6076f1a9c55e43bdce55a140`.

Headless Chrome 152 loaded the actual local application at 390 × 844, 820 ×
1180, and 1440 × 900 CSS pixels. At every viewport the browser verified the
three project checksums, loaded 4,516 whale cells, 2,793 vessel cells, the one
domain feature, and the one publisher VSR feature exactly once, and preserved
the intended layer order. Toggling vessel, whale, and domain visibility changed
the live layer properties without adding duplicates. The vessel surface,
qualified boundary, VSR reference, legends, units, excluded-area statement,
scrolling control panel, and SDK attribution were visually readable; body and
document had no horizontal overflow and keyboard focus retained a three-pixel
outline.

From a warm local development server, the three project layers reached ready
state 2.30–3.34 seconds after document completion. Local resource timings were
0.21–0.55 seconds per GeoJSON response; observed decoded sizes matched the
files, and transfer sizes reflected the development server's gzip responses.
Post-toggle JavaScript heap samples were 159–168 MB. These are local rendering
observations only, not deployed-performance claims.

Separate request-interception checks exercised an HTTP 404, malformed bytes
caught by the checksum, and an ArcGIS parse/load error with checksum support
artificially unavailable. In all three cases the failed vessel layer was
removed, its accessible warning remained, and the whale, domain, VSR, and map
stayed ready with exactly one copy each. The normal, missing-file, and
checksum-mismatch runs had no console errors; the forced 404 produced one
expected resource-log entry. The forced ArcGIS parse failure produced its two
expected console errors. The ignored browser report SHA-256 is
`8e9e1395539ccb0d2cdf18dedbb815effb555bf915184abc4a1a3352ee45501a`.

## Publisher-hosted VSR boundary

The map also loads the publisher-hosted 2026 California VSR boundary directly
from the public `WhaleAtlas_2026` Feature Service with the exact `FID = 126`
definition expression. Its source identity, expected one-feature response,
attribution, and use disclaimer are kept in a typed configuration module. The
application does not contain or persist the feature geometry. A checked native
visibility control, compact line legend, and inline source/use disclosure are
available from the map. VSR loading is independent of basemap initialization,
is limited to 15 seconds, and removes a failed layer while leaving the basemap
usable with an accessible warning.

On 2026-09-02 the keyed production/static export was served from the authorized
localhost origin and verified in headless Google Chrome at exact 390 × 844,
820 × 1180, and 1440 × 900 CSS-pixel viewports. At all three sizes the oceans
basemap and filtered boundary rendered in the correct Southern California
location; the visibility control hid and restored the layer; repeated ready
events left exactly one VSR layer; source and disclaimer content were reachable;
keyboard focus used a visible three-pixel outline; zoom controls and SDK
attribution remained unobscured; and neither the document nor body had
horizontal overflow. The publisher metadata and filtered query endpoints
returned HTTP 200, with no HTTP errors or unexpected request failures. The
sanitized console contained only the Calcite version information.

A separate 820 × 1180 failure check blocked only the publisher service. The
application removed the failed VSR layer, showed its concise accessible warning,
and retained a ready, non-updating oceans basemap with working zoom controls and
SDK attribution. No sign-in prompt or indefinite layer-loading state appeared.
The blocked request produced the expected inspector-blocked network failure and
two expected ArcGIS SDK console errors identifying FeatureLayer load and
LayerView creation failure. Verification screenshots and browser evidence remain
under the ignored local data root and were not committed.

The application shows a durable `Powered by Esri` attribution while the SDK is
loading and whenever the map cannot initialize. Once a map view is ready, the
SDK's default attribution replaces that fallback so its Esri and data-provider
credits remain automatic and responsive to the visible map without presenting
duplicate attribution. This follows Esri's current
[licensing and attribution guidance](https://developers.arcgis.com/javascript/latest/licensing/)
and the ArcGIS map component's default
[automatic attribution behavior](https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-map/).

Commands, required environment variables, and the deployment requirements are
documented in [../docs/development.md](../docs/development.md). The design this
application implements is in [../docs/architecture.md](../docs/architecture.md).

Do not restate commands or configuration in this file — `docs/development.md`
owns them, and a copy here will drift.
