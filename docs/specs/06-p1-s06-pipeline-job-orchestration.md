# Spec 06 — `P1-S06-pipeline-job-orchestration`

**Spec name**  
`P1-S06-pipeline-job-orchestration`

**Responsibility**  
Implement Python pipeline orchestration that creates and manages ingestion job lifecycle state from start through terminal status.

**Depends on**

- `P1-S02-db-schema-pipeline-ops`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [02-p1-s02-db-schema-pipeline-ops.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/02-p1-s02-db-schema-pipeline-ops.md)

**Files/artifacts produced**

- Pipeline entrypoint/orchestration updates in `apps/data-pipeline/src/main.py` and orchestration modules
- DB write helpers for pipeline job creation and lifecycle updates in `apps/data-pipeline/src/db`
- Unit tests for status transitions and counter updates

**In scope**

- Job creation, start timestamps, completion timestamps, and terminal status handling
- Processed/rejected row counter updates at orchestration level
- Structured error capture into `pipeline_jobs.error_message`

**Out of scope**

- CSV row validation rules
- Cleaning, normalization, deduplication, and skill mapping
- Prepared output table publishing
- TypeScript consumer logic

**Implementation requirements**

- Lifecycle transitions must be deterministic and idempotent for a single job run
- Failure path must reliably set failed status and persist an error summary
- Orchestrator must not embed business logic for later pipeline stages

**Exit criterion (verifiable done condition)**

1. A pipeline run creates a `pipeline_jobs` record and marks it `running`.
2. Successful completion marks job `succeeded` with finished timestamp and counters.
3. Simulated failure marks job `failed` and writes an error message.
4. Tests cover at least one success and one failure lifecycle path.
