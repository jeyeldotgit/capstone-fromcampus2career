from __future__ import annotations

import re
import string

_WHITESPACE_PATTERN = re.compile(r"\s+")
_PUNCTUATION_TRANSLATION = str.maketrans({character: " " for character in string.punctuation})


def collapse_whitespace(value: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", value.strip())


def strip_common_punctuation(value: str) -> str:
    return value.translate(_PUNCTUATION_TRANSLATION)


def clean_text(value: str) -> str:
    without_punctuation = strip_common_punctuation(value)
    return collapse_whitespace(without_punctuation).lower()
