# Roadmap

**Owns:** milestones, sequencing, current progress, and version direction.

Milestones are ordered by **dependency and outcome**, not by calendar date. No individual milestone carries a date. The only date in this project is the Version 1 target recorded in [project-brief.md](project-brief.md).

A milestone is not "in progress" because work has been thought about. It is in progress when something in the repository is changing for it, and complete only when every completion criterion below is satisfied.

**Status legend:** `Not started` · `In progress` · `Blocked` · `Complete`

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Project foundation | In progress |
| M2 | Data discovery and validation | Not started |
| M3 | Processing workflow | Not started |
| M4 | GIS application foundation | Not started |
| M5 | Core input layers | Not started |
| M6 | Whale–vessel exposure analysis | Not started |
| M7 | Application integration | Not started |
| M8 | Verification and reproducibility | Not started |
| M9 | Public release | Not started |

---

## M1 — Project foundation

**Status:** In progress

**Objective**
Establish the documentation baseline that everything else is built against: scope, sequencing, proposed architecture, source register, and working process. Get the project to a state where the next decision is a data decision rather than a scoping decision.

**Dependencies**
None.

**Deliverables**
- Relocated and preserved original project vision.
- Product scope document, roadmap, proposed architecture, data-source register, development process.
- Decision-record directory and format.
- Repository-level agent guidance.
- Recruiter-facing README.

**Completion criteria**
- The Version 1 question, scope, and non-goals are written down in one authoritative place.
- The proposed architecture is documented and explicitly marked as pending review.
- Every intended data source is registered with its verification status.
- No implementation directories, contracts, or schemas have been created.
- Documents do not contradict each other.

**Risks and open questions**
- The proposed architecture has not been reviewed against real data yet; parts of it may not survive M2.
- Documentation written before data inspection can encourage premature commitment. Anything unverified must stay labeled as unverified.

---

## M2 — Data discovery and validation

**Status:** Not started

**Objective**
Obtain and inspect the actual candidate datasets, and determine what analysis the data can genuinely support. This milestone is where assumptions become findings.

**Dependencies**
- M1 (source register exists with the questions each source must answer).

**Deliverables**
- A small, retrievable sample of each candidate dataset, inspected locally.
- For each source: confirmed format, coordinate reference system, spatial extent and resolution, temporal coverage, value meaning and units, and license or terms of use.
- A written definition of the Southern California study area: extent, projected CRS, and analysis grid, with the reasoning for each.
- A decision on the analytical period Version 1 will use.
- A decision on whether vessel speed can be derived reliably from the available AIS records.
- Updated source register with verification status replacing every "to be verified" entry that has been resolved.
- Architecture decision records for choices that constrain later work.

**Completion criteria**
- Every Version 1 input has an identified, retrievable, authoritative source with recorded provenance.
- The whale model layer's values are understood well enough to state what they mean in the application legend.
- The AIS extract needed for the study area and analytical period has been scoped, and its volume is known.
- The VSR boundary geometry is confirmed as obtainable from an authoritative source, or a documented derivation from published coordinates is agreed on.
- Redistribution terms are known for each dataset, so it is clear what may be committed or hosted publicly.
- Anything that cannot be verified is explicitly recorded as unresolved rather than assumed.

**Risks and open questions**
- The whale distribution model may not be published at a resolution or in a format that is directly usable, or may cover a different region or period than needed.
- AIS volume for the study area may be large enough to force a narrower analytical period or a coarser aggregation.
- The authoritative VSR boundary may only be published as text coordinates or as a map image rather than as a downloadable geometry.
- Whale-model and AIS temporal coverage may not overlap cleanly, which would constrain the analytical period.
- Licensing may restrict redistribution of a processed derivative.

---

## M3 — Processing workflow

**Status:** Not started

**Objective**
Turn raw source data into validated, derived geospatial datasets through an ordered, repeatable process.

**Dependencies**
- M2 (data confirmed, study area and grid defined, analytical period chosen).

**Deliverables**
- A documented, ordered processing path from raw inputs to derived datasets, implemented as scripts or as recorded tooling steps.
- Clipping, reprojection, and normalization of each input onto the common study area and analysis grid.
- Vessel-activity aggregation from AIS records, with vessel-class filtering applied and documented.
- Vessel-speed summarization, if M2 confirmed it is supportable.
- Input-validation checks: geometry validity, CRS correctness, extent coverage, null and outlier handling.
- Recorded data lineage for each derived dataset — source, retrieval date, and the steps applied.

**Completion criteria**
- Each derived dataset can be regenerated from raw inputs by following the documented process.
- Rerunning the process on unchanged inputs produces equivalent outputs.
- Every filtering and aggregation choice is documented with its rationale.
- Intermediate outputs have been inspected visually, not only programmatically.

**Risks and open questions**
- Raster–vector alignment and resampling choices can materially change results; the chosen approach must be justified.
- AIS records commonly contain implausible positions and speeds; the cleaning rules will need documenting and will affect outputs.
- Splitting work between ArcGIS Pro and Python risks steps that exist only as manual clicks and are therefore not reproducible. Manual steps must be recorded in enough detail to repeat.

---

## M4 — GIS application foundation

**Status:** Not started

**Objective**
Stand up the web application shell — the framework, the map, and the deployment path — before there is analytical content to put in it.

**Dependencies**
- M1 (architecture reviewed and accepted).
- Independent of M2 and M3; can proceed in parallel with data work.

**Deliverables**
- Application scaffold created following the reviewed architecture.
- A working map view of the study area using the ArcGIS Maps SDK for JavaScript.
- Environment-variable and credential handling in place, with nothing secret committed.
- **A verified ArcGIS Online capability check**, recording: access to an organization; content-creation and publishing privileges; permission to share items publicly; availability of hosted imagery and tile publishing as well as hosted feature layers; credit availability and which operations consume credits; and storage availability against quota.
- A test item published and shared publicly, then loaded from the application, proving the publish-and-serve path end to end before any real layer depends on it.
- A working deployment of the empty shell.
- Formatting, linting, and type-checking configured.

**Completion criteria**
- The application builds locally and in the deployment environment.
- The map renders, pans, and zooms over the study area.
- No API keys or credentials appear in the repository or in committed build output.
- The deployment is reachable and reflects the current main branch state.
- **The ArcGIS Online capability check is complete and recorded.** Publishing privileges, public sharing, imagery and tile support, credits, and storage are each confirmed or confirmed unavailable. The deployment path is not considered proven until a publicly shared item loads in the deployed application.
- Any capability found unavailable is recorded as a constraint on layer representation and hosting, and carried into the core-input-layers milestone rather than discovered there.

**Risks and open questions**
- **ArcGIS Online account capabilities are unverified and gate delivery.** If the available account cannot publish hosted imagery or tiles, cannot share publicly, or lacks credits or storage, the layer representation and possibly the whole hosting approach have to change. This is cheaper to discover here than at release.
- Credit consumption for publishing and storage is not yet understood and could constrain how often layers are republished during iteration.
- ArcGIS SDK licensing and API-key requirements for the intended hosting model need confirming before public deployment.
- Bundle size and initial load time of the SDK need an early look rather than a late one.

---

## M5 — Core input layers

**Status:** Not started

**Objective**
Publish the validated input datasets as hosted layers and make them visible in the application.

**Dependencies**
- M3 (validated derived datasets exist).
- M4 (application shell exists).

**Deliverables**
- Study area, VSR boundary, whale density, and vessel activity published as hosted layers.
- A web map assembling them with symbology chosen for legibility, not decoration.
- Layer visibility control and legends in the application.
- Popups or panels that state what each layer's values mean, including units.
- Recorded mapping from each hosted layer back to the derived dataset and processing step that produced it.

**Completion criteria**
- Each layer renders at the study-area scale within an acceptable load time.
- Every layer's legend states its units and the meaning of its values.
- Every layer names its source and its retrieval or processing date somewhere the user can reach.
- Layer geometry visually aligns across layers; no projection mismatch is visible.

**Risks and open questions**
- Hosted-layer size or feature-count limits may force further aggregation or generalization.
- Raster layers may need to be published differently from vector layers, with different performance characteristics.
- Symbology for a continuous density surface needs a defensible classification, since the class breaks chosen will shape how the map is read.

---

## M6 — Whale–vessel exposure analysis

**Status:** Not started

**Objective**
Produce the project's own analytical result: a documented relative exposure layer, and the inside-versus-outside VSR statistics derived from it. This is the milestone that makes the project an analysis rather than a viewer.

**Dependencies**
- M3 (validated, grid-aligned whale and vessel inputs).
- M2 (understood value meanings and units for both inputs).

**Deliverables**
- A written definition of the relative exposure calculation: inputs, normalization, weighting, combination method, and units.
- The derived exposure or hotspot layer over the study area.
- Inside-versus-outside VSR statistics: share of total relative exposure, share of high-exposure area, and the threshold definitions used.
- Identification of the largest concentrations of exposure outside the zone.
- A sensitivity check showing how the reported statistics respond to the main arbitrary choices, particularly the high-exposure threshold and the normalization method.
- An assumptions-and-limitations record covering what the exposure index does and does not represent.

**Completion criteria**
- The exposure calculation is reproducible from the derived inputs.
- Every reported statistic states its basis — area, total exposure, or cell count — and its threshold.
- The results are described in the vocabulary required by the project brief, with no risk or probability language.
- The sensitivity check is documented, including any case where a conclusion is not robust.
- The layer and the statistics are consistent: the numbers are computed from the published layer, not from a different intermediate.

**Risks and open questions**
- Combining a modeled density surface with an observed traffic measure implies choices about units and scaling that have no single correct answer; whatever is chosen must be justified and tested.
- Threshold-based "high exposure" statistics are sensitive to the threshold. Reporting a single number without sensitivity context would overstate certainty.
- Differing native resolutions between whale and vessel data force a resampling decision that can bias results toward one input.
- Edge effects at the study-area boundary may distort inside/outside comparisons near the VSR zone edge.

---

## M7 — Application integration

**Status:** Not started

**Objective**
Bring the analysis into the application so a visitor can explore the exposure layer and read the results without prior GIS knowledge.

**Dependencies**
- M5 (input layers published and displayed).
- M6 (exposure layer and statistics exist).

**Deliverables**
- The derived exposure layer published and rendered in the application.
- A results panel presenting the inside-versus-outside statistics.
- Explanatory text stating what the exposure layer represents, in plain language, with its assumptions visible at the point of reading.
- Methodology and limitations reachable from the application, not only from the repository.
- Responsive behavior adequate for a reviewer opening the app on a laptop or phone.

**Completion criteria**
- The statistics displayed match the documented analysis exactly.
- A first-time visitor can tell what they are looking at without reading the repository.
- Limitations are visible in the interface, not hidden behind a link nobody clicks.
- No wording in the interface violates the project's scientific communication rules.
- The application remains usable on a mid-range connection.

**Risks and open questions**
- Presenting a single headline percentage invites overinterpretation; the framing needs care.
- Interactive exploration of a raster surface in the browser may require serving a pre-rendered or tiled representation rather than raw values.

---

## M8 — Verification and reproducibility

**Status:** Not started

**Objective**
Confirm that the results are correct, that the process can be rerun, and that the documentation matches what was actually built.

**Dependencies**
- M6 (analysis complete).
- M7 (application integrated).

**Deliverables**
- End-to-end rerun of the processing path from raw inputs, with outputs compared against the published layers.
- Verification that every statistic in the application traces to a processing step.
- Automated checks over analytical logic where it exists as code.
- A documentation audit against the implemented behavior, correcting anything described as built that is not, and anything built that is not described.
- Recorded source retrieval dates and dataset versions used for the published results.

**Completion criteria**
- A rerun reproduces the published derived layers.
- No documented capability is absent from the implementation, and no implemented capability is undocumented.
- Every published number is traceable to an input and a step.
- Known limitations are recorded in one place and referenced from the application.

**Risks and open questions**
- Manual ArcGIS Pro steps are the most likely reproducibility gap; if a rerun is not repeatable, the step needs converting to script or documenting in far more detail.
- Source datasets can be revised or withdrawn upstream, which is why retrieval dates and versions must be recorded.

---

## M9 — Public release

**Status:** Not started

**Objective**
Make the project publicly presentable: deployed, documented, and readable by a reviewer who has ten minutes.

**Dependencies**
- M7 (application integrated).
- M8 (results verified).

**Deliverables**
- Deployed application at a stable public URL.
- README updated with the live demo link, screenshots, and headline results.
- Methodology, provenance, assumptions, and limitations complete and linked.
- Repository cleaned of dead files, unused scaffolding, and stale documentation.
- Repository metadata — description, topics, license posture — set appropriately.

**Completion criteria**
- The deployed application works from a clean browser session with no local setup.
- The README communicates the question, the method, the result, and the limitations without requiring any other document.
- Every documentation link resolves.
- Nothing in the repository claims a capability that does not exist.
- Version 1 scope items in [project-brief.md](project-brief.md) are all satisfied or explicitly recorded as reduced, with the reason.

**Risks and open questions**
- **Public delivery depends on ArcGIS Online account capabilities.** If public sharing, publishing privileges, imagery or tile support, credits, or storage prove insufficient, the layers cannot be served to a public visitor and the release is blocked regardless of how complete the analysis is. This is verified in M4 precisely so it is not discovered here.
- Credits and storage are consumable. A release can be blocked by an exhausted quota even when everything was working during development.
- Deployment hosting and any ArcGIS credential requirements must be settled before release, not at release.
- Screenshots and headline numbers go stale if the analysis is later revised; they need a stated "results as of" date.

---

## Version progression beyond Version 1

These are candidate directions for Version 2 and later. They are ordered roughly by how directly they build on Version 1, not by priority, and none is committed. Each requires its own data and methodology validation before it can be attempted, and each may prove infeasible with publicly available data.

Nothing in this section is a guaranteed scientific result. A proxy is a proxy, and a scenario is a hypothetical GIS experiment, not a finding and not a recommendation.

**UI/UX refinement**
Improve how the exposure layer is explained and read: legend and classification design, guided interpretation, comparison views, mobile layout, and accessibility. Depends on Version 1 being deployed and on observing where the current presentation misleads.

**Temporal analysis**
Break the overlap down by month or across the VSR season. Depends on the whale model and the AIS extract both supporting the intended time step, which M2 will determine. If the whale model is not time-varying at that step, seasonal claims cannot be made from it.

**Underwater-noise analysis**
Derive an estimated acoustic proxy from vessel traffic, vessel characteristics, and speed, following published methodology. Requires a defensible published method and the vessel attributes that method needs. AIS alone does not give sound levels, and any output must be presented as a modeled proxy with stated assumptions.

**Emissions analysis**
Estimate relative emissions intensity and how it varies with speed, following published methodology. Requires emission factors and vessel attributes that the AIS data may not carry. Any output is an estimate, not an inventory.

**Scenario analysis**
Compare how hypothetical zone geometries or exposure thresholds would change coverage of high-exposure areas. Depends on a Version 1 exposure layer whose sensitivity is already characterized, since scenario differences are only meaningful if the underlying index is stable. Framed as GIS experiments; the project does not recommend boundary changes.
