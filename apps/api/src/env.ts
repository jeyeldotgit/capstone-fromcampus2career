import { z } from "zod";
import dotenv from "dotenv";

dotenv.config();

const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  API_PORT: z.coerce.number().int().positive().default(3001),
  API_BASE_PATH: z.string().min(1).default("/api/v1"),
  SUPABASE_URL: z.string().url().default("https://example.supabase.co"),
  SUPABASE_ANON_KEY: z.string().default("placeholder-anon-key"),
  SUPABASE_SERVICE_ROLE_KEY: z.string().default("placeholder-service-role-key"),
  DATABASE_URL: z.string().default("postgresql://user:pass@localhost:5432/fcc"),
  REDIS_URL: z.string().default("https://example.upstash.io"),
});

export const env = EnvSchema.parse(process.env);
