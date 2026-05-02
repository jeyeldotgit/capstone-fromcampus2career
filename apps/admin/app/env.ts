import { z } from "zod";

const PublicEnvSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.string().url().default("http://localhost:3001/api/v1"),
  NEXT_PUBLIC_APP_NAME: z.string().min(1).default("From Campus to Career Admin"),
});

export const publicEnv = PublicEnvSchema.parse({
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
});
