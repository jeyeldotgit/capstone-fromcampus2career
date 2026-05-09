import { readFileSync } from "node:fs";
import postgres from "postgres";
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { runCoursesSeed } from "../run-courses.ts";
import { runTaxonomySeed } from "../run-taxonomy.ts";

const DATABASE_URL = process.env.DATABASE_URL;

const TAXONOMY_MIGRATION_SQL = readFileSync(
  new URL("../../../migrations/20260503143000_p1_s01_taxonomy_schema.sql", import.meta.url),
  "utf8",
);

const TAXONOMY_PATCH_MIGRATION_SQL = readFileSync(
  new URL("../../../migrations/20260505120000_p1_s01b_taxonomy_schema_patch.sql", import.meta.url),
  "utf8",
);

const suite = DATABASE_URL ? describe : describe.skip;

suite("courses seed integration", () => {
  const sql = postgres(DATABASE_URL as string, { max: 1 });

  async function tableExists(tableName: string): Promise<boolean> {
    const rows = await sql<{ exists: boolean }[]>`
      select exists (
        select 1
        from information_schema.tables
        where table_schema = 'public'
          and table_name = ${tableName}
      ) as exists;
    `;

    return rows[0]?.exists ?? false;
  }

  async function fetchCount(tableName: string): Promise<number> {
    const rows = await sql<{ count: string }[]>`select count(*)::text as count from ${sql(tableName)}`;
    return Number(rows[0]?.count ?? "0");
  }

  beforeAll(async () => {
    if (!(await tableExists("skills")) || !(await tableExists("courses"))) {
      await sql.unsafe(TAXONOMY_MIGRATION_SQL);
    }

    await sql.unsafe(TAXONOMY_PATCH_MIGRATION_SQL);

    await sql.unsafe(`
      delete from course_skills;
      delete from courses;
      delete from career_role_aliases;
      delete from skill_aliases;
      delete from career_roles;
      delete from skills;
    `);

    await runTaxonomySeed();
  });

  afterAll(async () => {
    await sql.end({ timeout: 5 });
  });

  test("seeds the expected course and course_skill row counts on first run", async () => {
    await runCoursesSeed();

    await expect(fetchCount("courses")).resolves.toBe(35);
    await expect(fetchCount("course_skills")).resolves.toBe(155);
  });

  test("keeps course and course_skill row counts unchanged on a second run", async () => {
    await runCoursesSeed();

    await expect(fetchCount("courses")).resolves.toBe(35);
    await expect(fetchCount("course_skills")).resolves.toBe(155);
  });

  test("maps IT203 to SQL and Database Design at full depth", async () => {
    const rows = await sql<{ skill_code: string; depth_weight: string }[]>`
      select s.code as skill_code, cs.depth_weight::text as depth_weight
      from course_skills cs
      join courses c on c.id = cs.course_id
      join skills s on s.id = cs.skill_id
      where c.code = 'IT203'
        and s.code in ('SK016', 'SK047')
      order by s.code;
    `;

    expect(rows).toEqual([
      { skill_code: "SK016", depth_weight: "1.00" },
      { skill_code: "SK047", depth_weight: "1.00" },
    ]);
  });

  test("maps CS302 to Machine Learning at full depth", async () => {
    const rows = await sql<{ depth_weight: string }[]>`
      select cs.depth_weight::text as depth_weight
      from course_skills cs
      join courses c on c.id = cs.course_id
      join skills s on s.id = cs.skill_id
      where c.code = 'CS302'
        and s.code = 'SK052';
    `;

    expect(rows[0]?.depth_weight).toBe("1.00");
  });

  test("keeps GE101 without course_skills rows", async () => {
    const rows = await sql<{ count: string }[]>`
      select count(*)::text as count
      from course_skills cs
      join courses c on c.id = cs.course_id
      where c.code = 'GE101';
    `;

    expect(Number(rows[0]?.count ?? "0")).toBe(0);
  });
});
