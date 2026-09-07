"""Inspect exact vessel/domain display exports directly in QGIS.

The script checksum-gates both GeoJSON files and manifests, validates their
declared CRS, geometry and values, and renders several views for human review.
It never converts or republishes either artifact. Run with QGIS's
``python-qgis.bat`` and ``QT_QPA_PLATFORM=offscreen``.
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
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor

VALUE_FIELD = "vessel_km_per_water_km2_all_commercial"
CLASSES = (
    (0.0, 0.0, "zero retained movement", "214,220,216,179"),
    (0.0, 1.0, "over 0 to 1", "218,240,214,194"),
    (1.0, 5.0, "over 1 to 5", "166,217,160,199"),
    (5.0, 20.0, "over 5 to 20", "90,174,108,204"),
    (20.0, 100.0, "over 20 to 100", "35,139,69,209"),
    (100.0, 10000.0, "over 100", "0,88,36,219"),
)
VIEWS = {
    "full-extent": None,
    "northern-boundary": (-121.9, 34.1, -119.0, 35.05),
    "southern-boundary": (-119.8, 32.0, -117.0, 33.0),
    "coast-and-islands": (-120.7, 33.1, -117.7, 34.7),
    "boundary-detail": (-119.5, 33.6, -118.5, 34.4),
}


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_bound_layer(path, expected_sha256, title):
    actual = checksum(path)
    if actual != expected_sha256:
        raise ValueError(f"{title} checksum mismatch")
    manifest_path = path.with_name(path.name + ".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["output"]["sha256"] != actual:
        raise ValueError(f"{title} manifest records a different checksum")
    layer = QgsVectorLayer(str(path), title, "ogr")
    if not layer.isValid():
        raise ValueError(f"QGIS could not open {title}")
    if layer.crs().authid() != "EPSG:4326" or not layer.crs().isGeographic():
        raise ValueError(f"{title} is not geographic EPSG:4326")
    return layer, manifest, manifest_path


def geometry_metrics(layer, id_field):
    invalid = []
    empty = []
    types = set()
    parts = rings = vertices = 0
    for feature in layer.getFeatures():
        geometry = feature.geometry()
        if geometry.isEmpty():
            empty.append(feature[id_field])
            continue
        if not geometry.isGeosValid():
            invalid.append(feature[id_field])
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
    return {
        "wkb_types": sorted(types),
        "polygon_parts": parts,
        "interior_rings": rings,
        "ring_vertices": vertices,
        "empty": empty,
        "invalid": invalid,
    }


def symbolize(vessel, domain):
    ranges = []
    for lower, upper, label, colour in CLASSES:
        symbol = QgsFillSymbol.createSimple({"color": colour, "outline_style": "no"})
        ranges.append(QgsRendererRange(lower, upper, symbol, label))
    vessel.setRenderer(QgsGraduatedSymbolRenderer(VALUE_FIELD, ranges))
    domain_symbol = QgsFillSymbol.createSimple(
        {
            "color": "45,205,184,9",
            "outline_color": "45,205,184,250",
            "outline_width": "1.2",
            "outline_style": "dash",
        }
    )
    domain.setRenderer(QgsSingleSymbolRenderer(domain_symbol))


def render(vessel, domain, output_dir):
    renders = {}
    extent = domain.extent()
    for name, window in VIEWS.items():
        settings = QgsMapSettings()
        settings.setLayers([domain, vessel])
        settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        settings.setExtent(extent if window is None else QgsRectangle(*window))
        settings.setOutputSize(QSize(2200, 1400))
        settings.setBackgroundColor(QColor("#eef3f4"))
        job = QgsMapRendererSequentialJob(settings)
        job.start()
        job.waitForFinished()
        path = output_dir / f"{name}.png"
        job.renderedImage().save(str(path), "PNG")
        renders[name] = {"path": path.name, "sha256": checksum(path)}
    return renders


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vessel", type=Path, required=True)
    parser.add_argument("--vessel-sha256", required=True)
    parser.add_argument("--domain", type=Path, required=True)
    parser.add_argument("--domain-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    interim = (Path(__file__).resolve().parents[2] / "data" / "interim").resolve()
    if not args.output_dir.resolve().is_relative_to(interim):
        raise ValueError("inspection requires an ignored interim output directory")
    if args.output_dir.exists():
        raise ValueError("inspection requires a fresh output directory")

    application = QgsApplication([], False)
    application.initQgis()
    vessel, vessel_manifest, vessel_manifest_path = load_bound_layer(
        args.vessel, args.vessel_sha256, "commercial vessel activity"
    )
    domain, domain_manifest, domain_manifest_path = load_bound_layer(
        args.domain, args.domain_sha256, "accepted analytical domain"
    )
    QgsProject.instance().addMapLayers([vessel, domain])

    vessel_geometry = geometry_metrics(vessel, "cell_id")
    domain_geometry = geometry_metrics(domain, "domain_id")
    densities = [feature[VALUE_FIELD] for feature in vessel.getFeatures()]
    overlaps = [
        feature["analytical_domain_overlap"] for feature in vessel.getFeatures()
    ]
    displayed_area = sum(
        feature["analytical_domain_area_km2"] for feature in vessel.getFeatures()
    )
    domain_feature = next(domain.getFeatures())
    outside_domain = []
    domain_shape = domain_feature.geometry()
    for feature in vessel.getFeatures():
        difference = feature.geometry().difference(domain_shape)
        if not difference.isEmpty() and difference.area() > 1e-14:
            outside_domain.append(feature["cell_id"])

    symbolize(vessel, domain)
    args.output_dir.mkdir(parents=True)
    renders = render(vessel, domain, args.output_dir)
    declared_vessel = vessel_manifest["output"]
    declared_domain = domain_manifest["output"]
    report = {
        "qgis_version": Qgis.QGIS_VERSION,
        "gdal_version": gdal.VersionInfo("RELEASE_NAME"),
        "inputs": {
            "vessel": {
                "name": args.vessel.name,
                "sha256": checksum(args.vessel),
                "manifest_sha256": checksum(vessel_manifest_path),
            },
            "domain": {
                "name": args.domain.name,
                "sha256": checksum(args.domain),
                "manifest_sha256": checksum(domain_manifest_path),
            },
        },
        "vessel": {
            "crs": vessel.crs().authid(),
            "feature_count": vessel.featureCount(),
            "fields": [field.name() for field in vessel.fields()],
            "geometry": vessel_geometry,
            "density_min": min(densities),
            "density_max": max(densities),
            "zero_activity_count": sum(value == 0 for value in densities),
            "full_count": overlaps.count("full"),
            "partial_count": overlaps.count("partial"),
            "displayed_domain_area_km2": displayed_area,
            "features_outside_domain": outside_domain,
        },
        "domain": {
            "crs": domain.crs().authid(),
            "feature_count": domain.featureCount(),
            "fields": [field.name() for field in domain.fields()],
            "geometry": domain_geometry,
            "properties": {
                name: domain_feature[name]
                for name in (
                    "domain_id",
                    "qualification",
                    "distance_nautical_miles",
                    "distance_m",
                    "measured_from",
                    "included_water_area_km2",
                )
            },
        },
        "agrees_with_manifests": {
            "vessel_feature_count": vessel.featureCount()
            == declared_vessel["feature_count"],
            "vessel_parts": vessel_geometry["polygon_parts"]
            == declared_vessel["polygon_part_count"],
            "vessel_rings": vessel_geometry["interior_rings"]
            == declared_vessel["interior_ring_count"],
            "vessel_vertices": vessel_geometry["ring_vertices"]
            == declared_vessel["coordinate_count"],
            "domain_feature_count": domain.featureCount()
            == declared_domain["feature_count"],
            "domain_parts": domain_geometry["polygon_parts"]
            == declared_domain["polygon_part_count"],
            "domain_rings": domain_geometry["interior_rings"]
            == declared_domain["interior_ring_count"],
            "domain_vertices": domain_geometry["ring_vertices"]
            == declared_domain["coordinate_count"],
        },
        "classification": [
            {"min": lower, "max": upper, "label": label, "rgba": colour}
            for lower, upper, label, colour in CLASSES
        ],
        "renders": renders,
        "visual_review": "not_performed_by_this_script",
    }
    report_path = args.output_dir / "inspection-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    json.dump(
        {
            "report": report_path.name,
            "report_sha256": checksum(report_path),
            "vessel_feature_count": vessel.featureCount(),
            "domain_feature_count": domain.featureCount(),
        },
        sys.stdout,
        sort_keys=True,
    )
    print()
    application.exitQgis()


main()
