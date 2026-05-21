import { drizzle, type PostgresJsDatabase } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { env } from "../env.js";

export type RepositoryDatabase = Pick<PostgresJsDatabase<Record<string, never>>, "select">;

let defaultClient: postgres.Sql | null = null;
let defaultDatabase: PostgresJsDatabase<Record<string, never>> | null = null;
let testDatabase: RepositoryDatabase | null = null;

export function getRepositoryDatabase(): RepositoryDatabase {
  if (testDatabase !== null) {
    return testDatabase;
  }

  if (defaultDatabase === null) {
    defaultClient = postgres(env.DATABASE_URL, { max: 1 });
    defaultDatabase = drizzle(defaultClient);
  }

  return defaultDatabase;
}

export function setRepositoryDatabaseForTests(database: RepositoryDatabase | null): void {
  testDatabase = database;
}
