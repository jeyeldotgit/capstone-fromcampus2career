from __future__ import annotations

"""Baseline skill decay detection from historical SDI snapshots."""

from datetime import date
from uuid import UUID

import polars as pl
from pydantic import BaseModel, Field

PERSISTED_PRECISION = 4
MIN_SNAPSHOTS = 3
DECAY_SLOPE_THRESHOLD = -0.10
MIN_CONFIDENCE = 0.70


class HistoricalSdiSnapshotRow(BaseModel):
    role_id: UUID
    skill_id: UUID
    demand_index: float = Field(ge=0.0, le=1.0)
    snapshot_date: date
    requirement_version: int = Field(gt=0)


class DecaySignalComputationRow(BaseModel):
    role_id: UUID
    skill_id: UUID
    decay_rate: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    requirement_version: int = Field(gt=0)


def detect_decay_signals(
    rows: list[HistoricalSdiSnapshotRow],
    *,
    min_snapshots: int = MIN_SNAPSHOTS,
    slope_threshold: float = DECAY_SLOPE_THRESHOLD,
    min_confidence: float = MIN_CONFIDENCE,
) -> list[DecaySignalComputationRow]:
    validated_rows = [HistoricalSdiSnapshotRow.model_validate(row) for row in rows]
    if len(validated_rows) == 0:
        return []

    frame = pl.DataFrame(
        [
            {
                "role_id": str(row.role_id),
                "skill_id": str(row.skill_id),
                "demand_index": row.demand_index,
                "snapshot_date": row.snapshot_date.isoformat(),
                "requirement_version": row.requirement_version,
            }
            for row in validated_rows
        ],
        schema={
            "role_id": pl.String,
            "skill_id": pl.String,
            "demand_index": pl.Float64,
            "snapshot_date": pl.String,
            "requirement_version": pl.Int64,
        },
    )

    signals: list[DecaySignalComputationRow] = []
    for pair in frame.select(["role_id", "skill_id"]).unique().sort(["role_id", "skill_id"]).iter_rows(named=True):
        pair_rows = (
            frame.filter(
                (pl.col("role_id") == pair["role_id"]) & (pl.col("skill_id") == pair["skill_id"])
            )
            .sort(["snapshot_date", "requirement_version"])
            .tail(min_snapshots)
        )
        if pair_rows.height < min_snapshots:
            continue

        demand_indexes = [float(row["demand_index"]) for row in pair_rows.iter_rows(named=True)]
        slope = _linear_slope(demand_indexes)
        confidence = _clip(abs(slope) / 0.20)
        if slope >= slope_threshold or confidence < min_confidence:
            continue

        latest_row = pair_rows.sort(["snapshot_date", "requirement_version"]).tail(1).to_dicts()[0]
        signals.append(
            DecaySignalComputationRow(
                role_id=UUID(str(pair["role_id"])),
                skill_id=UUID(str(pair["skill_id"])),
                decay_rate=_round(abs(slope)),
                confidence=_round(confidence),
                requirement_version=int(latest_row["requirement_version"]),
            )
        )

    return signals


def _linear_slope(values: list[float]) -> float:
    count = len(values)
    if count < 2:
        return 0.0
    x_values = list(range(count))
    mean_x = sum(x_values) / count
    mean_y = sum(values) / count
    denominator = sum((x_value - mean_x) ** 2 for x_value in x_values)
    if denominator == 0:
        return 0.0
    numerator = sum((x_value - mean_x) * (y_value - mean_y) for x_value, y_value in zip(x_values, values))
    return numerator / denominator


def _clip(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _round(value: float) -> float:
    return round(_clip(value), PERSISTED_PRECISION)
