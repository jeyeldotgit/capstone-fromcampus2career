from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import re

from src.intelligence.alias_lookup import normalize_signal

DEFAULT_COLLISION_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "as",
        "at",
        "be",
        "by",
        "do",
        "go",
        "in",
        "it",
        "of",
        "on",
        "or",
        "to",
        "up",
        "us",
        "we",
    }
)
SHORT_ALIAS_TOKEN_LENGTH = 3
_TOKEN_BOUNDARY_CHARS = r"A-Za-z0-9+#."


@dataclass(frozen=True, slots=True)
class AliasMatchingRule:
    normalized_alias: str
    requires_token_boundary: bool


AliasMatchingRules = dict[str, AliasMatchingRule]


def build_alias_matching_rules(
    aliases: Iterable[str] | Mapping[str, object],
    *,
    collision_words: frozenset[str] = DEFAULT_COLLISION_WORDS,
    short_alias_token_length: int = SHORT_ALIAS_TOKEN_LENGTH,
) -> AliasMatchingRules:
    alias_values = aliases.keys() if isinstance(aliases, Mapping) else aliases
    rules: AliasMatchingRules = {}
    for alias in alias_values:
        normalized_alias = normalize_signal(alias)
        if normalized_alias == "":
            continue
        rules[normalized_alias] = AliasMatchingRule(
            normalized_alias=normalized_alias,
            requires_token_boundary=_requires_token_boundary(
                normalized_alias,
                collision_words=collision_words,
                short_alias_token_length=short_alias_token_length,
            ),
        )
    return rules


def alias_matches_text(
    *,
    normalized_alias: str,
    normalized_text: str,
    rules: AliasMatchingRules,
) -> bool:
    alias = normalize_signal(normalized_alias)
    text = normalize_signal(normalized_text)
    rule = rules.get(alias)
    if rule is None:
        rule = AliasMatchingRule(
            normalized_alias=alias,
            requires_token_boundary=_requires_token_boundary(
                alias,
                collision_words=DEFAULT_COLLISION_WORDS,
                short_alias_token_length=SHORT_ALIAS_TOKEN_LENGTH,
            ),
        )

    if not rule.requires_token_boundary:
        return alias in text

    return re.search(_token_boundary_pattern(alias), text) is not None


def _requires_token_boundary(
    normalized_alias: str,
    *,
    collision_words: frozenset[str],
    short_alias_token_length: int,
) -> bool:
    tokens = [token for token in re.split(r"\s+", normalized_alias) if token]
    return (
        any(len(token) <= short_alias_token_length for token in tokens)
        or normalized_alias in collision_words
    )


def _token_boundary_pattern(normalized_alias: str) -> re.Pattern[str]:
    escaped_alias = re.escape(normalized_alias)
    return re.compile(
        rf"(?<![{_TOKEN_BOUNDARY_CHARS}]){escaped_alias}(?![{_TOKEN_BOUNDARY_CHARS}])"
    )
