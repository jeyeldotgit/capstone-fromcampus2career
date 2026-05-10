from __future__ import annotations

from typing import Annotated, Literal, cast
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import Connection, text

from src.db import get_connection, utcnow

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TerminalJobStatus = Literal["complete", "partial"]
PipelineJobStatus = Literal["pending", "running", "complete", "failed", "partial"]


class CreatePipelineJobInput(BaseModel):
    dataset_id: UUID
    job_type: NonEmptyStr


class PipelineJobIdInput(BaseModel):
    job_id: UUID


class CompletePipelineJobInput(PipelineJobIdInput):
    processed_rows: int = Field(ge=0)
    rejected_rows: int = Field(ge=0)
    output_version: int = Field(gt=0)


class FailPipelineJobInput(PipelineJobIdInput):
    error_message: NonEmptyStr


def create_job(dataset_id: UUID, job_type: str) -> UUID:
    payload = CreatePipelineJobInput(dataset_id=dataset_id, job_type=job_type)
    with get_connection() as connection:
        inserted_id = connection.execute(
            text(
                """
                insert into pipeline_jobs (
                    dataset_id,
                    job_type,
                    status,
                    processed_rows,
                    rejected_rows,
                    output_version,
                    error_message,
                    finished_at
                )
                values (
                    :dataset_id,
                    :job_type,
                    'pending',
                    0,
                    0,
                    null,
                    null,
                    null
                )
                returning id
                """
            ),
            {
                "dataset_id": payload.dataset_id,
                "job_type": payload.job_type,
            },
        ).scalar_one()

    return UUID(str(inserted_id))


def mark_running(job_id: UUID) -> None:
    payload = PipelineJobIdInput(job_id=job_id)
    with get_connection() as connection:
        updated_id = connection.execute(
            text(
                """
                update pipeline_jobs
                set status = 'running',
                    started_at = case
                        when status = 'pending' then :started_at
                        else started_at
                    end
                where id = :job_id
                  and status in ('pending', 'running')
                returning id
                """
            ),
            {
                "job_id": payload.job_id,
                "started_at": utcnow(),
            },
        ).scalar_one_or_none()

        if updated_id is not None:
            return

        current_status = _fetch_job_status(connection, payload.job_id)
        if current_status is None:
            raise ValueError(f"pipeline_jobs row not found for job_id={payload.job_id}")

        raise RuntimeError(
            f"cannot transition pipeline job {payload.job_id} to running from status '{current_status}'"
        )


def mark_complete(
    job_id: UUID,
    processed_rows: int,
    rejected_rows: int,
    output_version: int,
) -> TerminalJobStatus:
    payload = CompletePipelineJobInput(
        job_id=job_id,
        processed_rows=processed_rows,
        rejected_rows=rejected_rows,
        output_version=output_version,
    )

    terminal_status = _resolve_terminal_status(payload.rejected_rows)
    with get_connection() as connection:
        updated_status = connection.execute(
            text(
                """
                update pipeline_jobs
                set status = :status,
                    processed_rows = :processed_rows,
                    rejected_rows = :rejected_rows,
                    output_version = :output_version,
                    error_message = null,
                    finished_at = :finished_at
                where id = :job_id
                  and status = 'running'
                returning status
                """
            ),
            {
                "job_id": payload.job_id,
                "status": terminal_status,
                "processed_rows": payload.processed_rows,
                "rejected_rows": payload.rejected_rows,
                "output_version": payload.output_version,
                "finished_at": utcnow(),
            },
        ).scalar_one_or_none()

        if updated_status is not None:
            return cast(TerminalJobStatus, updated_status)

        current_status = _fetch_job_status(connection, payload.job_id)
        if current_status is None:
            raise ValueError(f"pipeline_jobs row not found for job_id={payload.job_id}")

        if current_status in ("complete", "partial"):
            return cast(TerminalJobStatus, current_status)

        raise RuntimeError(
            f"cannot transition pipeline job {payload.job_id} to terminal complete/partial from status '{current_status}'"
        )


def mark_failed(job_id: UUID, error_message: str) -> None:
    payload = FailPipelineJobInput(job_id=job_id, error_message=error_message)
    with get_connection() as connection:
        updated_id = connection.execute(
            text(
                """
                update pipeline_jobs
                set status = 'failed',
                    error_message = :error_message,
                    finished_at = :finished_at,
                    output_version = null
                where id = :job_id
                  and status in ('pending', 'running')
                returning id
                """
            ),
            {
                "job_id": payload.job_id,
                "error_message": _normalize_error_message(payload.error_message),
                "finished_at": utcnow(),
            },
        ).scalar_one_or_none()

        if updated_id is not None:
            return

        current_status = _fetch_job_status(connection, payload.job_id)
        if current_status is None:
            raise ValueError(f"pipeline_jobs row not found for job_id={payload.job_id}")

        if current_status == "failed":
            return

        raise RuntimeError(
            f"cannot transition pipeline job {payload.job_id} to failed from status '{current_status}'"
        )


def _resolve_terminal_status(rejected_rows: int) -> TerminalJobStatus:
    return "complete" if rejected_rows == 0 else "partial"


def _normalize_error_message(message: str) -> str:
    normalized = message.strip()
    max_length = 2000
    if len(normalized) > max_length:
        return normalized[:max_length]
    return normalized


def _fetch_job_status(connection: Connection, job_id: UUID) -> PipelineJobStatus | None:
    return connection.execute(
        text(
            """
            select status
            from pipeline_jobs
            where id = :job_id
            """
        ),
        {"job_id": job_id},
    ).scalar_one_or_none()
