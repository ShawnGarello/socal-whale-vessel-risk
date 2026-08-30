from __future__ import annotations

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pyarrow as pa
import pytest
from pyproj import Transformer
from shapely.geometry import LineString, Point, box

from whale_vessel_analysis import domain_evidence
from whale_vessel_analysis.domain_evidence import (
    DomainEvidenceError,
    Scenario,
    measure_candidate,
    run_domain_evidence,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _synthetic_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Path], Path]:
    interim = (tmp_path / "data" / "interim").resolve()
    monkeypatch.setattr(domain_evidence, "_PROJECT_INTERIM_ROOT", interim)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    grid_path = inputs / "grid.parquet"
    shoreline_archive = inputs / "shoreline.zip"
    station_archive = inputs / "stations.zip"
    vsr_path = inputs / "vsr.geojson"
    for path, payload in (
        (grid_path, b"synthetic grid"),
        (shoreline_archive, b"synthetic shoreline"),
        (station_archive, b"synthetic stations"),
        (vsr_path, b"synthetic VSR"),
    ):
        path.write_bytes(payload)

    config_path = inputs / "domain.toml"
    config_path.write_text(
        f'''schema_version = 1
analysis_crs = "EPSG:3310"
shoreline_crs = "EPSG:4269"
station_crs = "EPSG:4269"
vsr_crs = "EPSG:4326"
shoreline_member = "shoreline.shp"
station_member = "stations.gpkg"
shoreline_simplification_m = 0.0
vsr_segment_max_degrees = 0.01
buffer_quadrant_segments = 8
cell_area_tolerance_m2 = 0.001

[source_sha256]
grid = "{_sha256(grid_path)}"
shoreline_archive = "{_sha256(shoreline_archive)}"
station_archive = "{_sha256(station_archive)}"
vsr = "{_sha256(vsr_path)}"

[shoreline_filter]
lon_min = -121.0
lat_min = 33.0
lon_max = -119.0
lat_max = 35.0

[station_filter]
lon_min = -121.0
lat_min = 33.0
lon_max = -119.0
lat_max = 35.0

[[scenarios]]
id = "synthetic_coast"
basis = "coastline"
distance = 1
unit = "statute_mile"

[[scenarios]]
id = "synthetic_receivers"
basis = "receivers"
distance = 1
unit = "nautical_mile"
''',
        encoding="utf-8",
    )

    longitude, latitude = -120.0, 34.0
    x, y = Transformer.from_crs("EPSG:4269", "EPSG:3310", always_xy=True).transform(
        longitude, latitude
    )
    synthetic_grid = SimpleNamespace(
        cells=[SimpleNamespace(geometry=box(x - 2500, y - 2500, x + 2500, y + 2500))],
        sha256=_sha256(grid_path),
    )
    monkeypatch.setattr(domain_evidence, "load_default_config", lambda: object())
    monkeypatch.setattr(
        domain_evidence,
        "load_target_grid",
        lambda *_args, **_kwargs: synthetic_grid,
    )

    def load_geometries(uri: str, _expected_crs: str) -> tuple[pa.Table, np.ndarray]:
        if "shoreline.zip" in uri:
            return pa.table({}), np.array(
                [LineString([(-120.01, 33.99), (-120.01, 34.01)])], dtype=object
            )
        if "stations.zip" in uri:
            return pa.table(
                {
                    "stationName": ["Synthetic NAIS", "Excluded LOMA"],
                    "stationType": ["NAIS", "LOMA"],
                }
            ), np.array([Point(-120.0, 34.0), Point(-120.0, 34.0)], dtype=object)
        return pa.table({}), np.array(
            [box(-120.05, 33.95, -119.95, 34.05)], dtype=object
        )

    monkeypatch.setattr(domain_evidence, "_load_geometries", load_geometries)
    return {
        "config_path": config_path,
        "grid_path": grid_path,
        "shoreline_archive": shoreline_archive,
        "station_archive": station_archive,
        "vsr_path": vsr_path,
    }, interim


def test_distance_units_are_explicit() -> None:
    assert Scenario("a", "coastline", 40, "statute_mile").distance_m == pytest.approx(
        64373.76
    )
    assert Scenario("b", "coastline", 40, "nautical_mile").distance_m == pytest.approx(
        74080.0
    )


def test_candidate_measurement_uses_fractional_geometry() -> None:
    cells = np.array(
        [box(0, 0, 100, 100), box(100, 0, 200, 100), box(200, 0, 300, 100)],
        dtype=object,
    )
    result = measure_candidate(
        cells,
        box(-10, -10, 150, 110),
        box(-10, -10, 100, 110),
        Scenario("synthetic", "receivers", 40, "statute_mile"),
        tolerance_m2=1e-9,
    )
    assert result.included_water_area_m2 == pytest.approx(15000)
    assert result.inside_vsr_area_m2 == pytest.approx(10000)
    assert result.outside_vsr_area_m2 == pytest.approx(5000)
    assert result.fully_inside_cell_count == 1
    assert result.partly_inside_cell_count == 1
    assert result.wholly_outside_cell_count == 1
    assert result.to_dict(10000)["inside_fraction_of_candidate"] == pytest.approx(2 / 3)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('basis = "coastline"', 'basis = "unknown"', "basis must be"),
        ('unit = "statute_mile"', 'unit = "unknown"', "unit must be"),
        ('id = "coast_40_statute_miles"', 'id = ""', "nonempty"),
        ("distance = 40", "distance = 0", "distance must be positive"),
        (
            'analysis_crs = "EPSG:3310"',
            'analysis_crs = "EPSG:4326"',
            "must be EPSG:3310",
        ),
    ],
)
def test_configuration_rejects_invalid_values(old: str, new: str, message: str) -> None:
    path = Path(__file__).parents[1] / "evidence" / "domain-candidates.toml"
    payload = path.read_text(encoding="utf-8").replace(old, new, 1).encode()
    with pytest.raises(DomainEvidenceError, match=message):
        domain_evidence._load_config(payload)


def test_configuration_requires_unique_scenario_ids_and_nonempty_scenarios() -> None:
    path = Path(__file__).parents[1] / "evidence" / "domain-candidates.toml"
    text = path.read_text(encoding="utf-8")
    duplicate = text.replace(
        'id = "coast_40_nautical_miles"', 'id = "coast_40_statute_miles"'
    )
    with pytest.raises(DomainEvidenceError, match="scenario id must be unique"):
        domain_evidence._load_config(duplicate.encode())
    with pytest.raises(DomainEvidenceError, match="scenarios must be a nonempty"):
        domain_evidence._load_config(
            text.split("[[scenarios]]", maxsplit=1)[0].encode()
        )


def test_outputs_must_be_distinct_interim_paths_and_not_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim = (tmp_path / "data" / "interim").resolve()
    raw = tmp_path / "data" / "raw"
    monkeypatch.setattr(domain_evidence, "_PROJECT_INTERIM_ROOT", interim)
    same = interim / "same.json"
    with pytest.raises(DomainEvidenceError, match="must be distinct"):
        domain_evidence._validate_output_paths(
            same, same, (tmp_path / "input",), overwrite=False
        )
    with pytest.raises(DomainEvidenceError, match="beneath ignored data/interim"):
        domain_evidence._validate_output_paths(
            raw / "report.json",
            interim / "masks.parquet",
            (tmp_path / "input",),
            overwrite=False,
        )
    input_mask = interim / "input.parquet"
    with pytest.raises(DomainEvidenceError, match="distinct from every input"):
        domain_evidence._validate_output_paths(
            interim / "report.json",
            input_mask,
            (input_mask,),
            overwrite=False,
        )


def test_arbitrary_existing_outputs_cannot_be_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    interim = (tmp_path / "data" / "interim").resolve()
    interim.mkdir(parents=True)
    monkeypatch.setattr(domain_evidence, "_PROJECT_INTERIM_ROOT", interim)
    report = interim / "report.json"
    masks = interim / "masks.parquet"
    report.write_text('{"contract":"unrelated"}\n', encoding="utf-8")
    masks.write_bytes(b"unrelated")
    with pytest.raises(DomainEvidenceError, match="only replaces"):
        domain_evidence._validate_output_paths(
            report, masks, (tmp_path / "input",), overwrite=True
        )


def test_synthetic_end_to_end_outputs_are_deterministic_and_create_parents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs, interim = _synthetic_inputs(tmp_path, monkeypatch)
    first_report = interim / "first" / "report.json"
    first_masks = interim / "first" / "masks.parquet"
    second_report = interim / "second" / "report.json"
    second_masks = interim / "second" / "masks.parquet"

    first = run_domain_evidence(
        **inputs, report_path=first_report, masks_path=first_masks
    )
    second = run_domain_evidence(
        **inputs, report_path=second_report, masks_path=second_masks
    )

    assert first == second
    assert first_report.read_bytes() == second_report.read_bytes()
    assert first_masks.read_bytes() == second_masks.read_bytes()
    assert first["processing"]["receiver_names_in_filter"] == ["Synthetic NAIS"]  # type: ignore[index]


@pytest.mark.parametrize(
    ("source_marker", "message"),
    [
        ("shoreline.zip", "shoreline source subset cannot be empty"),
        ("stations.zip", "NAIS station source subset cannot be empty"),
    ],
)
def test_source_subsets_must_be_nonempty(
    source_marker: str,
    message: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs, interim = _synthetic_inputs(tmp_path, monkeypatch)
    load_geometries = domain_evidence._load_geometries

    def empty_selected_source(
        uri: str, expected_crs: str
    ) -> tuple[pa.Table, np.ndarray]:
        table, geometries = load_geometries(uri, expected_crs)
        if source_marker in uri:
            return table, np.array([], dtype=object)
        return table, geometries

    monkeypatch.setattr(domain_evidence, "_load_geometries", empty_selected_source)
    with pytest.raises(DomainEvidenceError, match=message):
        run_domain_evidence(
            **inputs,
            report_path=interim / "report.json",
            masks_path=interim / "masks.parquet",
        )


def test_atomic_failure_restores_existing_pair_without_partial_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs, interim = _synthetic_inputs(tmp_path, monkeypatch)
    report = interim / "evidence" / "report.json"
    masks = interim / "evidence" / "masks.parquet"
    run_domain_evidence(**inputs, report_path=report, masks_path=masks)
    original_report = report.read_bytes()
    original_masks = masks.read_bytes()
    with pytest.raises(DomainEvidenceError, match="explicit overwrite authorization"):
        run_domain_evidence(**inputs, report_path=report, masks_path=masks)
    real_replace = os.replace

    def fail_report_publication(source: Path, destination: Path) -> None:
        if destination == report and source.suffix == ".tmp":
            raise OSError("synthetic paired-publication failure")
        real_replace(source, destination)

    monkeypatch.setattr(domain_evidence, "_replace_file", fail_report_publication)
    with pytest.raises(
        DomainEvidenceError, match="synthetic paired-publication failure"
    ):
        run_domain_evidence(
            **inputs,
            report_path=report,
            masks_path=masks,
            overwrite=True,
        )

    assert report.read_bytes() == original_report
    assert masks.read_bytes() == original_masks
    assert list(report.parent.glob(".*.tmp")) == []
    assert list(report.parent.glob(".*.backup")) == []
