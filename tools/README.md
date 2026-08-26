# tools

**Owns:** small utilities that verify evidence recorded elsewhere in this repository.

This directory is **not** the analysis package. The Python analysis package
proposed in [architecture.md](../docs/architecture.md) does not exist yet and is
created by the processing-workflow milestone (M3). Nothing here processes data
for the analysis, produces a derived dataset, or writes anything that a result
depends on.

Anything added here has to earn its place by checking a claim the repository
already makes. If a tool starts producing analysis rather than verifying it, it
belongs in the analysis package instead.

---

## `m2_verify.py`

Regenerates the evidence behind the data-discovery milestone (M2) so a reader
can confirm that the numbers in [data-sources.md](../docs/data-sources.md) and
in the M2 decision records came from the data rather than from memory.

It does two separable things:

1. **Checks provenance.** It parses the *Local artifacts* table out of
   `docs/data-sources.md` and verifies every listed file against its recorded
   byte size and SHA-256. The manifest lives in that document rather than here,
   so the register is the single source of truth and this tool proves it is
   accurate instead of restating it. A mismatch is a non-zero exit.
2. **Recomputes the statistics.** Feature counts, value ranges and percentiles,
   AIS row populations and filters, geographic subset counts, VSR geometry
   checks and area, and the figures quoted in ADRs 0002 through 0006.

It does **not** assert that the prose is correct — only that the inputs are what
the register says they are, and that the statistics are what the inputs produce.
Comparing the two is the reader's job, and is deliberately not automated: the
point is to make the evidence inspectable, not to let a green check stand in
for reading it.

### Prerequisites

The source files it reads are **not committed** — they live under the ignored
local data root described in [data/README.md](../data/README.md). Retrieval
steps and parameters for every one of them are recorded in
[data-sources.md](../docs/data-sources.md). Without those files the tool reports
what is missing and exits non-zero; it will not download anything itself.

### Invocation

Run from the repository root.

```
python tools/m2_verify.py verify
```

Checks the manifest, then prints every regenerated statistic. Exit status `0`
means every artifact matched its recorded size and checksum.

```
python tools/m2_verify.py extract
```

Rebuilds the decompressed AIS inspection samples from the downloaded partial
responses. Deterministic — rerunning it reproduces byte-identical files, which
is what makes the `.csv` checksums in the manifest meaningful. Only needed if a
sample is missing or you want to confirm the extraction step itself.

### Versions this was run against

Recorded because GDAL and shapely versions can change geometry results at the
margins, and because "it worked on my machine" is not provenance.

| Component | Version |
|---|---|
| Python | 3.13.7 |
| numpy | 2.4.3 |
| pandas | 3.0.5 |
| shapely | 2.1.2 |
| pyproj | 3.7.2 |
| pyogrio | 0.13.0 |
| GDAL (via pyogrio) | 3.12.4 |

These were installed with `pip` into the author's user environment. **No pinned
environment file is committed yet**, because the project has no Python package
to pin one against — that arrives with the analysis package in M3, and this
table is the interim record.

### Reading the output

Three things in the output are worth knowing before quoting any of it:

- **The AIS figures come from a five-date sample taken at one time of day.**
  Every prefix begins at 00:00 UTC because a zip deflate stream can only be read
  from its start, and 00:00–00:34 UTC is 17:00–17:34 Pacific Daylight Time. The
  sample varies across dates; it does not vary across the day.
- **Volume figures are order-of-magnitude planning estimates**, produced by
  scaling a 34-minute window to 24 hours. They are not measurements.
- **The longitude profile is consistent with NOAA's published coverage
  limitation. It does not prove the cause.** Low record density offshore could
  be poor reception, genuinely low traffic, or both, and this sample cannot
  separate them.
