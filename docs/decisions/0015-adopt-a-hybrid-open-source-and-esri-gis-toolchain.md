# 0015 — Adopt a hybrid open-source and Esri GIS toolchain

**Status:** Accepted
**Date:** 2026-08-27

## Context

[ADR 0001](0001-accept-initial-architecture.md) accepted an initial architecture
that divided offline processing between ArcGIS Pro and Python and assumed that
validated layers would be hosted in ArcGIS Online. Those assumptions now need
refining without rewriting the historical record of what was known when ADR
0001 was accepted.

ArcGIS Pro is paid software and is unavailable to this project. It has not been
a prerequisite for the implemented work: the Python package already provides
the reproducible processing foundation, deterministic outputs, tests,
configuration, and lineage. On 2026-08-27, QGIS 4.2.1 successfully opened and
visually verified the exact generated EPSG:3310 GeoParquet containing 4,516
MultiPolygon features, with no conversion step.

The public application also has a direct Esri boundary that does not require
ArcGIS Pro. The implemented Next.js shell uses the ArcGIS Maps SDK for
JavaScript. ArcGIS Location Platform provides location services and a limited
single-user organization that can create hosted feature, vector-tile, and
map-tile data services. Its storage and bandwidth use a monthly free tier with
optional pay-as-you-go billing. Those capabilities make it a candidate Esri
host for project layers as well as a source of API-key-accessible basemap and
other location services. The account's actual service, storage, bandwidth,
free-tier, and billing status remain unverified. See Esri's
[portal and data services FAQ](https://developers.arcgis.com/documentation/portal-and-data-services/faq/).

ArcGIS Online organization hosting is a different capability boundary. The
available account's organization access, publishing privileges, public-sharing
permission, hosted feature, tile, and imagery support, credits, and storage
have not been checked. None may be assumed available or unavailable. Requiring
all project layers to be hosted there would therefore make Version 1 depend on
unknown paid-account capabilities rather than on the analytical and application
work the repository controls.

## Decision

Version 1 uses a hybrid open-source and Esri GIS toolchain with these
responsibilities:

- **Python** is the reproducible processing and analytical core. It owns source
  validation, deterministic transformations, tests, configuration, lineage,
  derived analytical outputs, and summary statistics.
- **QGIS** is the local GIS inspection, exploratory-review, cartographic-review,
  and visual-verification tool. A result may not depend on an unrecorded manual
  edit or transformation performed in QGIS.
- A **provider-neutral publication boundary** follows programmatic and visual
  validation. It exports or prepares validated artifacts for the delivery
  representation selected from evidence; publication does not change the
  analysis.
- **ArcGIS Online hosted layers** remain an allowed publication option when a
  real account check establishes the required organization, publishing,
  public-sharing, service-type, credit, and storage capabilities.
- **ArcGIS Location Platform hosted data services** are a separate publication
  candidate. They are limited to feature, vector-tile, and map-tile services
  and are usable only when actual output compatibility, public access, storage,
  bandwidth, monthly free-tier headroom, and billing status are verified. This
  project does not enable pay-as-you-go billing or authorize spending.
- If neither Esri-hosted route is available or suitable, Version 1 may use
  another publicly accessible static or otherwise supported layer-delivery
  method that the ArcGIS Maps SDK for JavaScript can consume. No non-Esri
  fallback format or provider is selected by this decision.
- **Next.js and the ArcGIS Maps SDK for JavaScript** remain the public
  application and map client.
- **ArcGIS platform services and items**, accessed from the browser through a
  minimally scoped and origin-restricted API key, remain the intended Esri
  integration where available. ArcGIS Location Platform accounts have API-key
  management privileges by default; ArcGIS Online has different account and
  privilege requirements. See Esri's
  [API-key authentication documentation](https://developers.arcgis.com/documentation/security-and-authentication/api-key-authentication/).
- **ArcGIS Pro is optional and unnecessary for Version 1.** It is neither a
  missing prerequisite nor a planned repository component.

The final public layer representation is still deferred. It will be selected
after real output size, geometry or raster characteristics, browser performance,
redistribution constraints, and actual account capabilities are measured. This
decision does not prematurely choose GeoJSON, vector tiles, hosted feature
layers, hosted imagery, or any other representation.

## Consequences

- The project remains finishable without ArcGIS Pro or a repository-owned
  ArcGIS Pro project.
- Python remains the authoritative production path. QGIS supplies required
  spatial validation and useful exploration, but does not become an
  undocumented processing pipeline.
- ArcGIS Location Platform limited data services and ArcGIS Online organization
  hosting remain separate Esri-hosted candidates. The architecture assumes
  neither. Account-type-specific evidence constrains or selects the publication
  route instead of deciding whether the analysis can exist.
- The final delivery representation remains open until measured output size,
  browser performance, redistribution constraints, and real account evidence
  support a choice. A fallback delivery route must be designed and verified
  later if neither Esri-hosted publication route is selected.
- The project keeps direct Esri relevance through the ArcGIS Maps SDK for
  JavaScript and available ArcGIS platform services, even if project layers are
  delivered through a non-Esri fallback.
- Generation-time lineage must not be manually edited. Later visual verification
  is separate evidence tied to the exact output checksum. Under the current
  implementation, an explicitly authorized overwrite replaces the output and
  sidecar without retaining prior run evidence automatically; append-only or
  versioned lineage remains future work.

## Alternatives considered

**Require ArcGIS Pro.** Rejected. It is unavailable, paid, and unnecessary for
the deterministic processing already implemented in Python. Making it a
prerequisite would add cost without improving reproducibility.

**Require ArcGIS Online hosted layers.** Rejected as a universal requirement.
Hosted layers remain a strong option, but the relevant account capabilities are
unverified and should inform a publication choice rather than become an
unsupported assumption.

**Abandon Esri technology entirely.** Rejected. The ArcGIS Maps SDK for
JavaScript and available platform services remain meaningful parts of the
public application and the project's GIS portfolio value.

**Use manual QGIS processing as the production workflow.** Rejected. QGIS is
well suited to inspection, exploration, and visual verification, but
unrecorded manual transformations would violate the project's reproducibility
and lineage requirements.
