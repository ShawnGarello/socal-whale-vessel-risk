"""Render an exact checksum-bound vessel grid in QGIS; review images separately.

Run using QGIS's python-qgis.bat with QT_QPA_PLATFORM=offscreen. This script
does not modify inputs or claim visual verification from image generation.
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
    QgsFillSymbol,
    QgsGraduatedSymbolRenderer,
    QgsMapRendererSequentialJob,
    QgsMapSettings,
    QgsProject,
    QgsRectangle,
    QgsRendererRange,
    QgsRuleBasedRenderer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--masks", type=Path, required=True)
    parser.add_argument("--vsr", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--field",
        default="vessel_km_all_commercial",
        choices=(
            "vessel_km_all_commercial",
            "reported_sog_mean_knots_all_commercial",
            "implied_speed_mean_knots_all_commercial",
        ),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2] / "data/interim"
    if not args.output_dir.resolve().is_relative_to(root) or args.output_dir.exists():
        raise ValueError("inspection requires a fresh ignored interim directory")
    if checksum(args.grid) != args.sha256:
        raise ValueError("grid checksum mismatch")
    if (
        checksum(args.masks)
        != "4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77"
    ):
        raise ValueError("accepted-domain context checksum mismatch")
    if (
        checksum(args.vsr)
        != "2358bd39df3f3ca084b8ef8c3ea3321c7d93fe9bec76f5a2d61e01370549c783"
    ):
        raise ValueError("immutable VSR snapshot checksum mismatch")
    app = QgsApplication([], False)
    app.initQgis()
    project = QgsProject.instance()
    grid = QgsVectorLayer(str(args.grid), "Vessel km, selected commercial types", "ogr")
    masks = QgsVectorLayer(str(args.masks), "Qualified receiver domain", "ogr")
    vsr = QgsVectorLayer(str(args.vsr), "2026 VSR context", "ogr")
    for layer in (grid, masks, vsr):
        if not layer.isValid():
            raise ValueError(f"could not open {layer.name()}")
        project.addMapLayer(layer)
    masks.setSubsetString("\"scenario_id\" = 'receivers_50_nautical_miles'")
    if (
        masks.featureCount() != 1
        or grid.featureCount() != 4516
        or grid.crs().authid() != "EPSG:3310"
    ):
        raise ValueError("unexpected features or CRS")
    invalid = sum(
        not feature.geometry().isGeosValid() for feature in grid.getFeatures()
    )
    if invalid:
        raise ValueError("invalid grid geometry")
    # Common physical-unit breaks for all candidates: never per-layer quantiles.
    breaks = [0, 1e-12, 100, 1000, 10000, 100000, 1e15]
    if args.field != "vessel_km_all_commercial":
        breaks = [0, 5, 10, 15, 20, 25, 35.000001]
    colors = ["#f3f3f3", "#dce9ef", "#9bc6d4", "#4592b5", "#185886", "#122b56"]
    ranges = []
    for low, high, color in zip(breaks[:-1], breaks[1:], colors, strict=True):
        symbol = QgsFillSymbol.createSimple({"color": color, "outline_style": "no"})
        ranges.append(QgsRendererRange(low, high, symbol, f"{low:g}-{high:g}"))
    renderer = QgsGraduatedSymbolRenderer(args.field, ranges)
    if args.field != "vessel_km_all_commercial":
        renderer = QgsRuleBasedRenderer.convertFromRenderer(renderer)
        null_symbol = QgsFillSymbol.createSimple(
            {"color": "#dedede", "outline_style": "no"}
        )
        renderer.rootRule().appendChild(
            QgsRuleBasedRenderer.Rule(
                null_symbol,
                filterExp=f'"{args.field}" IS NULL',
                label="No usable movement-speed weight",
            )
        )
    grid.setRenderer(renderer)
    for layer, color in ((masks, "0,90,210,255"), (vsr, "230,100,0,255")):
        layer.renderer().setSymbol(
            QgsFillSymbol.createSimple(
                {
                    "style": "no",
                    "outline_color": color,
                    "outline_width": "0.65",
                }
            )
        )
    settings = QgsMapSettings()
    settings.setLayers([vsr, masks, grid])
    settings.setDestinationCrs(grid.crs())
    settings.setOutputSize(QSize(1800, 1200))
    settings.setBackgroundColor(QColor("white"))
    transform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"), grid.crs(), project
    )
    views = {
        "full-context": (-122, 32, -117, 35),
        "shipping-corridors": (-120.1, 32.5, -117.1, 34.4),
        "north-edge": (-121.4, 34.3, -119.8, 35.1),
        "south-edge": (-119, 31.95, -117.1, 32.8),
    }
    args.output_dir.mkdir(parents=True)
    images = {}
    for name, bounds in views.items():
        settings.setExtent(transform.transformBoundingBox(QgsRectangle(*bounds)))
        job = QgsMapRendererSequentialJob(settings)
        job.start()
        job.waitForFinished()
        output = args.output_dir / f"{name}.png"
        if not job.renderedImage().save(str(output), "PNG"):
            raise RuntimeError("image save failed")
        images[name] = {"path": str(output.resolve()), "sha256": checksum(output)}
    report = {
        "grid_sha256": args.sha256,
        "qgis_version": Qgis.QGIS_VERSION,
        "rendered_at_utc": datetime.now(UTC).isoformat(),
        "crs": grid.crs().authid(),
        "features": grid.featureCount(),
        "invalid_geometry_count": invalid,
        "classification_breaks": breaks,
        "rendered_field": args.field,
        "units": "km" if args.field == "vessel_km_all_commercial" else "knots",
        "images": images,
        "visual_inspection_status": "not_completed_by_rendering",
        "context": "Blue receiver domain, orange VSR; not coverage evidence.",
    }
    (args.output_dir / "render-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    project.clear()
    app.exitQgis()


if __name__ == "__main__":
    main()
