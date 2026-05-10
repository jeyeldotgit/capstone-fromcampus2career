from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion.validator import REQUIRED_COLUMNS, read_csv_rows, validate_csv, validate_rows

FIXTURES_DIR = Path(__file__).parent / "fixtures"

BASE_ROW: dict[str, object] = {
    "external_id": "job-001",
    "source": "acme_jobs",
    "title": "Data Analyst",
    "company": "Acme Inc",
    "location": "Remote",
    "posted_at": "2026-05-01",
    "description": "Analyze product data",
    "url": "https://example.com/jobs/1",
    "employment_type": "Full-time",
    "salary_min": "70000",
    "salary_max": "90000",
    "currency": "USD",
    "experience_level": "Entry",
}


def test_all_rows_in_valid_csv_pass_with_zero_rejections() -> None:
    valid_rows, rejected_rows, rejected_count = validate_csv(FIXTURES_DIR / "valid_rows.csv")

    assert len(valid_rows) == 2
    assert rejected_rows == []
    assert rejected_count == 0
    assert valid_rows[0].external_id == "job-001"
    assert valid_rows[0].salary_min == Decimal("70000")


@pytest.mark.parametrize("column_name", REQUIRED_COLUMNS)
def test_each_missing_required_column_produces_missing_required_reason(column_name: str) -> None:
    row = {key: value for key, value in BASE_ROW.items() if key != column_name}

    valid_rows, rejected_rows, rejected_count = validate_rows([row])

    assert valid_rows == []
    assert rejected_count == 1
    assert len(rejected_rows) == 1
    assert rejected_rows[0].reason == f"MISSING_REQUIRED_FIELD:{column_name}"
    assert rejected_rows[0].raw_payload == row


def test_missing_required_columns_fixture_rejects_missing_url_header() -> None:
    valid_rows, rejected_rows, rejected_count = validate_csv(
        FIXTURES_DIR / "missing_required_columns.csv"
    )

    assert valid_rows == []
    assert rejected_count == 1
    assert rejected_rows[0].reason == "MISSING_REQUIRED_FIELD:url"


@pytest.mark.parametrize(
    "column_name",
    ("external_id", "source", "title", "company", "url"),
)
def test_each_empty_required_field_produces_empty_required_reason(column_name: str) -> None:
    row = {**BASE_ROW, column_name: "   "}

    valid_rows, rejected_rows, rejected_count = validate_rows([row])

    assert valid_rows == []
    assert rejected_count == 1
    assert len(rejected_rows) == 1
    assert rejected_rows[0].reason == f"EMPTY_REQUIRED_FIELD:{column_name}"


def test_invalid_posted_at_value_produces_invalid_date_reason() -> None:
    row = {**BASE_ROW, "posted_at": "not-a-date"}

    valid_rows, rejected_rows, rejected_count = validate_rows([row])

    assert valid_rows == []
    assert rejected_count == 1
    assert len(rejected_rows) == 1
    assert rejected_rows[0].reason == "INVALID_DATE:posted_at"


def test_missing_optional_columns_do_not_cause_rejection() -> None:
    row = {key: BASE_ROW[key] for key in REQUIRED_COLUMNS}

    valid_rows, rejected_rows, rejected_count = validate_rows([row])

    assert len(valid_rows) == 1
    assert rejected_rows == []
    assert rejected_count == 0
    assert valid_rows[0].employment_type is None
    assert valid_rows[0].salary_min is None
    assert valid_rows[0].salary_max is None
    assert valid_rows[0].currency is None
    assert valid_rows[0].experience_level is None


def test_mixed_csv_yields_valid_and_rejected_counts_summing_to_total_rows() -> None:
    csv_path = FIXTURES_DIR / "mixed_valid_and_invalid_rows.csv"
    total_rows = len(read_csv_rows(csv_path))

    valid_rows, rejected_rows, rejected_count = validate_csv(csv_path)

    assert len(valid_rows) == 1
    assert rejected_count == 3
    assert len(valid_rows) + rejected_count == total_rows
    assert [rejected.reason for rejected in rejected_rows] == [
        "EMPTY_REQUIRED_FIELD:company",
        "EMPTY_REQUIRED_FIELD:url",
        "INVALID_DATE:posted_at",
    ]


def test_rejected_count_integer_equals_rejected_rows_length() -> None:
    _, rejected_rows, rejected_count = validate_csv(
        FIXTURES_DIR / "mixed_valid_and_invalid_rows.csv"
    )

    assert rejected_count == len(rejected_rows)


def test_rejected_rows_carry_non_empty_reason_and_correct_one_based_row_number() -> None:
    _, rejected_rows, _ = validate_csv(FIXTURES_DIR / "mixed_valid_and_invalid_rows.csv")

    assert [(row.row_number, row.reason) for row in rejected_rows] == [
        (2, "EMPTY_REQUIRED_FIELD:company"),
        (3, "EMPTY_REQUIRED_FIELD:url"),
        (4, "INVALID_DATE:posted_at"),
    ]
    assert all(row.reason.strip() for row in rejected_rows)
