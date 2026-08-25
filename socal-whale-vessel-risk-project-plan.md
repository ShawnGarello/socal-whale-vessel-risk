# Southern California Whale–Vessel Impact GIS

**Repository:** `socal-whale-vessel-risk`
**Project type:** GIS / Environmental Data Analysis / Web Mapping
**Core technology:** ArcGIS Pro, ArcGIS Online, ArcGIS Maps SDK for JavaScript, Next.js, TypeScript, Python when necessary
**Application target:** September 1, 2026
Esri generally accepts internship applications from September 1 through December 31 and explicitly recommends applying early because positions are filled as qualified candidates are identified.
**Esri internship information:**
[https://www.esri.com/en-us/about/careers/student-jobs](https://www.esri.com/en-us/about/careers/student-jobs)

---

# 1. Project Overview

## Main idea

California contains important habitat for endangered blue whales while also supporting some of the busiest commercial shipping routes in the United States.
Large commercial vessels—including container ships, tankers, bulk carriers, vehicle carriers, and passenger vessels—can create several environmental pressures:

- Risk of vessel strikes with whales
- Underwater noise
- Air pollution
- Greenhouse-gas emissions

California's **Protecting Blue Whales and Blue Skies (BWBS)** program uses voluntary Vessel Speed Reduction (VSR) zones to address these impacts.
For the 2026 season, large oceangoing vessels of at least 300 gross tons are requested to travel at 10 knots or less inside designated California zones. The 2026 season runs from April 22 through December 31.
**California Ocean Protection Council overview:**
[https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/](https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/)
**Official Blue Whales and Blue Skies site:**
[https://bluewhalesblueskies.org/](https://bluewhalesblueskies.org/)
**2026 VSR information / ship operators:**
[https://bluewhalesblueskies.org/operators/](https://bluewhalesblueskies.org/operators/)

---

# 2. Main Research Question

**How well do California's Vessel Speed Reduction zones spatially and seasonally align with areas where large commercial shipping creates environmental pressure on blue whales and surrounding coastal ecosystems?**
The project can eventually investigate three major effects:

### 1. Whale–vessel strike exposure

Where do high modeled blue-whale densities overlap with heavy commercial vessel traffic?
How much of this overlap occurs inside versus outside current Vessel Speed Reduction zones?

### 2. Underwater-noise exposure

Where does commercial vessel traffic generate the greatest potential acoustic pressure within blue-whale habitat?
How might slower vessel speeds change this exposure?

### 3. Air pollution and greenhouse-gas emissions

Where are shipping emissions concentrated?
How could vessel-speed reduction affect estimated emissions in and around the management zones?
The BWBS program itself monitors vessel speeds, whale-strike risk, underwater noise, and emissions, so these categories directly relate to the actual California program.
**BWBS Methods & Monitoring:**
[https://bluewhalesblueskies.org/operators/methods-and-monitoring/](https://bluewhalesblueskies.org/operators/methods-and-monitoring/)
**BWBS program impacts:**
[https://bluewhalesblueskies.org/impact/](https://bluewhalesblueskies.org/impact/)

---

# 3. What the Project Is NOT Claiming

The application should not claim that it can predict exactly where a whale will be struck.
It should also not claim that I have determined California's objectively optimal VSR boundaries.
Instead, the project should function as a **GIS-based exploratory and decision-support analysis**.
The goal is to answer questions such as:

> Where do whale habitat and vessel activity overlap?

> How much of that geographic overlap is covered by existing VSR zones?

> How does that relationship change spatially or seasonally?

> How would hypothetical geographic configurations change those results?

---

# MILESTONE 0 — Understand GIS

## Goal

Before building the real project, understand what GIS actually represents.
Learn these concepts:

- Point
- Polyline
- Polygon
- Geometry
- Feature
- Attributes
- Layer
- FeatureLayer
- Raster
- Vector
- Basemap
- Latitude / longitude
- Coordinate systems
- Projections
- Spatial relationships
- Spatial queries

## Mental model

A normal database record might contain:

```
Name: Port of Los Angeles
```

A GIS feature contains:

```
Geometry + Attributes
```

For example:

```
POLYGON(...)
```

plus:

```
Name = VSR Zone
Season = 2026
Requested Speed = 10 knots
```

GIS allows those records to be analyzed based on **where they exist geographically**.

---

## Resource 1 — Get Started with ArcGIS Online

Start here.
This teaches:

- Layers
- Basemaps
- Styling
- Filtering
- Map Viewer
- Working with spatial data

Esri's current tutorial walks through adding layers, changing symbology, filtering data, and sharing a map.
[https://learn.arcgis.com/en/projects/get-started-with-arcgis-online/](https://learn.arcgis.com/en/projects/get-started-with-arcgis-online/)

---

## Resource 2 — Get Started with ArcGIS Pro

Do this after getting comfortable with Map Viewer.
ArcGIS Pro is where much of the serious GIS processing and analysis can happen.
Learn:

- Projects
- Maps
- Layers
- Attribute tables
- Symbology
- Selecting data
- Basic analysis

[https://learn.arcgis.com/en/projects/get-started-with-arcgis-pro/](https://learn.arcgis.com/en/projects/get-started-with-arcgis-pro/)

---

## Resource 3 — Esri Tutorial Gallery

Use this when I want additional GIS exercises.
[https://learn.arcgis.com/en/gallery/](https://learn.arcgis.com/en/gallery/)
Do not try to complete everything.
Pick exercises that involve:

- Spatial analysis
- Environmental data
- Ocean data
- Raster analysis
- Transportation

---

## Resource 4 — ArcGIS Living Atlas

Explore what datasets already exist before downloading everything myself.
[https://livingatlas.arcgis.com/](https://livingatlas.arcgis.com/)
Search terms:

```
blue whale
whale abundance
cetacean
vessel traffic
shipping
bathymetry
marine sanctuary
ocean
California
```

Important:
Finding a dataset on ArcGIS Online does **not** automatically mean it should be trusted.
Always check:

- Publisher
- Original source
- Date
- Geographic coverage
- Methodology
- What its values actually mean

Prefer authoritative sources such as NOAA, California agencies, Esri/Living Atlas, and established research institutions.

---

## Milestone 0 complete when

I can explain:

> GIS combines information about what something is with information about where it exists, allowing spatial relationships between datasets to be analyzed.

I should also understand the difference between:
**Vector data:** points, lines, polygons
and
**Raster data:** grids where each cell contains a value.

---

# MILESTONE 1 — Build My First ArcGIS Web Map

## Goal

Connect ArcGIS to an actual web application.
Do not build the whale application yet.
Learn:

- Map
- MapView
- Basemap
- Graphics
- Geometry
- Layers

---

## Resource — ArcGIS Maps SDK for JavaScript

This should become my main programming documentation.
[https://developers.arcgis.com/javascript/latest/](https://developers.arcgis.com/javascript/latest/)

### Tutorial collection

[https://developers.arcgis.com/javascript/latest/tutorials/](https://developers.arcgis.com/javascript/latest/tutorials/)
Start with:

### Display a map

[https://developers.arcgis.com/javascript/latest/tutorials/display-a-map/](https://developers.arcgis.com/javascript/latest/tutorials/display-a-map/)

### Add a point, line, and polygon

[https://developers.arcgis.com/javascript/latest/tutorials/add-a-point-line-and-polygon/](https://developers.arcgis.com/javascript/latest/tutorials/add-a-point-line-and-polygon/)

---

## Build

Create the repository:

```
socal-whale-vessel-risk
```

Create a basic application showing Southern California.
At minimum:

- ArcGIS basemap
- Pan
- Zoom
- One point
- One polyline
- One polygon

Do this portion manually so that I understand what the ArcGIS SDK is actually doing before using coding agents heavily.

---

## Milestone 1 complete when

I understand approximately:
Map
↓
Layer
↓
Feature
↓
Geometry + Attributes
and I can display geographic data from my own application.

---

# MILESTONE 2 — Learn FeatureLayers and Real GIS Data

## Goal

Move from manually created geometry to real geographic datasets.
FeatureLayers are extremely important.
A useful programming analogy is:
**FeatureLayer ≈ spatially enabled database table exposed through a service**
Esri defines a feature layer as a spatially enabled table whose features share a geometry type and fields.

---

## Resource — Add a FeatureLayer

[https://developers.arcgis.com/javascript/latest/tutorials/add-a-feature-layer/](https://developers.arcgis.com/javascript/latest/tutorials/add-a-feature-layer/)
Learn:

- Feature service URLs
- Fields
- Geometry
- FeatureLayer
- Loading remote GIS data

---

## Resource — Style a FeatureLayer

[https://developers.arcgis.com/javascript/latest/tutorials/style-a-feature-layer/](https://developers.arcgis.com/javascript/latest/tutorials/style-a-feature-layer/)
Learn how geographic features can change appearance according to their data.

---

## Resource — Query FeatureLayers

Reference:
[https://developers.arcgis.com/javascript/latest/references/core/layers/FeatureLayer/](https://developers.arcgis.com/javascript/latest/references/core/layers/FeatureLayer/)
FeatureLayers can be queried based on attributes, location, time, and other properties.

---

## Project task

Find or construct the **2026 California VSR zone**.
Official program information:
[https://bluewhalesblueskies.org/operators/](https://bluewhalesblueskies.org/operators/)
California government overview:
[https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/](https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/)
Use the official boundary/coordinates as the authoritative source whenever possible.
Eventually create:

```
2026_vsr_zone
```

as a project layer.

---

## Deliverable

Southern California map showing:
☑ 2026 VSR Zone
Clicking it should eventually show:

- Name
- 2026 season
- Requested vessel speed
- Basic program description

---

# MILESTONE 3 — Learn Spatial Queries

## Goal

Stop treating ArcGIS as simply a map renderer.
Learn how GIS asks geographic questions.
A normal database query might ask:

> Find vessels where speed > 10 knots.

A spatial query might ask:

> Find vessels located inside the VSR zone.

Or:

> Find whale-density regions that intersect the VSR boundary.

---

## Resource — SQL FeatureLayer Query

[https://developers.arcgis.com/javascript/latest/tutorials/query-a-feature-layer-sql/](https://developers.arcgis.com/javascript/latest/tutorials/query-a-feature-layer-sql/)
This teaches ordinary attribute-based queries.

---

## Resource — Spatial FeatureLayer Query

[https://developers.arcgis.com/javascript/latest/tutorials/query-a-feature-layer-spatial/](https://developers.arcgis.com/javascript/latest/tutorials/query-a-feature-layer-spatial/)

---

## Resource — Find Spatial Relationships

[https://developers.arcgis.com/javascript/latest/tutorials/find-spatial-relationships/](https://developers.arcgis.com/javascript/latest/tutorials/find-spatial-relationships/)
Learn concepts such as:

-

```
intersects
```

1.

```
contains
```

1.

```
within
```

1.

```
overlaps
```

ArcGIS spatial queries explicitly support analyzing relationships between input geometries and geographic features.

---

## Practice

Before using complicated whale data, test simple questions:

> Which features intersect my VSR polygon?

> Which points occur inside this area?

> Which geographic regions overlap?

---

## Milestone 3 complete when

I understand the difference between:
**attribute relationship**
and
**spatial relationship**
without needing to look it up.

---

# MILESTONE 4 — Learn Real Spatial Analysis

## Goal

Learn the operations that will eventually create my own analytical results.
Important concepts:

- Intersect
- Spatial Join
- Overlay
- Buffer
- Area calculations
- Raster analysis

These operations are more important to the internship project than creating a fancy UI.

---

## Resource — ArcGIS Pro Analysis Documentation

ArcGIS Pro overview:
[https://www.esri.com/en-us/arcgis/products/arcgis-pro/overview](https://www.esri.com/en-us/arcgis/products/arcgis-pro/overview)
ArcGIS Pro is designed for spatial-data management, mapping, analytics, imagery, and related GIS workflows.

---

## What I need to understand

### Intersect

Where do two geographic datasets occupy the same space?

### Spatial Join

Attach information from one geographic dataset to another because of their geographic relationship.

### Overlay

Combine multiple geographic datasets to uncover relationships that are not contained in any single dataset.

### Buffer

Create an area a specified distance around another geographic feature.

---

## Example

Eventually:
Blue-whale habitat
×
Commercial vessel activity
↓
Whale–vessel overlap
then:
Overlap regions
×
VSR boundary
↓
VSR coverage analysis

---

# MILESTONE 5 — Add Blue-Whale Data

## Goal

Understand and display the biological side of the project.
I should not rely primarily on exact whale sightings.
The more useful dataset is **modeled whale distribution/density**, which estimates where whales are more likely to occur.

---

## Primary resource — NOAA Species Distribution Models

[https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models](https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models)
NOAA provides California Current cetacean species-distribution resources based on long-running survey data, including habitat-based density estimates.
Study:

- What the values mean
- Geographic coverage
- Spatial resolution
- Time period
- Model limitations
- Whether blue-whale predictions are available in a usable GIS format

---

## Background resource — NOAA Cetacean Surveys

[https://www.fisheries.noaa.gov/west-coast/science-data/ship-based-cetacean-and-ecosystem-assessment-surveys-california-current](https://www.fisheries.noaa.gov/west-coast/science-data/ship-based-cetacean-and-ecosystem-assessment-surveys-california-current)
These surveys have been used to develop distribution models, identify hotspots, estimate populations, and support marine-mammal assessments.

---

## Optional background — NOAA WhaleWatch

[https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/whalewatch](https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/whalewatch)
WhaleWatch is useful for seeing how scientists combine whale observations and environmental variables to predict suitable blue-whale habitat.

---

## Optional Southern California background

NOAA Blue Whale Hot Spots:
[https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/blue-whale-hot-spots](https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/blue-whale-hot-spots)
This provides useful context for frequently used blue-whale areas off Southern California.

---

## GIS concept to learn here — Raster data

Blue-whale density may behave more like a continuous geographic surface than a collection of points.
Example:

```
0.12 | 0.20 | 0.51
0.18 | 0.65 | 0.91
0.08 | 0.39 | 0.74
```

Each grid cell represents some modeled geographic value.
Learn how ArcGIS handles raster/grid information.

---

## Project deliverable

Layers:
☑ 2026 VSR Zone
☑ Blue Whale Distribution / Density
I should be able to visually investigate how blue-whale habitat relates to the VSR boundary.

---

# MILESTONE 6 — Add Commercial Vessel Traffic

## Goal

Add the transportation component.
The main vessels of interest are large commercial oceangoing ships.
AIS—Automatic Identification System—provides geographic vessel observations including vessel location and characteristics.

---

## Primary resource — NOAA Vessel Traffic

[https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html](https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html)
NOAA's current vessel-traffic dataset is based on U.S. Coast Guard AIS information and is specifically intended for uses including traffic analysis, ecological studies, and location-based offshore research.

---

## Primary tool — NOAA AccessAIS

[https://coast.noaa.gov/digitalcoast/tools/ais.html](https://coast.noaa.gov/digitalcoast/tools/ais.html)
This is extremely useful.
AccessAIS allows vessel traffic to be downloaded for **user-defined geographic regions and time periods**, instead of downloading enormous national datasets.
Start with Southern California.
Do not download the entire United States.

---

## Resource — Marine Cadastre National Viewer

[https://coast.noaa.gov/digitalcoast/tools/mmc.html](https://coast.noaa.gov/digitalcoast/tools/mmc.html)
Use this before doing serious processing.
The viewer provides authoritative marine planning layers and is useful for understanding how professional ocean GIS systems organize vessel, boundary, habitat, infrastructure, and planning information.

---

## What I need to learn from AIS

Potentially:

- Vessel position
- Timestamp
- Vessel type
- Speed
- Course
- Vessel identity

Then learn how thousands of observations can become:

- Vessel tracks
- Traffic density
- Average-speed surfaces
- Geographic statistics

---

## Deliverable

Application layers:
☑ Blue Whale Density
☑ Commercial Vessel Traffic
☑ 2026 VSR Zone
At this point I should be able to visually see where shipping traffic and modeled whale habitat overlap.

---

# MILESTONE 7 — Build My First Original GIS Analysis

## Goal

This is the most important milestone before applying to Esri.
Create my own result from the input datasets.
Potential name:
**Whale–Vessel Spatial Overlap Index**
or
**Whale–Vessel Exposure Index**
Do NOT call it:
**Collision Probability**
unless there is enough scientific validation to support that claim.

---

## Concept

Blue-whale density
×
Commercial vessel activity
×
possibly vessel speed
↓
Relative whale–vessel exposure
Then:
Relative exposure
×
VSR boundary
↓
VSR geographic coverage

---

## Questions to calculate

- Where is whale–vessel overlap highest?
- What percentage of high-overlap regions fall within the VSR zone?
- What percentage fall outside?
- Where are the largest geographic gaps?
- Does the pattern change through the VSR season?

---

## BWBS resource — Methods & Monitoring

At this point, reread:
[https://bluewhalesblueskies.org/operators/methods-and-monitoring/](https://bluewhalesblueskies.org/operators/methods-and-monitoring/)
The program already uses scientific analysis to monitor vessel speeds, whale strikes, underwater noise, and emissions.
I should study the methodology so that my own analysis uses scientifically careful language.

---

## Deliverable

Actual calculated results.
For example:

```
High-overlap area inside VSR: X%
High-overlap area outside VSR: Y%
```

Those numbers should come from **my GIS analysis**, not from an existing website.
This is where the project starts becoming mine.

---

# MILESTONE 8 — Add Underwater Noise

## Goal

Expand from collision exposure into another environmental effect of commercial vessel activity.
Vessel noise is directly relevant to the BWBS program, which monitors underwater acoustic impacts alongside whale-strike risk and emissions.

---

## Start here

BWBS Methods & Monitoring:
[https://bluewhalesblueskies.org/operators/methods-and-monitoring/](https://bluewhalesblueskies.org/operators/methods-and-monitoring/)
Look specifically at:
**Reducing Underwater Noise**

---

## Deeper research

BWBS / Scripps underwater-noise report:
[https://bluewhalesblueskies.org/wp-content/uploads/BWBS\_2025\_ZoBell\_Report\_final.pdf](https://bluewhalesblueskies.org/wp-content/uploads/BWBS_2025_ZoBell_Report_final.pdf)
The report analyzes underwater sound associated with vessel activity and mitigation efforts in California waters.

---

## Potential analysis

Do not claim AIS alone gives exact underwater sound levels.
Instead, if the available research supports it, calculate an:
**estimated vessel-noise proxy**
using:
Vessel traffic
\+
Vessel characteristics
\+
Vessel speed
↓
Estimated acoustic pressure
Then:
Estimated noise
×
Blue-whale habitat
↓
Potential acoustic exposure
Clearly document assumptions.

---

## Deliverable

Impact selector:
○ Whale–vessel overlap
○ Underwater-noise exposure

---

# MILESTONE 9 — Add Air Pollution / Emissions

## Goal

Represent another co-benefit of vessel-speed reduction.
This section should be described mainly as a broader environmental/coastal-community effect rather than pretending emissions are the same biological threat as vessel strikes.

---

## Resource

BWBS Methods & Monitoring:
[https://bluewhalesblueskies.org/operators/methods-and-monitoring/](https://bluewhalesblueskies.org/operators/methods-and-monitoring/)
Read:
**Reducing Air Pollution**

---

## California overview

[https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/](https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/)
California describes BWBS as addressing whale-strike risk alongside underwater noise and air pollution.

---

## Potential outputs

Depending on the available methodology and data:

- Estimated NOx emissions
- Estimated greenhouse-gas emissions
- Relative emissions at different vessel speeds
- Geographic emissions intensity
- Difference between normal-speed and reduced-speed scenarios

---

## Deliverable

Impact selector:
○ Whale–vessel exposure
○ Underwater noise
○ Vessel emissions
○ Combined overview

---

# MILESTONE 10 — Scenario Analysis

## Goal

Turn the project into a simple GIS decision-support system.
Instead of asking only:

> What does the existing VSR zone cover?

also ask:

> What happens geographically under different hypothetical configurations?

---

## Example

### Current 2026 VSR boundary

High-exposure area covered: X%
Ocean area included: Y km²

### Hypothetical configuration

High-exposure area covered: Z%
Ocean area included: W km²
Then compare the tradeoff.

---

## Possible scenarios

- Current 2026 zone
- Slight geographic expansion
- Slight contraction
- Different seasonal boundaries
- Different exposure thresholds

These are **hypothetical GIS experiments**, not policy recommendations.

---

# FINAL APPLICATION VERSION

I do not need every milestone finished before September 1.

## Essential

Finish:

1. GIS fundamentals
2. ArcGIS web map
3. FeatureLayers
4. Spatial queries
5. Blue-whale layer
6. Commercial vessel layer
7. First spatial overlap / VSR coverage analysis

If I complete those, I already have a legitimate ArcGIS project.

## Stronger version

Add:

8. Underwater-noise analysis

## Later extensions

Add:

9. Emissions
10. Scenario analysis

Do not delay the Esri application trying to finish every possible feature.

---

# Final Project Architecture

Data sources:
**NOAA whale models**
[https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models](https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models)

-


**NOAA / USCG AIS vessel data**
[https://coast.noaa.gov/digitalcoast/tools/ais.html](https://coast.noaa.gov/digitalcoast/tools/ais.html)

-


**California / BWBS 2026 VSR information**
[https://bluewhalesblueskies.org/operators/](https://bluewhalesblueskies.org/operators/)
↓
**ArcGIS Pro / Python**

- Inspect data
- Clean data
- Project coordinate systems
- Crop Southern California region
- Perform spatial analysis
- Generate derived layers

↓
**ArcGIS Online**

- Host geographic layers
- Feature services
- Web maps

↓
**ArcGIS Maps SDK for JavaScript**
[https://developers.arcgis.com/javascript/latest/](https://developers.arcgis.com/javascript/latest/)
↓
**Next.js application**
↓
Interactive visualization of:

- Blue-whale habitat
- Commercial vessel traffic
- Vessel speeds
- VSR boundaries
- Whale–vessel spatial overlap
- Underwater-noise estimates
- Emissions estimates
- Scenario comparisons

---

# Most Important Bookmarks

## Esri / GIS

**ArcGIS Online Beginner Tutorial**
[https://learn.arcgis.com/en/projects/get-started-with-arcgis-online/](https://learn.arcgis.com/en/projects/get-started-with-arcgis-online/)
**ArcGIS Pro Beginner Tutorial**
[https://learn.arcgis.com/en/projects/get-started-with-arcgis-pro/](https://learn.arcgis.com/en/projects/get-started-with-arcgis-pro/)
**ArcGIS Tutorial Gallery**
[https://learn.arcgis.com/en/gallery/](https://learn.arcgis.com/en/gallery/)
**ArcGIS Living Atlas**
[https://livingatlas.arcgis.com/](https://livingatlas.arcgis.com/)
**ArcGIS Maps SDK for JavaScript**
[https://developers.arcgis.com/javascript/latest/](https://developers.arcgis.com/javascript/latest/)
**JavaScript SDK Tutorials**
[https://developers.arcgis.com/javascript/latest/tutorials/](https://developers.arcgis.com/javascript/latest/tutorials/)
**FeatureLayer Tutorial**
[https://developers.arcgis.com/javascript/latest/tutorials/add-a-feature-layer/](https://developers.arcgis.com/javascript/latest/tutorials/add-a-feature-layer/)
**Spatial Relationships Tutorial**
[https://developers.arcgis.com/javascript/latest/tutorials/find-spatial-relationships/](https://developers.arcgis.com/javascript/latest/tutorials/find-spatial-relationships/)

---

# Whale Resources

**NOAA Species Distribution Models**
[https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models](https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models)
**NOAA Cetacean Surveys**
[https://www.fisheries.noaa.gov/west-coast/science-data/ship-based-cetacean-and-ecosystem-assessment-surveys-california-current](https://www.fisheries.noaa.gov/west-coast/science-data/ship-based-cetacean-and-ecosystem-assessment-surveys-california-current)
**NOAA WhaleWatch**
[https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/whalewatch](https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/whalewatch)
**NOAA Blue Whale Hot Spots**
[https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/blue-whale-hot-spots](https://www.fisheries.noaa.gov/west-coast/marine-mammal-protection/blue-whale-hot-spots)

---

# Commercial Vessel / Ocean GIS Resources

**NOAA Vessel Traffic**
[https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html](https://coast.noaa.gov/digitalcoast/data/vesseltraffic.html)
**NOAA AccessAIS**
[https://coast.noaa.gov/digitalcoast/tools/ais.html](https://coast.noaa.gov/digitalcoast/tools/ais.html)
**NOAA Marine Cadastre Viewer**
[https://coast.noaa.gov/digitalcoast/tools/mmc.html](https://coast.noaa.gov/digitalcoast/tools/mmc.html)
**NOAA Digital Coast Data**
[https://coast.noaa.gov/digitalcoast/data/home.html](https://coast.noaa.gov/digitalcoast/data/home.html)

---

# California VSR / Research Resources

**Protecting Blue Whales and Blue Skies**
[https://bluewhalesblueskies.org/](https://bluewhalesblueskies.org/)
**2026 VSR Information**
[https://bluewhalesblueskies.org/operators/](https://bluewhalesblueskies.org/operators/)
**Methods & Monitoring**
[https://bluewhalesblueskies.org/operators/methods-and-monitoring/](https://bluewhalesblueskies.org/operators/methods-and-monitoring/)
**Program Impact**
[https://bluewhalesblueskies.org/impact/](https://bluewhalesblueskies.org/impact/)
**California Ocean Protection Council 2026 Overview**
[https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/](https://opc.ca.gov/2026/05/protecting-whales-from-ship-strikes/)
**Underwater Noise Research Report**
[https://bluewhalesblueskies.org/wp-content/uploads/BWBS\_2025\_ZoBell\_Report\_final.pdf](https://bluewhalesblueskies.org/wp-content/uploads/BWBS_2025_ZoBell_Report_final.pdf)

---

# One-Sentence Project Description

**An ArcGIS-based spatial analysis examining how California's Vessel Speed Reduction zones align with blue-whale habitat and large commercial vessel activity, with additional analysis of vessel-strike exposure, underwater noise, and shipping emissions.**

# Simple Explanation

The project combines:
**where whales are likely to be**

-


**where large commercial vessels travel and how fast they move**

-


**where California asks ships to slow down**
to determine how those geographic systems overlap.
The larger goal is to understand how GIS can help evaluate current marine-management strategies and explore the spatial tradeoffs of potential future configurations.