import { sql } from "drizzle-orm";
import {
  boolean,
  check,
  index,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import { skills } from "./skills";

export const skillAliases = pgTable(
  "skill_aliases",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    code: text("code").notNull(),
    skillId: uuid("skill_id").references(() => skills.id),
    alias: text("alias").notNull(),
    normalizedAlias: text("normalized_alias").notNull(),
    source: text("source"),
    notes: text("notes"),
    reviewed: boolean("reviewed").notNull().default(false),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("skill_aliases_code_unique").on(table.code),
    uniqueIndex("skill_aliases_alias_unique").on(table.alias),
    uniqueIndex("skill_aliases_normalized_alias_unique").on(table.normalizedAlias),
    index("skill_aliases_skill_id_idx").on(table.skillId),
    check("skill_aliases_alias_non_empty_chk", sql`char_length(btrim(${table.alias})) > 0`),
    check(
      "skill_aliases_normalized_alias_non_empty_chk",
      sql`char_length(btrim(${table.normalizedAlias})) > 0`,
    ),
    check(
      "skill_aliases_normalized_alias_consistency_chk",
      sql`${table.normalizedAlias} = lower(regexp_replace(btrim(${table.alias}), '[[:space:]]+', ' ', 'g'))`,
    ),
  ],
);

