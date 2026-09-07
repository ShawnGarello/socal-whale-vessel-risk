# socal-whale-vessel-risk

A GIS analysis of where modeled blue-whale habitat and commercial vessel activity overlap off Southern California, and how much of that overlap falls inside California's Vessel Speed Reduction zone.

> **Status: in development.** M1 through M3 are complete; M4 through M6 are in progress.
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
> **Nothing has been deployed or published.** There is no public URL, no
> project-derived layer is hosted anywhere. ADR 0021 selects free Vercel Hobby
> static delivery; release staging is implemented. Vercel Hobby and ArcGIS
> pay-as-you-go disabled are author-confirmed, while remaining account and
> eligibility verification, review and deployment approval remain open.
> Local rendering is not deployed verification. The exposure method and its distinct
> display/results delivery contracts are implemented and locally verified, but
> **the results are exploratory and not yet independently reviewed or accepted,
> and no number from them is a finding of this project yet.** The final
> delivery-route decision, M7 integration, public delivery, and deployment
> remain unfinished. See
> the [roadmap](docs/roadmap.md), the
> [M5 whale display handoff](docs/m5-whale-display-handoff.md), the
> [M5 vessel/domain display handoff](docs/m5-vessel-domain-display-handoff.md), the
> [M6 exposure handoff](docs/m6-exposure-foundation-handoff.md), the
> [M6 exposure-results delivery handoff](docs/m6-exposure-results-delivery-handoff.md), and the
> [M3 handoff](docs/m3-completion-handoff.md).

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

| Area | State |
|---|---|
| Project scope and roadmap | Documented |
| Architecture | Accepted and refined; Python/QGIS/Esri responsibilities and the publisher-hosted VSR display exception are recorded |
| Data sources | **M2 complete** — downloaded and inspected; properties, licensing, limits, and public-use/publication postures recorded with a reproducible provenance manifest. VSR redistribution permission remains unconfirmed, so project-hosted copies are prohibited |
| Study area | **Accepted with separate roles** — the map/context extent, modeled-whale-support water geometry, and scope-reduced `receivers_50_nautical_miles` analytical domain are distinct; see [ADR 0002](docs/decisions/0002-southern-california-study-area-extent.md) |
| Processing workflow | **M3 complete** — ready 153-date AIS input; verified water/whale grids and full candidate matrix; the selected vessel rules of [ADR 0018](docs/decisions/0018-use-vessel-kilometres-for-grid-activity.md) were accepted after real production generation, byte-identical repetition and QGIS validation. See [analysis](analysis/README.md). |
| Analysis and derived layers | **M6 in progress** — the water grid, whale grid, fresh current-code exploratory exposure bundles, and distinct exposure display/results contracts are generated, programmatically reconciled, reproducible, and visually verified in QGIS 4.2.1. The exposure method is [ADR 0020](docs/decisions/0020-propose-area-integrated-relative-exposure.md), accepted for exploratory execution only; its results await independent review and owner acceptance, one sensitivity comparison is materially non-robust, and no exposure layer or statistic is published or adopted as a headline |
| Web application | **M4 foundation and M5 input-layer displays built locally** — Next.js and TypeScript with an ArcGIS map shell over Southern California. The filtered publisher-hosted 2026 California VSR boundary and checksum-bound same-origin whale, vessel-activity, and analytical-domain layers render at the required responsive viewports with visibility controls, legends, source/method disclosures, deterministic ordering, and isolated failure behavior. Free Vercel static delivery is selected; account/eligibility checks, exposure display, deployment and public access remain unfinished |
| Deployment | Local staging implemented; account checks, review, approval and public deployment remain open |

## Technology direction

The accepted hybrid direction uses Python as the reproducible processing and analytical core, QGIS for local inspection and required visual verification, and a Next.js / TypeScript application using the [ArcGIS Maps SDK for JavaScript](https://developers.arcgis.com/javascript/latest/). The VSR boundary is a selected Version 1 exception at the publication boundary: the application loads the publisher's public Feature Service directly with `FID = 126`, attribution to Danielle Alvarez, CMSF, and BWBS, and the publisher's non-navigational disclaimer. The project does not host a copy. [ADR 0021](docs/decisions/0021-propose-vercel-static-input-delivery.md) selects checksum-addressed static same-origin files on free Vercel Hobby for project-derived layers. The whale, vessel-activity, and analytical-domain files are implemented and locally verified; the exposure export and results artifact are implemented and verified as local M7 delivery evidence but are not yet integrated. The author confirmed Vercel Hobby and ArcGIS pay-as-you-go disabled on 2026-09-07. Hobby eligibility, the remaining ArcGIS basemap account and key checks, and deployed-origin behavior remain unverified. Esri hosted-data capabilities are unselected and remain unverified. No project-derived layer has been published. Paid plans, trials, add-ons, pay-as-you-go, and other charged usage are prohibited.

Python produces the analysis and lineage; QGIS does not replace that production path. The browser displays and filters public results but does not compute exposure. ArcGIS Pro is optional and unnecessary for Version 1. Version 1 uses no custom backend or database. Details in [docs/architecture.md](docs/architecture.md) and [ADR 0015](docs/decisions/0015-adopt-a-hybrid-open-source-and-esri-gis-toolchain.md).

## Data sources

All three Version 1 inputs have been retrieved and inspected: the NOAA/SWFSC modeled blue-whale density surface, NOAA Marine Cadastre AIS vessel records, and the 2026 BWBS Vessel Speed Reduction zone. Formats, coordinate systems, resolutions, value meanings, coverage, volume, and terms of use are recorded — with a provenance manifest that can be re-checked against the local files — in [docs/data-sources.md](docs/data-sources.md).

Three findings are worth knowing before reading anything else. The AIS records come from land-based receivers, so Version 1 scope is reduced to the accepted `receivers_50_nautical_miles` domain: 50 nautical miles (92,600 metres) from the relevant NAIS reception stations, not from the coast. This is a system-performance-qualified AIS receiver domain, not empirical 2024 coverage. Receiver uptime, station completeness, feed interruptions, antenna and terrain effects, and observational completeness remain unknown or unverified; cells outside the domain will be excluded from headline statistics, not classified as low traffic. NOAA's 2025 vessel data is partial through September 30, so 2024 remains the latest published year covering the complete accepted July–November period. Version 1 therefore pairs the current (2026) speed-reduction zone with 2024 traffic. Finally, no explicit VSR redistribution grant was found. [ADR 0019](docs/decisions/0019-reference-the-publisher-hosted-vsr-service.md) resolves Version 1 through direct publisher-service display and prohibits a project-hosted copy; it does not rewrite that uncertainty as permission. Remaining limitations are listed in [docs/roadmap.md](docs/roadmap.md).

- **Modeled blue-whale distribution** — [NOAA Fisheries species distribution models](https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models)
- **Commercial vessel activity** — [NOAA / USCG AIS vessel traffic](https://coast.noaa.gov/digitalcoast/tools/ais.html)
- **VSR zone boundary and season** — [Blue Whales and Blue Skies](https://bluewhalesblueskies.org/operators/), with [California Ocean Protection Council](https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/) program context

## What this project does not claim

This is an exploratory portfolio spatial analysis, not a regulatory or production decision-support product. It does **not** predict individual whale strikes, calculate validated collision probability, or identify objectively optimal VSR boundaries, and it makes no policy recommendations. Its outputs describe *relative exposure* — where habitat and traffic coincide — not risk in any validated sense.

Any modeled distribution is an estimate, not observed whale locations. AIS limitations identified during data discovery — including the publisher's offshore coverage limit and self-reported vessel attributes — must remain visible through processing and reporting. Analytical choices such as thresholds, weightings, and time windows are documented as choices, with their rationale, wherever their results appear.

## Results

**No reviewed headline result is available yet.** A versioned machine-readable
M6 results artifact now exists for later M7 consumption, but independent audit,
owner acceptance, application integration, and release verification remain.

## Live demo

**Not yet deployed.** A public URL will be added here at release.

## Screenshots

**Not yet available.** Local verification screenshots remain ignored audit
evidence; public portfolio screenshots have not been selected or committed.

## Documentation

| Document | Contents |
|---|---|
| [docs/project-brief.md](docs/project-brief.md) | Authoritative scope: Version 1 definition, non-goals, success criteria |
| [docs/roadmap.md](docs/roadmap.md) | Dependency-ordered milestones, progress, and version direction |
| [docs/architecture.md](docs/architecture.md) | Accepted system design, implemented boundaries, and deferred decisions |
| [docs/data-sources.md](docs/data-sources.md) | Source register, provenance, and verification status |
| [docs/development.md](docs/development.md) | Engineering workflow |
| [docs/decisions/](docs/decisions/README.md) | Architecture decision records |
| [docs/project-vision-and-learning-plan.md](docs/project-vision-and-learning-plan.md) | Original project vision and GIS learning plan |
| [AGENTS.md](AGENTS.md) | Instructions for coding agents |

Built as a portfolio project. Target for Version 1: **September 10, 2026**.
