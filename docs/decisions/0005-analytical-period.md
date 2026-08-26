# 0005 — Use 1 July to 30 November 2024 as the Version 1 analytical period

**Status:** Accepted
**Date:** 2026-08-25

## Context

[Architecture](../architecture.md) deferred the analytical period until discovery established what temporal coverage the whale model and the AIS records actually share. Discovery found that they share almost nothing in the usual sense, because **only one of the three inputs has a time dimension at all.**

- **The blue-whale model is not a time series.** It is a single multi-year `Summer-Fall` average. `MONTH_NUMB` and `MONTH_NAME` are null throughout, and NOAA's field definition says the fields are "NOT USED because densities are averaged over multiple months". The InPort record gives the survey basis as **July–November** across nine years between 1991 and 2018. There is therefore no whale time step to align to — only a season the surface claims to represent.
- **The 2026 VSR season runs 22 April to 31 December 2026**, verified from the program's own page and map.
- **AIS broadcast points stop at 2024.** This was checked directly against the bulk archive on 2026-08-25: the year index and daily files return HTTP 200 for 2019 through 2024 and **404 for 2025 and 2026.** AccessAIS is documented as adding data every 90 days with a 145–165 day lag and holding a five-year rolling window.

The last point is decisive and was not anticipated. **The 2026 VSR season cannot be analysed, because the vessel data for it does not exist yet.** Version 1 has to combine a current zone with the most recent traffic available.

A second constraint follows from the first: since the whale surface represents summer and autumn, pairing it with vessel traffic from outside those months would combine a seasonal biological surface with traffic from a season it does not describe.

## Decision

The Version 1 analytical period is **1 July to 30 November 2024** — 153 days.

Version 1 combines three inputs of three different vintages, and states all three wherever results appear:

| Input | Vintage used |
|---|---|
| VSR zone geometry and program terms | **2026 season** — the current zone, which is what the research question asks about |
| Commercial vessel activity | **1 July – 30 November 2024** — the most recent data available |
| Modeled blue-whale density | **Multi-year summer–fall average**, survey basis 1991–2018 |

July to November is chosen because it is the survey window NOAA states for the whale model, so the traffic period matches the months the biological surface is built from. It also falls entirely inside the 22 April – 31 December VSR season window, so the comparison against the zone is made during months when the speed request is in effect.

## Consequences

- **Version 1 does not describe the 2026 season, and must never say it does.** It describes 2024 traffic evaluated against the zone as it stands in 2026. Any wording that implies otherwise is wrong.
- The vintage mismatch is a real limitation and belongs in the application, not only in the repository. A reader who assumes the traffic and the zone are contemporaneous will draw a stronger conclusion than the data supports.
- **Volume:** at the estimated ≈571,000 records per day for the study area, 153 days is **roughly 87 million AIS records**. Via the bulk route that means retrieving 153 national daily files at ~396 MB each — about 60 GB of transfer — and discarding most of each. The processing milestone should filter each day as it is retrieved rather than staging the whole set.
- Only one period is analysed, so Version 1 makes **no seasonal or month-to-month claims**, which is consistent with the project brief's non-goals and is now forced by the whale model regardless.
- This period is reproducible: the AIS archive is a fixed historical record, so a rerun retrieves identical files.
- **If the whale model's season definition resolves differently, this period may need to shift.** The register records an open question here: the survey basis is July–November, but a redistributor describes the same models' predictions as representing late June to early December. July–November is the conservative reading, anchored to what the publisher's own metadata states.
- When AIS for 2025 and 2026 is published, the analysis can be rerun on a more recent period. That would supersede this record rather than amend it.

## Alternatives considered

**The 2026 VSR season, 22 April – 31 December 2026.** The period the research question most naturally implies. **Not possible** — AIS broadcast points for 2026 are not published, and by the documented 145–165 day lag most of that season will not be available for months after it ends. This is a data availability blocker, not a preference.

**The full 2024 calendar year.** Rejected. It would include winter and spring months that the summer–fall whale surface does not represent, and would roughly double the AIS volume for traffic that cannot be paired with a matching whale value.

**22 April – 31 December 2024, mirroring the 2026 season dates onto 2024 traffic.** Rejected. It has the appeal of matching the season length, but it applies 2026 season dates to a year that had its own season, and it extends into months outside the whale model's basis. The 2024 season's own dates were not verified during discovery, and mirroring 2026's onto 2024 would be an invented alignment.

**A shorter window — a single month, or a few weeks.** Rejected. It would cut the volume problem substantially, but the whale surface is a multi-month average, so pairing it with a few weeks of traffic would give a result whose two halves describe very different time spans. Worth reconsidering only if the volume proves unmanageable, in which case the reduction gets recorded rather than made quietly.
