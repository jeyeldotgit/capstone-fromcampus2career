import { skills as sourceSkills } from "../../../seed/taxonomy-seed.ts";
import { SKILL_IDS } from "./id-maps.ts";

export interface SkillSeedRow {
  id: string;
  code: string;
  name: string;
  category: string;
  is_active: boolean;
  notes: string;
}

export const skillsSeed: SkillSeedRow[] = sourceSkills.map((skill) => ({
  id: SKILL_IDS[skill.skill_id as keyof typeof SKILL_IDS],
  code: skill.skill_id,
  name: skill.name,
  category: skill.category,
  is_active: skill.is_active,
  notes: skill.notes,
}));
