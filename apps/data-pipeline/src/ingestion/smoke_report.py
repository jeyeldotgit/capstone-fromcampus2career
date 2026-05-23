from __future__ import annotations

"""Structured local pipeline smoke report.

The structural pipeline confidence score is computed from emitted counters only:

    score = (0.35 * validation_pass_rate)
          + (0.35 * role_match_rate)
          + (0.30 * skill_match_rate)

where validation_pass_rate is valid rows divided by source rows, role_match_rate
is matched rows divided by deduplicated rows, and skill_match_rate is skill
matches divided by deduplicated rows, capped at 1.0. This is operational
confidence in the run shape, not a guarantee of intelligence quality.
"""

from collections import Counter
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

VALIDATION_PASS_RATE_WEIGHT = 0.35
ROLE_MATCH_RATE_WEIGHT = 0.35
SKILL_MATCH_RATE_WEIGHT = 0.30
MANUAL_REVIEW_CONFIDENCE_THRESHOLD = 0.80

PipelineJobStatus = Literal["complete", "partial", "failed"]


class SmokeReportCounters(BaseModel):
    rows_read_from_source_csv: int = Field(default=0, ge=0)
    rows_passing_adapter_mapping: int = Field(default=0, ge=0)
    rows_passing_raw_job_posting_validation: int = Field(default=0, ge=0)
    rows_rejected_by_validation: int = Field(default=0, ge=0)
    rows_surviving_deduplication: int = Field(default=0, ge=0)
    rows_matched_to_canonical_role: int = Field(default=0, ge=0)
    rows_unmatched_to_any_role: int = Field(default=0, ge=0)
    job_postings_inserted: int = Field(default=0, ge=0)
    job_postings_reused_existing: int = Field(default=0, ge=0)
    job_posting_skills_inserted: int = Field(default=0, ge=0)
    job_posting_skills_reused_existing: int = Field(default=0, ge=0)
    skill_matches_produced: int = Field(default=0, ge=0)
    evidence_rows_written_to_pipeline_skill_evidence_summary: int = Field(default=0, ge=0)
    role_skill_pairs_meeting_cumulative_evidence_threshold: int = Field(default=0, ge=0)
    role_skill_requirements_rows_published: int = Field(default=0, ge=0)
    sdi_snapshots_rows_published: int = Field(default=0, ge=0)
    skill_decay_signals_rows_published_or_activated: int = Field(default=0, ge=0)


class SmokeReportInput(BaseModel):
    counters: SmokeReportCounters
    validation_rejection_reasons: list[str] = Field(default_factory=list)
    unmatched_source_role_examples: list[str] = Field(default_factory=list)
    terminal_pipeline_job_status: PipelineJobStatus
    error_message: str | None = None


class SmokeReport(BaseModel):
    report_type: str
    confidence_label: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_formula: str
    confidence_weights: dict[str, float]
    manual_review_recommended_below: float
    manual_review_recommended: bool
    rates: dict[str, float]
    counters: SmokeReportCounters
    top_validation_rejection_reasons: list[dict[str, int | str]]
    unmatched_source_role_examples: list[str]
    terminal_pipeline_job_status: PipelineJobStatus
    error_message: str | None = None


def build_smoke_report(payload: SmokeReportInput) -> SmokeReport:
    counters = payload.counters
    validation_pass_rate = _safe_rate(
        counters.rows_passing_raw_job_posting_validation,
        counters.rows_read_from_source_csv,
    )
    role_match_rate = _safe_rate(
        counters.rows_matched_to_canonical_role,
        counters.rows_surviving_deduplication,
    )
    skill_match_rate = min(
        _safe_rate(
            counters.skill_matches_produced,
            counters.rows_surviving_deduplication,
        ),
        1.0,
    )
    confidence_score = round(
        (VALIDATION_PASS_RATE_WEIGHT * validation_pass_rate)
        + (ROLE_MATCH_RATE_WEIGHT * role_match_rate)
        + (SKILL_MATCH_RATE_WEIGHT * skill_match_rate),
        4,
    )

    return SmokeReport(
        report_type="phase1_pipeline_smoke_report",
        confidence_label="structural_pipeline_confidence",
        confidence_score=confidence_score,
        confidence_formula=(
            "0.35*validation_pass_rate + 0.35*role_match_rate + "
            "0.30*skill_match_rate"
        ),
        confidence_weights={
            "validation_pass_rate": VALIDATION_PASS_RATE_WEIGHT,
            "role_match_rate": ROLE_MATCH_RATE_WEIGHT,
            "skill_match_rate": SKILL_MATCH_RATE_WEIGHT,
        },
        manual_review_recommended_below=MANUAL_REVIEW_CONFIDENCE_THRESHOLD,
        manual_review_recommended=confidence_score < MANUAL_REVIEW_CONFIDENCE_THRESHOLD,
        rates={
            "validation_pass_rate": validation_pass_rate,
            "role_match_rate": role_match_rate,
            "skill_match_rate": skill_match_rate,
        },
        counters=counters,
        top_validation_rejection_reasons=_top_reasons(payload.validation_rejection_reasons),
        unmatched_source_role_examples=_unique_examples(payload.unmatched_source_role_examples),
        terminal_pipeline_job_status=payload.terminal_pipeline_job_status,
        error_message=payload.error_message,
    )


def smoke_report_to_json(report: SmokeReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True)


def smoke_report_to_terminal_summary(report: SmokeReport) -> str:
    lines = [
        "Phase 1 pipeline smoke report",
        f"status: {report.terminal_pipeline_job_status}",
        f"{report.confidence_label}: {report.confidence_score:.4f}",
        f"formula: {report.confidence_formula}",
        (
            "manual_review_recommended: "
            f"{str(report.manual_review_recommended).lower()} "
            f"(threshold < {report.manual_review_recommended_below:.2f})"
        ),
        "",
        smoke_report_to_json(report),
    ]
    return "\n".join(lines)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _top_reasons(reasons: list[str]) -> list[dict[str, int | str]]:
    return [
        {"reason": reason, "count": count}
        for reason, count in Counter(reasons).most_common(5)
    ]


def _unique_examples(examples: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for example in examples:
        normalized = example.strip()
        if normalized == "" or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
        if len(unique) == 5:
            break
    return unique
