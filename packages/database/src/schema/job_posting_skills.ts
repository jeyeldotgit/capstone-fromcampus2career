import { sql } from "drizzle-orm";
import { check, index, numeric, pgTable, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { careerRoles } from "./career_roles";
import { jobPostings } from "./job_postings";
import { skills } from "./skills";

export const jobPostingSkills = pgTable(
  "job_posting_skills",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    jobPostingId: uuid("job_posting_id")
      .notNull()
      .references(() => jobPostings.id),
    roleId: uuid("role_id")
      .notNull()
      .references(() => careerRoles.id),
    skillId: uuid("skill_id")
      .notNull()
      .references(() => skills.id),
    normalizedDepth: numeric("normalized_depth", { precision: 5, scale: 4 }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("job_posting_skills_posting_role_skill_unique").on(
      table.jobPostingId,
      table.roleId,
      table.skillId,
    ),
    index("job_posting_skills_role_skill_idx").on(table.roleId, table.skillId),
    index("job_posting_skills_skill_id_idx").on(table.skillId),
    check(
      "job_posting_skills_normalized_depth_range_chk",
      sql`${table.normalizedDepth} is null or (${table.normalizedDepth} >= 0 and ${table.normalizedDepth} <= 1)`,
    ),
  ],
);
