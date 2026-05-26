import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { beforeAll, describe, expect, test } from "vitest";

const DATABASE_URL = process.env.DATABASE_URL;
const PSQL_PATH = "psql";
const DOCKER_PATH = "docker";
const DOCKER_DATABASE_URL = DATABASE_URL
  ? DATABASE_URL.replace("@127.0.0.1:", "@host.docker.internal:").replace(
      "@localhost:",
      "@host.docker.internal:",
    )
  : undefined;

const PSQL_AVAILABLE = (() => {
  try {
    return spawnSync(PSQL_PATH, ["--version"], { encoding: "utf8" }).status === 0;
  } catch {
    return false;
  }
})();

const DOCKER_AVAILABLE = (() => {
  try {
    return spawnSync(DOCKER_PATH, ["--version"], { encoding: "utf8" }).status === 0;
  } catch {
    return false;
  }
})();

const USE_DOCKER_PSQL = !PSQL_AVAILABLE && DOCKER_AVAILABLE;
const CAN_RUN = Boolean(DATABASE_URL) && (PSQL_AVAILABLE || USE_DOCKER_PSQL);

const MIGRATIONS = [
  "20260503143000_p1_s01_taxonomy_schema.sql",
  "20260505120000_p1_s01b_taxonomy_schema_patch.sql",
  "20260504110000_p1_s03_prepared_intelligence.sql",
  "20260518120000_align_role_requirement_publish_contract.sql",
  "20260523120000_monthly_versioning_and_lineage.sql",
  "20260526120000_admin_readiness_contract_patch.sql",
] as const;

function migrationSql(name: string): string {
  return readFileSync(new URL(`../../migrations/${name}`, import.meta.url), "utf8");
}

function runSql(sqlText: string): string {
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run admin readiness schema tests");
  if (USE_DOCKER_PSQL) {
    assert.ok(DOCKER_DATABASE_URL, "DATABASE_URL must be provided to run admin readiness schema tests");
    return execFileSync(
      DOCKER_PATH,
      [
        "run",
        "--rm",
        "postgres:16-alpine",
        "psql",
        DOCKER_DATABASE_URL,
        "--set",
        "ON_ERROR_STOP=1",
        "--tuples-only",
        "--no-align",
        "--quiet",
        "--command",
        sqlText,
      ],
      { encoding: "utf8" },
    ).trim();
  }

  return execFileSync(
    PSQL_PATH,
    [DATABASE_URL, "--set", "ON_ERROR_STOP=1", "--tuples-only", "--no-align", "--quiet", "--command", sqlText],
    { encoding: "utf8" },
  ).trim();
}

function runSqlExpectFailure(sqlText: string): { status: number | null; stderr: string; stdout: string } {
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run admin readiness schema tests");
  const result = USE_DOCKER_PSQL
    ? spawnSync(
        DOCKER_PATH,
        [
          "run",
          "--rm",
          "postgres:16-alpine",
          "psql",
          DOCKER_DATABASE_URL as string,
          "--set",
          "ON_ERROR_STOP=1",
          "--tuples-only",
          "--no-align",
          "--quiet",
          "--command",
          sqlText,
        ],
        { encoding: "utf8" },
      )
    : spawnSync(
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

function tableExists(tableName: string): boolean {
  return runSql(`
    select exists (
      select 1 from information_schema.tables
      where table_schema = 'public'
        and table_name = '${tableName}'
    );
  `) === "t";
}

function columnExists(tableName: string, columnName: string): boolean {
  return runSql(`
    select exists (
      select 1 from information_schema.columns
      where table_schema = 'public'
        and table_name = '${tableName}'
        and column_name = '${columnName}'
    );
  `) === "t";
}

function constraintExists(constraintName: string): boolean {
  return runSql(`
    select exists (
      select 1
      from pg_constraint
      where conname = '${constraintName}'
    );
  `) === "t";
}

function insertRole(): string {
  return runSql(`
    insert into career_roles (code, title)
    values ('ADMIN_READY_ROLE_' || substr(md5(random()::text), 1, 8), 'Admin Ready Role ' || substr(md5(random()::text), 1, 8))
    returning id;
  `);
}

function insertSkill(): string {
  return runSql(`
    insert into skills (code, name)
    values ('ADMIN_READY_SKILL_' || substr(md5(random()::text), 1, 8), 'Admin Ready Skill ' || substr(md5(random()::text), 1, 8))
    returning id;
  `);
}

function insertDataset(): string {
  return runSql(`
    insert into market_datasets (file_path, source, source_url, status)
    values (
      'admin-ready-' || substr(md5(random()::text), 1, 8) || '.csv',
      'admin-readiness-test',
      'https://example.com/dataset.csv',
      'uploaded'
    )
    returning id;
  `);
}

function insertRequirementVersion(): number {
  const datasetId = insertDataset();
  const version = Number(runSql("select coalesce(max(version), 0) + 1 from role_requirement_versions;"));
  runSql(`
    insert into role_requirement_versions (version, dataset_id, period_month, period_revision)
    values (${version}, '${datasetId}'::uuid, date '2026-09-01', ${version});
  `);
  return version;
}

const suite = CAN_RUN ? describe : describe.skip;

suite("P1-S16 admin readiness contract patch", () => {
  beforeAll(() => {
    if (!tableExists("skills")) {
      runSql(migrationSql(MIGRATIONS[0]));
    }
    if (!columnExists("skills", "code")) {
      runSql(migrationSql(MIGRATIONS[1]));
    }
    if (!tableExists("role_requirement_versions")) {
      runSql(migrationSql(MIGRATIONS[2]));
    }
    if (!columnExists("role_requirement_versions", "is_current")) {
      runSql(migrationSql(MIGRATIONS[3]));
    }
    if (!columnExists("role_requirement_versions", "period_month")) {
      runSql(migrationSql(MIGRATIONS[4]));
    }
    if (!columnExists("market_datasets", "source_url")) {
      runSql(migrationSql(MIGRATIONS[5]));
    }
  });

  test("adds admin readiness columns and replaces incompatible constraints", () => {
    expect(columnExists("career_role_aliases", "reviewed")).toBe(true);
    expect(columnExists("market_datasets", "source_url")).toBe(true);
    expect(constraintExists("market_datasets_source_url_non_empty_when_present_chk")).toBe(true);
    expect(constraintExists("skill_decay_signals_decay_rate_range_chk")).toBe(true);
    expect(constraintExists("skill_aliases_reviewed_requires_skill_id_chk")).toBe(false);
  });

  test("accepts dismissed skill aliases as reviewed rows without skill linkage", () => {
    const token = `dismissed_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    const state = runSql(`
      insert into skill_aliases (code, alias, normalized_alias, reviewed)
      values ('ALIAS_' || substr(md5(random()::text), 1, 8), '${token}', '${token}', true)
      returning reviewed::text || '|' || (skill_id is null)::text;
    `);

    expect(state).toBe("true|true");
  });

  test("defaults career role aliases to reviewed", () => {
    const roleId = insertRole();
    const reviewed = runSql(`
      with alias_value as (
        select 'admin readiness role alias ' || substr(md5(random()::text), 1, 8) as value
      )
      insert into career_role_aliases (code, role_id, alias, normalized_alias)
      select
        'ROLE_ALIAS_' || substr(md5(random()::text), 1, 8),
        '${roleId}'::uuid,
        value,
        value
      from alias_value
      returning reviewed::text;
    `);

    expect(reviewed).toBe("true");
  });

  test("validates optional dataset source_url", () => {
    const datasetId = insertDataset();
    const blankSourceUrl = runSqlExpectFailure(`
      insert into market_datasets (file_path, source, source_url, status)
      values (
        'admin-ready-blank-' || substr(md5(random()::text), 1, 8) || '.csv',
        'admin-readiness-test',
        '   ',
        'uploaded'
      );
    `);

    expect(datasetId).toMatch(/[0-9a-f-]{36}/i);
    expect(blankSourceUrl.status).not.toBe(0);
    expect(`${blankSourceUrl.stderr}\n${blankSourceUrl.stdout}`).toMatch(/check constraint/i);
  });

  test("stores decay_rate as signed decline slope", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const positiveSkillId = insertSkill();
    const belowMinimumSkillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    const insertedId = runSql(`
      insert into skill_decay_signals (role_id, skill_id, decay_rate, confidence, requirement_version)
      values ('${roleId}'::uuid, '${skillId}'::uuid, -0.2500, 0.9000, ${requirementVersion})
      returning id;
    `);
    const positiveDecayRate = runSqlExpectFailure(`
      insert into skill_decay_signals (role_id, skill_id, decay_rate, confidence, requirement_version)
      values ('${roleId}'::uuid, '${positiveSkillId}'::uuid, 0.2500, 0.9000, ${requirementVersion});
    `);
    const belowMinimumDecayRate = runSqlExpectFailure(`
      insert into skill_decay_signals (role_id, skill_id, decay_rate, confidence, requirement_version)
      values ('${roleId}'::uuid, '${belowMinimumSkillId}'::uuid, -1.0001, 0.9000, ${requirementVersion});
    `);

    expect(insertedId).toMatch(/[0-9a-f-]{36}/i);
    expect(positiveDecayRate.status).not.toBe(0);
    expect(belowMinimumDecayRate.status).not.toBe(0);
  });
});
