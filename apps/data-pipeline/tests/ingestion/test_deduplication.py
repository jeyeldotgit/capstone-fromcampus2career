from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.contracts.normalized_job_posting import NormalizedJobPosting, normalize_job_posting
from src.contracts.raw_job_posting import RawJobPosting
from src.ingestion.deduplication import deduplicate_job_postings

INGESTED_AT = datetime(2026, 5, 10, 10, 0, tzinfo=timezone.utc)

BASE_ROW: dict[str, object] = {
    "external_id": "job-001",
    "source": "Acme Jobs",
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


def _posting(
    *,
    row_number: int,
    external_id: str,
    source: str = "Acme Jobs",
    title: str = "Data Analyst",
    company: str = "Acme Inc",
    posted_at: str = "2026-05-01",
) -> NormalizedJobPosting:
    return normalize_job_posting(
        RawJobPosting.model_validate(
            {
                **BASE_ROW,
                "external_id": external_id,
                "source": source,
                "title": title,
                "company": company,
                "posted_at": posted_at,
                "url": f"https://example.com/jobs/{external_id}",
            }
        ),
        source_row_number=row_number,
        ingested_at=INGESTED_AT,
    )


def _serialized(postings: list[NormalizedJobPosting]) -> str:
    payload = [posting.model_dump(mode="json") for posting in postings]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def test_two_rows_with_identical_key_return_one_survivor() -> None:
    first = _posting(row_number=1, external_id="job-001")
    duplicate = _posting(row_number=2, external_id="job-002")

    result = deduplicate_job_postings([first, duplicate])

    assert result == [first]


def test_three_rows_where_two_share_key_return_two_rows() -> None:
    first = _posting(row_number=1, external_id="job-001")
    duplicate = _posting(row_number=2, external_id="job-002")
    unique = _posting(row_number=3, external_id="job-003", title="Backend Engineer")

    result = deduplicate_job_postings([first, duplicate, unique])

    assert result == [first, unique]


def test_empty_input_returns_empty_output() -> None:
    assert deduplicate_job_postings([]) == []


def test_all_unique_rows_are_returned_unchanged() -> None:
    first = _posting(row_number=1, external_id="job-001", title="Data Analyst")
    second = _posting(row_number=2, external_id="job-002", title="Backend Engineer")

    result = deduplicate_job_postings([first, second])

    assert result == [first, second]


def test_duplicate_key_with_differing_input_order_keeps_same_lowest_row_survivor() -> None:
    first = _posting(row_number=1, external_id="job-001")
    middle = _posting(row_number=2, external_id="job-002")
    last = _posting(row_number=3, external_id="job-003")

    forward_result = deduplicate_job_postings([first, middle, last])
    reversed_result = deduplicate_job_postings([last, middle, first])

    assert forward_result == [first]
    assert reversed_result == [first]


def test_repeated_execution_on_same_input_is_byte_equivalent() -> None:
    rows = [
        _posting(row_number=3, external_id="job-003", title="Backend Engineer"),
        _posting(row_number=1, external_id="job-001"),
        _posting(row_number=2, external_id="job-002"),
    ]

    first_result = deduplicate_job_postings(rows)
    second_result = deduplicate_job_postings(rows)

    assert _serialized(first_result) == _serialized(second_result)


def test_punctuation_case_and_whitespace_variants_share_duplicate_key() -> None:
    first = _posting(row_number=1, external_id="job-001", title="Data Analyst", company="Acme Inc")
    duplicate = _posting(
        row_number=2,
        external_id="job-002",
        source=" acme   jobs ",
        title="DATA--Analyst!!!",
        company="Acme, Inc.",
    )

    result = deduplicate_job_postings([duplicate, first])

    assert result == [first]
