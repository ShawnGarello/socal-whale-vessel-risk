# 0009 — Mount the ArcGIS SDK through client-only map components

**Status:** Accepted
**Date:** 2026-08-25

## Context

[ADR 0001](0001-accept-initial-architecture.md) settled on the ArcGIS Maps SDK
for JavaScript inside a Next.js and TypeScript application. It did not say how
the SDK is mounted, and there are two decisions inside that question.

**Which SDK surface.** The SDK has historically been used by constructing a
`MapView` in code and attaching it to a DOM node. Since version 5.0 the SDK's
widgets are deprecated and its web components — `arcgis-map`, `arcgis-zoom`, and
the rest of the map, charts, and Calcite component libraries — are the path Esri
documents and supports going forward. Version 5.1.20 was current when this was
written.

**Where it initializes.** The components are custom elements. Importing one
registers it against `window.customElements`. Next.js prerenders pages during
`next build` in Node, where `window` does not exist, so anything that touches
the SDK at module scope on the server breaks the build.

Two further facts came out of running it in a browser rather than reasoning
about it:

- Left at its default, the SDK answers a rejected request by opening its own
  username and password dialog and waiting. In an anonymous public application
  that reads only publicly shared content, a missing or unauthorized API key
  therefore appeared as an indefinite loading state with a sign-in prompt over
  it — the worst possible failure mode, because it looks like a slow network.
- The SDK does not time out on its own, and not every failure raises an event.

## Decision

The map is mounted through the SDK's web components, initialized only in the
browser:

- `arcgis-map` and `arcgis-zoom` from `@arcgis/map-components`, with
  `@arcgis/core` and `@esri/calcite-components` as their required peers. No
  widgets, and no programmatic `MapView` construction.
- The component that imports them is isolated behind `next/dynamic` with
  `ssr: false`, so no SDK code is evaluated during the prerender or shipped in
  the initial HTML. That boundary lives in its own Client Component, because
  `ssr: false` is only permitted inside one.
- SDK assets are loaded from the ArcGIS CDN, which is the default for the npm
  packages since 4.34. Assets are not copied into the repository.
- `esriConfig.request.useIdentity = false`, so a rejected request fails
  immediately instead of prompting for a sign-in that will never come.
- Initialization is bounded by an explicit timeout, and the component reports
  three distinct states: loading, ready, and initialization failed. A view that
  becomes ready with a failed resource inside it is reported too, rather than
  shown as an empty map that looks like it worked.
- Cleanup relies on the component's documented default: `autoDestroyDisabled` is
  false, so disconnecting the element from the document destroys the view and
  its resources. Setting that flag without also calling `destroy()` would leak.

## Consequences

- The application follows the SDK's current supported surface, so it does not
  start life on a deprecated API that a later milestone would have to migrate.
- The SDK never runs on the server. Nothing about the map appears in the
  prerendered HTML, which is correct — there is nothing meaningful to prerender
  about a WebGL map.
- The map cannot render before JavaScript loads, and the initial HTML contains
  only the shell. For this application that is the honest representation; there
  is no static fallback for an interactive map worth pretending otherwise.
- Every future map feature — layers, legends, popups, the results panel — is
  added inside the same client boundary. Anything needing the SDK must live
  behind it, and that constraint should be stated when those milestones start.
- Loading assets from the ArcGIS CDN means the deployed application depends on
  `js.arcgis.com` being reachable. This suits a public portfolio deployment. An
  offline or network-restricted environment would need assets copied locally and
  `assetsPath` configured, which would be a change to this record.
- Turning identity off means the application can never prompt a visitor to sign
  in. That is intended for Version 1, which serves only publicly shared content.
  If a later version ever needs authenticated access, this is the line to
  revisit — and it should be revisited deliberately, because the default
  behaviour is worse than useless in a public app.

## Alternatives considered

**Programmatic `MapView` construction in a `useEffect`.** The long-standing
pattern, and it gives very direct control over the lifecycle. Rejected because
5.0 deprecated the widgets that pattern is normally paired with, it requires
importing the core stylesheet manually, and it means writing lifecycle code that
the component already implements and Esri already maintains.

**Loading the SDK from the CDN with a `<script>` tag and `$arcgis.import()`.**
Removes the SDK from the local build entirely and shrinks the export
substantially. Rejected because it forfeits TypeScript checking across the SDK
surface — which is most of the value of the TypeScript decision in
[ADR 0001](0001-accept-initial-architecture.md) — and makes the version a string
in a template rather than a locked dependency.

**Rendering the map on the server.** Not possible in any useful sense. The SDK
needs WebGL and a real DOM.

**Copying SDK assets into the repository.** The documented approach for
disconnected environments. Rejected as unnecessary here, and it would add a
build step and a large amount of committed or generated content for no benefit
to a public deployment.
