# Architecture

**Owns:** system design, component boundaries, and deferred design decisions.

> **Status: accepted and refined.** [ADR 0001](decisions/0001-accept-initial-architecture.md)
> accepted the initial direction. [ADR 0015](decisions/0015-adopt-a-hybrid-open-source-and-esri-gis-toolchain.md)
> refines its tooling and publication assumptions after implementation and
> visual-verification evidence; it does not rewrite ADR 0001's historical
> context. [ADR 0019](decisions/0019-reference-the-publisher-hosted-vsr-service.md)
> selects direct use of the publisher-hosted VSR Feature Service as a narrow
> Version 1 exception to the project-derived-layer publication boundary.
> [ADR 0021](decisions/0021-propose-vercel-static-input-delivery.md) selects
> checksum-addressed static project files on free Vercel Hobby. Initial
> eligibility, account, capacity and minimum browser-key checks passed on
> 2026-09-07. The isolated project now serves the reviewed-main package at its
> stable production origin. Production Toolbar is disabled for this project,
> and the final unchanged-package redeployment passed strict receipt matching
> for all 900 public files.
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
> `ready`. A bounded period vessel-rule evidence boundary is implemented and
> synthetically tested; it evaluates the four ADR 0018 candidate combinations
> from one whole-period adjacency stream without spatial allocation. On
> 2026-09-04, two profiled executions against that ready 153-date manifest
> reproduced exact deterministic evidence bytes. Those non-spatial executions
> did not compare candidate effects in individual grid cells, and no rule has
> been accepted. The later full-period spatial matrix has now been repeated,
> compared and inspected, and ADR 0018's selected production rules were accepted
> after real generation, repetition and QGIS validation. Publisher-side transfer
> and observational completeness remain unverified. Network retrieval remains
> unimplemented. The ADR 0020 exposure method is implemented and has been run
> locally for exploratory results, which are unreviewed and unaccepted; exposure
> display/results contracts are implemented and locally verified. Static
> delivery is selected by ADR 0021; the input-layer application is deployed,
> while the M7 exposure/results interface and complete release staging are
> implemented and browser-verified locally but not independently audited or
> deployed.
> Publisher-hosted VSR display is
> implemented and locally verified in the web application. Deterministic
> presentation exports and checksum-bound same-origin display are also
> implemented and locally verified for the whale, vessel-activity, and accepted
> analytical-domain layers. Vercel Hobby is selected and its route-specific
> account checks, isolated project, deployed-origin browser behavior and full
> receipt integrity are verified. M4 is complete.
> See the [roadmap](roadmap.md) for milestone status.

The analytical and statistical domain is accepted in
[ADR 0002](decisions/0002-southern-california-study-area-extent.md), and the VSR
display route is accepted in ADR 0019. Python uses the immutable ignored local
VSR snapshot for analysis; the browser displays `FID = 126` directly from
the publisher's public Feature Service. The project will not commit or publish
a copy or derivative of that geometry. Permission to redistribute remains
unconfirmed; Version 1 avoids redistribution rather than treating public access
as a licence.

ADR 0021 selects free Vercel Hobby as the public host for static project-derived
files. The whale,
vessel-activity, and accepted analytical-domain layers are exported as WGS 84
GeoJSON and read as static same-origin files, which is implemented and verified
locally and at the stable production origin. The M7 branch consumes the exposure
delivery contract through the same route locally; the release package does not
yet include it. On 2026-09-07 the author confirmed Vercel Hobby eligibility for
this personal, unpaid, non-monetized portfolio and ArcGIS Location Platform with
pay-as-you-go disabled. Current basemap use was 5,292 of 2,000,000 monthly
tiles, and the minimum browser key was verified against the exact localhost and
reserved production origins. The isolated Vercel project serves the keyed
reviewed-main package at `https://socal-whale-vessel-overlap.vercel.app`.
Location Platform hosted-data services and ArcGIS Online organization hosting
are unselected, so their actual publishing capabilities remain unverified and
are not M4 prerequisites. A later choice to use them requires a superseding
decision and route-specific free-capability evidence.

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
- **Public publication services** — validated project-derived outputs cross a
  provider-neutral boundary as checksum-addressed static files served beside
  the application on free Vercel Hobby. Esri hosted-data services are
  unselected; adopting one later requires a superseding decision.
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
        `----> checksum-addressed static same-origin files
               in the free Vercel Hobby application deployment
        |
        v
Next.js + ArcGIS Maps SDK for JavaScript <--------------------'
  project-derived public layers + publisher-hosted VSR + precomputed statistics
  ArcGIS platform basemap/services and public project layers where available
        |
        v
Static deployment -> visitor's browser
```

ADR 0021 selects the project-derived publication branch in this diagram. The
three M5 input layers are deployed and receipt-verified on that route. The M7
branch integrates the M6 exposure representation and versioned results locally,
but the release stage and public deployment still omit both. The VSR display
source is the publisher-hosted exception selected by ADR 0019. Summary statistics
follow the analysis boundary as a small, versioned build input; the browser does
not recompute them.

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
not an input to upstream artifact identity. The M6 exposure boundary applies
that domain's exact qualified geometry; selecting any of its outputs as a
headline statistic remains open.

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

A focused period vessel-rule evidence boundary reuses that relation's single
whole-period same-MMSI adjacency stream. Its production path requires the ready
153-date manifest and explicit 300/1,800-second gap values, explicit 30/50-knot
speed ceilings, and the explicit type-only/no-length-filter treatment. An
explicitly named incomplete-period override is limited to non-production use.
The boundary accounts cross-midnight segments to their starting observation's
UTC date while reporting them separately; summarizes passenger, cargo, tanker,
and union-recomputed commercial populations by date and whole period; and uses
exact scalar aggregates plus fixed bins rather than retaining observations or
segments for percentiles. All four candidate combinations are evaluated during
one bounded Arrow iteration. The deterministic JSON identity excludes paths,
clocks, runtime, machine details, resource settings, and output names; those
execution facts occur only in a time-bearing lineage sidecar. Atomic output is
restricted to ignored interim storage. In addition to its synthetic tests, two
profiled executions processed the real ready five-month input and reproduced
the exact deterministic `evidence.json` bytes. These executions were
non-spatial: they do not establish how the four candidates change individual
grid cells, accept a rule, create a production vessel grid, or perform exposure
analysis.

The candidate vessel-grid boundary streams whole-period pairs with explicit
rules, allocates exact water-support distance, and writes deterministic
GeoParquet/quality plus time-bearing lineage. All four full-period candidates
were generated, repeated, compared over six pairs and inspected in QGIS.
ADR 0018 selects 300 seconds / 30 knots; it was accepted on 2026-09-05 after
final production generation, byte-identical repetition, independent verification
and checksum-bound QGIS validation.

The distinct `production_vessel_input_v1` boundary now reuses that aggregation
engine with the selected configuration and a required ready period. An allocation
observer computes separate distance-weighted movement-speed descriptors from
the same pieces; it does not alter activity or repeat intersections. The
production writer reuses spatial serialization but defines its own contract,
identity and lineage. It consumes no candidate artifact, permits no overwrite,
and preserves failed temporary evidence. Speed semantics belong to ADR 0006.
Its real production generation, reproduction and QGIS validation completed with
M3; the exposure boundary below now consumes that output.

A distinct `exploratory_relative_exposure_v1` boundary implements the
[ADR 0020](decisions/0020-propose-area-integrated-relative-exposure.md) method
across four modules. `exposure_geometry` performs exact water/domain/VSR
intersection and difference in EPSG:3310, applies the established 0.01°
densification, verifies the retained domain and VSR bytes by checksum, and
splits a caller-supplied full-water integrated total by area fraction under the
labelled uniform-within-water-cell assumption. `exposure_inputs` joins the exact
retained M3 water, whale and vessel tables; it checks lineage against verified
dataset metadata — contract, configuration, vessel method and identity, dated
cleaned inputs, whale source, artifact digests, required validations and ordered
UTC steps — rather than against historical paths, so a regenerated upstream
bundle is admissible while analytical identity stays unchanged. Execution-specific
lineage hashes are recorded in run metadata only; they are deliberately excluded
from run identity, layer metadata and the deterministic report, which keeps
analytical identity separate from execution provenance. `exposure.py` holds the
calculation itself: per-cell intensity, the area-weighted quantile thresholds,
maximum-scaled display normalization, 10 km coarsening and the method
comparison. It keeps two areas deliberately distinct — intensity divides both
the whale and vessel terms by the cell's **full** water area, while integration
weights that intensity by **qualified** area and by its exact inside/outside VSR
partition — so the domain constrains what is summed, not what is divided by.
`exposure_run` composes the four: it computes both grids, the threshold family
and the sensitivity comparisons, then writes a deterministic bundle and reads it
back to re-verify formula, integration, geometry, nulls, indices, flags and
summaries.

That bundle — two GeoParquet layers, a sensitivity report and time-bearing run
metadata — is narrow ignored local evidence beneath `data/derived/`; it is not
itself a publication artifact. A separate `exposure_delivery` boundary consumes
all three deterministic files only when their expected checksums are supplied.
It re-verifies both tables, reconstructs the accepted calculations from their
serialized rows, and reconciles the complete report rather than treating a
matching report checksum as evidence of numerical correctness. It then creates
distinct `relative_exposure_display_v1` and
`relative_exposure_application_results_v1` public contracts. The analytical
module is invoked through the existing resource profiler and writes only to
ignored locations. Visual verification runs
separately through `analysis/scripts/qgis_inspect_exposure.py`, which binds
rendering to the exact output checksums rather than to generation lineage.

The delivery boundary builds every public nested object through an explicit
typed allowlist, validates controlled text and enumeration fields, and rejects
unexpected shapes. Private paths, credentials, debug metadata, execution clocks,
and upstream generation-lineage digests cannot propagate. The application
results identity is derived from deterministic analytical/result content and is
independent of the permitted delivery timestamp. This preserves the distinction
between analytical identity and truthful time-bearing generation provenance.

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

**Static same-origin representations are implemented for the three M5 project
input layers.** `blue_whale_display_export_v1` turns a validated
`blue_whale_grid_transfer_v1` GeoParquet artifact into RFC 7946 WGS 84 GeoJSON
plus a sanitized, publishable manifest. `commercial_vessel_display_export_v1`
and `analytical_domain_display_export_v1` produce separate vessel-activity and
accepted-domain GeoJSON/manifest pairs only after checksum-verifying the
accepted production vessel grid, its quality report, the domain masks, and the
domain evidence report. The vessel export clips vessel-cell water geometry to
the exact receiver-qualified domain in EPSG:3310 while retaining the complete
source-cell activity and support-water values; it does
not expose speed or distinct-vessel descriptors and performs no value
rescaling, simplification, rounding, or densification.

Both exporters write only to Git-ignored output roots inside this checkout and
rebuild public metadata from named allowlists, so filesystem paths,
credentials, raw inputs, private lineage, and VSR-derived geometry cannot reach
a public artifact. The application fetches each same-origin file, verifies its
checksum against the bytes loaded, and creates the ArcGIS layer from those same
bytes. Each invocation independently owns its request, checksum, Blob URL,
layer, readiness/count assertion, timeout, failure state, and cleanup; stale
executions cannot update state or remove or overwrite newer or unrelated
layers. Deterministic ordering keeps both analytical fills beneath the domain
and publisher VSR outlines.

This implemented representation is deployed through free Vercel Hobby under
ADR 0021. The three exact project files and their clean-browser behavior are
verified at the stable production origin. A platform-appended Toolbar loader on
the first deployment was eliminated by disabling Production Toolbar for this
project and redeploying the unchanged approved package; all public bytes now
match the receipt.

**A static exposure representation is also implemented and measured as local
delivery evidence.** The provider-neutral boundary emits qualified-water-only
RFC 7946 GeoJSON plus a sanitized manifest, and a separate small committed JSON
artifact carries exact summaries, units, denominators, null/exclusion meanings,
thresholds, sensitivity, source vintages, and generated presentation rounding.
The manifest binds the exact display checksum to the results checksum and
results ID. It carries neither VSR geometry nor per-cell VSR splits; excluded
cells are absent, never low or zero. The public properties preserve the primary
product and required log-traffic sensitivity while keeping speed separate.

This representation passed programmatic reconciliation, deterministic repeat,
checksum-bound QGIS inspection, independent numerical/scientific-content review
for exploratory public presentation, and author acceptance. M7 integrates it
through ADR 0021's selected static route: static generation validates the
versioned results, and the browser validates the fetched display/manifest pair
before creating the ArcGIS layer. The exact authorized package is deployed and
passed public receipt, header, keyed-browser, and VSR checks. Its retained
performance run combined 4× CPU throttling with delay/bandwidth controls on the
four project GeoJSON requests; it did not throttle the full page connection or
measure external ArcGIS requests. A later clean-browser run applied the same
100 ms / 10 Mbps profile globally before navigation, with cache disabled and 4×
CPU throttling. It exercised application HTML/JavaScript, all project layers,
the Oceans basemap, and publisher VSR service without recording external-service
timings. The functional criterion passed; neither run is a real-device benchmark.
The build-only results JSON is not public and no server runtime was added. A
representation change requires a later decision supported by measured need,
source terms and verified free capability.

### Publisher-hosted VSR display exception

[ADR 0019](decisions/0019-reference-the-publisher-hosted-vsr-service.md)
selects one narrow Version 1 exception. Python uses the exact immutable local
snapshot under ignored `data/raw/` for fractional inside-versus-outside
analysis. The public application instead loads `FID = 126` directly from
the publisher's public `WhaleAtlas_2026` Feature Service:

`https://services5.arcgis.com/4biRnCjZju47bNvA/arcgis/rest/services/WhaleAtlas_2026/FeatureServer/0`

The application shows that remote layer inside its own map and does not
redirect the visitor. This is implemented, deployed, and anonymously verified
against the analytical snapshot at the production origin. It attributes
Danielle Alvarez, CMSF, and BWBS according to ArcGIS item
`b400c7f418b04dc5a9d7ce5015adae32` and preserves
the publisher's non-navigational disclaimer. The project must not commit or publish the local
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

ArcGIS Online is an unselected publication option, not a processing tier or a
Version 1 prerequisite under ADR 0021. A later decision could select it only
after verifying the necessary free capabilities and access model.

The following facts remain unverified and must not be inferred from account type
or documentation alone:

- organization access, user type, role, and content-creation privileges;
- hosted feature, tile, and imagery publishing privileges;
- permission and organization policy for public sharing;
- credits and the cost of intended publishing/storage operations;
- available storage; and
- anonymous access to the resulting service.

These facts remain background unless a later decision selects this route. They
are not M4 gates and have not been checked against a real account.

### ArcGIS Location Platform limited organization and data services

ArcGIS Location Platform is an unselected Esri-hosted publication option as
well as a possible API-key and basemap provider. Esri documents it as a limited single-user
organization with support for creating hosted feature, vector-tile, and
map-tile services. It does not provide the full ArcGIS Online organization
capability set, and the documented Location Platform data-service list does not
include hosted imagery or scene services. See Esri's
[portal and data services FAQ](https://developers.arcgis.com/documentation/portal-and-data-services/faq/).

Location Platform storage and data-service bandwidth use monthly free tiers
with optional pay-as-you-go billing.

**Correction, rechecked 2026-09-06.** An earlier 2026-08-31 note in this project
recorded that `Everyone` sharing gives Location Platform hosted services
anonymous access. That is wrong, and it appears to have applied cross-product
sharing guidance to Location Platform. Esri's product-specific
[Location Platform data sharing and access guide](https://location.arcgis.com/help/data-sharing-and-access/)
states that "Hosted data services in ArcGIS Location Platform are not shared
publicly," and directs public-facing applications to use authenticated access
with developer credentials such as an API key. The
[feature-service sharing and security guide](https://developers.arcgis.com/documentation/portal-and-data-services/data-services/feature-services/sharing-and-security/)
lists `Owner (private)` as the only Location Platform sharing level, requiring a
scoped API key, while ArcGIS Online additionally offers Organization, Group, and
`Everyone (public)`.

**A visitor who never signs in is not the same as a token-free service
request.** A scoped, origin-restricted browser key can let visitors read a
private Location Platform layer without signing in, but the service itself is
not anonymous, the key is public once shipped, and the account owner carries the
resulting usage. Any Location Platform route for project-derived layers must be
designed on that basis. See also Esri's
[billing guide](https://location.arcgis.com/help/billing/) and
[current pricing](https://location.arcgis.com/pricing/). The documented free
tiers relevant to project data are 250 MB each
for feature storage and tiles/files/attachments storage, 125 MB each for
feature-query and feature-edit bandwidth, 25 GB each for vector-tile and
map-tile bandwidth, and 25,000 generated tiles. Basemaps have separate monthly
allowances of 2,000,000 tiles or 1,000 sessions. These are product-wide limits,
not verified balances for the author's account.

Before a later decision could select this route, the author must verify the real account's
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
That historical local result alone did not identify the account type or establish
project-layer hosting. The later route-specific account checks and stable-origin
deployment verification are recorded under M4 in the roadmap.

### Next.js, TypeScript, and the ArcGIS Maps SDK for JavaScript

The public application is a static Next.js and TypeScript presentation layer
using the ArcGIS Maps SDK for JavaScript. The application shell exists and
builds. The SDK is mounted through client-only web components per
[ADR 0009](decisions/0009-mount-arcgis-through-client-only-map-components.md),
while [ADR 0008](decisions/0008-deliver-the-application-as-a-static-export.md)
enforces a static build with no application server.

The client is responsible for:

- loading the selected project-derived public layer representations and the
  publisher-hosted VSR feature with independent layer lifecycles;
- rendering the map, layers, legends, visibility controls, and popups;
- presenting precomputed summary statistics and methodology;
- exposing units, assumptions, limitations, and provenance; and
- client-side view state and other presentational interactions.

The M7 results boundary reads the tracked application-results artifact during
static generation and rejects unsupported contracts or versions, missing
required fields, and incompatible results/display identities. Its public error
is fixed and path-safe; detailed read/parse diagnostics remain build-side. The
browser then fetches the exposure manifest and display, verifies the display
SHA-256 and exact contract/identity/count pairing, and creates the layer from the
verified bytes through the established independent GeoJSON lifecycle. Exposure
failure does not disable the four unrelated layers.

Presentation keeps analytical and cartographic choices distinct. The map may
switch between the proportional-product and log-traffic fields already present
in the display artifact; it does not calculate either formula. The sequential
display scale is a legend classification, not the analytical high-exposure
threshold. Relative exposure starts visible, whale and vessel fills start
hidden, and domain and VSR outlines remain visible above the fills. Deterministic
order is whale, vessel, exposure, domain, then VSR.

It does not retrieve raw inputs, transform analytical data, calculate exposure,
or derive reportable statistics. API-key-backed basemap rendering has been
observed and verified locally and at the stable deployed origin.

### ArcGIS Pro

ArcGIS Pro is optional and unnecessary for Version 1. It is paid software and
is unavailable to this project. There is no missing ArcGIS Pro prerequisite,
no planned `arcgis/` repository directory, and no milestone waits for a Pro
project. If it becomes available later, it may be used for optional inspection
or exploration under the same rule as QGIS: no production result may depend on
an unrecorded manual transformation.

## Processing versus presentation

| Concern                                | Python processing                             | QGIS review                   | Browser application |
| -------------------------------------- | --------------------------------------------- | ----------------------------- | ------------------- |
| Raw retrieval, validation, cleaning    | Owns                                          | May inspect read-only         | Never               |
| Reprojection, clipping, gridding       | Owns                                          | Verifies output               | Never               |
| Exposure and inside/outside statistics | Owns                                          | Verifies spatial output       | Never               |
| Exploratory method/cartography review  | Records accepted method in code/configuration | Supports exploration          | Never               |
| Publication-format conversion          | Reproducible export boundary                  | May inspect exported artifact | Never               |
| Layer visibility, opacity, map view    | —                                             | May preview                   | Owns                |
| Display filtering and popups           | —                                             | May preview                   | Owns                |

The rule is simple: if an operation can change a number a reader might quote,
it belongs in the reproducible Python path.

## Deployment model

[ADR 0021](decisions/0021-propose-vercel-static-input-delivery.md) selects the
author's preferred Vercel Hobby route. Local release staging packages committed
source, exactly four pinned public GeoJSON/manifest pairs, and the explicitly
allowlisted tracked results build input as static Build Output API v3 output.
The results JSON is available only to the isolated static build and is not a
public endpoint. Release identity and receipt verification bind both public and
build-only inputs.
On 2026-09-07 the author confirmed Vercel Hobby personal-use eligibility and
ArcGIS Location Platform with pay-as-you-go disabled. Basemap free-tier
headroom, minimum key scope and exact origin restrictions were verified. The
isolated `socal-whale-vessel-overlap` project serves the accepted M7 package
from application source commit `3dfedc1faab1dd830a79ab5fa0efce3b07c9db25`
at the intended stable production hostname. Later commits on `main` record
review, acceptance, and deployment evidence without changing that application
source. The entire project must remain within free capacity. Paid
plans, trials, add-ons, pay-as-you-go and other charged usage are prohibited.

- Next.js produces a static export served over HTTPS from a stable public URL.
- Version 1 has no custom backend, server-side analysis, database, or runtime
  application server.
- Project-derived public layers are loaded token-free by the browser as
  checksum-addressed same-origin files on free Vercel Hobby. The VSR boundary is loaded separately from the
  publisher's public Feature Service with `FID = 126`.
- ArcGIS platform basemap/service/item requests are made through the SDK with a
  scoped and origin-restricted browser API key where available.
- Esri hosted-data services are unselected. Using one later requires a
  superseding decision and its own free-capability and visitor-access evidence.

The application and project-file host are the same Vercel deployment. Selection
does not prove availability: completion requires a
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
- Generated display layers are **not** committed. The display exporters stage
  them into Git-ignored `web/public/layers/`, which `next dev` and `next build`
  serve from the same origin, so the application can read a generated layer
  without it entering version control. The exporter refuses every destination
  outside this checkout's ignored output roots.
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
  calendar-month extracts under the same controls. July through November have
  all been processed under those controls, and the shared period manifest is
  `ready` with 153 compatible dates, zero missing dates, and zero conflicts.
  Automated network transfer remains unimplemented, and publisher-side independent
  transfer completeness and observational completeness remain unverified.
  A complete cleaned-input period is an input result only: it establishes no
  period-wide vessel aggregation and no exposure analysis, neither of which
  exists. Guarded one-day-at-a-time bulk retrieval
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
  This bounds the assembly step; it does not by itself establish that a
  period-wide scan or any downstream aggregation is safe.

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
   retained automatically. M8's separate versioned exposure-verification
   records do not change that generation-time overwrite behavior.
2. **Post-generation visual verification is separate evidence tied to the exact
   output SHA-256.** It records the checksum, date, GIS tool and version,
   inspected views and checks, result, and relevant observations. It does not
   require or permit manually editing the generated lineage sidecar.

The current QGIS documentation records successful verification of the exact
water-grid, whale-grid, and project-display artifacts. Reusable checksum-bound
inspection commands now exist for the whale display and the combined
vessel/domain display; their retained reports remain separate from generation
lineage and under the ignored local data root.

**A public display artifact is a derived spatial layer and needs the same
treatment.** Changing representation for the browser can introduce exactly the
errors visual inspection exists to catch — a wrong axis order, a dropped hole, a
clipped boundary. The whale, vessel-activity, and analytical-domain display
exports were therefore inspected in QGIS in their browser-facing forms, opened
directly through OGR rather than converted, with inspection bound to the exact
output checksums and refusing to run on a mismatch.
`analysis/scripts/qgis_inspect_whale_display_export.py` checks the whale file;
`analysis/scripts/qgis_inspect_vessel_domain_display.py` checks the vessel and
domain pair together.

The exposure display received the same separate treatment through
`analysis/scripts/qgis_inspect_exposure_display.py`. QGIS 4.2.1 / GDAL 3.13.2
opened display SHA-256
`1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb`
directly as EPSG:4326 GeoJSON and confirmed 2,793 nonempty valid features plus
the manifest's counts, parts, holes, vertices, area, extent, and threshold
flags. The local VSR snapshot was inspection context only and was not exported.

The distinct M7 presentation boundary is covered by focused TypeScript tests for
contract/version/identity rejection, safe public errors, generated result
selection, null/zero/exclusion semantics, denominator wording, complete
sensitivity disclosure, and independent exposure lifecycle behavior. Browser
integration separately verifies the SDK-rendered layer, exact 2,793 count,
alignment, ordering, controls, generated strings, accessibility, responsive
overflow, and isolated failures at all three required viewports. Neither kind of
evidence replaces deployed-route verification.

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
compare them with what the deployed application serves. M8 owns that gate and
is in progress; it has not yet performed the fresh raw-to-public chain.

The implemented `exposure_verification` boundary loads checksum-pinned retained
M6 tables/report through existing validators and reconstructs display, manifest
and application results entirely in memory. It creates only fresh ignored
request/result records, with artifact/check/tool/time identities and outcomes;
failures and earlier records are preserved. Generation lineage is untouched.
Evidence-reference hashes establish byte identity, not visual or scientific
approval. This is not a general workflow or GIS-inspection framework. See the
[procedure and workload-specific reserves](../analysis/README.md#post-generation-exposure-verification)
and [criterion/evidence handoff](m8-verification-handoff.md). Its small-record
disk reserves must not be applied to analytical generation or the full-chain run.

## Performance and publication-format verification

ADR 0021 selects the static format and Vercel Hobby host. Deployed verification
still requires evidence from the real outputs, including:

- byte size, feature count, geometry complexity, and raster dimensions where
  applicable;
- transfer size, time to first meaningful map, pan/zoom responsiveness, memory
  use, and behavior on a mid-range connection/device;
- whether the representation supports required symbology, legends, popups and
  attribution, and what access a visitor needs — a token-free public file or
  service, or one read with a scoped browser credential;
- redistribution conditions for each source and derivative; and
- author-confirmed Vercel Hobby, personal-use eligibility and free capacity, plus the
  separate ArcGIS basemap account's free-tier/billing status.

All three M5 input layers have now been measured locally. The whale GeoJSON is
3,277,329 bytes raw / 574,907 gzip / 396,852 Brotli; the vessel GeoJSON is
2,720,788 / 541,477 / 385,764 bytes; and the analytical-domain GeoJSON is
867,910 / 265,035 / 199,834 bytes. The two new files total 3,588,698 raw bytes
and 585,598 Brotli bytes; all three total 6,866,027 raw bytes and 982,450 Brotli
bytes. The complete static export is 35,862,761 bytes across 899 files. In the
latest local Chrome check, project-ready times were 2.30–3.34 seconds, and the
three layers remained usable through visibility changes at all required
viewports. That is enough to continue evaluating the same-origin route
without tiling or geometry simplification.

The exposure display has also been measured locally: 2,542,744 bytes raw,
528,235 bytes at gzip level 9, and 375,238 bytes at Brotli quality 11 for 2,793
features. Its paired manifest is 6,803 bytes and the small application-results
artifact is 31,381 bytes. Static same-origin delivery is selected by ADR 0021.
The M7 package is deployed and its public receipt, keyed browser behavior,
results pairing/text, layer order and visibility, failure isolation, keyboard
access, scrolling, responsive layouts, and VSR identity were verified. The
retained three-viewport browser run includes exact counts and order, visibility
changes without duplication, and no horizontal overflow. Independent numerical
and content review and author acceptance are recorded. The retained performance
run is narrower than the roadmap criterion: it applied 4× CPU throttling and a
100 ms / 10 Mbps model only to project GeoJSON routes, while external service
throttling was disabled. The later globally applied run passed with all required
request classes observed, five ready single-instance layers, working controls,
pan/zoom, scrolling and keyboard focus, and no application error.

These measurements are observations of this project's static assets and the
deployed functional checks described above. They are **not** a benchmark of
ArcGIS platform services, no ArcGIS service timing is reported, and the global
functional model does not establish real-device or low-end-device behavior. The
Location Platform agreement's benchmarking and
benchmark-publication clauses remain unresolved and must be settled before any
timing exercise that measures ArcGIS services.

A material representation change requires a later decision. No paid service is
an authorized fallback.

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
│   └── public/layers/     # Git-ignored staging for generated display layers
└── results/               # small versioned application results (exists)
```

`results/` contains the versioned M6 application-results contract, distinct from
ignored analytical bundles in `data/derived/` and ignored display staging in
`web/public/layers/`. No other implementation directory is scaffolded before
its milestone needs it.

## Explicitly deferred decisions

| Decision                                                                                    | Deferred until                                                                                              | Selection basis                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Exposure formula, normalization, and weighting                                              | **Resolved for exploratory use** in [ADR 0020](decisions/0020-propose-area-integrated-relative-exposure.md) | Accepted for bounded local execution on 2026-09-06, computed reproducibly, independently reviewed, and accepted by the owner for the public exploratory presentation. Limitations and proxy language remain mandatory.                                                                                                     |
| High-exposure threshold                                                                     | **Resolved for exploratory use** in ADR 0020                                                                | The qualified-area-weighted 90th percentile, reported with 80/95 and a positive-only reference. Sensitivity is recorded, including the materially non-robust comparison, and the owner accepted the bounded public wording.                                                                                               |
| Final public representation and host for project-derived whale, vessel, and exposure layers | **Resolved by ADR 0021**                                                                                    | Checksum-addressed static files beside the application on free Vercel Hobby. The accepted package passed receipt, public-origin, keyed-browser, release-time VSR, and whole-connection functional verification. The corrected review/acceptance copy awaits a reviewed, authorized public release.                            |
| ArcGIS Location Platform publication route                                                  | Unselected by ADR 0021                                                                                      | Actual hosted-data creation, storage and sharing capabilities remain unverified and are not M4 requirements. The narrower Location Platform basemap account, allowance and key checks passed for the selected static route.                                                                                               |
| ArcGIS Online publication route                                                             | Unselected by ADR 0021                                                                                      | Actual organization and publishing capabilities remain unverified.                                                                                                                                                                                                                                                        |
| Static application host                                                                     | **Resolved and verified by ADR 0021 / M4**                                                                  | Free Vercel Hobby, author-confirmed and deployed on 2026-09-07. HTTPS, stable origin, static-export limits, exact receipt and clean-browser verification passed. No paid fallback is authorized.                                                                                                                          |
| General visual-verification record across spatial outputs                                   | M8 reproducibility work                                                                                     | Layer-specific checksum-bound commands now exist for the three project input displays and exposure evidence. A general record must cover every spatial output's checksum, date, GIS tool/version, inspected views/checks, result, and observations without mutating generation lineage.                                   |
| [ADR 0002](decisions/0002-southern-california-study-area-extent.md) accepts                 |
| `receivers_50_nautical_miles` as the scope-reduced,                                         |
| system-performance-qualified AIS analytical domain: 50 nautical miles, exactly              |
| 92,600 metres, from the relevant NAIS reception stations, not from the coast.               |
| It is not empirical 2024 coverage. Outside-domain cells are excluded from                   |
| headline statistics and are not classified as low traffic. Receiver uptime,                 |
| station completeness, feed interruptions, antenna and terrain effects, and                  |
| observational completeness remain unknown or unverified. M2 is **Complete**:                |
| ADR 0019 resolves its final publication-posture criterion by prohibiting                    |
| project-hosted VSR copies and selecting direct publisher-service display, not by            |
| claiming that redistribution permission was granted.                                        |

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
