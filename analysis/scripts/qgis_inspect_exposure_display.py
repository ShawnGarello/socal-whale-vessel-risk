"""Inspect an exact exposure display GeoJSON and render local review sheets.

The exported GeoJSON is opened directly through OGR.  Its checksum, manifest,
CRS, fields, values, geometry counts, and areas are checked before rendering.
The immutable VSR snapshot is used only as local visual context and is never
written to an output layer.  Rendering does not itself complete human visual
inspection; the exact sheets still must be viewed and recorded separately.

Run with QGIS ``python-qgis.bat`` and ``QT_QPA_PLATFORM=offscreen``.
"""

import argparse
import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

from osgeo import gdal
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsFillSymbol,
    QgsGraduatedSymbolRenderer,
    QgsMapRendererSequentialJob,
    QgsMapSettings,
    QgsProject,
    QgsRectangle,
    QgsRendererRange,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter

INDEX_BREAKS = (0.0, 1e-15, 0.001, 0.005, 0.02, 0.1, 0.5, 1.0000001)
INDEX_COLORS = (
    "236,236,236,210",
    "220,233,239,215",
    "179,214,223,220",
    "120,182,203,225",
    "54,133,173,230",
    "21,84,124,235",
    "16,43,78,240",
)
BOOLEAN_BREAKS = (-0.1, 0.5, 1.1)
BOOLEAN_COLORS = ("236,236,236,180", "21,84,124,235")
EXPECTED_FIELDS = {
    "id",  # OGR exposes the GeoJSON Feature.id as a provider field.
    "object_id",
    "cell_id",
    "water_area_km2",
    "qualified_area_km2",
    "product_intensity",
    "product_index",
    "product_high_p90",
    "log_traffic_intensity",
    "log_traffic_index",
    "log_traffic_high_p90",
}
VIEWS = {
    "full-extent": (-122.0, 32.0, -117.0, 35.0),
    "shipping-corridors": (-120.15, 32.5, -117.1, 34.4),
    "receiver-boundary": (-121.6, 33.1, -120.0, 34.4),
    "coast-and-islands": (-120.6, 33.2, -117.8, 34.6),
    "northern-edge": (-121.4, 34.3, -119.8, 35.1),
    "southern-edge": (-119.0, 31.95, -117.1, 32.8),
}


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def renderer(field):
    if field.endswith("high_p90"):
        breaks, colors = BOOLEAN_BREAKS, BOOLEAN_COLORS
    else:
        breaks, colors = INDEX_BREAKS, INDEX_COLORS
    ranges = []
    for low, high, color in zip(breaks[:-1], breaks[1:], colors, strict=True):
        symbol = QgsFillSymbol.createSimple({"color": color, "outline_style": "no"})
        ranges.append(QgsRendererRange(low, high, symbol, f"{low:g} - {high:g}"))
    return QgsGraduatedSymbolRenderer(field, ranges), breaks, colors


def inspect_features(layer):
    records = []
    types = set()
    parts = rings = vertices = 0
    invalid = []
    empty = []
    for feature in layer.getFeatures():
        geometry = feature.geometry()
        cell_id = feature["cell_id"]
        if geometry.isEmpty():
            empty.append(cell_id)
            continue
        if not geometry.isGeosValid():
            invalid.append(cell_id)
        wkb_type = geometry.wkbType()
        types.add(QgsWkbTypes.displayString(wkb_type))
        polygons = (
            geometry.asMultiPolygon()
            if QgsWkbTypes.isMultiType(wkb_type)
            else [geometry.asPolygon()]
        )
        for polygon in polygons:
            parts += 1
            rings += max(len(polygon) - 1, 0)
            vertices += sum(len(ring) for ring in polygon)
        records.append(
            {
                "cell_id": cell_id,
                "qualified_area_km2": feature["qualified_area_km2"],
                "product_index": feature["product_index"],
                "log_traffic_index": feature["log_traffic_index"],
                "product_high_p90": feature["product_high_p90"],
                "log_traffic_high_p90": feature["log_traffic_high_p90"],
            }
        )
    return {
        "records": records,
        "types": sorted(types),
        "polygon_parts": parts,
        "interior_rings": rings,
        "ring_vertices": vertices,
        "invalid": invalid,
        "empty": empty,
    }


def render_sheet(layer, vsr, panels, output, font_family):
    rows = (len(panels) + 1) // 2
    sheet = QImage(2000, 105 + rows * 580, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("white"))
    painter = QPainter(sheet)
    painter.setPen(QColor("#172b3a"))
    painter.setFont(QFont(font_family, 16))
    painter.drawText(
        25, 30, "M6 exposure display export | local review | not a final headline"
    )
    painter.setFont(QFont(font_family, 10))
    painter.drawText(
        25,
        55,
        "Product is primary; log traffic is sensitivity. Orange: immutable "
        "local VSR context.",
    )
    painter.drawText(
        25,
        78,
        "Only receiver-qualified water renders. Uniform-within-cell assumption; "
        "no collision probability.",
    )
    panel_records = {}
    for index, (name, field, bounds) in enumerate(panels):
        x = (index % 2) * 1000
        y = 105 + (index // 2) * 580
        style, breaks, colors = renderer(field)
        layer.setRenderer(style)
        settings = QgsMapSettings()
        settings.setLayers([vsr, layer])
        settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        settings.setExtent(QgsRectangle(*bounds))
        settings.setOutputSize(QSize(980, 490))
        settings.setBackgroundColor(QColor("white"))
        job = QgsMapRendererSequentialJob(settings)
        job.start()
        job.waitForFinished()
        painter.setFont(QFont(font_family, 12))
        painter.drawText(x + 12, y + 22, name)
        painter.drawImage(x + 10, y + 30, job.renderedImage())
        painter.setFont(QFont(font_family, 8))
        for legend_index, (low, high, color) in enumerate(
            zip(breaks[:-1], breaks[1:], colors, strict=True)
        ):
            legend_x = x + 12 + legend_index * 137
            painter.fillRect(
                legend_x,
                y + 534,
                12,
                12,
                QColor(*[int(channel) for channel in color.split(",")]),
            )
            painter.drawText(legend_x + 16, y + 545, f"{low:g} - {high:g}")
        panel_records[name] = {"field": field, "bounds_lon_lat": list(bounds)}
    painter.end()
    if not sheet.save(str(output), "PNG"):
        raise ValueError("could not save local review sheet")
    return panel_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--vsr", type=Path, required=True)
    parser.add_argument("--vsr-sha256", required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    interim = (Path(__file__).resolve().parents[2] / "data" / "interim").resolve()
    if not args.output_dir.resolve().is_relative_to(interim):
        raise ValueError("inspection requires an ignored interim output directory")
    if args.output_dir.exists():
        raise ValueError("inspection requires a fresh output directory")
    if checksum(args.export) != args.sha256:
        raise ValueError("exposure display checksum mismatch")
    if checksum(args.vsr) != args.vsr_sha256:
        raise ValueError("local VSR snapshot checksum mismatch")
    manifest_path = args.export.with_name(args.export.name + ".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["output"]["sha256"] != args.sha256:
        raise ValueError("display manifest records a different output checksum")

    application = QgsApplication([], False)
    application.initQgis()
    font_id = QFontDatabase.addApplicationFont(str(args.font.resolve()))
    if font_id < 0:
        raise ValueError("could not load the supplied local font")
    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
    project = QgsProject.instance()
    layer = QgsVectorLayer(str(args.export), "Exposure display export", "ogr")
    source_vsr = QgsVectorLayer(str(args.vsr), "Immutable local VSR context", "ogr")
    if not layer.isValid() or not source_vsr.isValid():
        raise ValueError("QGIS could not open a supplied layer")
    if layer.crs().authid() != "EPSG:4326" or not layer.crs().isGeographic():
        raise ValueError("exposure display must open as geographic EPSG:4326")
    if {field.name() for field in layer.fields()} != EXPECTED_FIELDS:
        raise ValueError("exposure display fields differ")
    if source_vsr.featureCount() != 1:
        raise ValueError("local VSR context must contain exactly one feature")
    vsr = QgsVectorLayer("Polygon?crs=EPSG:4326", "Local VSR outline", "memory")
    for source_feature in source_vsr.getFeatures():
        feature = QgsFeature()
        feature.setGeometry(source_feature.geometry())
        vsr.dataProvider().addFeatures([feature])
    vsr.renderer().setSymbol(
        QgsFillSymbol.createSimple(
            {
                "style": "no",
                "outline_color": "220,100,0,255",
                "outline_width": "0.6",
            }
        )
    )
    project.addMapLayer(layer)
    project.addMapLayer(vsr)

    measured = inspect_features(layer)
    records = measured["records"]
    if measured["invalid"] or measured["empty"]:
        raise ValueError("exposure display has invalid or empty geometry")
    for field in ("product_index", "log_traffic_index"):
        values = [record[field] for record in records if record[field] is not None]
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values):
            raise ValueError(f"{field} is outside [0,1]")
    declared = manifest["output"]
    extent = layer.extent()
    measured_extent = [
        extent.xMinimum(),
        extent.yMinimum(),
        extent.xMaximum(),
        extent.yMaximum(),
    ]
    qualified_area = math.fsum(record["qualified_area_km2"] for record in records)
    agreements = {
        "feature_count": layer.featureCount() == declared["feature_count"],
        "unique_cell_count": len({record["cell_id"] for record in records})
        == declared["unique_cell_count"],
        "polygon_parts": measured["polygon_parts"] == declared["polygon_part_count"],
        "interior_rings": measured["interior_rings"] == declared["interior_ring_count"],
        "ring_vertices": measured["ring_vertices"] == declared["coordinate_count"],
        "qualified_area": math.isclose(
            qualified_area,
            declared["qualified_area_km2_total"],
            rel_tol=1e-12,
            abs_tol=1e-9,
        ),
        "extent": all(
            math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
            for actual, expected in zip(
                measured_extent, declared["bounds_lon_lat"], strict=True
            )
        ),
    }
    if not all(agreements.values()):
        raise ValueError("QGIS measurements differ from the display manifest")

    args.output_dir.mkdir(parents=True)
    sheets = {}
    panel_sets = {
        "methods": [
            ("Primary proportional index", "product_index", VIEWS["full-extent"]),
            (
                "Log-traffic sensitivity index",
                "log_traffic_index",
                VIEWS["full-extent"],
            ),
            ("Primary all-valid p90", "product_high_p90", VIEWS["full-extent"]),
            ("Log-traffic all-valid p90", "log_traffic_high_p90", VIEWS["full-extent"]),
        ],
        "details": [
            (name.replace("-", " ").title(), "product_index", bounds)
            for name, bounds in VIEWS.items()
            if name != "full-extent"
        ],
    }
    for name, panels in panel_sets.items():
        output = args.output_dir / f"exposure-display-{name}.png"
        sheet_panels = render_sheet(layer, vsr, panels, output, font_family)
        sheets[output.name] = {
            "sha256": checksum(output),
            "panels": sheet_panels,
        }

    report = {
        "status": "rendered; human visual review not performed by this script",
        "date_utc": datetime.now(UTC).isoformat(),
        "inspected_file": args.export.name,
        "inspected_sha256": args.sha256,
        "manifest_sha256": checksum(manifest_path),
        "vsr_sha256": args.vsr_sha256,
        "qgis_version": Qgis.QGIS_VERSION,
        "gdal_version": gdal.VersionInfo("RELEASE_NAME"),
        "layer": {
            "provider": layer.dataProvider().name(),
            "crs": layer.crs().authid(),
            "feature_count": layer.featureCount(),
            "fields": [field.name() for field in layer.fields()],
            "extent": measured_extent,
        },
        "geometry": {
            "wkb_types": measured["types"],
            "polygon_parts": measured["polygon_parts"],
            "interior_rings": measured["interior_rings"],
            "ring_vertices": measured["ring_vertices"],
            "empty": measured["empty"],
            "invalid": measured["invalid"],
        },
        "values": {
            "qualified_area_km2": qualified_area,
            "product_index_nulls": sum(
                record["product_index"] is None for record in records
            ),
            "log_traffic_index_nulls": sum(
                record["log_traffic_index"] is None for record in records
            ),
            "product_high_p90_count": sum(
                record["product_high_p90"] is True for record in records
            ),
            "log_traffic_high_p90_count": sum(
                record["log_traffic_high_p90"] is True for record in records
            ),
        },
        "agrees_with_manifest": agreements,
        "sheets": sheets,
        "visual_review": "not_performed_by_this_script",
    }
    (args.output_dir / "render-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    json.dump(report, sys.stdout, indent=2)
    print()
    project.clear()
    application.exitQgis()


if __name__ == "__main__":
    main()
