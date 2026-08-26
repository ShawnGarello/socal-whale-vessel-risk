#!/usr/bin/env python3
"""Regenerate and check the evidence behind the M2 data-discovery findings.

This is a verification utility for one milestone, not the analysis package.
It reads local files that are deliberately not committed, recomputes the
numbers quoted in docs/data-sources.md and the M2 decision records, and
prints them so a reader can compare. It does not process data for the
analysis, does not write into data/, and must not grow into the M3 pipeline.

Two modes:

    python tools/m2_verify.py extract
        Rebuild the decompressed AIS inspection samples from the downloaded
        partial responses. Deterministic; safe to rerun.

    python tools/m2_verify.py verify
        Check every artifact in the provenance manifest against its recorded
        byte size and SHA-256, then recompute the M2 statistics.
        Exit status 0 means every artifact matched.

The manifest is not stored here. It is parsed out of the "Local artifacts"
table in docs/data-sources.md, so that document is the single source of truth
and this tool proves it is accurate rather than restating it.

See tools/README.md for the exact tool versions this was run against.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTER = REPO / "docs" / "data-sources.md"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")

# Southern California inspection box used throughout M2. It is the study-area
# box of ADR 0002 widened slightly so the AIS coverage falloff is visible.
SC_BOX = dict(lon_min=-122.5, lon_max=-117.0, lat_min=32.0, lat_max=35.2)

# The AIS date prefixes retained as the stratified sample.
AIS_DATES = ["2024_07_15", "2024_08_15", "2024_09_16", "2024_10_15", "2024_11_15"]

# Full compressed size of each sampled daily file, read from the server's
# Content-Length on the retrieval date. Used only for volume scaling.
AIS_FULL_ZIP_BYTES = {
    "2024_07_15": 395_954_655,
    "2024_08_15": 417_410_095,
    "2024_09_16": 367_566_530,
    "2024_10_15": 333_802_661,
    "2024_11_15": 329_394_301,
}

# The retained window: records strictly before this time are the complete
# whole minutes. See docs/data-sources.md, "Which rows each statistic uses".
WINDOW_CUTOFF = "T00:34:00"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rule(title: str) -> None:
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


def inflate_prefix(part_path: Path) -> str:
    """Decompress as much of a truncated zip as the deflate stream allows.

    The daily AIS file is a zip holding one CSV member. Only the leading
    bytes were retrieved, so the central directory is absent and zipfile
    cannot open it. The local file header at offset 0 is intact, which is
    enough to locate the start of the deflate stream and inflate it until
    the data runs out.
    """
    blob = part_path.read_bytes()
    if blob[:4] != b"PK\x03\x04":
        raise SystemExit(f"{part_path}: not a zip local file header")
    (_ver, _flag, method, _mt, _md, _crc, _csize, _usize,
     nlen, elen) = struct.unpack("<HHHHHIIIHH", blob[4:30])
    if method != 8:
        raise SystemExit(f"{part_path}: expected deflate, got method {method}")
    start = 30 + nlen + elen
    return zlib.decompressobj(-15).decompress(blob[start:]).decode("utf-8", "replace")


def sample_paths(date: str) -> tuple[Path, Path]:
    base = REPO / "data" / "raw" / "noaa-ais-2024"
    return base / f"AIS_{date}.head8MB.part", base / f"AIS_{date}.head_sample.csv"


# --------------------------------------------------------------------------
# extract
# --------------------------------------------------------------------------

def cmd_extract() -> int:
    """Rebuild each decompressed sample from its partial response.

    The final line of the inflated text is truncated because the download
    stopped mid-record, so it is dropped. Everything else is written
    verbatim with newline endings, which makes the output reproducible.
    """
    rule("extract: rebuilding AIS inspection samples from partial responses")
    for date in AIS_DATES:
        part, csv = sample_paths(date)
        if not part.exists():
            print(f"  MISSING  {part.relative_to(REPO)}")
            continue
        text = inflate_prefix(part)
        lines = text.split("\n")
        body = lines[:-1]           # drop the truncated final record
        csv.write_text("\n".join(body), encoding="utf-8", newline="\n")
        print(f"  {csv.relative_to(REPO)}  rows={len(body) - 1}  bytes={csv.stat().st_size}")
    print("\n  Rerun 'verify' to confirm the rebuilt files match the manifest.")
    return 0


# --------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------

def parse_manifest() -> list[dict]:
    """Read the 'Local artifacts' table out of the source register.

    Rows are recognised by containing a bare 64-character hex cell, so the
    surrounding prose can change without breaking this.
    """
    rows: list[dict] = []
    for line in REGISTER.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        digests = [c for c in cells if SHA_RE.match(c)]
        if not digests:
            continue
        paths = [c for c in cells if c.startswith("data/raw/")]
        sizes = [c for c in cells
                 if c.replace(",", "").isdigit() and len(c.replace(",", "")) >= 4]
        if not paths or not sizes:
            continue
        rows.append({
            "path": paths[0],
            "bytes": int(sizes[0].replace(",", "")),
            "sha256": digests[0],
        })
    return rows


def cmd_verify_manifest() -> tuple[int, int]:
    rule("verify: provenance manifest in docs/data-sources.md against local files")
    rows = parse_manifest()
    if not rows:
        raise SystemExit("no manifest rows parsed from docs/data-sources.md")
    ok = bad = 0
    for row in rows:
        target = REPO / row["path"]
        if not target.exists():
            print(f"  MISSING   {row['path']}")
            bad += 1
            continue
        size = target.stat().st_size
        digest = sha256_of(target)
        if size != row["bytes"]:
            print(f"  SIZE      {row['path']}: recorded {row['bytes']}, found {size}")
            bad += 1
        elif digest != row["sha256"]:
            print(f"  CHECKSUM  {row['path']}\n"
                  f"            recorded {row['sha256']}\n"
                  f"            found    {digest}")
            bad += 1
        else:
            print(f"  ok  {size:>12,} B  {digest[:16]}…  {row['path']}")
            ok += 1
    print(f"\n  {ok} artifact(s) matched, {bad} failed, {len(rows)} in manifest.")
    return ok, bad


# --------------------------------------------------------------------------
# whale model
# --------------------------------------------------------------------------

def check_whale() -> None:
    import numpy as np
    import shapely
    from pyogrio.raw import read
    from pyogrio import read_info

    gdb_b = REPO / "data/raw/noaa-swfsc-becker-2020b/swfsc_cce_becker_et_al_2020b.gdb"
    rule("whale model — Becker et al. 2020b, layer Blue_whale_summer_fall")
    if not gdb_b.exists():
        print("  extracted geodatabase not present; run the retrieval steps first")
        return

    info = read_info(gdb_b, layer="Blue_whale_summer_fall")
    print(f"  driver                {info['driver']}")
    print(f"  geometry type         {info['geometry_type']}")
    print(f"  feature count         {info['features']:,}")
    print(f"  CRS                   {info['crs']}")
    b = info["total_bounds"]
    print(f"  extent lon            {b[0]:.5f} .. {b[2]:.5f}")
    print(f"  extent lat            {b[1]:.5f} .. {b[3]:.5f}")

    meta, _, geom, data = read(gdb_b, layer="Blue_whale_summer_fall", read_geometry=True)
    cols = dict(zip(list(meta["fields"]), data))
    dens = cols["DENSITY"].astype("float64")
    area = cols["AREA_SQKM"].astype("float64")
    abund = cols["ABUNDANCE"].astype("float64")
    cv = cols["UNCERTAINTY"].astype("float64")

    for field in ("SPECIES", "STUDY", "STRATUM", "MODEL_TYPE", "SEASON"):
        print(f"  {field:<21} {sorted(set(cols[field].astype(str)))}")
    print(f"  MONTH_NUMB all null   {bool(np.isnan(cols['MONTH_NUMB'].astype('float64')).all())}")

    print(f"\n  DENSITY  min {dens.min():.6g}  median {np.median(dens):.6g}  max {dens.max():.6g}")
    print(f"  DENSITY  p95 {np.percentile(dens, 95):.6g}")
    print(f"  CV       min {cv.min():.4g}  median {np.median(cv):.4g}  max {cv.max():.4g}")
    print(f"  CV       -99999 sentinel present: {bool((cv == -99999).any())}")
    resid = np.abs(abund - dens * area)
    print(f"  max |ABUNDANCE - DENSITY*AREA_SQKM|  {resid.max():.3g}")
    print(f"  total modeled abundance   {abund.sum():.2f} animals")
    print(f"  total AREA_SQKM           {area.sum():,.1f} km2")

    g = shapely.from_wkb(geom)
    xmin, ymin, xmax, ymax = shapely.bounds(g).T
    full = area > 80
    print(f"\n  full-size cell width  median {np.median(xmax[full] - xmin[full]):.6f} deg")
    print(f"  full-size cell height median {np.median(ymax[full] - ymin[full]):.6f} deg")
    print(f"  cells with AREA_SQKM < 1 km2 (coast slivers)  {int((area < 1).sum())}")
    for lo, hi in ((30, 31), (34, 35), (48, 49)):
        sel = full & (ymin >= lo) & (ymin < hi)
        if sel.any():
            print(f"  mean AREA_SQKM {lo}-{hi}N   {area[sel].mean():.1f}")

    tree = shapely.STRtree(g)
    print("\n  point tests (density, CV):")
    for name, lon, lat in [
        ("Point Conception approach", -120.55, 34.42),
        ("Santa Barbara Channel", -119.70, 34.20),
        ("Santa Monica Bay", -118.55, 33.92),
        ("San Pedro Channel", -118.30, 33.60),
        ("Long Beach outer anchorage", -118.15, 33.68),
        ("San Diego approach", -117.30, 32.65),
        ("Tanner / Cortes Bank", -119.10, 32.75),
        ("San Nicolas Island (land)", -119.50, 33.25),
    ]:
        idx = tree.query(shapely.Point(lon, lat), predicate="intersects")
        if len(idx):
            i = idx[0]
            print(f"    {name:<28} {dens[i]:.6f}  {cv[i]:.3f}")
        else:
            print(f"    {name:<28} no cell (outside the modelled water area)")

    sub = (xmin >= -121.0) & (xmax <= -117.0) & (ymin >= 32.0) & (ymax <= 35.0)
    print(f"\n  cells fully within lon[-121,-117] lat[32,35]  {int(sub.sum())}")
    print(f"    area      {area[sub].sum():,.0f} km2")
    print(f"    abundance {abund[sub].sum():.2f} animals "
          f"({100 * abund[sub].sum() / abund.sum():.1f}% of the model total)")

    gdb_a = REPO / "data/raw/noaa-swfsc-becker-2020/swfsc_cce_becker_et_al_2020.gdb"
    if gdb_a.exists():
        print("\n  comparison product (2020, not selected):")
        for layer in ("Blue_whale_summer_fall", "Blue_whale_winter_spring"):
            m, _, _, d = read(gdb_a, layer=layer, read_geometry=False)
            c = dict(zip(list(m["fields"]), d))
            u = c["UNCERTAINTY"].astype("float64")
            print(f"    {layer}")
            print(f"      STUDY       {sorted(set(c['STUDY'].astype(str)))}")
            print(f"      MODEL_TYPE  {sorted(set(c['MODEL_TYPE'].astype(str)))}")
            print(f"      abundance   {c['ABUNDANCE'].astype('float64').sum():.1f}")
            print(f"      CV median {np.nanmedian(u):.3g}  max {np.nanmax(u):.3g}")


# --------------------------------------------------------------------------
# VSR zone
# --------------------------------------------------------------------------

def check_vsr():
    import numpy as np
    import shapely
    from shapely.geometry import shape, Point, box
    from shapely.ops import transform, nearest_points
    from pyproj import Transformer

    path = REPO / "data/raw/bwbs-vsr-2026/bwbs_ca_vsr_zone_2026.geojson"
    rule("VSR zone — BWBS/CMSF WhaleAtlas_2026, FID 126")
    if not path.exists():
        print("  geometry not present; run the retrieval steps first")
        return None

    doc = json.loads(path.read_text(encoding="utf-8"))
    feat = doc["features"][0]
    zone = shape(feat["geometry"])
    to3310 = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True)
    zp = transform(to3310.transform, zone)

    print(f"  declared CRS          {doc.get('crs')}")
    print(f"  geometry type         {zone.geom_type}")
    print(f"  valid                 {zone.is_valid}")
    rings = feat["geometry"]["coordinates"]
    print(f"  exterior vertices     {len(rings[0]):,}")
    print(f"  interior rings        {len(rings) - 1}")
    print(f"  bounds                {tuple(round(v, 5) for v in zone.bounds)}")
    print(f"  area (EPSG:3310)      {zp.area / 1e6:,.1f} km2")

    holes = []
    for ring in rings[1:]:
        p = shape({"type": "Polygon", "coordinates": [ring]})
        holes.append((transform(to3310.transform, p).area / 1e6, p.centroid.x, p.centroid.y))
    holes.sort(reverse=True)
    print(f"  total hole area       {sum(h[0] for h in holes):,.1f} km2")
    print("  largest holes (km2, lon, lat) — expected to be the Channel Islands:")
    for a, x, y in holes[:7]:
        print(f"    {a:8.1f}  {x:9.4f}  {y:8.4f}")

    published = [(41.97, -125.46), (40.34, -125.18), (37.69, -124.11), (36.32, -123.00),
                 (35.50, -123.00), (35.05, -122.10), (33.30, -121.21), (32.55, -117.13)]
    print("\n  distance from each published point to the exterior boundary (m, EPSG:3310):")
    for n, (lat, lon) in enumerate(published, 1):
        a, b = nearest_points(Point(lon, lat), zone.exterior)
        ax, ay = to3310.transform(a.x, a.y)
        bx, by = to3310.transform(b.x, b.y)
        print(f"    point {n}  ({lat:7.2f},{lon:9.2f})  {((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5:8.1f}")

    print("\n  containment tests:")
    for name, lon, lat in [
        ("Santa Barbara Channel", -119.70, 34.20),
        ("San Pedro Channel", -118.30, 33.60),
        ("San Diego approach", -117.30, 32.65),
        ("Tanner / Cortes Bank", -119.10, 32.75),
        ("far offshore SW of Bight", -121.00, 32.50),
        ("Los Angeles inner harbour", -118.22, 33.73),
    ]:
        print(f"    {'INSIDE ' if zone.contains(Point(lon, lat)) else 'outside'}  {name}")

    south = transform(to3310.transform, zone.intersection(box(-123, 31.5, -116.5, 35.0)))
    print(f"\n  zone area south of 35N  {south.area / 1e6:,.1f} km2 "
          f"({100 * south.area / zp.area:.1f}% of the zone)")
    return zone


# --------------------------------------------------------------------------
# study area candidates
# --------------------------------------------------------------------------

def check_study_area(zone) -> None:
    import numpy as np
    import shapely
    from shapely.geometry import box
    from shapely.ops import transform, unary_union
    from pyproj import Transformer
    from pyogrio.raw import read

    gdb = REPO / "data/raw/noaa-swfsc-becker-2020b/swfsc_cce_becker_et_al_2020b.gdb"
    rule("study-area candidates — water mask is the whale model's own coverage")
    if zone is None or not gdb.exists():
        print("  inputs not present")
        return

    _, _, geom, _ = read(gdb, layer="Blue_whale_summer_fall", read_geometry=True)
    water = unary_union(shapely.from_wkb(geom))
    to3310 = Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True).transform
    south_zone = transform(to3310, zone.intersection(box(-123, 31.5, -116.5, 35.3))).area / 1e6

    print(f"  {'candidate':<34}{'water km2':>11}{'in-zone':>10}{'out-zone':>10}{'% in':>7}{'zone capt':>11}")
    for name, bnds in [
        ("A  -121.0..-117.0, 32.0..35.0", (-121.0, 32.0, -117.0, 35.0)),
        ("B  -122.0..-117.0, 32.0..35.0", (-122.0, 32.0, -117.0, 35.0)),
        ("C  -122.5..-117.0, 32.0..35.2", (-122.5, 32.0, -117.0, 35.2)),
    ]:
        w = water.intersection(box(*bnds))
        wa = transform(to3310, w).area / 1e6
        iz = transform(to3310, w.intersection(zone)).area / 1e6
        print(f"  {name:<34}{wa:11,.0f}{iz:10,.0f}{wa - iz:10,.0f}"
              f"{100 * iz / wa:6.1f}%{100 * iz / south_zone:10.1f}%")

    b = shapely.segmentize(box(-122.0, 32.0, -117.0, 35.0), 0.01)
    x0, y0, x1, y1 = transform(to3310, b).bounds
    print(f"\n  candidate B projected bounds  x {x0:,.1f} .. {x1:,.1f}   y {y0:,.1f} .. {y1:,.1f}")
    print(f"  candidate B size              {(x1 - x0) / 1000:.1f} km x {(y1 - y0) / 1000:.1f} km")
    wb = transform(to3310, water.intersection(box(-122.0, 32.0, -117.0, 35.0))).area / 1e6
    print("  grid cell counts over candidate B water area:")
    for km in (1, 2, 2.5, 5, 10):
        print(f"    {km:4.1f} km cells -> {wb / (km * km):>10,.0f} water cells")
    s = 5000
    gx0, gy0 = np.floor(x0 / s) * s, np.floor(y0 / s) * s
    gx1, gy1 = np.ceil(x1 / s) * s, np.ceil(y1 / s) * s
    print(f"  5 km grid snapped to 5000 m multiples: x {gx0:,.0f}..{gx1:,.0f}  y {gy0:,.0f}..{gy1:,.0f}")
    print(f"    {int((gx1 - gx0) / s)} columns x {int((gy1 - gy0) / s)} rows "
          f"= {int((gx1 - gx0) / s) * int((gy1 - gy0) / s):,} cells")


# --------------------------------------------------------------------------
# AIS
# --------------------------------------------------------------------------

def load_ais(date: str):
    import pandas as pd
    _, csv = sample_paths(date)
    if not csv.exists():
        return None
    df = pd.read_csv(csv)
    df["dt"] = pd.to_datetime(df["BaseDateTime"])
    return df


def check_ais(zone) -> None:
    import numpy as np
    import pandas as pd
    import shapely

    rule("AIS — stratified sample of five daily prefixes, 2024")
    print("  Every prefix starts at 00:00 UTC because a zip deflate stream can only")
    print("  be read from its beginning. 00:00-00:34 UTC is 17:00-17:34 Pacific")
    print("  Daylight Time, so the sample covers five dates but ONE time of day.")

    frames = {}
    print(f"\n  {'date':<12}{'total rows':>12}{'in window':>11}{'after cutoff':>14}{'out-of-order':>14}")
    for date in AIS_DATES:
        df = load_ais(date)
        if df is None:
            print(f"  {date:<12}  sample missing — run 'extract'")
            continue
        cutoff = pd.Timestamp(f"{date.replace('_', '-')}{WINDOW_CUTOFF}")
        win = df[df["dt"] < cutoff]
        after = df[df["dt"] >= cutoff]
        t0 = df["dt"].min()
        late = int(((after["dt"] - t0).dt.total_seconds() > 3600).sum())
        frames[date] = (df, win)
        print(f"  {date:<12}{len(df):>12,}{len(win):>11,}{len(after):>14,}{late:>14,}")

    if not frames:
        return

    primary = "2024_07_15"
    df, win = frames[primary]
    print(f"\n  --- schema and quality, {primary}, full decompressed sample "
          f"({len(df):,} rows) ---")
    print(f"  columns: {list(df.columns[:-1])}")
    print(f"  fully identical duplicate rows      {int(df.duplicated().sum())}")
    print(f"  duplicate (MMSI, BaseDateTime)      {int(df.duplicated(subset=['MMSI', 'BaseDateTime']).sum())}")
    print(f"  LAT range   {df.LAT.min():.5f} .. {df.LAT.max():.5f}")
    print(f"  LON range   {df.LON.min():.5f} .. {df.LON.max():.5f}")
    for label, cond in [
        ("LAT == 91 (AIS sentinel)", df.LAT == 91),
        ("LON == 181 (AIS sentinel)", df.LON == 181),
        ("LAT == 0 and LON == 0", (df.LAT == 0) & (df.LON == 0)),
        ("|LAT| > 90", df.LAT.abs() > 90),
        ("|LON| > 180", df.LON.abs() > 180),
    ]:
        print(f"    {label:<32} {int(cond.sum())}")
    mm = df.MMSI.astype(str)
    print(f"    {'MMSI not 9 digits':<32} {int((mm.str.len() != 9).sum())}")
    print(f"    {'MMSI leading zero':<32} {int(mm.str.startswith('0').sum())}")
    print(f"    {'Heading == 511 (unavailable)':<32} {int((df.Heading == 511).sum())}"
          f"  ({100 * (df.Heading == 511).mean():.1f}%)")
    print(f"    {'COG == 360 (unavailable)':<32} {int((df.COG == 360).sum())}"
          f"  ({100 * (df.COG == 360).mean():.1f}%)")
    print("  missing values by column:")
    for c in df.columns[:-1]:
        n = int(df[c].isna().sum())
        if n:
            print(f"    {c:<20} {n:>8,}  ({100 * n / len(df):5.1f}%)")

    # -------- Southern California, retained window only --------
    print(f"\n  --- Southern California box {SC_BOX}, retained window only ---")
    print(f"  {'date':<12}{'SoCal rows':>11}{'% national':>11}{'MMSI':>7}"
          f"{'comm 60-89':>12}{'comm %':>9}{'>=100 m':>9}")
    shares, rates = [], []
    for date, (_full, w) in frames.items():
        sc = w[(w.LON >= SC_BOX["lon_min"]) & (w.LON <= SC_BOX["lon_max"]) &
               (w.LAT >= SC_BOX["lat_min"]) & (w.LAT <= SC_BOX["lat_max"])]
        comm = sc[sc.VesselType.between(60, 89)]
        big = comm[comm.Length >= 100]
        share = 100 * len(comm) / len(sc) if len(sc) else float("nan")
        shares.append(share)
        rates.append(len(sc) * (1440 / 34))
        print(f"  {date:<12}{len(sc):>11,}{100 * len(sc) / len(w):>10.2f}%"
              f"{sc.MMSI.nunique():>7}{len(comm):>12,}{share:>8.1f}%{len(big):>9,}")
    print(f"\n  commercial share across the five dates: "
          f"min {min(shares):.1f}%  max {max(shares):.1f}%  mean {sum(shares) / len(shares):.1f}%")
    print(f"  implied SoCal records/day (34-min scaling): "
          f"min {min(rates):,.0f}  max {max(rates):,.0f}  mean {sum(rates) / len(rates):,.0f}")
    print("  These scalings assume the 17:00-17:34 PDT rate holds all day. It")
    print("  almost certainly does not. Treat them as order-of-magnitude only.")

    # -------- reporting interval, speed, length --------
    sc = win[(win.LON >= SC_BOX["lon_min"]) & (win.LON <= SC_BOX["lon_max"]) &
             (win.LAT >= SC_BOX["lat_min"]) & (win.LAT <= SC_BOX["lat_max"])].copy()
    comm = sc[sc.VesselType.between(60, 89)].copy()
    print(f"\n  --- reporting interval, {primary} SoCal, retained window ---")
    for label, frame in [("all vessels", sc), ("commercial 60-89", comm),
                         ("commercial and moving (SOG>=1)", comm[comm.SOG.between(1, 102.2)])]:
        gaps = frame.sort_values(["MMSI", "dt"]).groupby("MMSI")["dt"].diff().dt.total_seconds().dropna()
        if len(gaps):
            print(f"    {label:<32} median {gaps.median():6.0f} s   n={len(gaps):,}")

    print(f"\n  --- SOG, {primary} SoCal commercial, retained window ---")
    sent = int((comm.SOG == 102.3).sum())
    clean = comm[comm.SOG < 102.2]["SOG"]
    print(f"    records                    {len(comm):,}")
    print(f"    SOG == 102.3 sentinel      {sent}  ({100 * sent / len(comm):.2f}%)")
    print(f"    SOG missing                {int(comm.SOG.isna().sum())}")
    print(f"    non-sentinel min/median/max {clean.min():.1f} / {clean.median():.1f} / {clean.max():.1f} kn")
    print(f"    negative SOG               {int((comm.SOG < 0).sum())}")
    print(f"    SOG > 40 excluding sentinel {int(((comm.SOG > 40) & (comm.SOG < 102.2)).sum())}")

    print(f"\n  --- Length per distinct commercial MMSI, {primary} ---")
    per = comm.groupby("MMSI")["Length"].max().dropna()
    bins = [0, 20, 50, 100, 150, 200, 250, 300, 400]
    counts = pd.cut(per, bins, right=False).value_counts().sort_index()
    for k, v in counts.items():
        print(f"    {str(k):<14} {v:>4}")

    print(f"\n  --- vessel type bands, {primary} SoCal, retained window ---")
    def band(v):
        if pd.isna(v):
            return "missing"
        v = int(v)
        for lo, hi, name in [(60, 69, "60-69 passenger"), (70, 79, "70-79 cargo"),
                             (80, 89, "80-89 tanker"), (30, 39, "30-39 fish/tow/sail/pleasure"),
                             (50, 59, "50-59 special craft")]:
            if lo <= v <= hi:
                return name
        return "0 not available" if v == 0 else "other"
    for k, v in sc.VesselType.map(band).value_counts().items():
        print(f"    {k:<32} {v:>6,}  ({100 * v / len(sc):5.1f}%)")

    # -------- longitude profile --------
    print(f"\n  --- records by longitude band, retained window, all five dates ---")
    print(f"  {'band':<22}{'all':>10}{'commercial':>13}")
    allsc = pd.concat([w[(w.LON >= SC_BOX['lon_min']) & (w.LON <= SC_BOX['lon_max']) &
                         (w.LAT >= SC_BOX['lat_min']) & (w.LAT <= SC_BOX['lat_max'])]
                       for _f, w in frames.values()])
    allcm = allsc[allsc.VesselType.between(60, 89)]
    edges = np.arange(-122.5, -116.9, 0.5)
    ha = pd.cut(allsc.LON, edges).value_counts().sort_index()
    hc = pd.cut(allcm.LON, edges).value_counts().sort_index()
    for k in ha.index:
        print(f"  {str(k):<22}{ha[k]:>10,}{hc.get(k, 0):>13,}")
    west = allsc[allsc.LON < -120.5]
    print(f"\n  west of -120.5:  {len(west):,} of {len(allsc):,} SoCal rows "
          f"({100 * len(west) / len(allsc):.2f}%)")
    print("  This pattern is CONSISTENT WITH NOAA's published 40-50 mile coverage")
    print("  limit. It does not by itself distinguish poor reception from low traffic.")

    if zone is not None:
        pts = shapely.points(allsc.LON.values, allsc.LAT.values)
        inz = shapely.contains(zone, pts)
        cpts = shapely.points(allcm.LON.values, allcm.LAT.values)
        cinz = shapely.contains(zone, cpts)
        print(f"\n  in the 2026 VSR zone (snapshot orientation only, NOT a result):")
        print(f"    all SoCal rows     {int(inz.sum()):,} of {len(allsc):,}  ({100 * inz.mean():.1f}%)")
        print(f"    commercial 60-89   {int(cinz.sum()):,} of {len(allcm):,}  ({100 * cinz.mean():.1f}%)")

    # -------- volume --------
    print("\n  --- volume, order-of-magnitude planning estimate ---")
    part, csv = sample_paths(primary)
    blob = part.read_bytes()
    (_v, _f, _m, _mt, _md, _c, csize, usize, _n, _e) = struct.unpack("<HHHHHIIIHH", blob[4:30])
    print(f"    {primary} declared compressed size   {csize:,} bytes")
    print(f"    {primary} declared uncompressed size {usize:,} bytes")
    nat = len(win) * (1440 / 34)
    print(f"    national rows in retained window     {len(win):,}")
    print(f"    implied national rows/day            {nat / 1e6:.2f} million")
    print(f"    implied bytes/row cross-check        {usize / nat:.1f}")
    print("    compressed size of each sampled day:")
    for d, n in AIS_FULL_ZIP_BYTES.items():
        print(f"      {d}  {n:,} bytes")
    mean_zip = sum(AIS_FULL_ZIP_BYTES.values()) / len(AIS_FULL_ZIP_BYTES)
    print(f"    mean over the five sampled days      {mean_zip / 1e6:.0f} MB")
    print(f"    153 days at that mean                {153 * mean_zip / 1e9:.0f} GB of transfer")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def cmd_verify() -> int:
    import numpy, pandas, pyogrio, pyproj, shapely
    rule("tool versions")
    print(f"  python   {sys.version.split()[0]}")
    print(f"  numpy    {numpy.__version__}")
    print(f"  pandas   {pandas.__version__}")
    print(f"  shapely  {shapely.__version__}")
    print(f"  pyproj   {pyproj.__version__}")
    print(f"  pyogrio  {pyogrio.__version__}  (GDAL {pyogrio.__gdal_version_string__})")

    ok, bad = cmd_verify_manifest()
    zone = None
    try:
        check_whale()
        zone = check_vsr()
        check_study_area(zone)
        check_ais(zone)
    except ImportError as exc:
        print(f"\n  a dependency is missing: {exc}")
        return 2

    rule("result")
    if bad:
        print(f"  FAILED — {bad} artifact(s) did not match the manifest.")
        return 1
    print(f"  Manifest OK: {ok} artifact(s) matched recorded size and SHA-256.")
    print("  Statistics above regenerate the values quoted in docs/data-sources.md")
    print("  and in the M2 decision records. Compare them by eye; this tool does")
    print("  not assert the documents are correct, only that the inputs are.")
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if mode == "extract":
        return cmd_extract()
    if mode == "verify":
        return cmd_verify()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
