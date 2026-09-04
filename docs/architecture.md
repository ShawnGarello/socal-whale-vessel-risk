# Architecture

**Owns:** system design, component boundaries, and deferred design decisions.

> **Status: accepted and refined.** [ADR 0001](decisions/0001-accept-initial-architecture.md)
> accepted the initial direction. [ADR 0015](decisions/0015-adopt-a-hybrid-open-source-and-esri-gis-toolchain.md)
> refines its tooling and publication assumptions after implementation and
> visual-verification evidence; it does not rewrite ADR 0001's historical
> context. [ADR 0019](decisions/0019-reference-the-publisher-hosted-vsr-service.md)
> selects direct use of the publisher-hosted VSR Feature Service as a narrow
> Version 1 exception to the project-derived-layer publication boundary.
>
> The Next.js application shell, Python processing foundation, deterministic
> one-extract AIS cleaning, projected water-grid construction, and deterministic
> whale-grid transfer are implemented and tested. Two clean whale-transfer runs
> produced byte-identical output, and QGIS 4.2.1 visually verified the exact
> generated water-grid and whale-grid GeoParquet artifacts. Local boundaries now
> verify and manifest one supplied AIS artifact and use bounded streaming to
> partition one author-supplied multi-date AccessAIS CSV or safe ZIP into
> deterministic daily cleaner inputs with resumable sequential period-manifest
> recording. The boundary was exercised with overlapping real one-day and
> two-day direct CSV deliveries, the seven-day operational gate, and the exact
> July monthly operational gate. Reordered equivalent daily content was reused,
> all 31 July dates reconciled, and the identical July retry reused every date.
> The July evidence passed independent audit, and the authorized August,
> September, October, and November months were then accumulated into the same
> period state: all 31 August, all 30 September, all 31 October, and all 30
> November dates reconciled, and each identical retry reused every date, so all
> 153 expected dates are recorded with no conflict and the shared manifest is
> `ready`. Publisher-side transfer
> and observational completeness remain unverified. Network retrieval remains
> unimplemented, and a complete cleaned-input period is not a vessel grid or an
> exposure result. Final period-wide vessel aggregation,
> exposure analysis, final public representations for project-derived layers,
> VSR service integration, and deployment also remain unfinished.
> See the [roadmap](roadmap.md) for milestone status.

The analytical and statistical domain is accepted in
[ADR 0002](decisions/0002-southern-california-study-area-extent.md), and the VSR
display route is accepted in ADR 0019. Python uses the immutable ignored local
VSR snapshot for analysis; the browser will display `FID = 126` directly from
the publisher's public Feature Service. The project will not commit or publish
a copy or derivative of that geometry. Permission to redistribute remains
unconfirmed; Version 1 avoids redistribution rather than treating public access
as a licence.

The publication route for the project's derived whale, vessel, and exposure
layers remains open. Official documentation confirms the Location Platform
product supports feature, vector-tile, and map-tile services and public
anonymous sharing under metered monthly free tiers. The author's actual account
product identity, controls, usage, remaining headroom, and billing state are
unverified because no authenticated session was available. ArcGIS Online
organization access is not applicable to the reported Location Platform branch
unless that product check fails. Account-specific evidence still constrains
that publication route; it does not determine whether the analysis can exist.

Changes to this accepted architecture are recorded under
[decisions/](decisions/README.md), not made silently.

---

## System context

The system has four kinds of participant:

- **Authoritative external publishers** — NOAA and the California BWBS program
  publish the whale distribution model, AIS vessel records, and VSR zone
  definition. They are read-only upstreams; provenance and verification status
  are owned by [data-sources.md](data-sources.md).
- **The author and local toolchain** — Python performs deterministic processing
  and analysis. QGIS inspects source and derived spatial artifacts and supplies
  visual-verification evidence. Local source and generated data are not
  committed.
- **Public publication services** — validated project-derived outputs cross a provider-neutral
  boundary into a publicly accessible representation. ArcGIS Location Platform
  limited data services and ArcGIS Online organization-hosted layers are
  separate Esri candidates. A non-Esri route remains available if neither fits.
  The VSR boundary is the Version 1 exception: the browser references the
  publisher's service directly instead of sending a copy across this boundary.
- **A visitor's browser** — a static Next.js application uses the ArcGIS Maps
  SDK for JavaScript to read public layers and available ArcGIS platform
  services. It presents and filters; it does not calculate exposure or reported
  statistics.

The load-bearing boundary is between analysis and presentation: every decision
that can change a reported number happens in the reproducible Python path. QGIS
inspection and publication may validate or represent an output, but may not
silently alter its analytical meaning.

## End-to-end data flow

```text
Authoritative sources
  NOAA whale distribution model
  NOAA / USCG AIS vessel records
  California BWBS VSR zone definition
        |                         `----> Publisher-hosted BWBS Feature Service
        v                                      |  FID = 126, display only
Local raw data store  (Git-ignored; inputs remain unchanged)
  immutable VSR snapshot for reproducible analysis          |
        |                                                    |
        v                                                    |
Deterministic Python processing and analysis                 |
  validate -> clean -> reproject -> grid/aggregate -> derive
  tests + versioned configuration + generation lineage
        |
        v
Validated derived artifacts and lineage
        |
        +----> QGIS inspection and visual verification
        |        separate checksum-bound evidence; no production edits
        |
        v
Provider-neutral publication / export boundary               |
  project-derived whale, vessel, and exposure layers         |
        |
        +----> ArcGIS Location Platform feature/vector-tile/map-tile service,
        |        when free-tier capacity and account capabilities permit
        |
        +----> ArcGIS Online organization-hosted layer,
        |        when privileges, credits, and storage permit
        |
        `----> selected non-Esri public representation,
               when neither Esri-hosted route is suitable
        |
        v
Next.js + ArcGIS Maps SDK for JavaScript <--------------------'
  project-derived public layers + publisher-hosted VSR + precomputed statistics
  ArcGIS platform basemap/services and public project layers where available
        |
        v
Static deployment -> visitor's browser
```

The three project-derived publication branches in this diagram are candidates,
not implemented fallbacks. Their final format and host remain deferred. The VSR
display source is selected but not implemented. Summary statistics follow the
analysis boundary and may be delivered as a small, versioned file the static
application reads; the browser does not recompute them.

## Component responsibilities

### Python

Python is the reproducible processing and analytical core.

**Implemented in part.** The src-based package under
[`analysis/`](../analysis/README.md) has a uv-locked Python 3.13 environment,
DuckDB as the production large-tabular engine, versioned configuration and
source/processing/lineage contracts, read-only input validators, deterministic
one-extract AIS cleaning, a local one-artifact AIS retrieval manifest boundary,
a bounded local multi-date AccessAIS delivery-intake boundary, resumable
sequential daily cleaning and period-manifest recording, and deterministic
EPSG:3310 water-grid construction. The retrieval boundary
performs no network request; it verifies retained bytes, archive safety and CRC,
the exact source header, and expected-date membership, and can bridge safe
interim extraction to the existing cleaner without changing observational
completeness. The period-intake boundary performs no network or AccessAIS order
automation. It streams one supplied direct CSV or safe ZIP, accounts for every
row, then uses bounded DuckDB sorting to publish canonical exact-date daily
inputs whose parsed-row multiset identity is independent of source order.
Duplicate multiplicity is preserved. It validates canonical manifest paths and
keeps immutable delivery identity, daily content identity, transfer
completeness, observational completeness, and 153-date period readiness
separate. Its managed intake, cleaner-output, and
period-manifest paths cannot overlap: the two directory roots are disjoint, and
the manifest cannot be inside either. The grid process accepts an explicit
polygon mask, clips it to the projected map/context boundary, intersects the
exact configured grid, and writes actual per-cell water geometry and area as
GeoParquet plus generation lineage.
These foundation paths do not retrieve the analytical-period AIS data over the
network, calculate relative exposure, or derive statistics. A separate
deterministic, tested whale-grid command transfers modeled density by
abundance-conserving area-weighted intersection, writes generation lineage, and
produced byte-identical outputs in two clean real-data runs; the exact derived
output was
also visually verified in QGIS 4.2.1.

The upstream `ProcessingConfig` contract is frozen at schema 1 and retains its
established digest because it identifies inputs to AIS cleaning, projected
water-grid generation, whale-grid transfer, and map-extent vessel aggregation.
Its legacy analytical-domain-status scalar is a compatibility sentinel, not the
current decision authority. The accepted downstream analytical/reporting domain
is instead a separate schema-1 contract. That contract assigns distinct stable
roles to the map/context extent, modeled-whale-support water geometry, and
`receivers_50_nautical_miles` system-performance-qualified AIS domain. It is
not an input to upstream artifact identity. Applying that domain to exposure
and headline statistics remains future M6 work.

A further implemented boundary assembles explicitly supplied one-date cleaner
bundles into a versioned multi-day period-input manifest. It keeps expected
date, retrieval-manifest state, independently verified retained-byte and archive
state, retrieval-to-cleaner linkage, cleaner-bundle compatibility, missing or
conflicting status, and unverified observational completeness as separate
states; it validates a supplied retrieval manifest's own `cleaning_reference`
checksums against the recorded bundle rather than associating them by date
alone; it marks the period ready only when all 153 expected dates carry a
compatible verified current entry; and it derives a period identity from
contracts, expected dates, deterministic cleaned-Parquet checksums, and
deterministic cleaner run identities. The quality-report and run-metadata
checksums are validated for integrity but excluded from that identity, because
the cleaner records local paths and real execution timestamps inside those
sidecars. Its bounded DuckDB relation scans the verified daily Parquet
partitions with an explicit memory limit and spill directory, streams a
deterministic global ordering as Arrow record batches instead of concatenating
the period in Python, and preserves same-vessel continuity across midnight. It
selects no plausibility threshold, constructs no segment, and emits no
vessel-activity grid.

A separate candidate vessel-grid boundary is implemented and synthetically
tested. It requires explicit maximum-gap, implied-speed, readiness, edge, and
support treatments; streams whole-period consecutive pairs from the verified
relation; allocates retained EPSG:3310 segment distance to the exact water grid;
and writes deterministic candidate GeoParquet and quality-report artifacts plus
time-bearing lineage. The documented four-parameter matrix was exercised and
repeated on the real 15--16 July input. This bounded execution does not select
accepted thresholds, establish period-wide completeness or scaling safety, or
produce the final production vessel-activity input. Final period-wide vessel
aggregation therefore remains unfinished.

Python owns or is planned to own:

- source retrieval boundaries and large-tabular handling;
- source validation, cleaning, filtering, deduplication, and reprojection;
- deterministic grid construction and water-mask intersection;
- whale-value transfer and vessel aggregation onto the analysis grid;
- the relative-exposure calculation and fractional inside/outside VSR
  statistics within the accepted analytical domain;
- synthetic tests whose answers are known by construction;
- versioned configuration, run metadata, provenance links, and output lineage;
- deterministic export preparation at the publication boundary.

Any repeatable transformation that changes a derived value belongs here. A
manual GIS experiment can inform a method, but that method becomes a recorded,
tested Python step before it contributes to a production result.

The implemented grid is GeoParquet 1.1.0 with WKB and explicit EPSG:3310
metadata as a **local deterministic processing format**. It is not the selected
public delivery format. ArcGIS compatibility for that file has not been
verified.

### QGIS

QGIS is the local GIS inspection, exploratory-review, cartographic-review, and
visual-verification tool. It is not the production processing system.

QGIS is used to:

- open exact source or derived spatial artifacts without conversion where the
  format is supported;
- inspect CRS, extent, layer placement, geometry, orientation, coastline and
  island gaps, boundary clipping, and other properties tests can miss;
- explore candidate methods or symbology before reproducible choices are
  implemented and recorded; and
- provide post-generation visual-verification evidence tied to the inspected
  output checksum.

On 2026-08-27, QGIS 4.2.1 successfully opened the exact generated GeoParquet
and verified 4,516 EPSG:3310 MultiPolygon features. This is evidence for that
specific checksum, not evidence that every future spatial output is correct.

No production result may depend on an unrecorded manual QGIS edit, conversion,
field calculation, geoprocessing action, or export. If exploration in QGIS
reveals a needed transformation, it is implemented in the Python path with
configuration, tests, and lineage. QGIS project files and rendered inspection
images are local evidence unless a later decision explicitly makes a small
artifact part of the repository.

### Publication and export boundary

Publication begins only after programmatic validation and visual inspection. It
may change representation for browser delivery, but it may not change the
underlying analytical values without returning to the Python processing path.

For project-derived layers, the boundary must preserve a traceable mapping
among:

- the validated derived artifact and its checksum;
- the generation run and source lineage;
- the post-generation visual-verification evidence;
- any export or tiling parameters; and
- the public layer or file the application consumes.

The final representation for project-derived whale, vessel, and exposure layers
is deliberately open. Candidate routes are ArcGIS Location Platform limited
data services, ArcGIS Online organization-hosted layers, and a non-Esri public
fallback if neither is suitable. Selection depends on measured output size,
feature count or raster characteristics, geometry complexity, browser
load/render performance, redistribution terms, anonymous-access requirements,
and verified account or hosting capabilities. GeoJSON, vector tiles, hosted
feature layers, hosted tile/imagery layers, and other supported representations
are candidates, not decisions.

### Publisher-hosted VSR display exception

[ADR 0019](decisions/0019-reference-the-publisher-hosted-vsr-service.md)
selects one narrow Version 1 exception. Python uses the exact immutable local
snapshot under ignored `data/raw/` for fractional inside-versus-outside
analysis. The public application will instead load `FID = 126` directly from
the publisher's public `WhaleAtlas_2026` Feature Service:

`https://services5.arcgis.com/4biRnCjZju47bNvA/arcgis/rest/services/WhaleAtlas_2026/FeatureServer/0`

The application will show that remote layer inside its own map, not redirect
the visitor. It must attribute Danielle Alvarez, CMSF, and BWBS according to
ArcGIS item `b400c7f418b04dc5a9d7ce5015adae32` and preserve the publisher's
non-navigational disclaimer. The project must not commit or publish the local
snapshot or any copied, clipped, simplified, converted, or derived VSR
geometry.

The remote layer is not frozen and does not become analytical provenance. Its
owner can change, remove, rate-limit, or privatize it. Version 1 does not add an
automatic synchronization or monitoring service. Before release, an anonymous
check must confirm the expected item, layer, and feature still exist and compare
the current geometry with the analytical snapshot. The application must not be
released while it displays a boundary that differs from the geometry used for
the statistics. A change requires an analysis rerun or reconciliation so they
match, or omission of the mismatched remote boundary from the release; a warning
alone is insufficient.

This no-copy route does not establish redistribution permission. It removes
redistribution from Version 1's publication requirements, but it does not make a
legal determination about other terms governing direct service use. A later
decision to host a project-controlled VSR copy requires a confirmed permission
posture.

### ArcGIS Online organization hosting

ArcGIS Online is a conditional publication and hosting option, not a processing
tier and not a prerequisite for Version 1. If a real account check verifies the
needed capabilities, it may host project feature, tile, or imagery layers and
serve them anonymously to the application.

The following facts remain unverified and must not be inferred from account type
or documentation alone:

- organization access, user type, role, and content-creation privileges;
- hosted feature, tile, and imagery publishing privileges;
- permission and organization policy for public sharing;
- credits and the cost of intended publishing/storage operations;
- available storage; and
- anonymous access to the resulting service.

If a required capability is unavailable, that evidence becomes a constraint on
the publication-format decision. It does not invalidate the Python analysis,
QGIS verification, static application, or Esri map-client integration. A later
milestone must evaluate ArcGIS Location Platform and, if needed, a non-Esri
public route; none is selected or implemented yet.

### ArcGIS Location Platform limited organization and data services

ArcGIS Location Platform is a separate Esri-hosted publication candidate, not
only an API-key and basemap provider. Esri documents it as a limited single-user
organization with support for creating hosted feature, vector-tile, and
map-tile services. It does not provide the full ArcGIS Online organization
capability set, and the documented Location Platform data-service list does not
include hosted imagery or scene services. See Esri's
[portal and data services FAQ](https://developers.arcgis.com/documentation/portal-and-data-services/faq/).

Location Platform storage and data-service bandwidth use monthly free tiers
with optional pay-as-you-go billing. Current official documentation was checked
on 2026-08-31 and also confirms `Everyone` sharing gives anonymous access; a
separate ArcGIS Online organization is not required for that Location Platform
path. See Esri's [sharing and security guide](https://developers.arcgis.com/documentation/portal-and-data-services/data-services/feature-services/sharing-and-security/),
[billing guide](https://location.arcgis.com/help/billing/), and
[current pricing](https://location.arcgis.com/pricing/). The documented free
tiers relevant to public project data are 250 MB each
for feature storage and tiles/files/attachments storage, 125 MB each for
feature-query and feature-edit bandwidth, 25 GB each for vector-tile and
map-tile bandwidth, and 25,000 generated tiles. Basemaps have separate monthly
allowances of 2,000,000 tiles or 1,000 sessions. These are product-wide limits,
not verified balances for the author's account.

Before this route can be selected, the author must verify the real account's
product identity, supported creation and sharing controls, current storage and
bandwidth use, remaining headroom, and billing status. This project does **not**
authorize enabling pay-as-you-go, adding a payment method, or incurring a
charge. If a safe test cannot remain within an already available free tier, it
is not run and the route remains unverified or is recorded as unsuitable.

### Browser API-key services

The application intends to use an ArcGIS basemap and may use other appropriate
platform services or project items through the ArcGIS Maps SDK where available.
Those browser requests use `NEXT_PUBLIC_ARCGIS_API_KEY`. Esri documents API-key
management privileges as available by default for ArcGIS Location Platform
accounts; ArcGIS Online accounts have separate user-type and privilege
requirements. See the
[API-key authentication documentation](https://developers.arcgis.com/documentation/security-and-authentication/api-key-authentication/).

A browser key is public by definition. It must be minimally scoped to the
services and public items the application reads, restricted to approved
origins, and must never carry publishing, content-management, organization, or
account-management privileges. Publishing credentials never enter the
application or repository.

The missing-key failure path is implemented and verified. On 2026-08-31 a real,
scoped browser key successfully rendered the `arcgis/oceans` basemap from the
authorized localhost origin in Chrome at all three required viewports; pan,
zoom, readiness, attribution handoff, and responsive containment were verified.
That local service-access result does not identify the account type or establish
project-layer hosting. Account capabilities and service access from a future
deployed origin remain to be checked.

### Next.js, TypeScript, and the ArcGIS Maps SDK for JavaScript

The public application is a static Next.js and TypeScript presentation layer
using the ArcGIS Maps SDK for JavaScript. The application shell exists and
builds. The SDK is mounted through client-only web components per
[ADR 0009](decisions/0009-mount-arcgis-through-client-only-map-components.md),
while [ADR 0008](decisions/0008-deliver-the-application-as-a-static-export.md)
enforces a static build with no application server.

The client is responsible for:

- loading the selected project-derived public layer representations and the
  publisher-hosted VSR feature;
- rendering the map, layers, legends, visibility controls, and popups;
- presenting precomputed summary statistics and methodology;
- exposing units, assumptions, limitations, and provenance; and
- client-side view state and other presentational interactions.

It does not retrieve raw inputs, transform analytical data, calculate exposure,
or derive reportable statistics. Local API-key-backed basemap rendering has
been observed and verified; no deployment exists, so deployed-origin rendering
remains unverified.

### ArcGIS Pro

ArcGIS Pro is optional and unnecessary for Version 1. It is paid software and
is unavailable to this project. There is no missing ArcGIS Pro prerequisite,
no planned `arcgis/` repository directory, and no milestone waits for a Pro
project. If it becomes available later, it may be used for optional inspection
or exploration under the same rule as QGIS: no production result may depend on
an unrecorded manual transformation.

## Processing versus presentation

| Concern | Python processing | QGIS review | Browser application |
|---|---|---|---|
| Raw retrieval, validation, cleaning | Owns | May inspect read-only | Never |
| Reprojection, clipping, gridding | Owns | Verifies output | Never |
| Exposure and inside/outside statistics | Owns | Verifies spatial output | Never |
| Exploratory method/cartography review | Records accepted method in code/configuration | Supports exploration | Never |
| Publication-format conversion | Reproducible export boundary | May inspect exported artifact | Never |
| Layer visibility, opacity, map view | — | May preview | Owns |
| Display filtering and popups | — | May preview | Owns |

The rule is simple: if an operation can change a number a reader might quote,
it belongs in the reproducible Python path.

## Deployment model

- Next.js produces a static export served over HTTPS from a stable public URL.
- Version 1 has no custom backend, server-side analysis, database, or runtime
  application server.
- Project-derived public layers are loaded directly by the browser from the
  selected delivery route. The VSR boundary is loaded separately from the
  publisher's public Feature Service with `FID = 126`.
- ArcGIS platform basemap/service/item requests are made through the SDK with a
  scoped and origin-restricted browser API key where available.
- The project-derived-layer route may use ArcGIS Location Platform limited data
  services, ArcGIS Online organization-hosted layers, or a non-Esri public
  representation. A later evidence-based decision selects among them.

The application host and layer host need not be the same provider. The static
hosting platform, project-layer representation, and project-layer host all
remain unselected. A local build proves none of them: completion requires a
clean-browser test of the deployed application, basemap/service access, public
project layers, and matching precomputed results.

## Secrets and credentials

- No credential, API key, token, connection string, account identifier, or
  password is committed, including in examples, screenshots, notebooks, or
  fixtures.
- Local browser configuration uses ignored `.env.local`; deployment values are
  supplied as build-time environment configuration.
- Committed examples list variable names only and contain no real keys.
- Every browser-delivered key is public, minimally scoped, origin-restricted,
  and read-only. It never has publishing or account-management rights.
- Any authenticated publication is an author-run action outside the repository.
  An agent does not sign in, publish, change sharing, spend credits, or operate
  the user's ArcGIS account.
- No account check or publication test enables pay-as-you-go billing, adds a
  payment method, exceeds an already available free tier, or otherwise
  authorizes spending.
- A committed credential is treated as compromised and rotated first.

## Large-data handling

- Raw source data is never committed. It lives in the Git-ignored local data
  root governed by [data/README.md](../data/README.md).
- Local interim and derived artifacts remain ignored. Small results the static
  application reads may be committed when their contract is implemented and
  their provenance is recorded.
- Public project-derived layers cross the publication boundary to the selected host;
  ArcGIS Location Platform and ArcGIS Online are separate conditional Esri
  destinations, with a non-Esri public route retained if neither is suitable.
- The VSR source snapshot and every project-created copy or derivative remain
  local and ignored. Public display references the publisher's service directly.
- Git LFS is not planned for Version 1. Any demonstrated need requires a
  decision record before large binaries are added.
- ADR 0017 accepts AccessAIS as the preferred retrieval route. The local supplied-
  artifact verification boundary, bounded multi-date delivery intake, resumable
  daily-cleaner orchestration, overlapping real one-day/two-day compatibility
  exercise, seven-day operational gate, and exact July monthly operational gate
  are implemented and complete. The July artifact passed its bounded resource
  and retry criteria, authorizing sequential author-submitted August--November
  calendar-month extracts under the same controls. August, September, and
  October have since been processed under those controls. November safety and
  complete 153-day processing safety remain unverified. Network transfer, independent
  transfer completeness, observational completeness, and analytical-period
  acquisition are not established. Guarded one-day-at-a-time bulk retrieval
  remains fallback only. An entire national season is never staged locally; the
  detailed retrieval guard belongs to [data/README.md](../data/README.md).
- AccessAIS daily cleaner compatibility uses the Version 2 canonical parsed-row
  multiset identity and artifact checksum, not source delivery order. Whole-
  delivery byte size and SHA-256 remain separate provenance. Version 1 intake
  manifests remain read-only valid and cannot be silently reused as Version 2
  output directories. Blank parsed fields are normalized to empty strings before
  sorting/export, and spill parents must be disjoint from every managed intake,
  cleaner, and period-manifest destination before output creation.
- The multi-day cleaned-input relation scans daily Parquet partitions through
  DuckDB under an explicit memory limit and an explicit ignored spill directory,
  and streams ordered results rather than materializing the period in Python.
  This bounds the assembly step; it does not establish that full-period
  retrieval or cleaning is safe.

DuckDB is the production large-tabular boundary per
[ADR 0012](decisions/0012-use-duckdb-for-large-tabular-processing.md). The
existing half-hour benchmark selects the foundation engine but does not
establish full-day or full-period performance.

## Testing and visual-verification boundaries

Testing effort follows consequence:

- Python analytical logic is tested with small synthetic inputs whose answers
  are known by construction, including the fractional-boundary cases in
  [ADR 0004](decisions/0004-analysis-grid-resolution.md).
- Processing validates CRS, extent, nulls, geometry, ranges, invariants, and
  output identity so bad inputs or outputs fail loudly.
- TypeScript receives type checking, linting, and tests for non-trivial
  presentation logic. The ArcGIS SDK and external services are verified through
  browser integration checks rather than unit tests.
- Every derived spatial layer requires visual inspection in QGIS or another
  explicitly recorded GIS tool. Tests do not reveal every projection,
  orientation, clipping, or rendering error.

Generation-time lineage and visual verification are related but distinct
evidence:

1. **Generation-time lineage must not be manually edited.** It records the
   inputs, configuration, processing steps, output checksum, validations
   performed during generation, and execution metadata. A field written as
   `visual_inspection_status: not_completed` remains truthful for that
   generation. Under the current implementation, an explicitly authorized
   overwrite replaces both the output and sidecar; prior run evidence is not
   retained automatically. Append-only or versioned lineage remains future
   work.
2. **Post-generation visual verification is separate evidence tied to the exact
   output SHA-256.** It records the checksum, date, GIS tool and version,
   inspected views and checks, result, and relevant observations. It does not
   require or permit manually editing the generated lineage sidecar.

The current QGIS documentation records successful verification of output
SHA-256 `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031`
on 2026-08-27 in QGIS 4.2.1. A formal reusable verification record or command
is not implemented. That follow-up belongs to the processing/reproducibility
workflow, not to this documentation-only architecture change.

## Reproducibility and lineage

Reproducibility rests on four linked practices:

1. **Recorded provenance:** publisher, retrieval method, parameters, date,
   version/vintage, local artifact identity, and checksum.
2. **An ordered Python processing path:** version-controlled code, versioned
   configuration, documented entrypoints, locked environment, tests, and run
   metadata.
3. **Separate spatial verification:** checksum-bound evidence recorded after
   inspecting the exact derived artifact.
4. **Traceable publication:** every project-derived public layer and reported
   statistic maps to a validated derived artifact, generation run, verification
   record, and any representation-changing export step. The publisher-hosted
   VSR layer instead maps to its item, service, feature filter, and release-time
   comparison with the local analytical snapshot.

The intended end-to-end test is to rerun from unchanged raw inputs, reproduce
the validated derived outputs, repeat spatial verification where required, and
compare them with what the deployed application serves. M8 owns that gate.

## Performance and publication-format selection

No final format or host is selected for the project-derived whale, vessel, and
exposure layers. The decision requires evidence from those real outputs,
including:

- byte size, feature count, geometry complexity, and raster dimensions where
  applicable;
- transfer size, time to first meaningful map, pan/zoom responsiveness, memory
  use, and behavior on a mid-range connection/device;
- whether the representation supports required symbology, legends, popups,
  attribution, and anonymous access;
- redistribution conditions for each source and derivative; and
- actual ArcGIS Location Platform service support, storage, bandwidth,
  free-tier/billing status; ArcGIS Online privileges, credits, and storage; or
  alternative-host capability and operating constraints.

The ArcGIS SDK's installed payload and local shell build have been measured,
but those measurements do not select a project-layer representation. Hosted
feature layers, hosted tiles/imagery, vector tiles, GeoJSON, and other formats
remain candidates until the real outputs exist and browser tests distinguish
them.

## Version 1 architectural constraints

Version 1 deliberately does not introduce a custom backend or API service,
microservices, PostGIS or another self-hosted database, job queues, schedulers,
containers, Kubernetes, or AI features. The provider-neutral publication
boundary does not authorize any of those. A future need must be demonstrated
and recorded before the architecture expands.

## Current and planned repository structure

`analysis/` and `web/` exist. The remaining entries are existing documentation
and local data boundaries or explicitly deferred small results; no ArcGIS Pro
directory is planned.

```text
socal-whale-vessel-risk/
├── docs/                  # documentation and ADRs (exists)
├── analysis/              # Python processing package and tests (exists)
├── data/                  # Git-ignored local data root (exists)
│   ├── raw/               # untouched source downloads
│   ├── interim/           # intermediate and verification artifacts
│   └── derived/           # validated local outputs before publication
├── web/                   # static Next.js application (exists)
└── results/               # small versioned application results [deferred]
```

Whether `results/` is distinct enough from `data/derived/` remains deferred
until the reporting-domain-dependent application-results contract is allowed.
No implementation directory is scaffolded before its milestone needs it.

## Explicitly deferred decisions

| Decision | Deferred until | Selection basis |
|---|---|---|
| Exposure formula, normalization, and weighting | Both final grid-aligned inputs are ready | Input units/distributions, scientific support, and sensitivity within the accepted `receivers_50_nautical_miles` domain. |
| High-exposure threshold | Exposure surface exists | Real value distribution and sensitivity analysis. |
| Final public representation and host for project-derived whale, vessel, and exposure layers | Real layer outputs, browser measurements, redistribution review, and account capability evidence exist | Output size/shape, anonymous browser performance, required interactions, legal constraints, usage limits, and supported service types. No format or provider is preselected. The publisher-hosted VSR exception is already selected in ADR 0019. |
| ArcGIS Location Platform publication route | Author completes the authenticated portion of the Location Platform capability check | Official documentation confirms a limited single-user organization, feature/vector-tile/map-tile support, and public anonymous sharing with current monthly free tiers. The real account's product identity, controls, usage, headroom, and billing status remain unverified. No pay-as-you-go activation or spending is authorized. |
| ArcGIS Online publication route | Author completes the ArcGIS Online capability check | Organization privileges, public sharing, hosted layer types, credits, storage, and anonymous access. A negative finding constrains the route rather than blocking all completion. |
| Non-Esri public delivery route, if needed | Both Esri routes are unavailable/unsuitable or measurements favor another route | Must preserve public access, static-client compatibility, attribution, lineage, and acceptable browser performance; no fallback is implemented today. |
| Static application host | Deployment milestone | HTTPS, stable origin, static-export limits, build-time environment values, and clean-browser verification. |
| Formal visual-verification record or command | M3/M8 reproducibility work | Must record output checksum, date, GIS tool/version, inspected views/checks, result, and observations without mutating generation lineage. |
[ADR 0002](decisions/0002-southern-california-study-area-extent.md) accepts
`receivers_50_nautical_miles` as the scope-reduced,
system-performance-qualified AIS analytical domain: 50 nautical miles, exactly
92,600 metres, from the relevant NAIS reception stations, not from the coast.
It is not empirical 2024 coverage. Outside-domain cells are excluded from
headline statistics and are not classified as low traffic. Receiver uptime,
station completeness, feed interruptions, antenna and terrain effects, and
observational completeness remain unknown or unverified. M2 is **Complete**:
ADR 0019 resolves its final publication-posture criterion by prohibiting
project-hosted VSR copies and selecting direct publisher-service display, not by
claiming that redistribution permission was granted.

Resolved choices remain recorded in their ADRs: the map/context extent and
qualified analytical domain ([0002](decisions/0002-southern-california-study-area-extent.md)), EPSG:3310
([0003](decisions/0003-projected-coordinate-system.md)), the 5 km grid and
fractional boundary accounting ([0004](decisions/0004-analysis-grid-resolution.md)),
the 2024 analytical period ([0005](decisions/0005-analytical-period.md)), separate
vessel-speed reporting ([0006](decisions/0006-report-vessel-speed-separately.md)),
the static application and client-only SDK boundary ([0008](decisions/0008-deliver-the-application-as-a-static-export.md),
[0009](decisions/0009-mount-arcgis-through-client-only-map-components.md)),
the Python toolchain and DuckDB engine ([0011](decisions/0011-use-uv-for-the-python-analysis-toolchain.md),
[0012](decisions/0012-use-duckdb-for-large-tabular-processing.md)), and the
whale-model support mask ([0014](decisions/0014-select-the-grid-water-mask.md)),
and direct publisher-hosted VSR display with no project-controlled copy
([0019](decisions/0019-reference-the-publisher-hosted-vsr-service.md)).
