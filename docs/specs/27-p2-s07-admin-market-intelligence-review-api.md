# Spec 27 - `P2-S07-admin-market-intelligence-review-api`

**Spec name**  
`P2-S07-admin-market-intelligence-review-api`

**Responsibility**  
Implement read-only MVP admin APIs for published role requirements and SDI snapshot review.

**Depends on**

- `P2-S01-admin-auth-users-and-route-foundation`
- `P2-S02-admin-shared-contracts`
- `P1-S12-typescript-read-model-contracts`

**Inputs**

- [20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md)

**Files/artifacts produced**

- Requirement-version listing route
- Role-requirement query route
- SDI snapshot query route
- Integration tests for read-only behavior and filters

**In scope**

- `GET /admin/requirement-versions`
- `GET /admin/requirements`
- `GET /admin/sdi-snapshots`

**Out of scope**

- Mutation endpoints for versioned intelligence tables
- Decay moderation endpoints (Phase 6 notes)

**Implementation requirements**

- Endpoints must read prepared publish tables and monthly current views only.
- Requirement responses should surface only published requirement rows; below-threshold evidence is available via pipeline evidence-summary route.
- No endpoint in this spec may write to versioned intelligence tables.

**Exit criterion (verifiable done condition)**

1. Admin can list requirement versions and query requirements by role/version.
2. Admin can query SDI snapshots by role/version.
3. Tests prove these endpoints are read-only and admin-guarded.
4. Tests prove no raw `job_postings` scan is used in these request paths.

