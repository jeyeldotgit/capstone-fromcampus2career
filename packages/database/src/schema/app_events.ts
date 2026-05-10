import { sql } from "drizzle-orm";
import { check, index, jsonb, pgTable, text, timestamp, uuid } from "drizzle-orm/pg-core";

export const appEventStatusValues = ["pending", "processing", "processed", "failed"] as const;

export type AppEventStatus = (typeof appEventStatusValues)[number];

export const appEvents = pgTable(
  "app_events",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    eventType: text("event_type").notNull(),
    aggregateType: text("aggregate_type").notNull(),
    aggregateId: uuid("aggregate_id"),
    payload: jsonb("payload").$type<Record<string, unknown>>().notNull(),
    status: text("status").$type<AppEventStatus>().notNull().default("pending"),
    availableAt: timestamp("available_at", { withTimezone: true }).notNull().defaultNow(),
    processedAt: timestamp("processed_at", { withTimezone: true }),
    errorMessage: text("error_message"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index("app_events_status_available_at_idx").on(table.status, table.availableAt),
    index("app_events_aggregate_type_aggregate_id_idx").on(table.aggregateType, table.aggregateId),
    check(
      "app_events_status_valid_chk",
      sql`${table.status} in ('pending', 'processing', 'processed', 'failed')`,
    ),
  ],
);
