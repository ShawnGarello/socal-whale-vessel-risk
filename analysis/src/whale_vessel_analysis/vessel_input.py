"""Production vessel input using the shared, conservation-tested grid engine.

No candidate file is consumed or promoted. A fresh verified period is streamed
through the established allocation engine with the selected ADR 0018 rules.
Speed descriptors observe those same pieces without changing activity.
"""

from __future__ import annotations

import hashlib
import math
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pyarrow as pa
import pyarrow.parquet as pq

from whale_vessel_analysis import vessel_grid as engine
from whale_vessel_analysis.cleaned_ais_bundle import canonical_json, sha256_file
from whale_vessel_analysis.config import ProcessingConfig
from whale_vessel_analysis.multiday_ais import accepted_utc_dates
from whale_vessel_analysis.multiday_ais_relation import PeriodRelation
from whale_vessel_analysis.vessel_speed import (
    SpeedStatus,
    SpeedSummary,
    SpeedTotals,
    combine_summaries,
    endpoint_speed,
    speed_method,
)
from whale_vessel_analysis.whale_grid import TargetGridInspection

CONTRACT = "production_vessel_input_v1"
QUALITY_CONTRACT = "production_vessel_input_quality_v1"
LINEAGE_CONTRACT = "production_vessel_input_lineage_v1"
PROCESSING_VERSION = "1.0.0"
GROUPS = (*engine.VESSEL_GROUPS, engine.ALL_COMMERCIAL)


def selected_parameters() -> engine.VesselGridParameters:
    return engine.VesselGridParameters(
        maximum_gap_seconds=300.0,
        implied_speed_ceiling_knots=30.0,
        period_readiness_treatment=engine.REQUIRE_READY_PERIOD,
        edge_treatment=engine.EDGE_TREATMENT,
        support_treatment=engine.SUPPORT_TREATMENT,
    )


def selected_method() -> dict[str, object]:
    method = selected_parameters().to_dict()
    method["vessel_length_filter"] = {
        "status": "type-only-no-length-filter",
        "minimum_length_m": None,
        "reason": (
            "selected commercial types are not program participation or a "
            "300-GT population"
        ),
    }
    return {
        **method,
        "decision": "ADR 0018 selected configuration, 2026-09-05",
        "threshold_status": (
            "project choices; not independently validated universal thresholds"
        ),
        "speed_summary": speed_method(),
    }


class _ProductionAccumulator(engine._Accumulator):
    def __init__(self, grid: TargetGridInspection) -> None:
        super().__init__(grid, selected_parameters())
        self.speed = {
            group: [SpeedTotals() for _ in grid.cells] for group in engine.VESSEL_GROUPS
        }
        self.current_speed: tuple[float, SpeedStatus, float | None] | None = None
        self.speed_segment_counts = {
            group: {
                status: 0 for status in ("available", "unavailable", "inconsistent")
            }
            for group in engine.VESSEL_GROUPS
        }

    def retained_segment(
        self, row: Mapping[str, object], distance_m: float, implied_speed: float
    ) -> None:
        # Validate source values even for stationary or outside-support segments.
        status, sog = endpoint_speed(
            row.get("sog_knots"), row.get("next_sog_knots"), implied_speed
        )
        self.current_speed = (implied_speed, status, sog)
        group = engine._group_value(row.get("vessel_type_group"), "vessel group")
        self.speed_segment_counts[group][status] += 1

    def allocated_piece(
        self, group: engine.VesselGroup, cell_order: int, length: float
    ) -> None:
        super().allocated_piece(group, cell_order, length)
        assert self.current_speed is not None
        implied, status, sog = self.current_speed
        self.speed[group][cell_order].add(length, implied, status, sog)

    def speed_cells(self) -> tuple[dict[str, SpeedSummary], ...]:
        cells = []
        for order in range(len(self.target_grid.cells)):
            values = {
                group: self.speed[group][order].finish()
                for group in engine.VESSEL_GROUPS
            }
            values[engine.ALL_COMMERCIAL] = combine_summaries(list(values.values()))
            cells.append(values)
        return tuple(cells)


@dataclass(frozen=True)
class VesselInput:
    aggregation: engine.VesselGridDataset
    speeds: tuple[dict[str, SpeedSummary], ...]
    input_id: str
    quality: Mapping[str, object]


def build_vessel_input(
    relation: PeriodRelation,
    grid: TargetGridInspection,
    reference: engine.PeriodInputReference,
    config: ProcessingConfig,
    *,
    batch_size: int,
) -> VesselInput:
    """Require the actual full period and freshly compute production values."""
    if reference.period_input_readiness.get("status") != "ready":
        raise engine.VesselGridError("production input requires a ready period")
    if tuple(p.utc_date for p in relation.partitions) != accepted_utc_dates():
        raise engine.VesselGridError(
            "production input requires all exact accepted dates"
        )
    if reference.observational_completeness.get("status") != "unverified":
        raise engine.VesselGridError(
            "observational completeness must remain unverified"
        )
    accumulator = _ProductionAccumulator(grid)
    aggregation = engine.aggregate_vessel_grid(
        relation,
        grid,
        reference,
        selected_parameters(),
        config,
        batch_size=batch_size,
        _accumulator=accumulator,
    )
    speeds = accumulator.speed_cells()
    for cell, speed in zip(aggregation.cells, speeds, strict=True):
        for group in GROUPS:
            if not math.isclose(
                cell.vessel_km[group],
                speed[group].total_km,
                rel_tol=1e-12,
                abs_tol=1e-9,
            ):
                raise engine.VesselGridError(
                    "speed distance categories do not conserve activity"
                )
    quality = dict(aggregation.quality)
    quality.pop("grid_id")
    quality.update(
        {
            "contract": QUALITY_CONTRACT,
            "processing_version": PROCESSING_VERSION,
            "status": "production configuration; visual validation recorded separately",
            "parameters": selected_method(),
            "aggregation_engine_version": engine.VESSEL_GRID_PROCESSING_VERSION,
            "speed_distance_conservation_passed": True,
            "speed_retained_segment_counts": {
                **accumulator.speed_segment_counts,
                engine.ALL_COMMERCIAL: {
                    status: sum(
                        counts[status]
                        for counts in accumulator.speed_segment_counts.values()
                    )
                    for status in ("available", "unavailable", "inconsistent")
                },
            },
            "speed_totals": {
                group: combine_summaries([cell[group] for cell in speeds]).to_dict()
                for group in GROUPS
            },
        }
    )
    limits = dict(cast(Mapping[str, object], quality["scope_and_limitations"]))
    limits["analytical_domain"] = (
        "modeled-whale water support; receiver reporting mask is separate "
        "downstream work"
    )
    quality["scope_and_limitations"] = limits
    identity = engine._identity_material(
        cells=aggregation.cells,
        target_grid=grid,
        period_input=reference,
        parameters=selected_parameters(),
        partitions=aggregation.partitions,
        quality=quality,
        configuration_sha256=config.digest(),
    )
    identity.update(
        {
            "contract": CONTRACT,
            "processing_version": PROCESSING_VERSION,
            "parameters": selected_method(),
            "speeds": [{g: cell[g].to_dict() for g in GROUPS} for cell in speeds],
        }
    )
    input_id = (
        "vessel-input-"
        + hashlib.sha256(canonical_json(identity).encode()).hexdigest()[:24]
    )
    quality["input_id"] = input_id
    return VesselInput(aggregation, speeds, input_id, quality)


def vessel_input_table(dataset: VesselInput) -> pa.Table:
    """Reuse exact spatial serialization, attach a distinct production contract."""
    table = engine._table(dataset.aggregation)
    metadata = dict(table.schema.metadata or {})
    product = engine._dataset_metadata(dataset.aggregation)
    product.update(
        {
            "contract": CONTRACT,
            "processing_version": PROCESSING_VERSION,
            "status": "production configuration; visual validation recorded separately",
            "grid_id": dataset.input_id,
            "parameters": selected_method(),
            "quality": dict(dataset.quality),
        }
    )
    units = dict(cast(Mapping[str, object], product["units"]))
    units.update(
        {
            "reported_sog_mean_knots": "distance-weighted endpoint reported SOG, knots",
            "implied_speed_mean_knots": (
                "distance-weighted segment-implied speed, knots"
            ),
            "sog_available_km": "allocated km with usable endpoint mean",
            "sog_unavailable_km": "allocated km with either endpoint SOG unavailable",
            "sog_inconsistent_km": (
                "allocated km excluded from reported mean by consistency screen"
            ),
        }
    )
    product["units"] = units
    metadata[b"whale_vessel_analysis"] = canonical_json(product).encode()
    for field in SpeedSummary(0, 0, 0, 0, 0).to_dict():
        for group in GROUPS:
            table = table.append_column(
                pa.field(f"{field}_{group}", pa.float64(), nullable="mean" in field),
                pa.array(
                    [cell[group].to_dict()[field] for cell in dataset.speeds],
                    pa.float64(),
                ),
            )
    return table.replace_schema_metadata(metadata)


def write_vessel_input(
    dataset: VesselInput,
    output_directory: Path,
    *,
    relation: PeriodRelation,
    started_at: datetime,
) -> dict[str, object]:
    """Publish a fresh atomic bundle; retain partial evidence on failure."""
    if started_at.utcoffset() != UTC.utcoffset(started_at):
        raise engine.VesselGridError("started_at must be timezone-aware UTC")
    target = engine._validate_output_directory(output_directory, False)
    engine.validate_input_output_separation(
        target,
        [
            dataset.aggregation.period_input.manifest_path,
            dataset.aggregation.target_grid.path,
            *(p.cleaned_path for p in relation.partitions),
        ],
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.temporary-", dir=target.parent)
    )
    grid_path = temporary / engine.VESSEL_GRID_FILENAME
    quality_path = temporary / engine.QUALITY_REPORT_FILENAME
    lineage_path = temporary / engine.RUN_METADATA_FILENAME
    try:
        table = vessel_input_table(dataset)
        pq.write_table(
            table,
            grid_path,
            compression="zstd",
            compression_level=9,
            use_dictionary=False,
            write_statistics=True,
            version="2.6",
            data_page_version="2.0",
            row_group_size=1024,
        )
        if not pq.read_table(grid_path).equals(table, check_metadata=True):
            raise engine.VesselGridError("production GeoParquet read-back differs")
        grid_hash = sha256_file(grid_path)
        quality = {
            **dataset.quality,
            "output": {
                "contract": CONTRACT,
                "input_id": dataset.input_id,
                "rows": len(dataset.aggregation.cells),
                "sha256": grid_hash,
            },
        }
        engine._write_json(quality_path, quality)
        quality_hash = sha256_file(quality_path)
        # Retain the shared lineage's verified partitions and execution settings;
        # name production steps and outputs explicitly, with the actual versions.
        lineage = engine._lineage_document(
            dataset=dataset.aggregation,
            relation=relation,
            grid_path=target / grid_path.name,
            grid_sha256=grid_hash,
            quality_path=target / quality_path.name,
            quality_sha256=quality_hash,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
        lineage.update(
            {
                "contract": LINEAGE_CONTRACT,
                "processing_version": PROCESSING_VERSION,
                "status": "production configuration",
                "method_status": (
                    "ADR 0018 selected rules; spatial validation recorded separately"
                ),
                "parameters": selected_method(),
            }
        )
        run = cast(dict[str, object], lineage["run"])
        run["run_id"] = dataset.input_id
        run["steps"] = [
            {
                "name": "shared-whole-period-vessel-grid-aggregation",
                "version": engine.VESSEL_GRID_PROCESSING_VERSION,
            },
            {
                "name": "production-vessel-input-with-separate-speed",
                "version": PROCESSING_VERSION,
            },
        ]
        outputs = cast(list[dict[str, object]], run["outputs"])
        outputs[0]["artifact_id"] = "production-vessel-input"
        outputs[1]["artifact_id"] = "production-vessel-input-quality"
        settings = cast(dict[str, object], lineage["execution_settings"])
        settings["identity_note"] = (
            "operational settings, clocks and paths do not participate in "
            "production identity"
        )
        engine._write_json(lineage_path, lineage)
        # Never overwrite an existing destination, including a concurrent arrival.
        engine._publish_bundle(temporary, target, False)
    except Exception as exc:
        raise engine.VesselGridError(
            f"production bundle failed; retained evidence at {temporary}: {exc}"
        ) from exc
    return {
        "contract": CONTRACT,
        "input_id": dataset.input_id,
        "grid_sha256": grid_hash,
        "quality_sha256": quality_hash,
        "lineage_sha256": sha256_file(target / lineage_path.name),
        "output_directory": str(target),
        "rows": table.num_rows,
    }
