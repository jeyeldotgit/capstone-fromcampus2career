import { readFileSync } from "node:fs";
import type { Sql } from "postgres";

const ADMIN_READINESS_MIGRATION_SQL = readFileSync(
  new URL(
    "../../../../../packages/database/migrations/20260526120000_admin_readiness_contract_patch.sql",
    import.meta.url,
  ),
  "utf8",
);

export async function applyAdminReadinessContractPatchIfNeeded(
  sql: Sql | null,
): Promise<void> {
  if (sql === null) {
    return;
  }

  await sql`select pg_advisory_lock(20260526120000)`;

  try {
    const [row] = await sql<{ exists: boolean }[]>`
      select exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'market_datasets'
          and column_name = 'source_url'
      ) as exists
    `;

    if (!row.exists) {
      await sql.unsafe(ADMIN_READINESS_MIGRATION_SQL);
    }
  } finally {
    await sql`select pg_advisory_unlock(20260526120000)`;
  }
}
