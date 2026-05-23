from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from src.db import get_connection
from src.publishing.models.role_requirement_publish_model import (
    RoleRequirementAggregateRow,
    RoleRequirementPublishInput,
)


class RoleRequirementPublishError(RuntimeError):
    pass


class RoleRequirementPublishConflictError(RoleRequirementPublishError):
    pass


class RoleRequirementPublishIntegrityError(RoleRequirementPublishError):
    pass


def publish_role_requirements(
    *,
    dataset_id: UUID,
    requirements: list[RoleRequirementAggregateRow],
    period_month: date | None = None,
    lineage_dataset_ids: list[UUID] | None = None,
    connection: Connection | None = None,
) -> int:
    payload = RoleRequirementPublishInput(dataset_id=dataset_id, requirements=requirements)

    try:
        if connection is not None:
            return _publish_with_connection(
                connection=connection,
                payload=payload,
                period_month=period_month,
                lineage_dataset_ids=lineage_dataset_ids,
            )

        with get_connection() as managed_connection:
            return _publish_with_connection(
                connection=managed_connection,
                payload=payload,
                period_month=period_month,
                lineage_dataset_ids=lineage_dataset_ids,
            )
    except IntegrityError as error:
        raise _to_publish_error(error) from error


def _publish_with_connection(
    *,
    connection: Connection,
    payload: RoleRequirementPublishInput,
    period_month: date | None,
    lineage_dataset_ids: list[UUID] | None,
) -> int:
    resolved_period_month = _resolve_period_month(
        connection=connection,
        dataset_id=payload.dataset_id,
        period_month=period_month,
    )
    lineage_ids = _lineage_dataset_ids(
        dataset_id=payload.dataset_id,
        lineage_dataset_ids=lineage_dataset_ids,
    )
    new_version = int(
        connection.execute(
            text(
                """
                select coalesce(max(version), 0) + 1
                from role_requirement_versions
                """
            )
        ).scalar_one()
    )
    period_revision = int(
        connection.execute(
            text(
                """
                select coalesce(max(period_revision), 0) + 1
                from role_requirement_versions
                where period_month = :period_month
                """
            ),
            {"period_month": resolved_period_month},
        ).scalar_one()
    )

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
                false
            )
            """
        ),
        {
            "version": new_version,
            "dataset_id": payload.dataset_id,
            "period_month": resolved_period_month,
            "period_revision": period_revision,
        },
    )

    connection.execute(
        text(
            """
            insert into role_requirement_version_datasets (
                requirement_version,
                dataset_id
            )
            values (
                :requirement_version,
                :dataset_id
            )
            """
        ),
        [
            {
                "requirement_version": new_version,
                "dataset_id": lineage_dataset_id,
            }
            for lineage_dataset_id in lineage_ids
        ],
    )

    if len(payload.requirements) > 0:
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
                values (
                    :role_id,
                    :skill_id,
                    :requirement_version,
                    :required_depth,
                    :demand_weight,
                    :evidence_count
                )
                """
            ),
            [
                {
                    "role_id": requirement.role_id,
                    "skill_id": requirement.skill_id,
                    "requirement_version": new_version,
                    "required_depth": requirement.required_depth,
                    "demand_weight": requirement.demand_weight,
                    "evidence_count": requirement.evidence_count,
                }
                for requirement in payload.requirements
            ],
        )

    connection.execute(
        text(
            """
            update role_requirement_versions
            set is_current = false
            where period_month = :period_month
              and version <> :new_version
              and is_current = true
            """
        ),
        {
            "new_version": new_version,
            "period_month": resolved_period_month,
        },
    )
    connection.execute(
        text(
            """
            update role_requirement_versions
            set is_current = true
            where version = :new_version
            """
        ),
        {"new_version": new_version},
    )

    return new_version


def _resolve_period_month(
    *,
    connection: Connection,
    dataset_id: UUID,
    period_month: date | None,
) -> date:
    if period_month is not None:
        return _validate_period_month(period_month)

    derived_period_month = connection.execute(
        text(
            """
            select date_trunc('month', max(posted_at))::date
            from job_postings
            where dataset_id = :dataset_id
            """
        ),
        {"dataset_id": dataset_id},
    ).scalar_one_or_none()
    if derived_period_month is None:
        raise ValueError("period_month is required when the dataset has no published posting window")

    return _validate_period_month(derived_period_month)


def _validate_period_month(value: date) -> date:
    if value.day != 1:
        raise ValueError("period_month must be the first day of the month")
    return value


def _lineage_dataset_ids(
    *,
    dataset_id: UUID,
    lineage_dataset_ids: list[UUID] | None,
) -> list[UUID]:
    ids = [dataset_id, *(lineage_dataset_ids or [])]
    unique_ids: list[UUID] = []
    seen_ids: set[UUID] = set()
    for lineage_dataset_id in ids:
        if lineage_dataset_id in seen_ids:
            continue
        seen_ids.add(lineage_dataset_id)
        unique_ids.append(lineage_dataset_id)
    return unique_ids


def _to_publish_error(error: IntegrityError) -> RoleRequirementPublishError:
    original_error_text = str(getattr(error, "orig", error)).lower()
    if "unique" in original_error_text or "duplicate key" in original_error_text:
        return RoleRequirementPublishConflictError(
            "role requirement publish failed because a uniqueness constraint was violated"
        )

    return RoleRequirementPublishIntegrityError(
        "role requirement publish failed because a database integrity constraint was violated"
    )
