import { sql, type InferInsertModel, type InferSelectModel } from "drizzle-orm";
import {
  boolean,
  check,
  index,
  integer,
  pgTable,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import { careerRoles } from "./career_roles";
import { marketDatasets } from "./market_datasets";
import { pipelineJobs } from "./pipeline_jobs";
import { skills } from "./skills";

export const pipelineSkillEvidenceSummary = pgTable(
  "pipeline_skill_evidence_summary",
  {
    id: uuid("id").primaryKey(),
    datasetId: uuid("dataset_id")
      .notNull()
      .references(() => marketDatasets.id),
    pipelineJobId: uuid("pipeline_job_id")
      .notNull()
      .references(() => pipelineJobs.id),
    roleId: uuid("role_id")
      .notNull()
      .references(() => careerRoles.id),
    skillId: uuid("skill_id")
      .notNull()
      .references(() => skills.id),
    evidenceCount: integer("evidence_count").notNull(),
    thresholdMet: boolean("threshold_met").notNull().default(false),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("pipeline_skill_evidence_summary_job_role_skill_unique").on(
      table.pipelineJobId,
      table.roleId,
      table.skillId,
    ),
    index("pipeline_skill_evidence_summary_role_skill_idx").on(table.roleId, table.skillId),
    index("pipeline_skill_evidence_summary_dataset_id_idx").on(table.datasetId),
    index("pipeline_skill_evidence_summary_pipeline_job_id_idx").on(table.pipelineJobId),
    check(
      "pipeline_skill_evidence_summary_evidence_count_non_negative_chk",
      sql`${table.evidenceCount} >= 0`,
    ),
  ],
);

export type PipelineSkillEvidenceSummary = InferSelectModel<typeof pipelineSkillEvidenceSummary>;
export type NewPipelineSkillEvidenceSummary = InferInsertModel<typeof pipelineSkillEvidenceSummary>;
