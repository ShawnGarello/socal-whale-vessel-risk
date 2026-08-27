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
JavaScript, and ArcGIS Location Platform services are intended to provide the
basemap and other API-key-accessible services where available. A successful
render with a real scoped browser API key remains unverified.

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
- If those capabilities are unavailable or unsuitable, Version 1 may use
  another publicly accessible static or otherwise supported layer-delivery
  method that the ArcGIS Maps SDK for JavaScript can consume. No fallback
  format or provider is selected by this decision.
- **Next.js and the ArcGIS Maps SDK for JavaScript** remain the public
  application and map client.
- **ArcGIS Location Platform services**, accessed from the browser through a
  minimally scoped and origin-restricted API key, are the intended basemap and
  service integration where available. This API-key boundary is distinct from
  authenticated ArcGIS Online organization publishing.
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
- ArcGIS Online hosting remains usable if verified, but the architecture does
  not assume it. The capability check constrains or selects the publication
  route instead of deciding whether the analysis can exist.
- The final delivery representation remains open until measured output size,
  browser performance, redistribution constraints, and real account evidence
  support a choice. A fallback delivery route must be designed and verified
  later if hosted ArcGIS Online publication is not selected.
- The project keeps direct Esri relevance through the ArcGIS Maps SDK for
  JavaScript and available ArcGIS platform services, even if project layers are
  delivered outside ArcGIS Online hosting.
- Generation lineage remains evidence of the generation run. Later visual
  verification is separate evidence tied to the exact output checksum; it does
  not require editing the generated lineage sidecar.

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
