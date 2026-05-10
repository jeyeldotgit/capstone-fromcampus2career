from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RejectedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_number: int = Field(gt=0)
    raw_payload: dict[str, object]
    reason: str = Field(min_length=1)
