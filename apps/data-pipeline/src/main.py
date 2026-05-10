from __future__ import annotations

from typing import Callable
from uuid import UUID

from pydantic import BaseModel, Field

from src.config.settings import settings
from src.db import app_event_repo, pipeline_job_repo


class PipelineResult(BaseModel):
    processed_rows: int = Field(ge=0)
    rejected_rows: int = Field(ge=0)
    output_version: int = Field(gt=0)


RunPipelineCallable = Callable[[UUID], PipelineResult]


def run_pipeline_job(
    dataset_id: UUID,
    job_type: str,
    run_pipeline: RunPipelineCallable,
) -> UUID:
    job_id = pipeline_job_repo.create_job(dataset_id=dataset_id, job_type=job_type)
    pipeline_job_repo.mark_running(job_id=job_id)

    try:
        pipeline_result = PipelineResult.model_validate(run_pipeline(job_id))
    except Exception as error:
        error_message = _to_error_message(error)
        pipeline_job_repo.mark_failed(job_id=job_id, error_message=error_message)
        app_event_repo.emit_ingestion_failed(pipeline_job_id=job_id, error_message=error_message)
        raise

    status = pipeline_job_repo.mark_complete(
        job_id=job_id,
        processed_rows=pipeline_result.processed_rows,
        rejected_rows=pipeline_result.rejected_rows,
        output_version=pipeline_result.output_version,
    )
    app_event_repo.emit_ingestion_completed(
        pipeline_job_id=job_id,
        status=status,
        output_version=pipeline_result.output_version,
    )
    return job_id


def _to_error_message(error: Exception) -> str:
    error_text = str(error).strip()
    if error_text:
        return error_text
    return error.__class__.__name__


def main() -> None:
    print("hello world")
    print("service: data-pipeline")
    print(f"environment: {settings.python_env}")


if __name__ == "__main__":
    main()
