from __future__ import annotations

import re
import string

from src.normalization.text_cleaner import collapse_whitespace

_TOKEN_PLACEHOLDERS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\bc\s*\+\s*\+", re.IGNORECASE), " cplusplusplaceholder ", "c++"),
    (re.compile(r"\bc\s*#", re.IGNORECASE), " csharpplaceholder ", "c#"),
    (re.compile(r"(?<!\w)\.net\b", re.IGNORECASE), " dotnetplaceholder ", ".net"),
)
_PUNCTUATION_FOR_TOKENS = string.punctuation.replace("+", "").replace("#", "").replace(".", "")
_PUNCTUATION_TRANSLATION = str.maketrans(
    {character: " " for character in _PUNCTUATION_FOR_TOKENS}
)


def normalize_skill_token(value: str) -> str:
    normalized = collapse_whitespace(value).lower()

    for pattern, placeholder, _replacement in _TOKEN_PLACEHOLDERS:
        normalized = pattern.sub(placeholder, normalized)

    normalized = collapse_whitespace(normalized.translate(_PUNCTUATION_TRANSLATION))

    for _pattern, placeholder, replacement in _TOKEN_PLACEHOLDERS:
        normalized = normalized.replace(placeholder.strip(), replacement)

    return normalized
