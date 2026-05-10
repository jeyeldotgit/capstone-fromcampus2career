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
    return spawnSync(DOCKER_PATH, ["version", "--format", "{{.Server.Version}}"], {
      encoding: "utf8",
    }).status === 0;
  } catch {
    return false;
  }
})();

const USE_DOCKER_PSQL = !PSQL_AVAILABLE && DOCKER_AVAILABLE;
const CAN_RUN = Boolean(DATABASE_URL) && (PSQL_AVAILABLE || USE_DOCKER_PSQL);

const TAXONOMY_MIGRATION_SQL = readFileSync(
  new URL("../../migrations/20260503143000_p1_s01_taxonomy_schema.sql", import.meta.url),
  "utf8",
);

const PIPELINE_OPS_MIGRATION_SQL = readFileSync(
  new URL("../../migrations/20260504100000_p1_s02_pipeline_ops.sql", import.meta.url),
  "utf8",
);

const APP_EVENTS_MIGRATION_SQL = readFileSync(
  new URL("../../migrations/20260510130000_add_app_events.sql", import.meta.url),
  "utf8",
);

function runSql(sqlText: string): string {
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run app events schema tests");
  if (USE_DOCKER_PSQL) {
    assert.ok(DOCKER_DATABASE_URL, "DATABASE_URL must be provided to run app events schema tests");
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
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run app events schema tests");
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

const suite = CAN_RUN ? describe : describe.skip;

suite("P1-S02-BJ app_events schema migration", () => {
  beforeAll(() => {
    if (!tableExists("skills")) {
      runSql(TAXONOMY_MIGRATION_SQL);
    }

    if (!tableExists("pipeline_jobs")) {
      runSql(PIPELINE_OPS_MIGRATION_SQL);
    }

    if (!tableExists("app_events")) {
      runSql(APP_EVENTS_MIGRATION_SQL);
    }
  });

  test("insert with all required fields succeeds", () => {
    const insertedId = runSql(`
      insert into app_events (
        event_type,
        aggregate_type,
        aggregate_id,
        payload,
        status,
        available_at
      )
      values (
        'pipeline.ingestion.completed',
        'pipeline_job',
        gen_random_uuid(),
        '{"pipelineJobId":"test-job","status":"complete"}'::jsonb,
        'processing',
        now()
      )
      returning id;
    `);

    expect(insertedId).toMatch(/[0-9a-f-]{36}/i);
  });

  test("insert without event_type is rejected by the database", () => {
    const failingInsert = runSqlExpectFailure(`
      insert into app_events (aggregate_type, payload)
      values ('pipeline_job', '{"status":"complete"}'::jsonb);
    `);

    expect(failingInsert.status).not.toBe(0);
    expect(`${failingInsert.stderr}\n${failingInsert.stdout}`).toMatch(/null value/i);
  });

  test("insert without aggregate_type is rejected by the database", () => {
    const failingInsert = runSqlExpectFailure(`
      insert into app_events (event_type, payload)
      values ('pipeline.ingestion.completed', '{"status":"complete"}'::jsonb);
    `);

    expect(failingInsert.status).not.toBe(0);
    expect(`${failingInsert.stderr}\n${failingInsert.stdout}`).toMatch(/null value/i);
  });

  test("insert without payload is rejected by the database", () => {
    const failingInsert = runSqlExpectFailure(`
      insert into app_events (event_type, aggregate_type)
      values ('pipeline.ingestion.completed', 'pipeline_job');
    `);

    expect(failingInsert.status).not.toBe(0);
    expect(`${failingInsert.stderr}\n${failingInsert.stdout}`).toMatch(/null value/i);
  });

  test("insert without available_at uses now default and succeeds", () => {
    const availableAt = runSql(`
      insert into app_events (event_type, aggregate_type, payload)
      values (
        'admin.dataset.ingest_requested',
        'market_dataset',
        '{"datasetId":"test-dataset"}'::jsonb
      )
      returning available_at is not null;
    `);

    expect(availableAt).toBe("t");
  });

  test("status defaults to pending when not provided", () => {
    const status = runSql(`
      insert into app_events (event_type, aggregate_type, payload)
      values (
        'roadmap.enrichment_requested',
        'skill_gap_result',
        '{"analysisResultId":"test-analysis"}'::jsonb
      )
      returning status;
    `);

    expect(status).toBe("pending");
  });

  test("insert with status outside the allowed vocabulary is rejected", () => {
    const failingInsert = runSqlExpectFailure(`
      insert into app_events (event_type, aggregate_type, payload, status)
      values (
        'pipeline.ingestion.completed',
        'pipeline_job',
        '{"status":"complete"}'::jsonb,
        'complete'
      );
    `);

    expect(failingInsert.status).not.toBe(0);
    expect(`${failingInsert.stderr}\n${failingInsert.stdout}`).toMatch(/app_events_status_valid_chk/i);
  });

  test("processed_at and error_message accept null without error", () => {
    const insertedId = runSql(`
      insert into app_events (
        event_type,
        aggregate_type,
        payload,
        processed_at,
        error_message
      )
      values (
        'market.requirements.published',
        'role_requirement_version',
        '{"version":1}'::jsonb,
        null,
        null
      )
      returning id;
    `);

    expect(insertedId).toMatch(/[0-9a-f-]{36}/i);
  });
});
