import { sql, type InferInsertModel, type InferSelectModel } from "drizzle-orm";
import { check, integer, pgTable, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { marketDatasets } from "./market_datasets";

export const roleRequirementVersions = pgTable(
  "role_requirement_versions",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    version: integer("version").notNull(),
    datasetId: uuid("dataset_id")
      .notNull()
      .references(() => marketDatasets.id),
    computedAt: timestamp("computed_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("role_requirement_versions_version_unique").on(table.version),
    check("role_requirement_versions_version_positive_chk", sql`${table.version} > 0`),
  ],
);

export type RoleRequirementVersion = InferSelectModel<typeof roleRequirementVersions>;
export type NewRoleRequirementVersion = InferInsertModel<typeof roleRequirementVersions>;
