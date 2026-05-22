from __future__ import annotations

import re
from uuid import UUID

from src.contracts.mapped_skill import MappedSkillItem, SkillMappingResult, SkillMatchType
from src.contracts.normalized_job_posting import NormalizedJobPosting
from src.intelligence.alias_lookup import AliasLookup, SkillLookupItem, normalize_signal
from src.intelligence.skill_matching_guards import (
    AliasMatchingRules,
    alias_matches_text,
    build_alias_matching_rules,
)

_SIGNAL_DELIMITER_PATTERN = re.compile(r"[,;\n]+")
SkillNameLookup = dict[str, SkillLookupItem]


def map_skills(
    posting: NormalizedJobPosting,
    alias_lookup: AliasLookup,
    skill_name_lookup: SkillNameLookup,
    alias_matching_rules: AliasMatchingRules | None = None,
) -> SkillMappingResult:
    mapped: list[MappedSkillItem] = []
    unresolved_terms: list[str] = []
    resolved_alias_rules = alias_matching_rules or build_alias_matching_rules(alias_lookup)

    for signal_text in _extract_skill_signals(posting.description):
        lookup_key = normalize_signal(signal_text)
        exact_match = skill_name_lookup.get(lookup_key)
        if exact_match is not None:
            mapped.append(_to_mapped_skill(signal_text, exact_match, "exact"))
            continue

        alias_match = alias_lookup.get(lookup_key)
        if alias_match is not None:
            mapped.append(_to_mapped_skill(signal_text, alias_match, "alias"))
            continue

        substring_alias_matches = [
            (normalized_alias, lookup_item)
            for normalized_alias, lookup_item in sorted(alias_lookup.items())
            if alias_matches_text(
                normalized_alias=normalized_alias,
                normalized_text=lookup_key,
                rules=resolved_alias_rules,
            )
        ]
        if len(substring_alias_matches) > 0:
            mapped.extend(
                _to_mapped_skill(signal_text, lookup_item, "alias")
                for _normalized_alias, lookup_item in substring_alias_matches
            )
            continue

        unresolved_terms.append(signal_text)

    return SkillMappingResult(
        posting_id=UUID(posting.external_id),
        mapped=mapped,
        unresolved_terms=unresolved_terms,
    )


def _extract_skill_signals(description: str) -> list[str]:
    return [
        signal
        for raw_signal in _SIGNAL_DELIMITER_PATTERN.split(description)
        if (signal := raw_signal.strip()) != ""
    ]


def _to_mapped_skill(
    signal_text: str,
    lookup_item: SkillLookupItem,
    match_type: SkillMatchType,
) -> MappedSkillItem:
    return MappedSkillItem(
        skill_id=lookup_item.skill_id,
        skill_name=lookup_item.skill_name,
        signal_text=signal_text,
        match_type=match_type,
    )
