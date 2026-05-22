from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.contracts.normalized_job_posting import NormalizedJobPosting
from src.intelligence.alias_lookup import SkillLookupItem, build_alias_lookup
from src.intelligence.skill_mapper import map_skills
from src.intelligence.skill_matching_guards import (
    alias_matches_text,
    build_alias_matching_rules,
)

POSTING_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
GO_ID = UUID("11111111-1111-1111-1111-111111111111")
DJANGO_ID = UUID("22222222-2222-2222-2222-222222222222")
MONGODB_ID = UUID("33333333-3333-3333-3333-333333333333")
ALGORITHMS_ID = UUID("44444444-4444-4444-4444-444444444444")
INGESTED_AT = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)


def _posting(description: str) -> NormalizedJobPosting:
    return NormalizedJobPosting.model_validate(
        {
            "external_id": str(POSTING_ID),
            "source": "Fixture Jobs",
            "title": "Backend Engineer",
            "company": "Acme Inc",
            "location": "Remote",
            "posted_at": "2026-05-01",
            "description": description,
            "url": "https://example.com/jobs/posting",
            "source_row_number": 1,
            "ingested_at": INGESTED_AT,
            "normalized_source": "fixture jobs",
            "normalized_title": "backend engineer",
            "normalized_company": "acme inc",
            "normalized_location": "remote",
            "normalized_description": description.lower(),
            "normalized_role_hint": "backend engineer",
        }
    )


def _alias_lookup():
    return build_alias_lookup(
        [
            ("Go", "go", GO_ID, "Go"),
            ("django", "django", DJANGO_ID, "Django"),
            ("mongodb", "mongodb", MONGODB_ID, "MongoDB"),
            ("algorithms", "algorithms", ALGORITHMS_ID, "Algorithms"),
        ]
    )


def test_short_alias_rules_are_derived_from_runtime_aliases() -> None:
    rules = build_alias_matching_rules(_alias_lookup())

    assert rules["go"].requires_token_boundary is True
    assert "django" in rules
    assert "mongodb" in rules
    assert "algorithms" in rules


def test_go_alias_does_not_match_inside_known_risky_words() -> None:
    rules = build_alias_matching_rules(_alias_lookup())

    assert alias_matches_text(
        normalized_alias="go",
        normalized_text="Django MongoDB Algorithm",
        rules=rules,
    ) is False


def test_go_alias_matches_as_whole_token() -> None:
    rules = build_alias_matching_rules(_alias_lookup())

    assert alias_matches_text(
        normalized_alias="go",
        normalized_text="Experience building Go services",
        rules=rules,
    ) is True


def test_skill_mapper_applies_short_alias_guard_to_substring_scan() -> None:
    result = map_skills(
        _posting("Django MongoDB Algorithm"),
        _alias_lookup(),
        skill_name_lookup={},
    )

    assert [item.skill_name for item in result.mapped] == ["Django", "MongoDB"]
    assert all(item.skill_name != "Go" for item in result.mapped)


def test_skill_mapper_still_maps_whole_token_go_alias() -> None:
    result = map_skills(
        _posting("Backend services in Go, Django"),
        _alias_lookup(),
        skill_name_lookup={},
    )

    assert [item.skill_name for item in result.mapped] == ["Go", "Django"]
