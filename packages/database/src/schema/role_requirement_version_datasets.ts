import { type InferInsertModel, type InferSelectModel } from "drizzle-orm";
import { index, integer, pgTable, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { marketDatasets } from "./market_datasets.js";
import { roleRequirementVersions } from "./role_requirement_versions.js";

export const roleRequirementVersionDatasets = pgTable(
  "role_requirement_version_datasets",
  {
    requirementVersion: integer("requirement_version")
      .notNull()
      .references(() => roleRequirementVersions.version),
    datasetId: uuid("dataset_id")
      .notNull()
      .references(() => marketDatasets.id),
    linkedAt: timestamp("linked_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("role_requirement_version_datasets_version_dataset_unique").on(
      table.requirementVersion,
      table.datasetId,
    ),
    index("role_requirement_version_datasets_dataset_id_idx").on(table.datasetId),
  ],
);

export type RoleRequirementVersionDataset = InferSelectModel<typeof roleRequirementVersionDatasets>;
export type NewRoleRequirementVersionDataset = InferInsertModel<typeof roleRequirementVersionDatasets>;
