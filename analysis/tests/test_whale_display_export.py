"""Known-answer tests for the deterministic public-display whale export.

Every fixture is built here, so the correct answer is known by construction. No
test reads a generated project artifact, and none of them needs the ignored
local data root.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest
import shapely
from shapely.geometry import MultiPolygon, Polygon, box

from whale_display_fixtures import (
    BASE_X,
    BASE_Y,
    CELL_SIZE_M,
    CENTRAL_MERIDIAN_LONGITUDE,
    _cell,
    _prepare,
    _table,
    _write_source,
)
from whale_vessel_analysis.spatial_grid import GEOMETRY_COLUMN
from whale_vessel_analysis.whale_display_export import (
    DISPLAY_CRS,
    GEOJSON_SUFFIX,
    MANIFEST_SUFFIX,
    PUBLIC_FIELDS,
    SOURCE_CRS,
    SOURCE_SCHEMA,
    WHALE_DISPLAY_EXPORT_CONTRACT,
    WHALE_DISPLAY_EXPORT_MANIFEST_CONTRACT,
    WITHHELD_FIELDS,
    DisplayExport,
    WhaleDisplayExportGeometryError,
    WhaleDisplayExportInputError,
    WhaleDisplayExportOutputError,
    build_export,
    build_manifest,
    load_source,
    validate_output_target,
    write_display_export,
)
from whale_vessel_analysis.whale_grid import (
    LINEAGE_SUFFIX,
    WHALE_GRID_CONTRACT,
)


def _signed_area(ring: Sequence[Sequence[float]]) -> float:
    total = 0.0
    for (x0, y0), (x1, y1) in itertools.pairwise(ring):
        total += x0 * y1 - x1 * y0
    return total / 2.0


def _decode(export: DisplayExport) -> dict[str, object]:
    return json.loads(export.geojson.decode("utf-8"))


# --------------------------------------------------------------------------
# Transformation, geometry, and value preservation
# --------------------------------------------------------------------------


def test_transforms_to_wgs84_with_longitude_latitude_axis_order(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    export = build_export(load_source(source_path, expected_sha256=digest))

    ring = _decode(export)["features"][0]["geometry"]["coordinates"][0]
    longitudes = [position[0] for position in ring]
    latitudes = [position[1] for position in ring]

    # The cell's western edge sits on EPSG:3310's own central meridian, so it
    # must come back as exactly 120 degrees west. Latitude and longitude cannot
    # be swapped without this failing loudly.
    assert min(longitudes) == pytest.approx(CENTRAL_MERIDIAN_LONGITUDE, abs=1e-9)
    assert max(longitudes) > CENTRAL_MERIDIAN_LONGITUDE
    assert all(32.0 < value < 35.0 for value in latitudes)
    assert all(-122.0 < value < -117.0 for value in longitudes)


def test_eastward_and_northward_cells_move_east_and_north(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0), _cell(0, 1), _cell(1, 0)])
    features = _decode(build_export(load_source(source_path, expected_sha256=digest)))[
        "features"
    ]
    centroids = [
        shapely.geometry.shape(feature["geometry"]).centroid for feature in features
    ]
    origin, east, north = centroids
    assert east.x > origin.x
    assert north.y > origin.y
    assert east.y == pytest.approx(origin.y, abs=1e-3)
    assert north.x == pytest.approx(origin.x, abs=1e-3)


def test_preserves_a_polygon_with_a_hole_and_orients_rings_for_rfc_7946(
    tmp_path: Path,
) -> None:
    outer = box(BASE_X, BASE_Y, BASE_X + CELL_SIZE_M, BASE_Y + CELL_SIZE_M)
    hole = box(BASE_X + 1_000, BASE_Y + 1_000, BASE_X + 2_000, BASE_Y + 2_000)
    with_hole = outer.difference(hole)
    assert len(with_hole.interiors) == 1

    source_path, digest = _prepare(tmp_path, [_cell(0, 0, geometry=with_hole)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    geometry = _decode(export)["features"][0]["geometry"]

    assert geometry["type"] == "Polygon"
    assert len(geometry["coordinates"]) == 2
    exterior, interior = geometry["coordinates"]
    # RFC 7946 section 3.1.6: exterior rings wind counterclockwise (positive
    # signed area) and holes wind clockwise (negative signed area).
    assert _signed_area(exterior) > 0
    assert _signed_area(interior) < 0
    assert exterior[0] == exterior[-1]
    assert interior[0] == interior[-1]
    assert export.diagnostics.interior_ring_count == 1
    assert export.diagnostics.polygon_part_count == 1


def test_preserves_multipolygon_parts(tmp_path: Path) -> None:
    parts = MultiPolygon(
        [
            box(BASE_X, BASE_Y, BASE_X + 1_000, BASE_Y + 1_000),
            box(BASE_X + 3_000, BASE_Y + 3_000, BASE_X + 4_000, BASE_Y + 4_000),
        ]
    )
    source_path, digest = _prepare(tmp_path, [_cell(0, 0, geometry=parts)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    geometry = _decode(export)["features"][0]["geometry"]

    assert geometry["type"] == "MultiPolygon"
    assert len(geometry["coordinates"]) == 2
    assert export.diagnostics.polygon_part_count == 2
    assert export.diagnostics.geometry_types == ("MultiPolygon",)


def test_publishes_the_documented_fields_and_no_others(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0, density=0.00123456789)])
    feature = _decode(build_export(load_source(source_path, expected_sha256=digest)))[
        "features"
    ][0]

    assert set(feature["properties"]) == {name for name, _unit, _why in PUBLIC_FIELDS}
    published = {name for name, _unit, _why in PUBLIC_FIELDS}
    withheld = {name for name, _reason in WITHHELD_FIELDS}
    assert published.isdisjoint(withheld)
    # Every source column is either published or explicitly justified as withheld.
    assert {name for name, _kind in SOURCE_SCHEMA} - {GEOMETRY_COLUMN} == (
        published | withheld
    ) - {"object_id"}


def test_preserves_analytical_values_exactly(tmp_path: Path) -> None:
    density = 0.0076482470000000004
    water = 24.999999999999996
    source_path, digest = _prepare(
        tmp_path,
        [_cell(0, 0, density=density, water_area_km2=water, coverage=0.9999999999)],
    )
    properties = _decode(
        build_export(load_source(source_path, expected_sha256=digest))
    )["features"][0]["properties"]

    assert properties["modeled_density_animals_per_km2"] == density
    assert properties["water_area_km2"] == water
    assert properties["modeled_abundance_allocation_animals"] == density * water
    assert properties["source_coverage_fraction"] == 0.9999999999
    assert properties["coverage_status"] == "complete"


def test_feature_identifiers_are_stable_and_deterministic(tmp_path: Path) -> None:
    cells = [_cell(0, 0), _cell(0, 1), _cell(1, 0), _cell(1, 1)]
    source_path, digest = _prepare(tmp_path, cells)
    features = _decode(build_export(load_source(source_path, expected_sha256=digest)))[
        "features"
    ]

    assert [feature["id"] for feature in features] == [
        "r000_c000",
        "r000_c001",
        "r001_c000",
        "r001_c001",
    ]
    assert [feature["properties"]["object_id"] for feature in features] == [1, 2, 3, 4]
    assert [feature["properties"]["cell_id"] for feature in features] == [
        feature["id"] for feature in features
    ]


def test_repeated_exports_of_the_same_source_are_byte_identical(
    tmp_path: Path,
) -> None:
    cells = [_cell(0, 0), _cell(0, 1), _cell(1, 0)]
    first_path, first_digest = _prepare(tmp_path / "a", cells)
    second_path, second_digest = _prepare(tmp_path / "b", cells)

    first = build_export(load_source(first_path, expected_sha256=first_digest))
    second = build_export(load_source(second_path, expected_sha256=second_digest))

    assert first.geojson == second.geojson
    assert first.sha256 == second.sha256


def test_collection_bbox_matches_the_transformed_extent(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0), _cell(1, 1)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    collection = _decode(export)

    bounds = shapely.total_bounds(
        [shapely.geometry.shape(f["geometry"]) for f in collection["features"]]
    ).tolist()
    assert collection["bbox"] == pytest.approx(bounds)
    assert list(export.diagnostics.bounds) == pytest.approx(bounds)


def test_diagnostics_report_the_transformed_totals(tmp_path: Path) -> None:
    source_path, digest = _prepare(
        tmp_path,
        [_cell(0, 0, density=0.001), _cell(0, 1, density=0.003)],
    )
    diagnostics = build_export(
        load_source(source_path, expected_sha256=digest)
    ).diagnostics

    assert diagnostics.feature_count == 2
    assert diagnostics.unique_cell_count == 2
    assert diagnostics.density_min == 0.001
    assert diagnostics.density_max == 0.003
    assert diagnostics.abundance_total == pytest.approx(0.001 * 25 + 0.003 * 25)
    assert diagnostics.water_area_km2_total == pytest.approx(50.0)
    assert diagnostics.max_vertex_roundtrip_metres < 1e-6
    assert diagnostics.transformation_definition
    assert "unitconvert" in diagnostics.transformation_definition


def test_rejects_geometry_that_leaves_the_configured_map_extent(
    tmp_path: Path,
) -> None:
    far_north = box(BASE_X, -100_000, BASE_X + CELL_SIZE_M, -95_000)
    source_path, digest = _prepare(tmp_path, [_cell(0, 0, geometry=far_north)])
    with pytest.raises(WhaleDisplayExportGeometryError, match="configured map extent"):
        build_export(load_source(source_path, expected_sha256=digest))


# --------------------------------------------------------------------------
# Source contract enforcement
# --------------------------------------------------------------------------


def test_rejects_a_source_whose_checksum_does_not_match(tmp_path: Path) -> None:
    source_path, _digest = _prepare(tmp_path, [_cell(0, 0)])
    with pytest.raises(WhaleDisplayExportInputError, match="checksum mismatch"):
        load_source(source_path, expected_sha256="f" * 64)


def test_rejects_a_missing_source(tmp_path: Path) -> None:
    with pytest.raises(WhaleDisplayExportInputError, match="does not exist"):
        load_source(tmp_path / "absent.parquet")


def test_rejects_a_non_parquet_source(tmp_path: Path) -> None:
    path = tmp_path / "whale.geojson"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(WhaleDisplayExportInputError, match=r"must be a \.parquet file"):
        load_source(path)


def test_rejects_a_different_dataset_contract(tmp_path: Path) -> None:
    source_path, digest = _prepare(
        tmp_path, [_cell(0, 0)], contract="vessel_activity_grid_v1"
    )
    with pytest.raises(WhaleDisplayExportInputError, match="source contract must be"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_different_schema_version(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)], schema_version=2)
    with pytest.raises(
        WhaleDisplayExportInputError, match="source schema version must be"
    ):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_source_declaring_a_different_analysis_crs(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)], analysis_crs="EPSG:4326")
    with pytest.raises(WhaleDisplayExportInputError, match="analysis CRS must be"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_geometry_stored_in_a_different_crs(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)], geometry_crs="EPSG:3857")
    with pytest.raises(WhaleDisplayExportInputError, match="geometry CRS must be"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_non_wkb_geometry_encoding(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)], encoding="WKT")
    with pytest.raises(WhaleDisplayExportInputError, match="encoding must be WKB"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_source_without_geoparquet_metadata(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)], omit_geo_metadata=True)
    with pytest.raises(WhaleDisplayExportInputError, match="GeoParquet metadata"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_missing_source_column(tmp_path: Path) -> None:
    source_path, digest = _prepare(
        tmp_path, [_cell(0, 0)], drop_column="source_coverage_fraction"
    )
    with pytest.raises(WhaleDisplayExportInputError, match="source columns must be"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_retyped_source_column(tmp_path: Path) -> None:
    source_path, digest = _prepare(
        tmp_path, [_cell(0, 0)], retype=("row_index", pa.int32())
    )
    with pytest.raises(WhaleDisplayExportInputError, match="column types do not match"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_nullable_source_columns(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)], nullable=True)
    with pytest.raises(WhaleDisplayExportInputError, match="non-nullable"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_duplicate_cell_identifiers(tmp_path: Path) -> None:
    duplicate = _cell(0, 0)
    source_path, digest = _prepare(tmp_path, [_cell(0, 0), duplicate])
    with pytest.raises(WhaleDisplayExportInputError, match="not unique"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_cell_id_that_disagrees_with_its_row_and_column(
    tmp_path: Path,
) -> None:
    cell = _cell(0, 1)
    cell["cell_id"] = "r009_c009"
    source_path, digest = _prepare(tmp_path, [_cell(0, 0), cell])
    with pytest.raises(WhaleDisplayExportInputError, match="does not match its row"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_rows_that_are_out_of_contract_order(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(1, 0), _cell(0, 0)])
    with pytest.raises(WhaleDisplayExportInputError, match="contract order"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_an_empty_source(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [])
    with pytest.raises(WhaleDisplayExportInputError, match="contains no rows"):
        load_source(source_path, expected_sha256=digest)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_rejects_non_finite_density(tmp_path: Path, value: float) -> None:
    cell = _cell(0, 0)
    cell["modeled_density_animals_per_km2"] = value
    source_path, digest = _prepare(tmp_path, [cell])
    with pytest.raises(WhaleDisplayExportInputError, match="is not finite"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_negative_density(tmp_path: Path) -> None:
    cell = _cell(0, 0)
    cell["modeled_density_animals_per_km2"] = -1e-9
    source_path, digest = _prepare(tmp_path, [cell])
    with pytest.raises(WhaleDisplayExportInputError, match="is negative"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_zero_water_area(tmp_path: Path) -> None:
    cell = _cell(0, 0)
    cell["water_area_km2"] = 0.0
    source_path, digest = _prepare(tmp_path, [cell])
    with pytest.raises(WhaleDisplayExportInputError, match="must be positive"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_coverage_fraction_outside_zero_to_one(tmp_path: Path) -> None:
    cell = _cell(0, 0)
    cell["source_coverage_fraction"] = 1.5
    source_path, digest = _prepare(tmp_path, [cell])
    with pytest.raises(WhaleDisplayExportInputError, match=r"outside \[0,1\]"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_an_unsupported_geometry_type(tmp_path: Path) -> None:
    line = shapely.geometry.LineString(
        [(BASE_X, BASE_Y), (BASE_X + CELL_SIZE_M, BASE_Y)]
    )
    source_path, digest = _prepare(tmp_path, [_cell(0, 0, geometry=line)])  # type: ignore[arg-type]
    with pytest.raises(WhaleDisplayExportInputError, match="only Polygon"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_invalid_source_geometry(tmp_path: Path) -> None:
    bowtie = Polygon(
        [
            (BASE_X, BASE_Y),
            (BASE_X + CELL_SIZE_M, BASE_Y + CELL_SIZE_M),
            (BASE_X + CELL_SIZE_M, BASE_Y),
            (BASE_X, BASE_Y + CELL_SIZE_M),
        ]
    )
    source_path, digest = _prepare(tmp_path, [_cell(0, 0, geometry=bowtie)])
    with pytest.raises(WhaleDisplayExportInputError, match="is invalid"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_empty_source_geometry(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0, geometry=Polygon())])
    with pytest.raises(WhaleDisplayExportInputError, match="is empty"):
        load_source(source_path, expected_sha256=digest)


# --------------------------------------------------------------------------
# Generation lineage handling
# --------------------------------------------------------------------------


def test_reads_the_run_id_from_a_matching_generation_lineage(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    source = load_source(source_path, expected_sha256=digest)
    assert source.run_id == "whale-grid-testfixture0000000000"
    assert source.lineage_sha256 is not None


def test_rejects_a_generation_lineage_recording_a_different_output(
    tmp_path: Path,
) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    sidecar = source_path.with_suffix(source_path.suffix + LINEAGE_SUFFIX)
    document = json.loads(sidecar.read_text(encoding="utf-8"))
    document["output"]["sha256"] = "b" * 64
    sidecar.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    with pytest.raises(WhaleDisplayExportInputError, match="different output checksum"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_generation_lineage_with_a_foreign_contract(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    sidecar = source_path.with_suffix(source_path.suffix + LINEAGE_SUFFIX)
    document = json.loads(sidecar.read_text(encoding="utf-8"))
    document["contract"] = "some_other_lineage_v1"
    sidecar.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    with pytest.raises(WhaleDisplayExportInputError, match="contract must be"):
        load_source(source_path, expected_sha256=digest)


def test_accepts_a_source_without_a_generation_lineage_sidecar(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source" / "whale-grid.parquet"
    digest = _write_source(source_path, _table([_cell(0, 0)]), lineage=False)
    source = load_source(source_path, expected_sha256=digest)
    assert source.run_id is None
    assert source.lineage_sha256 is None


# --------------------------------------------------------------------------
# Manifest content and sanitization
# --------------------------------------------------------------------------


def test_manifest_records_source_identity_units_and_declared_parameters(
    tmp_path: Path,
) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    manifest = build_manifest(
        export,
        output_name="blue-whale-density.geojson",
        exported_at=datetime(2026, 9, 6, tzinfo=UTC),
    )

    assert manifest["contract"] == WHALE_DISPLAY_EXPORT_MANIFEST_CONTRACT
    assert manifest["dataset_contract"] == WHALE_DISPLAY_EXPORT_CONTRACT
    assert manifest["exported_at"] == "2026-09-06T00:00:00Z"
    assert manifest["source"]["sha256"] == digest
    assert manifest["source"]["contract"] == WHALE_GRID_CONTRACT
    assert manifest["transformation"]["display_crs"] == DISPLAY_CRS
    assert manifest["transformation"]["source_crs"] == SOURCE_CRS
    assert manifest["transformation"]["always_xy"] is True
    assert manifest["transformation"]["geometry_simplification"] == "not_performed"
    assert manifest["transformation"]["coordinate_rounding"] == "not_performed"
    assert manifest["output"]["sha256"] == export.sha256
    assert manifest["output"]["bytes"] == len(export.geojson)
    assert manifest["output"]["media_type"] == "application/geo+json"
    units = {field["name"]: field["unit"] for field in manifest["fields"]["published"]}
    assert units["modeled_density_animals_per_km2"] == "animals/km\u00b2"
    assert units["water_area_km2"] == "km\u00b2"


def test_manifest_carries_no_local_path_or_private_lineage(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    serialized = json.dumps(
        build_manifest(
            export,
            output_name="blue-whale-density.geojson",
            exported_at=datetime(2026, 9, 6, tzinfo=UTC),
        )
    )

    assert str(tmp_path) not in serialized
    assert "whale-grid.parquet" not in serialized
    assert r"C:\\private\\raw" not in serialized
    assert "private" not in serialized.lower()
    for term in ("api_key", "apikey", "token", "password", "secret"):
        assert term not in serialized.lower()
    # The VSR boundary is never part of a project-published artifact.
    for term in ("vsr", "whaleatlas", "fid = 126", "services5.arcgis.com"):
        assert term not in serialized.lower()


def test_manifest_requires_a_utc_export_timestamp(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    with pytest.raises(WhaleDisplayExportOutputError, match="timezone-aware UTC"):
        build_manifest(
            export,
            output_name="blue-whale-density.geojson",
            exported_at=datetime(2026, 9, 6),  # deliberately naive
        )


def test_exported_geojson_contains_no_withheld_field_names(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    text = export.geojson.decode("utf-8")
    for name, _reason in WITHHELD_FIELDS:
        assert f'"{name}"' not in text


# --------------------------------------------------------------------------
# Output destinations and atomic publication
# --------------------------------------------------------------------------


def test_writes_the_geojson_and_manifest_together(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0), _cell(0, 1)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    output = tmp_path / "out" / "blue-whale-density.geojson"

    result = write_display_export(export, output, approved_roots=[tmp_path])

    assert output.read_bytes() == export.geojson
    assert result.output_sha256 == export.sha256
    assert result.output_bytes == len(export.geojson)
    manifest_path = output.with_name(output.name + MANIFEST_SUFFIX)
    assert result.manifest_path == manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["output"]["sha256"] == export.sha256
    assert manifest["output"]["name"] == "blue-whale-density.geojson"
    assert (
        hashlib.sha256(manifest_path.read_bytes()).hexdigest() == result.manifest_sha256
    )


def test_refuses_to_replace_an_existing_export_without_authorization(
    tmp_path: Path,
) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    output = tmp_path / "out" / "blue-whale-density.geojson"
    write_display_export(export, output, approved_roots=[tmp_path])

    with pytest.raises(WhaleDisplayExportOutputError, match="already exists"):
        write_display_export(export, output, approved_roots=[tmp_path])


def test_authorized_overwrite_replaces_both_files(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    output = tmp_path / "out" / "blue-whale-density.geojson"
    write_display_export(
        export,
        output,
        exported_at=datetime(2026, 9, 1, tzinfo=UTC),
        approved_roots=[tmp_path],
    )

    result = write_display_export(
        export,
        output,
        exported_at=datetime(2026, 9, 2, tzinfo=UTC),
        overwrite=True,
        approved_roots=[tmp_path],
    )

    assert output.read_bytes() == export.geojson
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["exported_at"] == "2026-09-02T00:00:00Z"
    leftovers = [item.name for item in output.parent.iterdir()]
    assert sorted(leftovers) == [
        "blue-whale-density.geojson",
        "blue-whale-density.geojson" + MANIFEST_SUFFIX,
    ]


def test_refuses_an_output_that_is_not_geojson(tmp_path: Path) -> None:
    with pytest.raises(WhaleDisplayExportOutputError, match=GEOJSON_SUFFIX):
        validate_output_target(tmp_path / "whale.json")


def test_refuses_an_output_under_the_raw_data_root() -> None:
    project_root = Path(__file__).resolve().parents[2]
    with pytest.raises(WhaleDisplayExportOutputError, match="raw data"):
        validate_output_target(project_root / "data" / "raw" / "whale.geojson")


def test_refuses_a_tracked_repository_destination() -> None:
    project_root = Path(__file__).resolve().parents[2]
    with pytest.raises(WhaleDisplayExportOutputError, match="must be under one of"):
        validate_output_target(project_root / "web" / "public" / "whale.geojson")
    with pytest.raises(WhaleDisplayExportOutputError, match="must be under one of"):
        validate_output_target(project_root / "docs" / "whale.geojson")


def test_accepts_the_ignored_generated_destinations() -> None:
    project_root = Path(__file__).resolve().parents[2]
    validate_output_target(project_root / "data" / "derived" / "m5" / "whale.geojson")
    validate_output_target(project_root / "data" / "interim" / "m5" / "whale.geojson")
    validate_output_target(project_root / "web" / "public" / "layers" / "whale.geojson")


def test_a_failed_manifest_write_leaves_an_existing_export_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    output = tmp_path / "out" / "blue-whale-density.geojson"
    first = write_display_export(
        export,
        output,
        exported_at=datetime(2026, 9, 1, tzinfo=UTC),
        approved_roots=[tmp_path],
    )
    original = output.read_bytes()
    original_manifest = first.manifest_path.read_bytes()

    real_replace = __import__("os").replace
    calls = {"count": 0}

    def failing_replace(source: object, destination: object) -> None:
        calls["count"] += 1
        # Fail while committing the manifest, after the GeoJSON has moved.
        if calls["count"] == 4:
            raise OSError("simulated failure")
        real_replace(source, destination)  # type: ignore[arg-type]

    monkeypatch.setattr(
        "whale_vessel_analysis.whale_display_export.os.replace", failing_replace
    )
    with pytest.raises(WhaleDisplayExportOutputError, match="could not write"):
        write_display_export(
            export,
            output,
            exported_at=datetime(2026, 9, 2, tzinfo=UTC),
            overwrite=True,
            approved_roots=[tmp_path],
        )

    assert output.read_bytes() == original
    assert first.manifest_path.read_bytes() == original_manifest
    assert sorted(item.name for item in output.parent.iterdir()) == [
        "blue-whale-density.geojson",
        "blue-whale-density.geojson" + MANIFEST_SUFFIX,
    ]
