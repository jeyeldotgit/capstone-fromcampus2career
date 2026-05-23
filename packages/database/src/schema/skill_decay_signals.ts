import { sql, type InferInsertModel, type InferSelectModel } from "drizzle-orm";
import {
  boolean,
  check,
  foreignKey,
  index,
  integer,
  numeric,
  pgTable,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import { careerRoles } from "./career_roles.js";
import { roleRequirementVersions } from "./role_requirement_versions.js";
import { skills } from "./skills.js";

export const skillDecaySignals = pgTable(
  "skill_decay_signals",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    roleId: uuid("role_id")
      .notNull()
      .references(() => careerRoles.id),
    skillId: uuid("skill_id")
      .notNull()
      .references(() => skills.id),
    decayRate: numeric("decay_rate", { precision: 5, scale: 4 }).notNull(),
    confidence: numeric("confidence", { precision: 5, scale: 4 }).notNull(),
    detectedAt: timestamp("detected_at", { withTimezone: true }).notNull().defaultNow(),
    requirementVersion: integer("requirement_version").notNull(),
    isActive: boolean("is_active").notNull().default(true),
  },
  (table) => [
    uniqueIndex("skill_decay_signals_role_skill_version_unique").on(
      table.roleId,
      table.skillId,
      table.requirementVersion,
    ),
    index("skill_decay_signals_role_version_idx").on(table.roleId, table.requirementVersion),
    index("skill_decay_signals_skill_version_idx").on(table.skillId, table.requirementVersion),
    index("skill_decay_signals_role_skill_active_idx").on(table.roleId, table.skillId, table.isActive),
    foreignKey({
      columns: [table.requirementVersion],
      foreignColumns: [roleRequirementVersions.version],
      name: "skill_decay_signals_requirement_version_fkey",
    }),
    check("skill_decay_signals_decay_rate_range_chk", sql`${table.decayRate} >= 0 and ${table.decayRate} <= 1`),
    check("skill_decay_signals_confidence_range_chk", sql`${table.confidence} >= 0 and ${table.confidence} <= 1`),
  ],
);

export type SkillDecaySignal = InferSelectModel<typeof skillDecaySignals>;
export type NewSkillDecaySignal = InferInsertModel<typeof skillDecaySignals>;
