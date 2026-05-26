# Spec 25 - `P2-S05-admin-datasets-and-ingestion-api`

**Spec name**  
`P2-S05-admin-datasets-and-ingestion-api`

**Responsibility**  
Implement MVP dataset validation, registration, and ingestion-trigger admin endpoints.

**Depends on**

- `P2-S01-admin-auth-users-and-route-foundation`
- `P2-S02-admin-shared-contracts`
- `P1-S16-admin-readiness-contract-patch`

**Inputs**

- [20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md)

**Files/artifacts produced**

- Dataset validation/register/ingest route handlers
- Storage-reader adapter interface for CSV validation
- Cloud Run trigger adapter boundary for ingestion start
- Job creation and event emission wiring
- Integration tests for register and ingest trigger flows

**In scope**

- `POST /admin/datasets/validate`
- `GET|POST /admin/datasets`
- `POST /admin/datasets/:id/ingest`

**Out of scope**

- Python pipeline internals
- Admin UI wizard implementation

**Implementation requirements**

- Dataset contracts include:
  - `filePath`
  - `sourceLabel`
  - `sourceUrl`
  - `status`
  - `uploadedBy`
- Ingestion trigger must:
  - create `pipeline_jobs` row
  - emit `admin.dataset.ingest_requested` event
  - call cloud-run adapter with dataset and pipeline-job identifiers
- Endpoint should support idempotency for ingestion-trigger retries.

**Exit criterion (verifiable done condition)**

1. Dataset validation endpoint reports required-column and row-level summary.
2. Dataset registration persists metadata including `sourceUrl`.
3. Ingestion trigger creates job row and app event in one transactional flow.
4. Trigger endpoint uses adapter boundary and is integration-testable without real cloud invocation.

