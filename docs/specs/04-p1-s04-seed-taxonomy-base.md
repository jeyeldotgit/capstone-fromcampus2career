# Spec 04 — `P1-S04-seed-taxonomy-base`

**Spec name**  
`P1-S04-seed-taxonomy-base`

**Responsibility**  
Create deterministic seed data for initial roles, skills, and aliases needed by normalization and mapping stages.

**Depends on**

- `P1-S01-db-schema-taxonomy`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [01-p1-s01-db-schema-taxonomy.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/01-p1-s01-db-schema-taxonomy.md)

**Files/artifacts produced**

- Seed script(s) and/or seed data files in `packages/database` seed path
- Deterministic lookup IDs or key strategy documentation for seeded taxonomy entities
- Seed verification tests for duplicate handling and alias normalization integrity

**In scope**

- Initial records for `skills`, `skill_aliases`, `career_roles`, and `career_role_aliases`
- Deterministic ordering and idempotent insert strategy
- Seed validation for duplicate alias collisions

**Out of scope**

- Schema/migration edits
- Course and course-skill seeds
- Python pipeline stage code
- TypeScript read-layer code

**Implementation requirements**

- Seed runs must be deterministic and repeatable
- Alias seeds must align with normalized alias constraints
- Seed process must fail fast on referential or uniqueness violations

**Exit criterion (verifiable done condition)**

1. Running taxonomy seed on an empty database inserts expected baseline records.
2. Re-running seed does not create duplicates or constraint violations.
3. Seed tests verify normalized alias uniqueness and deterministic counts.
4. No pipeline or API code is added in this spec.
