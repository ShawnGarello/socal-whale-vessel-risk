# socal-whale-vessel-risk

A GIS analysis of where modeled blue-whale habitat and commercial vessel activity overlap off Southern California, and how much of that overlap falls inside California's Vessel Speed Reduction zone.

> **Status: in development.** M1 through M6 are complete; M7 is in progress.
> The ready AIS period contains all 153 dates and 15,458,567 cleaned commercial
> observations. The exact water grid and modeled-whale transfer are reproducible
> and visually verified. All four full-period candidate vessel grids were
> generated, repeated, compared and inspected in QGIS.
>
> ADR 0018 is **Accepted**: it selects 300 seconds / 30 knots with explicit
> limitations. A production vessel-input command reuses the tested aggregation
> engine and adds separate descriptive movement-speed fields. The final
> period-wide vessel grid and speed summaries were generated, reproduced
> byte-identically, independently verified and inspected in QGIS on 2026-09-05.
> Acceptance does not claim the thresholds are scientifically validated, and
> publisher-transfer and observational completeness remain unverified.
>
> The web application displays the publisher-hosted VSR boundary directly;
> project copies of VSR geometry are prohibited. It also displays this
> project's own modeled blue-whale density grid, exported deterministically to
> WGS 84 GeoJSON and verified on 2026-09-06 in QGIS and in a browser at the
> three documented viewports. That layer is served as a static same-origin file
> and its identity is checked against its checksum in the browser.
> The accepted commercial-vessel activity and receiver-qualified analytical
> domain are now exported through the same checksum-bound presentation route
> and were verified locally in QGIS and Chrome at the same viewports. Vessel
> activity starts hidden, the domain remains visible as an outline, and the
> interface distinguishes excluded water from low or zero recorded activity.
>
> **The reviewed M4 input-layer application is deployed at the stable URL below and
> M4 is complete.** Route-specific plan, eligibility,
> basemap-capacity and browser-key checks passed on 2026-09-07. The approved
> checksum-bound package from merged `main` is reachable and its three pinned
> input files match exactly. Clean Chrome checks passed at all required
> viewports. After Production Toolbar was disabled for this project and the
> unchanged approved package was redeployed, all 900 public files matched the
> approved receipt byte-for-byte.
> The exposure method and its distinct display/results delivery contracts are
> implemented, independently reviewed for exploratory public presentation, and
> author-accepted with their limitations and prominent log-traffic sensitivity.
> **That review is not validation of collision probability, observed encounters,
> or VSR effectiveness.** The exact checksum-paired M5/M7 package from merged
> `main` was deployed on 2026-09-09 and passed public receipt, header, keyed
> responsive-browser and release-time VSR checks. A later whole-connection
> functional run applied the documented network profile to the complete page,
> including JavaScript, basemap, and publisher VSR requests, and passed. A
> separate criterion audit closed M5 and M6. M7 remains in progress only because
> the corrected review/acceptance sentence is implemented and fully tested on
> this branch but is not yet in a reviewed, authorized public release. See
> the [roadmap](docs/roadmap.md), the
> [M5–M7 closure audit](docs/m5-m7-closure-handoff.md), the
> [M5 whale display handoff](docs/m5-whale-display-handoff.md), the
> [M5 vessel/domain display handoff](docs/m5-vessel-domain-display-handoff.md), the
> [M3 handoff](docs/m3-completion-handoff.md), the
> [M6 exposure handoff](docs/m6-exposure-foundation-handoff.md), the
> [M6 exposure-results delivery handoff](docs/m6-exposure-results-delivery-handoff.md), and the
> [M7 exposure-interface handoff](docs/m7-exposure-interface-handoff.md), and the
> [M7 release-integration handoff](docs/m7-release-integration-handoff.md), and the
> [M5/M7 production candidate handoff](docs/m7-production-candidate-handoff.md).

## Why

The Southern California Bight carries some of the densest commercial shipping traffic in the United States and also holds foraging habitat for endangered blue whales. California's [Protecting Blue Whales and Blue Skies](https://bluewhalesblueskies.org/) program responds with voluntary Vessel Speed Reduction (VSR) zones, asking large vessels to slow down inside designated waters during a defined season.

These datasets originate from different sources, in different formats and at different resolutions, and require deliberate normalization before they can be compared in one transparent, reproducible analysis. This project brings the three onto a common study area and grid, and documents every step that gets them there.

## The question

> Where does modeled blue-whale habitat overlap with commercial vessel activity off Southern California, and how much of that relative exposure occurs inside versus outside the current Vessel Speed Reduction zone?

## Version 1 scope

Version 1 is an analytical MVP, not a map viewer: it produces a derived result rather than displaying layers someone else published. It is planned to include —

- a defined Southern California study area, projection, and analysis grid;
- an authoritative VSR zone boundary and its season definition;
- a modeled blue-whale density or distribution layer;
- processed commercial AIS vessel activity, with vessel speed where the data supports it;
- a documented **relative exposure** calculation combining whale density and vessel activity;
- a derived exposure / hotspot layer;
- inside-versus-outside VSR summary statistics;
- an interactive ArcGIS web application;
- reproducible processing, with documented methodology, provenance, assumptions, and limitations.

Underwater noise, vessel emissions, seasonal breakdowns, and scenario comparison are **out of scope for Version 1**. They remain genuine directions for later versions — see [docs/roadmap.md](docs/roadmap.md).

## Current status

| Area                        | State                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Project scope and roadmap   | Documented                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Architecture                | Accepted and refined; Python/QGIS/Esri responsibilities and the publisher-hosted VSR display exception are recorded                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Data sources                | **M2 complete** — downloaded and inspected; properties, licensing, limits, and public-use/publication postures recorded with a reproducible provenance manifest. VSR redistribution permission remains unconfirmed, so project-hosted copies are prohibited                                                                                                                                                                                                                                                                                                                             |
| Study area                  | **Accepted with separate roles** — the map/context extent, modeled-whale-support water geometry, and scope-reduced `receivers_50_nautical_miles` analytical domain are distinct; see [ADR 0002](docs/decisions/0002-southern-california-study-area-extent.md)                                                                                                                                                                                                                                                                                                                           |
| Processing workflow         | **M3 complete** — ready 153-date AIS input; verified water/whale grids and full candidate matrix; the selected vessel rules of [ADR 0018](docs/decisions/0018-use-vessel-kilometres-for-grid-activity.md) were accepted after real production generation, byte-identical repetition and QGIS validation. See [analysis](analysis/README.md).                                                                                                                                                                                                                                            |
| Analysis and derived layers | **M6 complete** — the water grid, whale grid, current-code exploratory exposure bundles, and distinct exposure display/results contracts are generated, reconciled, reproducible, and visually verified in QGIS 4.2.1. Independent numerical/scientific-content review and author acceptance are recorded, and the closure audit independently matched the primary calculation, fractional accounting, p90 statistic, outside-cell ranking, and all 2,793 display rows. The materially non-robust log-traffic sensitivity remains prominent. This is not validation of collision probability, observed encounters, or VSR effectiveness |
| Web application             | **M5 complete; M7 in progress** — the deployed package passed public receipt, headers, keyed responsive-browser, failure-isolation, accessibility, release-time VSR, and whole-connection functional checks. The stale sentence saying review and acceptance are pending is corrected and fully tested on this branch; M7 awaits a reviewed, authorized public release of that correction                                                                                                                                                                                                                                                            |
| Deployment                  | **M4 complete; authorized M5/M7 candidate live** — the existing `stemry/socal-whale-vessel-overlap` free-Hobby project serves the exact approved production package at the stable URL. All 902 public files matched the receipt inventory byte-for-byte; GitHub remains disconnected, no server runtime was introduced, and billing or unrelated project settings were not changed                                                                                                                                                                                                         |

**M8 verification is in progress.** A reusable exposure-verification command
records later checks without changing generation lineage. Retained-artifact
and public-byte checks passed; the fresh raw-to-public rerun and independent
documentation verification remain open. See the
[M8 evidence and next steps](docs/m8-verification-handoff.md).

## Technology direction

The accepted hybrid direction uses Python as the reproducible processing and analytical core, QGIS for local inspection and required visual verification, and a Next.js / TypeScript application using the [ArcGIS Maps SDK for JavaScript](https://developers.arcgis.com/javascript/latest/). The VSR boundary is a selected Version 1 exception at the publication boundary: the application loads the publisher's public Feature Service directly with `FID = 126`, attribution to Danielle Alvarez, CMSF, and BWBS, and the publisher's non-navigational disclaimer. The project does not host a copy. [ADR 0021](docs/decisions/0021-propose-vercel-static-input-delivery.md) selects checksum-addressed static same-origin files on free Vercel Hobby for project-derived layers. The whale, vessel-activity, analytical-domain, and exposure files are implemented and deployed as static same-origin assets; the build-only results JSON is not public. On 2026-09-09 the author confirmed the existing Hobby/free-only setup, disabled pay-as-you-go, available allowance, and restricted browser key remained current. Read-only release checks independently verified the current Vercel identity/project and the key's exact approved local and production origins plus rejection of an unrelated origin; they did not independently inspect billing UI state. The isolated existing Vercel project serves the approved package at the stable URL below. Esri hosted-data capabilities are unselected and remain unverified. Paid plans, trials, add-ons, pay-as-you-go, and other charged usage are prohibited.

Python produces the analysis and lineage; QGIS does not replace that production path. The browser displays and filters public results but does not compute exposure. ArcGIS Pro is optional and unnecessary for Version 1. Version 1 uses no custom backend or database. Details in [docs/architecture.md](docs/architecture.md) and [ADR 0015](docs/decisions/0015-adopt-a-hybrid-open-source-and-esri-gis-toolchain.md).

## Data sources

All three Version 1 inputs have been retrieved and inspected: the NOAA/SWFSC modeled blue-whale density surface, NOAA Marine Cadastre AIS vessel records, and the 2026 BWBS Vessel Speed Reduction zone. Formats, coordinate systems, resolutions, value meanings, coverage, volume, and terms of use are recorded — with a provenance manifest that can be re-checked against the local files — in [docs/data-sources.md](docs/data-sources.md).

Three findings are worth knowing before reading anything else. The AIS records come from land-based receivers, so Version 1 scope is reduced to the accepted `receivers_50_nautical_miles` domain: 50 nautical miles (92,600 metres) from the relevant NAIS reception stations, not from the coast. This is a system-performance-qualified AIS receiver domain, not empirical 2024 coverage. Receiver uptime, station completeness, feed interruptions, antenna and terrain effects, and observational completeness remain unknown or unverified; cells outside the domain will be excluded from headline statistics, not classified as low traffic. NOAA's 2025 vessel data is partial through September 30, so 2024 remains the latest published year covering the complete accepted July–November period. Version 1 therefore pairs the current (2026) speed-reduction zone with 2024 traffic. Finally, no explicit VSR redistribution grant was found. [ADR 0019](docs/decisions/0019-reference-the-publisher-hosted-vsr-service.md) resolves Version 1 through direct publisher-service display and prohibits a project-hosted copy; it does not rewrite that uncertainty as permission. Remaining limitations are listed in [docs/roadmap.md](docs/roadmap.md).

- **Modeled blue-whale distribution** — [NOAA Fisheries species distribution models](https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models)
- **Commercial vessel activity** — [NOAA / USCG AIS vessel traffic](https://coast.noaa.gov/digitalcoast/tools/ais.html)
- **VSR zone boundary and season** — [Blue Whales and Blue Skies](https://bluewhalesblueskies.org/operators/), with [California Ocean Protection Council](https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/) program context

## What this project does not claim

This is an exploratory portfolio spatial analysis, not a regulatory or production decision-support product. It does **not** predict individual whale strikes, calculate collision probability, identify observed encounters, measure VSR effectiveness, or identify objectively optimal VSR boundaries, and it makes no policy recommendations. Its outputs describe _relative exposure_ — where habitat and traffic coincide — not risk in any validated sense.

Any modeled distribution is an estimate, not observed whale locations. AIS limitations identified during data discovery — including the publisher's offshore coverage limit and self-reported vessel attributes — must remain visible through processing and reporting. Analytical choices such as thresholds, weightings, and time windows are documented as choices, with their rationale, wherever their results appear.

## Results

The exploratory public presentation passed independent numerical/scientific-
content review of the retained analytical tables, all 24 threshold/area
comparisons, and all 2,793 candidate display cells. The author accepted the
current results, limitations wording, and prominent log-traffic sensitivity.
The deployed M7 interface consumes the versioned machine-readable M6 results
artifact without recomputing it. These findings describe relative exposure;
they are not collision probability, observed encounters, or VSR effectiveness.
The analysis identifies the largest outside-zone concentrations conservatively
as ranked contributing cells; it does not claim that those cells form validated
hotspot clusters.

## Live demo

[Open the deployed exploratory exposure application](https://socal-whale-vessel-overlap.vercel.app/).

## Screenshots

**Not yet available.** Local verification screenshots remain ignored audit
evidence; public portfolio screenshots have not been selected or committed.

## Documentation

| Document                                                                             | Contents                                                               |
| ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| [docs/project-brief.md](docs/project-brief.md)                                       | Authoritative scope: Version 1 definition, non-goals, success criteria |
| [docs/roadmap.md](docs/roadmap.md)                                                   | Dependency-ordered milestones, progress, and version direction         |
| [docs/architecture.md](docs/architecture.md)                                         | Accepted system design, implemented boundaries, and deferred decisions |
| [docs/data-sources.md](docs/data-sources.md)                                         | Source register, provenance, and verification status                   |
| [docs/development.md](docs/development.md)                                           | Engineering workflow                                                   |
| [docs/decisions/](docs/decisions/README.md)                                          | Architecture decision records                                          |
| [docs/m7-exposure-interface-handoff.md](docs/m7-exposure-interface-handoff.md)       | Local M7 implementation, artifact, test, and browser evidence          |
| [docs/m7-release-integration-handoff.md](docs/m7-release-integration-handoff.md)     | M7 release tooling, candidate verification, and remaining gates        |
| [docs/project-vision-and-learning-plan.md](docs/project-vision-and-learning-plan.md) | Original project vision and GIS learning plan                          |
| [AGENTS.md](AGENTS.md)                                                               | Instructions for coding agents                                         |

Built as a portfolio project. Target for Version 1: **September 10, 2026**.
