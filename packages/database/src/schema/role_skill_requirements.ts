import { sql, type InferInsertModel, type InferSelectModel } from "drizzle-orm";
import { check, foreignKey, index, integer, numeric, pgTable, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { careerRoles } from "./career_roles";
import { roleRequirementVersions } from "./role_requirement_versions";
import { skills } from "./skills";

export const roleSkillRequirements = pgTable(
  "role_skill_requirements",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    roleId: uuid("role_id")
      .notNull()
      .references(() => careerRoles.id),
    skillId: uuid("skill_id")
      .notNull()
      .references(() => skills.id),
    requirementVersion: integer("requirement_version").notNull(),
    requiredDepth: numeric("required_depth", { precision: 5, scale: 4 }).notNull(),
    demandWeight: numeric("demand_weight", { precision: 5, scale: 4 }).notNull(),
    evidenceCount: integer("evidence_count").notNull().default(0),
  },
  (table) => [
    uniqueIndex("role_skill_requirements_role_skill_version_unique").on(
      table.roleId,
      table.skillId,
      table.requirementVersion,
    ),
    index("role_skill_requirements_role_version_idx").on(table.roleId, table.requirementVersion),
    index("role_skill_requirements_skill_version_idx").on(table.skillId, table.requirementVersion),
    foreignKey({
      columns: [table.requirementVersion],
      foreignColumns: [roleRequirementVersions.version],
      name: "role_skill_requirements_requirement_version_fkey",
    }),
    check(
      "role_skill_requirements_required_depth_range_chk",
      sql`${table.requiredDepth} >= 0 and ${table.requiredDepth} <= 1`,
    ),
    check(
      "role_skill_requirements_demand_weight_range_chk",
      sql`${table.demandWeight} >= 0.1 and ${table.demandWeight} <= 1`,
    ),
    check(
      "role_skill_requirements_evidence_count_min_chk",
      sql`${table.evidenceCount} >= 5`,
    ),
  ],
);

export type RoleSkillRequirement = InferSelectModel<typeof roleSkillRequirements>;
export type NewRoleSkillRequirement = InferInsertModel<typeof roleSkillRequirements>;
