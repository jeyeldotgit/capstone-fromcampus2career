import { and, eq } from "drizzle-orm";
import { sdiSnapshots } from "@fcc/database";
import { SdiSnapshotSchema, type SdiSnapshot } from "@fcc/shared";
import {
  getRepositoryDatabase,
  setRepositoryDatabaseForTests,
  type RepositoryDatabase,
} from "./database.js";

type SdiSnapshotRow = typeof sdiSnapshots.$inferSelect;

function normalizeNumber(value: number | string): number {
  return typeof value === "number" ? value : Number(value);
}

function parseSdiSnapshot(row: SdiSnapshotRow): SdiSnapshot {
  return SdiSnapshotSchema.parse({
    id: row.id,
    roleId: row.roleId,
    skillId: row.skillId,
    demandIndex: normalizeNumber(row.demandIndex),
    snapshotDate: row.snapshotDate,
    requirementVersion: row.requirementVersion,
  });
}

function buildSnapshotsByRoleAndVersionQuery(
  roleId: string,
  version: number,
  database: RepositoryDatabase = getRepositoryDatabase(),
) {
  return database
    .select()
    .from(sdiSnapshots)
    .where(and(eq(sdiSnapshots.roleId, roleId), eq(sdiSnapshots.requirementVersion, version)));
}

export async function getSnapshotsByRoleAndVersion(
  roleId: string,
  version: number,
): Promise<SdiSnapshot[]> {
  const rows = await buildSnapshotsByRoleAndVersionQuery(roleId, version);
  return rows.map(parseSdiSnapshot);
}

export const __testing = {
  buildSnapshotsByRoleAndVersionQuery,
  parseSdiSnapshot,
  setDatabaseForTests: setRepositoryDatabaseForTests,
};
