from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SkillDecaySignalPublishRow(BaseModel):
    role_id: UUID
    skill_id: UUID
    decay_rate: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    detected_at: datetime
    requirement_version: int = Field(gt=0)
    is_active: bool = True

    @field_validator("decay_rate", "confidence")
    @classmethod
    def _must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        return value
