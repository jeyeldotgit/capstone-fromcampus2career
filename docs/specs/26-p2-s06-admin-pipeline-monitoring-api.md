# Spec 26 - `P2-S06-admin-pipeline-monitoring-api`

**Spec name**  
`P2-S06-admin-pipeline-monitoring-api`

**Responsibility**  
Implement MVP admin pipeline-monitoring APIs, including live status notifications.

**Depends on**

- `P2-S01-admin-auth-users-and-route-foundation`
- `P2-S02-admin-shared-contracts`
- `P2-S05-admin-datasets-and-ingestion-api`

**Inputs**

- [20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md)

**Files/artifacts produced**

- Pipeline jobs list/detail routes
- Rejected rows and evidence summary routes
- Retry trigger route
- Authenticated SSE endpoint for pipeline job notifications
- Integration tests for monitoring APIs

**In scope**

- `GET /admin/pipeline-jobs`
- `GET /admin/pipeline-jobs/:id`
- `POST /admin/pipeline-jobs/:id/retry`
- `GET /admin/pipeline-jobs/:id/rejected-rows`
- `GET /admin/pipeline-jobs/:id/evidence-summary`
- `GET /admin/pipeline-job-events`

**Out of scope**

- Frontend polling/render behavior
- Python pipeline status-update internals

**Implementation requirements**

- Running/failed/partial/complete states must be returned with consistent status shape.
- Failed rows should expose row number, reason, and payload preview fields.
- SSE payloads must carry identifiers only; clients refetch details from APIs.
- Retry endpoint must create a new pipeline job, not mutate historical job rows.

**Exit criterion (verifiable done condition)**

1. Admin can list and inspect pipeline jobs and their statuses.
2. Rejected rows and evidence summary are retrievable per job.
3. Retry creates a new job linked to source dataset.
4. SSE endpoint emits authenticated ID-only notifications consumable by admin clients.

