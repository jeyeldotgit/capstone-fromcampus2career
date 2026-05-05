import { describe, expect, test } from "vitest";
import { careerRoleAliasesSeed } from "../taxonomy/career-role-aliases.seed.ts";
import { careerRolesSeed } from "../taxonomy/career-roles.seed.ts";
import { ROLE_ALIAS_IDS, ROLE_IDS, SKILL_ALIAS_IDS, SKILL_IDS } from "../taxonomy/id-maps.ts";
import { skillAliasesSeed } from "../taxonomy/skill-aliases.seed.ts";
import { skillsSeed } from "../taxonomy/skills.seed.ts";

function normalizeAlias(alias: string): string {
  return alias.toLowerCase().trim().replace(/\s+/g, " ");
}

function findDuplicates(values: string[]): string[] {
  const counts = new Map<string, number>();

  for (const value of values) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }

  return [...counts.entries()]
    .filter(([, count]) => count > 1)
    .map(([value]) => value)
    .sort((left, right) => left.localeCompare(right));
}

describe("taxonomy seed unit checks", () => {
  test("matches expected record counts", () => {
    expect(skillsSeed).toHaveLength(133);
    expect(skillAliasesSeed).toHaveLength(152);
    expect(careerRolesSeed).toHaveLength(40);
    expect(careerRoleAliasesSeed).toHaveLength(126);
  });

  test("uses globally unique UUIDs across all four maps", () => {
    const allIds = [
      ...Object.values(SKILL_IDS),
      ...Object.values(SKILL_ALIAS_IDS),
      ...Object.values(ROLE_IDS),
      ...Object.values(ROLE_ALIAS_IDS),
    ];

    expect(new Set(allIds).size).toBe(allIds.length);
    expect(allIds).toHaveLength(451);
  });

  test("keeps code values unique within each dataset", () => {
    expect(new Set(skillsSeed.map((skill) => skill.code)).size).toBe(skillsSeed.length);
    expect(new Set(skillAliasesSeed.map((skillAlias) => skillAlias.code)).size).toBe(
      skillAliasesSeed.length,
    );
    expect(new Set(careerRolesSeed.map((careerRole) => careerRole.code)).size).toBe(
      careerRolesSeed.length,
    );
    expect(
      new Set(careerRoleAliasesSeed.map((careerRoleAlias) => careerRoleAlias.code)).size,
    ).toBe(careerRoleAliasesSeed.length);
  });

  test("computes every skill alias normalized_alias with the required formula", () => {
    expect(
      skillAliasesSeed.every(
        (skillAlias) => skillAlias.normalized_alias === normalizeAlias(skillAlias.alias),
      ),
    ).toBe(true);
  });

  test("does not duplicate normalized skill alias values", () => {
    expect(findDuplicates(skillAliasesSeed.map((skillAlias) => skillAlias.normalized_alias))).toEqual(
      [],
    );
  });

  test("does not duplicate normalized career role alias values", () => {
    expect(
      findDuplicates(
        careerRoleAliasesSeed.map((careerRoleAlias) => careerRoleAlias.normalized_alias),
      ),
    ).toEqual([]);
  });

  test("strips notes from every career role alias row", () => {
    expect(
      careerRoleAliasesSeed.every(
        (careerRoleAlias) => !Object.prototype.hasOwnProperty.call(careerRoleAlias, "notes"),
      ),
    ).toBe(true);
  });

  test("resolves every skill_alias.skill_id to a UUID from SKILL_IDS", () => {
    const skillIds = new Set(Object.values(SKILL_IDS));

    expect(skillAliasesSeed.every((skillAlias) => skillIds.has(skillAlias.skill_id))).toBe(true);
  });

  test("resolves every career_role_alias.role_id to a UUID from ROLE_IDS", () => {
    const roleIds = new Set(Object.values(ROLE_IDS));

    expect(careerRoleAliasesSeed.every((careerRoleAlias) => roleIds.has(careerRoleAlias.role_id))).toBe(
      true,
    );
  });
});
