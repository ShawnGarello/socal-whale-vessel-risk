# Project Brief

**Owns:** the authoritative product scope for this repository. If another document describes scope differently, this document is correct and the other should be updated.

**Status:** Version 1 is defined and partially implemented. The application and
processing foundations exist, and the deterministic whale-grid transfer is
implemented, tested, reproducible, and visually verified. Version 1 remains
incomplete: AIS retrieval, vessel aggregation, exposure analysis, publication,
and deployment are unfinished.

---

## Purpose

Use GIS to make a specific spatial relationship visible and measurable: where modeled blue-whale habitat off Southern California coincides with commercial vessel activity, and how much of that coincidence falls inside the area where California asks ships to slow down.

The project is an exploratory spatial analysis with an interactive map application on top of it. It is built to be read and checked — the processing steps, the data provenance, and the assumptions behind every derived number are part of the deliverable, not an appendix to it.

## Problem statement

The Southern California Bight carries some of the densest commercial shipping traffic in the United States and also holds foraging habitat for endangered blue whales. California's Protecting Blue Whales and Blue Skies (BWBS) program responds with voluntary Vessel Speed Reduction (VSR) zones, asking large vessels to travel at reduced speed inside designated waters during a defined season.

These datasets originate from different sources, in different formats and at different resolutions, and require deliberate normalization before they can be compared in one transparent, reproducible analysis. Answering the question with public data and standard GIS operations therefore means bringing the three inputs onto a common study area and grid, and being explicit about what the combined layer does and does not mean. The value of the project is that transparency and reproducibility, not any claim to have combined these subjects first — the BWBS program itself already evaluates related inputs and impacts.

## Intended audience

- **Reviewers of this portfolio** — primarily Esri internship reviewers assessing GIS reasoning, spatial analysis, and application development. This is the primary audience for Version 1.
- **People interested in the BWBS/VSR program** who want to see where habitat and traffic overlap relative to the current zone without reading a research paper.
- **The project author**, as a working reference for the analysis and its assumptions.

This is not a tool for vessel operators, and it is not built for regulatory or navigational use.

## Central research question

> Where does modeled blue-whale habitat overlap with commercial vessel activity off Southern California, and how much of that relative exposure occurs inside versus outside the current Vessel Speed Reduction zone?

Version 1 exists to answer that one question well. Every other question the project could ask is deferred.

## What Version 1 means

Version 1 is a **meaningful analytical MVP**, not a map viewer. The distinction that matters:

- A map viewer displays layers someone else published and lets the user pan around them.
- An analytical MVP produces a derived result that did not exist before — a relative exposure surface computed from whale and vessel inputs — reports summary statistics from it, and documents how those numbers were produced well enough that someone else could reproduce them.

Version 1 is complete when the research question above has a defensible, documented, reproducible answer that a visitor can explore in a browser.

**Project-level target:** Version 1 complete by **September 5, 2026**. Individual milestones are ordered by dependency rather than by date; see [roadmap.md](roadmap.md).

## Version 1 functional scope

Version 1 must ultimately include all of the following. Supporting foundations
and the grid-aligned whale input are implemented, but the complete functional
scope is not: AIS retrieval, vessel aggregation, exposure analysis,
publication, and deployment remain unfinished.

**Analytical inputs**

1. A defined Southern California study area with an explicit extent, projected coordinate system, and analysis grid.
2. An authoritative VSR zone boundary, traceable to the program's own published geometry or coordinates, with its season definition recorded alongside it.
3. A modeled blue-whale density or distribution layer from an authoritative source, clipped to the study area, with the meaning and units of its values documented.
4. Processed commercial AIS vessel activity for the study area, filtered to the relevant vessel classes and aggregated into a traffic measure on the analysis grid.
5. Vessel-speed information derived from the AIS data where the data actually supports it. This is a scope item that may be reduced in ambition if data discovery shows the available records cannot support speed summaries reliably; any reduction is recorded rather than quietly dropped.

**Derived analysis**

6. A documented relative exposure calculation combining whale density and vessel activity — inputs, normalization, weighting, and units stated explicitly, with the reasoning behind each choice.
7. A derived exposure or hotspot layer produced by that calculation and published as a real layer, not a screenshot.
8. Inside-versus-outside VSR summary statistics computed from the derived layer, with the area basis and any thresholds stated.

**Delivery**

9. An interactive ArcGIS web application presenting the input layers, the derived exposure layer, the VSR boundary, and the summary statistics.
10. Reproducible processing: the path from raw source data to published layer captured as scripts or as documented, ordered tooling steps that another person could rerun.
11. Documented methodology, data provenance, assumptions, and limitations.
12. A deployed, publicly reachable application and a portfolio-quality public repository.

## Non-goals for Version 1

These are excluded from Version 1. Several are legitimate later work; see "Beyond Version 1" below.

- Underwater-noise estimation or acoustic exposure modeling.
- Vessel-emissions estimation.
- Alternative-boundary or speed-change scenario comparison.
- Seasonal or other temporal breakdowns of exposure beyond the single, clearly labeled analytical period Version 1 uses.
- Any claim about individual whale strikes, collision probability, or strike counts.
- Any recommendation that the VSR zone be moved, expanded, contracted, or made mandatory.
- User accounts, saved sessions, or any feature requiring per-user state.
- A custom backend, database, job queue, or server-side analysis service.
- Live or near-real-time vessel tracking.
- Species other than blue whales.

## Expected analytical outputs

Version 1 should produce, at minimum:

- A relative exposure surface over the study area, on a stated grid, with stated units and a stated value range.
- The share of total relative exposure inside the VSR zone versus outside it.
- The share of high-exposure area inside versus outside the VSR zone, with the "high" threshold defined and its sensitivity acknowledged.
- Identification of where the largest concentrations of exposure outside the zone occur.
- Supporting descriptive figures: study-area extent, whale-density input, vessel-activity input, and the VSR boundary.

Every number reported must be traceable to a processing step and an input dataset.

## Success criteria

Version 1 is successful when all of the following hold:

1. The central research question is answered with numbers produced by this project's own analysis.
2. A reader can determine, from the repository alone, where every input came from, how it was processed, and what each derived value means.
3. Someone with the same source data and tooling could rerun the processing and arrive at the same derived layers.
4. The web application loads and is usable, and the statistics shown in it match the documented analysis.
5. No claim in the repository or application exceeds what the data and method support.
6. Assumptions and limitations are stated where a reader will encounter them, not collected in a single appendix nobody reads.

## Scientific communication rules

These apply to the application UI, the README, the analysis documentation, figure captions, and commit messages.

**The project does not claim to:**

- predict individual whale strikes or where a strike will occur;
- calculate validated collision probability without supporting, cited methodology;
- determine objectively optimal VSR boundaries;
- produce exact underwater sound levels from AIS data alone;
- produce regulatory-grade emissions inventories without supporting methodology;
- make policy recommendations the analysis cannot support.

**Preferred vocabulary:** relative exposure, spatial overlap, exposure index, proxy, scenario, exploratory analysis, modeled distribution.

**Vocabulary to avoid unless the method genuinely supports it:** risk, probability, predicted strikes, optimal, should, recommended.

**Assumptions stay labeled as assumptions.** A choice made because the data required it — a threshold, a weighting, a temporal window, a vessel-class filter — is documented as a choice with its rationale, and stays visible wherever its results are reported. Do not silently convert an assumption into a fact.

## Beyond Version 1

The following are real continuations of the project, not discarded ideas. They are excluded from Version 1 only because Version 1 is scoped to one question. Each depends on data and methodology that must be validated first, and none is guaranteed to be feasible with public data.

- **UI/UX refinement** — clearer layer explanation, legend design, mobile behavior, and guided interpretation of the exposure layer.
- **Temporal and seasonal analysis** — how the overlap changes across the VSR season and across months, contingent on the temporal resolution of both the whale model and the AIS data.
- **Underwater-noise proxy** — an estimated acoustic-pressure proxy from traffic, vessel characteristics, and speed, following published methodology, presented as a proxy and never as measured sound levels.
- **Vessel-emissions proxy** — estimated emissions intensity and speed-related differences, following published methodology, presented as estimates.
- **Scenario comparison** — how hypothetical zone geometries or exposure thresholds would change coverage of high-exposure areas, framed as GIS experiments rather than as recommendations.

The original long-form vision behind these is preserved in [project-vision-and-learning-plan.md](project-vision-and-learning-plan.md).
