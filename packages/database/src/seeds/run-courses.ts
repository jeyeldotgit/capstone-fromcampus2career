import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { pathToFileURL } from "node:url";
import { courseSkills as courseSkillsTable } from "../schema/course_skills.ts";
import { courses as coursesTable } from "../schema/courses.ts";
import { COURSE_SKILLS } from "./courses/course-skills.seed.ts";
import { COURSES } from "./courses/courses.seed.ts";
import { SKILL_IDS } from "./taxonomy/id-maps.ts";

const EXPECTED_COURSE_COUNT = 35;
const EXPECTED_COURSE_SKILL_COUNT = 155;
const ALLOWED_DEPTH_WEIGHTS = new Set(["0.25", "0.50", "0.75", "1.00"]);
const INACTIVE_SKILL_CODES = ["SK010", "SK012", "SK014", "SK036", "SK092", "SK099"] as const;

function collectDuplicateValues(values: string[]): string[] {
  const counts = new Map<string, number>();

  for (const value of values) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }

  return [...counts.entries()]
    .filter(([, count]) => count > 1)
    .map(([value]) => value)
    .sort((left, right) => left.localeCompare(right));
}

function assertNoDuplicateValues(values: string[], label: string): void {
  const duplicates = collectDuplicateValues(values);

  if (duplicates.length > 0) {
    throw new Error(`${label} contains duplicate values: ${duplicates.join(", ")}`);
  }
}

function assertIdsExist(
  childIds: string[],
  validIds: ReadonlySet<string>,
  label: string,
): void {
  const missingIds = [...new Set(childIds.filter((childId) => !validIds.has(childId)))];

  if (missingIds.length > 0) {
    throw new Error(`${label} references unknown IDs: ${missingIds.join(", ")}`);
  }
}

export function validateCoursesSeedData(): void {
  if (COURSES.length !== EXPECTED_COURSE_COUNT) {
    throw new Error(
      `courses seed count mismatch: expected ${EXPECTED_COURSE_COUNT}, received ${COURSES.length}`,
    );
  }

  if (COURSE_SKILLS.length !== EXPECTED_COURSE_SKILL_COUNT) {
    throw new Error(
      `course_skills seed count mismatch: expected ${EXPECTED_COURSE_SKILL_COUNT}, received ${COURSE_SKILLS.length}`,
    );
  }

  assertNoDuplicateValues(
    COURSES.map((course) => course.code),
    "courses.code",
  );
  assertNoDuplicateValues(
    COURSE_SKILLS.map((courseSkill) => `${courseSkill.course_id}:${courseSkill.skill_id}`),
    "course_skills.course_id:skill_id",
  );
  assertNoDuplicateValues(
    COURSE_SKILLS.map((courseSkill) => courseSkill.id),
    "course_skills.id",
  );

  assertIdsExist(
    COURSE_SKILLS.map((courseSkill) => courseSkill.course_id),
    new Set(COURSES.map((course) => course.id)),
    "course_skills.course_id",
  );
  assertIdsExist(
    COURSE_SKILLS.map((courseSkill) => courseSkill.skill_id),
    new Set(Object.values(SKILL_IDS)),
    "course_skills.skill_id",
  );

  const invalidWeights = [
    ...new Set(
      COURSE_SKILLS.filter(
        (courseSkill) => !ALLOWED_DEPTH_WEIGHTS.has(courseSkill.depth_weight),
      ).map((courseSkill) => courseSkill.depth_weight),
    ),
  ];

  if (invalidWeights.length > 0) {
    throw new Error(`course_skills.depth_weight contains invalid values: ${invalidWeights.join(", ")}`);
  }

  const inactiveSkillIds = new Set(INACTIVE_SKILL_CODES.map((code) => SKILL_IDS[code]));
  const referencedInactiveSkillIds = [
    ...new Set(
      COURSE_SKILLS.filter((courseSkill) => inactiveSkillIds.has(courseSkill.skill_id)).map(
        (courseSkill) => courseSkill.skill_id,
      ),
    ),
  ];

  if (referencedInactiveSkillIds.length > 0) {
    throw new Error(
      `course_skills.skill_id references inactive skills: ${referencedInactiveSkillIds.join(", ")}`,
    );
  }
}

export async function runCoursesSeed(): Promise<void> {
  validateCoursesSeedData();

  const databaseUrl = process.env.DATABASE_URL;

  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required to run the courses seed");
  }

  const sql = postgres(databaseUrl, { max: 1 });
  const db = drizzle(sql);

  try {
    const insertedCourses = await db
      .insert(coursesTable)
      .values(
        COURSES.map((course) => ({
          id: course.id,
          code: course.code,
          title: course.title,
          units: course.units,
          description: course.description,
          isActive: course.is_active,
        })),
      )
      .onConflictDoNothing({ target: coursesTable.code })
      .returning({ id: coursesTable.id });
    console.info(`Seeded courses: ${insertedCourses.length} rows inserted`);

    const insertedCourseSkills = await db
      .insert(courseSkillsTable)
      .values(
        COURSE_SKILLS.map((courseSkill) => ({
          id: courseSkill.id,
          courseId: courseSkill.course_id,
          skillId: courseSkill.skill_id,
          depthWeight: courseSkill.depth_weight,
        })),
      )
      .onConflictDoNothing({
        target: [courseSkillsTable.courseId, courseSkillsTable.skillId],
      })
      .returning({ id: courseSkillsTable.id });
    console.info(`Seeded course_skills: ${insertedCourseSkills.length} rows inserted`);
  } finally {
    await sql.end({ timeout: 5 });
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runCoursesSeed().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
