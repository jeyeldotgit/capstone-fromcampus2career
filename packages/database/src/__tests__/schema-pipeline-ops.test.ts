import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { before, describe, test } from "node:test";

const DATABASE_URL = process.env.DATABASE_URL;
const PSQL_PATH = "psql";
const DOCKER_PATH = "docker";

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

const REQUIRED_TABLES = ["pipeline_jobs", "pipeline_rejected_rows"] as const;

const REQUIRED_CONSTRAINTS = [
  "pipeline_jobs_dataset_id_fkey",
  "pipeline_jobs_job_type_non_empty_chk",
  "pipeline_jobs_status_valid_chk",
  "pipeline_jobs_processed_rows_non_negative_chk",
  "pipeline_jobs_rejected_rows_non_negative_chk",
  "pipeline_jobs_output_version_positive_chk",
  "pipeline_jobs_error_message_non_empty_when_present_chk",
  "pipeline_jobs_finished_at_after_started_at_chk",
  "pipeline_jobs_terminal_state_fields_chk",
  "pipeline_jobs_output_version_terminal_state_chk",
  "pipeline_rejected_rows_pipeline_job_id_fkey",
  "pipeline_rejected_rows_pipeline_job_id_row_number_unique",
  "pipeline_rejected_rows_row_number_positive_chk",
  "pipeline_rejected_rows_reason_non_empty_chk",
] as const;

const REQUIRED_INDEXES = [
  "pipeline_jobs_dataset_id_created_at_idx",
  "pipeline_jobs_status_created_at_idx",
  "pipeline_jobs_output_version_idx",
  "pipeline_rejected_rows_pipeline_job_id_idx",
] as const;

const TAXONOMY_MIGRATION_SQL = readFileSync(
  new URL("../../migrations/20260503143000_p1_s01_taxonomy_schema.sql", import.meta.url),
  "utf8",
);

const PIPELINE_OPS_MIGRATION_SQL = readFileSync(
  new URL("../../migrations/20260504100000_p1_s02_pipeline_ops.sql", import.meta.url),
  "utf8",
);

function runSql(sqlText: string): string {
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run pipeline ops schema tests");
  if (USE_DOCKER_PSQL) {
    return execFileSync(
      DOCKER_PATH,
      [
        "run",
        "--rm",
        "postgres:16-alpine",
        "psql",
        DATABASE_URL,
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

  return execFileSync(PSQL_PATH, [DATABASE_URL, "--set", "ON_ERROR_STOP=1", "--tuples-only", "--no-align", "--quiet", "--command", sqlText], { encoding: "utf8" }).trim();
}

function runSqlExpectFailure(sqlText: string): { status: number | null; stderr: string; stdout: string } {
  assert.ok(DATABASE_URL, "DATABASE_URL must be provided to run pipeline ops schema tests");
  const result = USE_DOCKER_PSQL
    ? spawnSync(
        DOCKER_PATH,
        [
          "run",
          "--rm",
          "postgres:16-alpine",
          "psql",
          DATABASE_URL,
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

function insertDataset(): string {
  return runSql(`
    insert into market_datasets (file_path, source, status)
    values (
      'dataset_' || substr(md5(random()::text), 1, 8) || '.csv',
      'integration-test',
      'uploaded'
    )
    returning id;
  `);
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

describe(
  "P1-S02 pipeline ops schema migration",
  { skip: CAN_RUN ? false : "requires DATABASE_URL and either local psql or Docker" },
  () => {
    before(() => {
      if (!tableExists("skills")) {
        runSql(TAXONOMY_MIGRATION_SQL);
      }

      if (!tableExists("pipeline_jobs")) {
        runSql(PIPELINE_OPS_MIGRATION_SQL);
      }
    });

    test("creates pipeline ops tables", () => {
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

    test("creates required constraints and indexes", () => {
      const constraintList = REQUIRED_CONSTRAINTS.map((name) => `'${name}'`).join(", ");
      const constraintCount = Number(
        runSql(`
          select count(*)
          from pg_constraint
          where conname in (${constraintList});
        `),
      );

      assert.equal(constraintCount, REQUIRED_CONSTRAINTS.length);

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

      const indexList = REQUIRED_INDEXES.map((name) => `'${name}'`).join(", ");
      const indexCount = Number(
        runSql(`
          select count(*)
          from pg_indexes
          where schemaname = 'public'
            and indexname in (${indexList});
        `),
      );

      assert.equal(indexCount, REQUIRED_INDEXES.length);
    });

    test("rejects rejected-row inserts without a valid pipeline_job_id", () => {
      const failingInsert = runSqlExpectFailure(`
        insert into pipeline_rejected_rows (pipeline_job_id, row_number, raw_payload, reason)
        values (
          '00000000-0000-0000-0000-000000000000'::uuid,
          12,
          '{"title":"bad row"}'::jsonb,
          'missing required job reference'
        );
      `);

      assert.notEqual(failingInsert.status, 0);
      assert.match(`${failingInsert.stderr}\n${failingInsert.stdout}`, /foreign key constraint/i);
    });

    test("supports pending to running to complete lifecycle updates", () => {
      const datasetId = insertDataset();
      const jobId = runSql(`
        insert into pipeline_jobs (dataset_id, job_type)
        values ('${datasetId}'::uuid, 'ingestion')
        returning id;
      `);

      const pendingState = runSql(`
        select concat_ws('|', status, processed_rows, rejected_rows, output_version::text, finished_at::text)
        from pipeline_jobs
        where id = '${jobId}'::uuid;
      `);
      assert.equal(pendingState, "pending|0|0");

      runSql(`
        update pipeline_jobs
        set status = 'running',
            processed_rows = 25,
            rejected_rows = 2
        where id = '${jobId}'::uuid;
      `);

      const runningState = runSql(`
        select concat_ws('|', status, processed_rows, rejected_rows, finished_at::text)
        from pipeline_jobs
        where id = '${jobId}'::uuid;
      `);
      assert.equal(runningState, "running|25|2");

      runSql(`
        update pipeline_jobs
        set status = 'complete',
            processed_rows = 120,
            rejected_rows = 3,
            output_version = 1,
            finished_at = started_at + interval '1 minute'
        where id = '${jobId}'::uuid;
      `);

      const completedState = runSql(`
        select concat_ws('|', status, processed_rows, rejected_rows, output_version::text, (finished_at is not null)::text)
        from pipeline_jobs
        where id = '${jobId}'::uuid;
      `);
      assert.equal(completedState, "complete|120|3|1|true");
    });

    test("supports running to partial lifecycle updates", () => {
      const datasetId = insertDataset();
      const jobId = runSql(`
        insert into pipeline_jobs (dataset_id, job_type, status)
        values ('${datasetId}'::uuid, 'ingestion', 'running')
        returning id;
      `);

      runSql(`
        update pipeline_jobs
        set processed_rows = 80,
            rejected_rows = 5,
            output_version = 2,
            status = 'partial',
            finished_at = started_at + interval '30 seconds'
        where id = '${jobId}'::uuid;
      `);

      const partialState = runSql(`
        select concat_ws('|', status, processed_rows, rejected_rows, output_version::text, (finished_at is not null)::text)
        from pipeline_jobs
        where id = '${jobId}'::uuid;
      `);
      assert.equal(partialState, "partial|80|5|2|true");
    });

    test("rejects invalid counter and lifecycle state shapes", () => {
      const datasetId = insertDataset();

      const negativeCounters = runSqlExpectFailure(`
        insert into pipeline_jobs (dataset_id, job_type, processed_rows)
        values ('${datasetId}'::uuid, 'ingestion', -1);
      `);
      assert.notEqual(negativeCounters.status, 0);
      assert.match(`${negativeCounters.stderr}\n${negativeCounters.stdout}`, /check constraint/i);

      const missingFinishedAt = runSqlExpectFailure(`
        insert into pipeline_jobs (dataset_id, job_type, status)
        values ('${datasetId}'::uuid, 'ingestion', 'complete');
      `);
      assert.notEqual(missingFinishedAt.status, 0);
      assert.match(`${missingFinishedAt.stderr}\n${missingFinishedAt.stdout}`, /check constraint/i);

      const pendingWithOutputVersion = runSqlExpectFailure(`
        insert into pipeline_jobs (dataset_id, job_type, output_version)
        values ('${datasetId}'::uuid, 'ingestion', 1);
      `);
      assert.notEqual(pendingWithOutputVersion.status, 0);
      assert.match(`${pendingWithOutputVersion.stderr}\n${pendingWithOutputVersion.stdout}`, /check constraint/i);
    });
  },
);
