"""Inspect an exact checksum-bound whale display export in QGIS.

Opens the published GeoJSON directly through OGR — not a converted copy —
verifies its identity against the sanitized export manifest, checks CRS,
counts, geometry and values against what the manifest declares, and renders
views for separate visual review. Rendering an image is not itself visual
verification; a person still has to look at the renders and record the result.

Run using QGIS's python-qgis.bat with QT_QPA_PLATFORM=offscreen.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from osgeo import gdal
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
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
from qgis.PyQt.QtGui import QColor

# Mirrors web/lib/whale-source.ts: equal 0.001 animals/km2 classes with an open
# lowest and highest class, on the same purple ramp, so the QGIS view and the
# browser view are directly comparable.
CLASSES = (
    (0.0, 0.002, "under 0.002", "231,212,238,191"),
    (0.002, 0.003, "0.002 to 0.003", "195,154,214,191"),
    (0.003, 0.004, "0.003 to 0.004", "156,102,187,199"),
    (0.004, 0.005, "0.004 to 0.005", "116,57,155,204"),
    (0.005, 1.0, "0.005 and above", "75,29,110,209"),
)

# Views chosen to expose what a table cannot: wrong location or axis order,
# misalignment with the source model, boundary clipping, and coastline gaps.
VIEWS = {
    "full-extent": None,
    "northern-boundary": (-121.6, 34.2, -119.0, 35.1),
    "southern-boundary": (-119.5, 31.9, -117.0, 32.9),
    "coast-and-islands": (-120.6, 33.2, -117.8, 34.6),
    "grid-detail": (-118.6, 33.4, -117.9, 33.9),
}

VALUE_FIELD = "modeled_density_animals_per_km2"


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect_features(layer):
    densities = []
    cell_ids = []
    invalid = []
    empty = []
    types = set()
    parts = 0
    rings = 0
    vertices = 0
    for feature in layer.getFeatures():
        geometry = feature.geometry()
        if geometry.isEmpty():
            empty.append(feature["cell_id"])
            continue
        if not geometry.isGeosValid():
            invalid.append(feature["cell_id"])
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
            for ring in polygon:
                vertices += len(ring)
        densities.append(feature[VALUE_FIELD])
        cell_ids.append(feature["cell_id"])
    return {
        "densities": densities,
        "cell_ids": cell_ids,
        "invalid": invalid,
        "empty": empty,
        "types": sorted(types),
        "polygon_parts": parts,
        "interior_rings": rings,
        "ring_vertices": vertices,
    }


def classify(layer):
    ranges = []
    for lower, upper, label, colour in CLASSES:
        symbol = QgsFillSymbol.createSimple({"color": colour, "outline_style": "no"})
        ranges.append(QgsRendererRange(lower, upper, symbol, label))
    layer.setRenderer(QgsGraduatedSymbolRenderer(VALUE_FIELD, ranges))


def render(layer, output_dir):
    renders = {}
    extent = layer.extent()
    for name, window in VIEWS.items():
        settings = QgsMapSettings()
        settings.setLayers([layer])
        settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        settings.setExtent(extent if window is None else QgsRectangle(*window))
        settings.setOutputSize(QSize(2200, 1400))
        settings.setBackgroundColor(QColor("white"))
        job = QgsMapRendererSequentialJob(settings)
        job.start()
        job.waitForFinished()
        output = output_dir / f"{name}.png"
        job.renderedImage().save(str(output), "PNG")
        renders[name] = {"path": output.name, "sha256": checksum(output)}
    return renders


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    interim = (Path(__file__).resolve().parents[2] / "data" / "interim").resolve()
    if not args.output_dir.resolve().is_relative_to(interim):
        raise ValueError("inspection requires an ignored interim output directory")
    if args.output_dir.exists():
        raise ValueError("inspection requires a fresh output directory")

    export_sha256 = checksum(args.export)
    if export_sha256 != args.sha256:
        raise ValueError("export checksum mismatch")
    manifest_path = args.export.with_name(args.export.name + ".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["output"]["sha256"] != export_sha256:
        raise ValueError("export manifest records a different output checksum")

    application = QgsApplication([], False)
    application.initQgis()
    layer = QgsVectorLayer(str(args.export), "whale display export", "ogr")
    if not layer.isValid():
        raise ValueError(f"QGIS could not open the export: {args.export}")
    QgsProject.instance().addMapLayer(layer)

    measured = inspect_features(layer)
    classify(layer)
    args.output_dir.mkdir(parents=True)
    renders = render(layer, args.output_dir)
    extent = layer.extent()
    declared = manifest["output"]

    counts = {}
    for lower, upper, label, _colour in CLASSES:
        last = label == CLASSES[-1][2]
        counts[label] = sum(
            1
            for value in measured["densities"]
            if value >= lower and (value <= upper if last else value < upper)
        )

    report = {
        "inspected_file": args.export.name,
        "inspected_sha256": export_sha256,
        "manifest_sha256": checksum(manifest_path),
        "qgis_version": Qgis.QGIS_VERSION,
        "gdal_version": gdal.VersionInfo("RELEASE_NAME"),
        "layer": {
            "valid": layer.isValid(),
            "provider": layer.dataProvider().name(),
            "crs": layer.crs().authid(),
            "crs_is_geographic": layer.crs().isGeographic(),
            "feature_count": layer.featureCount(),
            "fields": [field.name() for field in layer.fields()],
            "extent": [
                extent.xMinimum(),
                extent.yMinimum(),
                extent.xMaximum(),
                extent.yMaximum(),
            ],
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
            "unique_cell_ids": len(set(measured["cell_ids"])),
            "density_min": min(measured["densities"]),
            "density_max": max(measured["densities"]),
        },
        "agrees_with_manifest": {
            "feature_count": layer.featureCount() == declared["feature_count"],
            "polygon_parts": (
                measured["polygon_parts"] == declared["polygon_part_count"]
            ),
            "interior_rings": (
                measured["interior_rings"] == declared["interior_ring_count"]
            ),
            "ring_vertices": measured["ring_vertices"] == declared["coordinate_count"],
            "density_min": (
                min(measured["densities"])
                == declared["modeled_density_animals_per_km2_min"]
            ),
            "density_max": (
                max(measured["densities"])
                == declared["modeled_density_animals_per_km2_max"]
            ),
        },
        "classification": [
            {"min": lower, "max": upper, "label": label, "rgba": colour}
            for lower, upper, label, colour in CLASSES
        ],
        "class_counts": counts,
        "renders": renders,
        "visual_review": "not_performed_by_this_script",
    }
    json.dump(report, sys.stdout, indent=2)
    print()
    application.exitQgis()


main()
