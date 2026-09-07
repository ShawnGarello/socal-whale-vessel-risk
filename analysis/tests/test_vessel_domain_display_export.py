"""Known-answer tests for vessel activity and analytical-domain display exports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapely
from pyproj import CRS

import whale_vessel_analysis.vessel_domain_display_export as export_module
from vessel_domain_display_fixtures import _write_table, prepare_sources, vessel_table
from whale_vessel_analysis.vessel_domain_display_export import (
    DOMAIN_OUTPUT_NAME,
    DOMAIN_SOURCE_CHECKSUM_FIELDS,
    MANIFEST_SUFFIX,
    VESSEL_OUTPUT_NAME,
    VESSEL_PUBLIC_FIELDS,
    ExportBundle,
    VesselDomainDisplayInputError,
    VesselDomainDisplayOutputError,
    build_domain_manifest,
    build_exports,
    build_vessel_manifest,
    load_domain_source,
    load_vessel_quality_source,
    load_vessel_source,
    write_export_bundle,
)


def _bundle(tmp_path: Path) -> ExportBundle:
    (
        vessel_path,
        vessel_sha,
        quality_path,
        quality_sha,
        domain_path,
        domain_sha,
        report_path,
        report_sha,
    ) = prepare_sources(tmp_path)
    vessel = load_vessel_source(vessel_path, expected_sha256=vessel_sha)
    quality = load_vessel_quality_source(
        quality_path, expected_sha256=quality_sha, vessel=vessel
    )
    domain = load_domain_source(
        domain_path,
        expected_sha256=domain_sha,
        report_path=report_path,
        expected_report_sha256=report_sha,
    )
    return build_exports(vessel, quality, domain)


def _decode(payload: bytes) -> dict[str, object]:
    return json.loads(payload.decode())


def test_known_answer_clips_partial_cells_and_preserves_values(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    collection = _decode(bundle.vessel.geojson)
    features = collection["features"]

    assert len(features) == 2
    assert [feature["id"] for feature in features] == ["r000_c000", "r000_c001"]
    first, partial = [feature["properties"] for feature in features]
    assert first["analytical_domain_overlap"] == "full"
    assert first["analytical_domain_fraction"] == 1.0
    assert first["vessel_km_all_commercial"] == 0.0
    assert partial["analytical_domain_overlap"] == "partial"
    assert partial["analytical_domain_fraction"] == pytest.approx(0.5)
    # The source-cell activity is descriptive and is never proportionally rescaled.
    assert partial["vessel_km_all_commercial"] == 25.0
    assert partial["vessel_km_per_water_km2_all_commercial"] == 1.0
    assert partial["analytical_domain_area_km2"] == pytest.approx(12.5)
    assert bundle.vessel.value_diagnostics == {
        "unique_cell_count": 2,
        "fully_inside_cell_count": 1,
        "partly_inside_cell_count": 1,
        "wholly_outside_cell_count": 2,
        "zero_activity_cell_count": 1,
        "positive_activity_cell_count": 1,
        "activity_density_min": 0.0,
        "activity_density_max": 1.0,
        "displayed_domain_area_km2": 37.5,
    }


def test_public_fields_exclude_speed_identity_and_grid_internals(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    properties = _decode(bundle.vessel.geojson)["features"][0]["properties"]
    assert set(properties) == {name for name, _unit, _meaning in VESSEL_PUBLIC_FIELDS}
    assert not any("speed" in name or "sog" in name for name in properties)
    assert not any("mmsi" in name for name in properties)
    assert "row_index" not in properties


def test_domain_semantics_and_crs_are_explicit(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    feature = _decode(bundle.domain.geojson)["features"][0]
    properties = feature["properties"]
    geometry = shapely.geometry.shape(feature["geometry"])

    assert feature["id"] == "receivers_50_nautical_miles"
    assert properties["distance_nautical_miles"] == 50
    assert properties["distance_m"] == 92_600
    assert properties["measured_from"] == "relevant_nais_reception_stations"
    assert "empirical_2024_coverage" not in properties
    assert properties["included_water_area_km2"] == 37.5
    manifest = build_domain_manifest(
        bundle, exported_at=datetime(2026, 9, 6, 12, tzinfo=UTC)
    )
    assert (
        manifest["reporting_contract"]["analytical_domain"]["empirical_2024_coverage"]
        is False
    )
    assert -122 < geometry.bounds[0] < -117
    assert 32 < geometry.bounds[1] < 35
    assert bundle.domain.diagnostics.max_vertex_roundtrip_metres < 1e-5


def test_repeated_exports_are_byte_identical(tmp_path: Path) -> None:
    first = _bundle(tmp_path / "first")
    second = _bundle(tmp_path / "second")
    assert first.vessel.geojson == second.vessel.geojson
    assert first.domain.geojson == second.domain.geojson
    assert first.vessel.sha256 == hashlib.sha256(first.vessel.geojson).hexdigest()
    assert first.domain.sha256 == hashlib.sha256(first.domain.geojson).hexdigest()


def test_manifests_are_sanitized_and_bind_both_sources(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    exported_at = datetime(2026, 9, 6, 12, tzinfo=UTC)
    documents = (
        build_vessel_manifest(bundle, exported_at=exported_at),
        build_domain_manifest(bundle, exported_at=exported_at),
    )
    serialized = json.dumps(documents, sort_keys=True)

    assert bundle.vessel_source.sha256 in serialized
    assert bundle.vessel_quality_source.sha256 in serialized
    assert bundle.domain_source.sha256 in serialized
    assert bundle.domain_source.report_sha256 in serialized
    assert bundle.vessel.sha256 in serialized
    assert bundle.domain.sha256 in serialized
    assert "C:\\" not in serialized
    assert "token" not in serialized.lower()
    assert "api_key" not in serialized.lower()
    assert "partitions" not in serialized
    assert "speed_role" in documents[0]["accepted_method"]
    accounting = documents[0]["processing_accounting"]
    assert accounting["candidate_segment_count"] == 10
    assert accounting["retained_segment_count"] == 8
    assert accounting["excluded_segment_count"] == 2
    assert accounting["primary_exclusion_counts"] == {
        "invalid_coordinate_transform": 0,
        "non_increasing_time": 0,
        "vessel_group_change": 0,
        "maximum_gap": 1,
        "implied_speed": 1,
    }
    assert accounting["all_commercial_distance_conservation"]["passed"] is True
    assert set(documents[1]["source"]["input_checksums"]) == set(
        DOMAIN_SOURCE_CHECKSUM_FIELDS
    )


def test_fixed_timestamp_manifests_are_deterministic(tmp_path: Path) -> None:
    exported_at = datetime(2026, 9, 6, 12, tzinfo=UTC)
    first = _bundle(tmp_path / "first")
    second = _bundle(tmp_path / "second")

    assert build_vessel_manifest(first, exported_at=exported_at) == (
        build_vessel_manifest(second, exported_at=exported_at)
    )
    assert build_domain_manifest(first, exported_at=exported_at) == (
        build_domain_manifest(second, exported_at=exported_at)
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("unsafe_evidence_id", "evidence id"),
        ("unexpected_source", "checksum fields"),
        ("disagreeing_grid", "grid checksum fields disagree"),
        ("invalid_cell_count", "non-negative integer"),
    ],
)
def test_rejects_unsanitized_or_invalid_domain_report_metadata(
    tmp_path: Path, mutation: str, message: str
) -> None:
    (
        vessel_path,
        vessel_sha,
        _quality_path,
        _quality_sha,
        domain_path,
        domain_sha,
        report_path,
        _report_sha,
    ) = prepare_sources(tmp_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if mutation == "unsafe_evidence_id":
        report["evidence_id"] = "domain-evidence-C:\\private\\artifact"
    elif mutation == "unexpected_source":
        report["sources"]["private_path"] = "c" * 64
    elif mutation == "disagreeing_grid":
        report["sources"]["grid_path_sha256"] = "c" * 64
    else:
        report["candidates"][0]["cells"]["wholly_outside"] = -1
    report_path.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    report_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()

    # The expected checksum is deliberately updated: sanitation is a contract
    # boundary, not something callers may bypass by identifying altered bytes.
    load_vessel_source(vessel_path, expected_sha256=vessel_sha)
    with pytest.raises(VesselDomainDisplayInputError, match=message):
        load_domain_source(
            domain_path,
            expected_sha256=domain_sha,
            report_path=report_path,
            expected_report_sha256=report_sha,
        )


def test_rejects_domain_geometry_with_the_wrong_crs(tmp_path: Path) -> None:
    (
        _vessel,
        _vessel_sha,
        _quality_path,
        _quality_sha,
        domain_path,
        _domain_sha,
        report_path,
        _report_sha,
    ) = prepare_sources(tmp_path)
    table = pq.read_table(domain_path)
    metadata = dict(table.schema.metadata or {})
    geo = json.loads(metadata[b"geo"])
    geo["columns"]["geometry"]["crs"] = CRS.from_epsg(4326).to_json_dict()
    metadata[b"geo"] = json.dumps(geo, sort_keys=True, separators=(",", ":")).encode()
    changed = table.replace_schema_metadata(metadata)
    changed_sha = _write_table(domain_path, changed)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["mask_output"]["sha256"] = changed_sha
    report_path.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    report_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()

    with pytest.raises(VesselDomainDisplayInputError, match="geometry CRS"):
        load_domain_source(
            domain_path,
            expected_sha256=changed_sha,
            report_path=report_path,
            expected_report_sha256=report_sha,
        )


@pytest.mark.parametrize("which", ["vessel", "quality", "domain", "report"])
def test_rejects_any_unidentified_input_checksum(tmp_path: Path, which: str) -> None:
    (
        vessel_path,
        vessel_sha,
        quality_path,
        _quality_sha,
        domain_path,
        domain_sha,
        report_path,
        report_sha,
    ) = prepare_sources(tmp_path)
    wrong = "0" * 64
    if which == "vessel":
        with pytest.raises(VesselDomainDisplayInputError, match="checksum mismatch"):
            load_vessel_source(vessel_path, expected_sha256=wrong)
    elif which == "quality":
        vessel = load_vessel_source(vessel_path, expected_sha256=vessel_sha)
        with pytest.raises(VesselDomainDisplayInputError, match="checksum mismatch"):
            load_vessel_quality_source(
                quality_path, expected_sha256=wrong, vessel=vessel
            )
    else:
        with pytest.raises(VesselDomainDisplayInputError, match="checksum mismatch"):
            load_domain_source(
                domain_path,
                expected_sha256=wrong if which == "domain" else domain_sha,
                report_path=report_path,
                expected_report_sha256=wrong if which == "report" else report_sha,
            )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("output_sha", "does not bind"),
        ("quality_input_id", "input id"),
        ("excluded_count", "do not reconcile"),
        ("completeness", "must remain unverified"),
        ("distance", "does not conserve"),
    ],
)
def test_rejects_mismatched_or_invalid_vessel_quality_accounting(
    tmp_path: Path, mutation: str, message: str
) -> None:
    (
        vessel_path,
        vessel_sha,
        quality_path,
        _quality_sha,
        _domain_path,
        _domain_sha,
        _report_path,
        _report_sha,
    ) = prepare_sources(tmp_path)
    vessel = load_vessel_source(vessel_path, expected_sha256=vessel_sha)
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    if mutation == "output_sha":
        quality["output"]["sha256"] = "0" * 64
    elif mutation == "quality_input_id":
        quality["input_id"] = "vessel-input-000000000000000000000000"
    elif mutation == "excluded_count":
        quality["counts"]["candidate_segments"]["excluded"] = 3
    elif mutation == "completeness":
        quality["input"]["observational_completeness"]["status"] = "verified"
    else:
        quality["distance_conservation"]["by_group"]["all_commercial"][
            "outside_support_m"
        ] = 100.0
    quality_path.write_text(
        json.dumps(quality, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    changed_sha = hashlib.sha256(quality_path.read_bytes()).hexdigest()
    vessel = replace(
        vessel,
        embedded_quality={
            key: value for key, value in quality.items() if key != "output"
        },
    )

    with pytest.raises(VesselDomainDisplayInputError, match=message):
        load_vessel_quality_source(
            quality_path, expected_sha256=changed_sha, vessel=vessel
        )


def test_rejects_domain_and_vessel_on_different_grids(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    altered = replace(bundle.domain_source, source_checksums={"grid": "0" * 64})
    with pytest.raises(VesselDomainDisplayInputError, match="different water grids"):
        build_exports(bundle.vessel_source, bundle.vessel_quality_source, altered)


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("parameters", "maximum_gap_seconds", 600.0, "maximum_gap_seconds"),
        ("parameters", "edge_treatment", "drop-edge", "edge_treatment"),
        ("parameters", "support_treatment", "centroids", "support_treatment"),
        ("input", "observational_completeness", {"status": "verified"}, "unverified"),
    ],
)
def test_rejects_changed_vessel_method_or_completeness(
    tmp_path: Path,
    section: str,
    field: str,
    value: object,
    message: str,
) -> None:
    table = vessel_table()
    metadata = dict(table.schema.metadata or {})
    document = json.loads(metadata[b"whale_vessel_analysis"])
    document[section][field] = value
    metadata[b"whale_vessel_analysis"] = json.dumps(
        document, sort_keys=True, separators=(",", ":")
    ).encode()
    table = table.replace_schema_metadata(metadata)
    path = tmp_path / "changed-method.parquet"
    digest = _write_table(path, table)
    with pytest.raises(VesselDomainDisplayInputError, match=message):
        load_vessel_source(path, expected_sha256=digest)


def test_rejects_disagreement_between_water_area_units(tmp_path: Path) -> None:
    table = vessel_table()
    index = table.schema.get_field_index("water_area_km2")
    changed = table.set_column(
        index,
        table.schema.field(index),
        pa.array([20.0, 25.0, 25.0, 25.0], type=pa.float64()),
    )
    path = tmp_path / "changed-units.parquet"
    digest = _write_table(path, changed)
    with pytest.raises(VesselDomainDisplayInputError, match="water-area units"):
        load_vessel_source(path, expected_sha256=digest)


def test_writes_atomic_bundle_only_to_approved_destinations(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    exported_at = datetime(2026, 9, 6, 12, tzinfo=UTC)
    output = (
        Path(__file__).resolve().parents[2] / "data/interim/test-vessel-domain-display"
    )
    result = write_export_bundle(
        bundle,
        output,
        exported_at=exported_at,
    )
    try:
        for path, digest, size, manifest_path, _manifest_digest in result.outputs:
            assert path.is_file() and path.stat().st_size == size
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
            assert manifest_path.is_file()
        with pytest.raises(VesselDomainDisplayOutputError, match="overwrite"):
            write_export_bundle(
                bundle,
                output,
                exported_at=exported_at,
            )
    finally:
        for name in (VESSEL_OUTPUT_NAME, DOMAIN_OUTPUT_NAME):
            (output / name).unlink(missing_ok=True)
            (output / f"{name}{MANIFEST_SUFFIX}").unlink(missing_ok=True)
        output.rmdir()

    with pytest.raises(VesselDomainDisplayOutputError, match="approved"):
        write_export_bundle(
            bundle,
            tmp_path / "public",
            exported_at=exported_at,
        )

    protected = Path(__file__).resolve().parents[2] / "data/raw/display-export"
    with pytest.raises(VesselDomainDisplayOutputError, match="raw data"):
        write_export_bundle(
            bundle,
            protected,
            exported_at=exported_at,
            approved_roots=[protected],
        )


def test_failed_overwrite_restores_the_complete_prior_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _bundle(tmp_path / "sources")
    output = tmp_path / "approved"
    timestamp = datetime(2026, 9, 6, 12, tzinfo=UTC)
    write_export_bundle(
        bundle,
        output,
        exported_at=timestamp,
        approved_roots=[output],
    )
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    real_replace = export_module.os.replace
    replacement_count = 0
    failed = False

    def fail_once_during_commit(source: Path, destination: Path) -> None:
        nonlocal replacement_count, failed
        replacement_count += 1
        if replacement_count == 7 and not failed:
            failed = True
            raise OSError("simulated bundle commit failure")
        real_replace(source, destination)

    monkeypatch.setattr(export_module.os, "replace", fail_once_during_commit)
    with pytest.raises(VesselDomainDisplayOutputError, match="simulated"):
        write_export_bundle(
            bundle,
            output,
            exported_at=timestamp,
            overwrite=True,
            approved_roots=[output],
        )

    assert {path.name: path.read_bytes() for path in output.iterdir()} == before
