# Public derived-layer delivery assessment

Inspection date: **2026-09-04 (America/Los_Angeles)**. Repository baseline:
`83120fdb034909b441194d2c88d5bdf811b7879e`, branch
`research/m4-m5-delivery-assessment`. Initial working tree was clean.

## Recommendation and decision status

Proceed next with a **local whale-only GeoJSONLayer integration trial**, using a
deterministic WGS 84 GeoJSON export of the validated whale grid. If that trial
passes, propose static same-origin delivery alongside the exported application
on **Cloudflare Pages Free through author-run Direct Upload**. This is a
recommendation for review, not an accepted hosting decision, deployment, or
claim that M4/M5 is complete.

The measured whale export is 4,640,159 bytes before HTTP compression, with
4,516 features and 44,773 coordinate positions. It is small enough to justify
a browser trial without first introducing tiles or geometry simplification.
Static delivery avoids Location Platform feature-query metering for these
derived files and gives each release an immutable public artifact identity.
It retains the existing ArcGIS SDK, Esri basemap, and publisher-hosted VSR.

There is a material correction to earlier repository evidence: current Esri
documentation says **Location Platform hosted services are not shared publicly**.
A visitor-facing application can instead access private hosted content with
scoped developer credentials. A visitor who does not sign in is different
from a token-free service request. The earlier 2026-08-31 inventory appears
to have treated cross-product sharing guidance as applying to Location Platform.
Do not rely on its `Everyone` claim for implementation. The product-specific
[Location Platform sharing guide](https://location.arcgis.com/help/data-sharing-and-access/)
states this directly; the [feature-service sharing guide](https://developers.arcgis.com/documentation/portal-and-data-services/data-services/feature-services/sharing-and-security/)
also marks public sharing unavailable in its Location Platform branch.

Location Platform remains a conditional alternative using an item-scoped,
read-only browser key, if its real account and measured usage fit. ArcGIS Online
hosting is conditional on an **existing** organization with appropriate access
and an author-confirmed no-spending posture; none was accessible here.
Neither alternative is proved operational. If static GeoJSON fails the browser
gate, first measure a reviewed display export with fewer unused attributes.
Then reassess hosted features or tiled display with a separate value-query
plan. Do not simplify analytical geometry or invent final vessel/exposure
sizes to justify a route.

## Authority, ownership, and completed work

[Project brief](project-brief.md) owns scope and scientific language;
[roadmap M4](roadmap.md#m4--gis-application-foundation) and
[M5](roadmap.md#m5--core-input-layers) own completion;
[architecture](architecture.md#performance-and-publication-format-selection)
owns the publication boundary; [development](development.md) owns workflow;
[source register](data-sources.md) and [local data policy](../data/README.md)
own provenance and handling.
[ADR 0008](decisions/0008-deliver-the-application-as-a-static-export.md),
[ADR 0015](decisions/0015-adopt-a-hybrid-open-source-and-esri-gis-toolchain.md),
and [ADR 0019](decisions/0019-reference-the-publisher-hosted-vsr-service.md)
remain the accepted decisions. This assessment does not supersede them.

Completed in this session:

- Read repository guidance and required project documents; inspected application
  source/configuration and locked versions without building it.
- Rehashed the four explicitly scoped whale/water/domain evidence artifacts;
  checked whale lineage and exact preservation of every water-grid column.
- Measured whale schema, geometry, CRS, bounds, values, and local byte sizes.
- Created and repeated one local-only, unsimplified GeoJSON export and gzip
  encoding under ignored `data/interim/delivery-assessment/`. Both repeats
  reproduced the recorded bytes.
- Checked current official product, sharing, pricing, SDK, hosting, and source
  documentation. Account access was unavailable; no account state was changed.
- Checked this document's relative links, factual distinctions, and whitespace.
  Only this Markdown document is committed.

No VSR geometry was read by the export script, copied, converted, simplified,
or published. The script hashes domain evidence but exports only the whale
grid. No application source, M3 code, shared status document, or decision record
was changed. No build, browser benchmark, large processing run, full test suite,
deployment, publication, account creation, credential operation, or external
message was performed.

## Existing application and outstanding gates

Inventory from [web README](../web/README.md),
[package manifest](../web/package.json), [lockfile](../web/package-lock.json),
[Next configuration](../web/next.config.ts), and
[map implementation](../web/components/ArcgisMapFrame.tsx):

| Component | Existing implementation and delivery consequence |
|---|---|
| Framework | Next.js 16.3.3, React 19.2.8, TypeScript 5.9.3; npm lockfile. |
| ArcGIS | Locked `@arcgis/core` and `@arcgis/map-components` 5.1.20; Calcite 5.1.2. Use supported components for additional SDK UI. |
| Static boundary | `output: "export"`, `trailingSlash: true`, unoptimized images; `web/out/` contains the static site. No Node runtime, backend, database, or browser analysis. |
| Map lifecycle | Client-only map import; `arcgis-map` and `arcgis-zoom`; initial center longitude -119.4, latitude 33.6, zoom 7. Initialization has a 20-second bound. |
| Authentication | Build-time `NEXT_PUBLIC_ARCGIS_API_KEY` accesses default `arcgis/oceans`; SDK identity prompts are disabled. No `.env.local` is supplied in this worktree. |
| Existing operational layer | Publisher `WhaleAtlas_2026/FeatureServer/0`, `FID = 126`, stable layer ID, expected count of one, 15-second layer-load bound, owned-resource cleanup and isolated failure. |
| Controls | Native VSR visibility checkbox, status/warning, line legend, expandable source/disclaimer. VSR popups are disabled. No derived-layer legend, popup, control, or result panel exists. |
| Attribution | Application `Powered by Esri` fallback until readiness, then SDK dynamic attribution. New layers must retain this handoff and provide their own source credit. |
| Local verification | README records successful keyed basemap/VSR checks at 390 × 844, 820 × 1180, and 1440 × 900. These are prior evidence, not rerun here. |
| Deployment | None. Earlier shell size was approximately 28 MiB / 900 files; neither is a fresh measurement or an initial download measurement. |

M4 still needs deployment-environment build and reachable-current-main evidence,
real account capability/billing checks, and the conditional Esri-hosted test
where safe. The changed Location Platform sharing evidence must be reconciled
with that test's wording before execution. This assessment does not waive it.

M5 still needs measured public representations of the project-derived inputs,
anonymous end-to-end rendering, usable load time, units, sources/dates, controls,
legends, alignment, and public-artifact lineage. The implemented VSR slice alone
does not meet M5. Final vessel rules, the final vessel input, and exposure work
remain governed by M3/M6; a ready AIS period is not one of those outputs.

## Local whale and lineage measurements

Inputs were read only from:

```text
C:\Users\teche\socal-whale-vessel-risk-analytical-domain\data\interim\m2-domain-evidence
```

| Artifact | Bytes | SHA-256 verified in this session |
|---|---:|---|
| `blue-whale-density-grid.parquet` | 523,986 | `421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62` |
| `noaa-whale-footprint-water-grid.parquet` | 437,466 | `7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031` |
| `domain-candidate-masks.parquet` | 887,833 | `4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77` |
| `domain-evidence-report.json` | 6,752 | `eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98` |

The whale/water identities match the exact derived-output evidence in
[development's whale-transfer evidence](development.md)
and [roadmap](roadmap.md). Domain identities match
[analytical-domain evidence](analytical-domain-evidence.md#reproducible-calculation).
The source register records the upstream NOAA 2020b distribution, not these
derived files as new raw sources.

The whale sidecar SHA-256 is
`8e437e22baf956d726953cb450595126e973a98f6c44db023604cba374a4a025`.
It identifies `blue_whale_grid_transfer_v1`, processing steps 1.0.1,
run `whale-grid-1d27df77bf1da01155fd`, and completion
`2026-08-29T04:50:52.894367Z`. It binds the exact water-grid checksum and
the `Blue_whale_summer_fall` source using `directory-tree-sha256-v1`:
`1bfdb2bc75b26a3a33aa81952f5fc6cc58bd8e8b73a93362017fa06f76ec94cf`.
That directory digest is not the downloaded ZIP digest
`5677b95178b507337d2bdf048c9ad69383b0b48f7c7a1cd829774eeecd8c7a5d`
in the source register. The raw ZIP/directory were not rehashed or revalidated
here; their relationship is inherited provenance, not a new raw-source audit.
The run's retrieval fields are null; the documented 2026-08-25 retrieval date
comes from the source register, not filesystem dates.

The sidecar's generation-time `visual_inspection_status: not_completed`
remains unchanged. Separate documentation records QGIS 4.2.1 / GDAL 3.13.2
verification on 2026-08-27 against the identical whale output checksum.
That establishes prior verification of the Parquet content, not visual
verification of this new GeoJSON.

| Measurement | Result |
|---|---|
| Rows / unique cell IDs | 4,516 / 4,516 |
| CRS | EPSG:3310, from GeoParquet CRS metadata; projected metres |
| Decoded WKB types | Polygon and MultiPolygon; 4,561 polygon parts, 35 interior rings |
| Coordinate positions | 44,773, including repeated ring-closing positions |
| Positions per feature | Minimum 4; median 5; interpolated 95th percentile 11.5; maximum 323 |
| Geometry checks | No empty or invalid source geometry; all original water-grid columns equal, including geometry and row order |
| Nulls | Zero in every column |
| EPSG:3310 bounds | x -189429.372291 to 272786.624451 m; y -667727.411447 to -333263.927782 m |
| Export geographic bounds | Longitude -122 to -117.097556437; latitude approximately 32 to 35.0000001083 degrees |
| Modeled density range | 0.00083394 to 0.007648247 animals/km² |

The decoded Polygon/MultiPolygon mix is the actual WKB measurement; earlier
QGIS documentation describes its layer geometry type as MultiPolygon. A layer
driver's advertised type is not necessarily each stored WKB's type.

There are 18 attributes plus binary geometry:

| Attributes | Stored type / meaning |
|---|---|
| `cell_id` | String; stable grid identity |
| `row_index`, `column_index` | int16; grid position |
| `cell_x_min_m`, `cell_y_min_m`, `cell_x_max_m`, `cell_y_max_m` | int32; nominal parent bounds in EPSG:3310 metres |
| `water_area_m2`, `water_area_km2` | double; actual biological-support water area |
| `modeled_abundance_allocation_animals` | double; allocated modeled animals, not observed counts |
| `modeled_density_animals_per_km2` | double; allocation divided by full cell water area |
| `source_covered_water_area_m2`, `source_covered_water_area_km2` | double; source-supported area |
| `uncovered_water_area_m2`, `uncovered_water_area_km2` | double; uncovered residual |
| `source_coverage_fraction` | double; unitless source support, not AIS completeness |
| `coverage_status` | String; explicit support classification |
| `source_polygon_count` | int32; contributing source polygons |

Lineage reports all 4,516 cells with complete source support, total water area
107,728.695924 km², and conserved allocation 344.1406562623342 modeled animals.
These are upstream diagnostic totals over biological support, not new
headline analytical-domain or VSR statistics. The 5 km reporting grid does not
improve the approximately 0.1-degree biological model resolution.
`UNCERTAINTY`/CV is **not propagated** into this grid.

### Local representation experiment

The reproducible script below uses the existing local analysis environment.
It preserves all attributes, feature order, IDs, polygon parts, and holes;
transforms stored vertices with explicit x/y ordering to WGS 84; orients
exteriors counterclockwise and holes clockwise; and emits compact UTF-8/LF
JSON without coordinate rounding, simplification, clipping, or densification.
No analysis values or areas are recomputed in geographic coordinates.

| Local output | Bytes | MiB (1,048,576 bytes) | SHA-256 |
|---|---:|---:|---|
| `whale.geojson` | 4,640,159 | 4.425 | `d22b8ae36e61a1ef56dc8b657f9011c810b4ac1a45635c5529fd37932c3c15d3` |
| `whale.geojson.gz` | 656,594 | 0.626 | `0cbf4b93ce53707dd808d015cf7469a9c9e1b502c3ac594b595d3637b17fc109` |

The gzip specimen uses level 9 and `mtime=0`. Both successful invocations
produced the same byte identities; read-back preserved every attribute and
found valid geometry for all features. An initial probe assumed all features
were MultiPolygon and stopped before writing output; using polygon-part
iteration resolved that measurement-script error.

Maximum stored-vertex round-trip displacement was 9.78 × 10⁻⁹ m. Maximum
sampled geographic-edge midpoint displacement against the original projected
chord was **0.368374 m**. The latter is an edge-midpoint diagnostic, not a proven
whole-edge error bound or an area-conservation check. PROJ reports 4 m operation
accuracy; numerical round-trip precision is not datum accuracy. The exact
pipeline and versions are printed by the script. A production export must
record the operation and review display tolerances; if needed, densify in
EPSG:3310 before transformation and measure the resulting file again.

**Unverified:** this GeoJSON's map appearance, ArcGIS loading, memory use,
HTTP transferred bytes, server compression, initial load time, and interaction
performance. The gzip file is a local encoding specimen, not evidence that a
host negotiates that encoding. Serve GeoJSON with a suitable JSON media type;
test actual `Content-Encoding` rather than pointing the SDK at a raw gzip file.
The full JSON is downloaded and decoded for client-side use; filtering displayed
features does not make this a spatially paged service. Browser geometry/index
memory can exceed compressed and decoded file sizes. No browser-memory factor
or visitor capacity is inferred here.

No final vessel or exposure artifact was available for assessment. Their sizes,
field counts, geometry complexity, combined browser footprint, and final
representation are **unmeasured**; do not multiply the whale file by three.

## Practical options

Official pages below were inspected on 2026-09-04. Live pages can change;
recheck before release. Cloudflare's limits page displayed an update date of
2026-09-05 when inspected; that page label is not this session's inspection date.

| Route | Capability and anonymous access | Free-only fit and limitations |
|---|---|---|
| Location Platform feature service | Feature queries suit field-based rendering and per-cell values. Current public-sharing documentation requires credentials for hosted data; a scoped browser key can support visitors without sign-in. | Conditional. Actual billing, item access, hosting privileges, storage and query headroom unknown. No token-free hosted endpoint is established. |
| Location Platform vector/map tiles | Product supports hosted vector and map tiles, not hosted image/scene creation in its limited organization. View-dependent tiles can reduce client geometry work. | More publishing and lineage work, with separate storage, generation and bandwidth meters. Not justified by this whale measurement alone. Tiles need measured detail/zoom choices; exact per-cell popups need a separately verified value-query design. |
| Existing ArcGIS Online organization | Hosted features can be published from GeoJSON with publishing/content privileges; public sharing additionally needs the public-sharing privilege and organization permission. | No organization was verified accessible. Recurring credit consumption is not inherently free, even if an organization has included credits. Do not buy a subscription/trial or presume institutional sponsorship. |
| Static WGS 84 GeoJSON via ArcGIS `GeoJSONLayer` | SDK accepts Polygon/MultiPolygon, field schemas, renderer, popup template and source copyright. Public HTTPS asset needs no layer credential; basemap still uses its existing credential model. | Recommended trial. Whole-file transfer/decoding; host limits and browser performance remain gates. No direct GeoParquet ingestion is proposed. |

Sources: [service/product matrix](https://developers.arcgis.com/documentation/portal-and-data-services/faq/),
[feature services](https://developers.arcgis.com/documentation/portal-and-data-services/data-services/feature-services/introduction/),
[Location Platform sharing](https://location.arcgis.com/help/data-sharing-and-access/),
[Online publishing](https://doc.arcgis.com/en/arcgis-online/manage-data/publish-features.htm),
[Online sharing](https://doc.arcgis.com/en/arcgis-online/share-maps/share-items.htm),
[GeoJSONLayer reference](https://developers.arcgis.com/javascript/latest/references/core/layers/GeoJSONLayer/),
and [VectorTileLayer reference](https://developers.arcgis.com/javascript/latest/references/core/layers/VectorTileLayer/).
Use explicit scalar fields in GeoJSON rather than embedding lineage objects as
feature attributes; preserve complete provenance in a separate public manifest.

### Location Platform allowances and account conditions

Current [pricing](https://location.arcgis.com/pricing/) lists:

| Meter | Published free allowance |
|---|---:|
| Feature storage | 250 MB |
| Tiles/files/attachments storage | 250 MB |
| Feature-query bandwidth | 125 MB per billing cycle |
| Feature-edit bandwidth | 125 MB per billing cycle |
| Vector-tile bandwidth | 25 GB per billing cycle |
| Map-tile bandwidth | 25 GB per billing cycle |
| Tiles generated during publishing | 25,000 per billing cycle |
| Basemap tiles / sessions | 2,000,000 tiles / 1,000 sessions, distinct metering models |

These are product allowances, not this author's balances. Stored feature
database size is not GeoParquet or GeoJSON file size. Query bandwidth is not a
request-count allowance. Neither the local gzip size nor its ratio establishes
feature-service response bytes or billable consumption. Measure query payloads,
paging and usage after a separately authorized minimal test before estimating
monthly traffic capacity.

The [billing guide](https://location.arcgis.com/help/billing/) says PAYG is off
by default for new accounts and free tiers refresh by billing cycle. Without
PAYG, exhausted service allowances stop access. It also warns that disabling
PAYG after storage overage does not immediately end existing storage charges.
Therefore even an observed off setting would need to be considered with current
storage state; no account mutation or blanket zero-cost assurance follows here.

For a later keyed alternative, [item-scoped API key documentation](https://developers.arcgis.com/documentation/security-and-authentication/api-key-authentication/api-key-credentials/location-platform/)
supports explicit item access and referrer restrictions. Any author-authorized
key change would need rebuild/redeployment, expiry/rotation planning, and checks
that the browser credential grants only intended reads. No such change occurred.

For Online, [credit documentation](https://doc.arcgis.com/en/arcgis-online/administer/credits.htm)
lists feature storage at 2.4 credits per 10 MB per month, calculated hourly.
This assessment neither converts local file bytes into service credits nor
authorizes consuming paid capacity. Record whether an existing allocation is
explicitly usable under the author's free-only constraint before considering it.

### Static host candidate

Cloudflare Pages Free is a concrete candidate for both `web/out/` and immutable
derived GeoJSON assets. [Static asset requests](https://developers.cloudflare.com/pages/functions/pricing/)
are documented as free and unlimited when they do not invoke Functions.
[Pages limits](https://developers.cloudflare.com/pages/platform/limits/) list
20,000 files, 25 MiB per file, 500 builds/month, and a 20-minute build timeout.
The measured whale JSON fits the per-file limit. The complete current export
has not been counted or built here.

[Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/)
accepts locally built assets and supplies a `pages.dev` address. It avoids a
GitHub App installation and lets ignored generated data enter a reviewed
deployment artifact without entering Git. Wrangler supports 20,000 files;
dashboard drag-and-drop supports only 1,000. Prefer the former for a future
authorized deployment given the earlier roughly 900-file shell. Direct Upload
projects cannot later switch to Git integration without a new project.

Proposed packaging: produce the static app, assemble an isolated ignored release
directory from its output plus checksum-addressed data and sanitized metadata,
verify that directory, then let the author upload it after authorization.
Do not place generated datasets in tracked `web/public/`. Deploy the whole
release together and record the application commit and data checksums.

For updates, generate new checksum-addressed filenames and pin the application
to one release manifest; never replace different bytes at an immutable URL.
Keep the prior complete release available for an author-authorized rollback.
Long-lived caching applies to immutable artifacts; the release entry point
must revalidate so it cannot mix new application code with stale data. Record
both analytical-generation and export dates, and check fetched bytes against
the pinned checksum after each upload. Any new hosted-service alternative
needs the same version mapping plus service schema/count/value read-back;
do not assume a successful import transferred every feature or preserved IDs.

Same-origin assets avoid a separate CORS dependency. If a different public
static origin is chosen, explicitly test HTTPS, CORS, JSON media type,
cache headers, anonymous access and absence of authentication redirects.
Keep any Functions, Worker, storage bindings, paid add-ons, or domain purchase
out of this proposed static-only route.

The [Cloudflare subscription agreement](https://www.cloudflare.com/terms/)
subjects use to product limits and acceptable-use terms, prohibits infringement,
and allows termination of free service. Free pricing is not an availability
guarantee. No Cloudflare account, project, plan, or accepted terms were inspected
or created. Author availability and acceptance remain prerequisites.

## Attribution and source-use posture

All routes retain [Esri SDK attribution](https://developers.arcgis.com/javascript/latest/licensing/):
Esri branding plus data-provider credit, with the existing dynamic attribution
and loading/error fallback intact. The SDK guide says no additional SDK purchase
is needed with the supported account arrangements, but service usage can cost
money and product terms still apply. The
[Location Platform terms index](https://location.arcgis.com/help/terms-of-use/)
links the agreement and supplemental data terms. The linked
[Location Platform agreement, revised November 21, 2025](https://www.esri.com/content/dam/esrisites/en-us/media/legal/platform/platform-legal.pdf),
Article 2.1, permits development, testing and deployment under its conditions;
Article 3.1 requires retained attribution and includes application-user terms.
Articles 3.1(b)(6) and 3.1(c)(6)(F) restrict platform benchmarking and public
communication of benchmark results without prior written permission. Before
timing tests against ArcGIS services or publishing platform benchmark results,
the author must resolve the applicable agreement and permission scope. Local
file-size measurements here do not benchmark ArcGIS. The public agreement was
read; the author's actual accepted or superseding agreement remains unverified.

The [NOAA 2020b metadata](https://www.fisheries.noaa.gov/inport/item/64349)
still names the selected distribution and its no-warranty use constraint.
Retain the source register's qualified derivative-publication assessment:
citation and disclaimer support the proposed use; do not relabel that as an
explicit publisher permission or an invented licence. Link the requested
Becker et al. citation from the source register, identify NOAA Fisheries/SWFSC,
2020b, source retrieval date, derived processing date and export date.

The live [NOAA AIS FAQ](https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf),
Appropriate Use and Citations sections, permits derived products with credit
and restricts use to coastal/ocean planning; the cited USCG conditions prohibit
charging for the data. Retain NOAA OCM/Marine Cadastre and USCG attribution for
eventual aggregate vessel products. The current live PDF identifies itself as
a June 2026 FAQ, whereas the retained source register describes May 2026.
It was consulted for current use terms only, not substituted for the immutable
source evidence or used to revise processing rules.

Eventual exposure attribution must include both analytical inputs and method
lineage, once implemented. Its public geometry must not be a copied or
VSR-clipped geometry: the immutable VSR input remains local to fractional
statistics. ADR 0019 continues to control direct publisher-service display,
Danielle Alvarez/CMSF/BWBS credit, disclaimer and release-time comparison.
A changed remote boundary must be reconciled with the analysis or omitted;
a warning alone is insufficient.

## Actual account evidence and author actions

The tools exposed in this session included public web retrieval and shell
execution, but no connected browser/account inspection tool. A bounded
read-only listener check found no debugging endpoint on localhost ports 9222
or 9223. No accessible authenticated ArcGIS session was established. This is
not proof that the author has no signed-in browser or no organization.

No cookies, browser profiles, credential stores, other-worktree keys or
environment secrets were searched. No credentials were printed. Existing
reported Location Platform ownership and prior localhost basemap success are
inherited evidence only; neither proves publishing access.

| Missing check | Needed author evidence, privately inspected without mutation |
|---|---|
| Account product | Location Platform confirmed, Online organization confirmed, or unavailable; no account identifiers in committed evidence |
| LP hosting/access | Feature/vector/map-tile creation controls and applicable item-access mechanism; actual sharing controls compared with the current documentation |
| LP free-only state | PAYG mode, absence of storage-overage exposure, current aggregate storage/query/edit/tile usage and adequate remaining headroom; keep invoices, payment details and subscription identifiers private |
| Online, if already available | Organization membership, content/publishing/public-sharing privileges, allowed service types, suitable existing credit allocation/storage, and no-spending permission |
| Static host | Existing Pages access or later author approval to establish a free account/project; actual free plan, stable origin and terms acceptance |
| Public basemap | Author supplies the scoped origin-restricted build credential privately in the later implementation/deployment context; no key value in this assessment |

The author can return non-sensitive capability outcomes and pass/fail headroom
conclusions using [development's account checklist](development.md#arcgis-account-type-capability-checks-and-service-access),
with the public-sharing correction above applied during owner review. No
author login is required to begin the local whale export/integration work.
Account creation, publication, spending, deployment, or credential changes need
a separate authorized session; none is authorized by this assessment.

## Proposed next implementation session

Proposed branch: `feat/m5-whale-static-delivery`, isolated from M3 work.
First coordinate ownership with M3 before adding any production exporter under
`analysis/` or changing shared documents. No new directory is proposed for
exposure contracts or results.

### Work possible with the whale grid now

1. Review the recommendation and record a narrow publication ADR after browser
   evidence supports it. Reconcile the Location Platform public-sharing claim
   in the owning documents; keep route recommendation separate from acceptance.
2. Promote the local experiment into a versioned Python export boundary, with
   explicit source checksum, target CRS/axis order, field mapping, stable IDs,
   output destinations and refusal of arbitrary overwrites. Preserve analytical
   attributes exactly; derive any display-only IDs deterministically.
3. Write separate export lineage: source artifact/run/configuration, upstream
   source references, source visual-verification checksum, exporter version,
   transform/precision choices, output checksum/count/bounds/units and time.
   Public metadata must omit local paths, account identifiers and secrets.
4. Integrate `GeoJSONLayer` through the current client-only map lifecycle.
   Define polygon geometry and fields explicitly, a stable object-ID mapping,
   density renderer and popup template. Add a whale visibility control, units
   and source/use disclosure. Keep the VSR outline above the whale fill.
5. Show modeled density in animals/km² and biological-support water area in km²;
   explain the summer–fall multi-year model and 5 km reporting grid. Do not show
   derived CV, observed-whale counts, AIS completeness, or exposure results.
   Classification breaks require a documented display rationale.
6. Verify the exact export in QGIS and in the SDK after the other session's
   memory-sensitive work finishes. Then run required web quality gates and a
   static build with privately supplied local configuration.
7. Prepare a checksum-bound release directory and deployment instructions.
   Author-run public upload is a later explicitly authorized action.

Acceptance checks for that session:

- Two clean exports produce identical data bytes; checks reject wrong source
  hash/CRS, invalid geometry and non-finite values. Known polygon-with-hole and
  axis-order fixtures verify transformation and field preservation.
- Exact 4,516 unique cells and original analytical values survive export and
  SDK queries. Verify polygon parts/holes, bounds and sampled boundary fidelity;
  investigate the tiny northern latitude overshoot rather than clipping silently.
- QGIS and SDK views align at full extent, coast/islands and grid detail;
  visual evidence binds the actual export checksum. Accept any densification
  or precision tolerance explicitly; do not infer accuracy from round-trip error.
- Required 390 × 844, 820 × 1180 and 1440 × 900 views retain readable units,
  working popups/visibility/keyboard focus, visible attribution and no overflow.
  Repeated readiness/remounts create one layer; blocking whale delivery leaves
  basemap/VSR usable and gives a bounded accessible warning without sign-in.
- Measure cold and warm browser requests, encoded/decoded response sizes,
  time to meaningful whale rendering, pan/zoom response and available memory
  diagnostics. Record hardware, browser, cache, CPU/network settings and runs.
  Resolve the platform-benchmark terms described above before any affected
  timing exercise; routine functional verification remains a separate check.
  **Proposed performance targets for review:** median whale-ready within
  5 seconds after map readiness across three cold runs at 10 Mbps/100 ms
  latency/4× CPU slowdown; no crash or sustained unresponsive interaction.
  These are project acceptance choices, not observed results or SDK guarantees.
  Agree the target before testing and report failures without relaxing it silently.
- The final static release stays under the selected host's actual file/count
  limits and contains no source data, VSR geometry, private lineage or credentials
  with publishing privileges. Browser basemap keys remain public and scoped.
- After separate deployment authorization: anonymous clean-browser HTTPS
  verification from the stable origin; actual compression, cache and CORS
  behavior; source metadata reachable; public bytes match the release checksum;
  deployed application commit matches the intended current main release.
  A successful local trial does not satisfy this public gate.

### Work waiting on final vessel/exposure outputs

Measure each exact validated final artifact when M3/M6 produces it: counts,
fields, CRS, geometry complexity, file/encoded sizes and combined browser cost.
Preserve final vessel units, analytical period (July–November 2024), population
and gap/speed/edge assumptions; speed is separate under ADR 0006. No candidate
vessel grid is promoted by this assessment.

Apply the accepted `receivers_50_nautical_miles` domain at the analytical
boundary. It is 92,600 metres from reception stations, not the coast and not
empirical 2024 coverage. Broader whale-support/context can remain visible but
outside-domain cells must not look like observed low traffic or enter headline
statistics. Reporting geometry and qualification must come from validated
downstream work, not a browser clip.

Only after the exposure method and outputs exist should M7 add their layer,
legend, units and precomputed statistics. Exported values and displayed
statistics must match their authoritative inputs; public display is never the
source of recomputed VSR fractions. Repeat combined-layer performance, source
rights, no-VSR-copy, version consistency and release checks then.

### Proposed owner updates, not performed here

- `docs/development.md`, `docs/roadmap.md`, `docs/architecture.md`,
  `web/README.md`, `AGENTS.md` and any overview repeating LP public sharing:
  review against the current product-specific documentation, distinguish
  token-free services from visitors using a scoped browser key, and adjust
  conditional test instructions without dropping M4 evidence requirements.
- Architecture has stale descriptions of VSR integration as unimplemented;
  reconcile with source and M5's completed local slice. The roadmap's toolchain
  inventory should distinguish Calcite 5.1.2 from Maps SDK 5.1.20.
- `docs/data-sources.md`: owner reviews the live FAQ revision separately from
  immutable retrieval provenance; do not silently replace the retained file.
- Following implementation, owners add the accepted export/hosting decision,
  commands, source-to-public-artifact mapping and actual validation results.
  Milestone completion remains their criterion-by-criterion determination.

## Handoff state

Assessment and local measurements are complete. Account privileges, host
availability, new-export visual inspection, browser performance, service usage,
actual transfer encoding, public loading and deployment remain pending.
Heavy builds, QGIS/browser runs and combined-layer measurements were deferred
to respect the concurrent memory-sensitive session. No full analysis/web suite
was run for this Markdown-only change.

The next useful action is the scoped whale export/integration session above,
while the author supplies private account capability outcomes. The static route
is conditional on its trial and host access; the final vessel/exposure route
must be reevaluated against actual outputs. No M4/M5 status was changed.

## Reproduce the local experiment

From this worktree root, save the exact script below as
`data/interim/delivery-assessment/inspect_whale.py` (ignored), then run:

```powershell
& analysis/.venv/Scripts/python.exe data/interim/delivery-assessment/inspect_whale.py
```

The existing environment used Python 3.13.7, PyArrow 25.0.1, Shapely 2.1.2,
Pyproj 3.7.2 and PROJ 9.5.1. Recreate it from the committed analysis uv lock
if needed, outside the concurrent heavy run. The script uses PyArrow directly,
avoiding the documented local GDAL Parquet-driver problem. It prints
measurements, writes only its two ignored output files, and refuses differing
existing output bytes. Paths deliberately name only the authorized source
directory. The full script is retained here because ignored evidence alone
would not make the committed assessment reproducible.

```python
import gzip
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pyarrow
import pyarrow.parquet as pq
import pyproj
import shapely
from shapely.geometry import mapping, shape
from shapely.ops import transform

source = Path(r'C:\Users\teche\socal-whale-vessel-risk-analytical-domain\data\interim\m2-domain-evidence')
destination = Path(__file__).resolve().parent
expected = {
    'blue-whale-density-grid.parquet': '421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62',
    'noaa-whale-footprint-water-grid.parquet': '7229098c7460d42ddf0e0377413859fa12e9f7c7bf1d2308beedfc655c087031',
    'domain-candidate-masks.parquet': '4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77',
    'domain-evidence-report.json': 'eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98',
}
identities = {}
for name, checksum in expected.items():
    raw = (source / name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == checksum, name
    identities[name] = {'bytes': len(raw), 'sha256': actual}
table = pq.read_table(source / 'blue-whale-density-grid.parquet', use_threads=False)
grid = pq.read_table(source / 'noaa-whale-footprint-water-grid.parquet', use_threads=False)
lineage_path = source / 'blue-whale-density-grid.parquet.lineage.json'
lineage = json.loads(lineage_path.read_text(encoding='utf-8'))
assert lineage['output']['sha256'] == expected['blue-whale-density-grid.parquet']
assert lineage['inputs']['target_grid']['sha256'] == expected['noaa-whale-footprint-water-grid.parquet']
for name in grid.column_names:
    assert table[name].equals(grid[name]), name
geo = json.loads(table.schema.metadata[b'geo'])
geometry_column = geo['primary_column']
crs = pyproj.CRS.from_json_dict(geo['columns'][geometry_column]['crs'])
assert crs.to_epsg() == 3310
geometries = shapely.from_wkb(table[geometry_column].to_pylist())
assert bool(np.all(shapely.is_valid(geometries)))
assert not bool(np.any(shapely.is_empty(geometries)))
vertices = shapely.get_num_coordinates(geometries)
parts = shapely.get_parts(geometries)
to_wgs = pyproj.Transformer.from_crs(crs, 4326, always_xy=True)
to_source = pyproj.Transformer.from_crs(4326, crs, always_xy=True)
features = []
max_roundtrip = 0.0
max_chord_midpoint = 0.0
for row, geometry in zip(table.to_pylist(), geometries):
    row.pop(geometry_column)
    converted = shapely.orient_polygons(transform(to_wgs.transform, geometry))
    original_coordinates = shapely.get_coordinates(geometry)
    x, y = to_wgs.transform(*original_coordinates.T)
    rx, ry = to_source.transform(x, y)
    max_roundtrip = max(max_roundtrip, float(np.max(np.hypot(rx-original_coordinates[:, 0], ry-original_coordinates[:, 1]))))
    for polygon in shapely.get_parts(converted):
        for ring in [polygon.exterior, *polygon.interiors]:
            coordinates = np.asarray(ring.coords)
            px, py = to_source.transform(*coordinates.T)
            midpoints = (coordinates[:-1] + coordinates[1:]) / 2
            mx, my = to_source.transform(*midpoints.T)
            max_chord_midpoint = max(max_chord_midpoint, float(np.max(np.hypot(mx-(px[:-1]+px[1:])/2, my-(py[:-1]+py[1:])/2))))
    features.append({'type': 'Feature', 'id': row['cell_id'], 'properties': row, 'geometry': mapping(converted)})
payload = (json.dumps({'type': 'FeatureCollection', 'features': features}, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
encoded = gzip.compress(payload, compresslevel=9, mtime=0)
decoded = json.loads(payload)
assert len(decoded['features']) == table.num_rows
assert all(shapely.is_valid(shape(f['geometry'])) for f in decoded['features'])
for f, row in zip(decoded['features'], table.to_pylist()):
    row.pop(geometry_column)
    assert f['properties'] == row
outputs = {}
for name, raw in [('whale.geojson', payload), ('whale.geojson.gz', encoded)]:
    path = destination / name
    if path.exists():
        assert path.read_bytes() == raw, 'Refuse replacement of different bytes'
    else:
        path.write_bytes(raw)
    outputs[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
report = {
    'inputs': identities,
    'lineage_sha256': hashlib.sha256(lineage_path.read_bytes()).hexdigest(),
    'schema': {field.name: str(field.type) for field in table.schema},
    'null_counts': {name: table[name].null_count for name in table.column_names},
    'features': table.num_rows, 'unique_cell_ids': len(set(table['cell_id'].to_pylist())),
    'crs': crs.to_string(), 'geometry_types': sorted(set(g.geom_type for g in geometries)),
    'polygon_parts': len(parts), 'interior_rings': int(sum(shapely.get_num_interior_rings(parts))),
    'vertices': int(sum(vertices)), 'vertex_min_median_p95_max': [float(v) for v in np.percentile(vertices, [0,50,95,100])],
    'bounds_3310': shapely.total_bounds(geometries).tolist(),
    'bounds_4326': shapely.total_bounds([shape(f['geometry']) for f in features]).tolist(),
    'density_min_max': [min(table['modeled_density_animals_per_km2'].to_pylist()), max(table['modeled_density_animals_per_km2'].to_pylist())],
    'all_grid_columns_preserved': True, 'max_vertex_roundtrip_metres': max_roundtrip,
    'max_geographic_chord_midpoint_error_metres': max_chord_midpoint,
    'transformation': to_wgs.definition, 'transformation_accuracy_metres': to_wgs.accuracy,
    'outputs': outputs,
    'versions': {'python': platform.python_version(), 'pyarrow': pyarrow.__version__, 'shapely': shapely.__version__, 'pyproj': pyproj.__version__, 'proj': pyproj.proj_version_str},
    'visual_verification': 'not_performed', 'browser_performance': 'unverified',
}
print(json.dumps(report, indent=2))
```
