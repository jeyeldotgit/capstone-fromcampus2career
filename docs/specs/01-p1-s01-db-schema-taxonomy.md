# Spec 01 — `P1-S01-db-schema-taxonomy`

**Spec name**  
`P1-S01-db-schema-taxonomy`

**Responsibility**  
Define the Phase 1 foundational taxonomy and dataset schema in Supabase Postgres so all downstream pipeline and read-layer work has stable relational contracts.

**Depends on**  
None.

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)

**Files/artifacts produced**

- Drizzle schema updates in `packages/database/src` for `skills`, `skill_aliases`, `career_roles`, `career_role_aliases`, `courses`, `course_skills`, and `market_datasets`
- SQL migration file(s) in `packages/database` migrations path
- Schema constraint tests in the existing database test location
- Short migration notes in `packages/database` documentation

**In scope**

- Table creation and constraints for taxonomy and dataset registration
- Alias normalization fields and uniqueness constraints needed for deterministic matching
- Indexes required for seeded lookup and downstream joins

**Out of scope**

- Pipeline operational tables
- Prepared intelligence tables
- Seed content values
- Python pipeline logic
- TypeScript read services

**Implementation requirements**

- Keep schema and migrations in sync and reproducible on an empty database
- Use explicit PK/FK/unique/check constraints for contract-critical integrity
- Keep naming and required columns aligned with Phase 1 vocabulary in `LLD.md`

**Column listings**

```txt
skills
- id uuid primary key
- code text unique not null
- name text unique not null
- category text
- notes text
- is_active boolean default true
- created_at timestamptz not null
```

```txt
skill_aliases
- id uuid primary key
- code text unique not null
- skill_id uuid references skills(id)
- alias text unique not null
- source text
- notes text
- reviewed boolean default false
- created_at timestamptz not null
```

```txt
career_roles
- id uuid primary key
- code text unique not null
- title text unique not null
- description text
- category text
- is_active boolean default true
- created_at timestamptz not null
```

```txt
career_role_aliases
- id uuid primary key
- code text unique not null
- role_id uuid not null references career_roles(id)
- alias text unique not null
- normalized_alias text not null
- created_at timestamptz not null
```

**Exit criterion (verifiable done condition)**

1. Database migration applies cleanly on a fresh database.
2. Tests confirm required taxonomy tables and constraints exist.
3. At least one test proves FK enforcement by rejecting an invalid reference.
4. No pipeline or prepared-output table is added in this spec.
