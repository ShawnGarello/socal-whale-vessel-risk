# 0013 — Remove conflicting AIS key records

**Status:** Accepted
**Date:** 2026-08-27

## Context

NOAA Marine Cadastre AIS flat CSVs can contain both fully identical rows and
repeated `(MMSI, BaseDateTime)` keys whose other fields disagree. The inspected
15 July prefix contains both. These cases are not equivalent:

- removing an additional byte-for-byte duplicate loses no information; but
- choosing one conflicting position, speed, or vessel attribute would assert
  that one source record is more trustworthy without evidence for that ranking.

The source is approximately time ordered, not guaranteed to be strictly
ordered, and no documented sequence or quality field identifies a preferred
record. A deterministic first-row or last-row rule would therefore be
repeatable but scientifically arbitrary. Retaining every conflict would pass
multiple positions for one vessel and timestamp into later spatial aggregation.

## Decision

The one-CSV AIS cleaning step applies two distinct policies after timestamp,
coordinate, map-extent, MMSI, reported-SOG, vessel-type, and commercial-group
filters:

1. For rows identical across all 17 published source fields, retain one row and
   count every additional copy as an `exact_duplicate_rows` removal. Because
   the rows are identical, which physical copy is retained cannot change the
   cleaned output.
2. After exact deduplication, if a valid MMSI and parsed UTC timestamp still
   identify more than one row, remove **every row in that key group**. Count the
   affected rows separately as `conflicting_mmsi_timestamp_rows`.

The quality report records row counts before and after both stages. The cleaned
Parquet output therefore contains at most one record for each MMSI/UTC-timestamp
key without inventing a source-quality ranking.

This decision is only about duplicate identity. It does not define an
implied-speed threshold, choose between position tracks, or establish a
behavioral plausibility rule.

## Consequences

- Later spatial aggregation cannot double-count exact copies or receive two
  different positions for the same vessel and timestamp.
- Conflicting source information is discarded conservatively. This can remove
  legitimate records, so the affected count remains visible in every run.
- The policy is deterministic and independent of input row order for the
  produced values: identical rows are interchangeable, and all conflicting
  rows are removed.
- If later evidence supplies a documented quality rank or correction rule, a
  new decision can supersede this one and select a record rather than remove the
  group.

The required M2 sample smoke check is supporting implementation evidence, not a
period-wide finding: among 2,495 commercial rows remaining after earlier
filters, the policy removed one additional exact duplicate and four rows with
conflicting MMSI/timestamp keys, leaving 2,490 cleaned rows.

## Alternatives considered

**Keep the first or last conflicting row.** Rejected. Physical file order is not
a documented quality rank, so this would convert ordering into an analytical
choice without evidence.

**Keep the row with the most populated attributes.** Rejected. Completeness
does not establish that its position or speed is correct, and the ranking would
mix unrelated field-quality judgments.

**Average conflicting positions or speeds.** Rejected. An average can create a
position or measurement the vessel never reported, and categorical attributes
cannot be averaged coherently.

**Retain every conflicting row.** Rejected. Later point counts and grid
aggregation would treat contradictory records as separate vessel activity.
