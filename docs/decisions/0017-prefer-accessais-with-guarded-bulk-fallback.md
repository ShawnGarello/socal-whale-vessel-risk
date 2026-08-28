# 0017 — Prefer AccessAIS extracts with a guarded daily-bulk fallback

**Status:** Proposed
**Date:** 2026-08-27

## Context

[ADR 0005](0005-analytical-period.md) fixes the AIS period at 1 July through
30 November 2024, 153 UTC dates. The current analysis command cleans one
explicitly supplied, single-UTC-date CSV extract. It deliberately reports date
completeness as `unverified`; timestamp bounds inside a file do not prove that
the publisher delivered every record for that date. Retrieval therefore needs
its own completeness and provenance boundary before cleaning begins.

NOAA documents two routes for the same historical broadcast-point product:

- [AccessAIS](https://coast.noaa.gov/digitalcoast/tools/ais.html) is a web-based
  clip-and-ship tool for an area and time period. Its
  [help sheet](https://coast.noaa.gov/data/marinecadastre/ais/accessais-help.pdf)
  says orders are limited to 2 GB, only one order per user can be active, and a
  delivery expires after 14 days or five accesses. An expired or failed order
  cannot be restarted; the same parameters must be submitted as a new order.
- The [2024 bulk index](https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/)
  exposes one nationwide compressed CSV for every calendar date. NOAA's
  [May 2026 AIS FAQ](https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf)
  directs requests under 2 GB to AccessAIS and larger requests to the bulk
  files.

Neither route supplies evidence that land-based receivers observed all traffic.
NOAA says collection interruptions occur and may make a daily file unusually
small, while the cause and duration of an outage may be unknown. Retrieval
completeness and AIS observability are therefore different questions. The
unresolved offshore observability domain remains owned by
[ADR 0002](0002-southern-california-study-area-extent.md).

## Evidence gathered on 2026-08-27 and 2026-08-28

### Verified from official documentation or read-only official endpoints

- AccessAIS supplies point data, not track lines or transit counts. It accepts
  a WGS 84 area and date range, uses an asynchronous email delivery, and has the
  limits above. NOAA documents a five-year rolling window and quarterly
  additions. The API's read-only
  [limit response](https://marinecadastre.gov/accessais/api/v1/search/limit)
  included 2024 in its available range and reported a 2 GB limit and one active
  order per user.
- A read-only request to the AccessAIS
  [status endpoint](https://marinecadastre.gov/accessais/api/v1/status)
  returned HTTP 200 and
  reported the API and its database as available. This proves only that the
  metadata service responded; it does not prove order creation or delivery.
- Read-only size estimates used `POST`
  `https://marinecadastre.gov/accessais/api/v1/search/limit` with
  `Content-Type: application/json`. This endpoint was observed in the AccessAIS
  web application's network behavior and current JavaScript bundle; NOAA does
  not document it as a supported production API. Its path, request shape and
  response shape may change without notice, so future production retrieval
  must not depend on it as a stable contract.
- The exact JSON fields are `fromDate`, `toDate`, `xMin`, `yMin`, `xMax` and
  `yMax`. The web application serializes dates as `YYYY-M-D 00:00:00` in UTC,
  without requiring zero-padded month or day values. The July request body was:

  ```json
  {
    "fromDate": "2024-7-1 00:00:00",
    "toDate": "2024-7-31 00:00:00",
    "xMin": -122,
    "yMin": 32,
    "xMax": -117,
    "yMax": 35
  }
  ```

  The other request bodies changed only `fromDate` and `toDate` to the exact
  strings shown below. The one-day body used `2024-7-15 00:00:00` for both date
  fields. The full-period body used `2024-7-1 00:00:00` and
  `2024-11-30 00:00:00` and returned HTTP 413. Because the endpoint is
  undocumented, these observed results do not independently establish its
  date-boundary semantics.
- The recorded estimates came from `data.estimate.n_records` and
  `data.estimate.n_bytes` in the JSON response. `data.estimate.limit` reported
  whether the estimate exceeded the service limit; the five monthly responses
  returned `false`. Top-level `status`, `success` and `valid` were also checked
  as `200`, `true` and `true`. The response also contained informational
  `data.bbox.sq_miles` and `data.runtime` values, which were not used in the
  volume decision.
- The five month-sized requests were each accepted by the estimator and below
  its 2 GB limit:

  | `fromDate` | `toDate` | Estimated records | Estimated bytes |
  |---|---|---:|---:|
  | `2024-7-1 00:00:00` | `2024-7-31 00:00:00` | 18,000,749 | 1,851,070,153 |
  | `2024-8-1 00:00:00` | `2024-8-31 00:00:00` | 18,286,289 | 1,880,613,226 |
  | `2024-9-1 00:00:00` | `2024-9-30 00:00:00` | 15,639,769 | 1,608,194,156 |
  | `2024-10-1 00:00:00` | `2024-10-31 00:00:00` | 16,356,927 | 1,681,834,982 |
  | `2024-11-1 00:00:00` | `2024-11-30 00:00:00` | 14,343,702 | 1,474,632,980 |
  | **Total of estimates** |  | **82,627,436** | **8,496,345,497** |

  These are service estimates, not delivered counts or measured file sizes.
  The request body contained only the dates and bounding coordinates shown
  above; no documented vessel-type filter was found and none is assumed.
- The bulk index listed all 366 dates in leap year 2024. Comparing it with the
  generated 153-date analytical-period calendar found zero missing filenames.
  Metadata-only HEAD requests for 1 July, 16 September, and 30 November returned
  HTTP 200, a `Content-Length`, `Last-Modified`, `ETag`, and
  `Accept-Ranges: bytes`. The five M2 prefix requests separately verified HTTP
  byte ranges against five dates. These checks establish listing and transfer
  capabilities, not complete-file integrity.

### Observed in the existing partial sample

Five 8 MiB bulk-file prefixes can be inflated into deterministic partial CSVs.
They support the existing schema and one-extract cleaner work, but none is a
complete day. The 15 July prefix is not strictly timestamp-ordered and its
observed timestamp bounds do not establish continuous coverage.

### Observed in the real bounded AccessAIS delivery

The author-controlled request for UTC date **2024-07-15**, WGS 84 longitude
**−122 to −117** and latitude **32 to 35**, completed as direct CSV
`AIS_178789652574876640_935-1787896526119.csv`. The manifest uses completion
timestamp `2026-08-28T15:44:29Z`. Read-only inspection measured 59,497,346 bytes
with SHA-256
`694ea3e8364de21467dea0affeb77e954d339e155d316dc4115b87ac01ffcca3`.
No independent HTTP `Content-Length`, `ETag`, or other object validator was
retained, so the manifest truthfully records local byte identity as verified
and independent byte completeness as `unverified`.

The direct CSV had the exact NOAA header and 582,419 rows. All 582,419
timestamps parsed, none were invalid, the only observed UTC date was
2024-07-15, and bounds were `2024-07-15T00:00:00Z` through
`2024-07-15T23:59:59Z`. Those bounds verify date organization, not transfer or
observational completeness.

The raw validator returned `passed: false` because 825 rows had invalid or
missing MMSIs and 2,233 had missing vessel types. The cleaner then accounted
for and removed those rows, 6,277 unavailable vessel types, 459,254
noncommercial vessel types, 13 exact duplicate rows, and 18 conflicting
MMSI/timestamp rows. The resulting 113,799-row
`noaa_marine_cadastre_ais_extract_v2` Parquet is 1,640,530 bytes, has SHA-256
`efbbcab006c63c8a4f021c7612dd3c84c25354a9805b55c4f7cebf00cc743ef6`,
and carries deterministic run ID `ais-362502c6a37b53e681b745f5`. It contains
179 unique commercial MMSIs: Cargo has 40,903 rows/67 MMSIs, Passenger has
42,363/67, and Tanker has 30,533/45. Required-field null rows and duplicate
MMSI/timestamp keys are both zero.

Two measured repeat cleaning runs reproduced the cleaned SHA-256 and run ID.
Runtime was 3.175186 and 3.094731 seconds; peak RSS was 1,591.441 and 1,589.828
MiB, with RSS increases of 1,553.262 and 1,551.969 MiB. The first run's peak
generated temporary/output disk footprint was approximately 1.576 MiB,
excluding the immutable raw CSV. The roughly 1.59 GiB peak memory is a real
scaling concern, not a basis for linear extrapolation. Monthly/full-period
processing has not been shown safe.

### Inferred

- Five sequential monthly AccessAIS orders are the smallest simple partition
  currently supported by the service estimates. Smaller partitions remain a
  recovery option if an estimate or order later exceeds the limit.
- AccessAIS should reduce transfer and peak local storage substantially relative
  to 153 nationwide daily archives. This is an inference from the estimator and
  the confirmed bulk sizes, not a measurement of delivered files.

### Still unverified

- Independent AccessAIS byte completeness, because HTTP length and stable
  object metadata were not retained with the exercised direct CSV; download and
  range-resume behavior also remain unverified.
- Safe monthly or full-period processing. The measured one-day peak memory
  requires optimization, bounded date-sized processing, spilling or memory
  controls, or another measured design before execution.
- No complete bulk daily archive has been downloaded, opened through its ZIP
  central directory, or checked through its CRC. NOAA publishes no checksum in
  the bulk index, so a locally computed SHA-256 would identify retrieved bytes
  but would not be a publisher-supplied digest.
- Neither route provides an authoritative expected record count for a UTC date.
  A zero or unusually small date can be detected but cannot automatically be
  classified as low traffic, receiver interruption, or incomplete delivery.

## Proposed decision

Use **five sequential, author-submitted AccessAIS monthly extracts** as the
preferred route, with the exact project map/context bounds and the five date
ranges in the table above. Use the **guarded one-day-at-a-time bulk route** only
when AccessAIS cannot create or deliver a bounded request, or when an exercised
delivery proves incompatible with the required processing boundary.

This decision remains **Proposed**. The real direct CSV passed the delivery-
format, local-identity, header/date, and cleaner-compatibility portion of the
gate. Independent transfer completeness was not retained, and the measured
one-day memory result does not establish safe monthly or full-period execution.
The acceptance criteria below therefore remain only partially satisfied.

AccessAIS order submission is an author-controlled action. It requires an email
address, acceptance of NOAA's privacy statement, and an external order. The
implemented code validates an author-supplied local delivery but does not submit
orders, store email addresses, or download from an expiring URL. Bulk URLs are
public and may later be retrieved by a guarded command without an account;
network retrieval is not implemented.

## Retrieval-manifest design

The implemented `noaa_ais_retrieval_manifest_v1` boundary creates one current
entry per explicitly supplied expected UTC date and keeps retry attempts inside
that entry. A new manifest pre-populates the complete accepted calendar from
`2024-07-01` through `2024-11-30`; only a byte-complete current entry with
status `verified` clears its date from the missing set. It is distinct from the
existing one-date cleaning quality report.

Each date entry records at least:

| Field | Required meaning |
|---|---|
| `utc_date` | Expected UTC calendar date; unique among current entries. |
| `route` | `accessais` or `bulk_daily`. |
| `request_id` | Stable local request identifier. For AccessAIS, also the token-free order or delivery identifier once known. |
| `source_locator` | Bulk public URL, or a redacted AccessAIS delivery reference. Expiring tokens and email addresses are never recorded. |
| `request_parameters` | Inclusive requested dates and WGS 84 coordinates, including coordinate order. |
| `source_filename` | Filename supplied by NOAA, not an invented completeness claim. |
| `retrieved_at_utc` | Actual successful retrieval timestamp. |
| `byte_size` and `sha256` | Identity of retained source bytes or, for a discarded bulk archive, the verified archive bytes before deletion. |
| `source_http_metadata` | Available `Content-Length`, `ETag`, and `Last-Modified`, recorded as source metadata rather than a checksum substitute. |
| `archive_verification` | Archive opens, member list is expected, and CRC validation passes. |
| `date_verification` | Parsed valid timestamps belong to the manifest date; observed min/max and row count are recorded. |
| `status` | `planned`, `ordered`, `available`, `transferring`, `retrieved`, `verified`, `unavailable`, `failed`, or `conflict`, with a reason and attempt history. |
| `cleaning_reference` | Later link to the one-date cleaning bundle and checksum; `observational_completeness_preserved: true` records that the cleaner retained `unverified`, and any attempted upgrade is rejected. |

The manifest must make four states separately visible:

1. **source listing or order availability**;
2. **byte-complete, archive-valid retrieval**;
3. **one verified manifest entry for every expected date**; and
4. **observational completeness**, which remains unverified because receiver
   coverage and outages are source limitations rather than transfer properties.

A period is retrieval-complete only when all 153 current entries have status
`verified` and the expected-date set difference is empty. Earliest/latest
timestamps, a plausible row count, or a filename alone never satisfies this
gate.

## Safe transfer, retry, and resume behavior

- Download to a uniquely named `.partial` file in the target filesystem. Hash
  while transferring when practical. Publish by atomic rename only after the
  expected HTTP response, final byte count, archive member and CRC checks, and
  date validation all pass.
- Resume a partial response only when the server advertises byte ranges and a
  stable validator proves it is the same object. Use `Range` with `If-Range`.
  If those conditions are absent or the validator changed, restart the
  temporary file; never append blindly.
- Raw retained deliveries are immutable. If a final path already exists and its
  checksum matches, reuse it without writing. If the checksum differs, stop
  with `conflict`; never replace it. A genuinely revised upstream object gets a
  new revision path and explicit lineage rather than an overwrite flag.
- A failed or corrupt attempt keeps its manifest history and reason but does not
  publish a final raw file. Retrying creates a new attempt. An expired
  AccessAIS link requires the author to submit the same parameters as a new
  order and record the new identifier; the old attempt is not rewritten.
- AccessAIS monthly deliveries are retained unchanged under ignored `data/raw/`.
  Any split into one-date CSVs is generated under `data/interim/` and is tied
  back to the delivery checksum.
- The bulk fallback handles one nationwide day at a time. After its byte count,
  SHA-256, ZIP CRC, member, header, UTC date, and scoped output have all been
  validated, the national archive is discarded as required by
  [the local data policy](../../data/README.md). The manifest retains its
  identity and validation results; the scoped generated file remains under
  `data/interim/`, not `data/raw/`.
- An overlapping AccessAIS order or repeated bulk date may not create a second
  current entry silently. Identical hashes are reusable evidence; different
  hashes require an explicit revision and conflict review.

Exact-row duplicates and conflicting `(MMSI, timestamp)` keys are not retrieval
failures. They remain visible source properties and are handled later by
[ADR 0013](0013-remove-conflicting-ais-key-records.md). A duplicated archive,
date, or manifest entry is a retrieval conflict and is handled here.

## Acceptance gate: one bounded one-day exercise

The author-controlled request for **2024-07-15**, WGS 84 bounds **longitude
-122.0 to -117.0 and latitude 32.0 to 35.0**, delivered the direct CSV described
above. The compatibility portion of this gate passed: the delivery format,
local byte identity, exact header/date organization, and cleaner behavior were
exercised without changing the source.

The read-only AccessAIS estimator returned **582,454 records and 59,895,276
bytes** for that one-day request. This is an estimate, approximately 59.9 MB
(57.1 MiB), not an expected checksum or delivered size. The alternative bulk
artifact is `AIS_2024_07_15.zip`, whose server-reported compressed size was
395,954,655 bytes during M2.

The exercise retained token-free parameters and a stable local identifier, the
unchanged delivered artifact, retrieval time, byte size, SHA-256, source
filename, and a one-date manifest entry. It:

1. established direct-CSV schema and exact date organization;
2. exercised the validator and `process-ais`, preserving the expected raw
   validation failure and successful cleaning reports;
3. recorded timestamp bounds and row counts without treating them as proof of
   transfer or observational completeness;
4. reproduced the cleaned checksum and run ID; and
5. measured DuckDB runtime, peak RSS, and generated disk footprint.

Route acceptance additionally requires independently supported transfer
completeness and a measured processing design that makes the proposed monthly
or full-period execution safe. Neither condition is satisfied here: source HTTP
metadata was not retained, and the one-day run peaked near 1.59 GiB RSS. No
monthly or full-period retrieval begins from this partially passed gate.

## Consequences

- Full-period transfer cannot start from this Proposed record. The immediate
  next step is resolving independent transfer-completeness evidence and the
  measured memory concern, not five monthly orders or 153 bulk downloads.
- The local retrieval command implements artifact inspection, the manifest
  contract, safe optional ZIP extraction, and an optional bridge to the current
  one-date cleaner. Materialization revalidates the inspected source identity
  before extraction and before publication. The command does not implement
  network transfer or resume. The bridge records
  `observational_completeness_preserved: true` only when the cleaner's
  `unverified` completeness field is unchanged and rejects an attempted
  upgrade.
- Monthly AccessAIS partitions bound each order below the currently reported
  service limit and make resubmission local to one month. Only one is submitted
  at a time.
- The bulk fallback remains reproducible and resumable without staging a
  national season. Its higher transfer volume is accepted only as a fallback
  cost.
- All raw, interim, manifest-attempt, and generated AIS files stay ignored.
  Committed documentation contains no email address, order token, cookie, or
  expiring delivery URL.

## Alternatives considered

**One AccessAIS order for the full period.** Rejected by the live estimator with
HTTP 413 and contradicted by the documented 2 GB limit.

**One AccessAIS order per day.** Not preferred. It would create 153 manual order
submissions even though the five monthly estimates fit. It remains a recovery
partition if an actual monthly order exceeds the estimate.

**Bulk daily files as the primary route.** Technically available but not
preferred. It transfers nationwide archives to retain a small spatial subset.
The guarded design makes it safe enough as a fallback, not efficient enough to
choose while the preferred route's independent completeness and scaling
questions are being resolved.

**Download the national season and filter afterwards.** Rejected. It violates
the local data policy, increases recovery cost, and is unnecessary for either
route.

**Treat the NOAA index as proof of complete observations.** Rejected. The index
proves that a named daily object is listed. It says nothing about receiver
coverage, collection interruptions, or records a receiver never observed.
