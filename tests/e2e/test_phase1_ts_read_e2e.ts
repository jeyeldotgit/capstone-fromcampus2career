import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import postgres from "postgres";
import { afterAll, describe, expect, test } from "vitest";
import {
  RoleSkillRequirementSchema,
  SdiSnapshotSchema,
  SkillDecaySignalSchema,
} from "../../packages/shared/src/index.js";
import {
  getActiveDecaySignalsByRole,
  getCurrentRequirementVersion,
  getRequirementsByRoleAndVersion,
  getSnapshotsByRoleAndVersion,
} from "../../apps/api/src/repositories/index.js";
import { __testing as roleRequirementTesting } from "../../apps/api/src/repositories/role-requirements.repository.js";
import { __testing as sdiTesting } from "../../apps/api/src/repositories/sdi.repository.js";
import { __testing as decayTesting } from "../../apps/api/src/repositories/decay.repository.js";

const DATABASE_URL = process.env.DATABASE_URL;

if (DATABASE_URL === undefined || DATABASE_URL.trim() === "") {
  throw new Error("DATABASE_URL is required for tests/e2e/test_phase1_ts_read_e2e.ts");
}

const sql = postgres(DATABASE_URL, { max: 1 });

const VALID_SOURCE = "p1-s13-e2e-valid";
const MIXED_SOURCE = "p1-s13-e2e-mixed";
const VALID_FILE_PATH = "p1-s13-e2e-valid-postings.csv";
const MIXED_FILE_PATH = "p1-s13-e2e-mixed-postings.csv";

type ScenarioName = "valid" | "mixed";

type PublishedRun = {
  scenario: ScenarioName;
  datasetId: string;
  jobId: string;
  outputVersion: number;
  status: "complete" | "partial";
};

type CountRow = {
  count: string | number;
};

type RoleRow = {
  role_id: string;
};

function asRecord(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null) {
    throw new Error(`Expected database row object, received ${typeof value}`);
  }
  return value as Record<string, unknown>;
}

function requireString(row: Record<string, unknown>, key: string): string {
  const value = row[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Expected non-empty string column '${key}'`);
  }
  return value;
}

function requireNumber(row: Record<string, unknown>, key: string): number {
  const value = row[key];
  const numberValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numberValue)) {
    throw new Error(`Expected numeric column '${key}'`);
  }
  return numberValue;
}

function requireStatus(row: Record<string, unknown>, key: string): "complete" | "partial" {
  const value = requireString(row, key);
  if (value !== "complete" && value !== "partial") {
    throw new Error(`Expected terminal status complete|partial, received '${value}'`);
  }
  return value;
}

async function loadPublishedRun(
  scenario: ScenarioName,
  source: string,
  filePath: string,
): Promise<PublishedRun> {
  const rows = await sql`
    select
      datasets.id as dataset_id,
      jobs.id as job_id,
      jobs.output_version,
      jobs.status
    from market_datasets datasets
    join pipeline_jobs jobs on jobs.dataset_id = datasets.id
    where datasets.source = ${source}
      and datasets.file_path = ${filePath}
    order by jobs.created_at desc
    limit 1
  `;
  const row = rows[0];
  if (row === undefined) {
    throw new Error(`Missing Phase 1 e2e pipeline run for source='${source}'`);
  }

  const record = asRecord(row);
  return {
    scenario,
    datasetId: requireString(record, "dataset_id"),
    jobId: requireString(record, "job_id"),
    outputVersion: requireNumber(record, "output_version"),
    status: requireStatus(record, "status"),
  };
}

async function countRows(query: Promise<CountRow[]>): Promise<number> {
  const rows = await query;
  const row = rows[0];
  if (row === undefined) {
    throw new Error("Expected count query to return one row");
  }
  return Number(row.count);
}

async function loadPublishedRoleId(version: number): Promise<string> {
  const rows = await sql<RoleRow[]>`
    select distinct role_id
    from role_skill_requirements
    where requirement_version = ${version}
    order by role_id
  `;
  expect(rows, `expected exactly one role for requirement_version=${version}`).toHaveLength(1);
  return rows[0].role_id;
}

async function assertPreparedReads(run: PublishedRun, expectedStatus: "complete" | "partial"): Promise<void> {
  expect(run.status).toBe(expectedStatus);

  const roleId = await loadPublishedRoleId(run.outputVersion);
  const directRequirementCount = await countRows(sql<CountRow[]>`
    select count(*)::int as count
    from role_skill_requirements
    where role_id = ${roleId}
      and requirement_version = ${run.outputVersion}
  `);
  const requirements = await getRequirementsByRoleAndVersion(roleId, run.outputVersion);

  expect(requirements).toHaveLength(directRequirementCount);
  expect(requirements).toHaveLength(2);
  for (const requirement of requirements) {
    expect(RoleSkillRequirementSchema.parse(requirement)).toEqual(requirement);
  }

  const directSdiCount = await countRows(sql<CountRow[]>`
    select count(*)::int as count
    from sdi_snapshots
    where role_id = ${roleId}
      and requirement_version = ${run.outputVersion}
  `);
  const snapshots = await getSnapshotsByRoleAndVersion(roleId, run.outputVersion);

  expect(snapshots).toHaveLength(directSdiCount);
  expect(snapshots).toHaveLength(2);
  for (const snapshot of snapshots) {
    expect(SdiSnapshotSchema.parse(snapshot)).toEqual(snapshot);
  }

  const activeDecayDirectCount = await countRows(sql<CountRow[]>`
    select count(*)::int as count
    from skill_decay_signals
    where role_id = ${roleId}
      and is_active = true
  `);
  const activeDecaySignals = await getActiveDecaySignalsByRole(roleId);

  expect(activeDecaySignals).toHaveLength(activeDecayDirectCount);
  for (const signal of activeDecaySignals) {
    expect(SkillDecaySignalSchema.parse(signal)).toEqual(signal);
  }

  if (run.scenario === "mixed") {
    expect(activeDecaySignals).toHaveLength(2);
  }
}

describe("Phase 1 TypeScript read-layer e2e", () => {
  test("reads Python-published valid and mixed prepared outputs through S12 contracts", async () => {
    const validRun = await loadPublishedRun("valid", VALID_SOURCE, VALID_FILE_PATH);
    const mixedRun = await loadPublishedRun("mixed", MIXED_SOURCE, MIXED_FILE_PATH);

    await assertPreparedReads(validRun, "complete");
    await assertPreparedReads(mixedRun, "partial");

    const currentVersion = await getCurrentRequirementVersion();
    expect(currentVersion?.version).toBe(mixedRun.outputVersion);
    expect(currentVersion?.datasetId).toBe(mixedRun.datasetId);
    expect(currentVersion?.isCurrent).toBe(true);
  });

  test("read repositories do not query raw job_postings", () => {
    const roleId = randomUUID();
    const querySql = [
      roleRequirementTesting.buildCurrentRequirementVersionQuery().toSQL().sql,
      roleRequirementTesting.buildRequirementsByRoleAndVersionQuery(roleId, 1).toSQL().sql,
      sdiTesting.buildSnapshotsByRoleAndVersionQuery(roleId, 1).toSQL().sql,
      decayTesting.buildActiveDecaySignalsByRoleQuery(roleId).toSQL().sql,
    ].join("\n");

    expect(querySql).not.toMatch(/job_postings|jobPostings/i);

    const sourceFiles = [
      "../../apps/api/src/repositories/role-requirements.repository.ts",
      "../../apps/api/src/repositories/sdi.repository.ts",
      "../../apps/api/src/repositories/decay.repository.ts",
    ].map((filePath) => readFileSync(new URL(filePath, import.meta.url), "utf8"));

    expect(sourceFiles.join("\n")).not.toMatch(/job_postings|jobPostings/i);
  });
});

afterAll(async () => {
  await sql.end();
});
