from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Connection, text

from src.db import get_connection

EVIDENCE_THRESHOLD = 5


class EvidenceSummaryInputRow(BaseModel):
    role_id: UUID
    skill_id: UUID
    evidence_count: int = Field(ge=0)


class EvidenceSummaryWriteResult(BaseModel):
    role_id: UUID
    skill_id: UUID
    evidence_count: int = Field(ge=0)
    cumulative_evidence_count: int = Field(ge=0)
    threshold_met: bool


def write_evidence_summaries(
    *,
    pipeline_job_id: UUID,
    dataset_id: UUID,
    rows: list[EvidenceSummaryInputRow],
    threshold: int = EVIDENCE_THRESHOLD,
    connection: Connection | None = None,
) -> list[EvidenceSummaryWriteResult]:
    validated_rows = [EvidenceSummaryInputRow.model_validate(row) for row in rows]
    if len(validated_rows) == 0:
        return []

    if connection is not None:
        return _write_evidence_summaries_with_connection(
            connection=connection,
            pipeline_job_id=pipeline_job_id,
            dataset_id=dataset_id,
            rows=validated_rows,
            threshold=threshold,
        )

    with get_connection() as managed_connection:
        return _write_evidence_summaries_with_connection(
            connection=managed_connection,
            pipeline_job_id=pipeline_job_id,
            dataset_id=dataset_id,
            rows=validated_rows,
            threshold=threshold,
        )


def _write_evidence_summaries_with_connection(
    *,
    connection: Connection,
    pipeline_job_id: UUID,
    dataset_id: UUID,
    rows: list[EvidenceSummaryInputRow],
    threshold: int,
) -> list[EvidenceSummaryWriteResult]:
    existing_counts = _load_existing_counts(connection=connection, rows=rows)
    results = [
        EvidenceSummaryWriteResult(
            role_id=row.role_id,
            skill_id=row.skill_id,
            evidence_count=row.evidence_count,
            cumulative_evidence_count=existing_counts.get((row.role_id, row.skill_id), 0)
            + row.evidence_count,
            threshold_met=(
                existing_counts.get((row.role_id, row.skill_id), 0) + row.evidence_count
            )
            >= threshold,
        )
        for row in rows
    ]

    connection.execute(
        text(
            """
            insert into pipeline_skill_evidence_summary (
                id,
                dataset_id,
                pipeline_job_id,
                role_id,
                skill_id,
                evidence_count,
                threshold_met
            )
            values (
                :id,
                :dataset_id,
                :pipeline_job_id,
                :role_id,
                :skill_id,
                :evidence_count,
                :threshold_met
            )
            """
        ),
        [
            {
                "id": uuid4(),
                "dataset_id": dataset_id,
                "pipeline_job_id": pipeline_job_id,
                "role_id": result.role_id,
                "skill_id": result.skill_id,
                "evidence_count": result.evidence_count,
                "threshold_met": result.threshold_met,
            }
            for result in results
        ],
    )

    return results


def _load_existing_counts(
    *,
    connection: Connection,
    rows: list[EvidenceSummaryInputRow],
) -> dict[tuple[UUID, UUID], int]:
    unique_pairs = sorted({(row.role_id, row.skill_id) for row in rows}, key=lambda pair: str(pair))
    values_sql = ", ".join(
        f"(cast(:role_id_{index} as uuid), cast(:skill_id_{index} as uuid))"
        for index, _pair in enumerate(unique_pairs)
    )
    parameters = {
        parameter_name: parameter_value
        for index, (role_id, skill_id) in enumerate(unique_pairs)
        for parameter_name, parameter_value in (
            (f"role_id_{index}", str(role_id)),
            (f"skill_id_{index}", str(skill_id)),
        )
    }

    result = connection.execute(
        text(
            f"""
            with requested(role_id, skill_id) as (
                values {values_sql}
            )
            select
                requested.role_id,
                requested.skill_id,
                coalesce(sum(summary.evidence_count), 0)::integer as evidence_count
            from requested
            left join pipeline_skill_evidence_summary summary
              on summary.role_id = requested.role_id
             and summary.skill_id = requested.skill_id
            group by requested.role_id, requested.skill_id
            """
        ),
        parameters,
    )

    return {
        (UUID(str(row["role_id"])), UUID(str(row["skill_id"]))): int(row["evidence_count"])
        for row in result.mappings()
    }
