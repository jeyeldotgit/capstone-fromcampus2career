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

const REQUIRED_TABLES = [
  "role_requirement_versions",
  "role_skill_requirements",
  "sdi_snapshots",
  "skill_decay_signals",
] as const;

const REQUIRED_CONSTRAINTS = [
  "role_requirement_versions_dataset_id_fkey",
  "role_requirement_versions_version_unique",
  "role_requirement_versions_version_positive_chk",
  "role_skill_requirements_role_id_fkey",
  "role_skill_requirements_skill_id_fkey",
  "role_skill_requirements_role_skill_version_unique",
  "role_skill_requirements_required_depth_range_chk",
  "role_skill_requirements_demand_weight_range_chk",
  "role_skill_requirements_evidence_count_min_chk",
  "sdi_snapshots_role_id_fkey",
  "sdi_snapshots_skill_id_fkey",
  "sdi_snapshots_role_skill_snapshot_date_unique",
  "sdi_snapshots_demand_index_range_chk",
  "skill_decay_signals_role_id_fkey",
  "skill_decay_signals_skill_id_fkey",
  "skill_decay_signals_role_skill_version_unique",
  "skill_decay_signals_decay_rate_range_chk",
  "skill_decay_signals_confidence_range_chk",
] as const;

const REQUIRED_INDEXES = [
  "role_skill_requirements_role_version_idx",
  "role_skill_requirements_skill_version_idx",
  "sdi_snapshots_role_snapshot_date_idx",
  "sdi_snapshots_skill_snapshot_date_idx",
  "skill_decay_signals_role_version_idx",
  "skill_decay_signals_skill_version_idx",
  "skill_decay_signals_role_skill_active_idx",
] as const;

const TAXONOMY_MIGRATION_SQL = readFileSync(
  new URL("../../migrations/20260503143000_p1_s01_taxonomy_schema.sql", import.meta.url),
  "utf8",
);

const PREPARED_INTELLIGENCE_MIGRATION_SQL = readFileSync(
  new URL("../../migrations/20260504110000_p1_s03_prepared_intelligence.sql", import.meta.url),
  "utf8",
);

function runSql(sqlText: string): string {
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run prepared intelligence schema tests");
  if (USE_DOCKER_PSQL) {
    assert.ok(
      DOCKER_DATABASE_URL,
      "DATABASE_URL must be provided to run prepared intelligence schema tests",
    );
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
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run prepared intelligence schema tests");
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
  const exists = runSql(`
    select exists (
      select 1
      from information_schema.tables
      where table_schema = 'public'
        and table_name = '${tableName}'
    );
  `);

  return exists === "t";
}

function insertDataset(): string {
  return runSql(`
    insert into market_datasets (file_path, source, status)
    values (
      'dataset_' || substr(md5(random()::text), 1, 8) || '.csv',
      'prepared-intelligence-test',
      'uploaded'
    )
    returning id;
  `);
}

function insertRole(): string {
  return runSql(`
    insert into career_roles (code, title)
    values (
      'CR_TEST_' || substr(md5(random()::text), 1, 8),
      'role_' || substr(md5(random()::text), 1, 8)
    )
    returning id;
  `);
}

function insertSkill(): string {
  return runSql(`
    insert into skills (code, name)
    values (
      'SK_TEST_' || substr(md5(random()::text), 1, 8),
      'skill_' || substr(md5(random()::text), 1, 8)
    )
    returning id;
  `);
}

function insertRequirementVersion(): string {
  const datasetId = insertDataset();

  return runSql(`
    insert into role_requirement_versions (version, dataset_id)
    values (
      floor(random() * 1000000 + 1)::integer,
      '${datasetId}'::uuid
    )
    returning version::text;
  `);
}

const suite = CAN_RUN ? describe : describe.skip;

suite("P1-S03 prepared intelligence schema migration", () => {
  beforeAll(() => {
    if (!tableExists("skills")) {
      runSql(TAXONOMY_MIGRATION_SQL);
    }

    if (!tableExists("role_requirement_versions")) {
      runSql(PREPARED_INTELLIGENCE_MIGRATION_SQL);
    }
  });

  test("creates prepared intelligence tables, constraints, and indexes", () => {
    const tableList = REQUIRED_TABLES.map((table) => `'${table}'`).join(", ");
    const tableCount = Number(
      runSql(`
        select count(*)
        from information_schema.tables
        where table_schema = 'public'
          and table_name in (${tableList});
      `),
    );
    expect(tableCount).toBe(REQUIRED_TABLES.length);

    const constraintList = REQUIRED_CONSTRAINTS.map((name) => `'${name}'`).join(", ");
    const constraintCount = Number(
      runSql(`
        select count(*)
        from pg_constraint
        where conname in (${constraintList});
      `),
    );
    expect(constraintCount).toBe(REQUIRED_CONSTRAINTS.length);

    const indexList = REQUIRED_INDEXES.map((name) => `'${name}'`).join(", ");
    const indexCount = Number(
      runSql(`
        select count(*)
        from pg_indexes
        where schemaname = 'public'
          and indexname in (${indexList});
      `),
    );
    expect(indexCount).toBe(REQUIRED_INDEXES.length);
  });

  test("accepts a valid role_requirement_versions row", () => {
    const datasetId = insertDataset();
    const insertedVersion = runSql(`
      insert into role_requirement_versions (version, dataset_id)
      values (
        floor(random() * 1000000 + 1)::integer,
        '${datasetId}'::uuid
      )
      returning version::text;
    `);

    expect(Number(insertedVersion)).toBeGreaterThan(0);
  });

  test("rejects a duplicate role_requirement_versions.version", () => {
    const datasetId = insertDataset();
    const version = Number(runSql(`select floor(random() * 1000000 + 1)::integer;`));

    runSql(`
      insert into role_requirement_versions (version, dataset_id)
      values (${version}, '${datasetId}'::uuid);
    `);

    const duplicateInsert = runSqlExpectFailure(`
      insert into role_requirement_versions (version, dataset_id)
      values (${version}, '${insertDataset()}'::uuid);
    `);

    expect(duplicateInsert.status).not.toBe(0);
    expect(`${duplicateInsert.stderr}\n${duplicateInsert.stdout}`).toMatch(/unique constraint/i);
  });

  test("accepts a valid role_skill_requirements row", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    const insertedId = runSql(`
      insert into role_skill_requirements (
        role_id,
        skill_id,
        requirement_version,
        required_depth,
        demand_weight,
        evidence_count
      )
      values (
        '${roleId}'::uuid,
        '${skillId}'::uuid,
        ${requirementVersion},
        0.8,
        0.6,
        5
      )
      returning id;
    `);

    expect(insertedId).toMatch(/[0-9a-f-]{36}/i);
  });

  test("rejects an invalid role_skill_requirements.role_id foreign key", () => {
    const skillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    const failingInsert = runSqlExpectFailure(`
      insert into role_skill_requirements (
        role_id,
        skill_id,
        requirement_version,
        required_depth,
        demand_weight,
        evidence_count
      )
      values (
        '00000000-0000-0000-0000-000000000000'::uuid,
        '${skillId}'::uuid,
        ${requirementVersion},
        0.6,
        0.5,
        5
      );
    `);

    expect(failingInsert.status).not.toBe(0);
    expect(`${failingInsert.stderr}\n${failingInsert.stdout}`).toMatch(/foreign key constraint/i);
  });

  test("rejects an invalid role_skill_requirements.skill_id foreign key", () => {
    const roleId = insertRole();
    const requirementVersion = insertRequirementVersion();

    const failingInsert = runSqlExpectFailure(`
      insert into role_skill_requirements (
        role_id,
        skill_id,
        requirement_version,
        required_depth,
        demand_weight,
        evidence_count
      )
      values (
        '${roleId}'::uuid,
        '00000000-0000-0000-0000-000000000000'::uuid,
        ${requirementVersion},
        0.6,
        0.5,
        5
      );
    `);

    expect(failingInsert.status).not.toBe(0);
    expect(`${failingInsert.stderr}\n${failingInsert.stdout}`).toMatch(/foreign key constraint/i);
  });

  test("rejects a duplicate role_skill_requirements role-skill-version tuple", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    runSql(`
      insert into role_skill_requirements (
        role_id,
        skill_id,
        requirement_version,
        required_depth,
        demand_weight,
        evidence_count
      )
      values (
        '${roleId}'::uuid,
        '${skillId}'::uuid,
        ${requirementVersion},
        0.7,
        0.8,
        5
      );
    `);

    const duplicateInsert = runSqlExpectFailure(`
      insert into role_skill_requirements (
        role_id,
        skill_id,
        requirement_version,
        required_depth,
        demand_weight,
        evidence_count
      )
      values (
        '${roleId}'::uuid,
        '${skillId}'::uuid,
        ${requirementVersion},
        0.9,
        0.9,
        6
      );
    `);

    expect(duplicateInsert.status).not.toBe(0);
    expect(`${duplicateInsert.stderr}\n${duplicateInsert.stdout}`).toMatch(/unique constraint/i);
  });

  test("rejects out-of-range required_depth, demand_weight, and evidence_count values", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    const belowMinimumDepth = runSqlExpectFailure(`
      insert into role_skill_requirements (role_id, skill_id, requirement_version, required_depth, demand_weight, evidence_count)
      values ('${roleId}'::uuid, '${skillId}'::uuid, ${requirementVersion}, -0.0001, 0.5, 5);
    `);
    expect(belowMinimumDepth.status).not.toBe(0);
    expect(`${belowMinimumDepth.stderr}\n${belowMinimumDepth.stdout}`).toMatch(/check constraint/i);

    const aboveMaximumDepth = runSqlExpectFailure(`
      insert into role_skill_requirements (role_id, skill_id, requirement_version, required_depth, demand_weight, evidence_count)
      values ('${roleId}'::uuid, '${skillId}'::uuid, ${requirementVersion}, 1.0001, 0.5, 5);
    `);
    expect(aboveMaximumDepth.status).not.toBe(0);
    expect(`${aboveMaximumDepth.stderr}\n${aboveMaximumDepth.stdout}`).toMatch(/check constraint/i);

    const belowMinimumWeight = runSqlExpectFailure(`
      insert into role_skill_requirements (role_id, skill_id, requirement_version, required_depth, demand_weight, evidence_count)
      values ('${roleId}'::uuid, '${skillId}'::uuid, ${requirementVersion}, 0.5, 0.0999, 5);
    `);
    expect(belowMinimumWeight.status).not.toBe(0);
    expect(`${belowMinimumWeight.stderr}\n${belowMinimumWeight.stdout}`).toMatch(/check constraint/i);

    const belowMinimumEvidence = runSqlExpectFailure(`
      insert into role_skill_requirements (role_id, skill_id, requirement_version, required_depth, demand_weight, evidence_count)
      values ('${roleId}'::uuid, '${skillId}'::uuid, ${requirementVersion}, 0.5, 0.5, 4);
    `);
    expect(belowMinimumEvidence.status).not.toBe(0);
    expect(`${belowMinimumEvidence.stderr}\n${belowMinimumEvidence.stdout}`).toMatch(/check constraint/i);
  });

  test("accepts a valid sdi_snapshots row", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    const insertedId = runSql(`
      insert into sdi_snapshots (role_id, skill_id, demand_index, snapshot_date, requirement_version)
      values ('${roleId}'::uuid, '${skillId}'::uuid, 0.75, date '2026-05-04', ${requirementVersion})
      returning id;
    `);

    expect(insertedId).toMatch(/[0-9a-f-]{36}/i);
  });

  test("rejects a duplicate sdi_snapshots role-skill-date tuple", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    runSql(`
      insert into sdi_snapshots (role_id, skill_id, demand_index, snapshot_date, requirement_version)
      values ('${roleId}'::uuid, '${skillId}'::uuid, 0.65, date '2026-05-05', ${requirementVersion});
    `);

    const duplicateInsert = runSqlExpectFailure(`
      insert into sdi_snapshots (role_id, skill_id, demand_index, snapshot_date, requirement_version)
      values ('${roleId}'::uuid, '${skillId}'::uuid, 0.7, date '2026-05-05', ${requirementVersion} + 1);
    `);

    expect(duplicateInsert.status).not.toBe(0);
    expect(`${duplicateInsert.stderr}\n${duplicateInsert.stdout}`).toMatch(/unique constraint/i);
  });

  test("rejects an sdi_snapshots demand_index outside the 0.0 to 1.0 range", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    const failingInsert = runSqlExpectFailure(`
      insert into sdi_snapshots (role_id, skill_id, demand_index, snapshot_date, requirement_version)
      values ('${roleId}'::uuid, '${skillId}'::uuid, 1.0001, date '2026-05-06', ${requirementVersion});
    `);

    expect(failingInsert.status).not.toBe(0);
    expect(`${failingInsert.stderr}\n${failingInsert.stdout}`).toMatch(/check constraint/i);
  });

  test("accepts a valid skill_decay_signals row", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    const insertedId = runSql(`
      insert into skill_decay_signals (
        role_id,
        skill_id,
        decay_rate,
        confidence,
        requirement_version,
        is_active
      )
      values (
        '${roleId}'::uuid,
        '${skillId}'::uuid,
        0.3,
        0.8,
        ${requirementVersion},
        true
      )
      returning id;
    `);

    expect(insertedId).toMatch(/[0-9a-f-]{36}/i);
  });

  test("rejects skill_decay_signals decay_rate and confidence outside the 0.0 to 1.0 range", () => {
    const roleId = insertRole();
    const skillId = insertSkill();
    const requirementVersion = insertRequirementVersion();

    const invalidDecayRate = runSqlExpectFailure(`
      insert into skill_decay_signals (role_id, skill_id, decay_rate, confidence, requirement_version)
      values ('${roleId}'::uuid, '${skillId}'::uuid, -0.0001, 0.8, ${requirementVersion});
    `);
    expect(invalidDecayRate.status).not.toBe(0);
    expect(`${invalidDecayRate.stderr}\n${invalidDecayRate.stdout}`).toMatch(/check constraint/i);

    const invalidConfidence = runSqlExpectFailure(`
      insert into skill_decay_signals (role_id, skill_id, decay_rate, confidence, requirement_version)
      values ('${roleId}'::uuid, '${skillId}'::uuid, 0.2, 1.0001, ${requirementVersion});
    `);
    expect(invalidConfidence.status).not.toBe(0);
    expect(`${invalidConfidence.stderr}\n${invalidConfidence.stdout}`).toMatch(/check constraint/i);
  });
});
