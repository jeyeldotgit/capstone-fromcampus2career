# Spec 07 — `P1-S07-pipeline-csv-validation-and-rejections`

**Spec name**  
`P1-S07-pipeline-csv-validation-and-rejections`

**Responsibility**  
Implement CSV required-column and row-level validation with explicit rejected-row persistence and reason tracking.

**Depends on**

- `P1-S02-db-schema-pipeline-ops`
- `P1-S06-pipeline-job-orchestration`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [06-p1-s06-pipeline-job-orchestration.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/06-p1-s06-pipeline-job-orchestration.md)

**Files/artifacts produced**

- CSV validation models/rules in `apps/data-pipeline/src/ingestion`
- Rejected-row writer in `apps/data-pipeline/src/db` or `apps/data-pipeline/src/ingestion`
- Validation and rejection tests with sample invalid rows in `apps/data-pipeline/tests`

**In scope**

- Required CSV headers and basic type/quality rule validation
- Row-level rejection classification and reason message generation
- Persistence to `pipeline_rejected_rows` linked to current pipeline job

**Out of scope**

- Cleaning and normalization transformations
- Deduplication logic
- Skill mapping and output publishing
- Final `pipeline_jobs` terminal status selection
- TypeScript read-layer behavior

**Decisions already made**

- This spec owns rejected-row detection, rejected-row persistence, and rejected-row count handoff.
- The pipeline orchestrator owns the final `complete` versus `partial` terminal status decision.
- If rejected rows exist and the downstream publish succeeds, the orchestrator marks the job `partial`.
- If rejected rows exist but a fatal pipeline error prevents publish, the orchestrator marks the job `failed`.

**Implementation requirements**

- Rejection reasons must be deterministic and human-debuggable
- Invalid rows must not pass to downstream transformation stages
- Rejected-row writes must include row index and raw payload snapshot
- Validation must return or persist a rejected-row count that orchestration can use during terminal status selection

**Exit criterion (verifiable done condition)**

1. Sample CSV with malformed data yields deterministic rejected-row records.
2. Each rejected row includes a non-empty reason and valid `pipeline_job_id`.
3. Tests verify valid rows continue to downstream flow while invalid rows are blocked.
4. Job rejected count matches inserted rejected-row count.
5. Tests verify the rejected-row count is available to orchestration without requiring orchestration to inspect raw rejected-row payloads.
