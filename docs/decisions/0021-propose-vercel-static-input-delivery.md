# 0021 — Propose Vercel static input delivery

**Status:** Proposed; author agreement and deployment approval pending
**Date:** 2026-09-07

## Context

The author prefers a free Vercel deployment of the existing application. Three
validated input GeoJSON files total 6,866,027 bytes and already support the
required local interactions. Their generation manifests are sanitized public
metadata. The browser verifies their hashes. A repository-only host build would
omit these ignored files. No exposure integration or final-results release is
part of this decision.

## Proposed decision

Use Vercel Hobby, conditional on the author's actual plan and personal-use
eligibility, for the static application and its three input layers. Build
committed source locally with locked npm dependencies, include only the pinned
input GeoJSON/manifest pairs, and prepare the documented Build Output API v3
static directory for an explicitly approved CLI prebuilt upload. No GitHub
integration, server functions, storage service, paid resource or CI deployment.

Keep the basemap account separate: verify its product, billing, available
basemap capacity and scoped/referrer-restricted key. Keep publisher VSR access
separate under ADR 0019. Project-derived static files require neither an Esri
publishing account nor a visitor credential.

Propose making the temporary Esri publish-and-serve test conditional on actually
selecting Esri project-data hosting. Require deployed checksum-verified access
to the selected static representation instead. Creating an unused hosted item
would prove an alternative route, while introducing item access, usage and
cleanup work that this delivery does not need. Unselected Esri data-service
capabilities would remain explicitly unverified, not unavailable or satisfied.
This proposal also narrows mandatory account checks to capabilities the selected
route uses; it requires explicit author agreement before changing M4.

**The existing M4 criteria remain authoritative until that agreement.** This
proposal neither waives them nor authorizes deployment. Current account state,
Hobby eligibility, release key access and production-origin verification remain
unresolved. Development owns provider references and operational steps.

## Consequences and alternatives

Generated spatial files remain ignored, and each retained release has an exact
application commit and file inventory. A previous complete package can be
uploaded again for rollback. The publisher controls VSR availability; the
initial input-layer check does not satisfy the snapshot comparison required
before statistics are publicly presented against that boundary.

An Esri hosted service remains a future option if measured needs justify it.
It is unnecessary for these small, locally verified static inputs. A remote
Git-only build is unsuitable without explicit artifact delivery. Vercel's
framework-aware `vercel build` requires project setup before its behavior can
be tested; assembling the documented static output directly makes local
preparation possible before account operations. Provider acceptance and actual
headers still require the approved deployment test.
