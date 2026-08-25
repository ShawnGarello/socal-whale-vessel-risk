# socal-whale-vessel-risk

An ArcGIS-based spatial analysis examining how California's Vessel Speed Reduction (VSR) zones align with blue-whale habitat and large commercial vessel activity off Southern California.

## Why

Southern California holds important habitat for endangered blue whales while also carrying some of the busiest commercial shipping traffic in the United States. Large vessels bring risk of ship strikes, underwater noise, and air and greenhouse-gas emissions. California's [Protecting Blue Whales and Blue Skies](https://bluewhalesblueskies.org/) program addresses this with voluntary speed-reduction zones — vessels of 300+ gross tons are asked to travel at 10 knots or less inside designated areas during the season.

This project asks a geographic question about that program:

> **How well do California's Vessel Speed Reduction zones spatially and seasonally align with the areas where commercial shipping creates the most pressure on blue whales and surrounding coastal ecosystems?**

## What it does

The analysis combines three things — where whales are likely to be, where large vessels travel and how fast, and where California asks ships to slow down — and measures how those geographies overlap:

- **Strike exposure** — where high modeled blue-whale density overlaps heavy vessel traffic, and how much of that overlap falls inside versus outside current VSR zones
- **Underwater noise** — where vessel traffic generates the greatest potential acoustic pressure within whale habitat
- **Emissions** — where shipping emissions concentrate, and how speed reduction could change them
- **Scenarios** — how alternative zone configurations would change those results

## What it is not

This is an exploratory, decision-support analysis, not a predictive or prescriptive one. It does not claim to predict where a whale will be struck, and it does not claim to identify California's objectively optimal VSR boundaries. Its purpose is to show where habitat, traffic, and management boundaries do and do not line up, and to make those spatial tradeoffs visible.

## Data sources

- [NOAA West Coast species distribution models](https://www.fisheries.noaa.gov/west-coast/science-data/species-distribution-models) — modeled blue-whale density
- [NOAA / USCG AIS vessel traffic](https://coast.noaa.gov/digitalcoast/tools/ais.html) — commercial vessel tracks and speeds
- [Blue Whales and Blue Skies](https://bluewhalesblueskies.org/operators/) — VSR zone boundaries and season definitions

## Stack

ArcGIS Pro and Python for data preparation and spatial analysis, ArcGIS Online for hosted feature services and web maps, and the ArcGIS Maps SDK for JavaScript inside a Next.js / TypeScript app for the interactive front end.

## Status

In progress. Foundations and the core habitat–traffic–VSR overlap analysis come first; noise, emissions, and scenario comparison follow.
