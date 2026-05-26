# Database Bootstrap and Migration Runbook

Spec: `P1-S00-db-environment-bootstrap`

This runbook provisions (or selects) a live Supabase database target, wires runtime environment variables for both TypeScript and Python, verifies both runtimes point to the same database, and documents safe migration execution.

## Migration Authoring and Apply Model

- Database schema source lives in Drizzle ORM table definitions under `packages/database/src/schema`.
- Migration SQL files are generated from schema changes using Drizzle Kit.
- Generated SQL files in `packages/database/migrations` are the deploy artifact and must be committed.
- Shared/live environments apply committed SQL files via `psql` with forward-only migration discipline.

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

## P1-S02 Pipeline Ops Migration Note

- Migration file: `packages/database/migrations/20260504100000_p1_s02_pipeline_ops.sql`
- Depends on: `20260503143000_p1_s01_taxonomy_schema.sql`
- Adds:
  - `pipeline_jobs` for ingestion job lifecycle state, counters, output version, and error summaries
  - `pipeline_rejected_rows` for row-level rejection diagnostics linked to a parent pipeline job
- Key integrity rules:
  - `pipeline_jobs.status` is constrained to `pending`, `running`, `complete`, `failed`, or `partial`
  - `pipeline_jobs.started_at`, `status`, and `created_at` are non-null
  - `pipeline_rejected_rows.pipeline_job_id` is required and FK-enforced
  - rejected rows are unique per `pipeline_job_id + row_number`
- Safe apply rule:
  - apply only after P1-S01 tables already exist because `pipeline_jobs.dataset_id` references `market_datasets(id)`

## P1-S03 Prepared Intelligence Migration Note

- Migration file: `packages/database/migrations/20260504110000_p1_s03_prepared_intelligence.sql`
- Depends on: `20260503143000_p1_s01_taxonomy_schema.sql`
- Adds:
  - `role_requirement_versions` for immutable published requirement-version headers linked to `market_datasets`
  - `role_skill_requirements` for per-role, per-skill published requirement rows keyed by integer `requirement_version`
  - `sdi_snapshots` for per-role, per-skill SDI snapshots keyed by `snapshot_date`
  - `skill_decay_signals` for per-role, per-skill decay metadata with `is_active` state
- Key integrity rules:
  - `role_requirement_versions.version` is unique and must be greater than `0`
  - `role_skill_requirements` is unique per `role_id + skill_id + requirement_version`
  - `sdi_snapshots` is unique per `role_id + skill_id + snapshot_date`
  - `skill_decay_signals` is unique per `role_id + skill_id + requirement_version`
  - numeric publish checks enforce `required_depth`, `demand_weight`, `demand_index`, `decay_rate`, and `confidence` ranges
  - `role_skill_requirements.evidence_count` keeps the LLD default of `0`, but published rows must satisfy `evidence_count >= 5`
- Versioning note:
  - child-table `requirement_version` columns are stored as plain integers with no FK to `role_requirement_versions(version)` to match the current LLD contract
  - `role_requirement_versions` intentionally omits `is_current`; latest-version reads should use `ORDER BY version DESC LIMIT 1`
- Safe apply rule:
  - apply only after P1-S01 tables already exist because the prepared-intelligence tables reference `market_datasets`, `career_roles`, and `skills`

## P1-S02-BJ App Events Backjob Migration Note

- Migration file: `packages/database/migrations/20260510130000_add_app_events.sql`
- Depends on: `20260504100000_p1_s02_pipeline_ops.sql`
- Why this is a backjob:
  - the original P1-S02 pipeline-ops merge added `pipeline_jobs` and `pipeline_rejected_rows`, but the MVP durable `app_events` outbox artifact was still missing
- Adds:
  - `app_events` for durable internal workflow events emitted by the TypeScript API and Python pipeline
  - `app_events_status_available_at_idx` for outbox polling by status and availability time
  - `app_events_aggregate_type_aggregate_id_idx` for aggregate-scoped event lookup
- Key integrity rules:
  - `app_events.status` is constrained to `pending`, `processing`, `processed`, or `failed`
  - `event_type`, `aggregate_type`, `payload`, `status`, `available_at`, and `created_at` are non-null
  - `status`, `available_at`, and `created_at` use database defaults for new events
  - `aggregate_id`, `processed_at`, and `error_message` remain nullable for system-level events and pending work
- Status vocabulary note:
  - `app_events` uses outbox-processing states: `pending`, `processing`, `processed`, `failed`
  - `pipeline_jobs` keeps ingestion lifecycle states: `pending`, `running`, `complete`, `failed`, `partial`
- Safe apply rule:
  - apply after P1-S02 so pipeline operational schema exists before dependent event-emission work is added

## P1-S16 Admin Readiness Contract Patch Migration Note

- Migration file: `packages/database/migrations/20260526120000_admin_readiness_contract_patch.sql`
- Depends on: `20260523120000_monthly_versioning_and_lineage.sql`
- Adds:
  - `career_role_aliases.reviewed` for admin-confirmed role alias state
  - `market_datasets.source_url` for optional dataset provenance metadata
- Changes:
  - drops `skill_aliases_reviewed_requires_skill_id_chk` so reviewed aliases can be dismissed without a canonical skill
  - converts existing positive `skill_decay_signals.decay_rate` values to signed negative slopes
  - replaces the decay-rate range check with `decay_rate >= -1 and decay_rate <= 0`
- Safe apply rule:
  - apply after P1-S15 because the patch expects versioned prepared-intelligence tables to exist
