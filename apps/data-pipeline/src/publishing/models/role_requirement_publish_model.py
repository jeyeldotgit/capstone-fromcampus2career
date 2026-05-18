from __future__ import annotations

import math
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RoleRequirementAggregateRow(BaseModel):
    role_id: UUID
    skill_id: UUID
    required_depth: float = Field(ge=0.0, le=1.0)
    demand_weight: float = Field(ge=0.1, le=1.0)
    evidence_count: int = Field(ge=5)

    @field_validator("required_depth", "demand_weight")
    @classmethod
    def _must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        return value


class RoleRequirementPublishInput(BaseModel):
    dataset_id: UUID
    requirements: list[RoleRequirementAggregateRow]
