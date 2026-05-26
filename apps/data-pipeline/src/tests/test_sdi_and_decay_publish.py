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
from src.intelligence.decay import HistoricalSdiSnapshotRow, detect_decay_signals
from src.intelligence.sdi import SdiPostingSkillInputRow, compute_sdi
from src.publishing.decay_publisher import publish_decay_signals
from src.publishing.sdi_publisher import ConflictError, publish_sdi_snapshots

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL is required for SDI and decay publish integration tests",
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


def test_sdi_output_is_deterministic_and_publish_is_idempotent(connection: Connection) -> None:
    seed = _seed_market_requirements(connection)
    _insert_job_posting_skill_fixture(connection, seed)
    rows = _sdi_input_rows(seed)

    first = compute_sdi(rows, snapshot_date=date(2026, 5, 1))
    second = compute_sdi(rows, snapshot_date=date(2026, 5, 1))

    assert first == second
    assert all(0.0 <= row.demand_index <= 1.0 for row in first)

    publish_rows = [
        SdiSnapshotPublishRow(
            role_id=row.role_id,
            skill_id=row.skill_id,
            demand_index=row.demand_index,
            snapshot_date=date(2026, 5, 1),
            requirement_version=seed.requirement_version,
        )
        for row in first
    ]
    before_counts = _protected_table_counts(connection)
    output_version = publish_sdi_snapshots(
        requirement_version=seed.requirement_version,
        rows=publish_rows,
        connection=connection,
    )
    repeat_output_version = publish_sdi_snapshots(
        requirement_version=seed.requirement_version,
        rows=publish_rows,
        connection=connection,
    )

    assert output_version == seed.requirement_version
    assert repeat_output_version == seed.requirement_version
    assert _count_sdi_rows(connection, seed.requirement_version) == len(publish_rows)
    assert _published_sdi_versions(connection, seed.requirement_version) == [seed.requirement_version]
    assert _protected_table_counts(connection) == before_counts


def test_sdi_same_day_rerun_with_differing_value_raises_conflict(connection: Connection) -> None:
    seed = _seed_market_requirements(connection)
    row = SdiSnapshotPublishRow(
        role_id=seed.role_id,
        skill_id=seed.skill_ids[0],
        demand_index=0.5,
        snapshot_date=date(2026, 5, 1),
        requirement_version=seed.requirement_version,
    )

    publish_sdi_snapshots(
        requirement_version=seed.requirement_version,
        rows=[row],
        connection=connection,
    )

    with pytest.raises(ConflictError):
        publish_sdi_snapshots(
            requirement_version=seed.requirement_version,
            rows=[
                SdiSnapshotPublishRow(
                    role_id=row.role_id,
                    skill_id=row.skill_id,
                    demand_index=0.6,
                    snapshot_date=row.snapshot_date,
                    requirement_version=row.requirement_version,
                )
            ],
            connection=connection,
        )

    assert _count_sdi_rows(connection, seed.requirement_version) == 1


def test_decay_detection_thresholds() -> None:
    role_id = uuid4()
    skill_id = uuid4()

    assert (
        detect_decay_signals(
            [
                _historical_snapshot(role_id, skill_id, 0.9, date(2026, 5, 1), 1),
                _historical_snapshot(role_id, skill_id, 0.7, date(2026, 5, 8), 2),
            ]
        )
        == []
    )
    assert (
        detect_decay_signals(
            [
                _historical_snapshot(role_id, skill_id, 0.7, date(2026, 5, 1), 1),
                _historical_snapshot(role_id, skill_id, 0.65, date(2026, 5, 8), 2),
                _historical_snapshot(role_id, skill_id, 0.61, date(2026, 5, 15), 3),
            ]
        )
        == []
    )

    signals = detect_decay_signals(
        [
            _historical_snapshot(role_id, skill_id, 0.9, date(2026, 5, 1), 1),
            _historical_snapshot(role_id, skill_id, 0.65, date(2026, 5, 8), 2),
            _historical_snapshot(role_id, skill_id, 0.4, date(2026, 5, 15), 3),
        ]
    )

    assert len(signals) == 1
    assert signals[0].decay_rate == -0.25
    assert signals[0].confidence == 1.0


def test_decay_publish_deactivates_prior_active_rows(connection: Connection) -> None:
    seed = _seed_market_requirements(connection)
    before_counts = _protected_table_counts(connection)

    first_output_version = publish_decay_signals(
        requirement_version=seed.requirement_version,
        rows=[
            SkillDecaySignalPublishRow(
                role_id=seed.role_id,
                skill_id=seed.skill_ids[0],
                decay_rate=-0.25,
                confidence=0.9,
                detected_at=datetime(2026, 5, 19, tzinfo=timezone.utc),
                requirement_version=seed.requirement_version,
            )
        ],
        connection=connection,
    )
    second_version = _insert_requirement_version(
        connection,
        seed.dataset_id,
        _next_requirement_version(connection),
        is_current=True,
    )
    second_output_version = publish_decay_signals(
        requirement_version=second_version,
        rows=[
            SkillDecaySignalPublishRow(
                role_id=seed.role_id,
                skill_id=seed.skill_ids[0],
                decay_rate=-0.3,
                confidence=1.0,
                detected_at=datetime(2026, 5, 20, tzinfo=timezone.utc),
                requirement_version=second_version,
            )
        ],
        connection=connection,
    )

    assert first_output_version == seed.requirement_version
    assert second_output_version == second_version
    assert _active_decay_count(connection, seed.role_id, seed.skill_ids[0]) == 1
    assert _all_decay_values_in_range(connection) is True
    assert _published_decay_versions(connection, seed.role_id, seed.skill_ids[0]) == [
        seed.requirement_version,
        second_version,
    ]
    assert _protected_table_counts(connection) == before_counts


def test_published_sdi_demand_index_values_are_in_range(connection: Connection) -> None:
    seed = _seed_market_requirements(connection)
    rows = compute_sdi(_sdi_input_rows(seed), snapshot_date=date(2026, 5, 1))
    publish_sdi_snapshots(
        requirement_version=seed.requirement_version,
        rows=[
            SdiSnapshotPublishRow(
                role_id=row.role_id,
                skill_id=row.skill_id,
                demand_index=row.demand_index,
                snapshot_date=date(2026, 5, 1),
                requirement_version=seed.requirement_version,
            )
            for row in rows
        ],
        connection=connection,
    )

    assert _all_sdi_values_in_range(connection, seed.requirement_version) is True


def test_all_published_sdi_rows_have_valid_requirement_version(connection: Connection) -> None:
    seed = _seed_market_requirements(connection)
    publish_sdi_snapshots(
        requirement_version=seed.requirement_version,
        rows=[
            SdiSnapshotPublishRow(
                role_id=seed.role_id,
                skill_id=seed.skill_ids[0],
                demand_index=0.5,
                snapshot_date=date(2026, 5, 1),
                requirement_version=seed.requirement_version,
            )
        ],
        connection=connection,
    )

    assert _published_sdi_versions(connection, seed.requirement_version) == [seed.requirement_version]


def test_same_day_sdi_rerun_with_identical_values_produces_no_duplicate_rows(connection: Connection) -> None:
    seed = _seed_market_requirements(connection)
    row = SdiSnapshotPublishRow(
        role_id=seed.role_id,
        skill_id=seed.skill_ids[0],
        demand_index=0.5,
        snapshot_date=date(2026, 5, 1),
        requirement_version=seed.requirement_version,
    )

    publish_sdi_snapshots(requirement_version=seed.requirement_version, rows=[row], connection=connection)
    publish_sdi_snapshots(requirement_version=seed.requirement_version, rows=[row], connection=connection)

    assert _count_sdi_rows(connection, seed.requirement_version) == 1


def test_decay_detection_returns_no_signal_with_fewer_than_three_snapshots() -> None:
    role_id = uuid4()
    skill_id = uuid4()

    assert detect_decay_signals(
        [
            _historical_snapshot(role_id, skill_id, 0.9, date(2026, 5, 1), 1),
            _historical_snapshot(role_id, skill_id, 0.7, date(2026, 5, 8), 2),
        ]
    ) == []


def test_decay_detection_returns_no_signal_when_slope_is_above_threshold() -> None:
    role_id = uuid4()
    skill_id = uuid4()

    assert detect_decay_signals(
        [
            _historical_snapshot(role_id, skill_id, 0.7, date(2026, 5, 1), 1),
            _historical_snapshot(role_id, skill_id, 0.65, date(2026, 5, 8), 2),
            _historical_snapshot(role_id, skill_id, 0.61, date(2026, 5, 15), 3),
        ]
    ) == []


def test_decay_detection_returns_active_signal_when_thresholds_are_met() -> None:
    role_id = uuid4()
    skill_id = uuid4()

    signals = detect_decay_signals(
        [
            _historical_snapshot(role_id, skill_id, 0.9, date(2026, 5, 1), 1),
            _historical_snapshot(role_id, skill_id, 0.65, date(2026, 5, 8), 2),
            _historical_snapshot(role_id, skill_id, 0.4, date(2026, 5, 15), 3),
        ]
    )

    assert len(signals) == 1
    assert signals[0].decay_rate == -0.25
    assert signals[0].confidence == 1.0


def test_all_published_decay_rows_have_valid_requirement_version(connection: Connection) -> None:
    seed = _seed_market_requirements(connection)
    publish_decay_signals(
        requirement_version=seed.requirement_version,
        rows=[
            SkillDecaySignalPublishRow(
                role_id=seed.role_id,
                skill_id=seed.skill_ids[0],
                decay_rate=-0.25,
                confidence=0.9,
                detected_at=datetime(2026, 5, 19, tzinfo=timezone.utc),
                requirement_version=seed.requirement_version,
            )
        ],
        connection=connection,
    )

    assert _published_decay_versions(connection, seed.role_id, seed.skill_ids[0]) == [seed.requirement_version]


def test_publish_entrypoints_return_non_null_output_version(connection: Connection) -> None:
    seed = _seed_market_requirements(connection)

    sdi_output_version = publish_sdi_snapshots(
        requirement_version=seed.requirement_version,
        rows=[
            SdiSnapshotPublishRow(
                role_id=seed.role_id,
                skill_id=seed.skill_ids[0],
                demand_index=0.5,
                snapshot_date=date(2026, 5, 1),
                requirement_version=seed.requirement_version,
            )
        ],
        connection=connection,
    )
    decay_output_version = publish_decay_signals(
        requirement_version=seed.requirement_version,
        rows=[
            SkillDecaySignalPublishRow(
                role_id=seed.role_id,
                skill_id=seed.skill_ids[0],
                decay_rate=-0.25,
                confidence=0.9,
                detected_at=datetime(2026, 5, 19, tzinfo=timezone.utc),
                requirement_version=seed.requirement_version,
            )
        ],
        connection=connection,
    )

    assert isinstance(sdi_output_version, int)
    assert isinstance(decay_output_version, int)
    assert sdi_output_version == seed.requirement_version
    assert decay_output_version == seed.requirement_version


def test_publish_paths_do_not_write_pipeline_jobs_or_app_events(connection: Connection) -> None:
    seed = _seed_market_requirements(connection)
    before_counts = _protected_table_counts(connection)

    publish_sdi_snapshots(
        requirement_version=seed.requirement_version,
        rows=[
            SdiSnapshotPublishRow(
                role_id=seed.role_id,
                skill_id=seed.skill_ids[0],
                demand_index=0.5,
                snapshot_date=date(2026, 5, 1),
                requirement_version=seed.requirement_version,
            )
        ],
        connection=connection,
    )
    publish_decay_signals(
        requirement_version=seed.requirement_version,
        rows=[
            SkillDecaySignalPublishRow(
                role_id=seed.role_id,
                skill_id=seed.skill_ids[0],
                decay_rate=-0.25,
                confidence=0.9,
                detected_at=datetime(2026, 5, 19, tzinfo=timezone.utc),
                requirement_version=seed.requirement_version,
            )
        ],
        connection=connection,
    )

    assert _protected_table_counts(connection) == before_counts


class MarketSeed:
    def __init__(
        self,
        *,
        dataset_id: UUID,
        role_id: UUID,
        skill_ids: list[UUID],
        requirement_version: int,
    ) -> None:
        self.dataset_id = dataset_id
        self.role_id = role_id
        self.skill_ids = skill_ids
        self.requirement_version = requirement_version


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
        if not _column_exists(connection, "role_requirement_versions", "period_month"):
            _run_migration(connection, "20260523120000_monthly_versioning_and_lineage.sql")
        if not _column_exists(connection, "market_datasets", "source_url"):
            _run_migration(connection, "20260526120000_admin_readiness_contract_patch.sql")
        if not _table_exists(connection, "job_postings"):
            _run_migration(connection, "20260519120000_add_job_posting_skill_evidence.sql")


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


def _seed_market_requirements(connection: Connection) -> MarketSeed:
    dataset_id = _insert_dataset(connection)
    role_id = _insert_role(connection)
    skill_ids = [_insert_skill(connection), _insert_skill(connection)]
    requirement_version = _insert_requirement_version(
        connection,
        dataset_id,
        _next_requirement_version(connection),
        is_current=True,
    )
    for skill_id in skill_ids:
        connection.execute(
            text(
                """
                insert into role_skill_requirements (
                    role_id,
                    skill_id,
                    requirement_version,
                    required_depth,
                    demand_weight,
                    evidence_count
                )
                values (:role_id, :skill_id, :requirement_version, 0.5, 0.5, 5)
                """
            ),
            {
                "role_id": role_id,
                "skill_id": skill_id,
                "requirement_version": requirement_version,
            },
        )
    return MarketSeed(
        dataset_id=dataset_id,
        role_id=role_id,
        skill_ids=skill_ids,
        requirement_version=requirement_version,
    )


def _insert_dataset(connection: Connection) -> UUID:
    return UUID(
        str(
            connection.execute(
                text(
                    """
                    insert into market_datasets (file_path, source, status)
                    values (:file_path, 'sdi-decay-publish-test', 'uploaded')
                    returning id
                    """
                ),
                {"file_path": f"sdi-{uuid4()}.csv"},
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
                {"code": f"SDI_ROLE_{token}", "title": f"SDI Role {token}"},
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
                {"code": f"SDI_SKILL_{token}", "name": f"SDI Skill {token}"},
            ).scalar_one()
        )
    )


def _insert_requirement_version(
    connection: Connection,
    dataset_id: UUID,
    version: int,
    *,
    is_current: bool,
) -> int:
    if is_current:
        connection.execute(
            text(
                """
                update role_requirement_versions
                set is_current = false
                where period_month = date '2026-05-01'
                  and is_current = true
                """
            )
        )

    return int(
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
                returning version
                """
            ),
            {
                "version": version,
                "dataset_id": dataset_id,
                "period_month": date(2026, 5, 1),
                "period_revision": version,
                "is_current": is_current,
            },
        ).scalar_one()
    )


def _next_requirement_version(connection: Connection) -> int:
    return int(
        connection.execute(
            text("select coalesce(max(version), 0) + 1 from role_requirement_versions")
        ).scalar_one()
    )


def _insert_job_posting_skill_fixture(connection: Connection, seed: MarketSeed) -> None:
    postings = [
        (UUID("10000000-0000-0000-0000-000000000001"), date(2026, 5, 19), [seed.skill_ids[0], seed.skill_ids[1]]),
        (UUID("10000000-0000-0000-0000-000000000002"), date(2026, 5, 12), [seed.skill_ids[0]]),
        (UUID("10000000-0000-0000-0000-000000000003"), date(2026, 4, 19), [seed.skill_ids[0]]),
    ]
    for posting_id, posted_at, skill_ids in postings:
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
                    posted_at
                )
                values (
                    :id,
                    :dataset_id,
                    :source,
                    :title,
                    'Fixture Co',
                    'Python SQL Analytics',
                    :role_id,
                    :posted_at
                )
                """
            ),
            {
                "id": posting_id,
                "dataset_id": seed.dataset_id,
                "source": f"fixture-{posting_id}",
                "title": f"Fixture Posting {posting_id}",
                "role_id": seed.role_id,
                "posted_at": posted_at,
            },
        )
        for skill_id in skill_ids:
            connection.execute(
                text(
                    """
                    insert into job_posting_skills (job_posting_id, role_id, skill_id, normalized_depth)
                    values (:job_posting_id, :role_id, :skill_id, 0.5)
                    """
                ),
                {
                    "job_posting_id": posting_id,
                    "role_id": seed.role_id,
                    "skill_id": skill_id,
                },
            )


def _sdi_input_rows(seed: MarketSeed) -> list[SdiPostingSkillInputRow]:
    return [
        SdiPostingSkillInputRow(
            job_posting_id=UUID("10000000-0000-0000-0000-000000000001"),
            dataset_id=seed.dataset_id,
            role_id=seed.role_id,
            skill_id=seed.skill_ids[0],
            posted_at=date(2026, 5, 19),
        ),
        SdiPostingSkillInputRow(
            job_posting_id=UUID("10000000-0000-0000-0000-000000000002"),
            dataset_id=seed.dataset_id,
            role_id=seed.role_id,
            skill_id=seed.skill_ids[0],
            posted_at=date(2026, 5, 12),
        ),
        SdiPostingSkillInputRow(
            job_posting_id=UUID("10000000-0000-0000-0000-000000000003"),
            dataset_id=seed.dataset_id,
            role_id=seed.role_id,
            skill_id=seed.skill_ids[0],
            posted_at=date(2026, 4, 19),
        ),
        SdiPostingSkillInputRow(
            job_posting_id=UUID("10000000-0000-0000-0000-000000000001"),
            dataset_id=seed.dataset_id,
            role_id=seed.role_id,
            skill_id=seed.skill_ids[1],
            posted_at=date(2026, 5, 19),
        ),
    ]


def _historical_snapshot(
    role_id: UUID,
    skill_id: UUID,
    demand_index: float,
    snapshot_date: date,
    requirement_version: int,
) -> HistoricalSdiSnapshotRow:
    return HistoricalSdiSnapshotRow(
        role_id=role_id,
        skill_id=skill_id,
        demand_index=demand_index,
        snapshot_date=snapshot_date,
        requirement_version=requirement_version,
    )


def _protected_table_counts(connection: Connection) -> tuple[int, int]:
    pipeline_jobs_count = int(connection.execute(text("select count(*) from pipeline_jobs")).scalar_one())
    app_events_count = int(connection.execute(text("select count(*) from app_events")).scalar_one())
    return pipeline_jobs_count, app_events_count


def _count_sdi_rows(connection: Connection, requirement_version: int) -> int:
    return int(
        connection.execute(
            text(
                """
                select count(*)
                from sdi_snapshots
                where requirement_version = :requirement_version
                """
            ),
            {"requirement_version": requirement_version},
        ).scalar_one()
    )


def _published_sdi_versions(connection: Connection, requirement_version: int) -> list[int]:
    return [
        int(value)
        for value in connection.execute(
            text(
                """
                select distinct requirement_version
                from sdi_snapshots
                where requirement_version = :requirement_version
                order by requirement_version
                """
            ),
            {"requirement_version": requirement_version},
        ).scalars()
    ]


def _all_sdi_values_in_range(connection: Connection, requirement_version: int) -> bool:
    return bool(
        connection.execute(
            text(
                """
                select bool_and(demand_index >= 0 and demand_index <= 1)
                from sdi_snapshots
                where requirement_version = :requirement_version
                """
            ),
            {"requirement_version": requirement_version},
        ).scalar_one()
    )


def _active_decay_count(connection: Connection, role_id: UUID, skill_id: UUID) -> int:
    return int(
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
            {"role_id": role_id, "skill_id": skill_id},
        ).scalar_one()
    )


def _all_decay_values_in_range(connection: Connection) -> bool:
    return bool(
        connection.execute(
            text(
                """
                select bool_and(decay_rate >= -1 and decay_rate <= 0 and confidence >= 0 and confidence <= 1)
                from skill_decay_signals
                """
            )
        ).scalar_one()
    )


def _published_decay_versions(connection: Connection, role_id: UUID, skill_id: UUID) -> list[int]:
    return [
        int(value)
        for value in connection.execute(
            text(
                """
                select distinct requirement_version
                from skill_decay_signals
                where role_id = :role_id
                  and skill_id = :skill_id
                order by requirement_version
                """
            ),
            {"role_id": role_id, "skill_id": skill_id},
        ).scalars()
    ]
