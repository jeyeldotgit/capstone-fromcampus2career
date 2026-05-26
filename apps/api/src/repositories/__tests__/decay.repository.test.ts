import { randomUUID } from "node:crypto";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { careerRoles, marketDatasets, roleRequirementVersions, skillDecaySignals, skills } from "@fcc/database";
import { SkillDecaySignalSchema } from "@fcc/shared";
import { __testing, getActiveDecaySignalsByRole } from "../decay.repository.js";
import { applyAdminReadinessContractPatchIfNeeded } from "./admin-readiness-test-db.js";

const DATABASE_URL = process.env.DATABASE_URL;
const client = DATABASE_URL === undefined ? null : postgres(DATABASE_URL, { max: 1 });
const db = client === null ? null : drizzle(client);
const suite = db === null ? describe.skip : describe;
let testVersion = 1_820_000_000;

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
  return `${2400 + (version % 500)}-${month}-01`;
}

async function seedRole(tx: TestTransaction): Promise<string> {
  const idToken = token();
  const [row] = await tx
    .insert(careerRoles)
    .values({ code: `P1S12_DECAY_ROLE_${idToken}`, title: `P1 S12 Decay Role ${idToken}` })
    .returning({ id: careerRoles.id });

  return row.id;
}

async function seedSkill(tx: TestTransaction): Promise<string> {
  const idToken = token();
  const [row] = await tx
    .insert(skills)
    .values({ code: `P1S12_DECAY_SKILL_${idToken}`, name: `P1 S12 Decay Skill ${idToken}` })
    .returning({ id: skills.id });

  return row.id;
}

async function seedRequirementVersion(tx: TestTransaction, periodRevision: number): Promise<number> {
  const [dataset] = await tx
    .insert(marketDatasets)
    .values({
      filePath: `p1-s12-decay-${token()}.csv`,
      source: "p1-s12-decay-test",
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

suite("decay repository", () => {
  test("getActiveDecaySignalsByRole returns only rows where is_active = true", async () => {
    await withRollback(async (tx) => {
      const roleId = await seedRole(tx);
      const skillId = await seedSkill(tx);
      const inactiveSkillId = await seedSkill(tx);
      const firstVersion = await seedRequirementVersion(tx, 1);
      const secondVersion = await seedRequirementVersion(tx, 2);

      await tx.insert(skillDecaySignals).values([
        {
          roleId,
          skillId,
          decayRate: "-0.2500",
          confidence: "0.9000",
          requirementVersion: firstVersion,
          isActive: true,
        },
        {
          roleId,
          skillId: inactiveSkillId,
          decayRate: "-0.3000",
          confidence: "0.8000",
          requirementVersion: secondVersion,
          isActive: false,
        },
      ]);

      const rows = await getActiveDecaySignalsByRole(roleId);

      expect(rows).toHaveLength(1);
      expect(rows[0]).toMatchObject({
        roleId,
        skillId,
        decayRate: -0.25,
        confidence: 0.9,
        requirementVersion: firstVersion,
        isActive: true,
      });
    });
  });

  test("returned rows conform to SkillDecaySignalSchema", async () => {
    await withRollback(async (tx) => {
      const roleId = await seedRole(tx);
      const skillId = await seedSkill(tx);
      const version = await seedRequirementVersion(tx, 3);

      await tx.insert(skillDecaySignals).values({
        roleId,
        skillId,
        decayRate: "-0.1000",
        confidence: "1.0000",
        requirementVersion: version,
        isActive: true,
      });

      const [row] = await getActiveDecaySignalsByRole(roleId);

      expect(SkillDecaySignalSchema.parse(row)).toEqual(row);
    });
  });

  test("confidence outside [0.0, 1.0] causes Zod parse to throw", () => {
    expect(() =>
      __testing.parseSkillDecaySignal({
        id: randomUUID(),
        roleId: randomUUID(),
        skillId: randomUUID(),
        decayRate: "-0.2500",
        confidence: "1.0001",
        detectedAt: new Date(),
        requirementVersion: 1,
        isActive: true,
      }),
    ).toThrow();
  });
});

afterAll(async () => {
  await client?.end();
});
