import { skillAliases as sourceSkillAliases } from "../../../seed/taxonomy-seed.ts";
import { SKILL_ALIAS_IDS, SKILL_IDS } from "./id-maps.ts";

export interface SkillAliasSeedRow {
  id: string;
  code: string;
  skill_id: string;
  alias: string;
  normalized_alias: string;
  source: string;
  reviewed: boolean;
  notes: string;
}

function normalizeSkillAlias(alias: string): string {
  return alias.toLowerCase().trim().replace(/\s+/g, " ");
}

function resolveSkillId(skillCode: string): string {
  const skillId = SKILL_IDS[skillCode as keyof typeof SKILL_IDS];

  if (!skillId) {
    throw new Error(`Unknown skill code in taxonomy seed: ${skillCode}`);
  }

  return skillId;
}

export const skillAliasesSeed: SkillAliasSeedRow[] = sourceSkillAliases.map((skillAlias) => ({
  id: SKILL_ALIAS_IDS[skillAlias.alias_id as keyof typeof SKILL_ALIAS_IDS],
  code: skillAlias.alias_id,
  skill_id: resolveSkillId(skillAlias.skill_id),
  alias: skillAlias.alias,
  normalized_alias: normalizeSkillAlias(skillAlias.alias),
  source: skillAlias.source,
  reviewed: skillAlias.reviewed,
  notes: skillAlias.notes,
}));
