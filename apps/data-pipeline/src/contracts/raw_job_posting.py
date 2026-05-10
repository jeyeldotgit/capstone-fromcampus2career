from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class RawJobPosting(BaseModel):
    model_config = ConfigDict(extra="ignore")

    external_id: str
    source: str
    title: str
    company: str
    location: str
    posted_at: date
    description: str
    url: str
    employment_type: str | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    currency: str | None = None
    experience_level: str | None = None

    @field_validator(
        "external_id",
        "source",
        "title",
        "company",
        "location",
        "description",
        "url",
        "employment_type",
        "currency",
        "experience_level",
        mode="before",
    )
    @classmethod
    def _coerce_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            if normalized == "":
                return None
            return normalized
        return str(value).strip()

    @field_validator("salary_min", "salary_max", mode="before")
    @classmethod
    def _coerce_optional_decimal(cls, value: Any) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return Decimal(str(value).strip())

    @field_validator("posted_at", mode="before")
    @classmethod
    def _coerce_posted_at(cls, value: Any) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.endswith("Z"):
                normalized = f"{normalized[:-1]}+00:00"
            try:
                return date.fromisoformat(normalized)
            except ValueError:
                return datetime.fromisoformat(normalized).date()
        raise TypeError("posted_at must be a date or ISO 8601 string")
