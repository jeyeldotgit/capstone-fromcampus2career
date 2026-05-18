import { sql } from "drizzle-orm";
import { check, date, index, pgTable, text, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { careerRoles } from "./career_roles";
import { marketDatasets } from "./market_datasets";

export const jobPostings = pgTable(
  "job_postings",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    datasetId: uuid("dataset_id")
      .notNull()
      .references(() => marketDatasets.id),
    source: text("source").notNull(),
    title: text("title").notNull(),
    company: text("company").notNull(),
    rawText: text("raw_text").notNull(),
    roleId: uuid("role_id")
      .notNull()
      .references(() => careerRoles.id),
    postedAt: date("posted_at", { mode: "string" }).notNull(),
    ingestedAt: timestamp("ingested_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("job_postings_source_title_company_posted_at_unique").on(
      table.source,
      table.title,
      table.company,
      table.postedAt,
    ),
    index("job_postings_dataset_role_posted_at_idx").on(table.datasetId, table.roleId, table.postedAt),
    index("job_postings_role_posted_at_idx").on(table.roleId, table.postedAt),
    check("job_postings_source_non_empty_chk", sql`char_length(btrim(${table.source})) > 0`),
    check("job_postings_title_non_empty_chk", sql`char_length(btrim(${table.title})) > 0`),
    check("job_postings_company_non_empty_chk", sql`char_length(btrim(${table.company})) > 0`),
    check("job_postings_raw_text_non_empty_chk", sql`char_length(btrim(${table.rawText})) > 0`),
  ],
);
