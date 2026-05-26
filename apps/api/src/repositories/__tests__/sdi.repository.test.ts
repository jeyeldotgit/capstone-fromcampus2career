import { randomUUID } from "node:crypto";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { careerRoles, marketDatasets, roleRequirementVersions, sdiSnapshots, skills } from "@fcc/database";
import { SdiSnapshotSchema } from "@fcc/shared";
import { __testing, getSnapshotsByRoleAndVersion } from "../sdi.repository.js";
import { applyAdminReadinessContractPatchIfNeeded } from "./admin-readiness-test-db.js";

const DATABASE_URL = process.env.DATABASE_URL;
const client = DATABASE_URL === undefined ? null : postgres(DATABASE_URL, { max: 1 });
const db = client === null ? null : drizzle(client);
const suite = db === null ? describe.skip : describe;
let testVersion = 1_810_000_000;

class RollbackTransaction extends Error {}

beforeAll(async () => {
  await applyAdminReadinessContractPatchIfNeeded(client);
});

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

function nextTestVersion(): number {
  testVersion += 1;
  return testVersion;
}

function periodMonthForVersion(version: number): string {
  const month = String((version % 12) + 1).padStart(2, "0");
  return `${2300 + (version % 500)}-${month}-01`;
}

async function seedRole(tx: TestTransaction): Promise<string> {
  const idToken = token();
  const [row] = await tx
    .insert(careerRoles)
    .values({ code: `P1S12_SDI_ROLE_${idToken}`, title: `P1 S12 SDI Role ${idToken}` })
    .returning({ id: careerRoles.id });

  return row.id;
}

async function seedSkill(tx: TestTransaction): Promise<string> {
  const idToken = token();
  const [row] = await tx
    .insert(skills)
    .values({ code: `P1S12_SDI_SKILL_${idToken}`, name: `P1 S12 SDI Skill ${idToken}` })
    .returning({ id: skills.id });

  return row.id;
}

async function seedRequirementVersion(tx: TestTransaction): Promise<number> {
  const [dataset] = await tx
    .insert(marketDatasets)
    .values({
      filePath: `p1-s12-sdi-${token()}.csv`,
      source: "p1-s12-sdi-test",
      status: "uploaded",
    })
    .returning({ id: marketDatasets.id });
  const version = nextTestVersion();
  const [row] = await tx
    .insert(roleRequirementVersions)
    .values({
      datasetId: dataset.id,
      version,
      periodMonth: periodMonthForVersion(version),
      periodRevision: version,
      isCurrent: false,
    })
    .returning({ version: roleRequirementVersions.version });

  return row.version;
}

suite("SDI repository", () => {
  test("getSnapshotsByRoleAndVersion returns rows for the given role and version", async () => {
    await withRollback(async (tx) => {
      const roleId = await seedRole(tx);
      const otherRoleId = await seedRole(tx);
      const skillId = await seedSkill(tx);
      const otherSkillId = await seedSkill(tx);
      const version = await seedRequirementVersion(tx);

      await tx.insert(sdiSnapshots).values([
        {
          roleId,
          skillId,
          demandIndex: "0.7500",
          snapshotDate: "2026-05-21",
          requirementVersion: version,
        },
        {
          roleId: otherRoleId,
          skillId: otherSkillId,
          demandIndex: "0.5000",
          snapshotDate: "2026-05-21",
          requirementVersion: version,
        },
      ]);

      const rows = await getSnapshotsByRoleAndVersion(roleId, version);

      expect(rows).toHaveLength(1);
      expect(rows[0]).toMatchObject({
        roleId,
        skillId,
        demandIndex: 0.75,
        snapshotDate: "2026-05-21",
        requirementVersion: version,
      });
    });
  });

  test("returned rows conform to SdiSnapshotSchema", async () => {
    await withRollback(async (tx) => {
      const roleId = await seedRole(tx);
      const skillId = await seedSkill(tx);
      const version = await seedRequirementVersion(tx);

      await tx.insert(sdiSnapshots).values({
        roleId,
        skillId,
        demandIndex: "1.0000",
        snapshotDate: "2026-05-22",
        requirementVersion: version,
      });

      const [row] = await getSnapshotsByRoleAndVersion(roleId, version);

      expect(SdiSnapshotSchema.parse(row)).toEqual(row);
    });
  });

  test("demandIndex outside [0.0, 1.0] causes Zod parse to throw", () => {
    expect(() =>
      __testing.parseSdiSnapshot({
        id: randomUUID(),
        roleId: randomUUID(),
        skillId: randomUUID(),
        demandIndex: "1.0001",
        snapshotDate: "2026-05-21",
        requirementVersion: 1,
      }),
    ).toThrow();
  });
});

afterAll(async () => {
  await client?.end();
});
