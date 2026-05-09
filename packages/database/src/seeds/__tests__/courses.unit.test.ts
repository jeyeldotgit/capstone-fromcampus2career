import { createHash } from "node:crypto";
import { describe, expect, test } from "vitest";
import {
  COURSE_SKILL_ID_NAMESPACE,
  COURSE_SKILLS,
} from "../courses/course-skills.seed.ts";
import { COURSES } from "../courses/courses.seed.ts";
import { SKILL_IDS } from "../taxonomy/id-maps.ts";

const ALLOWED_DEPTH_WEIGHTS = new Set(["0.25", "0.50", "0.75", "1.00"]);
const INACTIVE_SKILL_CODES = ["SK010", "SK012", "SK014", "SK036", "SK092", "SK099"] as const;

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

function parseUuid(uuid: string): Buffer {
  return Buffer.from(uuid.replaceAll("-", ""), "hex");
}

function stringifyUuid(bytes: Buffer): string {
  const hex = bytes.toString("hex");
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20, 32),
  ].join("-");
}

function uuidV5(name: string, namespace: string): string {
  const hash = createHash("sha1").update(parseUuid(namespace)).update(name, "utf8").digest();
  const bytes = Buffer.from(hash.subarray(0, 16));

  bytes[6] = (bytes[6] & 0x0f) | 0x50;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  return stringifyUuid(bytes);
}

describe("courses seed unit checks", () => {
  test("exports exactly 35 course rows", () => {
    expect(COURSES).toHaveLength(35);
  });

  test("exports exactly 155 course skill rows", () => {
    expect(COURSE_SKILLS).toHaveLength(155);
  });

  test("resolves every course_skills.skill_id to a UUID from SKILL_IDS", () => {
    const skillIds = new Set(Object.values(SKILL_IDS));

    expect(COURSE_SKILLS.every((courseSkill) => skillIds.has(courseSkill.skill_id))).toBe(true);
  });

  test("does not reference inactive skills", () => {
    const inactiveSkillIds = new Set(INACTIVE_SKILL_CODES.map((code) => SKILL_IDS[code]));

    expect(COURSE_SKILLS.every((courseSkill) => !inactiveSkillIds.has(courseSkill.skill_id))).toBe(
      true,
    );
  });

  test("does not duplicate course and skill pairs", () => {
    expect(
      findDuplicates(
        COURSE_SKILLS.map((courseSkill) => `${courseSkill.course_id}:${courseSkill.skill_id}`),
      ),
    ).toEqual([]);
  });

  test("uses only approved depth_weight values", () => {
    expect(COURSE_SKILLS.every((courseSkill) => ALLOWED_DEPTH_WEIGHTS.has(courseSkill.depth_weight))).toBe(
      true,
    );
  });

  test("uses unique course_skills IDs", () => {
    expect(new Set(COURSE_SKILLS.map((courseSkill) => courseSkill.id)).size).toBe(
      COURSE_SKILLS.length,
    );
  });

  test("generates stable course_skills IDs from course_id and skill_id", () => {
    expect(
      COURSE_SKILLS.every(
        (courseSkill) =>
          courseSkill.id ===
          uuidV5(`${courseSkill.course_id}:${courseSkill.skill_id}`, COURSE_SKILL_ID_NAMESPACE),
      ),
    ).toBe(true);
  });

  test("keeps GE101 intentionally unmapped", () => {
    const ge101 = COURSES.find((course) => course.code === "GE101");

    expect(ge101).toBeDefined();
    expect(COURSE_SKILLS.filter((courseSkill) => courseSkill.course_id === ge101?.id)).toHaveLength(
      0,
    );
  });
});
