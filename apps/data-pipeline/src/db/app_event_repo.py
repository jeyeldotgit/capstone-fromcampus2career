from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CompletedEventStatus = Literal["complete", "partial"]


class CompletedIngestionEventInput(BaseModel):
    pipeline_job_id: UUID
    status: CompletedEventStatus
    output_version: int = Field(gt=0)


class FailedIngestionEventInput(BaseModel):
    pipeline_job_id: UUID
    error_message: NonEmptyStr


def emit_ingestion_completed(
    pipeline_job_id: UUID,
    status: CompletedEventStatus,
    output_version: int,
) -> None:
    _ = CompletedIngestionEventInput(
        pipeline_job_id=pipeline_job_id,
        status=status,
        output_version=output_version,
    )
    raise NotImplementedError(
        "Slice 1 stub: emit_ingestion_completed is implemented in slice 3"
    )


def emit_ingestion_failed(pipeline_job_id: UUID, error_message: str) -> None:
    _ = FailedIngestionEventInput(
        pipeline_job_id=pipeline_job_id,
        error_message=error_message,
    )
    raise NotImplementedError("Slice 1 stub: emit_ingestion_failed is implemented in slice 3")
