# Spec 28 - `P2-S08-admin-backend-acceptance-suite`

**Spec name**  
`P2-S08-admin-backend-acceptance-suite`

**Responsibility**  
Create a Phase 2 acceptance suite that verifies admin backend route correctness, auth gating, and contract compatibility with published pipeline data.

**Depends on**

- `P2-S01-admin-auth-users-and-route-foundation`
- `P2-S02-admin-shared-contracts`
- `P2-S03-admin-taxonomy-api`
- `P2-S04-admin-courses-and-mappings-api`
- `P2-S05-admin-datasets-and-ingestion-api`
- `P2-S06-admin-pipeline-monitoring-api`
- `P2-S07-admin-market-intelligence-review-api`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [apps/api/AGENTS.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/apps/api/AGENTS.md)

**Files/artifacts produced**

- Route integration test suite for admin endpoints
- Contract-compatibility tests against Phase 1 published outputs
- Test command/task entry for CI
- Checkpoint notes for expected assertions

**In scope**

- Auth and role-guard behavior on every Phase 2 admin route
- Request validation and error-shape determinism
- CRUD happy paths and conflict/validation failures
- Dataset/job/evidence/rejected-row read and mutation boundaries
- Requirement/SDI read-only boundary validation

**Out of scope**

- Admin frontend tests
- Full Cloud Run integration execution
- Phase 6 deferred feature tests

**Implementation requirements**

- All tests must run deterministically with mockable adapters.
- Acceptance suite must include at least one complete admin workflow:
  - auth session
  - taxonomy mutation
  - dataset register
  - ingest trigger
  - pipeline monitoring reads
  - requirements/SDI review reads
- Test failures must clearly identify route and contract boundary that failed.

**Exit criterion (verifiable done condition)**

1. Every MVP admin route has at least one guarded integration test.
2. Missing JWT and non-admin scenarios are covered for protected routes.
3. Contract tests prove compatibility with Phase 1 published-output reads.
4. CI entry exists for running the Phase 2 admin acceptance suite.

