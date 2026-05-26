import { z } from "zod";

const PostgresUuidSchema = z.string().regex(
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/,
  {
    message: "Expected a Postgres UUID string",
  },
);

export const SkillAliasReviewActionSchema = z.discriminatedUnion("action", [
  z.object({
    action: z.literal("approve"),
    skillId: PostgresUuidSchema,
  }).strict(),
  z.object({
    action: z.literal("dismiss"),
  }).strict(),
]);

export type SkillAliasReviewAction = z.infer<typeof SkillAliasReviewActionSchema>;
