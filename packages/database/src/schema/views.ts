import { boolean, date, integer, numeric, pgView, timestamp, uuid } from "drizzle-orm/pg-core";

export const currentMonthlyRoleSkillRequirements = pgView("v_current_monthly_role_skill_requirements", {
  id: uuid("id"),
  roleId: uuid("role_id"),
  skillId: uuid("skill_id"),
  requirementVersion: integer("requirement_version"),
  requiredDepth: numeric("required_depth", { precision: 5, scale: 4 }),
  demandWeight: numeric("demand_weight", { precision: 5, scale: 4 }),
  evidenceCount: integer("evidence_count"),
  periodMonth: date("period_month", { mode: "string" }),
  periodRevision: integer("period_revision"),
  triggeringDatasetId: uuid("triggering_dataset_id"),
  computedAt: timestamp("computed_at", { withTimezone: true }),
}).existing();

export const currentMonthlySdiSnapshots = pgView("v_current_monthly_sdi_snapshots", {
  id: uuid("id"),
  roleId: uuid("role_id"),
  skillId: uuid("skill_id"),
  demandIndex: numeric("demand_index", { precision: 5, scale: 4 }),
  snapshotDate: date("snapshot_date", { mode: "string" }),
  requirementVersion: integer("requirement_version"),
  periodMonth: date("period_month", { mode: "string" }),
  periodRevision: integer("period_revision"),
  triggeringDatasetId: uuid("triggering_dataset_id"),
  computedAt: timestamp("computed_at", { withTimezone: true }),
}).existing();

export const currentMonthlySkillDecaySignals = pgView("v_current_monthly_skill_decay_signals", {
  id: uuid("id"),
  roleId: uuid("role_id"),
  skillId: uuid("skill_id"),
  decayRate: numeric("decay_rate", { precision: 5, scale: 4 }),
  confidence: numeric("confidence", { precision: 5, scale: 4 }),
  detectedAt: timestamp("detected_at", { withTimezone: true }),
  requirementVersion: integer("requirement_version"),
  isActive: boolean("is_active"),
  periodMonth: date("period_month", { mode: "string" }),
  periodRevision: integer("period_revision"),
  triggeringDatasetId: uuid("triggering_dataset_id"),
  computedAt: timestamp("computed_at", { withTimezone: true }),
}).existing();

export type CurrentMonthlyRoleSkillRequirement = typeof currentMonthlyRoleSkillRequirements.$inferSelect;
export type CurrentMonthlySdiSnapshot = typeof currentMonthlySdiSnapshots.$inferSelect;
export type CurrentMonthlySkillDecaySignal = typeof currentMonthlySkillDecaySignals.$inferSelect;
