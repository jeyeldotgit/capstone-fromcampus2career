from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.contracts.raw_job_posting import RawJobPosting
from src.ingestion.validator import read_csv_rows


class JobStreetAdaptationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class JobStreetAdaptationFailure:
    row_number: int
    raw_payload: dict[str, Any]
    reason: str


REQUIRED_FIELD_CANDIDATES: dict[str, tuple[str, ...]] = {
    "external_id": ("posting_id",),
    "source": ("platform", "source_dataset"),
    "posted_at": ("posted_date",),
    "title": ("job_title", "title"),
    "company": ("company_name", "company"),
    "location": ("location",),
    "description": ("description", "job_description"),
    "url": ("url", "job_url"),
}

OPTIONAL_FIELD_CANDIDATES: dict[str, tuple[str, ...]] = {
    "employment_type": ("employment_type", "work_type"),
    "salary_min": ("salary_min",),
    "salary_max": ("salary_max",),
    "currency": ("currency",),
    "experience_level": ("experience_level",),
}


def adapt_jobstreet_csv(csv_path: str | Path) -> tuple[list[RawJobPosting], list[JobStreetAdaptationFailure]]:
    return adapt_jobstreet_rows(read_csv_rows(csv_path))


def adapt_jobstreet_rows(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[list[RawJobPosting], list[JobStreetAdaptationFailure]]:
    adapted_rows: list[RawJobPosting] = []
    failures: list[JobStreetAdaptationFailure] = []

    for row_number, row in enumerate(rows, start=1):
        raw_payload = dict(row)
        try:
            adapted_rows.append(adapt_jobstreet_row(raw_payload))
        except JobStreetAdaptationError as error:
            failures.append(
                JobStreetAdaptationFailure(
                    row_number=row_number,
                    raw_payload=raw_payload,
                    reason=str(error),
                )
            )

    return adapted_rows, failures


def adapt_jobstreet_row(row: Mapping[str, Any]) -> RawJobPosting:
    canonical_payload: dict[str, Any] = {}

    for target_field, source_columns in REQUIRED_FIELD_CANDIDATES.items():
        source_column = _first_present_column(row, source_columns)
        if source_column is None:
            expected = "|".join(source_columns)
            raise JobStreetAdaptationError(f"MISSING_SOURCE_COLUMN:{target_field}:{expected}")

        value = row[source_column]
        if target_field == "posted_at":
            value = _normalize_posted_date(value)
        canonical_payload[target_field] = value

    for target_field, source_columns in OPTIONAL_FIELD_CANDIDATES.items():
        source_column = _first_present_column(row, source_columns)
        if source_column is None:
            continue
        value = row[source_column]
        if _is_blank(value):
            continue
        canonical_payload[target_field] = value

    try:
        return RawJobPosting.model_validate(canonical_payload)
    except ValidationError as error:
        reason = ";".join(
            f"CANONICAL_VALIDATION:{'.'.join(str(part) for part in issue['loc'])}:{issue['msg']}"
            for issue in error.errors()
        )
        raise JobStreetAdaptationError(reason) from error


def _first_present_column(row: Mapping[str, Any], candidates: Sequence[str]) -> str | None:
    for column_name in candidates:
        if column_name in row:
            return column_name
    return None


def _normalize_posted_date(value: Any) -> str:
    if not isinstance(value, str):
        return str(value)

    normalized = value.strip()
    if len(normalized) == 7:
        try:
            return date.fromisoformat(f"{normalized}-01").isoformat()
        except ValueError as error:
            raise JobStreetAdaptationError("INVALID_SOURCE_DATE:posted_date") from error

    try:
        return date.fromisoformat(normalized).isoformat()
    except ValueError as error:
        raise JobStreetAdaptationError("INVALID_SOURCE_DATE:posted_date") from error


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""
