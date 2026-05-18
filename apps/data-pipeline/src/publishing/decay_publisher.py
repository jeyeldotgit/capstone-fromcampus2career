from __future__ import annotations

from sqlalchemy import Connection, text

from src.contracts.skill_decay_signal import SkillDecaySignalPublishRow
from src.db import get_connection
from src.publishing.sdi_publisher import RequirementVersionNotFoundError


def publish_decay_signals(
    *,
    requirement_version: int,
    rows: list[SkillDecaySignalPublishRow],
    connection: Connection | None = None,
) -> int:
    validated_rows = [SkillDecaySignalPublishRow.model_validate(row) for row in rows]
    if any(row.requirement_version != requirement_version for row in validated_rows):
        raise ValueError("all decay rows must use the requested requirement_version")

    if connection is not None:
        return _publish_with_connection(
            connection=connection,
            requirement_version=requirement_version,
            rows=validated_rows,
        )

    with get_connection() as managed_connection:
        return _publish_with_connection(
            connection=managed_connection,
            requirement_version=requirement_version,
            rows=validated_rows,
        )


def _publish_with_connection(
    *,
    connection: Connection,
    requirement_version: int,
    rows: list[SkillDecaySignalPublishRow],
) -> int:
    _ensure_requirement_version_exists(connection=connection, requirement_version=requirement_version)

    for row in rows:
        connection.execute(
            text(
                """
                update skill_decay_signals
                set is_active = false
                where role_id = :role_id
                  and skill_id = :skill_id
                  and is_active = true
                """
            ),
            {
                "role_id": row.role_id,
                "skill_id": row.skill_id,
            },
        )
        connection.execute(
            text(
                """
                insert into skill_decay_signals (
                    role_id,
                    skill_id,
                    decay_rate,
                    confidence,
                    detected_at,
                    requirement_version,
                    is_active
                )
                values (
                    :role_id,
                    :skill_id,
                    :decay_rate,
                    :confidence,
                    :detected_at,
                    :requirement_version,
                    :is_active
                )
                """
            ),
            {
                "role_id": row.role_id,
                "skill_id": row.skill_id,
                "decay_rate": row.decay_rate,
                "confidence": row.confidence,
                "detected_at": row.detected_at,
                "requirement_version": row.requirement_version,
                "is_active": row.is_active,
            },
        )

    return requirement_version


def _ensure_requirement_version_exists(
    *,
    connection: Connection,
    requirement_version: int,
) -> None:
    exists = connection.execute(
        text(
            """
            select exists (
                select 1
                from role_requirement_versions
                where version = :requirement_version
            )
            """
        ),
        {"requirement_version": requirement_version},
    ).scalar_one()
    if not exists:
        raise RequirementVersionNotFoundError(
            f"role_requirement_versions row not found for version={requirement_version}"
        )
