# Spec 15 - `P1-S15-monthly-intelligence-versioning-and-lineage`

**Spec name**  
`P1-S15-monthly-intelligence-versioning-and-lineage`

**Responsibility**  
Make monthly market intelligence a first-class, query-safe contract so historical data remains usable, multiple publishes in the same month can coexist, and product reads can resolve a clear "current per month" record set.

**Problem this spec solves**

- Today, each live run creates a new global `role_requirement_versions.is_current = true`, which makes the previous run non-current even when it is for a different month.
- `sdi_snapshots` uniqueness is currently `(role_id, skill_id, snapshot_date)`, which prevents coexistence of multiple published versions for the same month.
- Historical monthly intelligence exists but is hard to query safely because "current" is global, not month-scoped.
- Dataset provenance for a published monthly intelligence version is not explicit.

**Decision summary**

- Keep immutable versioned outputs.
- Add month-scoped version metadata and month-scoped current pointer behavior.
- Allow multiple versions for the same month to coexist.
- Add explicit dataset lineage per published version.
- Keep one spec with phased implementation so MVP can land safely without blocking follow-up improvements.

**Depends on**

- `P1-S03-db-schema-prepared-intelligence`
- `P1-S10-pipeline-role-requirements-publish`
- `P1-S11-pipeline-sdi-and-decay-publish`
- `P1-S12-typescript-read-model-contracts`
- `P1-S14-pipeline-runner-and-quality-hardening`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [arch.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/arch.md)
- [HLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/HLD.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [03-p1-s03-db-schema-prepared-intelligence.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/03-p1-s03-db-schema-prepared-intelligence.md)
- [10-p1-s10-pipeline-role-requirements-publish.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/10-p1-s10-pipeline-role-requirements-publish.md)
- [11-p1-s11-pipeline-sdi-and-decay-publish.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/11-p1-s11-pipeline-sdi-and-decay-publish.md)

**Files/artifacts produced**

- Drizzle schema updates in `packages/database/src/schema`
- Forward-only SQL migration(s) in `packages/database/migrations`
- Python publisher updates in `apps/data-pipeline/src/publishing`
- Runner and pipeline wiring updates in `apps/data-pipeline/src/runner.py` and related modules
- Contract and integration tests in `packages/database/src/__tests__` and `apps/data-pipeline/src/tests`
- SQL read views for query ergonomics (admin/analytics safe reads)
- Core architecture documentation updates in `docs/arch.md`, `docs/HLD.md`, and `docs/LLD.md`

**In scope**

- Month-scoped version identity for published intelligence outputs
- Coexistence rules for multiple versions in the same month
- Dataset lineage mapping for each published version
- Month-scoped "current" pointer behavior
- SDI publish compatibility with coexistence
- Historical monthly query contract (raw-table and view-based)

**Out of scope**

- Frontend implementation details
- Replacing TypeScript product logic with Python
- LLM-dependent logic for correctness
- Rewriting ingestion adapters or taxonomy model from scratch

**Core documentation alignment (mandatory)**

- This spec must update `docs/arch.md`, `docs/HLD.md`, and `docs/LLD.md` in the same change set as schema/contract updates.
- `arch.md` must reflect the authoritative month-scoped versioning model and immutable publish semantics.
- `HLD.md` must reflect system-level publish/read behavior for monthly current pointers, coexistence, and lineage.
- `LLD.md` must reflect exact table/constraint/view contracts and publisher flow details.
- If any implementation deviates from these documents, the implementation is blocked until docs are reconciled.

## Target contract

### 1. Version header model (`role_requirement_versions`)

Add:

- `period_month date not null` (must be first day of month, for example `2026-04-01`)
- `period_revision integer not null` (starts at `1` for each month, increments per republish of same month)

Keep:

- global `version` as immutable publish ID
- `is_current` flag

Required constraints/indexes:

- `unique(version)` (existing)
- `unique(period_month, period_revision)`
- partial unique index: one current row per month  
  `unique(period_month) where is_current = true`
- check: `period_revision > 0`

Behavior:

- publishing a new version for month `M` flips `is_current=false` only for existing rows in month `M`
- publishes for month `M` do not change `is_current` rows in other months

### 2. Dataset lineage model

Add table:

- `role_requirement_version_datasets`
  - `requirement_version integer not null` FK -> `role_requirement_versions.version`
  - `dataset_id uuid not null` FK -> `market_datasets.id`
  - `linked_at timestamptz not null default now()`
  - unique on `(requirement_version, dataset_id)`

Purpose:

- preserve which dataset(s) contributed to one published version
- support future monthly aggregate mode across multiple datasets

### 3. SDI coexistence model (`sdi_snapshots`)

Change uniqueness from:

- `(role_id, skill_id, snapshot_date)`

To:

- `(role_id, skill_id, snapshot_date, requirement_version)`

Add FK:

- `requirement_version` -> `role_requirement_versions.version`

Publisher rules:

- idempotent only when all of `role_id`, `skill_id`, `snapshot_date`, `requirement_version`, and `demand_index` match
- conflict if same composite key exists with different `demand_index`
- `snapshot_date` must equal the selected `period_month` for the published `requirement_version`

### 4. Decay publish month-safety (`skill_decay_signals`)

Keep unique `(role_id, skill_id, requirement_version)`.

Add FK:

- `requirement_version` -> `role_requirement_versions.version`

Publisher behavior update:

- deactivation of prior active rows must be scoped to the same `period_month` as the incoming publish, not global across all months
- this prevents backfill runs for old months from deactivating current-month active rows

## Publish flow contract

1. Determine `period_month` for the run (explicit input or derived as month-start from publishing window).
2. Allocate `version = max(version) + 1` (global immutable ID).
3. Allocate `period_revision = max(period_revision for period_month) + 1`.
4. Insert `role_requirement_versions(version, dataset_id, period_month, period_revision, is_current=false)`.
5. Insert lineage rows into `role_requirement_version_datasets` (minimum one dataset for MVP).
6. Publish `role_skill_requirements`, `sdi_snapshots`, and `skill_decay_signals` linked to that `version`.
7. Flip `is_current` false only for previous rows in same `period_month`.
8. Flip `is_current` true for new `(period_month, period_revision)` row.
9. Commit atomically.

All steps above must occur in one transaction for a publish.

## Read/query contract

Provide stable query surfaces:

- `v_current_monthly_role_skill_requirements`
- `v_current_monthly_sdi_snapshots`
- `v_current_monthly_skill_decay_signals`

Each view resolves through `role_requirement_versions where is_current = true` and is month-safe.

Historical analysis queries must be able to filter by:

- `period_month`
- `period_revision`
- global `version`
- contributing `dataset_id` via lineage table

## Implementation requirements

- DB schema is defined in Drizzle; migration SQL is generated and committed.
- Migration application to shared/live environments uses forward-only SQL and includes tests for changed constraints/contracts.
- Python publishers remain deterministic and typed.
- Student request-response paths do not call Python and do not scan raw `job_postings`.
- No in-place overwrite of published intelligence rows; all changes are new versions.
- `docs/arch.md`, `docs/HLD.md`, and `docs/LLD.md` must be updated in lockstep with schema and publish-contract changes.

## MVP scope for this fix

Required in MVP:

- `period_month` and `period_revision` in `role_requirement_versions`
- month-scoped `is_current` behavior
- lineage table and inserts
- `sdi_snapshots` coexistence via uniqueness including `requirement_version`
- requirement-version FK coverage for SDI and decay tables
- read views for current monthly outputs

Deferred (but planned in this spec):

- full monthly aggregate mode that publishes one month from multiple datasets in one run
- scheduler/orchestrator batching UX for multi-dataset monthly consolidation
- historical backfill automation CLI

## Exit criteria

1. Schema migration applies cleanly and is reversible only by new forward migration, not manual rollback.
2. Tests prove only one `is_current=true` row exists per `period_month`.
3. Tests prove two versions for same month can coexist (`period_revision` increments).
4. Tests prove `sdi_snapshots` accepts same `(role, skill, snapshot_date)` across different `requirement_version` values.
5. Tests prove `sdi_snapshots` rejects duplicate rows within same composite key when values conflict.
6. Tests prove decay deactivation is scoped by month and does not deactivate active rows from other months.
7. Tests prove lineage table captures all linked datasets for each published version.
8. Read views return deterministic current-month outputs and are compatible with TypeScript read contracts.
9. `docs/arch.md`, `docs/HLD.md`, and `docs/LLD.md` are updated and consistent with the implemented schema and runtime contracts.

## Slices

**Slice 1 - Schema and migrations**

- Add `period_month`, `period_revision` to `role_requirement_versions`
- Add `role_requirement_version_datasets`
- Update `sdi_snapshots` unique index and add FK
- Add FK for `skill_decay_signals.requirement_version`
- Add month-scoped current partial unique index

**Slice 2 - Role requirement publisher**

- accept/derive `period_month`
- allocate `period_revision`
- month-scoped `is_current` flip
- write lineage rows

**Slice 3 - SDI and decay publishers**

- SDI idempotency/conflict keys updated for coexistence
- enforce `snapshot_date == period_month` for target `requirement_version`
- month-scoped active decay deactivation logic

**Slice 4 - Read model views and contracts**

- add current-month views
- update TypeScript read-layer contracts/tests if needed

**Slice 5 - Runner and docs**

- runner supports explicit `period_month` override for backfill/testing
- docs include historical query examples by month, revision, and dataset lineage
- update `docs/arch.md`, `docs/HLD.md`, and `docs/LLD.md` to match final contract and remove conflicting legacy wording

## Open decisions to settle before implementation

1. Whether `period_month` is always derived from posting window or can be explicitly set in live runs.
2. Whether `dataset_id` on `role_requirement_versions` remains "triggering dataset" while lineage holds complete provenance (recommended: yes).
3. Whether `skill_decay_signals.is_active` should mean "current for month" or "current globally" (recommended: current for month).
4. Whether monthly aggregate across multiple datasets is included in MVP or follow-up (recommended: follow-up within this spec).
