import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { afterAll, describe, expect, test } from "vitest";
import {
  careerRoles,
  marketDatasets,
  roleRequirementVersions,
  roleSkillRequirements,
  skills,
} from "@fcc/database";
import { RoleSkillRequirementSchema } from "@fcc/shared";
import {
  __testing,
  getCurrentRequirementVersion,
  getRequirementsByRoleAndVersion,
} from "../role-requirements.repository.js";
import { __testing as decayTesting } from "../decay.repository.js";
import { __testing as sdiTesting } from "../sdi.repository.js";

const DATABASE_URL = process.env.DATABASE_URL;
const client = DATABASE_URL === undefined ? null : postgres(DATABASE_URL, { max: 1 });
const db = client === null ? null : drizzle(client);
const suite = db === null ? describe.skip : describe;

class RollbackTransaction extends Error {}

type TestDatabase = NonNullable<typeof db>;
type TestTransaction = Parameters<Parameters<TestDatabase["transaction"]>[0]>[0];

async function withRollback(run: (tx: TestTransaction) => Promise<void>): Promise<void> {
  if (db === null) {
    throw new Error("DATABASE_URL is required for repository integration tests");
  }

  try {
    await db.transaction(async (tx) => {
      __testing.setDatabaseForTests(tx);
      await run(tx);
      throw new RollbackTransaction();
    });
  } catch (error) {
    if (!(error instanceof RollbackTransaction)) {
      throw error;
    }
  } finally {
    __testing.setDatabaseForTests(null);
  }
}

function token(): string {
  return randomUUID().replaceAll("-", "").slice(0, 12);
}

async function seedDataset(tx: TestTransaction): Promise<string> {
  const [row] = await tx
    .insert(marketDatasets)
    .values({
      filePath: `p1-s12-${token()}.csv`,
      source: "p1-s12-role-requirements-test",
      status: "uploaded",
    })
    .returning({ id: marketDatasets.id });

  return row.id;
}

async function seedRole(tx: TestTransaction): Promise<string> {
  const idToken = token();
  const [row] = await tx
    .insert(careerRoles)
    .values({
      code: `P1S12_ROLE_${idToken}`,
      title: `P1 S12 Role ${idToken}`,
    })
    .returning({ id: careerRoles.id });

  return row.id;
}

async function seedSkill(tx: TestTransaction): Promise<string> {
  const idToken = token();
  const [row] = await tx
    .insert(skills)
    .values({
      code: `P1S12_SKILL_${idToken}`,
      name: `P1 S12 Skill ${idToken}`,
    })
    .returning({ id: skills.id });

  return row.id;
}

async function seedRequirementVersion(
  tx: TestTransaction,
  datasetId: string,
  isCurrent: boolean,
): Promise<number> {
  const version = Math.floor(Math.random() * 1_000_000_000) + 1;
  const [row] = await tx
    .insert(roleRequirementVersions)
    .values({
      version,
      datasetId,
      isCurrent,
    })
    .returning({ version: roleRequirementVersions.version });

  return row.version;
}

suite("role requirements repository", () => {
  test("getCurrentRequirementVersion returns the row where is_current = true", async () => {
    await withRollback(async (tx) => {
      const datasetId = await seedDataset(tx);
      const version = await seedRequirementVersion(tx, datasetId, true);

      const result = await getCurrentRequirementVersion();

      expect(result).not.toBeNull();
      expect(result?.version).toBe(version);
      expect(result?.datasetId).toBe(datasetId);
      expect(result?.isCurrent).toBe(true);
    });
  });

  test("getCurrentRequirementVersion returns null when no current version exists", async () => {
    expect(__testing.parseCurrentRequirementVersionRows([])).toBeNull();
  });

  test("getRequirementsByRoleAndVersion returns rows matching roleId and version", async () => {
    await withRollback(async (tx) => {
      const datasetId = await seedDataset(tx);
      const roleId = await seedRole(tx);
      const otherRoleId = await seedRole(tx);
      const skillId = await seedSkill(tx);
      const otherSkillId = await seedSkill(tx);
      const version = await seedRequirementVersion(tx, datasetId, false);

      await tx.insert(roleSkillRequirements).values([
        {
          roleId,
          skillId,
          requirementVersion: version,
          requiredDepth: "0.8000",
          demandWeight: "0.6000",
          evidenceCount: 5,
        },
        {
          roleId: otherRoleId,
          skillId: otherSkillId,
          requirementVersion: version,
          requiredDepth: "0.7000",
          demandWeight: "0.5000",
          evidenceCount: 5,
        },
      ]);

      const rows = await getRequirementsByRoleAndVersion(roleId, version);

      expect(rows).toHaveLength(1);
      expect(rows[0]).toMatchObject({
        roleId,
        skillId,
        requirementVersion: version,
        requiredDepth: 0.8,
        demandWeight: 0.6,
        evidenceCount: 5,
      });
    });
  });

  test("returned rows conform to RoleSkillRequirementSchema", async () => {
    await withRollback(async (tx) => {
      const datasetId = await seedDataset(tx);
      const roleId = await seedRole(tx);
      const skillId = await seedSkill(tx);
      const version = await seedRequirementVersion(tx, datasetId, false);

      await tx.insert(roleSkillRequirements).values({
        roleId,
        skillId,
        requirementVersion: version,
        requiredDepth: "0.5000",
        demandWeight: "1.0000",
        evidenceCount: 6,
      });

      const [row] = await getRequirementsByRoleAndVersion(roleId, version);

      expect(RoleSkillRequirementSchema.parse(row)).toEqual(row);
    });
  });

  test("requiredDepth outside [0.0, 1.0] causes Zod parse to throw", () => {
    expect(() =>
      __testing.parseRoleSkillRequirement({
        id: randomUUID(),
        roleId: randomUUID(),
        skillId: randomUUID(),
        requirementVersion: 1,
        requiredDepth: "1.0001",
        demandWeight: "0.5000",
        evidenceCount: 5,
      }),
    ).toThrow();
  });

  test("demandWeight below 0.1 causes Zod parse to throw", () => {
    expect(() =>
      __testing.parseRoleSkillRequirement({
        id: randomUUID(),
        roleId: randomUUID(),
        skillId: randomUUID(),
        requirementVersion: 1,
        requiredDepth: "0.5000",
        demandWeight: "0.0999",
        evidenceCount: 5,
      }),
    ).toThrow();
  });
});

describe("prepared-intelligence read path guards", () => {
  test("repository query builders do not reference job_postings", () => {
    const roleId = randomUUID();
    const querySql = [
      __testing.buildCurrentRequirementVersionQuery().toSQL().sql,
      __testing.buildRequirementsByRoleAndVersionQuery(roleId, 1).toSQL().sql,
      sdiTesting.buildSnapshotsByRoleAndVersionQuery(roleId, 1).toSQL().sql,
      decayTesting.buildActiveDecaySignalsByRoleQuery(roleId).toSQL().sql,
    ].join("\n");

    expect(querySql).not.toMatch(/job_postings|jobPostings/i);
  });

  test("repository source files do not import job_postings schema", () => {
    const sourceFiles = [
      "../role-requirements.repository.ts",
      "../sdi.repository.ts",
      "../decay.repository.ts",
    ].map((filePath) => readFileSync(new URL(filePath, import.meta.url), "utf8"));

    expect(sourceFiles.join("\n")).not.toMatch(/job_postings|jobPostings/i);
  });
});

afterAll(async () => {
  await client?.end();
});
