from __future__ import annotations

"""Deterministic Skill Demand Index computation for prepared market outputs."""

from datetime import date, timedelta
from uuid import UUID

import polars as pl
from pydantic import BaseModel, Field
from sqlalchemy import Connection, text

PERSISTED_PRECISION = 4
DEFAULT_WINDOW_DAYS = 90


class SdiPostingSkillInputRow(BaseModel):
    job_posting_id: UUID
    dataset_id: UUID
    role_id: UUID
    skill_id: UUID
    posted_at: date


class SdiComputationRow(BaseModel):
    role_id: UUID
    skill_id: UUID
    frequency_share: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    growth_score: float = Field(ge=0.0, le=1.0)
    demand_index: float = Field(ge=0.0, le=1.0)


def load_sdi_posting_skill_rows(
    *,
    connection: Connection,
    dataset_id: UUID,
    requirement_version: int,
    window_start: date | None = None,
    window_end: date | None = None,
) -> list[SdiPostingSkillInputRow]:
    filters = ["postings.dataset_id = :dataset_id", "requirements.requirement_version = :requirement_version"]
    parameters: dict[str, object] = {
        "dataset_id": dataset_id,
        "requirement_version": requirement_version,
    }
    if window_start is not None:
        filters.append("postings.posted_at >= :window_start")
        parameters["window_start"] = window_start
    if window_end is not None:
        filters.append("postings.posted_at <= :window_end")
        parameters["window_end"] = window_end

    result = connection.execute(
        text(
            f"""
            select
                postings.id as job_posting_id,
                postings.dataset_id,
                posting_skills.role_id,
                posting_skills.skill_id,
                postings.posted_at
            from job_postings postings
            join job_posting_skills posting_skills
              on posting_skills.job_posting_id = postings.id
             and posting_skills.role_id = postings.role_id
            join role_skill_requirements requirements
              on requirements.role_id = posting_skills.role_id
             and requirements.skill_id = posting_skills.skill_id
            where {" and ".join(filters)}
            order by posting_skills.role_id, posting_skills.skill_id, postings.posted_at, postings.id
            """
        ),
        parameters,
    )

    return [
        SdiPostingSkillInputRow(
            job_posting_id=UUID(str(row["job_posting_id"])),
            dataset_id=UUID(str(row["dataset_id"])),
            role_id=UUID(str(row["role_id"])),
            skill_id=UUID(str(row["skill_id"])),
            posted_at=row["posted_at"],
        )
        for row in result.mappings()
    ]


def compute_sdi(
    rows: list[SdiPostingSkillInputRow],
    *,
    snapshot_date: date,
    previous_rows: list[SdiPostingSkillInputRow] | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> list[SdiComputationRow]:
    current_rows = [SdiPostingSkillInputRow.model_validate(row) for row in rows]
    if len(current_rows) == 0:
        return []

    current_frame = _to_frame(current_rows)
    previous_frame = _to_frame(previous_rows or [])
    current_role_totals = _role_posting_totals(current_frame)
    previous_frequency = _frequency_by_pair(previous_frame) if previous_frame.height > 0 else {}

    grouped = (
        current_frame.group_by(["role_id", "skill_id"])
        .agg(
            pl.col("job_posting_id").n_unique().alias("skill_posting_count"),
            pl.col("posted_at").alias("posted_dates"),
        )
        .sort(["role_id", "skill_id"])
    )

    output: list[SdiComputationRow] = []
    for row in grouped.iter_rows(named=True):
        role_id = str(row["role_id"])
        skill_id = str(row["skill_id"])
        total_for_role = current_role_totals[role_id]
        frequency_share = _clip(int(row["skill_posting_count"]) / total_for_role)
        recency_score = _mean_recency_score(
            posted_dates=[date.fromisoformat(value) for value in row["posted_dates"]],
            snapshot_date=snapshot_date,
            window_days=window_days,
        )
        previous_share = previous_frequency.get((role_id, skill_id))
        growth_score = 0.5 if previous_share is None else _clip(((frequency_share - previous_share) + 1.0) / 2.0)
        demand_index = _clip(
            (0.50 * frequency_share) + (0.30 * recency_score) + (0.20 * growth_score)
        )

        output.append(
            SdiComputationRow(
                role_id=UUID(role_id),
                skill_id=UUID(skill_id),
                frequency_share=_round(frequency_share),
                recency_score=_round(recency_score),
                growth_score=_round(growth_score),
                demand_index=_round(demand_index),
            )
        )

    return output


def previous_window(
    *,
    window_start: date,
    window_end: date,
) -> tuple[date, date]:
    span_days = (window_end - window_start).days + 1
    previous_end = window_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=span_days - 1)
    return previous_start, previous_end


def _to_frame(rows: list[SdiPostingSkillInputRow]) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "job_posting_id": str(row.job_posting_id),
                "dataset_id": str(row.dataset_id),
                "role_id": str(row.role_id),
                "skill_id": str(row.skill_id),
                "posted_at": row.posted_at.isoformat(),
            }
            for row in rows
        ],
        schema={
            "job_posting_id": pl.String,
            "dataset_id": pl.String,
            "role_id": pl.String,
            "skill_id": pl.String,
            "posted_at": pl.String,
        },
    )


def _role_posting_totals(frame: pl.DataFrame) -> dict[str, int]:
    return {
        str(row["role_id"]): int(row["total"])
        for row in frame.group_by("role_id")
        .agg(pl.col("job_posting_id").n_unique().alias("total"))
        .iter_rows(named=True)
    }


def _frequency_by_pair(frame: pl.DataFrame) -> dict[tuple[str, str], float]:
    role_totals = _role_posting_totals(frame)
    grouped = (
        frame.group_by(["role_id", "skill_id"])
        .agg(pl.col("job_posting_id").n_unique().alias("skill_posting_count"))
        .sort(["role_id", "skill_id"])
    )
    return {
        (str(row["role_id"]), str(row["skill_id"])): _clip(
            int(row["skill_posting_count"]) / role_totals[str(row["role_id"])]
        )
        for row in grouped.iter_rows(named=True)
    }


def _mean_recency_score(
    *,
    posted_dates: list[date],
    snapshot_date: date,
    window_days: int,
) -> float:
    if len(posted_dates) == 0:
        return 0.0
    bounded_window_days = max(window_days, 1)
    scores = [
        _clip(1.0 - (max((snapshot_date - posted_at).days, 0) / bounded_window_days))
        for posted_at in posted_dates
    ]
    return sum(scores) / len(scores)


def _clip(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _round(value: float) -> float:
    return round(_clip(value), PERSISTED_PRECISION)
