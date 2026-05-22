from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.contracts.raw_job_posting import RawJobPosting
from src.ingestion.jobstreet_adapter import (
    JobStreetAdaptationError,
    adapt_jobstreet_csv,
    adapt_jobstreet_row,
    adapt_jobstreet_rows,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _base_row() -> dict[str, object]:
    return {
        "posting_id": "jobstreet-001",
        "platform": "jobstreet",
        "source_dataset": "jobstreet_live_ph",
        "posted_date": "2026-05",
        "job_title": "Data Analyst",
        "company_name": "Acme Analytics",
        "location": "Makati City",
        "description": "Analyze data with SQL and Python.",
        "url": "https://ph.jobstreet.com/job/1",
        "employment_type": "Full time",
        "salary_min": "70000",
        "salary_max": "90000",
        "currency": "PHP",
        "experience_level": "Entry",
    }


def test_maps_required_columns_and_month_only_date_to_raw_job_posting() -> None:
    posting = adapt_jobstreet_row(_base_row())

    assert isinstance(posting, RawJobPosting)
    assert posting.external_id == "jobstreet-001"
    assert posting.source == "jobstreet"
    assert posting.posted_at.isoformat() == "2026-05-01"
    assert posting.title == "Data Analyst"
    assert posting.company == "Acme Analytics"
    assert posting.location == "Makati City"
    assert posting.description == "Analyze data with SQL and Python."
    assert posting.url == "https://ph.jobstreet.com/job/1"
    assert posting.employment_type == "Full time"
    assert posting.salary_min == Decimal("70000")
    assert posting.salary_max == Decimal("90000")
    assert posting.currency == "PHP"
    assert posting.experience_level == "Entry"


def test_uses_source_dataset_when_platform_column_is_absent() -> None:
    row = _base_row()
    row.pop("platform")

    posting = adapt_jobstreet_row(row)

    assert posting.source == "jobstreet_live_ph"


def test_uses_description_variant_when_description_column_is_absent() -> None:
    row = _base_row()
    row.pop("description")
    row["job_description"] = "Build reports with Power BI."

    posting = adapt_jobstreet_row(row)

    assert posting.description == "Build reports with Power BI."


def test_uses_url_variant_when_url_column_is_absent() -> None:
    row = _base_row()
    row.pop("url")
    row["job_url"] = "https://ph.jobstreet.com/job/variant"

    posting = adapt_jobstreet_row(row)

    assert posting.url == "https://ph.jobstreet.com/job/variant"


def test_supports_fixture_column_names_title_company_and_work_type() -> None:
    row = _base_row()
    row.pop("job_title")
    row.pop("company_name")
    row.pop("employment_type")
    row["title"] = "Software Engineer"
    row["company"] = "Fixture Co"
    row["work_type"] = "Contract/Temp"

    posting = adapt_jobstreet_row(row)

    assert posting.title == "Software Engineer"
    assert posting.company == "Fixture Co"
    assert posting.employment_type == "Contract/Temp"


def test_malformed_month_only_date_produces_clear_adaptation_error() -> None:
    row = {**_base_row(), "posted_date": "2026-13"}

    with pytest.raises(JobStreetAdaptationError, match="INVALID_SOURCE_DATE:posted_date"):
        adapt_jobstreet_row(row)


def test_absent_required_mapping_source_column_produces_clear_error() -> None:
    row = _base_row()
    row.pop("posting_id")

    with pytest.raises(
        JobStreetAdaptationError,
        match=r"MISSING_SOURCE_COLUMN:external_id:posting_id",
    ):
        adapt_jobstreet_row(row)


def test_canonical_validation_is_not_bypassed() -> None:
    row = {**_base_row(), "url": "   "}

    with pytest.raises(JobStreetAdaptationError, match="CANONICAL_VALIDATION:url"):
        adapt_jobstreet_row(row)


def test_rows_return_adaptation_failures_without_silent_nulls() -> None:
    valid_row = _base_row()
    invalid_row = _base_row()
    invalid_row.pop("url")
    invalid_row.pop("job_url", None)

    adapted_rows, failures = adapt_jobstreet_rows([valid_row, invalid_row])

    assert len(adapted_rows) == 1
    assert len(failures) == 1
    assert failures[0].row_number == 2
    assert failures[0].reason == "MISSING_SOURCE_COLUMN:url:url|job_url"


def test_jobstreet_fixture_rows_map_into_raw_contract() -> None:
    adapted_rows, failures = adapt_jobstreet_csv(FIXTURES_DIR / "05-2026_jobstreet_dataset.csv")

    assert failures == []
    assert len(adapted_rows) == 119
    assert all(isinstance(row, RawJobPosting) for row in adapted_rows)
    assert {row.source for row in adapted_rows} == {"jobstreet"}
    assert {row.posted_at.day for row in adapted_rows} == {1}
