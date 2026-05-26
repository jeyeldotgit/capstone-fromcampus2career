# Spec 20 - `P2-S00-admin-mvp-storyboard-and-phase6-notes`

**Spec name**  
`P2-S00-admin-mvp-storyboard-and-phase6-notes`

**Responsibility**  
Define the Phase 2 MVP Admin storyboard boundary and record explicit Phase 6 Admin expansion notes so deferred scope remains discoverable and testable later.

**Depends on**

- `P1-S16-admin-readiness-contract-patch`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [arch.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/arch.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)

**Files/artifacts produced**

- MVP admin storyboard contract note in docs
- Phase 6 Admin Notes section with deferred capabilities
- Route-to-screen mapping table for MVP admin backend dependencies

**MVP storyboard in scope**

- Login and admin access control
- Dashboard summary and quick links
- Skill management
- Career role and alias management
- Course catalog and course-skill mappings
- Dataset validation and registration
- Pipeline job monitoring with rejected rows and evidence summary
- Read-only requirements and SDI snapshot review

**Deferred to Phase 6 Admin Notes**

- Recommendation catalog management UX
- User and role management UX
- Decay signal moderation and deactivation workflow
- Richer SDI analytics and trend tooling
- Bulk moderation and bulk mapping actions
- Expanded dashboard analytics and advanced filtering

**Implementation requirements**

- Each MVP storyboard surface must map to a concrete admin API contract in Phase 2 specs.
- Deferred items must include intended API dependencies and acceptance notes, even when endpoints are not built in Phase 2.
- This spec must be kept aligned with `dev-roadmap.md` so phase boundaries stay explicit.

**Exit criterion (verifiable done condition)**

1. MVP admin screen list and API dependencies are documented and approved.
2. Deferred Phase 6 Admin Notes are captured in the same spec and mirrored in roadmap text.
3. No deferred item is mixed into Phase 2 endpoint implementation specs unless explicitly promoted.

