from __future__ import annotations

from datetime import date
from uuid import UUID
from uuid import uuid4

import pytest

from src.contracts.mapped_skill import MappedSkillItem
from src.contracts.mapped_skill import MappedRoleSkillRow
from src.runner import RunnerError, _deduplicate_mapped_skills, _prepare_sdi_input_rows


def _mapped_skill(skill_id: str, signal_text: str) -> MappedSkillItem:
    return MappedSkillItem(
        skill_id=UUID(skill_id),
        skill_name=f"Skill {signal_text}",
        signal_text=signal_text,
        match_type="alias",
    )


def test_deduplicate_mapped_skills_keeps_first_entry_per_skill() -> None:
    python_id = "11111111-1111-1111-1111-111111111111"
    sql_id = "22222222-2222-2222-2222-222222222222"
    deduplicated = _deduplicate_mapped_skills(
        [
            _mapped_skill(python_id, "python"),
            _mapped_skill(sql_id, "sql"),
            _mapped_skill(python_id, "python programming"),
            _mapped_skill(sql_id, "structured query language"),
        ]
    )

    assert [item.skill_id for item in deduplicated] == [UUID(python_id), UUID(sql_id)]
    assert [item.signal_text for item in deduplicated] == ["python", "sql"]


def test_prepare_sdi_input_rows_filters_and_deduplicates_rows() -> None:
    role_id = uuid4()
    required_skill_id = uuid4()
    excluded_skill_id = uuid4()
    posting_id = uuid4()
    dataset_id = uuid4()
    mapped_rows = [
        MappedRoleSkillRow(
            job_posting_id=posting_id,
            role_id=role_id,
            skill_id=required_skill_id,
            normalized_depth=0.8,
        ),
        MappedRoleSkillRow(
            job_posting_id=posting_id,
            role_id=role_id,
            skill_id=required_skill_id,
            normalized_depth=0.8,
        ),
        MappedRoleSkillRow(
            job_posting_id=posting_id,
            role_id=role_id,
            skill_id=excluded_skill_id,
            normalized_depth=0.8,
        ),
    ]

    rows = _prepare_sdi_input_rows(
        dataset_id=dataset_id,
        mapped_rows=mapped_rows,
        posting_dates_by_id={posting_id: date(2026, 4, 1)},
        required_pairs={(role_id, required_skill_id)},
    )

    assert len(rows) == 1
    assert rows[0].job_posting_id == posting_id
    assert rows[0].role_id == role_id
    assert rows[0].skill_id == required_skill_id
    assert rows[0].dataset_id == dataset_id
    assert rows[0].posted_at == date(2026, 4, 1)


def test_prepare_sdi_input_rows_raises_when_posting_date_missing() -> None:
    role_id = uuid4()
    skill_id = uuid4()
    posting_id = uuid4()

    with pytest.raises(RunnerError, match="missing posted_at"):
        _prepare_sdi_input_rows(
            dataset_id=uuid4(),
            mapped_rows=[
                MappedRoleSkillRow(
                    job_posting_id=posting_id,
                    role_id=role_id,
                    skill_id=skill_id,
                    normalized_depth=0.8,
                )
            ],
            posting_dates_by_id={},
            required_pairs={(role_id, skill_id)},
        )


def test_deduplicate_mapped_skills_preserves_unique_items() -> None:
    python_id = "11111111-1111-1111-1111-111111111111"
    sql_id = "22222222-2222-2222-2222-222222222222"
    deduplicated = _deduplicate_mapped_skills(
        [
            _mapped_skill(python_id, "python"),
            _mapped_skill(sql_id, "sql"),
        ]
    )

    assert [item.skill_id for item in deduplicated] == [UUID(python_id), UUID(sql_id)]
