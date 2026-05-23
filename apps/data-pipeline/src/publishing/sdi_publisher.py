from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Connection, text

from src.contracts.sdi_snapshot import SdiSnapshotPublishRow
from src.db import get_connection


class ConflictError(RuntimeError):
    pass


class RequirementVersionNotFoundError(RuntimeError):
    pass


def publish_sdi_snapshots(
    *,
    requirement_version: int,
    rows: list[SdiSnapshotPublishRow],
    connection: Connection | None = None,
) -> int:
    validated_rows = [SdiSnapshotPublishRow.model_validate(row) for row in rows]
    if any(row.requirement_version != requirement_version for row in validated_rows):
        raise ValueError("all SDI rows must use the requested requirement_version")

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
    rows: list[SdiSnapshotPublishRow],
) -> int:
    period_month = _load_requirement_period_month(
        connection=connection,
        requirement_version=requirement_version,
    )

    for row in rows:
        if row.snapshot_date != period_month:
            raise ValueError("sdi snapshot_date must equal the requirement version period_month")

        existing = connection.execute(
            text(
                """
                select demand_index
                from sdi_snapshots
                where role_id = :role_id
                  and skill_id = :skill_id
                  and snapshot_date = :snapshot_date
                  and requirement_version = :requirement_version
                """
            ),
            {
                "role_id": row.role_id,
                "skill_id": row.skill_id,
                "snapshot_date": row.snapshot_date,
                "requirement_version": row.requirement_version,
            },
        ).mappings().one_or_none()

        if existing is not None:
            existing_demand_index = round(float(existing["demand_index"]), 4)
            incoming_demand_index = round(row.demand_index, 4)
            if existing_demand_index == incoming_demand_index:
                continue
            raise ConflictError(
                "sdi_snapshots already contains a differing row for role_id, skill_id, snapshot_date, and requirement_version"
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
                "role_id": row.role_id,
                "skill_id": row.skill_id,
                "demand_index": row.demand_index,
                "snapshot_date": row.snapshot_date,
                "requirement_version": row.requirement_version,
            },
        )

    return requirement_version


def _load_requirement_period_month(
    *,
    connection: Connection,
    requirement_version: int,
) -> date:
    period_month = connection.execute(
        text(
            """
            select period_month
            from role_requirement_versions
            where version = :requirement_version
            """
        ),
        {"requirement_version": requirement_version},
    ).scalar_one_or_none()
    if period_month is None:
        raise RequirementVersionNotFoundError(
            f"role_requirement_versions row not found for version={requirement_version}"
        )
    return period_month
