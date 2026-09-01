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
