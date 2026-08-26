# 0008 — Deliver the application as a static Next.js export

**Status:** Accepted
**Date:** 2026-08-25

## Context

[ADR 0001](0001-accept-initial-architecture.md) accepted an architecture in
which every analytical result is computed offline and published, and the browser
only presents and filters. [architecture.md](../architecture.md) describes the
deployment model as "a static or statically-rendered Next.js build" and rules
out an application server for Version 1.

That left a real choice at implementation time. Next.js runs happily as a Node
server, and most hosting platforms deploy it that way by default. Choosing the
server mode would not have broken anything immediately — it would simply have
left the door open. Server Components, route handlers reading a request, and
server actions are all available in that mode, and any one of them could quietly
introduce server-side work that the architecture says must not exist.

Next.js 16.3.3 supports a full static export through `output: "export"`, which
writes plain HTML, CSS, and JavaScript and makes the server-dependent features
build errors rather than options.

## Decision

The application is built as a static export. `web/next.config.ts` sets:

- `output: "export"` — the build writes a complete static site to `web/out/`.
- `trailingSlash: true` — routes emit `out/<route>/index.html`, so hosts that do
  not rewrite extensionless URLs still resolve them.
- `images: { unoptimized: true }` — `next/image` optimization needs a server.

`next start` is removed from the scripts, because it serves a Node build and
would misrepresent how this application is deployed.

## Consequences

- The architecture's "no backend, no server-side analytical processing" rule is
  enforced by the build rather than by discipline. Reaching for cookies, request
  headers, rewrites, redirects, incremental static regeneration, server actions,
  or a request-reading route handler fails the build, at the moment it is
  written, with the reason attached.
- The deployment surface is as small as it gets: any HTTPS static host will do,
  and hosting is cheap, fast, and hard to break.
- Every `NEXT_PUBLIC_` environment variable is inlined at build time. Changing
  one requires a rebuild and redeploy — configuration cannot be adjusted on a
  running deployment. The deployment platform must therefore support build-time
  environment variables.
- The build output is roughly 30 MB across several hundred files, almost all of
  it ArcGIS Maps SDK chunks. That is on-disk size, not download size — the SDK
  is code-split — but it does constrain which hosts are usable, so file-count
  and size limits have to be checked when the platform is chosen.
- If Version 1 ever genuinely needs server-side work, this record is superseded
  rather than edited, and [ADR 0001](0001-accept-initial-architecture.md) is
  reconsidered with it — because the constraint originates there, not here.

## Alternatives considered

**Next.js in its default server mode, deployed to a Node host.** Rejected. It
gives the application capabilities the architecture explicitly excludes, and
nothing in Version 1 needs them. The value of the static export is precisely
that the excluded capabilities stop being available.

**A single-page application with no framework, or a lighter build tool such as
Vite.** Would work, and would produce a smaller toolchain. Not chosen because
[ADR 0001](0001-accept-initial-architecture.md) already settled on Next.js and
TypeScript, and re-opening that on implementation-detail grounds would be
churn. Nothing found while building the shell argues against Next.js here.

**Server-side rendering of the map.** Not viable, and not desirable. The ArcGIS
Maps SDK is a browser library that needs WebGL and a real DOM; there is nothing
useful to render on a server. See
[ADR 0009](0009-mount-arcgis-through-client-only-map-components.md).
