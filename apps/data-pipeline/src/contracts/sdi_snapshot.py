from __future__ import annotations

import math
from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SdiSnapshotPublishRow(BaseModel):
    role_id: UUID
    skill_id: UUID
    demand_index: float = Field(ge=0.0, le=1.0)
    snapshot_date: date
    requirement_version: int = Field(gt=0)

    @field_validator("demand_index")
    @classmethod
    def _must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("demand_index must be finite")
        return value
