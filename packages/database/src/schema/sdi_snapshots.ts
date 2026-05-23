import { sql, type InferInsertModel, type InferSelectModel } from "drizzle-orm";
import { check, date, foreignKey, index, integer, numeric, pgTable, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { careerRoles } from "./career_roles.js";
import { roleRequirementVersions } from "./role_requirement_versions.js";
import { skills } from "./skills.js";

export const sdiSnapshots = pgTable(
  "sdi_snapshots",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    roleId: uuid("role_id")
      .notNull()
      .references(() => careerRoles.id),
    skillId: uuid("skill_id")
      .notNull()
      .references(() => skills.id),
    demandIndex: numeric("demand_index", { precision: 5, scale: 4 }).notNull(),
    snapshotDate: date("snapshot_date", { mode: "string" }).notNull(),
    requirementVersion: integer("requirement_version").notNull(),
  },
  (table) => [
    uniqueIndex("sdi_snapshots_role_skill_snapshot_version_unique").on(
      table.roleId,
      table.skillId,
      table.snapshotDate,
      table.requirementVersion,
    ),
    index("sdi_snapshots_role_snapshot_date_idx").on(table.roleId, table.snapshotDate),
    index("sdi_snapshots_skill_snapshot_date_idx").on(table.skillId, table.snapshotDate),
    foreignKey({
      columns: [table.requirementVersion],
      foreignColumns: [roleRequirementVersions.version],
      name: "sdi_snapshots_requirement_version_fkey",
    }),
    check("sdi_snapshots_demand_index_range_chk", sql`${table.demandIndex} >= 0 and ${table.demandIndex} <= 1`),
  ],
);

export type SdiSnapshot = InferSelectModel<typeof sdiSnapshots>;
export type NewSdiSnapshot = InferInsertModel<typeof sdiSnapshots>;
