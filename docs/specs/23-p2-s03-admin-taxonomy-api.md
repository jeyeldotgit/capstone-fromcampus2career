# Spec 23 - `P2-S03-admin-taxonomy-api`

**Spec name**  
`P2-S03-admin-taxonomy-api`

**Responsibility**  
Implement MVP admin taxonomy endpoints for skills, roles, role aliases, and skill-alias review.

**Depends on**

- `P2-S01-admin-auth-users-and-route-foundation`
- `P2-S02-admin-shared-contracts`

**Inputs**

- [20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md)
- [16-p1-s16-admin-readiness-contract-patch.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/16-p1-s16-admin-readiness-contract-patch.md)

**Files/artifacts produced**

- Admin taxonomy routes under `/api/v1/admin`
- Service and repository modules for taxonomy operations
- Integration tests for CRUD and review workflows

**In scope**

- `GET|POST /admin/skills`
- `PUT /admin/skills/:id`
- `GET|POST /admin/roles`
- `GET|PUT /admin/roles/:id`
- `POST|PUT /admin/role-aliases`
- `GET|POST /admin/skill-aliases`
- `PUT /admin/skill-aliases/:id/review`

**Out of scope**

- Recommendation catalog APIs
- User-role administration APIs

**Implementation requirements**

- Enforce uniqueness conflicts for skill code/name and role code/title.
- Alias normalization remains server-side authoritative.
- Skill-alias review must support:
  - approve with `skillId`
  - dismiss without `skillId`
- Route responses must include stable conflict metadata for UI field binding.

**Exit criterion (verifiable done condition)**

1. Taxonomy endpoints support list/create/update flows with validation and role guard.
2. Approve and dismiss skill-alias review flows both pass integration tests.
3. Uniqueness conflicts return deterministic machine-readable errors.

