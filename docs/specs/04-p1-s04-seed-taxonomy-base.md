# Spec 04 — `P1-S04-seed-taxonomy-base`

**Spec name**
`P1-S04-seed-taxonomy-base`

**Responsibility**
Create deterministic seed data for initial roles, skills, and aliases
needed by normalization and mapping stages.

**Depends on**

- `P1-S01-db-schema-taxonomy` — tables must exist
- `P1-S01b-db-schema-taxonomy-patch` — code, notes, and category columns
  must exist before seed runs

**Inputs**

- `docs/dev-roadmap.md`
- `docs/LLD.md`
- `docs/specs/01-p1-s01-db-schema-taxonomy.md`
- `docs/specs/01b-p1-s01b-db-schema-taxonomy-patch.md`
- Existing seed data file provided by human reviewer

**Files/artifacts produced**

- `packages/database/src/seeds/taxonomy/id-maps.ts`
- `packages/database/src/seeds/taxonomy/skills.seed.ts`
- `packages/database/src/seeds/taxonomy/skill-aliases.seed.ts`
- `packages/database/src/seeds/taxonomy/career-roles.seed.ts`
- `packages/database/src/seeds/taxonomy/career-role-aliases.seed.ts`
- `packages/database/src/seeds/run-taxonomy.ts`
- `packages/database/src/seeds/__tests__/taxonomy.unit.test.ts`
- `packages/database/src/seeds/__tests__/taxonomy.integration.test.ts`
- `packages/database/package.json` updated with seed script if not present

**In scope**

- Initial records for `skills` (133), `skill_aliases` (152),
  `career_roles` (40), and `career_role_aliases` (126)
- Hardcoded UUID maps for all four tables in `id-maps.ts`
- Static foreign key resolution through UUID maps at seed time
- Deterministic ordering and idempotent upsert strategy
- Seed validation for duplicate alias collisions before insert
- Computed `normalized_alias` for `skill_aliases` rows
- Preserved `normalized_alias` for `career_role_aliases` rows as authored

**Out of scope**

- `recommendation_catalog` — own spec
- Course and course-skill seeds
- Schema or migration edits
- Python pipeline stage code
- TypeScript read-layer or API code
- Broader career-search query normalization beyond the persisted alias
  key contract
- Punctuation stripping, phrase mapping, or fuzzy-search preparation

**ID strategy**
All four tables use hardcoded UUIDs defined in `id-maps.ts` using a
readable zero-padded namespace pattern:
Skills: 00000000-0000-0001-0000-000000000001 through 000000000133
Skill aliases: 00000000-0000-0002-0000-000000000001 through 000000000152
Career roles: 00000000-0000-0003-0000-000000000001 through 000000000040
Role aliases: 00000000-0000-0004-0000-000000000001 through 000000000126

Exported maps: `SKILL_IDS`, `SKILL_ALIAS_IDS`, `ROLE_IDS`,
`ROLE_ALIAS_IDS`. Foreign key fields in alias tables must be resolved
to UUIDs through these maps — never insert string codes into FK columns.

**Alias normalization contract**
For this spec, `normalized_alias` must follow the existing taxonomy
schema constraint from `P1-S01-db-schema-taxonomy`.

The authoritative Postgres formula is:
lower(regexp_replace(btrim(alias), '[[:space:]]+', ' ', 'g'))

The TypeScript equivalent used in the seed runner is:

```ts
alias.toLowerCase().trim().replace(/\s+/g, " ");
```

This applies to `skill_aliases.normalized_alias` only. It must be
computed by the seed runner — not copied from source data.

`career_role_aliases.normalized_alias` must be preserved exactly as
authored in the source data — do not recompute.

This contract is intentionally narrower than career-search query
normalization in `LLD.md`. Punctuation stripping, phrase mapping, and
fuzzy-search preparation are not part of this seed spec.

**Field corrections from actual schema**

- `career_role_aliases.notes` does not exist in the schema — strip it
  from source data, do not insert it
- `skill_aliases.normalized_alias` is required by the schema as
  `NOT NULL UNIQUE` — must be computed for every row
- `career_role_aliases` has a `code` column — must be populated from
  the `RA*` identifier in source data
- `skill_aliases` has a `code` column — must be populated from the
  `SA*` identifier in source data

**Confirmed insert field map**
skills: id, code, name, category, is_active, notes
skill_aliases: id, code, skill_id, alias, normalized_alias,
source, reviewed, notes
career_roles: id, code, title, description, is_active, category
career_role_aliases: id, code, role_id, alias, normalized_alias

**Upsert strategy**
skills: conflict on code
career_roles: conflict on code
skill_aliases: conflict on alias
career_role_aliases: conflict on alias

**Insert order**

skills
career_roles
skill_aliases
career_role_aliases

**Test expectations**
Tests must live in the TypeScript database package and use Vitest.

Required unit coverage — pure Vitest with no database dependency:

- Deterministic seed ordering and counts per table
- Computed normalized_alias values match normalization formula
- No duplicate normalized_alias values within skill_aliases seed set
- No duplicate normalized_alias values within career_role_aliases seed set
- No notes field present in any career_role_alias row payload
- All foreign key references resolve to a value in the parent UUID map
- All UUID values across all four maps are globally unique

Required integration verification — Vitest with live database:

- Seed against empty Postgres with S01 and S01b applied
- Assert row counts match expected values per table
- Re-run seed and assert counts are unchanged
- Assert at least one skill is queryable by code
- Assert at least one career role alias FK resolves to correct parent role

CI may run unit tests in the default path and database-backed tests in
a separate database-enabled job. Both are required for spec acceptance.

**Implementation requirements**

- Seed runs must be deterministic and repeatable
- Alias seeds must compute normalized_alias with the contract above
- Seed data must be validated for duplicate normalized_alias collisions
  before attempting inserts — fail fast if collisions found
- Seed process must fail fast on referential or uniqueness violations
- career_role_aliases.notes must be stripped before insert

**Exit criteria**

1. Running taxonomy seed on an empty database inserts all 451 expected
   records without errors.
2. Re-running seed does not create duplicates or constraint violations.
3. Pure Vitest unit tests verify deterministic counts, normalized alias
   values, and uniqueness rules without requiring a database connection.
4. Database-backed integration test proves insert success on an empty
   database and idempotent re-run behavior.
5. No pipeline, API, schema, or migration code is added in this spec.
