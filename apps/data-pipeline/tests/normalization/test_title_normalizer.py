from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.normalization.title_normalizer import normalize_title


def test_title_normalizer_uses_text_cleaning_rules() -> None:
    assert normalize_title("  DATA--Analyst!!! ") == "data analyst"


def test_title_normalizer_expands_common_seniority_abbreviations() -> None:
    assert normalize_title("Sr. Backend Eng") == "senior backend engineer"
    assert normalize_title("Jr Frontend Dev") == "junior frontend developer"


def test_title_punctuation_case_and_whitespace_variants_match() -> None:
    values = [
        "Senior Data Analyst",
        " senior   data analyst ",
        "SR. DATA-ANALYST",
        "Sr, Data Analyst!",
    ]

    assert {normalize_title(value) for value in values} == {"senior data analyst"}
