from __future__ import annotations

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
    connection: Connection | None = None,
) -> int:
    payload = RoleRequirementPublishInput(dataset_id=dataset_id, requirements=requirements)

    try:
        if connection is not None:
            return _publish_with_connection(connection=connection, payload=payload)

        with get_connection() as managed_connection:
            return _publish_with_connection(connection=managed_connection, payload=payload)
    except IntegrityError as error:
        raise _to_publish_error(error) from error


def _publish_with_connection(
    *,
    connection: Connection,
    payload: RoleRequirementPublishInput,
) -> int:
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

    connection.execute(
        text(
            """
            insert into role_requirement_versions (
                version,
                dataset_id,
                is_current
            )
            values (
                :version,
                :dataset_id,
                false
            )
            """
        ),
        {
            "version": new_version,
            "dataset_id": payload.dataset_id,
        },
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
            where version <> :new_version
              and is_current = true
            """
        ),
        {"new_version": new_version},
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


def _to_publish_error(error: IntegrityError) -> RoleRequirementPublishError:
    original_error_text = str(getattr(error, "orig", error)).lower()
    if "unique" in original_error_text or "duplicate key" in original_error_text:
        return RoleRequirementPublishConflictError(
            "role requirement publish failed because a uniqueness constraint was violated"
        )

    return RoleRequirementPublishIntegrityError(
        "role requirement publish failed because a database integrity constraint was violated"
    )
