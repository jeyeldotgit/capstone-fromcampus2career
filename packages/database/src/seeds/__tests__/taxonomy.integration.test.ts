import { readFileSync } from "node:fs";
import postgres from "postgres";
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { runTaxonomySeed } from "../run-taxonomy.ts";

const DATABASE_URL = process.env.DATABASE_URL;

const TAXONOMY_MIGRATION_SQL = readFileSync(
  new URL("../../../migrations/20260503143000_p1_s01_taxonomy_schema.sql", import.meta.url),
  "utf8",
);

const TAXONOMY_PATCH_MIGRATION_SQL = readFileSync(
  new URL("../../../migrations/20260505120000_p1_s01b_taxonomy_schema_patch.sql", import.meta.url),
  "utf8",
);

const suite = DATABASE_URL ? describe : describe.skip;

suite("taxonomy seed integration", () => {
  const sql = postgres(DATABASE_URL as string, { max: 1 });

  async function tableExists(tableName: string): Promise<boolean> {
    const rows = await sql<{ exists: boolean }[]>`
      select exists (
        select 1
        from information_schema.tables
        where table_schema = 'public'
          and table_name = ${tableName}
      ) as exists;
    `;

    return rows[0]?.exists ?? false;
  }

  async function fetchCount(tableName: string): Promise<number> {
    const rows = await sql<{ count: string }[]>`select count(*)::text as count from ${sql(tableName)}`;
    return Number(rows[0]?.count ?? "0");
  }

  beforeAll(async () => {
    if (!(await tableExists("skills"))) {
      await sql.unsafe(TAXONOMY_MIGRATION_SQL);
    }

    await sql.unsafe(TAXONOMY_PATCH_MIGRATION_SQL);

    await sql.unsafe(`
      delete from career_role_aliases;
      delete from skill_aliases;
      delete from career_roles;
      delete from skills;
    `);
  });

  afterAll(async () => {
    await sql.end({ timeout: 5 });
  });

  test("seeds the expected row counts on first run", async () => {
    await runTaxonomySeed();

    await expect(fetchCount("skills")).resolves.toBe(133);
    await expect(fetchCount("skill_aliases")).resolves.toBe(152);
    await expect(fetchCount("career_roles")).resolves.toBe(40);
    await expect(fetchCount("career_role_aliases")).resolves.toBe(126);
  });

  test("keeps row counts unchanged on a second run", async () => {
    await runTaxonomySeed();

    await expect(fetchCount("skills")).resolves.toBe(133);
    await expect(fetchCount("skill_aliases")).resolves.toBe(152);
    await expect(fetchCount("career_roles")).resolves.toBe(40);
    await expect(fetchCount("career_role_aliases")).resolves.toBe(126);
  });

  test("queries a seeded skill by code", async () => {
    const rows = await sql<{ name: string }[]>`
      select name
      from skills
      where code = 'SK001';
    `;

    expect(rows[0]?.name).toBe("Python");
  });

  test("resolves a seeded career role alias to its parent role title", async () => {
    const rows = await sql<{ title: string }[]>`
      select cr.title
      from career_role_aliases cra
      join career_roles cr on cr.id = cra.role_id
      where cra.code = 'RA001';
    `;

    expect(rows[0]?.title).toBe("Software Developer");
  });
});
