"""Regression tests for the display export's public-safety boundaries.

Two defects motivate this module.

The manifest used to copy the source artifact's `method` and `inputs` objects
wholesale. That metadata is producer-controlled, so anything a producer put
there reached the supposedly sanitized public manifest. It is now rebuilt field
by field from a named, validated allowlist.

The destination guard used to protect only this checkout's `data/raw` and to
permit any path outside this checkout's root, which accepted another worktree's
`data/raw`. Destinations are now an allowlist anchored to this checkout, with
raw-data and Git locations refused by directory shape wherever they appear.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pytest

from whale_display_fixtures import REMOVE, _cell, _prepare
from whale_vessel_analysis.whale_display_export import (
    APPROVED_OUTPUT_ROOTS,
    MAX_PUBLIC_TEXT_LENGTH,
    PUBLIC_INPUT_CHECKSUM_FIELDS,
    PUBLIC_METHOD_NUMBER_FIELDS,
    PUBLIC_METHOD_TEXT_FIELDS,
    WhaleDisplayExportInputError,
    WhaleDisplayExportOutputError,
    build_export,
    build_manifest,
    load_source,
    reject_protected_location,
    validate_output_target,
)
from whale_vessel_analysis.whale_grid import LINEAGE_SUFFIX

EXPORTED_AT = datetime(2026, 9, 6, tzinfo=UTC)

# Values shaped like somewhere on a filesystem or network. None of them is a
# real path or a real credential; they exist so a leak would be unmistakable.
LOCATION_SHAPED_VALUES = (
    "C:\\Users\\someone\\private\\notes.txt",
    "\\\\server\\share\\notes.txt",
    "https://internal.example.invalid/secret",
    "/home/someone/.config/credentials",
    "~/secrets/key.txt",
    "file:///c:/keys.txt",
)


def _manifest_text(tmp_path: Path, **table_kwargs: object) -> str:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)], **table_kwargs)
    export = build_export(load_source(source_path, expected_sha256=digest))
    return json.dumps(
        build_manifest(
            export,
            output_name="blue-whale-density.geojson",
            exported_at=EXPORTED_AT,
        )
    )


# --------------------------------------------------------------------------
# Public metadata is rebuilt, not copied
# --------------------------------------------------------------------------


def test_drops_unlisted_source_metadata_instead_of_copying_it(tmp_path: Path) -> None:
    serialized = _manifest_text(
        tmp_path,
        metadata_overrides={
            "method.operator_notes": "C:\\Users\\someone\\private\\keys.txt",
            "method.internal_host": "https://internal.example.invalid/build/42",
            "inputs.api_key": "NOT-A-REAL-TOKEN-0000000000000000000000",
            "inputs.operator_home": "/home/someone/.arcgis/credentials",
        },
    )

    for smuggled in (
        "operator_notes",
        "internal_host",
        "api_key",
        "operator_home",
        "private",
        "NOT-A-REAL-TOKEN",
        "credentials",
        "internal.example.invalid",
    ):
        assert smuggled not in serialized


def test_publishes_exactly_the_named_method_and_input_fields(tmp_path: Path) -> None:
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    source = load_source(source_path, expected_sha256=digest)

    method = source.dataset_metadata["method"]
    inputs = source.dataset_metadata["inputs"]
    assert isinstance(method, dict)
    assert isinstance(inputs, dict)
    assert set(method) == {*PUBLIC_METHOD_TEXT_FIELDS, *PUBLIC_METHOD_NUMBER_FIELDS}
    assert set(inputs) == set(PUBLIC_INPUT_CHECKSUM_FIELDS)


@pytest.mark.parametrize("poisoned", LOCATION_SHAPED_VALUES)
def test_rejects_a_named_method_field_shaped_like_a_location(
    tmp_path: Path, poisoned: str
) -> None:
    source_path, digest = _prepare(
        tmp_path, [_cell(0, 0)], metadata_overrides={"method.name": poisoned}
    )

    with pytest.raises(WhaleDisplayExportInputError, match=r"method.name"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_an_over_long_named_method_field(tmp_path: Path) -> None:
    source_path, digest = _prepare(
        tmp_path,
        [_cell(0, 0)],
        metadata_overrides={"method.name": "a" * (MAX_PUBLIC_TEXT_LENGTH + 1)},
    )

    with pytest.raises(WhaleDisplayExportInputError, match="exceeds"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_control_character_in_a_named_method_field(tmp_path: Path) -> None:
    source_path, digest = _prepare(
        tmp_path,
        [_cell(0, 0)],
        metadata_overrides={"method.name": "abundance\u0000conserving"},
    )

    with pytest.raises(WhaleDisplayExportInputError, match="control character"):
        load_source(source_path, expected_sha256=digest)


def test_rejects_a_blank_named_method_field(tmp_path: Path) -> None:
    source_path, digest = _prepare(
        tmp_path, [_cell(0, 0)], metadata_overrides={"method.name": "   "}
    )

    with pytest.raises(WhaleDisplayExportInputError, match="is blank"):
        load_source(source_path, expected_sha256=digest)


@pytest.mark.parametrize("field", PUBLIC_METHOD_TEXT_FIELDS)
def test_rejects_a_missing_named_method_field(tmp_path: Path, field: str) -> None:
    source_path, digest = _prepare(
        tmp_path, [_cell(0, 0)], metadata_overrides={f"method.{field}": REMOVE}
    )

    with pytest.raises(WhaleDisplayExportInputError, match="is absent"):
        load_source(source_path, expected_sha256=digest)


@pytest.mark.parametrize("field", PUBLIC_METHOD_TEXT_FIELDS)
def test_rejects_a_mistyped_named_method_field(tmp_path: Path, field: str) -> None:
    source_path, digest = _prepare(
        tmp_path, [_cell(0, 0)], metadata_overrides={f"method.{field}": 12}
    )

    with pytest.raises(WhaleDisplayExportInputError, match="must be a string"):
        load_source(source_path, expected_sha256=digest)


@pytest.mark.parametrize("field", PUBLIC_METHOD_NUMBER_FIELDS)
def test_rejects_a_missing_method_tolerance(tmp_path: Path, field: str) -> None:
    source_path, digest = _prepare(
        tmp_path, [_cell(0, 0)], metadata_overrides={f"method.{field}": REMOVE}
    )

    with pytest.raises(WhaleDisplayExportInputError, match="is absent"):
        load_source(source_path, expected_sha256=digest)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_rejects_a_non_finite_method_tolerance(tmp_path: Path, value: float) -> None:
    source_path, digest = _prepare(
        tmp_path,
        [_cell(0, 0)],
        metadata_overrides={"method.coverage_exact_tolerance_m2": value},
    )

    with pytest.raises(WhaleDisplayExportInputError, match="not finite"):
        load_source(source_path, expected_sha256=digest)


@pytest.mark.parametrize("value", ["1.0", True, None])
def test_rejects_a_mistyped_method_tolerance(tmp_path: Path, value: object) -> None:
    source_path, digest = _prepare(
        tmp_path,
        [_cell(0, 0)],
        metadata_overrides={"method.coverage_exact_tolerance_m2": value},
    )

    with pytest.raises(WhaleDisplayExportInputError, match="must be a number"):
        load_source(source_path, expected_sha256=digest)


@pytest.mark.parametrize("field", PUBLIC_INPUT_CHECKSUM_FIELDS)
def test_rejects_an_input_checksum_that_is_not_a_sha256(
    tmp_path: Path, field: str
) -> None:
    source_path, digest = _prepare(
        tmp_path,
        [_cell(0, 0)],
        metadata_overrides={f"inputs.{field}": "../../etc/passwd"},
    )

    with pytest.raises(WhaleDisplayExportInputError, match="hexadecimal"):
        load_source(source_path, expected_sha256=digest)


@pytest.mark.parametrize("block", ["method", "inputs"])
def test_rejects_a_non_object_metadata_block(tmp_path: Path, block: str) -> None:
    source_path, digest = _prepare(
        tmp_path, [_cell(0, 0)], metadata_overrides={block: "not-an-object"}
    )

    with pytest.raises(
        WhaleDisplayExportInputError, match=f"{block} must be an object"
    ):
        load_source(source_path, expected_sha256=digest)


@pytest.mark.parametrize(
    "run_id",
    [
        "C:\\Users\\someone\\private\\run",
        "run id with spaces",
        "a" * 65,
        "",
        "-leading-dash",
        "../escape",
    ],
)
def test_rejects_an_unsafe_generation_run_identifier(
    tmp_path: Path, run_id: str
) -> None:
    """The run id is lifted out of producer-written lineage, so it is validated."""
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    sidecar = source_path.with_suffix(source_path.suffix + LINEAGE_SUFFIX)
    document = json.loads(sidecar.read_text(encoding="utf-8"))
    document["run"]["run_id"] = run_id
    sidecar.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")

    with pytest.raises(WhaleDisplayExportInputError, match="run_id"):
        load_source(source_path, expected_sha256=digest)


def test_manifest_serialization_refuses_non_finite_numbers(tmp_path: Path) -> None:
    """JSON has no NaN or Infinity, so a public artifact must never carry one."""
    source_path, digest = _prepare(tmp_path, [_cell(0, 0)])
    export = build_export(load_source(source_path, expected_sha256=digest))
    manifest = build_manifest(
        export, output_name="blue-whale-density.geojson", exported_at=EXPORTED_AT
    )
    manifest["output"] = {"corrupted": math.nan}

    with pytest.raises(ValueError, match="Out of range float"):
        json.dumps(manifest, allow_nan=False)


# --------------------------------------------------------------------------
# Destinations are an allowlist anchored to this checkout
# --------------------------------------------------------------------------


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_approved_roots_are_this_checkouts_ignored_generated_directories() -> None:
    relative = [
        root.relative_to(_project_root()).as_posix() for root in APPROVED_OUTPUT_ROOTS
    ]

    assert relative == ["data/derived", "data/interim", "web/public/layers"]


def test_refuses_a_destination_outside_the_approved_roots(tmp_path: Path) -> None:
    with pytest.raises(WhaleDisplayExportOutputError, match="approved roots"):
        validate_output_target(tmp_path / "anywhere.geojson")


def test_refuses_another_checkouts_raw_directory() -> None:
    """A sibling worktree shares the layout, so its raw data must be refused."""
    project_root = _project_root()
    sibling = project_root.parent / f"{project_root.name}-another-checkout"

    with pytest.raises(WhaleDisplayExportOutputError, match="raw data"):
        validate_output_target(sibling / "data" / "raw" / "leak.geojson")


@pytest.mark.parametrize(
    "relative",
    [
        Path("data") / "interim" / "x.geojson",
        Path("data") / "derived" / "x.geojson",
        Path("web") / "public" / "layers" / "x.geojson",
        Path("docs") / "x.geojson",
    ],
)
def test_refuses_another_checkouts_directories(relative: Path) -> None:
    project_root = _project_root()
    sibling = project_root.parent / f"{project_root.name}-another-checkout"

    with pytest.raises(WhaleDisplayExportOutputError, match="approved roots"):
        validate_output_target(sibling / relative)


def test_refuses_this_checkouts_tracked_directories() -> None:
    project_root = _project_root()

    for relative in (
        Path("docs") / "x.geojson",
        Path("web") / "public" / "x.geojson",
        Path("analysis") / "x.geojson",
    ):
        with pytest.raises(WhaleDisplayExportOutputError, match="approved roots"):
            validate_output_target(project_root / relative)


def test_accepts_this_checkouts_approved_roots() -> None:
    for root in APPROVED_OUTPUT_ROOTS:
        validate_output_target(root / "nested" / "blue-whale-density.geojson")


def test_refuses_raw_and_git_locations_by_shape_anywhere(tmp_path: Path) -> None:
    """Defence in depth: refused even where the allowlist would otherwise allow."""
    with pytest.raises(WhaleDisplayExportOutputError, match="raw data"):
        reject_protected_location(tmp_path / "any" / "data" / "raw" / "x.geojson")
    with pytest.raises(WhaleDisplayExportOutputError, match="Git metadata"):
        reject_protected_location(tmp_path / "repo" / ".git" / "x.geojson")

    # A caller-supplied approved root cannot authorize either of them.
    with pytest.raises(WhaleDisplayExportOutputError, match="raw data"):
        validate_output_target(
            tmp_path / "data" / "raw" / "x.geojson", approved_roots=[tmp_path]
        )
    with pytest.raises(WhaleDisplayExportOutputError, match="Git metadata"):
        validate_output_target(
            tmp_path / ".git" / "x.geojson", approved_roots=[tmp_path]
        )
