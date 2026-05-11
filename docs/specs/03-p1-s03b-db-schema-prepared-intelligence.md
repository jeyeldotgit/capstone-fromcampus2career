# Spec P1-S03b — `P1-S03b-db-schema-evidence-summary`

**Spec name**
`P1-S03b-db-schema-evidence-summary`

**Responsibility**
Add the `pipeline_skill_evidence_summary` table to track per-run and cumulative
role-skill evidence counts, and update architecture documentation to reflect the
new schema artifact.

**Depends on**

- `P1-S03-db-schema-prepared-intelligence` must be merged into main before starting.

**Inputs**

- docs/arch.md
- docs/HLD.md
- docs/LLD.md
- docs/specs/03-p1-s03-db-schema-prepared-intelligence.md

**Files/artifacts produced**

- SQL migration adding `pipeline_skill_evidence_summary`
- Drizzle schema definition for the new table
- Updated arch.md, HLD.md, and LLD.md to reflect the new table

**In scope**

- `pipeline_skill_evidence_summary` table definition and migration
- Drizzle schema entry in `packages/database/src/schema/pipeline.ts`
- Documentation updates to arch.md, HLD.md, and LLD.md
- Indexes required for efficient cumulative evidence reads

**Out of scope — do not touch**

- Any existing migration or schema file from P1-S03
- Aggregation logic (that is P1-S10)
- Publishing logic (that is P1-S10)
- Any TypeScript service or repository logic
- Any file not listed in OUTPUT

**Table definition**

```txt
pipeline_skill_evidence_summary
- id uuid primary key
- dataset_id uuid not null references market_datasets(id)
- pipeline_job_id uuid not null references pipeline_jobs(id)
- role_id uuid not null references career_roles(id)
- skill_id uuid not null references skills(id)
- evidence_count int not null
- threshold_met boolean not null default false
- created_at timestamptz not null
- unique(pipeline_job_id, role_id, skill_id)
```

**Indexes required**

- `(role_id, skill_id)` — for cumulative evidence aggregation across datasets
- `(dataset_id)` — for per-dataset admin review queries
- `(pipeline_job_id)` — for job-scoped lookups

**Documentation update rules**

- arch.md: add `pipeline_skill_evidence_summary` to the authoritative data ownership
  table under pipeline data, with owner noted as Python pipeline
- HLD.md: add the table to the pipeline data section of section 10 (Data Storage Strategy)
- LLD.md: add the table definition to section 5 (Database Schema) under Pipeline Tables,
  add it to the ERD, and add it to the read model notes for admin pipeline job summary

**Implementation requirements**

- Migration must be forward-only
- `evidence_count` must have a check constraint: `evidence_count >= 0`
- `threshold_met` must be computed and stored by the aggregator at write time,
  not derived at read time
- The table is write-once per `(pipeline_job_id, role_id, skill_id)` —
  no updates after insert
- Breaking change footer must be included in the migration commit message

**Exit criteria (self-check before each slice commit)**

- [ ] Migration applies cleanly against a fresh test database with S03 already applied
- [ ] Drizzle schema matches the applied migration exactly
- [ ] Unique constraint on `(pipeline_job_id, role_id, skill_id)` is present and tested
- [ ] FK constraints on dataset_id, pipeline_job_id, role_id, skill_id are present
- [ ] Check constraint `evidence_count >= 0` is present
- [ ] All three documentation files updated with no unresolved placeholders
- [ ] No existing migration or S03 schema file is modified

**OUTPUT**

- packages/database/src/schema/pipeline.ts (append only — add new table definition)
- packages/database/migrations/<timestamp>\_add_pipeline_skill_evidence_summary.sql
- docs/arch.md
- docs/HLD.md
- docs/LLD.md

---

SLICES:

Slice 1 — Migration and Drizzle schema
Files:
packages/database/migrations/<timestamp>\_add_pipeline_skill_evidence_summary.sql
packages/database/src/schema/pipeline.ts (append only)
Commit: feat(db)!: add pipeline_skill_evidence_summary table and migration
Commit body must include:
Implements: P1-S03b-db-schema-evidence-summary
Depends on: P1-S03-db-schema-prepared-intelligence
BREAKING CHANGE: adds pipeline_skill_evidence_summary table; existing S03
consumers unaffected but pipeline publishers must write to this table from S10 onward
Self-check: migration applies cleanly on top of S03, Drizzle schema compiles
under strict mode, unique and FK constraints are present, check constraint
evidence_count >= 0 is present, no existing migration file is modified.

Slice 2 — Documentation updates
Files:
docs/arch.md
docs/HLD.md
docs/LLD.md
Commit: docs: update arch, HLD, and LLD to reflect pipeline_skill_evidence_summary
Commit body must include:
Implements: P1-S03b-db-schema-evidence-summary
Depends on: P1-S03-db-schema-prepared-intelligence
Self-check: all three files reference pipeline_skill_evidence_summary in the
correct sections, no architecture placeholder text remains, no other table
definition or section is modified.

WORKFLOW:

1. Branch from: main
   Confirm P1-S03 is merged before branching
2. Branch name: feat/p1-s03b-db-schema-evidence-summary
3. Implement and commit slices in order: slice-1, slice-2
4. Each slice must pass its own self-check before its commit
5. Do NOT push or open PR — stop after both commits and report done

PROCESS:

1. Read all referenced input files before writing any code
2. Output an implementation plan covering:
   - proposed column shapes and constraint definitions
   - index strategy for cumulative reads across datasets
   - exact sections in arch.md, HLD.md, and LLD.md that require changes
   - ERD update plan for LLD section 5
   - migration naming and ordering relative to existing S03 migrations
3. Wait for explicit approval of the plan before generating any file
