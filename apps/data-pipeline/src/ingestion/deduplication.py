from __future__ import annotations

import polars as pl

from src.contracts.normalized_job_posting import NormalizedJobPosting

_DEDUPLICATION_KEY: tuple[str, ...] = (
    "source",
    "title",
    "company",
    "posted_at",
)


def deduplicate_job_postings(
    postings: list[NormalizedJobPosting],
) -> list[NormalizedJobPosting]:
    if len(postings) == 0:
        return []

    frame = pl.DataFrame(
        [
            {
                "source": posting.normalized_source,
                "title": posting.normalized_title,
                "company": posting.normalized_company,
                "posted_at": posting.posted_at,
                "source_row_number": posting.source_row_number,
            }
            for posting in postings
        ]
    )

    # Duplicate survivors are selected by the lowest source row number so the
    # same CSV row wins even when callers provide rows in a different order.
    survivor_row_numbers = (
        frame.sort([*_DEDUPLICATION_KEY, "source_row_number"])
        .group_by(_DEDUPLICATION_KEY, maintain_order=True)
        .agg(pl.col("source_row_number").first())
        .sort("source_row_number")
        .get_column("source_row_number")
        .to_list()
    )

    survivors_by_row_number = {posting.source_row_number: posting for posting in postings}
    return [survivors_by_row_number[row_number] for row_number in survivor_row_numbers]
