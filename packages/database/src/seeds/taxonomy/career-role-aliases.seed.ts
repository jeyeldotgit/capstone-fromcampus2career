import { careerRoleAliases as sourceCareerRoleAliases } from "../../../seed/taxonomy-seed.ts";
import { ROLE_ALIAS_IDS, ROLE_IDS } from "./id-maps.ts";

export interface CareerRoleAliasSeedRow {
  id: string;
  code: string;
  role_id: string;
  alias: string;
  normalized_alias: string;
}

function resolveRoleId(roleCode: string): string {
  const roleId = ROLE_IDS[roleCode as keyof typeof ROLE_IDS];

  if (!roleId) {
    throw new Error(`Unknown career role code in taxonomy seed: ${roleCode}`);
  }

  return roleId;
}

export const careerRoleAliasesSeed: CareerRoleAliasSeedRow[] = sourceCareerRoleAliases.map(
  (careerRoleAlias) => ({
    id: ROLE_ALIAS_IDS[careerRoleAlias.alias_id as keyof typeof ROLE_ALIAS_IDS],
    code: careerRoleAlias.alias_id,
    role_id: resolveRoleId(careerRoleAlias.role_id),
    alias: careerRoleAlias.alias,
    normalized_alias: careerRoleAlias.normalized_alias,
  }),
);
