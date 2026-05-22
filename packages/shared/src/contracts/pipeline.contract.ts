import { z } from "zod";

const IsoDateTimeSchema = z.string().refine((value) => !Number.isNaN(Date.parse(value)), {
  message: "Expected an ISO datetime string",
});

const IsoDateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, {
  message: "Expected an ISO date string",
});

const PostgresUuidSchema = z.string().regex(
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/,
  {
    message: "Expected a Postgres UUID string",
  },
);

export const RoleRequirementVersionSchema = z.object({
  id: PostgresUuidSchema,
  version: z.number().int().positive(),
  datasetId: PostgresUuidSchema,
  computedAt: IsoDateTimeSchema,
  isCurrent: z.boolean(),
});

export type RoleRequirementVersion = z.infer<typeof RoleRequirementVersionSchema>;

export const RoleSkillRequirementSchema = z.object({
  id: PostgresUuidSchema,
  roleId: PostgresUuidSchema,
  skillId: PostgresUuidSchema,
  requirementVersion: z.number().int().positive(),
  requiredDepth: z.number().min(0).max(1),
  demandWeight: z.number().min(0.1).max(1),
  evidenceCount: z.number().int().nonnegative(),
});

export type RoleSkillRequirement = z.infer<typeof RoleSkillRequirementSchema>;

export const SdiSnapshotSchema = z.object({
  id: PostgresUuidSchema,
  roleId: PostgresUuidSchema,
  skillId: PostgresUuidSchema,
  demandIndex: z.number().min(0).max(1),
  snapshotDate: IsoDateSchema,
  requirementVersion: z.number().int().positive(),
});

export type SdiSnapshot = z.infer<typeof SdiSnapshotSchema>;

export const SkillDecaySignalSchema = z.object({
  id: PostgresUuidSchema,
  roleId: PostgresUuidSchema,
  skillId: PostgresUuidSchema,
  decayRate: z.number().finite(),
  confidence: z.number().min(0).max(1),
  detectedAt: IsoDateTimeSchema,
  requirementVersion: z.number().int().positive(),
  isActive: z.boolean(),
});

export type SkillDecaySignal = z.infer<typeof SkillDecaySignalSchema>;
