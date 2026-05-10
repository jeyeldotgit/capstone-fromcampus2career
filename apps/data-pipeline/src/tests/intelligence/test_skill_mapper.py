from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import UUID

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.contracts.normalized_job_posting import NormalizedJobPosting
from src.intelligence.alias_lookup import AliasLookup, SkillLookupItem, build_alias_lookup
from src.intelligence.skill_mapper import SkillNameLookup, map_skills

POSTING_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PYTHON_ID = UUID("11111111-1111-1111-1111-111111111111")
JAVASCRIPT_ID = UUID("22222222-2222-2222-2222-222222222222")
MACHINE_LEARNING_ID = UUID("33333333-3333-3333-3333-333333333333")
INGESTED_AT = datetime(2026, 5, 10, 10, 0, tzinfo=timezone.utc)


def _posting(description: str) -> NormalizedJobPosting:
    return NormalizedJobPosting.model_validate(
        {
            "external_id": str(POSTING_ID),
            "source": "Fixture Jobs",
            "title": "Data Analyst",
            "company": "Acme Inc",
            "location": "Remote",
            "posted_at": "2026-05-01",
            "description": description,
            "url": "https://example.com/jobs/posting",
            "source_row_number": 1,
            "ingested_at": INGESTED_AT,
            "normalized_source": "fixture jobs",
            "normalized_title": "data analyst",
            "normalized_company": "acme inc",
            "normalized_location": "remote",
            "normalized_description": description.lower(),
            "normalized_role_hint": "data analyst",
        }
    )


def _alias_lookup() -> AliasLookup:
    return build_alias_lookup(
        [
            ("js", "js", JAVASCRIPT_ID, "JavaScript"),
            ("javascript es6", "javascript es6", JAVASCRIPT_ID, "JavaScript"),
        ]
    )


def _skill_name_lookup() -> SkillNameLookup:
    return {
        "python": SkillLookupItem(PYTHON_ID, "Python"),
        "machine learning": SkillLookupItem(MACHINE_LEARNING_ID, "Machine Learning"),
    }


def test_exact_name_match() -> None:
    result = map_skills(_posting("Python"), _alias_lookup(), _skill_name_lookup())

    assert result.posting_id == POSTING_ID
    assert len(result.mapped) == 1
    assert result.mapped[0].skill_id == PYTHON_ID
    assert result.mapped[0].skill_name == "Python"
    assert result.mapped[0].signal_text == "Python"
    assert result.mapped[0].match_type == "exact"
    assert result.unresolved_terms == []


def test_alias_match() -> None:
    result = map_skills(_posting("js"), _alias_lookup(), _skill_name_lookup())

    assert len(result.mapped) == 1
    assert result.mapped[0].skill_id == JAVASCRIPT_ID
    assert result.mapped[0].match_type == "alias"
    assert result.unresolved_terms == []


def test_multiple_aliases_same_skill() -> None:
    result = map_skills(_posting("js; javascript es6"), _alias_lookup(), _skill_name_lookup())

    assert [item.skill_id for item in result.mapped] == [JAVASCRIPT_ID, JAVASCRIPT_ID]
    assert [item.match_type for item in result.mapped] == ["alias", "alias"]
    assert result.unresolved_terms == []


def test_unresolved_term_preserved() -> None:
    result = map_skills(_posting("Python, COBOL"), _alias_lookup(), _skill_name_lookup())

    assert [item.skill_id for item in result.mapped] == [PYTHON_ID]
    assert result.unresolved_terms == ["COBOL"]


def test_empty_signal_list() -> None:
    result = map_skills(_posting(" , ; \n "), _alias_lookup(), _skill_name_lookup())

    assert result.mapped == []
    assert result.unresolved_terms == []


def test_case_insensitive_exact() -> None:
    result = map_skills(_posting("PYTHON"), _alias_lookup(), _skill_name_lookup())

    assert len(result.mapped) == 1
    assert result.mapped[0].skill_id == PYTHON_ID
    assert result.mapped[0].match_type == "exact"
    assert result.unresolved_terms == []


def test_no_db_write(monkeypatch: pytest.MonkeyPatch) -> None:
    from src import db as pipeline_db

    connection_calls: list[str] = []

    def forbidden_get_connection() -> object:
        connection_calls.append("get_connection")
        raise AssertionError("skill mapping must not open a database connection")

    monkeypatch.setattr(pipeline_db, "get_connection", forbidden_get_connection)

    result = map_skills(_posting("Python"), _alias_lookup(), _skill_name_lookup())

    assert len(result.mapped) == 1
    assert connection_calls == []
