# Spec 22 - `P2-S02-admin-shared-contracts`

**Spec name**  
`P2-S02-admin-shared-contracts`

**Responsibility**  
Define reusable TypeScript/Zod contracts for admin route inputs and outputs.

**Depends on**

- `P2-S01-admin-auth-users-and-route-foundation`

**Inputs**

- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [apps/api/AGENTS.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/apps/api/AGENTS.md)

**Files/artifacts produced**

- Shared admin request/response schemas in `packages/shared/src/contracts`
- API route validation schemas consumed by Hono routes
- API-client type exports in `packages/api-client/src`

**In scope**

- Admin list envelope contract:
  - `items`
  - `page`
  - `pageSize`
  - `total`
- Shared query contracts for pagination, sorting, and filter primitives
- Shared mutation response contract with stable success and conflict shapes

**Out of scope**

- Route business logic
- Database schema changes

**Implementation requirements**

- Route handlers must validate query/body/params through shared schemas.
- Shared contracts must remain strict-mode compatible with no `any`.
- Conflict responses must provide machine-readable field and constraint keys.

**Exit criterion (verifiable done condition)**

1. All Phase 2 admin route specs consume shared contract primitives.
2. Contract tests validate parsing and error-shape stability.
3. API-client exports compile and are reusable by admin frontend in Phase 3.

