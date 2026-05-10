from __future__ import annotations

from src.normalization.text_cleaner import clean_text

_TITLE_TOKEN_REPLACEMENTS: dict[str, str] = {
    "sr": "senior",
    "jr": "junior",
    "dev": "developer",
    "eng": "engineer",
}


def normalize_title(value: str) -> str:
    tokens = clean_text(value).split()
    canonical_tokens = [_TITLE_TOKEN_REPLACEMENTS.get(token, token) for token in tokens]
    return " ".join(canonical_tokens)
