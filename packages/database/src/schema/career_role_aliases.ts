import { sql } from "drizzle-orm";
import {
  check,
  index,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";
import { careerRoles } from "./career_roles";

export const careerRoleAliases = pgTable(
  "career_role_aliases",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    code: text("code").notNull(),
    roleId: uuid("role_id")
      .notNull()
      .references(() => careerRoles.id),
    alias: text("alias").notNull(),
    normalizedAlias: text("normalized_alias").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("career_role_aliases_code_unique").on(table.code),
    uniqueIndex("career_role_aliases_alias_unique").on(table.alias),
    uniqueIndex("career_role_aliases_normalized_alias_unique").on(table.normalizedAlias),
    index("career_role_aliases_role_id_idx").on(table.roleId),
    check("career_role_aliases_alias_non_empty_chk", sql`char_length(btrim(${table.alias})) > 0`),
    check(
      "career_role_aliases_normalized_alias_non_empty_chk",
      sql`char_length(btrim(${table.normalizedAlias})) > 0`,
    ),
    check(
      "career_role_aliases_normalized_alias_consistency_chk",
      sql`${table.normalizedAlias} = lower(regexp_replace(btrim(${table.alias}), '[[:space:]]+', ' ', 'g'))`,
    ),
  ],
);

