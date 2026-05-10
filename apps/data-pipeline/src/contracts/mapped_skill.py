from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SkillMatchType = Literal["exact", "alias"]


class MappedSkillItem(BaseModel):
    skill_id: UUID
    skill_name: NonEmptyStr
    signal_text: NonEmptyStr
    match_type: SkillMatchType


class SkillMappingResult(BaseModel):
    posting_id: UUID
    mapped: list[MappedSkillItem]
    unresolved_terms: list[str]
