from __future__ import annotations

import csv
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

import whale_vessel_analysis.ais_processing as ais_processing
from whale_vessel_analysis.ais import AIS_PUBLISHED_HEADER
from whale_vessel_analysis.ais_processing import (
    CLEANED_FILENAME,
    QUALITY_REPORT_FILENAME,
    RUN_METADATA_FILENAME,
    AISProcessingError,
    process_ais_csv,
)
from whale_vessel_analysis.cli import main
from whale_vessel_analysis.config import load_default_config


def _row(**updates: str) -> list[str]:
    values = {
        "MMSI": "123456789",
        "BaseDateTime": "2024-07-15T00:00:00",
        "LAT": "34.0",
        "LON": "-118.0",
        "SOG": "12.5",
        "COG": "145.0",
        "Heading": "145",
        "VesselName": "SYNTHETIC VESSEL",
        "IMO": "IMO1234567",
        "CallSign": "TEST1",
        "VesselType": "70",
        "Status": "0",
        "Length": "200",
        "Width": "30",
        "Draft": "9.5",
        "Cargo": "70",
        "TransceiverClass": "A",
    }
    values.update(updates)
    return [values[field] for field in AIS_PUBLISHED_HEADER]


def _write_csv(
    path: Path,
    rows: list[list[str]],
    header: tuple[str, ...] = AIS_PUBLISHED_HEADER,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _report(output: Path) -> dict[str, object]:
    return json.loads((output / QUALITY_REPORT_FILENAME).read_text(encoding="utf-8"))


def _clock(*timestamps: datetime) -> Callable[[], datetime]:
    values = iter(timestamps)
    return lambda: next(values)


def test_cleaning_filters_and_normalizations_are_counted(tmp_path: Path) -> None:
    source = tmp_path / "day.csv"
    exact = _row(
        MMSI="323456789",
        BaseDateTime="2024-07-15T00:10:00",
        VesselType="80",
    )
    _write_csv(
        source,
        [
            _row(),
            _row(MMSI="223456789", BaseDateTime="2024-07-15T00:01:00", LON="-123"),
            _row(MMSI="223456780", BaseDateTime="2024-07-15T00:02:00", LAT="NaN"),
            _row(MMSI="223456781", BaseDateTime="malformed"),
            _row(MMSI="012345678", BaseDateTime="2024-07-15T00:03:00"),
            _row(
                MMSI="223456782",
                BaseDateTime="2024-07-15T00:04:00",
                SOG="102.3",
                COG="360",
                Heading="511",
                VesselType="60",
                Length="",
            ),
            _row(MMSI="223456783", BaseDateTime="2024-07-15T00:05:00", VesselType="30"),
            _row(MMSI="223456784", BaseDateTime="2024-07-15T00:06:00", VesselType=""),
            _row(
                MMSI="223456785", BaseDateTime="2024-07-15T00:07:00", VesselType="abc"
            ),
            _row(
                MMSI="223456786", BaseDateTime="2024-07-15T00:08:00", VesselType="70.5"
            ),
            _row(MMSI="223456787", BaseDateTime="2024-07-15T00:09:00", VesselType="0"),
            exact,
            exact,
            _row(MMSI="423456789", BaseDateTime="2024-07-15T00:11:00", LAT="34.0"),
            _row(MMSI="423456789", BaseDateTime="2024-07-15T00:11:00", LAT="34.1"),
        ],
    )
    output = tmp_path / "bundle"

    result = process_ais_csv(source, output, load_default_config())

    assert result.input_rows == 15
    assert result.output_rows == 3
    assert output.is_dir()
    assert {path.name for path in output.iterdir()} == {
        CLEANED_FILENAME,
        QUALITY_REPORT_FILENAME,
        RUN_METADATA_FILENAME,
    }
    report = _report(output)
    assert report["contract"] == "noaa_marine_cadastre_ais_extract_v2"
    assert report["temporal_coverage"] == {
        "observed_utc_date": "2024-07-15",
        "earliest_valid_observed_at_utc": "2024-07-15T00:00:00Z",
        "latest_valid_observed_at_utc": "2024-07-15T00:11:00Z",
        "completeness": {
            "status": "unverified",
            "reason": (
                "the supplied CSV carries no retained retrieval metadata that "
                "proves complete UTC-day coverage"
            ),
        },
    }
    assert report["configuration"]["analytical_domain_status"] == "accepted"
    assert report["counts"]["removals"] == {
        "conflicting_mmsi_timestamp_rows": 2,
        "exact_duplicate_rows": 1,
        "invalid_coordinate_rows": 1,
        "invalid_mmsi_rows": 1,
        "invalid_reported_sog_rows": 0,
        "invalid_timestamp_rows": 1,
        "malformed_vessel_type_rows": 2,
        "missing_vessel_type_rows": 1,
        "noncommercial_vessel_type_rows": 1,
        "outside_map_extent_rows": 1,
        "unavailable_vessel_type_rows": 1,
    }
    assert report["counts"]["normalizations"] == {
        "cog_sentinel_to_null_rows": 1,
        "heading_sentinel_to_null_rows": 1,
        "invalid_cog_to_null_rows": 0,
        "invalid_heading_to_null_rows": 0,
        "sog_sentinel_to_null_rows": 1,
        "unavailable_or_invalid_length_to_null_rows": 1,
    }
    with duckdb.connect() as connection:
        rows = connection.execute(
            f"""
            SELECT mmsi, sog_knots, vessel_type_group, length_m
            FROM read_parquet('{(output / CLEANED_FILENAME).as_posix()}')
            ORDER BY mmsi
            """
        ).fetchall()
    assert rows == [
        ("123456789", 12.5, "cargo", 200.0),
        ("223456782", None, "passenger", None),
        ("323456789", 12.5, "tanker", 200.0),
    ]


def test_invalid_reported_sog_is_removed_without_a_maximum_rule(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sog.csv"
    _write_csv(
        source,
        [
            _row(MMSI="123456781", SOG="not-a-number"),
            _row(MMSI="123456782", BaseDateTime="2024-07-15T00:01:00", SOG="-1"),
            _row(MMSI="123456783", BaseDateTime="2024-07-15T00:02:00", SOG="200"),
        ],
    )
    output = tmp_path / "bundle"

    process_ais_csv(source, output, load_default_config())

    report = _report(output)
    assert report["counts"]["removals"]["invalid_reported_sog_rows"] == 2
    assert (
        report["processing_parameters"]["reported_sog_validity"][
            "universal_maximum_enabled"
        ]
        is False
    )
    parquet_path = (output / CLEANED_FILENAME).as_posix()
    with duckdb.connect() as connection:
        assert connection.execute(
            f"SELECT sog_knots FROM read_parquet('{parquet_path}')"
        ).fetchone() == (200.0,)


def test_missing_nonfinite_and_out_of_range_coordinates_are_removed(
    tmp_path: Path,
) -> None:
    source = tmp_path / "coordinates.csv"
    _write_csv(
        source,
        [
            _row(MMSI="123456781", LAT=""),
            _row(MMSI="123456782", BaseDateTime="2024-07-15T00:01:00", LAT="Inf"),
            _row(MMSI="123456783", BaseDateTime="2024-07-15T00:02:00", LAT="91"),
            _row(MMSI="123456784", BaseDateTime="2024-07-15T00:03:00"),
        ],
    )
    output = tmp_path / "bundle"

    result = process_ais_csv(source, output, load_default_config())

    assert result.output_rows == 1
    assert _report(output)["counts"]["removals"]["invalid_coordinate_rows"] == 3


def test_output_and_metadata_are_deterministic_for_the_same_invocation(
    tmp_path: Path,
) -> None:
    source = tmp_path / "day.csv"
    _write_csv(source, [_row()])
    output = tmp_path / "bundle"

    fixed = datetime(2026, 8, 27, 12, tzinfo=UTC)
    first = process_ais_csv(source, output, load_default_config(), clock=lambda: fixed)
    first_bytes = {name: (output / name).read_bytes() for name in _BUNDLE_NAMES}
    second = process_ais_csv(
        source,
        output,
        load_default_config(),
        overwrite=True,
        clock=lambda: fixed,
    )

    assert first.run_id == second.run_id
    assert first.output_sha256 == second.output_sha256
    assert first_bytes == {name: (output / name).read_bytes() for name in _BUNDLE_NAMES}


_BUNDLE_NAMES = (CLEANED_FILENAME, QUALITY_REPORT_FILENAME, RUN_METADATA_FILENAME)


def test_existing_output_is_refused_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "day.csv"
    _write_csv(source, [_row()])
    output = tmp_path / "bundle"
    process_ais_csv(source, output, load_default_config())

    with pytest.raises(AISProcessingError, match="already exists"):
        process_ais_csv(source, output, load_default_config())


def test_overwrite_refuses_an_unowned_directory(tmp_path: Path) -> None:
    source = tmp_path / "day.csv"
    _write_csv(source, [_row()])
    output = tmp_path / "not-a-bundle"
    output.mkdir()
    (output / "unrelated.txt").write_text("preserve me", encoding="utf-8")

    with pytest.raises(AISProcessingError, match="only replaces"):
        process_ais_csv(source, output, load_default_config(), overwrite=True)

    assert (output / "unrelated.txt").read_text(encoding="utf-8") == "preserve me"


def test_output_under_raw_data_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "day.csv"
    _write_csv(source, [_row()])
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    monkeypatch.setattr(ais_processing, "_PROJECT_RAW_ROOT", raw_root.resolve())
    output = raw_root / "forbidden-bundle"

    with pytest.raises(AISProcessingError, match="cannot be written under raw data"):
        process_ais_csv(source, output, load_default_config())

    assert not output.exists()


def test_header_only_input_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "header-only.csv"
    _write_csv(source, [])
    output = tmp_path / "bundle"

    with pytest.raises(AISProcessingError, match="contains no data rows"):
        process_ais_csv(source, output, load_default_config())

    assert not output.exists()


def test_input_with_zero_valid_timestamps_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "invalid-timestamps.csv"
    _write_csv(
        source,
        [
            _row(BaseDateTime="malformed"),
            _row(MMSI="223456789", BaseDateTime="2024-99-99T00:00:00"),
        ],
    )
    output = tmp_path / "bundle"

    with pytest.raises(AISProcessingError, match="zero valid UTC timestamps"):
        process_ais_csv(source, output, load_default_config())

    assert not output.exists()


def test_multiple_utc_dates_are_rejected_without_an_output_bundle(
    tmp_path: Path,
) -> None:
    source = tmp_path / "two-days.csv"
    _write_csv(
        source,
        [_row(), _row(MMSI="223456789", BaseDateTime="2024-07-16T00:00:00")],
    )
    output = tmp_path / "bundle"

    with pytest.raises(AISProcessingError, match="multiple UTC dates"):
        process_ais_csv(source, output, load_default_config())

    assert not output.exists()


def test_partial_day_extract_reports_unverified_temporal_coverage(
    tmp_path: Path,
) -> None:
    source = tmp_path / "partial-day.csv"
    _write_csv(
        source,
        [
            _row(BaseDateTime="2024-07-15T06:15:00"),
            _row(MMSI="223456789", BaseDateTime="2024-07-15T06:45:00"),
        ],
    )
    output = tmp_path / "bundle"

    process_ais_csv(source, output, load_default_config())

    coverage = _report(output)["temporal_coverage"]
    assert coverage["observed_utc_date"] == "2024-07-15"
    assert coverage["earliest_valid_observed_at_utc"] == "2024-07-15T06:15:00Z"
    assert coverage["latest_valid_observed_at_utc"] == "2024-07-15T06:45:00Z"
    assert coverage["completeness"]["status"] == "unverified"


def test_run_metadata_records_real_injected_execution_timestamps(
    tmp_path: Path,
) -> None:
    source = tmp_path / "extract.csv"
    _write_csv(source, [_row()])
    output = tmp_path / "bundle"
    started_at = datetime(2026, 8, 27, 14, 30, 5, tzinfo=UTC)
    completed_at = datetime(2026, 8, 27, 14, 30, 8, tzinfo=UTC)

    process_ais_csv(
        source,
        output,
        load_default_config(),
        clock=_clock(started_at, completed_at),
    )

    metadata = json.loads((output / RUN_METADATA_FILENAME).read_text(encoding="utf-8"))
    assert metadata["run"]["started_at"] == "2026-08-27T14:30:05Z"
    assert metadata["run"]["completed_at"] == "2026-08-27T14:30:08Z"
    assert metadata["analytical_period"] == {
        "start_date": "2024-07-01",
        "end_date": "2024-11-30",
    }
    assert "real UTC execution timestamps" in metadata["execution_timestamp_semantics"]


def test_empty_cleaned_result_has_the_stable_parquet_schema(tmp_path: Path) -> None:
    source = tmp_path / "noncommercial.csv"
    _write_csv(source, [_row(VesselType="30")])
    output = tmp_path / "bundle"

    result = process_ais_csv(source, output, load_default_config())

    assert result.output_rows == 0
    parquet_path = (output / CLEANED_FILENAME).as_posix()
    with duckdb.connect() as connection:
        description = connection.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{parquet_path}')"
        ).fetchall()
    assert [column[0] for column in description] == [
        "mmsi",
        "observed_at_utc",
        "latitude",
        "longitude",
        "sog_knots",
        "cog_degrees",
        "heading_degrees",
        "vessel_type_code",
        "vessel_type_group",
        "length_m",
    ]


def test_cli_process_ais_success_and_failure_boundaries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "day.csv"
    _write_csv(source, [_row()])
    output = tmp_path / "bundle"
    config_path = (
        Path(__file__).parents[1]
        / "src"
        / "whale_vessel_analysis"
        / "default_config.toml"
    )

    assert (
        main(
            [
                "process-ais",
                "--input",
                str(source),
                "--output-dir",
                str(output),
                "--config",
                str(config_path),
            ]
        )
        == 0
    )
    success = capsys.readouterr()
    payload = json.loads(success.out)
    assert payload["output_rows"] == 1
    assert success.err == ""

    invalid = tmp_path / "invalid.csv"
    _write_csv(invalid, [_row()], header=("not", "the", "published", "header"))
    failed_output = tmp_path / "failed"
    assert (
        main(
            [
                "process-ais",
                "--input",
                str(invalid),
                "--output-dir",
                str(failed_output),
            ]
        )
        == 2
    )
    failure = capsys.readouterr()
    assert failure.out == ""
    assert "does not match the published schema" in failure.err
    assert not failed_output.exists()
