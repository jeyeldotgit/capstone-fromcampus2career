from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import Connection, text

from src.db import get_connection, utcnow

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CompletedEventStatus = Literal["complete", "partial"]
EventType = Literal["pipeline.ingestion.completed", "pipeline.ingestion.failed"]

INGESTION_COMPLETED_EVENT_TYPE: EventType = "pipeline.ingestion.completed"
INGESTION_FAILED_EVENT_TYPE: EventType = "pipeline.ingestion.failed"


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
    payload = CompletedIngestionEventInput(
        pipeline_job_id=pipeline_job_id,
        status=status,
        output_version=output_version,
    )
    _emit_terminal_event(
        event_type=INGESTION_COMPLETED_EVENT_TYPE,
        pipeline_job_id=payload.pipeline_job_id,
        payload_body={
            "type": INGESTION_COMPLETED_EVENT_TYPE,
            "pipelineJobId": str(payload.pipeline_job_id),
            "status": payload.status,
            "outputVersion": payload.output_version,
        },
    )


def emit_ingestion_failed(pipeline_job_id: UUID, error_message: str) -> None:
    payload = FailedIngestionEventInput(
        pipeline_job_id=pipeline_job_id,
        error_message=error_message,
    )
    _emit_terminal_event(
        event_type=INGESTION_FAILED_EVENT_TYPE,
        pipeline_job_id=payload.pipeline_job_id,
        payload_body={
            "type": INGESTION_FAILED_EVENT_TYPE,
            "pipelineJobId": str(payload.pipeline_job_id),
            "status": "failed",
            "errorMessage": payload.error_message,
        },
    )


def _emit_terminal_event(
    *,
    event_type: EventType,
    pipeline_job_id: UUID,
    payload_body: dict[str, object],
) -> bool:
    with get_connection() as connection:
        _acquire_terminal_event_lock(
            connection=connection,
            pipeline_job_id=pipeline_job_id,
            event_type=event_type,
        )
        insert_result = connection.execute(
            text(
                """
                insert into app_events (
                    event_type,
                    aggregate_type,
                    aggregate_id,
                    payload,
                    status,
                    available_at
                )
                select
                    :event_type,
                    'pipeline_job',
                    :aggregate_id,
                    cast(:payload as jsonb),
                    'pending',
                    :available_at
                where not exists (
                    select 1
                    from app_events
                    where aggregate_id = :aggregate_id
                      and event_type = :event_type
                )
                """
            ),
            {
                "event_type": event_type,
                "aggregate_id": pipeline_job_id,
                "payload": json.dumps(payload_body, separators=(",", ":")),
                "available_at": utcnow(),
            },
        )

    return insert_result.rowcount > 0


def _acquire_terminal_event_lock(
    *,
    connection: Connection,
    pipeline_job_id: UUID,
    event_type: EventType,
) -> None:
    connection.execute(
        text("select pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _terminal_event_lock_key(pipeline_job_id, event_type)},
    )


def _terminal_event_lock_key(pipeline_job_id: UUID, event_type: EventType) -> int:
    raw = f"{pipeline_job_id}:{event_type}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)
