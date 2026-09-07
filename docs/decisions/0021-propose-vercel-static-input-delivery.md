# 0021 — Use Vercel static input delivery

**Status:** Accepted; deployment approval pending
**Date:** 2026-09-07

## Context

The author prefers a free Vercel deployment of the existing application. Three
validated input GeoJSON files total 6,866,027 bytes and already support the
required local interactions. Their generation manifests are sanitized public
metadata. The browser verifies their hashes. A repository-only host build would
omit these ignored files. No exposure integration or final-results release is
part of this decision.

## Decision

Use Vercel Hobby, conditional on verifying the author's actual plan and
personal-use eligibility, for the static application and its project-derived
static layers. Build
committed source locally with locked npm dependencies, include only the pinned
application-required artifacts and public manifests, and prepare the documented Build Output API v3
static directory for an explicitly approved CLI prebuilt upload. No GitHub
integration, server functions, storage service, paid resource or CI deployment.
The entire project remains free: paid plans, trials, add-ons, pay-as-you-go and
other charged usage are prohibited. If verified free eligibility, capacity or
service access is unavailable, deployment stops and the delivery decision must
be revisited without selecting a paid fallback.

Keep the basemap account separate: verify its product, billing, available
basemap capacity and scoped/referrer-restricted key. Keep publisher VSR access
separate under ADR 0019. Project-derived static files require neither an Esri
publishing account nor a visitor credential.

The temporary Esri publish-and-serve test is conditional on actually selecting
Esri project-data hosting. The selected static route instead requires deployed
checksum-verified access to the selected static representation. Creating an
unused hosted item would prove an alternative route, while introducing item
access, usage and cleanup work that this delivery does not need. Unselected Esri data-service
capabilities would remain explicitly unverified, not unavailable or satisfied.
Mandatory account checks cover capabilities the selected route uses: Vercel
Hobby plan and eligibility, and the ArcGIS basemap account's product, billing,
free-tier headroom, browser-key scope and exact origin restrictions. ArcGIS
hosted-data creation, storage, sharing and ArcGIS Online organization privileges
are outside M4 unless a later accepted decision selects them.

Acceptance does not authorize deployment or any account change. Actual account
state, Hobby eligibility, basemap capacity, key scope, referrers, release-key
access and production-origin verification remain unverified. Development owns
provider references and operational steps.

## Consequences and alternatives

Generated spatial files remain ignored, and each retained release has an exact
application commit and file inventory. A previous complete package can be
uploaded again for rollback. The publisher controls VSR availability; the
initial input-layer check does not satisfy the snapshot comparison required
before statistics are publicly presented against that boundary.

An Esri hosted service would require a later superseding decision supported by
measured need and verified free capability. It is unnecessary for the small,
locally verified static inputs. A remote
Git-only build is unsuitable without explicit artifact delivery. Vercel's
framework-aware `vercel build` requires project setup before its behavior can
be tested; assembling the documented static output directly makes local
preparation possible before account operations. Provider acceptance and actual
headers still require the approved deployment test.
