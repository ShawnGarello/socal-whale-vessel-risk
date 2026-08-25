# socal-whale-vessel-risk

A GIS analysis of where modeled blue-whale habitat and commercial vessel activity overlap off Southern California, and how much of that overlap falls inside California's Vessel Speed Reduction zone.

> **Status: in development — documentation and planning stage.**
> The analysis and the web application described below are defined but **not yet implemented**. Nothing in this repository is a result yet.

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
| Architecture | Proposed, pending review |
| Data sources | Identified, **not yet verified or downloaded** |
| Processing workflow | Not started |
| Analysis and derived layers | Not started |
| Web application | Not started |
| Deployment | Not started |

## Technology direction

Proposed and subject to review: ArcGIS Pro and Python for offline data preparation and spatial analysis → ArcGIS Online for hosted layers and web maps → a Next.js / TypeScript application using the [ArcGIS Maps SDK for JavaScript](https://developers.arcgis.com/javascript/latest/).

All analysis happens offline and is published as a result. The browser displays and filters; it does not compute exposure. Version 1 uses no custom backend or database. Details in [docs/architecture.md](docs/architecture.md).

## Data sources

Identified source categories. None has been downloaded, inspected, or verified yet; formats, resolutions, coverage, and licensing are all open questions tracked in [docs/data-sources.md](docs/data-sources.md).

- **Modeled blue-whale distribution** — [NOAA Fisheries species distribution models](https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models)
- **Commercial vessel activity** — [NOAA / USCG AIS vessel traffic](https://coast.noaa.gov/digitalcoast/tools/ais.html)
- **VSR zone boundary and season** — [Blue Whales and Blue Skies](https://bluewhalesblueskies.org/operators/), with [California Ocean Protection Council](https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/) program context

## What this project does not claim

This is an exploratory, decision-support spatial analysis. It does **not** predict individual whale strikes, calculate validated collision probability, or identify objectively optimal VSR boundaries, and it makes no policy recommendations. Its outputs describe *relative exposure* — where habitat and traffic coincide — not risk in any validated sense.

Any modeled distribution is an estimate, not observed whale locations. Potential AIS limitations — including coverage variation and self-reported vessel attributes — will be evaluated during data discovery. Analytical choices such as thresholds, weightings, and time windows are documented as choices, with their rationale, wherever their results appear.

## Results

**Not yet available.** Headline statistics will be published here once the analysis is complete and verified.

## Live demo

**Not yet deployed.** A public URL will be added here at release.

## Screenshots

**Not yet available.** Added once the application renders real layers.

## Documentation

| Document | Contents |
|---|---|
| [docs/project-brief.md](docs/project-brief.md) | Authoritative scope: Version 1 definition, non-goals, success criteria |
| [docs/roadmap.md](docs/roadmap.md) | Dependency-ordered milestones, progress, and version direction |
| [docs/architecture.md](docs/architecture.md) | Proposed system design and deferred decisions |
| [docs/data-sources.md](docs/data-sources.md) | Source register, provenance, and verification status |
| [docs/development.md](docs/development.md) | Engineering workflow |
| [docs/decisions/](docs/decisions/README.md) | Architecture decision records |
| [docs/project-vision-and-learning-plan.md](docs/project-vision-and-learning-plan.md) | Original project vision and GIS learning plan |
| [AGENTS.md](AGENTS.md) | Instructions for coding agents |

Built as a portfolio project. Target for Version 1: **September 5, 2026**.
