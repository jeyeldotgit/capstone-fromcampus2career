# Spec P1-S01b — `P1-S01b-db-schema-taxonomy-patch`

**Spec name**
`P1-S01b-db-schema-taxonomy-patch`

**Responsibility**
Add missing columns and human-readable code identifiers to the taxonomy
schema to support seed data, admin context fields, and dashboard display.

**Depends on**

- `P1-S01-db-schema-taxonomy` — must be applied before this patch

**Target branch**
`origin/feature/p1-s01-db-schema-taxonomy`

**Inputs**

- `packages/database/src/schema/skills.ts`
- `packages/database/src/schema/roles.ts`
- `packages/database/src/migrations/` (latest applied migration)
- `docs/LLD.md` (Database Schema section)
- `docs/specs/01-p1-s01-db-schema-taxonomy.md`

**Files/artifacts produced**

- One new Drizzle migration file in `packages/database/src/migrations/`
- Updated Drizzle schema files:
  - `packages/database/src/schema/skills.ts`
  - `packages/database/src/schema/roles.ts`
- Updated `docs/LLD.md` (Database Schema section only)
- Updated `docs/specs/01-p1-s01-db-schema-taxonomy.md` (column listings only)

**In scope**

- Add `code text unique not null` to `skills`
- Add `code text unique not null` to `skill_aliases`
- Add `code text unique not null` to `career_roles`
- Add `code text unique not null` to `career_role_aliases`
- Add `notes text` (nullable) to `skills`
- Add `notes text` (nullable) to `skill_aliases`
- Add `category text` (nullable) to `career_roles`
- Update corresponding Drizzle schema definitions to match
- Update LLD Database Schema section to reflect all new columns
- Update S01 spec column listings to reflect all new columns
- Migration must be reversible (include down migration)

**Out of scope**

- Seed data
- Any other table changes
- API or pipeline code
- Changes to any other schema file
- Changes to any other section of the LLD beyond Database Schema
- Changes to any other spec beyond S01 column listings

**Implementation requirements**

- Migration must be additive only — no existing columns altered or dropped
- `code` columns must be `text unique not null` on all four tables
- `notes` and `category` columns must be nullable with no default value
- Drizzle schema files must reflect all new columns after migration
- Migration file must follow the existing naming convention in the
  migrations folder
- Running the migration on an already-patched database must not throw errors
- LLD and S01 spec updates must be limited to column listing changes only —
  no architectural prose may be altered

**Exit criteria**

1. Migration applies cleanly on a fresh S01 database.
2. Migration applies cleanly on an already-patched database without errors.
3. Drizzle schema types include all new columns across all four tables.
4. LLD Database Schema section reflects the new columns for all four tables.
5. S01 spec column listings reflect the new columns for all four tables.
6. No seed, API, or pipeline code is introduced.
7. Down migration reverts all seven new columns cleanly.
