import { sql } from "drizzle-orm";
import { check, index, jsonb, pgTable, text, timestamp, uniqueIndex, uuid, integer } from "drizzle-orm/pg-core";
import { pipelineJobs } from "./pipeline_jobs";

export const pipelineRejectedRows = pgTable(
  "pipeline_rejected_rows",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    pipelineJobId: uuid("pipeline_job_id")
      .notNull()
      .references(() => pipelineJobs.id),
    rowNumber: integer("row_number").notNull(),
    rawPayload: jsonb("raw_payload").notNull(),
    reason: text("reason").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("pipeline_rejected_rows_pipeline_job_id_row_number_unique").on(
      table.pipelineJobId,
      table.rowNumber,
    ),
    index("pipeline_rejected_rows_pipeline_job_id_idx").on(table.pipelineJobId),
    check("pipeline_rejected_rows_row_number_positive_chk", sql`${table.rowNumber} > 0`),
    check(
      "pipeline_rejected_rows_reason_non_empty_chk",
      sql`char_length(btrim(${table.reason})) > 0`,
    ),
  ],
);
