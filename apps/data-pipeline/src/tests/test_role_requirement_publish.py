from __future__ import annotations

import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.contracts.mapped_skill import MappedRoleSkillRow
from src.intelligence.role_requirement_aggregator import aggregate_role_requirements
from src.publishing.evidence_summary_writer import (
    EvidenceSummaryInputRow,
    write_evidence_summaries,
)
from src.publishing.models.role_requirement_publish_model import RoleRequirementAggregateRow
from src.publishing.role_requirement_publisher import (
    RoleRequirementPublishIntegrityError,
    publish_role_requirements,
)

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is required for role requirement publish integration tests",
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATIONS_DIR = REPO_ROOT / "packages" / "database" / "migrations"


@pytest.fixture(scope="session")
def engine() -> Engine:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL, future=True)
    _bootstrap_schema(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def connection(engine: Engine) -> Connection:
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


def test_aggregate_tracks_cumulative_thresholds_and_publish_filters(connection: Connection) -> None:
    dataset_id = _insert_dataset(connection)
    current_job_id = _insert_pipeline_job(connection, dataset_id)
    old_dataset_id = _insert_dataset(connection)
    old_job_id = _insert_pipeline_job(connection, old_dataset_id)
    role_id = _insert_role(connection)
    publish_skill_id = _insert_skill(connection)
    excluded_skill_id = _insert_skill(connection)
    all_null_skill_id = _insert_skill(connection)

    _insert_evidence_summary(
        connection,
        dataset_id=old_dataset_id,
        pipeline_job_id=old_job_id,
        role_id=role_id,
        skill_id=publish_skill_id,
        evidence_count=2,
        threshold_met=False,
    )
    _insert_evidence_summary(
        connection,
        dataset_id=old_dataset_id,
        pipeline_job_id=old_job_id,
        role_id=role_id,
        skill_id=excluded_skill_id,
        evidence_count=1,
        threshold_met=False,
    )

    mapped_rows = [
        *_mapped_rows(role_id, publish_skill_id, [0.4, 0.6, 0.8]),
        *_mapped_rows(role_id, excluded_skill_id, [0.3, 0.5, 0.7], start_index=4),
        *_mapped_rows(role_id, all_null_skill_id, [None, None], start_index=7),
    ]

    publish_rows = aggregate_role_requirements(
        pipeline_job_id=current_job_id,
        dataset_id=dataset_id,
        mapped_rows=mapped_rows,
        connection=connection,
    )

    assert len(publish_rows) == 1
    assert publish_rows[0].skill_id == publish_skill_id
    assert publish_rows[0].required_depth == 0.6
    assert publish_rows[0].demand_weight == 0.375
    assert publish_rows[0].evidence_count == 5

    new_version = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=publish_rows,
        connection=connection,
    )

    assert _count_current_versions(connection) == 1
    assert _count_requirements(connection, new_version) == 1
    assert _version_is_current(connection, new_version) is True
    assert _requirement_evidence_count(connection, new_version, role_id, publish_skill_id) == 5
    assert _version_exists(connection, new_version) is True

    assert _summary_threshold(connection, current_job_id, role_id, publish_skill_id) is True
    assert _summary_threshold(connection, current_job_id, role_id, excluded_skill_id) is False
    assert _summary_exists(connection, current_job_id, role_id, all_null_skill_id) is False


def test_successful_publish_flips_previous_current_version(connection: Connection) -> None:
    previous_dataset_id = _insert_dataset(connection)
    previous_version = _insert_requirement_version(
        connection,
        dataset_id=previous_dataset_id,
        version=1,
        is_current=True,
    )
    dataset_id = _insert_dataset(connection)
    role_id = _insert_role(connection)
    skill_id = _insert_skill(connection)

    new_version = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=[
            RoleRequirementAggregateRow(
                role_id=role_id,
                skill_id=skill_id,
                required_depth=0.7,
                demand_weight=0.5,
                evidence_count=5,
            )
        ],
        connection=connection,
    )

    assert new_version == previous_version + 1
    assert _version_is_current(connection, previous_version) is False
    assert _version_is_current(connection, new_version) is True


def test_publisher_returns_inserted_version_integer(connection: Connection) -> None:
    dataset_id = _insert_dataset(connection)
    role_id = _insert_role(connection)
    skill_id = _insert_skill(connection)

    new_version = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=[
            RoleRequirementAggregateRow(
                role_id=role_id,
                skill_id=skill_id,
                required_depth=0.5,
                demand_weight=1.0,
                evidence_count=6,
            )
        ],
        connection=connection,
    )

    stored_version = connection.execute(
        text(
            """
            select version
            from role_requirement_versions
            where version = :version
            """
        ),
        {"version": new_version},
    ).scalar_one()

    assert stored_version == new_version


def test_publish_model_rejects_invalid_depth_and_weight_before_db_write() -> None:
    role_id = uuid4()
    skill_id = uuid4()

    with pytest.raises(ValidationError):
        RoleRequirementAggregateRow(
            role_id=role_id,
            skill_id=skill_id,
            required_depth=1.0001,
            demand_weight=0.5,
            evidence_count=5,
        )

    with pytest.raises(ValidationError):
        RoleRequirementAggregateRow(
            role_id=role_id,
            skill_id=skill_id,
            required_depth=0.5,
            demand_weight=0.0999,
            evidence_count=5,
        )


def test_invalid_role_fk_rolls_back_failed_publish(connection: Connection) -> None:
    dataset_id = _insert_dataset(connection)
    skill_id = _insert_skill(connection)
    versions_before = _count_versions(connection)
    savepoint = connection.begin_nested()

    try:
        with pytest.raises(RoleRequirementPublishIntegrityError):
            publish_role_requirements(
                dataset_id=dataset_id,
                requirements=[
                    RoleRequirementAggregateRow(
                        role_id=uuid4(),
                        skill_id=skill_id,
                        required_depth=0.5,
                        demand_weight=0.5,
                        evidence_count=5,
                    )
                ],
                connection=connection,
            )
    finally:
        if savepoint.is_active:
            savepoint.rollback()

    assert _count_versions(connection) == versions_before
    assert _count_current_versions(connection) == 0


def test_duplicate_evidence_summary_insert_raises_constraint_error(connection: Connection) -> None:
    dataset_id = _insert_dataset(connection)
    pipeline_job_id = _insert_pipeline_job(connection, dataset_id)
    role_id = _insert_role(connection)
    skill_id = _insert_skill(connection)
    row = EvidenceSummaryInputRow(role_id=role_id, skill_id=skill_id, evidence_count=1)

    write_evidence_summaries(
        pipeline_job_id=pipeline_job_id,
        dataset_id=dataset_id,
        rows=[row],
        connection=connection,
    )

    savepoint = connection.begin_nested()
    try:
        with pytest.raises(IntegrityError):
            write_evidence_summaries(
                pipeline_job_id=pipeline_job_id,
                dataset_id=dataset_id,
                rows=[row],
                connection=connection,
            )
    finally:
        if savepoint.is_active:
            savepoint.rollback()


def test_zero_role_denominator_skips_role_with_warning(
    connection: Connection,
    caplog: pytest.LogCaptureFixture,
) -> None:
    dataset_id = _insert_dataset(connection)
    pipeline_job_id = _insert_pipeline_job(connection, dataset_id)
    role_id = _insert_role(connection)
    skill_id = _insert_skill(connection)

    result = aggregate_role_requirements(
        pipeline_job_id=pipeline_job_id,
        dataset_id=dataset_id,
        mapped_rows=[
            MappedRoleSkillRow(
                job_posting_id=uuid4(),
                role_id=role_id,
                skill_id=skill_id,
                normalized_depth=0.5,
            )
        ],
        total_matched_postings_by_role={role_id: 0},
        connection=connection,
    )

    assert result == []
    assert _summary_exists(connection, pipeline_job_id, role_id, skill_id) is False
    assert "total_matched_postings_for_role=0" in caplog.text


def _bootstrap_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        if not _table_exists(connection, "skills"):
            _run_migration(connection, "20260503143000_p1_s01_taxonomy_schema.sql")
            _run_migration(connection, "20260505120000_p1_s01b_taxonomy_schema_patch.sql")
        if not _table_exists(connection, "pipeline_jobs"):
            _run_migration(connection, "20260504100000_p1_s02_pipeline_ops.sql")
        if not _table_exists(connection, "role_requirement_versions"):
            _run_migration(connection, "20260504110000_p1_s03_prepared_intelligence.sql")
        if not _column_exists(connection, "role_requirement_versions", "is_current"):
            _run_migration(connection, "20260518120000_align_role_requirement_publish_contract.sql")
        if not _table_exists(connection, "pipeline_skill_evidence_summary"):
            _run_migration(connection, "20260511120000_add_pipeline_skill_evidence_summary.sql")


def _run_migration(connection: Connection, migration_name: str) -> None:
    connection.exec_driver_sql((MIGRATIONS_DIR / migration_name).read_text(encoding="utf-8"))


def _table_exists(connection: Connection, table_name: str) -> bool:
    return bool(
        connection.execute(
            text(
                """
                select exists (
                    select 1
                    from information_schema.tables
                    where table_schema = 'public'
                      and table_name = :table_name
                )
                """
            ),
            {"table_name": table_name},
        ).scalar_one()
    )


def _column_exists(connection: Connection, table_name: str, column_name: str) -> bool:
    return bool(
        connection.execute(
            text(
                """
                select exists (
                    select 1
                    from information_schema.columns
                    where table_schema = 'public'
                      and table_name = :table_name
                      and column_name = :column_name
                )
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar_one()
    )


def _insert_dataset(connection: Connection) -> UUID:
    return UUID(
        str(
            connection.execute(
                text(
                    """
                    insert into market_datasets (file_path, source, status)
                    values (:file_path, 'role-requirement-publish-test', 'uploaded')
                    returning id
                    """
                ),
                {"file_path": f"test-{uuid4()}.csv"},
            ).scalar_one()
        )
    )


def _insert_pipeline_job(connection: Connection, dataset_id: UUID) -> UUID:
    return UUID(
        str(
            connection.execute(
                text(
                    """
                    insert into pipeline_jobs (dataset_id, job_type, status)
                    values (:dataset_id, 'role_requirement_publish_test', 'running')
                    returning id
                    """
                ),
                {"dataset_id": dataset_id},
            ).scalar_one()
        )
    )


def _insert_role(connection: Connection) -> UUID:
    unique_token = uuid4().hex[:12]
    return UUID(
        str(
            connection.execute(
                text(
                    """
                    insert into career_roles (code, title)
                    values (:code, :title)
                    returning id
                    """
                ),
                {
                    "code": f"ROLE_{unique_token}",
                    "title": f"Role {unique_token}",
                },
            ).scalar_one()
        )
    )


def _insert_skill(connection: Connection) -> UUID:
    unique_token = uuid4().hex[:12]
    return UUID(
        str(
            connection.execute(
                text(
                    """
                    insert into skills (code, name)
                    values (:code, :name)
                    returning id
                    """
                ),
                {
                    "code": f"SKILL_{unique_token}",
                    "name": f"Skill {unique_token}",
                },
            ).scalar_one()
        )
    )


def _insert_requirement_version(
    connection: Connection,
    *,
    dataset_id: UUID,
    version: int,
    is_current: bool,
) -> int:
    return int(
        connection.execute(
            text(
                """
                insert into role_requirement_versions (version, dataset_id, is_current)
                values (:version, :dataset_id, :is_current)
                returning version
                """
            ),
            {
                "version": version,
                "dataset_id": dataset_id,
                "is_current": is_current,
            },
        ).scalar_one()
    )


def _insert_evidence_summary(
    connection: Connection,
    *,
    dataset_id: UUID,
    pipeline_job_id: UUID,
    role_id: UUID,
    skill_id: UUID,
    evidence_count: int,
    threshold_met: bool,
) -> None:
    connection.execute(
        text(
            """
            insert into pipeline_skill_evidence_summary (
                id,
                dataset_id,
                pipeline_job_id,
                role_id,
                skill_id,
                evidence_count,
                threshold_met
            )
            values (
                :id,
                :dataset_id,
                :pipeline_job_id,
                :role_id,
                :skill_id,
                :evidence_count,
                :threshold_met
            )
            """
        ),
        {
            "id": uuid4(),
            "dataset_id": dataset_id,
            "pipeline_job_id": pipeline_job_id,
            "role_id": role_id,
            "skill_id": skill_id,
            "evidence_count": evidence_count,
            "threshold_met": threshold_met,
        },
    )


def _mapped_rows(
    role_id: UUID,
    skill_id: UUID,
    depths: list[float | None],
    *,
    start_index: int = 1,
) -> list[MappedRoleSkillRow]:
    return [
        MappedRoleSkillRow(
            job_posting_id=UUID(f"aaaaaaaa-aaaa-aaaa-aaaa-{index:012d}"),
            role_id=role_id,
            skill_id=skill_id,
            normalized_depth=depth,
        )
        for index, depth in enumerate(depths, start=start_index)
    ]


def _count_versions(connection: Connection) -> int:
    return int(connection.execute(text("select count(*) from role_requirement_versions")).scalar_one())


def _count_current_versions(connection: Connection) -> int:
    return int(
        connection.execute(
            text("select count(*) from role_requirement_versions where is_current = true")
        ).scalar_one()
    )


def _count_requirements(connection: Connection, version: int) -> int:
    return int(
        connection.execute(
            text(
                """
                select count(*)
                from role_skill_requirements
                where requirement_version = :version
                """
            ),
            {"version": version},
        ).scalar_one()
    )


def _version_exists(connection: Connection, version: int) -> bool:
    return bool(
        connection.execute(
            text(
                """
                select exists (
                    select 1
                    from role_requirement_versions
                    where version = :version
                )
                """
            ),
            {"version": version},
        ).scalar_one()
    )


def _version_is_current(connection: Connection, version: int) -> bool:
    return bool(
        connection.execute(
            text(
                """
                select is_current
                from role_requirement_versions
                where version = :version
                """
            ),
            {"version": version},
        ).scalar_one()
    )


def _requirement_evidence_count(
    connection: Connection,
    version: int,
    role_id: UUID,
    skill_id: UUID,
) -> int:
    return int(
        connection.execute(
            text(
                """
                select evidence_count
                from role_skill_requirements
                where requirement_version = :version
                  and role_id = :role_id
                  and skill_id = :skill_id
                """
            ),
            {
                "version": version,
                "role_id": role_id,
                "skill_id": skill_id,
            },
        ).scalar_one()
    )


def _summary_exists(
    connection: Connection,
    pipeline_job_id: UUID,
    role_id: UUID,
    skill_id: UUID,
) -> bool:
    return bool(
        connection.execute(
            text(
                """
                select exists (
                    select 1
                    from pipeline_skill_evidence_summary
                    where pipeline_job_id = :pipeline_job_id
                      and role_id = :role_id
                      and skill_id = :skill_id
                )
                """
            ),
            {
                "pipeline_job_id": pipeline_job_id,
                "role_id": role_id,
                "skill_id": skill_id,
            },
        ).scalar_one()
    )


def _summary_threshold(
    connection: Connection,
    pipeline_job_id: UUID,
    role_id: UUID,
    skill_id: UUID,
) -> bool:
    return bool(
        connection.execute(
            text(
                """
                select threshold_met
                from pipeline_skill_evidence_summary
                where pipeline_job_id = :pipeline_job_id
                  and role_id = :role_id
                  and skill_id = :skill_id
                """
            ),
            {
                "pipeline_job_id": pipeline_job_id,
                "role_id": role_id,
                "skill_id": skill_id,
            },
        ).scalar_one()
    )
