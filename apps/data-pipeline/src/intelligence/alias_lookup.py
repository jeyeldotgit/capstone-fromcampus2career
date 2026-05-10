from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import re
from typing import cast
from uuid import UUID

from sqlalchemy import Connection, text

from src.db import get_connection

_WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class SkillLookupItem:
    skill_id: UUID
    skill_name: str


SkillAliasRow = tuple[str, str, UUID, str]
AliasLookup = dict[str, SkillLookupItem]


def normalize_signal(value: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", value.strip()).lower()


def build_alias_lookup(rows: Iterable[SkillAliasRow]) -> AliasLookup:
    lookup: AliasLookup = {}
    for _alias, normalized_alias, skill_id, skill_name in rows:
        if normalized_alias in lookup:
            raise ValueError(f"duplicate normalized_alias in skill alias lookup: {normalized_alias}")

        lookup[normalized_alias] = SkillLookupItem(
            skill_id=skill_id,
            skill_name=skill_name,
        )

    return lookup


def load_skill_alias_rows(connection: Connection | None = None) -> list[SkillAliasRow]:
    if connection is not None:
        return _load_skill_alias_rows_from_connection(connection)

    with get_connection() as managed_connection:
        return _load_skill_alias_rows_from_connection(managed_connection)


def _load_skill_alias_rows_from_connection(connection: Connection) -> list[SkillAliasRow]:
    result = connection.execute(
        text(
            """
            select
                skill_aliases.alias,
                skill_aliases.normalized_alias,
                skills.id as skill_id,
                skills.name as skill_name
            from skill_aliases
            join skills on skills.id = skill_aliases.skill_id
            where skills.is_active = true
            order by skill_aliases.normalized_alias, skill_aliases.alias
            """
        )
    )
    rows = cast(Sequence[Mapping[str, object]], result.mappings().all())

    return [
        (
            str(row["alias"]),
            str(row["normalized_alias"]),
            UUID(str(row["skill_id"])),
            str(row["skill_name"]),
        )
        for row in rows
    ]
