from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
import sys
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, Engine, create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.contracts.sdi_snapshot import SdiSnapshotPublishRow
from src.contracts.skill_decay_signal import SkillDecaySignalPublishRow
from src.publishing.models.role_requirement_publish_model import RoleRequirementAggregateRow
from src.publishing.role_requirement_publisher import (
    RoleRequirementPublishIntegrityError,
    publish_role_requirements,
)
from src.publishing.sdi_publisher import ConflictError, publish_sdi_snapshots
from src.publishing.decay_publisher import publish_decay_signals

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is required for monthly publish integration tests",
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


def test_role_publish_month_scoped_current_revision_lineage_and_rollback(connection: Connection) -> None:
    role_id = _insert_role(connection)
    skill_id = _insert_skill(connection)
    may_dataset_id = _insert_dataset(connection)
    lineage_dataset_id = _insert_dataset(connection)
    june_dataset_id = _insert_dataset(connection)
    requirement = _requirement(role_id, skill_id)
    may_revision_before = _max_period_revision(connection, date(2026, 5, 1))
    may_count_before = _version_count_for_month(connection, date(2026, 5, 1))

    may_v1 = publish_role_requirements(
        dataset_id=may_dataset_id,
        requirements=[requirement],
        period_month=date(2026, 5, 1),
        lineage_dataset_ids=[lineage_dataset_id],
        connection=connection,
    )
    june_v1 = publish_role_requirements(
        dataset_id=june_dataset_id,
        requirements=[requirement],
        period_month=date(2026, 6, 1),
        connection=connection,
    )
    may_v2 = publish_role_requirements(
        dataset_id=may_dataset_id,
        requirements=[requirement],
        period_month=date(2026, 5, 1),
        connection=connection,
    )

    assert _period_revision(connection, may_v1) == may_revision_before + 1
    assert _period_revision(connection, may_v2) == may_revision_before + 2
    assert _current_versions_for_month(connection, date(2026, 5, 1)) == [may_v2]
    assert _current_versions_for_month(connection, date(2026, 6, 1)) == [june_v1]
    assert _version_is_current(connection, may_v1) is False
    assert _version_count_for_month(connection, date(2026, 5, 1)) == may_count_before + 2
    assert _lineage_dataset_ids(connection, may_v1) == {may_dataset_id, lineage_dataset_id}

    versions_before = _version_count(connection)
    savepoint = connection.begin_nested()
    try:
        with pytest.raises(RoleRequirementPublishIntegrityError):
            publish_role_requirements(
                dataset_id=may_dataset_id,
                requirements=[_requirement(uuid4(), skill_id)],
                period_month=date(2026, 7, 1),
                connection=connection,
            )
    finally:
        if savepoint.is_active:
            savepoint.rollback()

    assert _version_count(connection) == versions_before


def test_sdi_coexistence_conflict_and_period_month_enforcement(connection: Connection) -> None:
    role_id = _insert_role(connection)
    skill_id = _insert_skill(connection)
    dataset_id = _insert_dataset(connection)
    requirement = _requirement(role_id, skill_id)
    first_version = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=[requirement],
        period_month=date(2026, 5, 1),
        connection=connection,
    )
    second_version = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=[requirement],
        period_month=date(2026, 5, 1),
        connection=connection,
    )

    publish_sdi_snapshots(
        requirement_version=first_version,
        rows=[_sdi_row(role_id, skill_id, first_version, 0.5, date(2026, 5, 1))],
        connection=connection,
    )
    publish_sdi_snapshots(
        requirement_version=second_version,
        rows=[_sdi_row(role_id, skill_id, second_version, 0.6, date(2026, 5, 1))],
        connection=connection,
    )

    assert _sdi_count_for_pair(connection, role_id, skill_id, date(2026, 5, 1)) == 2

    with pytest.raises(ConflictError):
        publish_sdi_snapshots(
            requirement_version=second_version,
            rows=[_sdi_row(role_id, skill_id, second_version, 0.7, date(2026, 5, 1))],
            connection=connection,
        )

    with pytest.raises(ValueError):
        publish_sdi_snapshots(
            requirement_version=second_version,
            rows=[_sdi_row(role_id, skill_id, second_version, 0.7, date(2026, 5, 2))],
            connection=connection,
        )


def test_decay_deactivation_is_scoped_to_period_month(connection: Connection) -> None:
    role_id = _insert_role(connection)
    skill_id = _insert_skill(connection)
    dataset_id = _insert_dataset(connection)
    requirement = _requirement(role_id, skill_id)
    jan_v1 = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=[requirement],
        period_month=date(2026, 1, 1),
        connection=connection,
    )
    feb_v1 = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=[requirement],
        period_month=date(2026, 2, 1),
        connection=connection,
    )
    jan_v2 = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=[requirement],
        period_month=date(2026, 1, 1),
        connection=connection,
    )

    publish_decay_signals(
        requirement_version=jan_v1,
        rows=[_decay_row(role_id, skill_id, jan_v1, 0.2)],
        connection=connection,
    )
    publish_decay_signals(
        requirement_version=feb_v1,
        rows=[_decay_row(role_id, skill_id, feb_v1, 0.3)],
        connection=connection,
    )
    publish_decay_signals(
        requirement_version=jan_v2,
        rows=[_decay_row(role_id, skill_id, jan_v2, 0.4)],
        connection=connection,
    )

    assert _active_decay_count_for_month(connection, role_id, skill_id, date(2026, 1, 1)) == 1
    assert _active_decay_count_for_month(connection, role_id, skill_id, date(2026, 2, 1)) == 1


def test_current_monthly_views_return_only_current_rows(connection: Connection) -> None:
    role_id = _insert_role(connection)
    skill_id = _insert_skill(connection)
    dataset_id = _insert_dataset(connection)
    requirement = _requirement(role_id, skill_id)
    old_version = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=[requirement],
        period_month=date(2026, 8, 1),
        connection=connection,
    )
    current_version = publish_role_requirements(
        dataset_id=dataset_id,
        requirements=[requirement],
        period_month=date(2026, 8, 1),
        connection=connection,
    )

    publish_sdi_snapshots(
        requirement_version=old_version,
        rows=[_sdi_row(role_id, skill_id, old_version, 0.4, date(2026, 8, 1))],
        connection=connection,
    )
    publish_sdi_snapshots(
        requirement_version=current_version,
        rows=[_sdi_row(role_id, skill_id, current_version, 0.8, date(2026, 8, 1))],
        connection=connection,
    )
    publish_decay_signals(
        requirement_version=current_version,
        rows=[_decay_row(role_id, skill_id, current_version, 0.1)],
        connection=connection,
    )

    assert _view_count(connection, "v_current_monthly_role_skill_requirements", current_version) == 1
    assert _view_count(connection, "v_current_monthly_sdi_snapshots", current_version) == 1
    assert _view_count(connection, "v_current_monthly_skill_decay_signals", current_version) == 1
    assert _view_count(connection, "v_current_monthly_role_skill_requirements", old_version) == 0
    assert _view_count(connection, "v_current_monthly_sdi_snapshots", old_version) == 0


def _bootstrap_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        if not _table_exists(connection, "skills"):
            _run_migration(connection, "20260503143000_p1_s01_taxonomy_schema.sql")
            _run_migration(connection, "20260505120000_p1_s01b_taxonomy_schema_patch.sql")
        if not _table_exists(connection, "pipeline_jobs"):
            _run_migration(connection, "20260504100000_p1_s02_pipeline_ops.sql")
        if not _table_exists(connection, "app_events"):
            _run_migration(connection, "20260510130000_add_app_events.sql")
        if not _table_exists(connection, "role_requirement_versions"):
            _run_migration(connection, "20260504110000_p1_s03_prepared_intelligence.sql")
        if not _column_exists(connection, "role_requirement_versions", "is_current"):
            _run_migration(connection, "20260518120000_align_role_requirement_publish_contract.sql")
        if not _table_exists(connection, "pipeline_skill_evidence_summary"):
            _run_migration(connection, "20260511120000_add_pipeline_skill_evidence_summary.sql")
        if not _table_exists(connection, "job_postings"):
            _run_migration(connection, "20260519120000_add_job_posting_skill_evidence.sql")
        if not _column_exists(connection, "role_requirement_versions", "period_month"):
            _run_migration(connection, "20260523120000_monthly_versioning_and_lineage.sql")


def _run_migration(connection: Connection, migration_name: str) -> None:
    connection.exec_driver_sql((MIGRATIONS_DIR / migration_name).read_text(encoding="utf-8"))


def _table_exists(connection: Connection, table_name: str) -> bool:
    return bool(
        connection.execute(
            text(
                """
                select exists (
                    select 1 from information_schema.tables
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
                    select 1 from information_schema.columns
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
                    values (:file_path, 'monthly-publish-test', 'uploaded')
                    returning id
                    """
                ),
                {"file_path": f"monthly-publish-{uuid4()}.csv"},
            ).scalar_one()
        )
    )


def _insert_role(connection: Connection) -> UUID:
    token = uuid4().hex[:12]
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
                {"code": f"MONTHLY_ROLE_{token}", "title": f"Monthly Role {token}"},
            ).scalar_one()
        )
    )


def _insert_skill(connection: Connection) -> UUID:
    token = uuid4().hex[:12]
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
                {"code": f"MONTHLY_SKILL_{token}", "name": f"Monthly Skill {token}"},
            ).scalar_one()
        )
    )


def _requirement(role_id: UUID, skill_id: UUID) -> RoleRequirementAggregateRow:
    return RoleRequirementAggregateRow(
        role_id=role_id,
        skill_id=skill_id,
        required_depth=0.7,
        demand_weight=0.8,
        evidence_count=5,
    )


def _sdi_row(
    role_id: UUID,
    skill_id: UUID,
    requirement_version: int,
    demand_index: float,
    snapshot_date: date,
) -> SdiSnapshotPublishRow:
    return SdiSnapshotPublishRow(
        role_id=role_id,
        skill_id=skill_id,
        demand_index=demand_index,
        snapshot_date=snapshot_date,
        requirement_version=requirement_version,
    )


def _decay_row(
    role_id: UUID,
    skill_id: UUID,
    requirement_version: int,
    decay_rate: float,
) -> SkillDecaySignalPublishRow:
    return SkillDecaySignalPublishRow(
        role_id=role_id,
        skill_id=skill_id,
        decay_rate=decay_rate,
        confidence=0.9,
        detected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        requirement_version=requirement_version,
        is_active=True,
    )


def _period_revision(connection: Connection, version: int) -> int:
    return int(
        connection.execute(
            text("select period_revision from role_requirement_versions where version = :version"),
            {"version": version},
        ).scalar_one()
    )


def _max_period_revision(connection: Connection, period_month: date) -> int:
    return int(
        connection.execute(
            text(
                """
                select coalesce(max(period_revision), 0)
                from role_requirement_versions
                where period_month = :period_month
                """
            ),
            {"period_month": period_month},
        ).scalar_one()
    )


def _current_versions_for_month(connection: Connection, period_month: date) -> list[int]:
    return [
        int(version)
        for version in connection.execute(
            text(
                """
                select version
                from role_requirement_versions
                where period_month = :period_month
                  and is_current = true
                order by version
                """
            ),
            {"period_month": period_month},
        ).scalars()
    ]


def _version_is_current(connection: Connection, version: int) -> bool:
    return bool(
        connection.execute(
            text("select is_current from role_requirement_versions where version = :version"),
            {"version": version},
        ).scalar_one()
    )


def _version_count_for_month(connection: Connection, period_month: date) -> int:
    return int(
        connection.execute(
            text("select count(*) from role_requirement_versions where period_month = :period_month"),
            {"period_month": period_month},
        ).scalar_one()
    )


def _lineage_dataset_ids(connection: Connection, version: int) -> set[UUID]:
    return {
        UUID(str(dataset_id))
        for dataset_id in connection.execute(
            text(
                """
                select dataset_id
                from role_requirement_version_datasets
                where requirement_version = :version
                """
            ),
            {"version": version},
        ).scalars()
    }


def _version_count(connection: Connection) -> int:
    return int(connection.execute(text("select count(*) from role_requirement_versions")).scalar_one())


def _sdi_count_for_pair(connection: Connection, role_id: UUID, skill_id: UUID, snapshot_date: date) -> int:
    return int(
        connection.execute(
            text(
                """
                select count(*)
                from sdi_snapshots
                where role_id = :role_id
                  and skill_id = :skill_id
                  and snapshot_date = :snapshot_date
                """
            ),
            {"role_id": role_id, "skill_id": skill_id, "snapshot_date": snapshot_date},
        ).scalar_one()
    )


def _active_decay_count_for_month(
    connection: Connection,
    role_id: UUID,
    skill_id: UUID,
    period_month: date,
) -> int:
    return int(
        connection.execute(
            text(
                """
                select count(*)
                from skill_decay_signals signals
                join role_requirement_versions versions
                  on versions.version = signals.requirement_version
                where signals.role_id = :role_id
                  and signals.skill_id = :skill_id
                  and signals.is_active = true
                  and versions.period_month = :period_month
                """
            ),
            {"role_id": role_id, "skill_id": skill_id, "period_month": period_month},
        ).scalar_one()
    )


def _view_count(connection: Connection, view_name: str, requirement_version: int) -> int:
    return int(
        connection.execute(
            text(f"select count(*) from {view_name} where requirement_version = :requirement_version"),
            {"requirement_version": requirement_version},
        ).scalar_one()
    )
