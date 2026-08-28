from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import pytest

from whale_vessel_analysis.ais import AIS_PUBLISHED_HEADER
from whale_vessel_analysis.ais_retrieval import (
    AISRetrievalError,
    RequestBounds,
    RetrievalRequest,
    SourceHttpMetadata,
    attach_cleaning_reference,
    inspect_ais_artifact,
    load_retrieval_manifest,
    materialize_verified_csv_bundle,
    record_verified_attempt,
)

EXPECTED_DATE = date(2024, 7, 15)


def _row(
    timestamp: str = "2024-07-15T00:00:00", *, mmsi: str = "123456789"
) -> list[str]:
    values = {
        "MMSI": mmsi,
        "BaseDateTime": timestamp,
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
    return [values[field] for field in AIS_PUBLISHED_HEADER]


def _csv_bytes(
    rows: list[list[str]], header: tuple[str, ...] = AIS_PUBLISHED_HEADER
) -> bytes:
    import io

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    path.write_bytes(_csv_bytes(rows))


def _write_zip(
    path: Path,
    members: dict[str, bytes],
    *,
    compression: int = zipfile.ZIP_DEFLATED,
) -> None:
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def _request(
    source_filename: str, source_reference: str = "author-supplied delivery"
) -> RetrievalRequest:
    return RetrievalRequest(
        expected_utc_date=EXPECTED_DATE,
        route="accessais",
        request_id="accessais-2024-07-15-bbox-v1",
        source_reference=source_reference,
        request_parameters=RequestBounds(
            from_date=EXPECTED_DATE,
            through_date=EXPECTED_DATE,
            lon_min=-122.0,
            lat_min=32.0,
            lon_max=-117.0,
            lat_max=35.0,
        ),
        source_filename=source_filename,
        retrieved_at_utc=datetime(2026, 8, 27, 20, 0, tzinfo=UTC),
        source_http_metadata=SourceHttpMetadata(etag='"synthetic"'),
    )


def test_valid_single_day_csv_is_identified_by_content(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.unknown"
    _write_csv(artifact, [_row(), _row("2024-07-15T23:59:59", mmsi="223456789")])

    inspection = inspect_ais_artifact(
        artifact, EXPECTED_DATE, source_content_length=artifact.stat().st_size
    )

    assert inspection.container == "csv"
    assert inspection.byte_size == artifact.stat().st_size
    assert inspection.sha256 == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert inspection.source_content_length_match is True
    assert inspection.date_inspection.row_count == 2
    assert inspection.date_inspection.observed_utc_dates == ("2024-07-15",)


def test_valid_single_day_archive_checks_members_and_crc(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.bin"
    _write_zip(
        artifact,
        {
            "delivery/readme.txt": b"synthetic metadata\n",
            "delivery/points.csv": _csv_bytes([_row()]),
        },
    )

    inspection = inspect_ais_artifact(
        artifact, EXPECTED_DATE, source_content_length=artifact.stat().st_size
    )

    assert inspection.container == "zip"
    assert inspection.crc_valid is True
    assert inspection.archive_members == (
        "delivery/readme.txt",
        "delivery/points.csv",
    )
    assert inspection.selected_csv_member == "delivery/points.csv"


def test_manifest_serialization_is_deterministic(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.csv"
    _write_csv(artifact, [_row()])
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)
    first = tmp_path / "first" / "manifest.json"
    second = tmp_path / "second" / "manifest.json"

    record_verified_attempt(first, _request("delivery.csv"), inspection)
    record_verified_attempt(second, _request("delivery.csv"), inspection)

    assert first.read_bytes() == second.read_bytes()
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["observational_completeness"]["status"] == "unverified"
    assert payload["entries"][0]["cleaning_compatibility"]["status"] == (
        "header_compatible_not_exercised"
    )


def test_cleaning_reference_cannot_upgrade_observational_completeness(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "delivery.csv"
    manifest_path = tmp_path / "manifest.json"
    _write_csv(artifact, [_row()])
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)
    record_verified_attempt(manifest_path, _request("delivery.csv"), inspection)
    original = manifest_path.read_bytes()

    with pytest.raises(
        AISRetrievalError,
        match="must preserve unverified observational completeness",
    ):
        attach_cleaning_reference(
            manifest_path,
            EXPECTED_DATE,
            {"cleaner_reported_completeness": "verified"},
        )

    assert manifest_path.read_bytes() == original
    stored = load_retrieval_manifest(manifest_path)
    entry = cast(list[dict[str, object]], stored["entries"])[0]
    completeness = cast(dict[str, object], entry["observational_completeness"])
    assert completeness["status"] == "unverified"


def test_one_verified_date_leaves_other_analytical_dates_missing(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "delivery.zip"
    manifest_path = tmp_path / "manifest.json"
    _write_zip(artifact, {"points.csv": _csv_bytes([_row()])})
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)

    update = record_verified_attempt(
        manifest_path, _request("delivery.zip"), inspection
    )

    expected = cast(list[str], update.manifest["expected_utc_dates"])
    summary = cast(dict[str, object], update.manifest["period_retrieval"])
    missing = cast(list[str], summary["missing_expected_utc_dates"])
    assert len(expected) == 153
    assert expected[0] == "2024-07-01"
    assert expected[-1] == "2024-11-30"
    assert summary["status"] == "not_verified"
    assert len(missing) == 152
    assert "2024-07-15" not in missing


def test_plain_csv_without_independent_length_keeps_byte_completeness_unverified(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "delivery.csv"
    manifest_path = tmp_path / "manifest.json"
    _write_csv(artifact, [_row()])
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)

    update = record_verified_attempt(
        manifest_path, _request("delivery.csv"), inspection
    )

    entry = cast(dict[str, object], cast(list[object], update.manifest["entries"])[0])
    retrieval = cast(dict[str, object], entry["retrieval_verification"])
    completeness = cast(dict[str, object], retrieval["byte_completeness"])
    assert entry["status"] == "retrieved"
    assert completeness["status"] == "unverified"
    summary = cast(dict[str, object], update.manifest["period_retrieval"])
    missing = cast(list[str], summary["missing_expected_utc_dates"])
    assert summary["status"] == "not_verified"
    assert len(missing) == 153
    assert "2024-07-15" in missing


def test_missing_source_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(AISRetrievalError, match="does not exist"):
        inspect_ais_artifact(tmp_path / "missing.csv", EXPECTED_DATE)


def test_header_only_csv_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "empty.csv"
    artifact.write_bytes(_csv_bytes([]))

    with pytest.raises(AISRetrievalError, match="zero data rows"):
        inspect_ais_artifact(artifact, EXPECTED_DATE)


def test_corrupt_zip_crc_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "corrupt.zip"
    content = _csv_bytes([_row()])
    _write_zip(
        artifact,
        {"points.csv": content},
        compression=zipfile.ZIP_STORED,
    )
    damaged = bytearray(artifact.read_bytes())
    position = damaged.index(content) + len(content) - 2
    damaged[position] ^= 1
    artifact.write_bytes(damaged)

    with pytest.raises(AISRetrievalError, match="CRC validation failed"):
        inspect_ais_artifact(artifact, EXPECTED_DATE)


def test_archive_path_traversal_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "unsafe.zip"
    _write_zip(artifact, {"../points.csv": _csv_bytes([_row()])})

    with pytest.raises(AISRetrievalError, match="unsafe archive member"):
        inspect_ais_artifact(artifact, EXPECTED_DATE)


@pytest.mark.parametrize(
    ("members", "message"),
    [
        ({"readme.txt": b"no CSV\n"}, "no CSV member"),
        (
            {"first.csv": _csv_bytes([_row()]), "second.csv": _csv_bytes([_row()])},
            "multiple ambiguous CSV members",
        ),
    ],
)
def test_archive_requires_one_unambiguous_csv_member(
    tmp_path: Path, members: dict[str, bytes], message: str
) -> None:
    artifact = tmp_path / "ambiguous.zip"
    _write_zip(artifact, members)

    with pytest.raises(AISRetrievalError, match=message):
        inspect_ais_artifact(artifact, EXPECTED_DATE)


def test_wrong_header_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "wrong-header.csv"
    wrong_header = tuple(
        field for field in AIS_PUBLISHED_HEADER if field != "TransceiverClass"
    )
    artifact.write_bytes(_csv_bytes([_row()[:-1]], wrong_header))

    with pytest.raises(AISRetrievalError, match="missing columns"):
        inspect_ais_artifact(artifact, EXPECTED_DATE)


@pytest.mark.parametrize(
    "timestamps",
    [
        ["2024-07-16T00:00:00"],
        ["2024-07-15T00:00:00", "2024-07-16T00:00:00"],
    ],
)
def test_unexpected_or_multiple_utc_dates_are_rejected(
    tmp_path: Path, timestamps: list[str]
) -> None:
    artifact = tmp_path / "wrong-date.csv"
    _write_csv(
        artifact,
        [
            _row(timestamp, mmsi=f"{index + 1}23456789")
            for index, timestamp in enumerate(timestamps)
        ],
    )

    with pytest.raises(AISRetrievalError, match="expected UTC date 2024-07-15"):
        inspect_ais_artifact(artifact, EXPECTED_DATE)


def test_duplicate_current_manifest_entry_is_rejected(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.csv"
    manifest_path = tmp_path / "manifest.json"
    _write_csv(artifact, [_row()])
    inspection = inspect_ais_artifact(
        artifact, EXPECTED_DATE, source_content_length=artifact.stat().st_size
    )
    record_verified_attempt(manifest_path, _request("delivery.csv"), inspection)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["entries"].append(payload["entries"][0])
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AISRetrievalError, match="duplicate current"):
        load_retrieval_manifest(manifest_path)


def test_identical_retry_reuses_current_evidence(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.csv"
    manifest_path = tmp_path / "manifest.json"
    _write_csv(artifact, [_row()])
    inspection = inspect_ais_artifact(
        artifact, EXPECTED_DATE, source_content_length=artifact.stat().st_size
    )

    record_verified_attempt(manifest_path, _request("delivery.csv"), inspection)
    update = record_verified_attempt(
        manifest_path, _request("delivery.csv"), inspection
    )

    entry = cast(dict[str, object], cast(list[object], update.manifest["entries"])[0])
    assert update.outcome == "identical_retry"
    assert entry["status"] == "verified"
    attempts = cast(list[dict[str, object]], entry["attempt_history"])
    assert [attempt["outcome"] for attempt in attempts] == [
        "verified",
        "identical_reuse",
    ]


def test_conflicting_retry_preserves_original_identity(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    manifest_path = tmp_path / "manifest.json"
    _write_csv(first, [_row()])
    _write_csv(second, [_row("2024-07-15T00:01:00")])
    first_inspection = inspect_ais_artifact(
        first, EXPECTED_DATE, source_content_length=first.stat().st_size
    )
    second_inspection = inspect_ais_artifact(
        second, EXPECTED_DATE, source_content_length=second.stat().st_size
    )

    record_verified_attempt(manifest_path, _request("first.csv"), first_inspection)
    update = record_verified_attempt(
        manifest_path, _request("second.csv"), second_inspection
    )

    entry = cast(dict[str, object], cast(list[object], update.manifest["entries"])[0])
    retrieval = cast(dict[str, object], entry["retrieval_verification"])
    identity = cast(dict[str, object], retrieval["identity"])
    assert update.outcome == "conflict"
    assert entry["status"] == "conflict"
    assert identity["sha256"] == first_inspection.sha256


def test_source_reference_redacts_email_token_and_delivery_path(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.csv"
    manifest_path = tmp_path / "manifest.json"
    _write_csv(artifact, [_row()])
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)
    address = "author" + chr(64) + "example.invalid"
    secret = "synthetic-secret-value"
    source_reference = (
        f"https://delivery.invalid/orders/private?token={secret}&email={address}"
    )

    record_verified_attempt(
        manifest_path,
        _request("delivery.csv", source_reference=source_reference),
        inspection,
    )

    serialized = manifest_path.read_text(encoding="utf-8")
    assert address not in serialized
    assert secret not in serialized
    assert "/orders/private" not in serialized
    assert "redacted-delivery" in serialized


def test_extraction_refuses_data_raw_destination(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.zip"
    _write_zip(artifact, {"points.csv": _csv_bytes([_row()])})
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)

    with pytest.raises(AISRetrievalError, match="under data/raw"):
        materialize_verified_csv_bundle(
            artifact,
            inspection,
            EXPECTED_DATE,
            tmp_path / "data" / "raw" / "bundle",
        )


def test_extraction_refuses_arbitrary_existing_destination(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.zip"
    output = tmp_path / "data" / "interim" / "bundle"
    _write_zip(artifact, {"points.csv": _csv_bytes([_row()])})
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)
    output.mkdir(parents=True)
    (output / "unrelated.txt").write_text("preserve me", encoding="utf-8")

    with pytest.raises(AISRetrievalError, match="complete compatible"):
        materialize_verified_csv_bundle(artifact, inspection, EXPECTED_DATE, output)

    assert (output / "unrelated.txt").read_text(encoding="utf-8") == "preserve me"


def test_compatible_extraction_bundle_is_reused(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.zip"
    output = tmp_path / "data" / "interim" / "bundle"
    _write_zip(artifact, {"nested/points.csv": _csv_bytes([_row()])})
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)

    first = materialize_verified_csv_bundle(artifact, inspection, EXPECTED_DATE, output)
    second = materialize_verified_csv_bundle(
        artifact, inspection, EXPECTED_DATE, output
    )

    assert not first.reused
    assert second.reused
    assert first.csv_sha256 == second.csv_sha256


def test_extraction_rejects_artifact_swapped_after_inspection(tmp_path: Path) -> None:
    artifact = tmp_path / "delivery.zip"
    output = tmp_path / "data" / "interim" / "bundle"
    _write_zip(artifact, {"points.csv": _csv_bytes([_row()])})
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)
    _write_zip(
        artifact,
        {"points.csv": _csv_bytes([_row("2024-07-15T00:01:00")])},
    )

    with pytest.raises(AISRetrievalError, match="no longer matches"):
        materialize_verified_csv_bundle(artifact, inspection, EXPECTED_DATE, output)

    assert not output.exists()


def test_extraction_publication_failure_is_atomic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "delivery.zip"
    output = tmp_path / "data" / "interim" / "bundle"
    _write_zip(artifact, {"points.csv": _csv_bytes([_row()])})
    inspection = inspect_ais_artifact(artifact, EXPECTED_DATE)
    original_rename = Path.rename

    def fail_publication(path: Path, target: Path) -> Path:
        if path.name.startswith(f".{output.name}.temporary-"):
            raise OSError("synthetic publication failure")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_publication)

    with pytest.raises(AISRetrievalError, match="synthetic publication failure"):
        materialize_verified_csv_bundle(artifact, inspection, EXPECTED_DATE, output)

    assert not output.exists()
    assert list(output.parent.glob(f".{output.name}.temporary-*")) == []
