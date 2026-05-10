import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { pathToFileURL } from "node:url";
import { careerRoleAliases as careerRoleAliasesTable } from "../schema/career_role_aliases.ts";
import { careerRoles as careerRolesTable } from "../schema/career_roles.ts";
import { skills as skillsTable } from "../schema/skills.ts";
import { skillAliases as skillAliasesTable } from "../schema/skill_aliases.ts";
import { careerRoleAliasesSeed } from "./taxonomy/career-role-aliases.seed.ts";
import { careerRolesSeed } from "./taxonomy/career-roles.seed.ts";
import { ROLE_ALIAS_IDS, ROLE_IDS, SKILL_ALIAS_IDS, SKILL_IDS } from "./taxonomy/id-maps.ts";
import { skillAliasesSeed } from "./taxonomy/skill-aliases.seed.ts";
import { skillsSeed } from "./taxonomy/skills.seed.ts";

function collectDuplicateValues(values: string[]): string[] {
  const counts = new Map<string, number>();

  for (const value of values) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }

  return [...counts.entries()]
    .filter(([, count]) => count > 1)
    .map(([value]) => value)
    .sort((left, right) => left.localeCompare(right));
}

function assertNoDuplicateValues(values: string[], label: string): void {
  const duplicates = collectDuplicateValues(values);

  if (duplicates.length > 0) {
    throw new Error(`${label} contains duplicate values: ${duplicates.join(", ")}`);
  }
}

function assertIdsExist(
  childIds: string[],
  validIds: ReadonlySet<string>,
  label: string,
): void {
  const missingIds = [...new Set(childIds.filter((childId) => !validIds.has(childId)))];

  if (missingIds.length > 0) {
    throw new Error(`${label} references unknown IDs: ${missingIds.join(", ")}`);
  }
}

export function validateTaxonomySeedData(): void {
  if (skillsSeed.length !== Object.keys(SKILL_IDS).length) {
    throw new Error(
      `skills seed count mismatch: expected ${Object.keys(SKILL_IDS).length}, received ${skillsSeed.length}`,
    );
  }
  if (skillAliasesSeed.length !== Object.keys(SKILL_ALIAS_IDS).length) {
    throw new Error(
      `skill_aliases seed count mismatch: expected ${Object.keys(SKILL_ALIAS_IDS).length}, received ${skillAliasesSeed.length}`,
    );
  }
  if (careerRolesSeed.length !== Object.keys(ROLE_IDS).length) {
    throw new Error(
      `career_roles seed count mismatch: expected ${Object.keys(ROLE_IDS).length}, received ${careerRolesSeed.length}`,
    );
  }
  if (careerRoleAliasesSeed.length !== Object.keys(ROLE_ALIAS_IDS).length) {
    throw new Error(
      `career_role_aliases seed count mismatch: expected ${Object.keys(ROLE_ALIAS_IDS).length}, received ${careerRoleAliasesSeed.length}`,
    );
  }

  assertNoDuplicateValues(
    skillAliasesSeed.map((skillAlias) => skillAlias.normalized_alias),
    "skill_aliases.normalized_alias",
  );
  assertNoDuplicateValues(
    careerRoleAliasesSeed.map((careerRoleAlias) => careerRoleAlias.normalized_alias),
    "career_role_aliases.normalized_alias",
  );
  assertIdsExist(
    skillAliasesSeed.map((skillAlias) => skillAlias.skill_id),
    new Set(Object.values(SKILL_IDS)),
    "skill_aliases.skill_id",
  );
  assertIdsExist(
    careerRoleAliasesSeed.map((careerRoleAlias) => careerRoleAlias.role_id),
    new Set(Object.values(ROLE_IDS)),
    "career_role_aliases.role_id",
  );
}

export async function runTaxonomySeed(): Promise<void> {
  validateTaxonomySeedData();

  const databaseUrl = process.env.DATABASE_URL;

  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required to run the taxonomy seed");
  }

  const sql = postgres(databaseUrl, { max: 1 });
  const db = drizzle(sql);

  try {
    const insertedSkills = await db
      .insert(skillsTable)
      .values(
        skillsSeed.map((skill) => ({
          id: skill.id,
          code: skill.code,
          name: skill.name,
          category: skill.category,
          isActive: skill.is_active,
          notes: skill.notes,
        })),
      )
      .onConflictDoNothing({ target: skillsTable.code })
      .returning({ id: skillsTable.id });
    console.info(`Seeded skills: ${insertedSkills.length} rows inserted`);

    const insertedCareerRoles = await db
      .insert(careerRolesTable)
      .values(
        careerRolesSeed.map((careerRole) => ({
          id: careerRole.id,
          code: careerRole.code,
          title: careerRole.title,
          description: careerRole.description,
          isActive: careerRole.is_active,
          category: careerRole.category,
        })),
      )
      .onConflictDoNothing({ target: careerRolesTable.code })
      .returning({ id: careerRolesTable.id });
    console.info(`Seeded career_roles: ${insertedCareerRoles.length} rows inserted`);

    const insertedSkillAliases = await db
      .insert(skillAliasesTable)
      .values(
        skillAliasesSeed.map((skillAlias) => ({
          id: skillAlias.id,
          code: skillAlias.code,
          skillId: skillAlias.skill_id,
          alias: skillAlias.alias,
          normalizedAlias: skillAlias.normalized_alias,
          source: skillAlias.source,
          reviewed: skillAlias.reviewed,
          notes: skillAlias.notes,
        })),
      )
      .onConflictDoNothing({ target: skillAliasesTable.alias })
      .returning({ id: skillAliasesTable.id });
    console.info(`Seeded skill_aliases: ${insertedSkillAliases.length} rows inserted`);

    const insertedCareerRoleAliases = await db
      .insert(careerRoleAliasesTable)
      .values(
        careerRoleAliasesSeed.map((careerRoleAlias) => ({
          id: careerRoleAlias.id,
          code: careerRoleAlias.code,
          roleId: careerRoleAlias.role_id,
          alias: careerRoleAlias.alias,
          normalizedAlias: careerRoleAlias.normalized_alias,
        })),
      )
      .onConflictDoNothing({ target: careerRoleAliasesTable.alias })
      .returning({ id: careerRoleAliasesTable.id });
    console.info(`Seeded career_role_aliases: ${insertedCareerRoleAliases.length} rows inserted`);
  } finally {
    await sql.end({ timeout: 5 });
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runTaxonomySeed().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
