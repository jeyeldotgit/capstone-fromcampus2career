import { sql } from "drizzle-orm";
import { boolean, check, pgTable, text, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";

export const careerRoles = pgTable(
  "career_roles",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    code: text("code").notNull(),
    title: text("title").notNull(),
    description: text("description"),
    category: text("category"),
    isActive: boolean("is_active").notNull().default(true),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("career_roles_code_unique").on(table.code),
    uniqueIndex("career_roles_title_unique").on(table.title),
    check("career_roles_title_non_empty_chk", sql`char_length(btrim(${table.title})) > 0`),
  ],
);

