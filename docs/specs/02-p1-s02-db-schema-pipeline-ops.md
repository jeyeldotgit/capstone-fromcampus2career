# Spec 02 — `P1-S02-db-schema-pipeline-ops`

**Spec name**  
`P1-S02-db-schema-pipeline-ops`

**Responsibility**  
Define the pipeline operational schema used to track ingestion job lifecycle, counters, rejected-row diagnostics, and durable app-event outbox records.

**Depends on**

- `P1-S01-db-schema-taxonomy`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [01-p1-s01-db-schema-taxonomy.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/01-p1-s01-db-schema-taxonomy.md)

**Files/artifacts produced**

- Drizzle schema updates for `pipeline_jobs`, `pipeline_rejected_rows`, and `app_events` in `packages/database/src`
- SQL migration file(s) in `packages/database` migrations path
- Table-integrity tests for job status transitions, rejected-row foreign keys, and app-event outbox defaults
- Pipeline-ops migration notes in `packages/database` documentation

**In scope**

- Pipeline ops table definitions, keys, constraints, and indexes
- Column shape for job status, row counters, output version, and error metadata
- FK relationship from rejected rows to pipeline jobs
- `app_events` outbox table shape for durable internal workflow events
- Job status vocabulary: `pending`, `running`, `complete`, `failed`, `partial`

**Out of scope**

- Taxonomy schema changes
- Prepared intelligence schema
- Seed data files
- Python processing logic
- TypeScript read services

**Implementation requirements**

- Keep `pipeline_jobs` compatible with deterministic state transitions
- Ensure rejected rows can be traced to a single pipeline job
- Ensure app events can be traced to an aggregate type and aggregate id
- Add constraints that prevent null-critical lifecycle fields where required

**Exit criterion (verifiable done condition)**

1. Migration creates pipeline operational and app-event outbox tables with expected constraints.
2. Tests verify a rejected row cannot exist without a valid `pipeline_job_id`.
3. Tests verify job counters and status fields can be updated through expected lifecycle steps.
4. Tests verify `app_events` defaults new events to `pending` with a required `event_type`, `aggregate_type`, payload, and `available_at`.
5. No prepared-output, seed, or API-layer changes are introduced.
