# 0019 — Reference the publisher-hosted VSR service

**Status:** Accepted
**Date:** 2026-09-02

## Context

Version 1 needs the 2026 California Vessel Speed Reduction (VSR) boundary in
two places with different requirements. Reproducible inside-versus-outside
analysis needs a fixed input whose byte identity and retrieval date do not
change underneath a rerun. The public application needs a visible boundary,
but publishing a project-controlled copy would require a redistribution
posture that the source evidence does not provide.

BWBS/CMSF publicly shares ArcGIS item
`b400c7f418b04dc5a9d7ce5015adae32`. Its public Feature Service exposes the
California VSR feature as `FID = 126` at:

`https://services5.arcgis.com/4biRnCjZju47bNvA/arcgis/rest/services/WhaleAtlas_2026/FeatureServer/0`

The item identifies Danielle Alvarez, the California Marine Sanctuary
Foundation (CMSF), and Protecting Blue Whales and Blue Skies (BWBS), and carries
a non-navigational use disclaimer. Public anonymous access is not an explicit
licence to redistribute the geometry. No explicit redistribution grant has
been found.

## Decision

Version 1 separates the VSR analytical input from the VSR display source:

- Python analysis uses the exact immutable VSR snapshot retrieved on
  2026-08-25 and retained under ignored `data/raw/`. That snapshot is the
  geometry used for reproducible fractional inside-versus-outside calculations.
- The snapshot, and every copied, clipped, simplified, converted, or otherwise
  derived VSR geometry, remains local. This project must not commit or publish
  a project-controlled copy.
- The public application loads the publisher's public Feature Service directly
  and applies `FID = 126`. The remote layer appears inside the project's map;
  visitors are not redirected to another application.
- Application attribution must identify Danielle Alvarez, CMSF, and BWBS as
  specified by the publisher's item. The publisher's non-navigational
  disclaimer must remain available with the displayed layer, including that
  the layer should not be used for navigation, mariners retain responsibility
  for navigation, the measures may not be comprehensive, and omission does not
  establish the absence of a VSR zone, Area to Be Avoided, or Traffic
  Separation Scheme.
- Version 1 has no automatic synchronization or continuous-monitoring service.
  Before final release, an anonymous check must confirm that the expected item,
  layer, and `FID = 126` still exist and must compare the then-current source
  state with the retained analytical snapshot.
- If the publisher changes the geometry after the analytical snapshot, the
  release must either rerun or reconcile the analysis against the changed
  source, or state clearly that the remotely displayed boundary is not the
  version that produced the statistics. It must not silently imply a match.

This is a conservative no-copy architecture, not a legal conclusion. Permission
to redistribute remains unconfirmed. Permission would need to be established
only if a later version chooses to host a project-controlled copy or derivative
of the VSR geometry.

## Consequences

- The VSR publication question no longer requires an affirmative redistribution
  grant for Version 1 because Version 1 does not redistribute the geometry.
- The VSR layer is a selected exception to the provider-neutral publication
  boundary used for project-derived whale, vessel, and exposure layers. Their
  public representations and hosts remain undecided.
- The analytical result remains reproducible from a frozen local input even if
  the publisher later edits or removes the public service.
- Display availability and version are controlled by the publisher. The service
  can change, disappear, be rate-limited, or become private, and a live display
  can drift from the analytical snapshot.
- Release verification is intentionally manual and proportionate to this
  portfolio project. A monitoring service, synchronization job, backend, or
  scheduler is not introduced.

## Alternatives considered

**Publish the retained snapshot or a processed copy.** Rejected for Version 1.
No explicit redistribution grant has been found, and public access to the
publisher's service is not treated as such a grant.

**Ask the publisher for permission before release.** Not required for the
selected no-copy route. It becomes relevant if the project later decides to
host a copy.

**Construct a new polygon from the published points and a shoreline.** Rejected.
It would introduce project-chosen closure and shoreline assumptions at the
boundary used for the headline comparison, while still creating a
project-controlled geometry.

**Automatically mirror or monitor the source.** Rejected as disproportionate.
Release-time anonymous availability and version comparison address the relevant
Version 1 failure modes without adding an operational service.
