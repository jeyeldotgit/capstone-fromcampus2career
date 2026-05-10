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
- DB write helpers for terminal `app_events` emission
- Unit tests for status transitions, counter updates, output-version handoff, and terminal event emission

**In scope**

- Job creation, start timestamps, completion timestamps, and terminal status handling
- Processed/rejected row counter updates at orchestration level
- Completion handoff that accepts the publishing stage's `output_version`
- Terminal event emission to `app_events`
- Structured error capture into `pipeline_jobs.error_message`

**Out of scope**

- CSV row validation rules
- Cleaning, normalization, deduplication, and skill mapping
- Prepared output table publishing
- TypeScript consumer logic
- Admin realtime notification delivery

**Decisions already made**

- The orchestrator owns final job status selection.
- Terminal status is `complete` when the run publishes successfully with `rejected_rows = 0`.
- Terminal status is `partial` when the run publishes successfully with `rejected_rows > 0`.
- Terminal status is `failed` when the run has a fatal error and does not successfully publish a new output version.
- CSV validation owns rejected-row classification and persistence, but the orchestrator consumes the final rejected-row count and decides whether the terminal status is `complete` or `partial`.
- Publishing owns creation of the role requirement version and returns the produced `output_version` to the orchestrator.
- The orchestrator writes `pipeline_jobs.output_version` before marking the job `complete` or `partial`.
- Python emits `pipeline.ingestion.completed` for both `complete` and `partial` terminal states, with the final status and `output_version` in the event payload.
- Python emits `pipeline.ingestion.failed` for fatal failures after persisting the failed job state.

**Implementation requirements**

- Lifecycle transitions must be deterministic and idempotent for a single job run
- Completion must accept `processed_rows`, `rejected_rows`, and non-null `output_version`
- Completion must persist `output_version`, counters, terminal status, and `finished_at` in the job lifecycle update
- Failure path must reliably set failed status and persist an error summary
- Failure path must leave `output_version` null unless a previously committed publish can be safely and explicitly reconciled
- Terminal `app_events` writes must be idempotent for retries of the same pipeline job and event type
- Orchestrator must not embed business logic for later pipeline stages

**Exit criterion (verifiable done condition)**

1. A pipeline run creates a `pipeline_jobs` record and marks it `running`.
2. Successful completion with zero rejected rows marks job `complete` with finished timestamp, counters, and `output_version`.
3. Successful completion with rejected rows marks job `partial` with finished timestamp, counters, and `output_version`.
4. Simulated failure marks job `failed`, writes an error message, and does not require `output_version`.
5. Tests cover success, partial, and failure lifecycle paths.
6. Tests verify `pipeline.ingestion.completed` and `pipeline.ingestion.failed` events are emitted with the expected aggregate id and payload.
