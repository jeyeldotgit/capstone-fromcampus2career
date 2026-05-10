from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import polars as pl
from pydantic import ValidationError

from src.contracts.raw_job_posting import RawJobPosting
from src.ingestion.rejected_row import RejectedRow

REQUIRED_COLUMNS: tuple[str, ...] = (
    "external_id",
    "source",
    "title",
    "company",
    "location",
    "posted_at",
    "description",
    "url",
)
OPTIONAL_COLUMNS: tuple[str, ...] = (
    "employment_type",
    "salary_min",
    "salary_max",
    "currency",
    "experience_level",
)
EMPTY_REQUIRED_COLUMNS: tuple[str, ...] = (
    "external_id",
    "source",
    "title",
    "company",
    "url",
)


def read_csv_rows(csv_path: str | Path) -> list[dict[str, object]]:
    frame = pl.read_csv(
        csv_path,
        infer_schema=False,
        null_values=[],
        missing_utf8_is_empty_string=True,
    )
    return [dict(row) for row in frame.iter_rows(named=True)]


def validate_csv(csv_path: str | Path) -> tuple[list[RawJobPosting], list[RejectedRow], int]:
    return validate_rows(read_csv_rows(csv_path))


def validate_rows(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[list[RawJobPosting], list[RejectedRow], int]:
    valid_rows: list[RawJobPosting] = []
    rejected_rows: list[RejectedRow] = []

    for row_number, row in enumerate(rows, start=1):
        raw_payload = dict(row)
        rejection_reason = _first_rejection_reason(raw_payload)

        if rejection_reason is not None:
            rejected_rows.append(
                RejectedRow(
                    row_number=row_number,
                    raw_payload=raw_payload,
                    reason=rejection_reason,
                )
            )
            continue

        valid_rows.append(RawJobPosting.model_validate(raw_payload))

    return valid_rows, rejected_rows, len(rejected_rows)


def _first_rejection_reason(raw_payload: Mapping[str, Any]) -> str | None:
    for column_name in REQUIRED_COLUMNS:
        if column_name not in raw_payload:
            return f"MISSING_REQUIRED_FIELD:{column_name}"

    for column_name in EMPTY_REQUIRED_COLUMNS:
        if _is_empty(raw_payload[column_name]):
            return f"EMPTY_REQUIRED_FIELD:{column_name}"

    if not _has_valid_posted_at(raw_payload["posted_at"]):
        return "INVALID_DATE:posted_at"

    return None


def _is_empty(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _has_valid_posted_at(value: Any) -> bool:
    try:
        RawJobPosting.model_validate(
            {
                "external_id": "date-check",
                "source": "date-check",
                "title": "date-check",
                "company": "date-check",
                "location": "date-check",
                "posted_at": value,
                "description": "date-check",
                "url": "https://example.com/date-check",
            }
        )
    except (TypeError, ValueError, ValidationError):
        return False
    return True
