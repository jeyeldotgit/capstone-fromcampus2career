# Spec 21 - `P2-S01-admin-auth-users-and-route-foundation`

**Spec name**  
`P2-S01-admin-auth-users-and-route-foundation`

**Responsibility**  
Implement Phase 2 admin authentication and authorization foundation for all protected admin routes.

**Depends on**

- `P1-S16-admin-readiness-contract-patch`
- `P2-S00-admin-mvp-storyboard-and-phase6-notes`

**Inputs**

- [apps/api/AGENTS.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/apps/api/AGENTS.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)

**Files/artifacts produced**

- `users` table/schema/contract updates if missing fields
- Supabase JWT validation middleware
- App-user lookup middleware and active-user check
- Admin guard middleware for `/admin/*` routes
- Shared error envelope with stable error codes
- Integration tests for auth and role gating

**In scope**

- `POST /auth/session`
- Admin middleware chain: auth -> app-user -> active-status -> role check
- Standardized admin error codes:
  - `UNAUTHENTICATED`
  - `FORBIDDEN`
  - `VALIDATION_ERROR`
  - `CONFLICT`
  - `NOT_FOUND`

**Out of scope**

- Admin resource CRUD endpoints
- Student route changes
- Frontend session handling

**Implementation requirements**

- No admin route may execute business logic before passing admin guard.
- Auth adapter must be mockable for integration tests.
- `users` role/status state must be authoritative for admin access decisions.

**Exit criterion (verifiable done condition)**

1. Missing/invalid JWT requests return 401 with `UNAUTHENTICATED`.
2. Non-admin authenticated requests return 403 with `FORBIDDEN`.
3. Inactive/suspended users are blocked from admin routes.
4. Admin users can pass middleware and hit protected route handlers.

