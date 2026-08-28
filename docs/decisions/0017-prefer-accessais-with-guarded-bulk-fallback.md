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

## Evidence gathered on 2026-08-27

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

### Inferred

- Five sequential monthly AccessAIS orders are the smallest simple partition
  currently supported by the service estimates. Smaller partitions remain a
  recovery option if an estimate or order later exceeds the limit.
- AccessAIS should reduce transfer and peak local storage substantially relative
  to 153 nationwide daily archives. This is an inference from the estimator and
  the confirmed bulk sizes, not a measurement of delivered files.

### Still unverified

- The author submitted the bounded 2024-07-15 acceptance-gate request, and NOAA
  was still processing it when the local verification boundary was completed.
  No artifact or token-free identifier has been supplied for inspection. The
  delivery contents, archive layout, source filename, download headers,
  range-resume behavior, and exact date-boundary semantics have not been
  observed.
- NOAA says AccessAIS and bulk files differ slightly in format and structure,
  with a 2026 upgrade planned to remove the differences. Whether an AccessAIS
  delivery satisfies the current exact 17-column cleaning header is unknown.
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

This decision remains **Proposed**. The service limits, estimates, bulk fallback,
and local verification boundary are documented, but the preferred delivery path
has not been exercised and its output has not reached the existing cleaner.
Acceptance requires the bounded one-day exercise below.

AccessAIS order submission is an author-controlled action. It requires an email
address, acceptance of NOAA's privacy statement, and an external order. The
implemented code validates an author-supplied local delivery but does not submit
orders, store email addresses, or download from an expiring URL. Bulk URLs are
public and may later be retrieved by a guarded command without an account;
network retrieval is not implemented.

## Retrieval-manifest design

The implemented `noaa_ais_retrieval_manifest_v1` boundary creates one current
entry per explicitly supplied expected UTC date and keeps retry attempts inside
that entry. It is distinct from the existing one-date cleaning quality report.
Generating and pre-populating all expected dates from `2024-07-01` through
`2024-11-30` is not implemented yet.

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
| `cleaning_reference` | Later link to the one-date cleaning bundle and checksum; retrieval verification never copies or upgrades its completeness field. |

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

## Acceptance gate: one bounded complete-day exercise

The author submitted one AccessAIS request for **2024-07-15**, WGS 84 bounds
**longitude -122.0 to -117.0 and latitude 32.0 to 35.0**. NOAA was still
processing it when the local verification boundary was completed. No delivery
artifact has been supplied, so submission itself does not pass this gate. That
date remains useful because its partial bulk prefix and existing cleaner smoke
result provide a checksum-bound comparison point without being mistaken for
complete-day evidence.

The read-only AccessAIS estimator returned **582,454 records and 59,895,276
bytes** for that one-day request. This is an estimate, approximately 59.9 MB
(57.1 MiB), not an expected checksum or delivered size. The alternative bulk
artifact is `AIS_2024_07_15.zip`, whose server-reported compressed size was
395,954,655 bytes during M2.

The exercise must retain the token-free order parameters and identifier, the
unchanged delivered artifact, retrieval time, byte size, SHA-256, archive
validation, source filename, and a one-date manifest entry. It then must:

1. establish the delivered schema and archive/date organization;
2. confirm whether the current validator and `process-ais` command accept it;
3. record valid timestamp bounds, per-date row counts, and any unexpected
   dates without treating those as proof of observational completeness;
4. run the existing validation and cleaning checks and preserve their reports;
5. measure the complete scoped day's DuckDB runtime and peak local footprint;
   and
6. compare the full-day evidence with the partial sample only to identify how
   the prefix differed, never to retroactively call the prefix complete.

Successful delivery, manifest verification, and cleaning compatibility are the
evidence needed to accept this route. If the order cannot be delivered or its
format is incompatible, the same date is the bounded user-authorized bulk
fallback exercise. No full-period retrieval begins until one route passes this
gate.

## Consequences

- Full-period transfer cannot start from this Proposed record. The immediate
  next step is receipt and read-only exercise of the submitted one-day delivery,
  not five monthly orders and not 153 bulk downloads.
- The local retrieval command implements artifact inspection, the manifest
  contract, safe optional ZIP extraction, and an optional bridge to the current
  one-date cleaner. It does not implement network transfer or resume. The bridge
  asserts that the cleaner's `unverified` completeness field is unchanged.
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
choose before AccessAIS is exercised.

**Download the national season and filter afterwards.** Rejected. It violates
the local data policy, increases recovery cost, and is unnecessary for either
route.

**Treat the NOAA index as proof of complete observations.** Rejected. The index
proves that a named daily object is listed. It says nothing about receiver
coverage, collection interruptions, or records a receiver never observed.
