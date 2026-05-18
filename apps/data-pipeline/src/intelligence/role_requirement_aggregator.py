from __future__ import annotations

import logging
from collections.abc import Mapping
from uuid import UUID

import polars as pl
from sqlalchemy import Connection

from src.contracts.mapped_skill import MappedRoleSkillRow
from src.publishing.evidence_summary_writer import (
    EVIDENCE_THRESHOLD,
    EvidenceSummaryInputRow,
    write_evidence_summaries,
)
from src.publishing.models.role_requirement_publish_model import RoleRequirementAggregateRow

logger = logging.getLogger(__name__)
PERSISTED_PRECISION = 4


def aggregate_role_requirements(
    *,
    pipeline_job_id: UUID,
    dataset_id: UUID,
    mapped_rows: list[MappedRoleSkillRow],
    total_matched_postings_by_role: Mapping[UUID, int] | None = None,
    connection: Connection | None = None,
) -> list[RoleRequirementAggregateRow]:
    validated_rows = [MappedRoleSkillRow.model_validate(row) for row in mapped_rows]
    if len(validated_rows) == 0:
        return []

    frame = pl.DataFrame(
        [
            {
                "job_posting_id": str(row.job_posting_id),
                "role_id": str(row.role_id),
                "skill_id": str(row.skill_id),
                "normalized_depth": row.normalized_depth,
            }
            for row in validated_rows
        ],
        schema={
            "job_posting_id": pl.String,
            "role_id": pl.String,
            "skill_id": pl.String,
            "normalized_depth": pl.Float64,
        },
    )

    role_totals = _resolve_role_totals(
        frame=frame,
        total_matched_postings_by_role=total_matched_postings_by_role,
    )
    usable_role_ids = _role_ids_with_positive_totals(role_totals)
    if len(usable_role_ids) == 0:
        return []

    usable_frame = frame.filter(pl.col("role_id").is_in(usable_role_ids))
    if usable_frame.height == 0:
        return []

    grouped = (
        usable_frame.group_by(["role_id", "skill_id"])
        .agg(
            pl.col("normalized_depth").mean().alias("required_depth"),
            pl.col("job_posting_id").n_unique().alias("skill_posting_count"),
        )
        .filter(pl.col("required_depth").is_not_null())
        .sort(["role_id", "skill_id"])
    )
    if grouped.height == 0:
        return []

    per_run_metrics = _to_per_run_metrics(grouped=grouped, role_totals=role_totals)
    summary_results = write_evidence_summaries(
        pipeline_job_id=pipeline_job_id,
        dataset_id=dataset_id,
        rows=[
            EvidenceSummaryInputRow(
                role_id=row["role_id"],
                skill_id=row["skill_id"],
                evidence_count=row["skill_posting_count"],
            )
            for row in per_run_metrics
        ],
        connection=connection,
    )
    cumulative_counts = {
        (result.role_id, result.skill_id): result.cumulative_evidence_count
        for result in summary_results
    }

    return [
        RoleRequirementAggregateRow(
            role_id=row["role_id"],
            skill_id=row["skill_id"],
            required_depth=row["required_depth"],
            demand_weight=row["demand_weight"],
            evidence_count=cumulative_counts[(row["role_id"], row["skill_id"])],
        )
        for row in per_run_metrics
        if cumulative_counts[(row["role_id"], row["skill_id"])] >= EVIDENCE_THRESHOLD
    ]


def _resolve_role_totals(
    *,
    frame: pl.DataFrame,
    total_matched_postings_by_role: Mapping[UUID, int] | None,
) -> dict[str, int]:
    role_totals = {
        str(row["role_id"]): int(row["total_matched_postings_for_role"])
        for row in frame.group_by("role_id")
        .agg(pl.col("job_posting_id").n_unique().alias("total_matched_postings_for_role"))
        .iter_rows(named=True)
    }
    if total_matched_postings_by_role is None:
        return role_totals

    role_totals.update(
        {str(role_id): int(total_count) for role_id, total_count in total_matched_postings_by_role.items()}
    )
    return role_totals


def _role_ids_with_positive_totals(role_totals: Mapping[str, int]) -> list[str]:
    usable_role_ids: list[str] = []
    for role_id, total in sorted(role_totals.items()):
        if total <= 0:
            logger.warning(
                "skipping role requirement aggregation for role_id=%s because total_matched_postings_for_role=%s",
                role_id,
                total,
            )
            continue
        usable_role_ids.append(role_id)
    return usable_role_ids


def _to_per_run_metrics(
    *,
    grouped: pl.DataFrame,
    role_totals: Mapping[str, int],
) -> list[dict[str, UUID | int | float]]:
    metrics: list[dict[str, UUID | int | float]] = []
    for row in grouped.iter_rows(named=True):
        total_for_role = role_totals[str(row["role_id"])]
        frequency_share = int(row["skill_posting_count"]) / total_for_role
        metrics.append(
            {
                "role_id": UUID(str(row["role_id"])),
                "skill_id": UUID(str(row["skill_id"])),
                "skill_posting_count": int(row["skill_posting_count"]),
                "required_depth": _clip_round(float(row["required_depth"]), 0.0, 1.0),
                "demand_weight": _clip_round(max(0.1, frequency_share), 0.1, 1.0),
            }
        )
    return metrics


def _clip_round(value: float, minimum: float, maximum: float) -> float:
    return round(min(max(value, minimum), maximum), PERSISTED_PRECISION)
