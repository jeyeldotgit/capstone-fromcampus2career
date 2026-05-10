from __future__ import annotations

from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.intelligence.alias_lookup import build_alias_lookup, normalize_signal

MACHINE_LEARNING_ID = UUID("33333333-3333-3333-3333-333333333333")


def test_whitespace_normalization() -> None:
    rows = [
        (
            "Machine   Learning",
            "machine learning",
            MACHINE_LEARNING_ID,
            "Machine Learning",
        )
    ]

    lookup = build_alias_lookup(rows)
    normalized_signal = normalize_signal("  Machine\t Learning  ")

    assert normalized_signal == "machine learning"
    assert lookup[normalized_signal].skill_id == MACHINE_LEARNING_ID
    assert lookup[normalized_signal].skill_name == "Machine Learning"
