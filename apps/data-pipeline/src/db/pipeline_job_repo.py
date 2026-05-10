from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TerminalJobStatus = Literal["complete", "partial"]


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
    _ = CreatePipelineJobInput(dataset_id=dataset_id, job_type=job_type)
    raise NotImplementedError("Slice 1 stub: create_job is implemented in slice 2")


def mark_running(job_id: UUID) -> None:
    _ = PipelineJobIdInput(job_id=job_id)
    raise NotImplementedError("Slice 1 stub: mark_running is implemented in slice 2")


def mark_complete(
    job_id: UUID,
    processed_rows: int,
    rejected_rows: int,
    output_version: int,
) -> TerminalJobStatus:
    _ = CompletePipelineJobInput(
        job_id=job_id,
        processed_rows=processed_rows,
        rejected_rows=rejected_rows,
        output_version=output_version,
    )
    raise NotImplementedError("Slice 1 stub: mark_complete is implemented in slice 2")


def mark_failed(job_id: UUID, error_message: str) -> None:
    _ = FailPipelineJobInput(job_id=job_id, error_message=error_message)
    raise NotImplementedError("Slice 1 stub: mark_failed is implemented in slice 2")
