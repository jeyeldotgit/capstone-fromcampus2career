import { describe, expect, test } from "vitest";
import { SkillAliasReviewActionSchema, SkillDecaySignalSchema } from "@fcc/shared";

const UUID = "10000000-0000-4000-8000-000000000001";

describe("admin readiness shared contracts", () => {
  test("accepts signed decay rates and rejects positive or non-finite values", () => {
    const baseSignal = {
      id: UUID,
      roleId: UUID,
      skillId: UUID,
      confidence: 0.9,
      detectedAt: "2026-05-01T00:00:00.000Z",
      requirementVersion: 1,
      isActive: true,
    };

    expect(SkillDecaySignalSchema.parse({ ...baseSignal, decayRate: -0.25 }).decayRate).toBe(-0.25);
    expect(SkillDecaySignalSchema.parse({ ...baseSignal, decayRate: 0 }).decayRate).toBe(0);
    expect(() => SkillDecaySignalSchema.parse({ ...baseSignal, decayRate: 0.25 })).toThrow();
    expect(() => SkillDecaySignalSchema.parse({ ...baseSignal, decayRate: -1.0001 })).toThrow();
    expect(() => SkillDecaySignalSchema.parse({ ...baseSignal, decayRate: Number.NaN })).toThrow();
  });

  test("requires skillId for alias approval but not dismissal", () => {
    expect(SkillAliasReviewActionSchema.parse({ action: "approve", skillId: UUID })).toEqual({
      action: "approve",
      skillId: UUID,
    });
    expect(SkillAliasReviewActionSchema.parse({ action: "dismiss" })).toEqual({ action: "dismiss" });
    expect(() => SkillAliasReviewActionSchema.parse({ action: "approve" })).toThrow();
    expect(() => SkillAliasReviewActionSchema.parse({ action: "dismiss", skillId: UUID })).toThrow();
  });
});
