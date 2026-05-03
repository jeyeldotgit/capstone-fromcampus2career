import { sql } from "drizzle-orm";
import { boolean, check, integer, pgTable, text, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";

export const courses = pgTable(
  "courses",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    code: text("code").notNull(),
    title: text("title").notNull(),
    units: integer("units"),
    description: text("description"),
    isActive: boolean("is_active").notNull().default(true),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("courses_code_unique").on(table.code),
    check("courses_code_non_empty_chk", sql`char_length(btrim(${table.code})) > 0`),
    check("courses_title_non_empty_chk", sql`char_length(btrim(${table.title})) > 0`),
    check("courses_units_non_negative_chk", sql`${table.units} is null or ${table.units} >= 0`),
  ],
);

