import { sql } from "drizzle-orm";
import { check, index, integer, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";
import { marketDatasets } from "./market_datasets";

export const pipelineJobs = pgTable(
  "pipeline_jobs",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    datasetId: uuid("dataset_id")
      .notNull()
      .references(() => marketDatasets.id),
    jobType: text("job_type").notNull(),
    status: text("status").notNull().default("pending"),
    processedRows: integer("processed_rows").notNull().default(0),
    rejectedRows: integer("rejected_rows").notNull().default(0),
    outputVersion: integer("output_version"),
    errorMessage: text("error_message"),
    startedAt: timestamp("started_at", { withTimezone: true }).notNull().defaultNow(),
    finishedAt: timestamp("finished_at", { withTimezone: true }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index("pipeline_jobs_dataset_id_created_at_idx").on(table.datasetId, table.createdAt),
    index("pipeline_jobs_status_created_at_idx").on(table.status, table.createdAt),
    index("pipeline_jobs_output_version_idx").on(table.outputVersion),
    check("pipeline_jobs_job_type_non_empty_chk", sql`char_length(btrim(${table.jobType})) > 0`),
    check(
      "pipeline_jobs_status_valid_chk",
      sql`${table.status} in ('pending', 'running', 'complete', 'failed', 'partial')`,
    ),
    check("pipeline_jobs_processed_rows_non_negative_chk", sql`${table.processedRows} >= 0`),
    check("pipeline_jobs_rejected_rows_non_negative_chk", sql`${table.rejectedRows} >= 0`),
    check(
      "pipeline_jobs_output_version_positive_chk",
      sql`${table.outputVersion} is null or ${table.outputVersion} > 0`,
    ),
    check(
      "pipeline_jobs_error_message_non_empty_when_present_chk",
      sql`${table.errorMessage} is null or char_length(btrim(${table.errorMessage})) > 0`,
    ),
    check(
      "pipeline_jobs_finished_at_after_started_at_chk",
      sql`${table.finishedAt} is null or ${table.finishedAt} >= ${table.startedAt}`,
    ),
    check(
      "pipeline_jobs_terminal_state_fields_chk",
      sql`
        (
          ${table.status} in ('pending', 'running')
          and ${table.finishedAt} is null
        )
        or (
          ${table.status} in ('complete', 'partial', 'failed')
          and ${table.finishedAt} is not null
        )
      `,
    ),
    check(
      "pipeline_jobs_output_version_terminal_state_chk",
      sql`${table.outputVersion} is null or ${table.status} in ('complete', 'partial')`,
    ),
  ],
);
