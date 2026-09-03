# web

The Next.js and TypeScript application for the SoCal whale–vessel spatial
overlap project. It is a presentation layer only: no backend, no database, and
no analysis runs here.

The map client uses the ArcGIS Maps SDK for JavaScript and is designed to read
ArcGIS platform services and authorized items through a scoped browser API key.
Local API-key-backed access to the `arcgis/oceans` basemap, pan/zoom, and the
ready-map attribution handoff were verified in Chrome at the three required
viewports on 2026-08-31. Deployed-origin access remains unverified, and this
local basemap result does not establish account or project-layer hosting
capabilities. Current official documentation confirms that Location Platform
can create feature, vector-tile, and map-tile services and can share them for
anonymous public access without a separate ArcGIS Online organization. The
author's real account controls, billing state, usage, and free-tier headroom are
still unverified because no authenticated session was available for the
read-only inventory. Project layers will use the public representation selected
after real output, performance, redistribution, and account evidence exists.
Candidates remain Location Platform limited data services, ArcGIS Online
organization-hosted layers if needed, and a non-Esri public fallback. No route
is implemented, no hosted-feature test has been performed, and paid usage is not
authorized.

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
