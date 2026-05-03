# Spec 05 — `P1-S05-seed-courses-and-mappings`

**Spec name**  
`P1-S05-seed-courses-and-mappings`

**Responsibility**  
Create deterministic seed data for courses and course-to-skill mappings required for early student-skill profile derivation.

**Depends on**

- `P1-S01-db-schema-taxonomy`
- `P1-S04-seed-taxonomy-base`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [04-p1-s04-seed-taxonomy-base.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/04-p1-s04-seed-taxonomy-base.md)

**Files/artifacts produced**

- Seed script(s) and/or seed data files for `courses` and `course_skills` in `packages/database`
- Referential integrity seed tests for course-to-skill mapping inserts
- Seed run notes documenting expected baseline counts

**In scope**

- Initial `courses` rows and `course_skills` junction rows
- Deterministic mapping strategy tied to seeded skill catalog
- Idempotent behavior for repeated seed execution

**Out of scope**

- Taxonomy schema changes
- Pipeline computations
- Prepared output publishing
- TypeScript route/service logic

**Implementation requirements**

- Every `course_skills` entry must map to an existing seeded course and skill
- Seed logic must be deterministic and safe to re-run
- Constraint failures must be surfaced clearly during seed execution

**Exit criterion (verifiable done condition)**

1. Seed creates expected course and mapping records on a clean database.
2. Re-running seed preserves deterministic counts and no duplicate junction rows.
3. Tests verify all mapping FKs resolve to valid course and skill IDs.
4. No pipeline processing or API read logic is included.
