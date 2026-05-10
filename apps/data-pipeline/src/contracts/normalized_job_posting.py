from __future__ import annotations

from datetime import datetime

from pydantic import Field

from src.contracts.raw_job_posting import RawJobPosting
from src.normalization.text_cleaner import clean_text


class NormalizedJobPosting(RawJobPosting):
    source_row_number: int = Field(gt=0)
    ingested_at: datetime
    normalized_source: str = Field(min_length=1)
    normalized_title: str = Field(min_length=1)
    normalized_company: str = Field(min_length=1)
    normalized_location: str
    normalized_description: str
    normalized_role_hint: str = Field(min_length=1)


def normalize_job_posting(
    posting: RawJobPosting,
    *,
    source_row_number: int,
    ingested_at: datetime,
) -> NormalizedJobPosting:
    normalized_title = clean_text(posting.title)

    return NormalizedJobPosting.model_validate(
        {
            **posting.model_dump(),
            "source_row_number": source_row_number,
            "ingested_at": ingested_at,
            "normalized_source": clean_text(posting.source),
            "normalized_title": normalized_title,
            "normalized_company": clean_text(posting.company),
            "normalized_location": clean_text(posting.location),
            "normalized_description": clean_text(posting.description),
            "normalized_role_hint": normalized_title,
        }
    )
