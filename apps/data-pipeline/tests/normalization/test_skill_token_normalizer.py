from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.normalization.skill_token_normalizer import normalize_skill_token


def test_skill_token_normalizer_lowercases_and_collapses_whitespace() -> None:
    assert normalize_skill_token("  Machine\t Learning  ") == "machine learning"


def test_skill_token_normalizer_strips_ordinary_punctuation() -> None:
    assert normalize_skill_token("Python, SQL; dashboards!") == "python sql dashboards"


def test_skill_token_normalizer_preserves_c_family_tokens() -> None:
    assert normalize_skill_token("C++, C#, and SQL") == "c++ c# and sql"


def test_skill_token_punctuation_case_and_whitespace_variants_match() -> None:
    values = [
        "Data Visualization",
        " data   visualization ",
        "DATA-VISUALIZATION",
        "Data, Visualization!",
    ]

    assert {normalize_skill_token(value) for value in values} == {"data visualization"}
