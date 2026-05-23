from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
import sys
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, Engine, create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.contracts.skill_decay_signal import SkillDecaySignalPublishRow
from src.intelligence.decay import HistoricalSdiSnapshotRow, detect_decay_signals
from src.publishing.decay_publisher import publish_decay_signals

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is required for decay fixture integration tests",
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATIONS_DIR = REPO_ROOT / "packages" / "database" / "migrations"
ROLE_ID = UUID("14000000-0000-4000-8000-000000000001")
SKILL_ID = UUID("14000000-0000-4000-8000-000000000002")
SNAPSHOT_ROWS = [
    (date(2026, 3, 1), 0.90),
    (date(2026, 4, 1), 0.65),
    (date(2026, 5, 1), 0.40),
]


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


def test_deterministic_decay_fixture_publishes_active_signal_in_rollback_mode(connection: Connection) -> None:
    versions = _seed_decay_fixture(connection)
    rows = _load_decay_rows(connection)

    signals = detect_decay_signals(rows)
    assert len(signals) == 1
    assert signals[0].role_id == ROLE_ID
    assert signals[0].skill_id == SKILL_ID
    assert signals[0].decay_rate == 0.25
    assert signals[0].confidence >= 0.70

    latest_version = versions[-1]
    publish_decay_signals(
        requirement_version=latest_version,
        rows=[
            SkillDecaySignalPublishRow(
                role_id=signal.role_id,
                skill_id=signal.skill_id,
                decay_rate=signal.decay_rate,
                confidence=signal.confidence,
                detected_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
                requirement_version=latest_version,
                is_active=True,
            )
            for signal in signals
        ],
        connection=connection,
    )

    active_count = int(
        connection.execute(
            text(
                """
                select count(*)
                from skill_decay_signals
                where role_id = :role_id
                  and skill_id = :skill_id
                  and is_active = true
                """
            ),
            {"role_id": ROLE_ID, "skill_id": SKILL_ID},
        ).scalar_one()
    )
    assert active_count >= 1


def _seed_decay_fixture(connection: Connection) -> list[int]:
    _delete_fixture_rows(connection)
    dataset_id = UUID(
        str(
            connection.execute(
                text(
                    """
                    insert into market_datasets (file_path, source, status)
                    values (:file_path, 'p1-s14-decay-fixture', 'uploaded')
                    returning id
                    """
                ),
                {"file_path": f"p1-s14-decay-fixture-{uuid4()}.csv"},
            ).scalar_one()
        )
    )
    connection.execute(
        text(
            """
            insert into career_roles (id, code, title)
            values (:id, :code, :title)
            """
        ),
        {"id": ROLE_ID, "code": "P1_S14_DECAY_ROLE", "title": "P1 S14 Decay Role"},
    )
    connection.execute(
        text(
            """
            insert into skills (id, code, name)
            values (:id, :code, :name)
            """
        ),
        {"id": SKILL_ID, "code": "P1_S14_DECAY_SKILL", "name": "P1 S14 Decay Skill"},
    )

    next_version = int(
        connection.execute(text("select coalesce(max(version), 0) + 1 from role_requirement_versions")).scalar_one()
    )
    versions = [next_version, next_version + 1, next_version + 2]
    for version, (snapshot_date, demand_index) in zip(versions, SNAPSHOT_ROWS):
        connection.execute(
            text(
                """
                insert into role_requirement_versions (
                    version,
                    dataset_id,
                    period_month,
                    period_revision,
                    is_current
                )
                values (
                    :version,
                    :dataset_id,
                    :period_month,
                    :period_revision,
                    :is_current
                )
                """
            ),
            {
                "version": version,
                "dataset_id": dataset_id,
                "period_month": snapshot_date,
                "period_revision": version,
                "is_current": False,
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
                    :demand_index,
                    :snapshot_date,
                    :requirement_version
                )
                """
            ),
            {
                "role_id": ROLE_ID,
                "skill_id": SKILL_ID,
                "demand_index": demand_index,
                "snapshot_date": snapshot_date,
                "requirement_version": version,
            },
        )
    return versions


def _load_decay_rows(connection: Connection) -> list[HistoricalSdiSnapshotRow]:
    return [
        HistoricalSdiSnapshotRow(
            role_id=UUID(str(row["role_id"])),
            skill_id=UUID(str(row["skill_id"])),
            demand_index=float(row["demand_index"]),
            snapshot_date=row["snapshot_date"],
            requirement_version=int(row["requirement_version"]),
        )
        for row in connection.execute(
            text(
                """
                select role_id, skill_id, demand_index, snapshot_date, requirement_version
                from sdi_snapshots
                where role_id = :role_id
                  and skill_id = :skill_id
                order by snapshot_date
                """
            ),
            {"role_id": ROLE_ID, "skill_id": SKILL_ID},
        ).mappings()
    ]


def _delete_fixture_rows(connection: Connection) -> None:
    connection.execute(
        text(
            """
            delete from skill_decay_signals
            where role_id = :role_id
              and skill_id = :skill_id
            """
        ),
        {"role_id": ROLE_ID, "skill_id": SKILL_ID},
    )
    connection.execute(
        text(
            """
            delete from sdi_snapshots
            where role_id = :role_id
              and skill_id = :skill_id
            """
        ),
        {"role_id": ROLE_ID, "skill_id": SKILL_ID},
    )
    connection.execute(
        text("delete from career_roles where id = :role_id"),
        {"role_id": ROLE_ID},
    )
    connection.execute(
        text("delete from skills where id = :skill_id"),
        {"skill_id": SKILL_ID},
    )


def _bootstrap_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        if not _table_exists(connection, "skills"):
            _run_migration(connection, "20260503143000_p1_s01_taxonomy_schema.sql")
            _run_migration(connection, "20260505120000_p1_s01b_taxonomy_schema_patch.sql")
        if not _table_exists(connection, "role_requirement_versions"):
            _run_migration(connection, "20260504110000_p1_s03_prepared_intelligence.sql")
        if not _column_exists(connection, "role_requirement_versions", "is_current"):
            _run_migration(connection, "20260518120000_align_role_requirement_publish_contract.sql")
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
