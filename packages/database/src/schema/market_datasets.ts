import { sql } from "drizzle-orm";
import { check, index, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";

export const marketDatasets = pgTable(
  "market_datasets",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    filePath: text("file_path").notNull(),
    source: text("source"),
    status: text("status").notNull(),
    uploadedBy: uuid("uploaded_by"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index("market_datasets_status_created_at_idx").on(table.status, table.createdAt),
    check("market_datasets_file_path_non_empty_chk", sql`char_length(btrim(${table.filePath})) > 0`),
    check("market_datasets_status_non_empty_chk", sql`char_length(btrim(${table.status})) > 0`),
    check(
      "market_datasets_source_non_empty_when_present_chk",
      sql`${table.source} is null or char_length(btrim(${table.source})) > 0`,
    ),
  ],
);

