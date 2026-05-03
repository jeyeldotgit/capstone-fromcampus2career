# Database Bootstrap and Migration Runbook

Spec: `P1-S00-db-environment-bootstrap`

This runbook provisions (or selects) a live Supabase database target, wires runtime environment variables for both TypeScript and Python, verifies both runtimes point to the same database, and documents safe migration execution.

## Scope Guardrails

- This spec does not introduce new schema or seed data.
- The only migration referenced for validation is the already-existing `P1-S01` SQL file.
- Never commit real credentials.

## Prerequisites

- Supabase project access (owner/admin or credentials from an owner).
- `pnpm` installed.
- `uv` installed.
- `node` 20.6+ (for `--env-file`).
- `psql` installed and on `PATH`.

Quick checks:

```powershell
pnpm --version
uv --version
node --version
psql --version
```

## 1) Acquire Supabase Credentials

From Supabase Dashboard for a single target project:

1. `SUPABASE_URL`:
- Project Settings -> API -> Project URL
2. `SUPABASE_SERVICE_ROLE_KEY`:
- Project Settings -> API -> `service_role` key (server-side only)
3. `DATABASE_URL`:
- Project -> Connect -> Postgres connection string
- Use a single connection mode consistently for both runtimes.

Required rule:

- `apps/api/.env` and `apps/data-pipeline/.env` must use the same database target (same host and database name).

## 2) Create Local Env Files (Never Commit)

From repository root:

```powershell
Copy-Item .env.example .env
Copy-Item apps/api/.env.example apps/api/.env
Copy-Item apps/data-pipeline/.env.example apps/data-pipeline/.env
```

Fill live values in:

- `.env` (shared defaults as needed)
- `apps/api/.env`
- `apps/data-pipeline/.env`

Do not stage these files.

## 3) Preflight Safety Checks

1. Ensure placeholders were replaced:

```powershell
rg -n "placeholder|your-project-ref|YOUR_DB_PASSWORD|example\.supabase" apps/api/.env apps/data-pipeline/.env
```

Expected: no matches.

2. Ensure Git is not staging secrets:

```powershell
git status --short
```

Expected: no `.env` files listed under staged changes.

## 4) Verify TypeScript Runtime (API)

### 4.1 Build + health check

```powershell
pnpm --filter @fcc/api build
```

Start API in one terminal:

```powershell
pnpm --filter @fcc/api start
```

Health check in another terminal:

```powershell
Invoke-RestMethod http://localhost:3001/api/v1/health
```

Expected response includes:

- `message: hello world`
- `service: api`

### 4.2 TypeScript-side SQL probe (using API env)

```powershell
$apiDbUrl = node --env-file=apps/api/.env -p "process.env.DATABASE_URL"
psql $apiDbUrl --set ON_ERROR_STOP=1 --tuples-only --no-align --command "select current_database(), inet_server_addr(), inet_server_port();"
```

Expected: one row with database name and server address details.

## 5) Verify Python Runtime (Pipeline)

Run from `apps/data-pipeline`:

```powershell
Set-Location apps/data-pipeline
```

### 5.1 Settings load check

```powershell
uv run python -c "from src.config.settings import settings; print(f'python_env={settings.python_env}'); print(f'supabase_url={settings.supabase_url}')"
```

Expected: prints configured environment and Supabase URL (not placeholders).

### 5.2 DB connectivity check through Python runtime

```powershell
uv run python -c "import subprocess; from src.config.settings import settings; result = subprocess.run(['psql', settings.database_url, '--set', 'ON_ERROR_STOP=1', '--tuples-only', '--no-align', '--command', 'select current_database(), inet_server_addr(), inet_server_port();'], check=True, capture_output=True, text=True); print(result.stdout.strip())"
```

Expected: one row with database name and server address details.

## 6) Confirm Both Runtimes Target the Same Database

Compare host and database from both env files:

```powershell
$apiDbUrl = node --env-file=apps/api/.env -p "process.env.DATABASE_URL"
$pipeDbUrl = node --env-file=apps/data-pipeline/.env -p "process.env.DATABASE_URL"

$api = [System.Uri]$apiDbUrl
$pipe = [System.Uri]$pipeDbUrl

"api_host=$($api.Host); api_db=$($api.AbsolutePath.TrimStart('/'))"
"pipeline_host=$($pipe.Host); pipeline_db=$($pipe.AbsolutePath.TrimStart('/'))"
```

Expected:

- `api_host == pipeline_host`
- `api_db == pipeline_db`

## 7) Migration Execution Paths

Migration file for bootstrap validation:

- `packages/database/migrations/20260503143000_p1_s01_taxonomy_schema.sql`

### 7.1 Local/Fresh path (disposable or reset-safe target)

Use only on a disposable database or an explicitly reset-safe environment.

```powershell
$apiDbUrl = node --env-file=apps/api/.env -p "process.env.DATABASE_URL"
psql $apiDbUrl --set ON_ERROR_STOP=1 --single-transaction --file packages/database/migrations/20260503143000_p1_s01_taxonomy_schema.sql
```

Post-apply verification:

```powershell
psql $apiDbUrl --set ON_ERROR_STOP=1 --tuples-only --no-align --command "select table_name from information_schema.tables where table_schema='public' and table_name in ('skills','skill_aliases','career_roles','career_role_aliases','courses','course_skills','market_datasets') order by table_name;"
```

Expected: 7 table names returned.

### 7.2 Live path (forward-only)

Use when the target DB is a shared/live Supabase environment.

Rules:

- Do not drop schema or run destructive reset commands.
- Apply only reviewed SQL migration files.
- Keep `ON_ERROR_STOP=1` enabled.

Apply:

```powershell
$apiDbUrl = node --env-file=apps/api/.env -p "process.env.DATABASE_URL"
psql $apiDbUrl --set ON_ERROR_STOP=1 --single-transaction --file packages/database/migrations/20260503143000_p1_s01_taxonomy_schema.sql
```

If migration was previously applied, review first before re-running.

## 8) Rollback and Safety Notes

Before applying any migration to live/shared DB:

1. Take a backup/snapshot (for example `pg_dump`) and record when it was taken.
2. Confirm target environment and project ref with another engineer.
3. Run with `ON_ERROR_STOP=1` and `--single-transaction` where compatible.
4. If migration fails:
- Stop immediately.
- Do not patch data manually in production.
- Restore from backup if needed, or ship a corrective migration in version control.

## 9) Troubleshooting

- `psql not recognized`:
- Install PostgreSQL client tools and ensure `psql` is on `PATH`.
- API health endpoint not reachable:
- Confirm API is running on port `3001` and `API_BASE_PATH=/api/v1`.
- Placeholder values detected:
- Replace placeholders in both runtime `.env` files before verifying connectivity.
- Target mismatch between API and pipeline:
- Re-check both `DATABASE_URL` values and ensure same host/database.

## 10) Exit Checklist

- [ ] Supabase project selected/provisioned and credentials acquired securely.
- [ ] Local `.env` files created from templates; no credentials staged.
- [ ] API runtime passes health check.
- [ ] Python runtime loads settings and performs DB probe.
- [ ] API and pipeline confirm same database target.
- [ ] Migration command path validated with local/fresh vs live distinction documented.
- [ ] Rollback safety notes reviewed before live execution.
