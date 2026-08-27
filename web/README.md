# web

The Next.js and TypeScript application for the SoCal whale–vessel spatial
overlap project. It is a presentation layer only: no backend, no database, and
no analysis runs here.

The map client uses the ArcGIS Maps SDK for JavaScript and is designed to read
ArcGIS platform services and authorized items through a scoped browser API key.
Successful API-key-backed access remains unverified. Project layers will use the
public representation selected after real output, performance, redistribution,
and account-type evidence exists. Candidates are ArcGIS
Location Platform limited feature/vector-tile/map-tile services, ArcGIS Online
organization-hosted layers, and a non-Esri public fallback if neither is
suitable. No route is implemented, and paid usage is not authorized.

Commands, required environment variables, and the deployment requirements are
documented in [../docs/development.md](../docs/development.md). The design this
application implements is in [../docs/architecture.md](../docs/architecture.md).

Do not restate commands or configuration in this file — `docs/development.md`
owns them, and a copy here will drift.
