# Spec 12 — `P1-S12-typescript-read-model-contracts`

**Spec name**  
`P1-S12-typescript-read-model-contracts`

**Responsibility**  
Implement strict TypeScript read-layer contracts and repositories that consume published Phase 1 prepared-output tables only.

**Depends on**

- `P1-S03-db-schema-prepared-intelligence`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [03-p1-s03-db-schema-prepared-intelligence.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/03-p1-s03-db-schema-prepared-intelligence.md)

**Files/artifacts produced**

- Shared response/input contract updates in `packages/shared/src`
- Read repository/query modules in `apps/api/src` targeting prepared-output tables
- Runtime validation schemas for read payloads in TypeScript layer
- Unit/integration tests proving prepared-table reads and validating payload shape

**In scope**

- Typed read interfaces and validators for role requirements, SDI, and decay outputs
- Repository/query paths that read only published prepared outputs
- Contract-level tests for parsing/typing and expected table joins

**Out of scope**

- Database migrations
- Python pipeline computations
- Seed scripts
- Student write paths and admin mutation APIs

**Implementation requirements**

- TypeScript must remain in strict mode with no `any` on boundary payloads
- External boundaries must have runtime validation and static typing
- Required read paths must not query raw `job_postings`

**Exit criterion (verifiable done condition)**

1. TypeScript tests pass for parsing and reading prepared output tables.
2. Guard tests prove read-layer queries do not target raw `job_postings`.
3. Shared contracts and API-layer read code compile under strict type checks.
4. No Python pipeline logic is changed in this spec.
