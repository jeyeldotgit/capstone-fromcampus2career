from __future__ import annotations

import json
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text

from src.db import get_connection
from src.ingestion.rejected_row import RejectedRow


class WriteRejectedRowsInput(BaseModel):
    pipeline_job_id: UUID
    rejected_rows: list[RejectedRow]


def write_rejected_rows(pipeline_job_id: UUID, rejected_rows: list[RejectedRow]) -> int:
    payload = WriteRejectedRowsInput(
        pipeline_job_id=pipeline_job_id,
        rejected_rows=rejected_rows,
    )
    if len(payload.rejected_rows) == 0:
        return 0

    rows_to_insert = [
        {
            "pipeline_job_id": payload.pipeline_job_id,
            "row_number": rejected_row.row_number,
            "raw_payload": json.dumps(rejected_row.raw_payload, separators=(",", ":")),
            "reason": rejected_row.reason,
        }
        for rejected_row in payload.rejected_rows
    ]

    with get_connection() as connection:
        result = connection.execute(
            text(
                """
                insert into pipeline_rejected_rows (
                    pipeline_job_id,
                    row_number,
                    raw_payload,
                    reason
                )
                values (
                    :pipeline_job_id,
                    :row_number,
                    cast(:raw_payload as jsonb),
                    :reason
                )
                """
            ),
            rows_to_insert,
        )

    return result.rowcount
