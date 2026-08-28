# socal-whale-vessel-risk

A GIS analysis of where modeled blue-whale habitat and commercial vessel activity overlap off Southern California, and how much of that overlap falls inside California's Vessel Speed Reduction zone.

> **Status: in development.**
> The web application shell and Python processing foundation exist. The Python package validates the inspected input contracts, can clean one explicitly supplied single-UTC-date NOAA AIS CSV extract into a local Parquet/report/lineage bundle, and has produced the deterministic projected water grid. QGIS 4.2.1 visually verified that exact local grid. No exposure layer or public project layer exists, and nothing in this repository is an exposure result yet.
> The deterministic whale-grid transfer is also implemented and tested; two
> clean runs produced byte-identical output, and QGIS 4.2.1 visually verified
> the exact derived GeoParquet. AIS retrieval, vessel aggregation, exposure
> analysis, publication, and deployment remain unfinished.

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
| Architecture | Accepted as the initial direction; the application and processing foundations are built against it |
| Data sources | Downloaded and inspected; properties, licensing, and limits recorded, with a reproducible provenance manifest |
| Study area | Map extent proposed; **the analytical domain for statistics is still open** — see [ADR 0002](docs/decisions/0002-southern-california-study-area-extent.md) |
| Processing workflow | **In progress** — locked Python package, DuckDB engine, contracts, validators, a tested one-extract AIS cleaning command, deterministic projected water-grid generation, and deterministic tested whale-grid transfer with byte-identical reruns; AIS retrieval, vessel aggregation, and exposure processing remain unfinished |
| Analysis and derived layers | **In progress** — the projected per-cell water grid and whale-grid output are generated, programmatically verified, reproducible, and visually verified in QGIS 4.2.1; exposure and later analytical layers remain unfinished |
| Web application | **Foundation built** — Next.js and TypeScript with an ArcGIS map shell over Southern California. Basemap configured but successful keyed rendering still unverified; no project layers or analysis |
| Deployment | Not started |

## Technology direction

The accepted hybrid direction uses Python as the reproducible processing and analytical core, QGIS for local inspection and required visual verification, and a Next.js / TypeScript application using the [ArcGIS Maps SDK for JavaScript](https://developers.arcgis.com/javascript/latest/). Three project-layer publication candidates remain open: limited ArcGIS Location Platform feature/vector-tile/map-tile services within verified free-tier capacity, ArcGIS Online organization-hosted layers when account capabilities support them, and a non-Esri public fallback if neither fits. ArcGIS platform basemap and item access is intended to use a properly scoped browser API key where available; successful API-key-backed access remains unverified. No publication route has been implemented, and the project does not authorize paid usage.

Python produces the analysis and lineage; QGIS does not replace that production path. The browser displays and filters public results but does not compute exposure. ArcGIS Pro is optional and unnecessary for Version 1. Version 1 uses no custom backend or database. Details in [docs/architecture.md](docs/architecture.md) and [ADR 0015](docs/decisions/0015-adopt-a-hybrid-open-source-and-esri-gis-toolchain.md).

## Data sources

All three Version 1 inputs have been retrieved and inspected: the NOAA/SWFSC modeled blue-whale density surface, NOAA Marine Cadastre AIS vessel records, and the 2026 BWBS Vessel Speed Reduction zone. Formats, coordinate systems, resolutions, value meanings, coverage, volume, and terms of use are recorded — with a provenance manifest that can be re-checked against the local files — in [docs/data-sources.md](docs/data-sources.md).

Two findings are worth knowing before reading anything else. The AIS records come from land-based receivers and NOAA states coverage is unavailable more than 40–50 miles offshore, which is inside the area this project cares about; until that is resolved, the region over which statistics can be defended is an open question. NOAA's 2025 vessel data is partial through September 30, so 2024 remains the latest published year covering the complete accepted July–November period. Version 1 therefore pairs the current (2026) speed-reduction zone with 2024 traffic. What remains unresolved is listed in [docs/roadmap.md](docs/roadmap.md).

- **Modeled blue-whale distribution** — [NOAA Fisheries species distribution models](https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models)
- **Commercial vessel activity** — [NOAA / USCG AIS vessel traffic](https://coast.noaa.gov/digitalcoast/tools/ais.html)
- **VSR zone boundary and season** — [Blue Whales and Blue Skies](https://bluewhalesblueskies.org/operators/), with [California Ocean Protection Council](https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/) program context

## What this project does not claim

This is an exploratory, decision-support spatial analysis. It does **not** predict individual whale strikes, calculate validated collision probability, or identify objectively optimal VSR boundaries, and it makes no policy recommendations. Its outputs describe *relative exposure* — where habitat and traffic coincide — not risk in any validated sense.

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
