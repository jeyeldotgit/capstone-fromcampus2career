# Spec P1-S10 — `P1-S10-pipeline-role-requirements-publish` (updated)

**Spec name**
`P1-S10-pipeline-role-requirements-publish`

**Responsibility**
Compute role-level skill requirements from mapped pipeline output using cumulative
evidence tracking and publish immutable requirement version snapshots.

**Depends on**

- `P1-S03-db-schema-prepared-intelligence`
- `P1-S03b-db-schema-evidence-summary`
- `P1-S06-pipeline-job-orchestration`
- `P1-S09-pipeline-skill-mapping`

All four must be merged into main before starting.

**Inputs**

- docs/arch.md
- docs/HLD.md
- docs/LLD.md
- docs/specs/03-p1-s03-db-schema-prepared-intelligence.md
- docs/specs/03b-p1-s03b-db-schema-evidence-summary.md
- docs/specs/09-p1-s09-pipeline-skill-mapping.md

**Files/artifacts produced**

- Aggregation module in `apps/data-pipeline/src/intelligence/`
- Evidence summary writer in `apps/data-pipeline/src/publishing/`
- Publishing module in `apps/data-pipeline/src/publishing/`
- Pydantic publish models in `apps/data-pipeline/src/publishing/models/`
- Integration tests in `apps/data-pipeline/src/tests/`

**In scope**

- `role_requirement_aggregator.py` — groups mapped job postings into per-run
  role-skill evidence rows, writes to `pipeline_skill_evidence_summary`,
  and returns pairs that meet the cumulative threshold
- `evidence_summary_writer.py` — handles inserts to
  `pipeline_skill_evidence_summary` per pipeline run
- `role_requirement_publish_model.py` — Pydantic publish contract for
  role-skill requirement rows
- `role_requirement_publisher.py` — atomically creates a new
  `role_requirement_versions` record and inserts `role_skill_requirements` rows
- `test_role_requirement_publish.py` — integration tests covering aggregation,
  evidence tracking, threshold enforcement, and publish atomicity

**Out of scope — do not touch**

- SDI snapshot computation (that is P1-S11)
- Skill decay signal computation (that is P1-S12)
- TypeScript read repositories (that is P1-S14)
- API endpoints or admin UI
- `pipeline_jobs` terminal status update (owned by orchestrator in P1-S06)
- Any file not listed in OUTPUT

**Implementation requirements**

- Evidence count is cumulative across all pipeline runs for a given
  `(role_id, skill_id)` pair — the aggregator reads the sum of
  `evidence_count` from all existing `pipeline_skill_evidence_summary` rows
  for that pair, adds the current run's count, and uses the total for
  threshold evaluation
- `threshold_met` is stored on the current run's summary row using the
  cumulative total at write time, not the per-run count alone
- A role-skill pair is eligible for publishing only when cumulative
  `evidence_count >= 5`
- Publishing must be atomic at the version level: either all
  `role_skill_requirements` rows for a version are written and
  `role_requirement_versions.is_current` is flipped, or nothing is committed
- `required_depth` must be normalized to the range `0.0` to `1.0` (inclusive)
- `demand_weight` must be normalized to the range `0.1` to `1.0` (inclusive)
- Unique constraint must be enforced on `(role_id, skill_id, requirement_version)`
- `role_id` must reference a valid `career_roles(id)` FK
- `skill_id` must reference a valid `skills(id)` FK
- `requirement_version` must reference a valid `role_requirement_versions.version`
- check: `required_depth >= 0.0` and `required_depth <= 1.0`
- check: `demand_weight >= 0.1` and `demand_weight <= 1.0`
- check: `evidence_count >= 0`
- Publisher must return the created requirement version integer to the caller
- The orchestrator, not the publisher, owns the terminal `pipeline_jobs`
  status update
- A failed publish must not create or flip any `role_requirement_versions` row
  to `is_current = true`
- All transforms must be deterministic for the same input dataset and config
- Python 3.12, Polars, and Pydantic are the only approved libraries
- No TypeScript, no HTTP serving, no student-owned table writes in this spec

**DECISIONS ALREADY MADE — do not reopen these in the plan**

- Evidence count is cumulative across datasets, not isolated per dataset
- `pipeline_skill_evidence_summary` is the source of truth for cumulative counts
- `threshold_met` is computed and stored at write time using the cumulative total
- `pipeline_skill_evidence_summary` rows are write-once per
  `(pipeline_job_id, role_id, skill_id)`
- Sub-threshold pairs are visible to admins through
  `pipeline_skill_evidence_summary` where `threshold_met = false`
- `role_requirement_versions.is_current` of the previous version is set to false
  in the same transaction before the new version is marked current
- The version integer is `max(version) + 1` from `role_requirement_versions`
  at publish time
- Publishing is insert-only for requirement rows; no in-place updates to
  existing versions

**EXIT CRITERIA (self-check before each slice commit)**

- [ ] Aggregator reads cumulative evidence from `pipeline_skill_evidence_summary`
      and adds the current run count before threshold evaluation
- [ ] Evidence summary writer inserts one row per `(pipeline_job_id, role_id, skill_id)`
      with correct `threshold_met` value based on cumulative total
- [ ] Pairs where cumulative `evidence_count < 5` are excluded from publish output
- [ ] Publish model validates depth range `0.0–1.0` and weight range `0.1–1.0`
      at Pydantic level before any DB call
- [ ] Publisher inserts version header and all requirement rows in one transaction
- [ ] Publisher flips previous `is_current` to false before setting new version
      to true in the same transaction
- [ ] Publisher returns the created version integer to the caller
- [ ] A simulated publish failure leaves no `is_current = true` row and no
      partial requirement rows committed
- [ ] Integration tests cover: successful publish, cumulative evidence threshold,
      per-run sub-threshold tracking, depth/weight boundary values, FK violation
      handling, transaction rollback on failure
- [ ] No SDI, decay, or TypeScript files are created or modified

**OUTPUT**

- apps/data-pipeline/src/intelligence/role_requirement_aggregator.py
- apps/data-pipeline/src/publishing/evidence_summary_writer.py
- apps/data-pipeline/src/publishing/models/role_requirement_publish_model.py
- apps/data-pipeline/src/publishing/role_requirement_publisher.py
- apps/data-pipeline/src/tests/test_role_requirement_publish.py

---

SLICES:

Slice 1 — Evidence summary writer
Files: apps/data-pipeline/src/publishing/evidence_summary_writer.py
Commit: feat(pipeline): add evidence summary writer for per-run skill evidence tracking
Commit body must include:
Implements: P1-S10-pipeline-role-requirements-publish
Depends on: P1-S03b-db-schema-evidence-summary
Self-check: writer accepts a pipeline_job_id, dataset_id, and a list of
per-run `(role_id, skill_id, evidence_count)` tuples, reads the existing
cumulative count for each pair from `pipeline_skill_evidence_summary`,
computes the cumulative total, sets `threshold_met` accordingly, and inserts
one row per pair. Duplicate `(pipeline_job_id, role_id, skill_id)` raises
a constraint error. No aggregation logic lives here.

Slice 2 — Aggregation logic and Pydantic publish model
Files:
apps/data-pipeline/src/intelligence/role_requirement_aggregator.py
apps/data-pipeline/src/publishing/models/role_requirement_publish_model.py
Commit: feat(pipeline): add role requirement aggregator and publish model
Commit body must include:
Implements: P1-S10-pipeline-role-requirements-publish
Depends on: P1-S09-pipeline-skill-mapping, P1-S03b-db-schema-evidence-summary
Self-check: aggregator groups mapped job postings by `(role_id, skill_id)`,
computes per-run depth and weight values, calls evidence summary writer to
persist and retrieve cumulative counts, filters to pairs where cumulative
`evidence_count >= 5`, and returns a list of validated
`RoleRequirementAggregateRow` objects. Pydantic model enforces depth in
`[0.0, 1.0]` and weight in `[0.1, 1.0]` with validation errors before
any DB call.

Slice 3 — Publisher with atomic transaction
Files: apps/data-pipeline/src/publishing/role_requirement_publisher.py
Commit: feat(pipeline): add atomic role requirement publisher
Commit body must include:
Implements: P1-S10-pipeline-role-requirements-publish
Depends on: P1-S03-db-schema-prepared-intelligence
Self-check: publisher opens one transaction, inserts `role_requirement_versions`
header row, bulk-inserts all `role_skill_requirements` rows, sets previous
`is_current` to false, sets new version `is_current` to true, commits, and
returns the new version integer. Any exception triggers full rollback with no
committed version or requirement rows.

Slice 4 — Integration tests
Files: apps/data-pipeline/src/tests/test_role_requirement_publish.py
Required test cases: - successful publish creates exactly one new role_requirement_versions row
with is_current = true - successful publish inserts correct role_skill_requirements row count - previous version is_current is set to false after new publish - pair with per-run count of 3 and existing cumulative count of 2 clears
threshold and is published (total = 5) - pair with per-run count of 3 and existing cumulative count of 1 does not
clear threshold and is excluded from publish (total = 4) - excluded pair is still written to pipeline_skill_evidence_summary with
threshold_met = false - required_depth outside [0.0, 1.0] raises Pydantic ValidationError
before DB write - demand_weight below 0.1 raises Pydantic ValidationError before DB write - invalid role_id FK causes transaction rollback with no committed
version row - publish failure leaves no is_current = true row for the failed version - returned version integer matches role_requirement_versions.version
of the new row
Commit: test(pipeline): add role requirement publish integration tests
Commit body must include:
Implements: P1-S10-pipeline-role-requirements-publish
Depends on: P1-S03b-db-schema-evidence-summary
Self-check: all 11 test cases pass with pytest against a test database seeded
with valid career_roles, skills, market_datasets, and pipeline_jobs rows.
No SDI or decay tables are touched in any test.

WORKFLOW:

1. Branch from: main
   Confirm P1-S03, P1-S03b, P1-S06, and P1-S09 are all merged before branching
2. Branch name: feat/p1-s10-pipeline-role-requirements-publish
3. Implement and commit slices in order: slice-1, slice-2, slice-3, slice-4
4. Each slice must pass its own self-check before its commit
5. Do NOT push or open PR — stop after all 4 commits and report done

PROCESS:

1. Read all referenced input files before writing any code
2. Output an implementation plan covering:
   - cumulative evidence read strategy: how the aggregator queries existing
     summary rows before writing the current run
   - depth averaging strategy across job postings within the current run
   - demand_weight normalization formula
   - evidence summary writer insert flow and duplicate handling
   - transaction structure for the publisher: version header, bulk insert,
     is_current flip order, rollback guarantee
   - FK and uniqueness constraint handling: how violations are caught
     and surfaced
   - test database seeding strategy: minimum seed data for all 11 test cases
   - return value contract: how the version integer flows from publisher
     to the orchestration caller
3. Wait for explicit approval of the plan before generating any file
