import { sql, type InferInsertModel, type InferSelectModel } from "drizzle-orm";
import { boolean, check, date, integer, pgTable, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { marketDatasets } from "./market_datasets.js";

export const roleRequirementVersions = pgTable(
  "role_requirement_versions",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    version: integer("version").notNull(),
    datasetId: uuid("dataset_id")
      .notNull()
      .references(() => marketDatasets.id),
    periodMonth: date("period_month", { mode: "string" }).notNull(),
    periodRevision: integer("period_revision").notNull(),
    computedAt: timestamp("computed_at", { withTimezone: true }).notNull().defaultNow(),
    isCurrent: boolean("is_current").notNull().default(false),
  },
  (table) => [
    uniqueIndex("role_requirement_versions_version_unique").on(table.version),
    uniqueIndex("role_requirement_versions_period_month_revision_unique").on(
      table.periodMonth,
      table.periodRevision,
    ),
    uniqueIndex("role_requirement_versions_current_period_month_unique")
      .on(table.periodMonth)
      .where(sql`${table.isCurrent} = true`),
    check("role_requirement_versions_version_positive_chk", sql`${table.version} > 0`),
    check("role_requirement_versions_period_revision_positive_chk", sql`${table.periodRevision} > 0`),
    check(
      "role_requirement_versions_period_month_start_chk",
      sql`date_trunc('month', ${table.periodMonth}::timestamp)::date = ${table.periodMonth}`,
    ),
  ],
);

export type RoleRequirementVersion = InferSelectModel<typeof roleRequirementVersions>;
export type NewRoleRequirementVersion = InferInsertModel<typeof roleRequirementVersions>;
