"""Known-answer and boundary tests for downstream M6 delivery contracts."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from pyproj import CRS
from shapely.geometry import box

from whale_vessel_analysis import exposure_run
from whale_vessel_analysis.cleaned_ais_bundle import sha256_file
from whale_vessel_analysis.exposure import prepare_cells
from whale_vessel_analysis.exposure_delivery import (
    DISPLAY_FIELDS,
    EXPECTED_INPUT_SHA256,
    ExposureDeliveryInputError,
    ExposureDeliveryOutputError,
    _area_text,
    _percent_text,
    _threshold_text,
    build_delivery_export,
    build_results_export,
    load_bundle,
    parse_utc_timestamp,
    verify_results_document,
    write_delivery,
)
from whale_vessel_analysis.exposure_geometry import ExposureBoundaries
from whale_vessel_analysis.exposure_inputs import ExposureInputCell


def _cell(
    name: str,
    x: int,
    width: int,
    density: float,
    distance: float,
    *,
    y: int = -500_000,
) -> ExposureInputCell:
    water = box(x, y, x + width, y + 1000)
    area = water.area / 1e6
    return ExposureInputCell(
        name,
        x,
        y,
        water,
        area,
        density,
        density * area,
        distance,
    )


def _grids(*, all_zero: bool = False):
    inputs = (
        _cell("a", 0, 1000, 2, 0 if all_zero else 10),
        _cell("b", 1000, 2000, 1, 0 if all_zero else 20),
        _cell("excluded", 4000, 1000, 999, 0 if all_zero else 999),
    )
    boundaries = ExposureBoundaries(
        box(0, -500_000, 2000, -499_000),
        box(0, -500_000, 500, -499_000),
        "EPSG:3310",
    )
    cells = prepare_cells(inputs, boundaries)
    return {"5km": cells, "10km": cells}


def _identity() -> dict[str, object]:
    basis: dict[str, object] = {
        "method": exposure_run.method_contract(),
        "input_sha256": dict(EXPECTED_INPUT_SHA256),
        "software": {
            "python": "3.13.7",
            "pyarrow": "25.0.1",
            "shapely": "2.1.2",
            "pyproj": "3.7.2",
        },
    }
    basis["run_id"] = (
        "exposure-"
        + hashlib.sha256(exposure_run.json_text(basis).encode()).hexdigest()[:24]
    )
    return basis


def _make_bundle(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    name: str = "bundle",
    all_zero: bool = False,
    started: datetime = datetime(2026, 9, 6, tzinfo=UTC),
) -> tuple[Path, dict[str, str]]:
    monkeypatch.setattr(exposure_run, "ROOT", root)
    bundle = root / "data" / "derived" / name
    result = exposure_run.write_bundle(
        bundle,
        _grids(all_zero=all_zero),
        _identity(),
        started,
        {},
        {"vessel_lineage": "a" * 64},
    )
    hashes = {
        "5km": result["output_sha256"]["exposure-5km.parquet"],
        "10km": result["output_sha256"]["exposure-10km.parquet"],
        "report": sha256_file(bundle / "sensitivity-report.json"),
    }
    return bundle, hashes


def _load(bundle: Path, hashes: dict[str, str]):
    return load_bundle(
        bundle,
        expected_5km_sha256=hashes["5km"],
        expected_10km_sha256=hashes["10km"],
        expected_report_sha256=hashes["report"],
    )


def test_known_answer_results_denominators_thresholds_and_display_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    inspection = _load(bundle, hashes)
    export = build_delivery_export(
        inspection,
        display_name="relative-exposure.geojson",
        generated_at=datetime(2026, 9, 6, 22, tzinfo=UTC),
    )
    results = json.loads(export.results.payload)
    scenario = results["scenarios"]["5km_product"]

    assert scenario["integrated_exposure"]["total_qualified"] == 30
    assert scenario["integrated_exposure"]["inside_vsr"] == 10
    assert scenario["integrated_exposure"]["outside_vsr"] == 20
    assert scenario["integrated_exposure"]["inside_share"] == pytest.approx(1 / 3)
    assert (
        scenario["integrated_exposure"]["presentation"]["inside_share_percent_1dp"]
        == "33.3%"
    )
    assert (
        "integrated inside plus integrated outside"
        in scenario["integrated_exposure"]["share_denominator"]
    )

    p90 = scenario["high_exposure"]["all_valid"][1]
    assert p90["threshold"] == 20
    assert p90["selected_water_area_km2"] == 1
    assert p90["inside_share_of_selected_water"] == 0.5
    assert p90["presentation"]["inside_share_percent_1dp"] == "50.0%"
    assert (
        "selected high-exposure qualified water area"
        in scenario["high_exposure"]["area_share_denominator"]
    )

    display = json.loads(export.display.geojson)
    assert [feature["id"] for feature in display["features"]] == ["a", "b"]
    assert set(display["features"][0]["properties"]) == {
        name for name, _unit, _meaning in DISPLAY_FIELDS
    }
    assert display["features"][1]["properties"]["water_area_km2"] == 2
    assert display["features"][1]["properties"]["qualified_area_km2"] == 1
    assert not any(
        "inside_vsr" in field or "outside_vsr" in field
        for field in display["features"][0]["properties"]
    )
    manifest = json.loads(export.display_manifest)
    assert manifest["geometry"]["source_crs"] == "EPSG:3310"
    assert manifest["geometry"]["display_crs"] == "EPSG:4326"
    exterior = display["features"][0]["geometry"]["coordinates"][0]
    signed_area = (
        sum(
            left[0] * right[1] - right[0] * left[1]
            for left, right in pairwise(exterior)
        )
        / 2
    )
    assert signed_area > 0  # RFC 7946 counterclockwise exterior ring.


def test_all_zero_nulls_are_preserved_without_high_classification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch, all_zero=True)
    inspection = _load(bundle, hashes)
    export = build_delivery_export(
        inspection,
        display_name="relative-exposure.geojson",
        generated_at=datetime(2026, 9, 6, tzinfo=UTC),
    )
    display = json.loads(export.display.geojson)
    for feature in display["features"]:
        assert feature["properties"]["product_index"] is None
        assert feature["properties"]["log_traffic_index"] is None
        assert feature["properties"]["product_high_p90"] is None
        assert feature["properties"]["log_traffic_high_p90"] is None
    scenario = json.loads(export.results.payload)["scenarios"]["5km_product"]
    assert scenario["integrated_exposure"]["total_qualified"] == 0
    assert scenario["integrated_exposure"]["inside_share"] is None
    assert (
        scenario["integrated_exposure"]["presentation"]["inside_share_percent_1dp"]
        is None
    )
    assert not scenario["high_exposure"]["all_valid"][1]["available"]
    assert (
        scenario["high_exposure"]["all_valid"][1]["inside_share_of_selected_water"]
        is None
    )


def test_presentation_rounding_is_declared_and_known_by_construction() -> None:
    assert _percent_text(0.12345) == "12.3%"
    assert _percent_text(0.98765) == "98.8%"
    assert _percent_text(0.9995) == "100.0%"
    assert _area_text(12.34) == "12.3 km^2"
    assert _threshold_text(0.23455) == "0.2346"


def test_rejects_incompatible_source_schema_and_inconsistent_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    source = bundle / "exposure-5km.parquet"
    table = pq.read_table(source).drop(["water_area_km2"])
    pq.write_table(table, source)
    hashes["5km"] = sha256_file(source)
    report_path = bundle / "sensitivity-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["output_sha256"]["exposure-5km.parquet"] = hashes["5km"]
    report_path.write_text(exposure_run.json_text(report), encoding="utf-8")
    hashes["report"] = sha256_file(report_path)
    with pytest.raises(ExposureDeliveryInputError, match="schema differs"):
        _load(bundle, hashes)

    other, other_hashes = _make_bundle(tmp_path, monkeypatch, name="other")
    other_report_path = other / "sensitivity-report.json"
    other_report = json.loads(other_report_path.read_text(encoding="utf-8"))
    other_report["identity"]["method"]["speed_weight"] = "invented"
    other_report_path.write_text(exposure_run.json_text(other_report), encoding="utf-8")
    other_hashes["report"] = sha256_file(other_report_path)
    with pytest.raises(ExposureDeliveryInputError, match="identities differ"):
        _load(other, other_hashes)


def test_rejects_incompatible_source_crs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    source = bundle / "exposure-5km.parquet"
    table = pq.read_table(source)
    metadata = dict(table.schema.metadata or {})
    geo = json.loads(metadata[b"geo"])
    geo["columns"]["geometry"]["crs"] = CRS.from_epsg(4326).to_json_dict()
    metadata[b"geo"] = exposure_run.json_text(geo).encode()
    pq.write_table(table.replace_schema_metadata(metadata), source)
    hashes["5km"] = sha256_file(source)
    report_path = bundle / "sensitivity-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["output_sha256"]["exposure-5km.parquet"] = hashes["5km"]
    report_path.write_text(exposure_run.json_text(report), encoding="utf-8")
    hashes["report"] = sha256_file(report_path)
    with pytest.raises(ExposureDeliveryInputError, match="EPSG:3310"):
        _load(bundle, hashes)


def test_checksum_is_required_and_serialized_results_reject_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    with pytest.raises(ExposureDeliveryInputError, match="checksum mismatch"):
        load_bundle(
            bundle,
            expected_5km_sha256="f" * 64,
            expected_10km_sha256=hashes["10km"],
            expected_report_sha256=hashes["report"],
        )
    inspection = _load(bundle, hashes)
    result = build_results_export(
        inspection, generated_at=datetime(2026, 9, 6, tzinfo=UTC)
    )
    tampered = copy.deepcopy(result.document)
    tampered["scenarios"]["5km_product"]["integrated_exposure"]["inside_share"] = 0.99
    with pytest.raises(ExposureDeliveryOutputError, match="identity differs"):
        verify_results_document(tampered, inspection)


def test_upstream_run_metadata_is_not_read_and_does_not_change_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, first_hashes = _make_bundle(
        tmp_path,
        monkeypatch,
        name="first",
        started=datetime(2026, 9, 6, tzinfo=UTC),
    )
    repeat, repeat_hashes = _make_bundle(
        tmp_path,
        monkeypatch,
        name="repeat",
        started=datetime(2026, 9, 7, tzinfo=UTC),
    )
    repeat_metadata = repeat / "run-metadata.json"
    metadata = json.loads(repeat_metadata.read_text(encoding="utf-8"))
    metadata["input_lineage_sha256"] = {"vessel_lineage": "b" * 64}
    repeat_metadata.write_text(json.dumps(metadata), encoding="utf-8")
    assert first_hashes == repeat_hashes

    generated_at = datetime(2026, 9, 6, 22, tzinfo=UTC)
    one = build_delivery_export(
        _load(first, first_hashes),
        display_name="relative-exposure.geojson",
        generated_at=generated_at,
    )
    two = build_delivery_export(
        _load(repeat, repeat_hashes),
        display_name="relative-exposure.geojson",
        generated_at=generated_at,
    )
    assert one.display.geojson == two.display.geojson
    assert one.display_manifest == two.display_manifest
    assert one.results.payload == two.results.payload


def test_delivery_is_byte_repeatable_into_fresh_locations_and_timestamp_is_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    inspection = _load(bundle, hashes)
    generated_at = datetime(2026, 9, 6, 22, tzinfo=UTC)
    outputs = []
    for name in ("one", "two"):
        root = tmp_path / "published" / name
        display = root / "relative-exposure.geojson"
        results = root / "exposure-results.v1.json"
        write_delivery(
            inspection,
            display,
            results,
            generated_at=generated_at,
            display_roots=[root],
            results_roots=[root],
        )
        outputs.append(
            (
                display.read_bytes(),
                display.with_name(display.name + ".manifest.json").read_bytes(),
                results.read_bytes(),
            )
        )
    assert outputs[0] == outputs[1]

    earlier = build_results_export(inspection, generated_at=generated_at)
    later = build_results_export(
        inspection, generated_at=datetime(2026, 9, 7, 22, tzinfo=UTC)
    )
    assert earlier.document["results_id"] == later.document["results_id"]
    assert earlier.payload != later.payload


def test_destination_guards_and_existing_output_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    inspection = _load(bundle, hashes)
    generated_at = datetime(2026, 9, 6, tzinfo=UTC)
    root = tmp_path / "published"
    display = root / "relative-exposure.geojson"
    results = root / "exposure-results.v1.json"
    write_delivery(
        inspection,
        display,
        results,
        generated_at=generated_at,
        display_roots=[root],
        results_roots=[root],
    )
    with pytest.raises(ExposureDeliveryOutputError, match="already exists"):
        write_delivery(
            inspection,
            display,
            results,
            generated_at=generated_at,
            display_roots=[root],
            results_roots=[root],
        )
    raw = tmp_path / "another-checkout" / "data" / "raw"
    with pytest.raises(ExposureDeliveryOutputError, match="raw data"):
        write_delivery(
            inspection,
            raw / "relative-exposure.geojson",
            raw / "exposure-results.v1.json",
            generated_at=generated_at,
            display_roots=[raw],
            results_roots=[raw],
        )


def test_public_artifacts_have_no_private_locator_credential_or_vsr_geometry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle, hashes = _make_bundle(tmp_path, monkeypatch)
    export = build_delivery_export(
        _load(bundle, hashes),
        display_name="relative-exposure.geojson",
        generated_at=datetime(2026, 9, 6, tzinfo=UTC),
    )
    combined = "\n".join(
        (
            export.display.geojson.decode(),
            export.display_manifest.decode(),
            export.results.payload.decode(),
        )
    ).lower()
    assert str(tmp_path).lower() not in combined
    assert "run-metadata.json" not in combined
    assert "input_lineage_sha256" not in combined
    assert "password" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    display = json.loads(export.display.geojson)
    assert all(
        set(feature["properties"]).isdisjoint(
            {"inside_vsr_area_km2", "outside_vsr_area_km2"}
        )
        for feature in display["features"]
    )


def test_parse_timestamp_requires_utc() -> None:
    assert parse_utc_timestamp("2026-09-06T22:00:00Z").tzinfo == UTC
    with pytest.raises(ExposureDeliveryOutputError, match="must be UTC"):
        parse_utc_timestamp("2026-09-06T22:00:00-07:00")
