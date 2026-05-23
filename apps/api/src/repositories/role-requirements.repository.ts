import { and, desc, eq } from "drizzle-orm";
import { roleRequirementVersions, roleSkillRequirements } from "@fcc/database";
import {
  RoleRequirementVersionSchema,
  RoleSkillRequirementSchema,
  type RoleRequirementVersion,
  type RoleSkillRequirement,
} from "@fcc/shared";
import {
  getRepositoryDatabase,
  setRepositoryDatabaseForTests,
  type RepositoryDatabase,
} from "./database.js";

type RequirementVersionRow = typeof roleRequirementVersions.$inferSelect;
type RoleSkillRequirementRow = typeof roleSkillRequirements.$inferSelect;

function normalizeDateTime(value: Date | string): string {
  if (value instanceof Date) {
    return value.toISOString();
  }

  return new Date(value).toISOString();
}

function normalizeNumber(value: number | string): number {
  return typeof value === "number" ? value : Number(value);
}

function parseRequirementVersion(row: RequirementVersionRow): RoleRequirementVersion {
  return RoleRequirementVersionSchema.parse({
    id: row.id,
    version: row.version,
    datasetId: row.datasetId,
    periodMonth: row.periodMonth,
    periodRevision: row.periodRevision,
    computedAt: normalizeDateTime(row.computedAt),
    isCurrent: row.isCurrent,
  });
}

function parseRoleSkillRequirement(row: RoleSkillRequirementRow): RoleSkillRequirement {
  return RoleSkillRequirementSchema.parse({
    id: row.id,
    roleId: row.roleId,
    skillId: row.skillId,
    requirementVersion: row.requirementVersion,
    requiredDepth: normalizeNumber(row.requiredDepth),
    demandWeight: normalizeNumber(row.demandWeight),
    evidenceCount: row.evidenceCount,
  });
}

function parseCurrentRequirementVersionRows(
  rows: RequirementVersionRow[],
): RoleRequirementVersion | null {
  const [row] = rows;
  return row === undefined ? null : parseRequirementVersion(row);
}

function buildCurrentRequirementVersionQuery(database: RepositoryDatabase = getRepositoryDatabase()) {
  return database
    .select()
    .from(roleRequirementVersions)
    .where(eq(roleRequirementVersions.isCurrent, true))
    .orderBy(desc(roleRequirementVersions.version))
    .limit(1);
}

function buildRequirementsByRoleAndVersionQuery(
  roleId: string,
  version: number,
  database: RepositoryDatabase = getRepositoryDatabase(),
) {
  return database
    .select()
    .from(roleSkillRequirements)
    .where(
      and(
        eq(roleSkillRequirements.roleId, roleId),
        eq(roleSkillRequirements.requirementVersion, version),
      ),
    );
}

export async function getCurrentRequirementVersion(): Promise<RoleRequirementVersion | null> {
  const rows = await buildCurrentRequirementVersionQuery();
  return parseCurrentRequirementVersionRows(rows);
}

export async function getRequirementsByRoleAndVersion(
  roleId: string,
  version: number,
): Promise<RoleSkillRequirement[]> {
  const rows = await buildRequirementsByRoleAndVersionQuery(roleId, version);
  return rows.map(parseRoleSkillRequirement);
}

export const __testing = {
  buildCurrentRequirementVersionQuery,
  buildRequirementsByRoleAndVersionQuery,
  parseCurrentRequirementVersionRows,
  parseRequirementVersion,
  parseRoleSkillRequirement,
  setDatabaseForTests: setRepositoryDatabaseForTests,
};
