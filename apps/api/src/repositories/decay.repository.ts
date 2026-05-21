import { and, eq } from "drizzle-orm";
import { skillDecaySignals } from "@fcc/database";
import { SkillDecaySignalSchema, type SkillDecaySignal } from "@fcc/shared";
import {
  getRepositoryDatabase,
  setRepositoryDatabaseForTests,
  type RepositoryDatabase,
} from "./database.js";

type SkillDecaySignalRow = typeof skillDecaySignals.$inferSelect;

function normalizeDateTime(value: Date | string): string {
  if (value instanceof Date) {
    return value.toISOString();
  }

  return new Date(value).toISOString();
}

function normalizeNumber(value: number | string): number {
  return typeof value === "number" ? value : Number(value);
}

function parseSkillDecaySignal(row: SkillDecaySignalRow): SkillDecaySignal {
  return SkillDecaySignalSchema.parse({
    id: row.id,
    roleId: row.roleId,
    skillId: row.skillId,
    decayRate: normalizeNumber(row.decayRate),
    confidence: normalizeNumber(row.confidence),
    detectedAt: normalizeDateTime(row.detectedAt),
    requirementVersion: row.requirementVersion,
    isActive: row.isActive,
  });
}

function buildActiveDecaySignalsByRoleQuery(
  roleId: string,
  database: RepositoryDatabase = getRepositoryDatabase(),
) {
  return database
    .select()
    .from(skillDecaySignals)
    .where(and(eq(skillDecaySignals.roleId, roleId), eq(skillDecaySignals.isActive, true)));
}

export async function getActiveDecaySignalsByRole(roleId: string): Promise<SkillDecaySignal[]> {
  const rows = await buildActiveDecaySignalsByRoleQuery(roleId);
  return rows.map(parseSkillDecaySignal);
}

export const __testing = {
  buildActiveDecaySignalsByRoleQuery,
  parseSkillDecaySignal,
  setDatabaseForTests: setRepositoryDatabaseForTests,
};
