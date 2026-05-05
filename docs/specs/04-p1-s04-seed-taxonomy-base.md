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
- Vitest seed-data tests for duplicate handling, deterministic counts, and alias normalization integrity
- Database-backed seed verification in the existing `packages/database` test location or equivalent documented verification script

**In scope**

- Initial records for `skills`, `skill_aliases`, `career_roles`, and `career_role_aliases`
- Deterministic ordering and idempotent insert strategy
- Seed validation for duplicate alias collisions
- Persisted alias normalization needed to populate `normalized_alias` columns deterministically

**Out of scope**

- Schema/migration edits
- Course and course-skill seeds
- Python pipeline stage code
- TypeScript read-layer code
- Broader career-search query normalization behavior beyond the persisted alias key contract

**Alias normalization contract**

- For this spec, `normalized_alias` must follow the existing taxonomy schema constraint from `P1-S01-db-schema-taxonomy`.
- The required normalization formula is: `lower(regexp_replace(btrim(alias), '[[:space:]]+', ' ', 'g'))`.
- This applies to both `skill_aliases.normalized_alias` and `career_role_aliases.normalized_alias`.
- This contract is intentionally narrower than career-search query normalization in `LLD.md`; punctuation stripping, phrase mapping, and fuzzy-search preparation are not part of this seed spec unless the schema contract changes first.

**Test expectations**

- Tests for this spec must live in the TypeScript database package and use Vitest.
- Required unit coverage: pure Vitest tests with no database dependency that validate deterministic seed ordering/counts, derived `normalized_alias` values, and fail-fast detection of duplicate normalized aliases inside the seed set.
- Required integration verification: a Vitest database-backed test, or equivalent documented database verification invoked by Vitest/package scripts, that runs against a disposable Postgres database when `DATABASE_URL` is available and proves empty-database insert plus safe re-run behavior.
- CI may run the pure unit tests in the default path and the database-backed verification in a separate database-enabled job, but both are part of spec acceptance.

**Implementation requirements**

- Seed runs must be deterministic and repeatable
- Alias seeds must compute `normalized_alias` with the contract above rather than inventing a separate rule
- Seed data must be validated for duplicate `normalized_alias` collisions before attempting inserts
- Seed process must fail fast on referential or uniqueness violations

**Exit criterion (verifiable done condition)**

1. Running taxonomy seed on an empty database inserts expected baseline records.
2. Re-running seed does not create duplicates or constraint violations.
3. Pure Vitest tests verify deterministic counts/order and normalized alias uniqueness rules without requiring a database.
4. Database-backed verification proves seed insert success on an empty database and idempotent re-run behavior.
5. No pipeline or API code is added in this spec.
