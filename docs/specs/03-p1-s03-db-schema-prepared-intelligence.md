# Spec 03 — `P1-S03-db-schema-prepared-intelligence`

**Spec name**  
`P1-S03-db-schema-prepared-intelligence`

**Responsibility**  
Define versioned prepared-intelligence schema tables used by TypeScript consumers and published by the Python pipeline.

**Depends on**

- `P1-S01-db-schema-taxonomy`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [01-p1-s01-db-schema-taxonomy.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/01-p1-s01-db-schema-taxonomy.md)

**Files/artifacts produced**

- Drizzle schema updates for `role_requirement_versions`, `role_skill_requirements`, `sdi_snapshots`, and `skill_decay_signals` in `packages/database/src`
- SQL migration file(s) in `packages/database` migrations path
- Constraint/index tests for version linkage and uniqueness guarantees
- Prepared-output schema notes in `packages/database` documentation

**In scope**

- Prepared intelligence table definitions and versioning columns
- PK/FK/unique/check constraints that enforce immutable versioned outputs
- Indexes needed for latest-version and per-role/skill lookups

**Out of scope**

- Pipeline job/rejected-row schema
- Seed data payloads
- Python computation implementations
- TypeScript read repositories and runtime validators

**Implementation requirements**

- Preserve immutable snapshot semantics by version rather than in-place overwrite
- Enforce uniqueness rules per role, skill, and version/date combinations
- Keep schema aligned with Phase 1 checkpoint table requirements

**Exit criterion (verifiable done condition)**

1. Migration applies and creates all four prepared-intelligence tables.
2. Tests confirm uniqueness and FK constraints on versioned records.
3. Tests confirm invalid version references are rejected.
4. No non-schema pipeline or API logic is changed.
