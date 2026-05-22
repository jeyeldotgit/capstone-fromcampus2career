from __future__ import annotations

import os
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
import sys
from typing import Callable
from uuid import UUID

import pytest
from sqlalchemy import Connection, Engine, create_engine, text

APPS_PIPELINE_DIR = Path(__file__).resolve().parents[2] / "apps" / "data-pipeline"
if str(APPS_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_PIPELINE_DIR))

from src.contracts.mapped_skill import MappedRoleSkillRow
from src.contracts.sdi_snapshot import SdiSnapshotPublishRow
from src.contracts.skill_decay_signal import SkillDecaySignalPublishRow
from src.db import get_connection
from src.db.rejected_row_writer import write_rejected_rows
from src.ingestion.deduplication import deduplicate_job_postings
from src.ingestion.validator import validate_csv
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

DATABASE_URL = os.getenv("DATABASE_URL")
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

VALID_DATASET_SOURCE = "p1-s13-e2e-valid"
MIXED_DATASET_SOURCE = "p1-s13-e2e-mixed"
VALID_FILE_PATH = "p1-s13-e2e-valid-postings.csv"
MIXED_FILE_PATH = "p1-s13-e2e-mixed-postings.csv"
DATASET_SOURCE_PREFIX = "p1-s13-e2e-"

ROLE_ALIAS_TOKEN = "data analytics specialist"
PYTHON_ALIAS_TOKEN = "python3"
SQL_ALIAS_TOKEN = "sql queries"

HISTORICAL_DATE_1 = date(2026, 1, 1)
HISTORICAL_DATE_2 = date(2026, 3, 1)
VALID_SNAPSHOT_DATE = date(2026, 6, 1)
MIXED_SNAPSHOT_DATE = date(2026, 7, 1)
HISTORICAL_VERSION_1 = 900001
HISTORICAL_VERSION_2 = 900002


class RunOutcome:
    def __init__(self, *, dataset_id: UUID, job_id: UUID, output_version: int) -> None:
        self.dataset_id = dataset_id
        self.job_id = job_id
        self.output_version = output_version


@pytest.fixture(scope="session")
def engine() -> Engine:
    if DATABASE_URL is None:
        pytest.fail("DATABASE_URL is required for tests/e2e/test_phase1_pipeline_e2e.py")
    return create_engine(DATABASE_URL, future=True)


def test_phase1_pipeline_e2e_complete_and_partial_paths(engine: Engine) -> None:
    with engine.begin() as connection:
        role_id, python_skill_id, sql_skill_id = _assert_seeded_aliases(connection)
        _cleanup_previous_artifacts(connection, role_id, (python_skill_id, sql_skill_id))

    valid_outcome = _run_fixture(
        engine=engine,
        dataset_source=VALID_DATASET_SOURCE,
        dataset_file_path=VALID_FILE_PATH,
        fixture_path=FIXTURES_DIR / "valid_postings.csv",
        snapshot_date=VALID_SNAPSHOT_DATE,
    )
    mixed_outcome = _run_fixture(
        engine=engine,
        dataset_source=MIXED_DATASET_SOURCE,
        dataset_file_path=MIXED_FILE_PATH,
        fixture_path=FIXTURES_DIR / "mixed_postings.csv",
        snapshot_date=MIXED_SNAPSHOT_DATE,
    )

    with engine.begin() as connection:
        _assert_pipeline_job(
            connection=connection,
            job_id=valid_outcome.job_id,
            expected_status="complete",
            expected_processed_rows=10,
            expected_rejected_rows=0,
            expected_output_version=valid_outcome.output_version,
        )
        _assert_pipeline_job(
            connection=connection,
            job_id=mixed_outcome.job_id,
            expected_status="partial",
            expected_processed_rows=10,
            expected_rejected_rows=2,
            expected_output_version=mixed_outcome.output_version,
        )

        _assert_rejected_rows(
            connection=connection,
            job_id=valid_outcome.job_id,
            expected=[],
        )
        _assert_rejected_rows(
            connection=connection,
            job_id=mixed_outcome.job_id,
            expected=[
                (11, "EMPTY_REQUIRED_FIELD:company"),
                (12, "EMPTY_REQUIRED_FIELD:url"),
            ],
        )

        _assert_terminal_event(
            connection=connection,
            job_id=valid_outcome.job_id,
            expected_status="complete",
            expected_output_version=valid_outcome.output_version,
        )
        _assert_terminal_event(
            connection=connection,
            job_id=mixed_outcome.job_id,
            expected_status="partial",
            expected_output_version=mixed_outcome.output_version,
        )

        _assert_requirement_version_for_dataset(
            connection=connection,
            dataset_id=valid_outcome.dataset_id,
            expected_version=valid_outcome.output_version,
            expected_is_current=False,
        )
        _assert_requirement_version_for_dataset(
            connection=connection,
            dataset_id=mixed_outcome.dataset_id,
            expected_version=mixed_outcome.output_version,
            expected_is_current=True,
        )

        valid_pairs = _assert_role_skill_requirements(
            connection=connection,
            requirement_version=valid_outcome.output_version,
            expected_row_count=2,
            expected_evidence_count=5,
        )
        mixed_pairs = _assert_role_skill_requirements(
            connection=connection,
            requirement_version=mixed_outcome.output_version,
            expected_row_count=2,
            expected_evidence_count=10,
        )

        _assert_evidence_summary_rows(
            connection=connection,
            job_id=valid_outcome.job_id,
            expected_pairs=valid_pairs,
        )
        _assert_evidence_summary_rows(
            connection=connection,
            job_id=mixed_outcome.job_id,
            expected_pairs=mixed_pairs,
        )

        _assert_sdi_snapshots(
            connection=connection,
            requirement_version=valid_outcome.output_version,
            expected_row_count=2,
        )
        _assert_sdi_snapshots(
            connection=connection,
            requirement_version=mixed_outcome.output_version,
            expected_row_count=2,
        )

        _assert_decay_signals(
            connection=connection,
            requirement_version=valid_outcome.output_version,
            expected_row_count=2,
            expected_is_active=False,
        )
        _assert_decay_signals(
            connection=connection,
            requirement_version=mixed_outcome.output_version,
            expected_row_count=2,
            expected_is_active=True,
        )


def _run_fixture(
    *,
    engine: Engine,
    dataset_source: str,
    dataset_file_path: str,
    fixture_path: Path,
    snapshot_date: date,
) -> RunOutcome:
    with engine.begin() as connection:
        dataset_id = _insert_dataset(
            connection=connection,
            source=dataset_source,
            file_path=dataset_file_path,
        )

    callback = _build_pipeline_callback(
        dataset_id=dataset_id,
        fixture_path=fixture_path,
        snapshot_date=snapshot_date,
    )
    job_id = run_pipeline_job(dataset_id=dataset_id, job_type="ingestion", run_pipeline=callback)

    with engine.begin() as connection:
        output_version = int(
            connection.execute(
                text(
                    """
                    select output_version
                    from pipeline_jobs
                    where id = :job_id
                    """
                ),
                {"job_id": job_id},
            ).scalar_one()
        )

    return RunOutcome(dataset_id=dataset_id, job_id=job_id, output_version=output_version)


def _build_pipeline_callback(
    *,
    dataset_id: UUID,
    fixture_path: Path,
    snapshot_date: date,
) -> Callable[[UUID], PipelineResult]:
    def _run(job_id: UUID) -> PipelineResult:
        valid_rows, rejected_rows, _rejected_count = validate_csv(fixture_path)
        write_rejected_rows(pipeline_job_id=job_id, rejected_rows=rejected_rows)

        with get_connection() as connection:
            normalized_rows = [
                _normalize_row(raw_row=row, row_number=index + 1)
                for index, row in enumerate(valid_rows)
            ]
            deduplicated_rows = deduplicate_job_postings(normalized_rows)
            role_alias_to_id = _load_role_alias_lookup(connection)
            skill_alias_lookup = build_alias_lookup(load_skill_alias_rows(connection=connection))
            skill_name_lookup = _load_skill_name_lookup(connection)

            role_totals: dict[UUID, set[UUID]] = defaultdict(set)
            mapped_rows: list[MappedRoleSkillRow] = []

            for posting in deduplicated_rows:
                normalized_role_alias = normalize_role_hint(posting.normalized_role_hint)
                role_id = role_alias_to_id.get(normalized_role_alias)
                if role_id is None:
                    raise AssertionError(
                        f"No seeded career_role_aliases match normalized title '{normalized_role_alias}'"
                    )

                posting_id = UUID(posting.external_id)
                _insert_job_posting(connection, dataset_id, posting_id, role_id, posting)

                mapping_result = map_skills(
                    posting=posting,
                    alias_lookup=skill_alias_lookup,
                    skill_name_lookup=skill_name_lookup,
                )
                if len(mapping_result.mapped) == 0:
                    raise AssertionError(
                        f"No skills mapped for posting external_id={posting.external_id}"
                    )

                role_totals[role_id].add(posting_id)
                for mapped_skill in mapping_result.mapped:
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
            if len(aggregates) == 0:
                raise AssertionError(
                    "role_requirement_aggregator returned zero publishable pairs; expected at least one"
                )

            output_version = publish_role_requirements(
                dataset_id=dataset_id,
                requirements=aggregates,
                connection=connection,
            )

            sdi_input_rows = load_sdi_posting_skill_rows(
                connection=connection,
                dataset_id=dataset_id,
                requirement_version=output_version,
            )
            sdi_rows = compute_sdi(
                sdi_input_rows,
                snapshot_date=snapshot_date,
            )
            if len(sdi_rows) == 0:
                raise AssertionError(
                    "compute_sdi returned zero rows for published requirements; expected at least one row"
                )

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

            _seed_historical_snapshots(
                connection=connection,
                role_skill_pairs=[(row.role_id, row.skill_id) for row in sdi_rows],
            )
            decay_input_rows = _load_decay_input_rows(
                connection=connection,
                role_skill_pairs=[(row.role_id, row.skill_id) for row in sdi_rows],
                current_requirement_version=output_version,
                current_snapshot_date=snapshot_date,
            )
            decay_rows = detect_decay_signals(decay_input_rows)
            if len(decay_rows) == 0:
                raise AssertionError(
                    "detect_decay_signals returned zero rows; expected deterministic decay signals for published pairs"
                )

            publish_decay_signals(
                requirement_version=output_version,
                rows=[
                    SkillDecaySignalPublishRow(
                        role_id=row.role_id,
                        skill_id=row.skill_id,
                        decay_rate=row.decay_rate,
                        confidence=row.confidence,
                        detected_at=datetime.combine(
                            snapshot_date,
                            datetime.min.time(),
                            tzinfo=timezone.utc,
                        ),
                        requirement_version=output_version,
                        is_active=True,
                    )
                    for row in decay_rows
                ],
                connection=connection,
            )

        return PipelineResult(
            processed_rows=len(deduplicated_rows),
            rejected_rows=len(rejected_rows),
            output_version=output_version,
        )

    return _run


def _normalize_row(*, raw_row: object, row_number: int):
    from src.contracts.normalized_job_posting import normalize_job_posting

    return normalize_job_posting(
        raw_row,
        source_row_number=row_number,
        ingested_at=datetime.now(timezone.utc),
    )


def _load_role_alias_lookup(connection: Connection) -> dict[str, UUID]:
    rows = connection.execute(
        text(
            """
            select normalized_alias, role_id
            from career_role_aliases
            """
        )
    ).mappings()
    return {
        str(row["normalized_alias"]): UUID(str(row["role_id"]))
        for row in rows
    }


def _load_skill_name_lookup(connection: Connection) -> dict[str, SkillLookupItem]:
    rows = connection.execute(
        text(
            """
            select id, name
            from skills
            where is_active = true
            """
        )
    ).mappings()
    return {
        normalize_signal(str(row["name"])): SkillLookupItem(
            skill_id=UUID(str(row["id"])),
            skill_name=str(row["name"]),
        )
        for row in rows
    }


def _insert_dataset(*, connection: Connection, source: str, file_path: str) -> UUID:
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
                {"file_path": file_path, "source": source},
            ).scalar_one()
        )
    )


def _insert_job_posting(
    connection: Connection,
    dataset_id: UUID,
    posting_id: UUID,
    role_id: UUID,
    posting: object,
) -> None:
    from src.contracts.normalized_job_posting import NormalizedJobPosting

    row = NormalizedJobPosting.model_validate(posting)
    connection.execute(
        text(
            """
            insert into job_postings (
                id,
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
                :id,
                :dataset_id,
                :source,
                :title,
                :company,
                :raw_text,
                :role_id,
                :posted_at,
                :ingested_at
            )
            """
        ),
        {
            "id": posting_id,
            "dataset_id": dataset_id,
            "source": row.normalized_source,
            "title": row.normalized_title,
            "company": row.normalized_company,
            "raw_text": row.normalized_description,
            "role_id": role_id,
            "posted_at": row.posted_at,
            "ingested_at": row.ingested_at,
        },
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


def _seed_historical_snapshots(
    *,
    connection: Connection,
    role_skill_pairs: list[tuple[UUID, UUID]],
) -> None:
    for role_id, skill_id in role_skill_pairs:
        connection.execute(
            text(
                """
                insert into sdi_snapshots (
                    role_id,
                    skill_id,
                    demand_index,
                    snapshot_date,
                    requirement_version
                )
                values (
                    :role_id,
                    :skill_id,
                    0.9500,
                    :snapshot_date,
                    :requirement_version
                )
                on conflict (role_id, skill_id, snapshot_date) do nothing
                """
            ),
            {
                "role_id": role_id,
                "skill_id": skill_id,
                "snapshot_date": HISTORICAL_DATE_1,
                "requirement_version": HISTORICAL_VERSION_1,
            },
        )
        connection.execute(
            text(
                """
                insert into sdi_snapshots (
                    role_id,
                    skill_id,
                    demand_index,
                    snapshot_date,
                    requirement_version
                )
                values (
                    :role_id,
                    :skill_id,
                    0.8000,
                    :snapshot_date,
                    :requirement_version
                )
                on conflict (role_id, skill_id, snapshot_date) do nothing
                """
            ),
            {
                "role_id": role_id,
                "skill_id": skill_id,
                "snapshot_date": HISTORICAL_DATE_2,
                "requirement_version": HISTORICAL_VERSION_2,
            },
        )


def _load_decay_input_rows(
    *,
    connection: Connection,
    role_skill_pairs: list[tuple[UUID, UUID]],
    current_requirement_version: int,
    current_snapshot_date: date,
) -> list[HistoricalSdiSnapshotRow]:
    rows: list[HistoricalSdiSnapshotRow] = []
    for role_id, skill_id in role_skill_pairs:
        pair_rows = connection.execute(
            text(
                """
                select role_id, skill_id, demand_index, snapshot_date, requirement_version
                from sdi_snapshots
                where role_id = :role_id
                  and skill_id = :skill_id
                  and (
                    (snapshot_date in (:historical_1, :historical_2) and requirement_version in (:version_1, :version_2))
                    or
                    (snapshot_date = :current_snapshot_date and requirement_version = :current_requirement_version)
                  )
                order by snapshot_date asc
                """
            ),
            {
                "role_id": role_id,
                "skill_id": skill_id,
                "historical_1": HISTORICAL_DATE_1,
                "historical_2": HISTORICAL_DATE_2,
                "version_1": HISTORICAL_VERSION_1,
                "version_2": HISTORICAL_VERSION_2,
                "current_snapshot_date": current_snapshot_date,
                "current_requirement_version": current_requirement_version,
            },
        ).mappings()
        for row in pair_rows:
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


def _assert_seeded_aliases(connection: Connection) -> tuple[UUID, UUID, UUID]:
    role_row = connection.execute(
        text(
            """
            select role_id
            from career_role_aliases
            where normalized_alias = :normalized_alias
            limit 1
            """
        ),
        {"normalized_alias": ROLE_ALIAS_TOKEN},
    ).mappings().one_or_none()
    if role_row is None:
        raise AssertionError(
            "Missing seeded career_role_aliases row for 'data analytics specialist'"
        )

    python_row = connection.execute(
        text(
            """
            select skill_id
            from skill_aliases
            where normalized_alias = :normalized_alias
            limit 1
            """
        ),
        {"normalized_alias": PYTHON_ALIAS_TOKEN},
    ).mappings().one_or_none()
    if python_row is None:
        raise AssertionError("Missing seeded skill_aliases row for 'python3'")

    sql_row = connection.execute(
        text(
            """
            select skill_id
            from skill_aliases
            where normalized_alias = :normalized_alias
            limit 1
            """
        ),
        {"normalized_alias": SQL_ALIAS_TOKEN},
    ).mappings().one_or_none()
    if sql_row is None:
        raise AssertionError("Missing seeded skill_aliases row for 'sql queries'")

    return (
        UUID(str(role_row["role_id"])),
        UUID(str(python_row["skill_id"])),
        UUID(str(sql_row["skill_id"])),
    )


def _cleanup_previous_artifacts(
    connection: Connection,
    role_id: UUID,
    skill_ids: tuple[UUID, UUID],
) -> None:
    dataset_ids = [
        UUID(str(value))
        for value in connection.execute(
            text(
                """
                select id
                from market_datasets
                where source like :source_prefix
                """
            ),
            {"source_prefix": f"{DATASET_SOURCE_PREFIX}%"},
        ).scalars()
    ]
    if len(dataset_ids) > 0:
        for dataset_id in dataset_ids:
            version_rows = connection.execute(
                text(
                    """
                    select version
                    from role_requirement_versions
                    where dataset_id = :dataset_id
                    """
                ),
                {"dataset_id": dataset_id},
            )
            versions = [int(value) for value in version_rows.scalars()]
            for version in versions:
                connection.execute(
                    text(
                        """
                        delete from skill_decay_signals
                        where requirement_version = :requirement_version
                        """
                    ),
                    {"requirement_version": version},
                )
                connection.execute(
                    text(
                        """
                        delete from sdi_snapshots
                        where requirement_version = :requirement_version
                        """
                    ),
                    {"requirement_version": version},
                )
                connection.execute(
                    text(
                        """
                        delete from role_skill_requirements
                        where requirement_version = :requirement_version
                        """
                    ),
                    {"requirement_version": version},
                )
            connection.execute(
                text(
                    """
                    delete from role_requirement_versions
                    where dataset_id = :dataset_id
                    """
                ),
                {"dataset_id": dataset_id},
            )

    job_ids = [
        UUID(str(value))
        for value in connection.execute(
            text(
                """
                select id
                from pipeline_jobs
                where dataset_id in (
                    select id
                    from market_datasets
                    where source like :source_prefix
                )
                """
            ),
            {"source_prefix": f"{DATASET_SOURCE_PREFIX}%"},
        ).scalars()
    ]
    if len(job_ids) > 0:
        for job_id in job_ids:
            connection.execute(
                text("delete from pipeline_rejected_rows where pipeline_job_id = :job_id"),
                {"job_id": job_id},
            )
            connection.execute(
                text(
                    """
                    delete from app_events
                    where aggregate_type = 'pipeline_job'
                      and aggregate_id = :job_id
                    """
                ),
                {"job_id": job_id},
            )
            connection.execute(
                text("delete from pipeline_skill_evidence_summary where pipeline_job_id = :job_id"),
                {"job_id": job_id},
            )
            connection.execute(
                text("delete from pipeline_jobs where id = :job_id"),
                {"job_id": job_id},
            )

    if len(dataset_ids) > 0:
        for dataset_id in dataset_ids:
            connection.execute(
                text(
                    """
                    delete from job_posting_skills
                    where job_posting_id in (
                        select id
                        from job_postings
                        where dataset_id = :dataset_id
                    )
                    """
                ),
                {"dataset_id": dataset_id},
            )
            connection.execute(
                text("delete from job_postings where dataset_id = :dataset_id"),
                {"dataset_id": dataset_id},
            )
            connection.execute(
                text("delete from market_datasets where id = :dataset_id"),
                {"dataset_id": dataset_id},
            )

    for skill_id in skill_ids:
        connection.execute(
            text(
                """
                delete from sdi_snapshots
                where role_id = :role_id
                  and skill_id = :skill_id
                  and snapshot_date in (:historical_1, :historical_2)
                  and requirement_version in (:version_1, :version_2)
                """
            ),
            {
                "role_id": role_id,
                "skill_id": skill_id,
                "historical_1": HISTORICAL_DATE_1,
                "historical_2": HISTORICAL_DATE_2,
                "version_1": HISTORICAL_VERSION_1,
                "version_2": HISTORICAL_VERSION_2,
            },
        )


def _assert_pipeline_job(
    *,
    connection: Connection,
    job_id: UUID,
    expected_status: str,
    expected_processed_rows: int,
    expected_rejected_rows: int,
    expected_output_version: int,
) -> None:
    row = connection.execute(
        text(
            """
            select status, processed_rows, rejected_rows, output_version
            from pipeline_jobs
            where id = :job_id
            """
        ),
        {"job_id": job_id},
    ).mappings().one_or_none()
    if row is None:
        raise AssertionError(f"pipeline_jobs missing row for job_id={job_id}")

    assert row["status"] == expected_status, (
        f"pipeline_jobs.status mismatch for job_id={job_id}: "
        f"expected={expected_status}, actual={row['status']}"
    )
    assert int(row["processed_rows"]) == expected_processed_rows, (
        f"pipeline_jobs.processed_rows mismatch for job_id={job_id}: "
        f"expected={expected_processed_rows}, actual={row['processed_rows']}"
    )
    assert int(row["rejected_rows"]) == expected_rejected_rows, (
        f"pipeline_jobs.rejected_rows mismatch for job_id={job_id}: "
        f"expected={expected_rejected_rows}, actual={row['rejected_rows']}"
    )
    assert int(row["output_version"]) == expected_output_version, (
        f"pipeline_jobs.output_version mismatch for job_id={job_id}: "
        f"expected={expected_output_version}, actual={row['output_version']}"
    )


def _assert_rejected_rows(
    *,
    connection: Connection,
    job_id: UUID,
    expected: list[tuple[int, str]],
) -> None:
    rows = list(
        connection.execute(
            text(
                """
                select row_number, reason
                from pipeline_rejected_rows
                where pipeline_job_id = :job_id
                order by row_number asc
                """
            ),
            {"job_id": job_id},
        ).mappings()
    )
    actual = [(int(row["row_number"]), str(row["reason"])) for row in rows]
    assert actual == expected, (
        f"pipeline_rejected_rows mismatch for job_id={job_id}: "
        f"expected={expected}, actual={actual}"
    )


def _assert_terminal_event(
    *,
    connection: Connection,
    job_id: UUID,
    expected_status: str,
    expected_output_version: int,
) -> None:
    rows = list(
        connection.execute(
            text(
                """
                select payload
                from app_events
                where aggregate_type = 'pipeline_job'
                  and aggregate_id = :job_id
                  and event_type = 'pipeline.ingestion.completed'
                """
            ),
            {"job_id": job_id},
        ).mappings()
    )
    assert len(rows) == 1, (
        f"app_events terminal completion row mismatch for job_id={job_id}: "
        f"expected=1, actual={len(rows)}"
    )

    payload = rows[0]["payload"]
    assert payload["status"] == expected_status, (
        f"app_events payload.status mismatch for job_id={job_id}: "
        f"expected={expected_status}, actual={payload['status']}"
    )
    assert int(payload["outputVersion"]) == expected_output_version, (
        f"app_events payload.outputVersion mismatch for job_id={job_id}: "
        f"expected={expected_output_version}, actual={payload['outputVersion']}"
    )


def _assert_requirement_version_for_dataset(
    *,
    connection: Connection,
    dataset_id: UUID,
    expected_version: int,
    expected_is_current: bool,
) -> None:
    rows = list(
        connection.execute(
            text(
                """
                select version, is_current
                from role_requirement_versions
                where dataset_id = :dataset_id
                """
            ),
            {"dataset_id": dataset_id},
        ).mappings()
    )
    assert len(rows) == 1, (
        f"role_requirement_versions row count mismatch for dataset_id={dataset_id}: "
        f"expected=1, actual={len(rows)}"
    )
    row = rows[0]
    assert int(row["version"]) == expected_version, (
        f"role_requirement_versions.version mismatch for dataset_id={dataset_id}: "
        f"expected={expected_version}, actual={row['version']}"
    )
    assert bool(row["is_current"]) is expected_is_current, (
        f"role_requirement_versions.is_current mismatch for dataset_id={dataset_id}: "
        f"expected={expected_is_current}, actual={row['is_current']}"
    )


def _assert_role_skill_requirements(
    *,
    connection: Connection,
    requirement_version: int,
    expected_row_count: int,
    expected_evidence_count: int,
) -> list[tuple[UUID, UUID]]:
    rows = list(
        connection.execute(
            text(
                """
                select role_id, skill_id, evidence_count
                from role_skill_requirements
                where requirement_version = :requirement_version
                order by role_id, skill_id
                """
            ),
            {"requirement_version": requirement_version},
        ).mappings()
    )
    assert len(rows) == expected_row_count, (
        f"role_skill_requirements row count mismatch for version={requirement_version}: "
        f"expected={expected_row_count}, actual={len(rows)}"
    )
    for row in rows:
        assert int(row["evidence_count"]) == expected_evidence_count, (
            f"role_skill_requirements.evidence_count mismatch for version={requirement_version}, "
            f"role_id={row['role_id']}, skill_id={row['skill_id']}: "
            f"expected={expected_evidence_count}, actual={row['evidence_count']}"
        )

    return [
        (UUID(str(row["role_id"])), UUID(str(row["skill_id"])))
        for row in rows
    ]


def _assert_evidence_summary_rows(
    *,
    connection: Connection,
    job_id: UUID,
    expected_pairs: list[tuple[UUID, UUID]],
) -> None:
    rows = list(
        connection.execute(
            text(
                """
                select role_id, skill_id, evidence_count, threshold_met
                from pipeline_skill_evidence_summary
                where pipeline_job_id = :job_id
                order by role_id, skill_id
                """
            ),
            {"job_id": job_id},
        ).mappings()
    )
    assert len(rows) == len(expected_pairs), (
        f"pipeline_skill_evidence_summary row count mismatch for pipeline_job_id={job_id}: "
        f"expected={len(expected_pairs)}, actual={len(rows)}"
    )
    actual_pairs = [(UUID(str(row["role_id"])), UUID(str(row["skill_id"]))) for row in rows]
    assert actual_pairs == sorted(expected_pairs, key=lambda pair: (str(pair[0]), str(pair[1]))), (
        f"pipeline_skill_evidence_summary role/skill pair mismatch for pipeline_job_id={job_id}: "
        f"expected={expected_pairs}, actual={actual_pairs}"
    )
    for row in rows:
        assert int(row["evidence_count"]) == 5, (
            f"pipeline_skill_evidence_summary.evidence_count mismatch for pipeline_job_id={job_id}, "
            f"role_id={row['role_id']}, skill_id={row['skill_id']}: expected=5, actual={row['evidence_count']}"
        )
        assert bool(row["threshold_met"]) is True, (
            f"pipeline_skill_evidence_summary.threshold_met mismatch for pipeline_job_id={job_id}, "
            f"role_id={row['role_id']}, skill_id={row['skill_id']}: expected=true"
        )


def _assert_sdi_snapshots(
    *,
    connection: Connection,
    requirement_version: int,
    expected_row_count: int,
) -> None:
    rows = list(
        connection.execute(
            text(
                """
                select role_id, skill_id, demand_index, snapshot_date
                from sdi_snapshots
                where requirement_version = :requirement_version
                order by role_id, skill_id
                """
            ),
            {"requirement_version": requirement_version},
        ).mappings()
    )
    assert len(rows) == expected_row_count, (
        f"sdi_snapshots row count mismatch for version={requirement_version}: "
        f"expected={expected_row_count}, actual={len(rows)}"
    )
    for row in rows:
        demand_index = float(row["demand_index"])
        assert 0.0 <= demand_index <= 1.0, (
            f"sdi_snapshots.demand_index out of range for version={requirement_version}, "
            f"role_id={row['role_id']}, skill_id={row['skill_id']}: actual={demand_index}"
        )


def _assert_decay_signals(
    *,
    connection: Connection,
    requirement_version: int,
    expected_row_count: int,
    expected_is_active: bool,
) -> None:
    rows = list(
        connection.execute(
            text(
                """
                select role_id, skill_id, decay_rate, confidence, is_active
                from skill_decay_signals
                where requirement_version = :requirement_version
                order by role_id, skill_id
                """
            ),
            {"requirement_version": requirement_version},
        ).mappings()
    )
    assert len(rows) == expected_row_count, (
        f"skill_decay_signals row count mismatch for version={requirement_version}: "
        f"expected={expected_row_count}, actual={len(rows)}"
    )
    for row in rows:
        decay_rate = float(row["decay_rate"])
        confidence = float(row["confidence"])
        assert 0.0 <= decay_rate <= 1.0, (
            f"skill_decay_signals.decay_rate out of range for version={requirement_version}, "
            f"role_id={row['role_id']}, skill_id={row['skill_id']}: actual={decay_rate}"
        )
        assert 0.0 <= confidence <= 1.0, (
            f"skill_decay_signals.confidence out of range for version={requirement_version}, "
            f"role_id={row['role_id']}, skill_id={row['skill_id']}: actual={confidence}"
        )
        assert bool(row["is_active"]) is expected_is_active, (
            f"skill_decay_signals.is_active mismatch for version={requirement_version}, "
            f"role_id={row['role_id']}, skill_id={row['skill_id']}: "
            f"expected={expected_is_active}, actual={row['is_active']}"
        )
