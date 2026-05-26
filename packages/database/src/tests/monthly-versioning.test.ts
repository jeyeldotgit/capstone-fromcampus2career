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
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run monthly versioning tests");
  if (USE_DOCKER_PSQL) {
    assert.ok(DOCKER_DATABASE_URL, "DATABASE_URL must be provided to run monthly versioning tests");
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
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run monthly versioning tests");
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

function insertDataset(): string {
  return runSql(`
    insert into market_datasets (file_path, source, status)
    values ('monthly-' || substr(md5(random()::text), 1, 8) || '.csv', 'monthly-versioning-test', 'uploaded')
    returning id;
  `);
}

function insertRole(): string {
  return runSql(`
    insert into career_roles (code, title)
    values ('MONTHLY_ROLE_' || substr(md5(random()::text), 1, 8), 'Monthly Role ' || substr(md5(random()::text), 1, 8))
    returning id;
  `);
}

function insertSkill(): string {
  return runSql(`
    insert into skills (code, name)
    values ('MONTHLY_SKILL_' || substr(md5(random()::text), 1, 8), 'Monthly Skill ' || substr(md5(random()::text), 1, 8))
    returning id;
  `);
}

function nextVersion(): number {
  return Number(runSql("select coalesce(max(version), 0) + 1 from role_requirement_versions;"));
}

function insertVersion(periodMonth: string, revision: number, isCurrent: boolean, datasetId = insertDataset()): number {
  const version = nextVersion();
  runSql(`
    insert into role_requirement_versions (
      version,
      dataset_id,
      period_month,
      period_revision,
      is_current
    )
    values (${version}, '${datasetId}'::uuid, date '${periodMonth}', ${revision}, ${isCurrent});
  `);
  return version;
}

const suite = CAN_RUN ? describe : describe.skip;

suite("P1-S15 monthly intelligence versioning schema", () => {
  beforeAll(() => {
    if (!tableExists("skills")) {
      for (const migration of MIGRATIONS.slice(0, 2)) {
        runSql(migrationSql(migration));
      }
    }
    if (!tableExists("role_requirement_versions")) {
      runSql(migrationSql("20260504110000_p1_s03_prepared_intelligence.sql"));
    }
    if (!columnExists("role_requirement_versions", "is_current")) {
      runSql(migrationSql("20260518120000_align_role_requirement_publish_contract.sql"));
    }
    if (!columnExists("role_requirement_versions", "period_month")) {
      runSql(migrationSql("20260523120000_monthly_versioning_and_lineage.sql"));
    }
    if (!columnExists("market_datasets", "source_url")) {
      runSql(migrationSql("20260526120000_admin_readiness_contract_patch.sql"));
    }
  });

  test("enforces month-start periods, positive revisions, and one current row per month", () => {
    const firstVersion = insertVersion("2026-04-01", 1, true);
    const duplicateCurrent = runSqlExpectFailure(`
      insert into role_requirement_versions (version, dataset_id, period_month, period_revision, is_current)
      values (${nextVersion()}, '${insertDataset()}'::uuid, date '2026-04-01', 2, true);
    `);
    const invalidMonth = runSqlExpectFailure(`
      insert into role_requirement_versions (version, dataset_id, period_month, period_revision)
      values (${nextVersion()}, '${insertDataset()}'::uuid, date '2026-04-15', 1);
    `);
    const invalidRevision = runSqlExpectFailure(`
      insert into role_requirement_versions (version, dataset_id, period_month, period_revision)
      values (${nextVersion()}, '${insertDataset()}'::uuid, date '2026-05-01', 0);
    `);

    expect(firstVersion).toBeGreaterThan(0);
    expect(duplicateCurrent.status).not.toBe(0);
    expect(invalidMonth.status).not.toBe(0);
    expect(invalidRevision.status).not.toBe(0);
  });

  test("allows same-month version coexistence through period_revision", () => {
    const firstVersion = insertVersion("2026-06-01", 1, false);
    const secondVersion = insertVersion("2026-06-01", 2, false);
    const duplicateRevision = runSqlExpectFailure(`
      insert into role_requirement_versions (version, dataset_id, period_month, period_revision)
      values (${nextVersion()}, '${insertDataset()}'::uuid, date '2026-06-01', 2);
    `);

    expect(secondVersion).toBe(firstVersion + 1);
    expect(duplicateRevision.status).not.toBe(0);
  });

  test("captures lineage and allows SDI coexistence across requirement versions", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const datasetId = insertDataset();
    const otherDatasetId = insertDataset();
    const firstVersion = insertVersion("2026-07-01", 1, false, datasetId);
    const secondVersion = insertVersion("2026-07-01", 2, true, datasetId);

    runSql(`
      insert into role_requirement_version_datasets (requirement_version, dataset_id)
      values (${secondVersion}, '${datasetId}'::uuid), (${secondVersion}, '${otherDatasetId}'::uuid);
      insert into sdi_snapshots (role_id, skill_id, demand_index, snapshot_date, requirement_version)
      values
        ('${roleId}'::uuid, '${skillId}'::uuid, 0.6000, date '2026-07-01', ${firstVersion}),
        ('${roleId}'::uuid, '${skillId}'::uuid, 0.7000, date '2026-07-01', ${secondVersion});
    `);

    const lineageCount = Number(runSql(`
      select count(*) from role_requirement_version_datasets
      where requirement_version = ${secondVersion};
    `));
    const sdiCount = Number(runSql(`
      select count(*) from sdi_snapshots
      where role_id = '${roleId}'::uuid
        and skill_id = '${skillId}'::uuid
        and snapshot_date = date '2026-07-01';
    `));

    expect(lineageCount).toBe(2);
    expect(sdiCount).toBe(2);
  });

  test("current monthly views include current rows and exclude non-current versions", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const oldVersion = insertVersion("2026-08-01", 1, false);
    const currentVersion = insertVersion("2026-08-01", 2, true);

    runSql(`
      insert into role_skill_requirements (role_id, skill_id, requirement_version, required_depth, demand_weight, evidence_count)
      values
        ('${roleId}'::uuid, '${skillId}'::uuid, ${oldVersion}, 0.5000, 0.5000, 5),
        ('${roleId}'::uuid, '${skillId}'::uuid, ${currentVersion}, 0.7000, 0.7000, 6);
      insert into sdi_snapshots (role_id, skill_id, demand_index, snapshot_date, requirement_version)
      values
        ('${roleId}'::uuid, '${skillId}'::uuid, 0.4000, date '2026-08-01', ${oldVersion}),
        ('${roleId}'::uuid, '${skillId}'::uuid, 0.8000, date '2026-08-01', ${currentVersion});
      insert into skill_decay_signals (role_id, skill_id, decay_rate, confidence, requirement_version, is_active)
      values
        ('${roleId}'::uuid, '${skillId}'::uuid, -0.1000, 0.8000, ${oldVersion}, false),
        ('${roleId}'::uuid, '${skillId}'::uuid, -0.2000, 0.9000, ${currentVersion}, true);
    `);

    expect(Number(runSql(`select count(*) from v_current_monthly_role_skill_requirements where requirement_version = ${currentVersion};`))).toBe(1);
    expect(Number(runSql(`select count(*) from v_current_monthly_sdi_snapshots where requirement_version = ${currentVersion};`))).toBe(1);
    expect(Number(runSql(`select count(*) from v_current_monthly_skill_decay_signals where requirement_version = ${currentVersion};`))).toBe(1);
    expect(Number(runSql(`select count(*) from v_current_monthly_role_skill_requirements where requirement_version = ${oldVersion};`))).toBe(0);
  });
});
