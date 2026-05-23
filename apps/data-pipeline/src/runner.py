from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, text

from src import db
from src.contracts.mapped_skill import MappedRoleSkillRow, MappedSkillItem
from src.contracts.normalized_job_posting import NormalizedJobPosting, normalize_job_posting
from src.contracts.sdi_snapshot import SdiSnapshotPublishRow
from src.contracts.skill_decay_signal import SkillDecaySignalPublishRow
from src.db import app_event_repo, pipeline_job_repo, rejected_row_writer
from src.db.rejected_row_writer import write_rejected_rows
from src.ingestion.deduplication import deduplicate_job_postings
from src.ingestion.jobstreet_adapter import adapt_jobstreet_rows
from src.ingestion.rejected_row import RejectedRow
from src.ingestion.smoke_report import (
    SmokeReportCounters,
    SmokeReportInput,
    build_smoke_report,
    smoke_report_to_terminal_summary,
)
from src.ingestion.validator import read_csv_rows, validate_rows
from src.intelligence.alias_lookup import SkillLookupItem, build_alias_lookup, load_skill_alias_rows, normalize_signal
from src.intelligence.decay import HistoricalSdiSnapshotRow, detect_decay_signals
from src.intelligence.role_requirement_aggregator import aggregate_role_requirements
from src.intelligence.sdi import compute_sdi, load_sdi_posting_skill_rows
from src.intelligence.skill_mapper import map_skills
from src.main import PipelineResult, run_pipeline_job
from src.normalization.role_hint_normalizer import normalize_role_hint
from src.publishing.decay_publisher import publish_decay_signals
from src.publishing.role_requirement_publisher import publish_role_requirements
from src.publishing.sdi_publisher import publish_sdi_snapshots

SUPPORTED_SOURCES = ("jobstreet", "canonical")


class RunnerError(RuntimeError):
    pass


class RunnerExecutionError(RunnerError):
    def __init__(self, report_text: str) -> None:
        super().__init__("local pipeline runner failed")
        self.report_text = report_text


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    dry_run = not args.live
    try:
        report_text = run_local_pipeline(
            csv_path=args.csv_path,
            source=args.source,
            dry_run=dry_run,
        )
    except RunnerExecutionError as error:
        print(error.report_text)
        return 1
    except Exception as error:
        print(
            smoke_report_to_terminal_summary(
                build_smoke_report(
                    SmokeReportInput(
                        counters=SmokeReportCounters(),
                        terminal_pipeline_job_status="failed",
                        error_message=_to_error_message(error),
                    )
                )
            )
        )
        return 1

    print(report_text)
    return 0


def run_local_pipeline(*, csv_path: Path, source: str, dry_run: bool = True) -> str:
    if source not in SUPPORTED_SOURCES:
        raise RunnerError(f"unsupported source '{source}'; expected one of {', '.join(SUPPORTED_SOURCES)}")

    engine = db.get_engine()
    connection = engine.connect()
    transaction = connection.begin()
    should_commit = not dry_run
    try:
        with _bind_repository_connections(connection):
            report_text = _run_pipeline_in_connection(
                connection=connection,
                csv_path=csv_path,
                source=source,
            )
        if should_commit:
            transaction.commit()
        else:
            transaction.rollback()
        return report_text
    except Exception:
        transaction.rollback()
        raise
    finally:
        connection.close()


def _run_pipeline_in_connection(*, connection: Connection, csv_path: Path, source: str) -> str:
    source_rows = read_csv_rows(csv_path)
    counters = SmokeReportCounters(rows_read_from_source_csv=len(source_rows))
    validation_rejection_reasons: list[str] = []
    unmatched_role_examples: list[str] = []
    source_role_hints_by_external_id: dict[str, str] = {
        str(row.get("posting_id") or row.get("external_id") or ""): str(
            row.get("role_normalized") or row.get("role") or row.get("title") or ""
        )
        for row in source_rows
    }

    dataset_id = _insert_dataset(connection=connection, csv_path=csv_path, source=source)
    def _pipeline_callback(job_id: UUID) -> PipelineResult:
        if source == "jobstreet":
            valid_rows, adaptation_failures = adapt_jobstreet_rows(source_rows)
            counters.rows_passing_adapter_mapping = len(valid_rows)
            rejected_rows = [
                RejectedRow(
                    row_number=failure.row_number,
                    raw_payload=failure.raw_payload,
                    reason=failure.reason,
                )
                for failure in adaptation_failures
            ]
        else:
            valid_rows, rejected_rows, _rejected_count = validate_rows(source_rows)
            counters.rows_passing_adapter_mapping = len(valid_rows)

        validation_rejection_reasons.extend(row.reason for row in rejected_rows)
        counters.rows_passing_raw_job_posting_validation = len(valid_rows)
        counters.rows_rejected_by_validation = len(rejected_rows)
        write_rejected_rows(pipeline_job_id=job_id, rejected_rows=rejected_rows)

        normalized_rows = [
            normalize_job_posting(
                posting,
                source_row_number=index + 1,
                ingested_at=datetime.now(timezone.utc),
            )
            for index, posting in enumerate(valid_rows)
        ]
        deduplicated_rows = deduplicate_job_postings(normalized_rows)
        counters.rows_surviving_deduplication = len(deduplicated_rows)

        role_alias_lookup = _load_role_alias_lookup(connection)
        skill_alias_lookup = build_alias_lookup(load_skill_alias_rows(connection=connection))
        skill_name_lookup = _load_skill_name_lookup(connection)
        role_totals: dict[UUID, set[UUID]] = defaultdict(set)
        mapped_rows: list[MappedRoleSkillRow] = []

        for posting in deduplicated_rows:
            role_hint = source_role_hints_by_external_id.get(posting.external_id) or posting.normalized_role_hint
            role_id = role_alias_lookup.get(normalize_role_hint(role_hint))
            if role_id is None:
                unmatched_role_examples.append(role_hint)
                counters.rows_unmatched_to_any_role += 1
                continue

            counters.rows_matched_to_canonical_role += 1
            posting_id = _insert_job_posting(
                connection=connection,
                dataset_id=dataset_id,
                role_id=role_id,
                posting=posting,
            )
            mapping_posting = posting.model_copy(update={"external_id": str(posting_id)})
            mapping_result = map_skills(
                posting=mapping_posting,
                alias_lookup=skill_alias_lookup,
                skill_name_lookup=skill_name_lookup,
            )
            unique_mapped_skills = _deduplicate_mapped_skills(mapping_result.mapped)
            role_totals[role_id].add(posting_id)
            counters.skill_matches_produced += len(unique_mapped_skills)
            for mapped_skill in unique_mapped_skills:
                _insert_job_posting_skill(
                    connection=connection,
                    posting_id=posting_id,
                    role_id=role_id,
                    skill_id=mapped_skill.skill_id,
                    normalized_depth=0.8,
                )
                mapped_rows.append(
                    MappedRoleSkillRow(
                        job_posting_id=posting_id,
                        role_id=role_id,
                        skill_id=mapped_skill.skill_id,
                        normalized_depth=0.8,
                    )
                )

        aggregates = aggregate_role_requirements(
            pipeline_job_id=job_id,
            dataset_id=dataset_id,
            mapped_rows=mapped_rows,
            total_matched_postings_by_role={
                role_id: len(posting_ids)
                for role_id, posting_ids in role_totals.items()
            },
            connection=connection,
        )
        counters.evidence_rows_written_to_pipeline_skill_evidence_summary = _count_evidence_rows(
            connection,
            job_id,
        )
        counters.role_skill_pairs_meeting_cumulative_evidence_threshold = _count_threshold_met_evidence_rows(
            connection,
            job_id,
        )

        output_version = publish_role_requirements(
            dataset_id=dataset_id,
            requirements=aggregates,
            connection=connection,
        )
        counters.role_skill_requirements_rows_published = len(aggregates)

        sdi_input_rows = load_sdi_posting_skill_rows(
            connection=connection,
            dataset_id=dataset_id,
            requirement_version=output_version,
        )
        snapshot_date = _snapshot_date(valid_rows)
        sdi_rows = compute_sdi(sdi_input_rows, snapshot_date=snapshot_date)
        publish_sdi_snapshots(
            requirement_version=output_version,
            rows=[
                SdiSnapshotPublishRow(
                    role_id=row.role_id,
                    skill_id=row.skill_id,
                    demand_index=row.demand_index,
                    snapshot_date=snapshot_date,
                    requirement_version=output_version,
                )
                for row in sdi_rows
            ],
            connection=connection,
        )
        counters.sdi_snapshots_rows_published = len(sdi_rows)

        decay_input_rows = _load_decay_input_rows(
            connection=connection,
            role_skill_pairs=[(row.role_id, row.skill_id) for row in sdi_rows],
        )
        decay_rows = detect_decay_signals(decay_input_rows)
        publish_decay_signals(
            requirement_version=output_version,
            rows=[
                SkillDecaySignalPublishRow(
                    role_id=row.role_id,
                    skill_id=row.skill_id,
                    decay_rate=row.decay_rate,
                    confidence=row.confidence,
                    detected_at=datetime.combine(snapshot_date, datetime.min.time(), tzinfo=timezone.utc),
                    requirement_version=output_version,
                    is_active=True,
                )
                for row in decay_rows
            ],
            connection=connection,
        )
        counters.skill_decay_signals_rows_published_or_activated = len(decay_rows)

        return PipelineResult(
            processed_rows=len(deduplicated_rows),
            rejected_rows=len(rejected_rows),
            output_version=output_version,
        )

    terminal_status = "failed"
    error_message: str | None = None
    try:
        job_id = run_pipeline_job(dataset_id=dataset_id, job_type="ingestion", run_pipeline=_pipeline_callback)
        terminal_status = _load_pipeline_job_status(connection=connection, job_id=job_id)
    except Exception as error:
        error_message = _to_error_message(error)
        terminal_status = "failed"
        report = build_smoke_report(
            SmokeReportInput(
                counters=counters,
                validation_rejection_reasons=validation_rejection_reasons,
                unmatched_source_role_examples=unmatched_role_examples,
                terminal_pipeline_job_status=terminal_status,
                error_message=error_message,
            )
        )
        raise RunnerExecutionError(smoke_report_to_terminal_summary(report)) from error

    report = build_smoke_report(
        SmokeReportInput(
            counters=counters,
            validation_rejection_reasons=validation_rejection_reasons,
            unmatched_source_role_examples=unmatched_role_examples,
            terminal_pipeline_job_status=terminal_status,
            error_message=error_message,
        )
    )
    return smoke_report_to_terminal_summary(report)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local Phase 1 pipeline smoke test.")
    parser.add_argument("--csv-path", type=Path, required=True, help="Path to the source CSV file.")
    parser.add_argument("--source", choices=SUPPORTED_SOURCES, required=True, help="Source adapter to use.")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run all stages and roll back database writes before exit. This is the default.",
    )
    mode_group.add_argument(
        "--live",
        action="store_true",
        help="Persist pipeline writes. Required for committed database changes.",
    )
    return parser.parse_args(argv)


@contextmanager
def _bind_repository_connections(connection: Connection) -> Iterator[None]:
    @contextmanager
    def _managed_connection() -> Iterator[Connection]:
        yield connection

    modules = (pipeline_job_repo, app_event_repo, rejected_row_writer)
    original_get_connections: list[tuple[Any, Callable[[], Any]]] = [
        (module, module.get_connection)
        for module in modules
    ]
    try:
        for module, _original in original_get_connections:
            module.get_connection = _managed_connection  # type: ignore[method-assign]
        yield
    finally:
        for module, original in original_get_connections:
            module.get_connection = original  # type: ignore[method-assign]


def _insert_dataset(*, connection: Connection, csv_path: Path, source: str) -> UUID:
    return UUID(
        str(
            connection.execute(
                text(
                    """
                    insert into market_datasets (file_path, source, status)
                    values (:file_path, :source, 'uploaded')
                    returning id
                    """
                ),
                {"file_path": str(csv_path), "source": source},
            ).scalar_one()
        )
    )


def _load_role_alias_lookup(connection: Connection) -> dict[str, UUID]:
    return {
        str(row["normalized_alias"]): UUID(str(row["role_id"]))
        for row in connection.execute(
            text(
                """
                select normalized_alias, role_id
                from career_role_aliases
                order by normalized_alias
                """
            )
        ).mappings()
    }


def _load_skill_name_lookup(connection: Connection) -> dict[str, SkillLookupItem]:
    return {
        normalize_signal(str(row["name"])): SkillLookupItem(
            skill_id=UUID(str(row["id"])),
            skill_name=str(row["name"]),
        )
        for row in connection.execute(
            text(
                """
                select id, name
                from skills
                where is_active = true
                order by name
                """
            )
        ).mappings()
    }


def _insert_job_posting(
    *,
    connection: Connection,
    dataset_id: UUID,
    role_id: UUID,
    posting: NormalizedJobPosting,
) -> UUID:
    return UUID(
        str(
            connection.execute(
                text(
                    """
                    insert into job_postings (
                        dataset_id,
                        source,
                        title,
                        company,
                        raw_text,
                        role_id,
                        posted_at,
                        ingested_at
                    )
                    values (
                        :dataset_id,
                        :source,
                        :title,
                        :company,
                        :raw_text,
                        :role_id,
                        :posted_at,
                        :ingested_at
                    )
                    returning id
                    """
                ),
                {
                    "dataset_id": dataset_id,
                    "source": posting.normalized_source,
                    "title": posting.normalized_title,
                    "company": posting.normalized_company,
                    "raw_text": posting.normalized_description,
                    "role_id": role_id,
                    "posted_at": posting.posted_at,
                    "ingested_at": posting.ingested_at,
                },
            ).scalar_one()
        )
    )


def _insert_job_posting_skill(
    *,
    connection: Connection,
    posting_id: UUID,
    role_id: UUID,
    skill_id: UUID,
    normalized_depth: float,
) -> None:
    connection.execute(
        text(
            """
            insert into job_posting_skills (
                job_posting_id,
                role_id,
                skill_id,
                normalized_depth
            )
            values (
                :job_posting_id,
                :role_id,
                :skill_id,
                :normalized_depth
            )
            """
        ),
        {
            "job_posting_id": posting_id,
            "role_id": role_id,
            "skill_id": skill_id,
            "normalized_depth": normalized_depth,
        },
    )


def _deduplicate_mapped_skills(mapped_skills: list[MappedSkillItem]) -> list[MappedSkillItem]:
    seen_skill_ids: set[UUID] = set()
    unique_skills: list[MappedSkillItem] = []
    for mapped_skill in mapped_skills:
        if mapped_skill.skill_id in seen_skill_ids:
            continue
        seen_skill_ids.add(mapped_skill.skill_id)
        unique_skills.append(mapped_skill)
    return unique_skills


def _load_decay_input_rows(
    *,
    connection: Connection,
    role_skill_pairs: list[tuple[UUID, UUID]],
) -> list[HistoricalSdiSnapshotRow]:
    rows: list[HistoricalSdiSnapshotRow] = []
    for role_id, skill_id in sorted(set(role_skill_pairs), key=lambda pair: (str(pair[0]), str(pair[1]))):
        for row in connection.execute(
            text(
                """
                select role_id, skill_id, demand_index, snapshot_date, requirement_version
                from sdi_snapshots
                where role_id = :role_id
                  and skill_id = :skill_id
                order by snapshot_date, requirement_version
                """
            ),
            {"role_id": role_id, "skill_id": skill_id},
        ).mappings():
            rows.append(
                HistoricalSdiSnapshotRow(
                    role_id=UUID(str(row["role_id"])),
                    skill_id=UUID(str(row["skill_id"])),
                    demand_index=float(row["demand_index"]),
                    snapshot_date=row["snapshot_date"],
                    requirement_version=int(row["requirement_version"]),
                )
            )
    return rows


def _count_evidence_rows(connection: Connection, job_id: UUID) -> int:
    return int(
        connection.execute(
            text("select count(*) from pipeline_skill_evidence_summary where pipeline_job_id = :job_id"),
            {"job_id": job_id},
        ).scalar_one()
    )


def _count_threshold_met_evidence_rows(connection: Connection, job_id: UUID) -> int:
    return int(
        connection.execute(
            text(
                """
                select count(*)
                from pipeline_skill_evidence_summary
                where pipeline_job_id = :job_id
                  and threshold_met = true
                """
            ),
            {"job_id": job_id},
        ).scalar_one()
    )


def _load_pipeline_job_status(*, connection: Connection, job_id: UUID) -> str:
    status = str(
        connection.execute(
            text("select status from pipeline_jobs where id = :job_id"),
            {"job_id": job_id},
        ).scalar_one()
    )
    if status not in {"complete", "partial", "failed"}:
        raise RunnerError(f"pipeline job ended in non-terminal status '{status}'")
    return status


def _snapshot_date(rows: list[Any]) -> date:
    if len(rows) == 0:
        return date.today()
    return max(row.posted_at for row in rows)


def _to_error_message(error: Exception) -> str:
    message = str(error).strip()
    return message if message else error.__class__.__name__


if __name__ == "__main__":
    raise SystemExit(main())
