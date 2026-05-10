from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.contracts.normalized_job_posting import NormalizedJobPosting, normalize_job_posting
from src.contracts.raw_job_posting import RawJobPosting
from src.normalization.text_cleaner import clean_text, collapse_whitespace, strip_common_punctuation


BASE_ROW: dict[str, object] = {
    "external_id": "job-001",
    "source": "Acme Jobs",
    "title": "  Data Analyst!!!  ",
    "company": "Acme, Inc.",
    "location": "  Remote   PH ",
    "posted_at": "2026-05-01",
    "description": "Analyze: product-data; dashboards.",
    "url": "https://example.com/jobs/1",
    "employment_type": "Full-time",
    "salary_min": "70000",
    "salary_max": "90000",
    "currency": "USD",
    "experience_level": "Entry",
}


def test_collapse_whitespace_trims_and_reduces_internal_runs() -> None:
    assert collapse_whitespace("  data\t\tanalyst\nrole  ") == "data analyst role"


def test_strip_common_punctuation_replaces_punctuation_with_spaces() -> None:
    assert strip_common_punctuation("Data-Analyst, dashboards/API.") == "Data Analyst  dashboards API "


def test_clean_text_lowercases_strips_punctuation_and_collapses_whitespace() -> None:
    assert clean_text("  Senior, DATA--Analyst!!!  ") == "senior data analyst"


def test_punctuation_case_and_whitespace_variants_match() -> None:
    values = [
        "Data Analyst",
        " data   analyst ",
        "DATA-ANALYST",
        "Data, Analyst!",
    ]

    assert {clean_text(value) for value in values} == {"data analyst"}


def test_normalized_job_posting_validates_from_s07_row_shape() -> None:
    raw_posting = RawJobPosting.model_validate(BASE_ROW)

    normalized = normalize_job_posting(
        raw_posting,
        source_row_number=7,
        ingested_at=datetime(2026, 5, 10, 10, 0, tzinfo=timezone.utc),
    )

    assert isinstance(normalized, NormalizedJobPosting)
    assert normalized.source_row_number == 7
    assert normalized.normalized_source == "acme jobs"
    assert normalized.normalized_title == "data analyst"
    assert normalized.normalized_company == "acme inc"
    assert normalized.normalized_location == "remote ph"
    assert normalized.normalized_description == "analyze product data dashboards"
    assert normalized.normalized_role_hint == "data analyst"
