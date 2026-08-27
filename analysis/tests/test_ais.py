from __future__ import annotations

import csv
from pathlib import Path

import pytest

from whale_vessel_analysis.ais import (
    AIS_PUBLISHED_HEADER,
    AISSchemaError,
    AISValidationError,
    normalize_documented_measurement,
    validate_ais_csv,
    validate_header,
)
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


@pytest.mark.parametrize(
    ("field", "sentinel"),
    [("SOG", "102.3"), ("COG", 360.0), ("Heading", "511")],
)
def test_documented_sentinels_normalize_to_missing(
    field: str, sentinel: str | float
) -> None:
    assert normalize_documented_measurement(field, sentinel) is None


def test_non_sentinel_measurement_is_preserved() -> None:
    assert normalize_documented_measurement("SOG", "10.5") == 10.5


def test_unknown_sentinel_field_is_rejected() -> None:
    with pytest.raises(AISValidationError, match="no documented sentinel"):
        normalize_documented_measurement("Draft", "0")


def test_exact_published_header_is_accepted() -> None:
    validate_header(AIS_PUBLISHED_HEADER)


def test_missing_required_column_is_rejected() -> None:
    header = tuple(field for field in AIS_PUBLISHED_HEADER if field != "SOG")

    with pytest.raises(AISSchemaError, match="missing columns: SOG"):
        validate_header(header)


def test_reordered_header_is_rejected() -> None:
    header = list(AIS_PUBLISHED_HEADER)
    header[0], header[1] = header[1], header[0]

    with pytest.raises(AISSchemaError, match="published order"):
        validate_header(header)


def test_validates_utc_coordinates_and_all_sentinels(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.csv"
    _write_csv(path, [_row(SOG="102.3", COG="360", Heading="511")])

    result = validate_ais_csv(path, load_default_config().spatial.map_extent)

    assert result.passed
    assert result.total_rows == 1
    assert result.rows_in_map_extent == 1
    assert result.unavailable_sog_rows == 1
    assert result.unavailable_cog_rows == 1
    assert result.unavailable_heading_rows == 1
    assert result.invalid_sog_rows == 0
    assert result.invalid_cog_rows == 0
    assert result.invalid_heading_rows == 0


def test_reports_invalid_values_by_construction(tmp_path: Path) -> None:
    path = tmp_path / "invalid.csv"
    _write_csv(
        path,
        [
            _row(
                MMSI="012345678",
                BaseDateTime="not-a-timestamp",
                LAT="91",
                SOG="-1",
                COG="361",
                Heading="512",
                VesselType="100",
            ),
            _row(MMSI="223456789", VesselType=""),
        ],
    )

    result = validate_ais_csv(path, load_default_config().spatial.map_extent)

    assert not result.passed
    assert result.total_rows == 2
    assert result.rows_in_map_extent == 1
    assert result.invalid_timestamp_rows == 1
    assert result.invalid_coordinate_rows == 1
    assert result.invalid_mmsi_rows == 1
    assert result.invalid_sog_rows == 1
    assert result.invalid_cog_rows == 1
    assert result.invalid_heading_rows == 1
    assert result.missing_vessel_type_rows == 1
    assert result.invalid_vessel_type_rows == 1
    assert len(result.messages()) == 8


def test_empty_data_file_is_not_a_success(tmp_path: Path) -> None:
    path = tmp_path / "header-only.csv"
    _write_csv(path, [])

    result = validate_ais_csv(path, load_default_config().spatial.map_extent)

    assert not result.passed
    assert result.messages() == ["AIS input contains no data rows"]
