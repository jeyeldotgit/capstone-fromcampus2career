from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.normalization.role_hint_normalizer import (
    normalize_persisted_alias,
    normalize_role_hint,
    normalize_role_hint_query,
)


def test_persisted_alias_contract_trims_collapses_and_lowercases_only() -> None:
    assert normalize_persisted_alias("  Senior,   Data\tAnalyst!  ") == "senior, data analyst!"


def test_role_hint_uses_persisted_alias_contract() -> None:
    assert normalize_role_hint("  QA / Test   Engineer ") == "qa / test engineer"


def test_query_normalization_can_strip_punctuation_without_changing_alias_contract() -> None:
    raw_value = "  QA / Test   Engineer "

    assert normalize_persisted_alias(raw_value) == "qa / test engineer"
    assert normalize_role_hint_query(raw_value) == "qa test engineer"
