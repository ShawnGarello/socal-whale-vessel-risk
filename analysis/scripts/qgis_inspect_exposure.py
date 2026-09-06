"""Render checksum-bound M6 review sheets locally; generation is not inspection.

Run with QGIS python-qgis.bat and QT_QPA_PLATFORM=offscreen. No input or
generation-time lineage is modified; no VSR geometry is written or exported.
"""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFillSymbol,
    QgsGraduatedSymbolRenderer,
    QgsMapRendererSequentialJob,
    QgsMapSettings,
    QgsProject,
    QgsRectangle,
    QgsRendererRange,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter

COLORS = ["#ececec", "#dce9ef", "#b3d6df", "#78b6cb", "#3685ad", "#15547c", "#102b4e"]


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def renderer(field):
    if "high_p" in field:
        breaks, colors = [-0.1, 0.5, 1.1], ["#ececec", "#15547c"]
    elif field.endswith("index"):
        breaks, colors = [0, 1e-15, 0.001, 0.005, 0.02, 0.1, 0.5, 1.0000001], COLORS
    elif field.startswith("product"):
        breaks, colors = [0, 1e-15, 0.01, 0.05, 0.1, 0.5, 2, 100], COLORS
    else:
        breaks, colors = [0, 1e-15, 0.001, 0.003, 0.006, 0.012, 0.024, 0.1], COLORS
    ranges = []
    for low, high, color in zip(breaks[:-1], breaks[1:], colors, strict=True):
        symbol = QgsFillSymbol.createSimple({"color": color, "outline_style": "no"})
        ranges.append(QgsRendererRange(low, high, symbol, f"{low:g}-{high:g}"))
    return QgsGraduatedSymbolRenderer(field, ranges), breaks, colors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--expected-5km", required=True)
    parser.add_argument("--expected-10km", required=True)
    parser.add_argument("--domain", type=Path, required=True)
    parser.add_argument("--vsr", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2] / "data/interim"
    if not args.output.resolve().is_relative_to(root) or args.output.exists():
        raise ValueError("fresh ignored interim output required")
    if (
        checksum(args.domain)
        != "4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77"
    ):
        raise ValueError("domain checksum differs")
    if (
        checksum(args.vsr)
        != "2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783"
    ):
        raise ValueError("snapshot checksum differs")
    checksums = {"5km": args.expected_5km, "10km": args.expected_10km}
    for size, expected in checksums.items():
        if checksum(args.bundle / f"exposure-{size}.parquet") != expected:
            raise ValueError("exposure checksum differs")
    app = QgsApplication([], False)
    app.initQgis()
    font_id = QFontDatabase.addApplicationFont(str(args.font.resolve()))
    if font_id < 0:
        raise ValueError("could not load the supplied local font")
    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
    project = QgsProject.instance()
    crs = QgsCoordinateReferenceSystem("EPSG:3310")
    geographic = QgsCoordinateReferenceSystem("EPSG:4326")
    transform = QgsCoordinateTransform(geographic, crs, project)
    masks = QgsVectorLayer(str(args.domain), "Accepted receiver domain", "ogr")
    masks.setSubsetString("\"scenario_id\" = 'receivers_50_nautical_miles'")
    source = QgsVectorLayer(str(args.vsr), "Immutable snapshot", "ogr")
    if not masks.isValid() or not source.isValid() or masks.featureCount() != 1:
        raise ValueError("context inputs did not open")
    # Match the analytical geographic edge densification, in memory only.
    vsr = QgsVectorLayer("Polygon?crs=EPSG:3310", "Local VSR context", "memory")
    for f in source.getFeatures():
        geometry = f.geometry().densifyByDistance(0.01)
        geometry.transform(transform)
        if not geometry.isGeosValid():
            raise ValueError("projected VSR context invalid")
        feature = QgsFeature()
        feature.setGeometry(geometry)
        vsr.dataProvider().addFeatures([feature])
    for layer, color in ((masks, "0,95,210,255"), (vsr, "220,100,0,255")):
        layer.renderer().setSymbol(
            QgsFillSymbol.createSimple(
                {
                    "style": "no",
                    "outline_color": color,
                    "outline_width": "0.45",
                }
            )
        )
        project.addMapLayer(layer)
    args.output.mkdir(parents=True)
    records = {
        "status": "rendered; visual inspection not completed by rendering",
        "date_utc": datetime.now(UTC).isoformat(),
        "qgis_version": Qgis.QGIS_VERSION,
        "input_sha256": checksums,
        "vsr_sha256": checksum(args.vsr),
        "domain_sha256": checksum(args.domain),
        "font_sha256": checksum(args.font),
        "layers": {},
        "sheets": {},
    }
    full = (-122, 32, -117, 35)
    fields = [
        "product_intensity",
        "log_traffic_intensity",
        "product_index",
        "log_traffic_index",
        "product_high_p90",
        "log_traffic_high_p90",
    ]
    detail = [
        ("shipping-corridors", (-120.15, 32.5, -117.1, 34.4)),
        ("northern-edge", (-121.4, 34.3, -119.8, 35.1)),
        ("southern-edge", (-119, 31.95, -117.1, 32.8)),
        ("receiver-boundary", (-121.6, 33.1, -120, 34.4)),
    ]
    for size in checksums:
        layer = QgsVectorLayer(
            str(args.bundle / f"exposure-{size}.parquet"), size, "ogr"
        )
        if not layer.isValid() or layer.crs().authid() != "EPSG:3310":
            raise ValueError("exposure layer did not open in EPSG:3310")
        project.addMapLayer(layer)
        present = [f for f in layer.getFeatures() if f.hasGeometry()]
        invalid = sum(not f.geometry().isGeosValid() for f in present)
        if invalid:
            raise ValueError("invalid qualified output geometry")
        records["layers"][size] = {
            "rows": layer.featureCount(),
            "nonempty_geometry_count": len(present),
            "invalid_geometries": invalid,
            "crs": layer.crs().authid(),
        }
        sets = {
            "methods": [(field, field, full) for field in fields],
            "details": [(name, "product_index", bounds) for name, bounds in detail],
        }
        for kind, panels in sets.items():
            sheet = QImage(
                2000, 100 + 580 * ((len(panels) + 1) // 2), QImage.Format.Format_ARGB32
            )
            sheet.fill(QColor("white"))
            painter = QPainter(sheet)
            painter.setPen(QColor("#172b3a"))
            painter.setFont(QFont(font_family, 16))
            painter.drawText(
                25, 30, f"M6 exploratory review | {size} | {kind} | not final headlines"
            )
            painter.setFont(QFont(font_family, 11))
            painter.drawText(
                25,
                55,
                "Orange: immutable VSR. Blue: receiver-qualified domain. "
                "White: excluded/no water geometry. Grey: valid zero/low.",
            )
            painter.drawText(
                25,
                77,
                "Uniform exposure within cell water; 2024 traffic, multi-year "
                "modeled whales, 2026 boundary; no collision probability.",
            )
            classifications = {}
            for index, (name, field, bounds) in enumerate(panels):
                x, y = (index % 2) * 1000, 100 + (index // 2) * 580
                style, breaks, colors = renderer(field)
                layer.setRenderer(style)
                settings = QgsMapSettings()
                settings.setLayers([vsr, masks, layer])
                settings.setDestinationCrs(crs)
                settings.setOutputSize(QSize(980, 490))
                settings.setBackgroundColor(QColor("white"))
                settings.setExtent(
                    transform.transformBoundingBox(QgsRectangle(*bounds))
                )
                job = QgsMapRendererSequentialJob(settings)
                job.start()
                job.waitForFinished()
                painter.setFont(QFont(font_family, 12))
                painter.drawText(x + 12, y + 22, name)
                painter.drawImage(x + 10, y + 30, job.renderedImage())
                painter.setFont(QFont(font_family, 8))
                for j, (low, high, color) in enumerate(
                    zip(breaks[:-1], breaks[1:], colors, strict=True)
                ):
                    px = x + 12 + j * 137
                    painter.fillRect(px, y + 534, 12, 12, QColor(color))
                    painter.drawText(px + 16, y + 545, f"{low:g} - {high:g}")
                classifications[name] = {
                    "field": field,
                    "breaks": breaks,
                    "bounds_lonlat": bounds,
                }
            painter.end()
            output = args.output / f"{size}-{kind}.png"
            if not sheet.save(str(output), "PNG"):
                raise ValueError("could not save local review image")
            records["sheets"][output.name] = {
                "sha256": checksum(output),
                "panels": classifications,
            }
        project.removeMapLayer(layer.id())
    (args.output / "render-report.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(records, indent=2))
    project.clear()
    app.exitQgis()


if __name__ == "__main__":
    main()
