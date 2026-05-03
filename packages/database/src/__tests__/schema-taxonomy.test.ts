import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { before, describe, test } from "node:test";

const DATABASE_URL = process.env.DATABASE_URL;
const PSQL_PATH = "psql";
const PSQL_AVAILABLE = spawnSync(PSQL_PATH, ["--version"], { encoding: "utf8" }).status === 0;
const CAN_RUN = Boolean(DATABASE_URL) && PSQL_AVAILABLE;

const REQUIRED_TABLES = [
  "skills",
  "skill_aliases",
  "career_roles",
  "career_role_aliases",
  "courses",
  "course_skills",
  "market_datasets",
] as const;

const OUT_OF_SCOPE_TABLES = [
  "pipeline_jobs",
  "pipeline_rejected_rows",
  "role_requirement_versions",
  "role_skill_requirements",
  "sdi_snapshots",
  "skill_decay_signals",
] as const;

const REQUIRED_CONSTRAINTS = [
  "skills_name_unique",
  "skills_name_non_empty_chk",
  "career_roles_title_unique",
  "career_roles_title_non_empty_chk",
  "courses_code_unique",
  "courses_code_non_empty_chk",
  "courses_title_non_empty_chk",
  "courses_units_non_negative_chk",
  "market_datasets_file_path_non_empty_chk",
  "market_datasets_status_non_empty_chk",
  "market_datasets_source_non_empty_when_present_chk",
  "skill_aliases_skill_id_fkey",
  "skill_aliases_alias_unique",
  "skill_aliases_normalized_alias_unique",
  "skill_aliases_alias_non_empty_chk",
  "skill_aliases_normalized_alias_non_empty_chk",
  "skill_aliases_normalized_alias_consistency_chk",
  "skill_aliases_reviewed_requires_skill_id_chk",
  "career_role_aliases_role_id_fkey",
  "career_role_aliases_alias_unique",
  "career_role_aliases_normalized_alias_unique",
  "career_role_aliases_alias_non_empty_chk",
  "career_role_aliases_normalized_alias_non_empty_chk",
  "career_role_aliases_normalized_alias_consistency_chk",
  "course_skills_course_id_fkey",
  "course_skills_skill_id_fkey",
  "course_skills_course_id_skill_id_unique",
  "course_skills_depth_weight_range_chk",
] as const;

const REQUIRED_INDEXES = [
  "skill_aliases_skill_id_idx",
  "career_role_aliases_role_id_idx",
  "course_skills_skill_id_idx",
  "course_skills_course_id_idx",
  "market_datasets_status_created_at_idx",
] as const;

const MIGRATION_SQL = readFileSync(
  new URL("../../migrations/20260503143000_p1_s01_taxonomy_schema.sql", import.meta.url),
  "utf8",
);

function runSql(sqlText: string): string {
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run taxonomy schema tests");
  return execFileSync(
    PSQL_PATH,
    [DATABASE_URL, "--set", "ON_ERROR_STOP=1", "--tuples-only", "--no-align", "--quiet", "--command", sqlText],
    { encoding: "utf8" },
  ).trim();
}

function runSqlExpectFailure(sqlText: string): { status: number | null; stderr: string; stdout: string } {
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run taxonomy schema tests");
  const result = spawnSync(
    PSQL_PATH,
    [DATABASE_URL, "--set", "ON_ERROR_STOP=1", "--tuples-only", "--no-align", "--quiet", "--command", sqlText],
    { encoding: "utf8" },
  );

  return {
    status: result.status,
    stderr: result.stderr ?? "",
    stdout: result.stdout ?? "",
  };
}

describe(
  "P1-S01 taxonomy schema migration",
  { skip: CAN_RUN ? false : "requires DATABASE_URL and psql installed" },
  () => {
    before(() => {
      runSql(MIGRATION_SQL);
    });

    test("creates all 7 taxonomy tables", () => {
      const tableList = REQUIRED_TABLES.map((table) => `'${table}'`).join(", ");
      const count = Number(
        runSql(`
          select count(*)
          from information_schema.tables
          where table_schema = 'public'
            and table_name in (${tableList});
        `),
      );

      assert.equal(count, REQUIRED_TABLES.length);
    });

    test("creates required PK/FK/unique/check constraints", () => {
      const constraintList = REQUIRED_CONSTRAINTS.map((name) => `'${name}'`).join(", ");
      const count = Number(
        runSql(`
          select count(*)
          from pg_constraint
          where conname in (${constraintList});
        `),
      );

      assert.equal(count, REQUIRED_CONSTRAINTS.length);

      const pkCount = Number(
        runSql(`
          select count(*)
          from pg_constraint
          where contype = 'p'
            and conrelid in (
              select oid from pg_class where relname in (${REQUIRED_TABLES.map((table) => `'${table}'`).join(", ")})
            );
        `),
      );

      assert.equal(pkCount, REQUIRED_TABLES.length);
    });

    test("creates required explicit join indexes", () => {
      const indexList = REQUIRED_INDEXES.map((name) => `'${name}'`).join(", ");
      const count = Number(
        runSql(`
          select count(*)
          from pg_indexes
          where schemaname = 'public'
            and indexname in (${indexList});
        `),
      );

      assert.equal(count, REQUIRED_INDEXES.length);
    });

    test("rejects invalid course_skills.skill_id foreign key reference", () => {
      runSql(`
        with new_skill as (
          insert into skills (name)
          values ('skill_' || substr(md5(random()::text), 1, 8))
          returning id
        ),
        new_course as (
          insert into courses (code, title)
          values (
            'code_' || substr(md5(random()::text), 1, 8),
            'course_' || substr(md5(random()::text), 1, 8)
          )
          returning id
        )
        insert into course_skills (course_id, skill_id, depth_weight)
        select new_course.id, new_skill.id, 0.75
        from new_course, new_skill;
      `);

      const failingInsert = runSqlExpectFailure(`
        with new_course as (
          insert into courses (code, title)
          values (
            'badfk_' || substr(md5(random()::text), 1, 8),
            'course_' || substr(md5(random()::text), 1, 8)
          )
          returning id
        )
        insert into course_skills (course_id, skill_id, depth_weight)
        select new_course.id, '00000000-0000-0000-0000-000000000000'::uuid, 0.65
        from new_course;
      `);

      assert.notEqual(failingInsert.status, 0);
      assert.match(`${failingInsert.stderr}\n${failingInsert.stdout}`, /foreign key constraint/i);
    });

    test("does not create out-of-scope pipeline/prepared-output tables", () => {
      const tableList = OUT_OF_SCOPE_TABLES.map((table) => `'${table}'`).join(", ");
      const count = Number(
        runSql(`
          select count(*)
          from information_schema.tables
          where table_schema = 'public'
            and table_name in (${tableList});
        `),
      );

      assert.equal(count, 0);
    });
  },
);

