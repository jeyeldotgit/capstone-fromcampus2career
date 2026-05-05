import { careerRoles as sourceCareerRoles } from "../../../seed/taxonomy-seed.ts";
import { ROLE_IDS } from "./id-maps.ts";

export interface CareerRoleSeedRow {
  id: string;
  code: string;
  title: string;
  description: string;
  is_active: boolean;
  category: string;
}

export const careerRolesSeed: CareerRoleSeedRow[] = sourceCareerRoles.map((careerRole) => ({
  id: ROLE_IDS[careerRole.role_id as keyof typeof ROLE_IDS],
  code: careerRole.role_id,
  title: careerRole.title,
  description: careerRole.description,
  is_active: careerRole.is_active,
  category: careerRole.category,
}));
