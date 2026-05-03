# From Campus to Career

Monorepo for **From Campus to Career**, with a strict split between:

- **TypeScript product layer** (`apps/api`, `apps/admin`, `apps/mobile`)
- **Python data pipeline** (`apps/data-pipeline`)
- **Supabase Postgres contract layer** (`packages/database`)

## Architecture Boundaries

- TypeScript owns user-facing request/response behavior.
- Python owns offline ingestion, normalization, SDI, and decay computation.
- Supabase Postgres is the shared system contract.
- Required student request paths must not call Python.
- Required student request paths must not scan raw `job_postings`.
- LLM usage is optional enrichment only, never required for correctness.

## Repository Layout

```txt
apps/
  admin/           Next.js admin UI
  api/             Hono + TypeScript API
  data-pipeline/   Python offline pipeline
  mobile/          Expo mobile app (planned)
packages/
  database/        DB schema/migrations/seeds (Phase 1)
  shared/          Shared TS contracts/schemas
  api-client/      Shared API client package
docs/
  specs/           Phase work specs
```

## Prerequisites

- Node.js 20+
- pnpm 10+
- Python 3.12+
- uv (`pip install uv` or official installer)
- Supabase project with Postgres connection details

## Quick Start

1. Install dependencies:

```bash
pnpm install
```

2. Create local env files from templates:

- Root: `.env` from [.env.example](/c:/Users/BEBELABS/Documents/FromCampus2Career/.env.example)
- API: `apps/api/.env` from [apps/api/.env.example](/c:/Users/BEBELABS/Documents/FromCampus2Career/apps/api/.env.example)
- Admin: `apps/admin/.env` from [apps/admin/.env.example](/c:/Users/BEBELABS/Documents/FromCampus2Career/apps/admin/.env.example)
- Pipeline: `apps/data-pipeline/.env` from [apps/data-pipeline/.env.example](/c:/Users/BEBELABS/Documents/FromCampus2Career/apps/data-pipeline/.env.example)

3. Fill live values for:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side only)
- `DATABASE_URL`

4. Run services:

```bash
pnpm dev:api
pnpm dev:admin
pnpm dev:pipeline
```

Or run all workspace dev tasks:

```bash
pnpm dev
```

## Runtime Checks

- API health: `GET http://localhost:3001/api/v1/health`
- Pipeline sanity run:

```bash
pnpm --filter @fcc/data-pipeline dev
```

## Phase 1 Spec Pack

Phase 1 work is decomposed into focused, executable specs under [docs/specs](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs).

Execution order starts with:

- [00-p1-s00-db-environment-bootstrap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/00-p1-s00-db-environment-bootstrap.md)
- [01-p1-s01-db-schema-taxonomy.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/01-p1-s01-db-schema-taxonomy.md)
- ...through `S13`

`S00` is the explicit live DB bootstrap stage:

- Supabase project or target DB setup
- env wiring for API and pipeline
- connection verification
- migration runner setup

## Current Status

- API and pipeline scaffolding are in place.
- Database package is currently minimal and will be expanded through Phase 1 specs.
- Root `.gitignore` may include local environment and tooling exclusions.

## Notes

- Do not commit secrets.
- Do not use service-role credentials in client-facing code.
- Keep schema, contracts, and tests updated together for boundary changes.
