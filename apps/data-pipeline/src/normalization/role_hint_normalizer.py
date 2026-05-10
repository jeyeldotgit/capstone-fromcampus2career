from __future__ import annotations

import re

from src.normalization.text_cleaner import clean_text

_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_persisted_alias(value: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", value.strip()).lower()


def normalize_role_hint(value: str) -> str:
    return normalize_persisted_alias(value)


def normalize_role_hint_query(value: str) -> str:
    return clean_text(value)
