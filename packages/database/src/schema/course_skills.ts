import { sql } from "drizzle-orm";
import { check, index, numeric, pgTable, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { courses } from "./courses";
import { skills } from "./skills";

export const courseSkills = pgTable(
  "course_skills",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    courseId: uuid("course_id")
      .notNull()
      .references(() => courses.id),
    skillId: uuid("skill_id")
      .notNull()
      .references(() => skills.id),
    depthWeight: numeric("depth_weight", { precision: 3, scale: 2 }).notNull().default("1.0"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex("course_skills_course_id_skill_id_unique").on(table.courseId, table.skillId),
    index("course_skills_course_id_idx").on(table.courseId),
    index("course_skills_skill_id_idx").on(table.skillId),
    check(
      "course_skills_depth_weight_range_chk",
      sql`${table.depthWeight} > 0 and ${table.depthWeight} <= 1`,
    ),
  ],
);

