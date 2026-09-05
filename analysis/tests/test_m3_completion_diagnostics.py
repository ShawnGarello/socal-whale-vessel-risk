"""Known-geometry checks for the bounded session diagnostic tooling."""

import importlib.util
import json
from contextlib import contextmanager
from pathlib import Path

import pyarrow as pa
import pytest
from pyproj import Transformer


def test_cell_comparison_preserves_signed_changes_and_zero_denominator():
    script = (
        Path(__file__).resolve().parents[1] / "scripts/compare_vessel_candidates.py"
    )
    spec = importlib.util.spec_from_file_location("m3_comparison", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    first = [
        {"cell_id": "a", "vessel_km_cargo": 3},
        {"cell_id": "b", "vessel_km_cargo": 0},
    ]
    second = [
        {"cell_id": "a", "vessel_km_cargo": 1},
        {"cell_id": "b", "vessel_km_cargo": 4},
    ]
    result = module.compare_cells(first, second, "cargo")
    assert result["net_difference_km"] == 2
    assert result["absolute_difference_km"] == 6
    assert result["changed_at_least_1_km"] == 2
    assert result["top_ten_cells"][0]["cell_id"] == "b"
    assert result["top_ten_share_of_absolute_difference"] == 1
    assert (
        module.compare_cells(first, first, "cargo")[
            "top_ten_share_of_absolute_difference"
        ]
        is None
    )
    with pytest.raises(ValueError, match="cell identities"):
        module.compare_cells(first, second[::-1], "cargo")


def test_diagnostics_known_distances_missing_speed_and_hourly_evidence(
    tmp_path, monkeypatch
):
    script = (
        Path(__file__).resolve().parents[1] / "scripts/m3_completion_diagnostics.py"
    )
    spec = importlib.util.spec_from_file_location("m3_diagnostics", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module, "__file__", str(tmp_path / "analysis/scripts/diagnostics.py")
    )
    manifest = {"period_input_id": "multiday-ais-17e982f999f7093945193378", "dates": []}
    monkeypatch.setattr(module, "load_period_manifest", lambda path: manifest)
    monkeypatch.setattr(module, "sha256_file", lambda path: "synthetic")
    monkeypatch.setattr(module, "RelationResources", lambda *args: args)
    inverse = Transformer.from_crs(3310, 4326, always_xy=True)
    longitude, latitude = inverse.transform(0, -500000)
    rows = []
    # 1000 m / 60 s = 32.3974 knots; 2000 m / 60 s = 64.7948 knots.
    # Zero distance is retained; an absent endpoint and a 1801 s gap are not.
    for distance, seconds, sog in [
        (1000, 60, 32),
        (2000, 60, 10),
        (0, 600, None),
        (1000, 1801, 1),
        (1000, None, 1),
    ]:
        end_lon, end_lat = inverse.transform(distance, -500000)
        rows.append(
            {
                "longitude": longitude,
                "latitude": latitude,
                "next_longitude": end_lon,
                "next_latitude": end_lat,
                "observed_at_utc": 0,
                "next_observed_at_utc": seconds * 1000000 if seconds else None,
                "vessel_type_group": "passenger",
                "sog_knots": sog,
                "next_sog_knots": sog,
            }
        )

    class Connection:
        def execute(self, query):
            self.result = (
                [("2024-09-29", 20, "passenger", 5, 1)]
                if "hour(" in query
                else [("passenger", "20-50", 5, 1)]
            )
            return self

        def fetchall(self):
            return self.result

    class Relation:
        connection = Connection()
        view_name = "synthetic"

        def adjacent_observation_batches(self, batch_size):
            assert batch_size == 50000
            yield pa.RecordBatch.from_pylist(rows)

    @contextmanager
    def relation(*args, **kwargs):
        assert kwargs == {"require_ready": True}
        yield Relation()

    monkeypatch.setattr(module, "open_period_relation", relation)
    output = tmp_path / "data/interim/check/diagnostics.json"
    arguments = [
        "--manifest",
        "synthetic.json",
        "--output",
        str(output),
        "--temp-directory",
        str(tmp_path / "spill"),
    ]
    assert module.main(arguments) == 0
    report = json.loads(output.read_text())
    strata = report["segment_strata"]
    assert sum(bucket["segments"] for bucket in strata.values()) == 3
    mid = strata["passenger/0-300/30-50"]
    assert mid["parent_metres"] == pytest.approx(1000, abs=1e-6)
    assert mid["within_2_knots_of_endpoint_mean"] == 1
    assert strata["passenger/0-300/50+"]["within_5_knots_of_endpoint_mean"] == 0
    stationary = strata["passenger/300-1800/0-30"]
    assert stationary["parent_metres"] == 0
    assert "both_sog_available" not in stationary
    assert report["hourly"] == [["2024-09-29", 20, "passenger", 5, 1]]
    with pytest.raises(ValueError, match="fresh ignored interim"):
        module.main(arguments)
