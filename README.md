# socal-whale-vessel-risk

A GIS analysis of where modeled blue-whale habitat and commercial vessel activity overlap off Southern California, and how much of that overlap falls inside California's Vessel Speed Reduction zone.

> **Status: in development.**
> The web application shell and Python processing foundation exist. The Python package validates the inspected input contracts, verifies and manifests one explicitly supplied local AIS delivery, partitions an author-supplied multi-date AccessAIS CSV or safe ZIP into deterministic daily inputs through a bounded local intake, sequentially cleans and resumably records those inputs under explicit verified DuckDB resources, can clean one single-UTC-date NOAA AIS CSV extract into a local Parquet/report/lineage bundle, and has produced the deterministic projected water grid. A controlled two-day resource investigation supports per-date-bounded cleaning for the inspected dates and defines a seven-day gate. An initial seven-day attempt was legitimately refused by the documented 2 GiB available-memory preflight. A later resumed first run processed and recorded all seven dates within every resource limit, and an identical retry reused all seven without regeneration. Two separate completed browser downloads also produced byte-identical files. This combined operational evidence is sufficient for the portfolio MVP to authorize only the next July 1--31 monthly scale test. Publisher-side independent byte completeness and observational completeness remain `unverified`; the evidence does not prove that NOAA's extract contained every possible AIS record. QGIS 4.2.1 visually verified the exact local grid. A vessel-activity evidence harness has been exercised on the real bounded 15 July bundle and exact grid. A separate candidate vessel-grid aggregation boundary is implemented and synthetically tested; all four documented parameter combinations were exercised on the real 15--16 July input, repeated deterministically, and inspected in corrected QGIS views with the accepted-domain and VSR outlines visible above the candidate grids. These are candidate results, not a final period-wide or production vessel grid. No exposure layer or public project layer exists, and nothing in this repository is an exposure result yet.
> The deterministic whale-grid transfer is also implemented and tested; two
> clean runs produced byte-identical output, and QGIS 4.2.1 visually verified
> the exact derived GeoParquet. Network and analytical-period AIS retrieval,
> final period-wide vessel aggregation, accepted vessel thresholds, a production
> vessel input, exposure analysis, publication, and deployment remain unfinished.
> Data discovery (M2) is complete. Its final publication question was resolved
> through a conservative no-copy VSR architecture, not by claiming
> redistribution permission: analysis retains the immutable ignored local
> snapshot, while the future public map will display the publisher-hosted
> `FID = 126` feature directly.

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
| Processing workflow | **In progress** — locked Python package, DuckDB engine, contracts, validators, a bounded local multi-date AccessAIS intake and resumable resource-controlled daily-cleaning path exercised with real one-day, two-day, and seven-day deliveries; two byte-identical completed browser downloads plus the successful seven-day first run and all-date reuse retry authorize only the July 1--31 monthly scale test for this portfolio MVP, while publisher-side byte completeness and observational completeness remain `unverified`; deterministic projected water-grid generation, deterministic tested whale-grid transfer with byte-identical reruns, and implemented/synthetically tested candidate vessel-grid aggregation exercised across the real two-day parameter matrix with deterministic repeats and corrected QGIS inspection; safe monthly/full-period scaling, analytical-period AIS retrieval, accepted vessel thresholds, final period-wide vessel aggregation, the production vessel input, and exposure processing remain unfinished |
| Analysis and derived layers | **In progress** — the projected per-cell water grid and whale-grid output are generated, programmatically verified, reproducible, and visually verified in QGIS 4.2.1; exposure and later analytical layers remain unfinished |
| Web application | **Foundation built** — Next.js and TypeScript with an ArcGIS map shell over Southern California. Local keyed oceans-basemap rendering, pan/zoom, attribution handoff, and the required responsive viewports are verified; deployment, account capabilities, project layers, and analysis remain unfinished |
| Deployment | Not started |

## Technology direction

The accepted hybrid direction uses Python as the reproducible processing and analytical core, QGIS for local inspection and required visual verification, and a Next.js / TypeScript application using the [ArcGIS Maps SDK for JavaScript](https://developers.arcgis.com/javascript/latest/). The VSR boundary is a selected Version 1 exception at the publication boundary: the future application will load the publisher's public Feature Service directly with `FID = 126`, attribution to Danielle Alvarez, CMSF, and BWBS, and the publisher's non-navigational disclaimer. The project will not host a copy. Three publication candidates remain open for the project-derived whale, vessel, and exposure layers: limited ArcGIS Location Platform feature/vector-tile/map-tile services within verified free-tier capacity, ArcGIS Online organization-hosted layers when account capabilities support them, and a non-Esri public fallback if neither fits. Current official documentation confirms Location Platform's limited service types, anonymous public sharing, and published free tiers; the author's actual account controls, billing state, usage, and headroom remain unverified. Local ArcGIS basemap access through a scoped browser API key is verified, while deployed-origin access and project-derived-layer hosting are not. No project layer has been published, and the project does not authorize paid usage.

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

**Not yet available.** Headline statistics will be published here once the analysis is complete and verified.

## Live demo

**Not yet deployed.** A public URL will be added here at release.

## Screenshots

**Not yet available.** No screenshots are included with this architecture update; they will be added only after the application renders real layers.

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

Built as a portfolio project. Target for Version 1: **September 5, 2026**.
