# Spec 24 - `P2-S04-admin-courses-and-mappings-api`

**Spec name**  
`P2-S04-admin-courses-and-mappings-api`

**Responsibility**  
Implement MVP admin endpoints for course catalog management and course-to-skill mapping management.

**Depends on**

- `P2-S01-admin-auth-users-and-route-foundation`
- `P2-S02-admin-shared-contracts`

**Inputs**

- [20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/20-p2-s00-admin-mvp-storyboard-and-phase6-notes.md)

**Files/artifacts produced**

- Admin course routes and mapping routes
- Validation schemas for depth weight and duplicate mapping prevention
- App-event emission for downstream profile recompute intent
- Integration tests for course and mapping workflows

**In scope**

- `GET|POST /admin/courses`
- `GET|PUT /admin/courses/:id`
- `GET|PUT /admin/courses/:id/skill-mappings`

**Out of scope**

- Student profile recomputation execution
- Student course APIs

**Implementation requirements**

- Mapping depth range must enforce `0.01..1.00`.
- Duplicate `course_id + skill_id` mappings must return conflict errors.
- Mapping save must emit an app-event to signal future recomputation workflow integration.

**Exit criterion (verifiable done condition)**

1. Admin can create/update/list courses through guarded endpoints.
2. Admin can create/remove/update skill mappings with range validation.
3. Duplicate mapping attempts fail with deterministic conflict responses.
4. Mapping mutation emits app-event for recompute intent.

