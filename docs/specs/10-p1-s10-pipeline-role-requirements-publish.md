# Spec 10 — `P1-S10-pipeline-role-requirements-publish`

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

- `docs/arch.md`
- `docs/HLD.md`
- `docs/LLD.md`
- `docs/specs/03-p1-s03-db-schema-prepared-intelligence.md`
- `docs/specs/03b-p1-s03b-db-schema-evidence-summary.md`
- `docs/specs/09-p1-s09-pipeline-skill-mapping.md`

**Files/artifacts produced**

- Aggregation module in `apps/data-pipeline/src/intelligence/`
- Evidence summary writer in `apps/data-pipeline/src/publishing/`
- Publishing module in `apps/data-pipeline/src/publishing/`
- Pydantic publish models in `apps/data-pipeline/src/publishing/models/`
- Integration tests in `apps/data-pipeline/src/tests/`

**In scope**

- `role_requirement_aggregator.py` — groups mapped job postings into per-run
  role-skill evidence rows, computes deterministic requirement metrics, writes to
  `pipeline_skill_evidence_summary`, and returns pairs that meet the cumulative threshold
- `evidence_summary_writer.py` — handles inserts to
  `pipeline_skill_evidence_summary` per pipeline run
- `role_requirement_publish_model.py` — Pydantic publish contract for
  `role_skill_requirements` rows
- `role_requirement_publisher.py` — atomically creates a new
  `role_requirement_versions` record and inserts `role_skill_requirements` rows
- `test_role_requirement_publish.py` — integration tests covering aggregation,
  evidence tracking, threshold enforcement, and publish atomicity

**Out of scope — do not touch**

- SDI snapshot computation (that is `P1-S11`)
- Skill decay signal computation (that is `P1-S11`)
- TypeScript read repositories (that is `P1-S12`)
- API endpoints or admin UI
- `pipeline_jobs` terminal status update (owned by orchestrator in `P1-S06`)
- Any file not listed in OUTPUT

**Implementation requirements**

- Evidence count is cumulative across all pipeline runs for a given
  `(role_id, skill_id)` pair. The aggregator reads the sum of `evidence_count`
  from all existing `pipeline_skill_evidence_summary` rows for that pair, adds
  the current run's count, and uses the total for threshold evaluation.
- `threshold_met` is stored on the current run's summary row using the
  cumulative total at write time, not the per-run count alone.
- A role-skill pair is eligible for publishing only when cumulative
  `evidence_count >= 5`.
- `pipeline_skill_evidence_summary` is the source of truth for cumulative counts.
- `role_skill_requirements.evidence_count` must be written as the cumulative
  evidence total for that `(role_id, skill_id)` pair at publish time, including
  the current run.
- `role_requirement_versions.dataset_id` must store the triggering `dataset_id`
  for the pipeline run that created the published version. It identifies the
  producing run, not the full historical provenance of cumulative evidence.
- The mapped output consumed by this slice must provide one normalized
  per-posting depth value in the range `[0.0, 1.0]` for each mapped
  `(job_posting_id, role_id, skill_id)` row. This field is the input to
  `required_depth` aggregation for this slice.
- `required_depth` must be computed as the arithmetic mean of the mapped
  per-posting depth values for a given `(role_id, skill_id)` pair within the
  current pipeline run. Null depth values are excluded. The result is clipped to
  `[0.0, 1.0]` and rounded to persisted precision before validation and insert.
- `demand_weight` must be computed from current-run posting frequency for the
  role. Let:
  `frequency_share = skill_posting_count / total_matched_postings_for_role`
  where `skill_posting_count` is the number of matched postings in the current
  run for the role that contain the skill at least once, and
  `total_matched_postings_for_role` is the total number of matched postings in
  the current run for that role. Then:
  `demand_weight = max(0.1, frequency_share)`
  The result must be clipped to `[0.1, 1.0]` and rounded to persisted precision
  before validation and insert.
- Publishing must be atomic at the version level: either all
  `role_skill_requirements` rows for a version are written and
  `role_requirement_versions.is_current` is flipped, or nothing is committed.
- Unique constraint must be enforced on
  `(role_id, skill_id, requirement_version)`.
- `role_id` must reference a valid `career_roles(id)` FK.
- `skill_id` must reference a valid `skills(id)` FK.
- `requirement_version` must reference a valid
  `role_requirement_versions.version`.
- Check constraints must hold:
  `required_depth >= 0.0 and required_depth <= 1.0`,
  `demand_weight >= 0.1 and demand_weight <= 1.0`,
  `evidence_count >= 0`.
- Publisher must return the created requirement version integer to the caller.
- A failed publish must not create or flip any `role_requirement_versions` row
  to `is_current = true`.
- All transforms must be deterministic for the same input dataset and config.
- Python 3.12, Polars, and Pydantic are the only approved libraries.
- No TypeScript, no HTTP serving, and no student-owned table writes are allowed
  in this spec.

**Decisions already made — do not reopen these in the plan**

- Evidence count is cumulative across datasets, not isolated per dataset.
- `pipeline_skill_evidence_summary` rows are write-once per
  `(pipeline_job_id, role_id, skill_id)`.
- Sub-threshold pairs are visible to admins through
  `pipeline_skill_evidence_summary where threshold_met = false`.
- `role_requirement_versions.is_current` of the previous version is set to false
  in the same transaction before the new version is marked current.
- The version integer is `max(version) + 1` from `role_requirement_versions`
  at publish time.
- Publishing is insert-only for requirement rows; no in-place updates to
  existing versions.
- MVP honesty rule: version allocation via `max(version) + 1` assumes a single
  active role-requirement publish transaction at a time. Concurrent publishes
  are not supported in MVP and may fail with a uniqueness conflict.

**Exit criteria (self-check before each slice commit)**

1. Aggregator reads cumulative evidence from `pipeline_skill_evidence_summary`
   and adds the current run count before threshold evaluation.
2. Evidence summary writer inserts one row per
   `(pipeline_job_id, role_id, skill_id)` with correct `threshold_met` based on
   cumulative total.
3. Pairs where cumulative `evidence_count < 5` are excluded from publish output.
4. Successful publish creates exactly one new `role_requirement_versions` row
   with `is_current = true`.
5. Successful publish inserts the correct `role_skill_requirements` row count.
6. Previous version `is_current` is set to false after new publish.
7. Published `role_skill_requirements.evidence_count` matches the cumulative
   total at publish time.
8. Publish model validates `required_depth` in `[0.0, 1.0]` before any DB call.
9. Publish model validates `demand_weight` in `[0.1, 1.0]` before any DB call.
10. A simulated publish failure leaves no failed-version `is_current = true`
    row and no partial requirement rows committed.
11. Publisher returns the created version integer, and the returned value matches
    `role_requirement_versions.version` in the inserted row.

**OUTPUT**

- `apps/data-pipeline/src/intelligence/role_requirement_aggregator.py`
- `apps/data-pipeline/src/publishing/evidence_summary_writer.py`
- `apps/data-pipeline/src/publishing/models/role_requirement_publish_model.py`
- `apps/data-pipeline/src/publishing/role_requirement_publisher.py`
- `apps/data-pipeline/src/tests/test_role_requirement_publish.py`

---

## Slices

**Slice 1 — Evidence summary writer**  
Files: `apps/data-pipeline/src/publishing/evidence_summary_writer.py`

Self-check:
writer accepts a `pipeline_job_id`, `dataset_id`, and a list of per-run
`(role_id, skill_id, evidence_count)` tuples, reads existing cumulative counts
from `pipeline_skill_evidence_summary`, computes cumulative totals, sets
`threshold_met`, and inserts one row per pair. Duplicate
`(pipeline_job_id, role_id, skill_id)` raises a constraint error. No
aggregation logic lives here.

**Slice 2 — Aggregation logic and Pydantic publish model**  
Files:

- `apps/data-pipeline/src/intelligence/role_requirement_aggregator.py`
- `apps/data-pipeline/src/publishing/models/role_requirement_publish_model.py`

Self-check:
aggregator groups mapped posting-skill rows by `(role_id, skill_id)`,
computes:

- `required_depth` as the mean of mapped per-posting depth values in the current run
- `demand_weight` from current-run `frequency_share`
- per-run evidence counts
  then calls the evidence summary writer, filters to cumulative
  `evidence_count >= 5`, and returns validated `RoleRequirementAggregateRow`
  objects. The Pydantic model enforces depth, weight, and non-negative evidence
  constraints before any DB call.

**Slice 3 — Publisher with atomic transaction**  
Files: `apps/data-pipeline/src/publishing/role_requirement_publisher.py`

Self-check:
publisher opens one transaction, computes `new_version = max(version) + 1`,
inserts the `role_requirement_versions` header with the triggering
`dataset_id`, bulk-inserts all `role_skill_requirements` rows including
cumulative `evidence_count`, sets previous `is_current` to false, sets the new
version `is_current` to true, commits, and returns the new version integer. Any
exception triggers full rollback with no committed version or requirement rows.

**Slice 4 — Integration tests**  
Files: `apps/data-pipeline/src/tests/test_role_requirement_publish.py`

Required test cases:

1. successful publish creates exactly one new `role_requirement_versions` row
   with `is_current = true`
2. successful publish inserts the correct `role_skill_requirements` row count
3. previous version `is_current` is set to false after new publish
4. pair with per-run count `3` and existing cumulative count `2` clears
   threshold and is published
5. pair with per-run count `3` and existing cumulative count `1` does not clear
   threshold and is excluded from publish
6. excluded pair is still written to `pipeline_skill_evidence_summary` with
   `threshold_met = false`
7. published `role_skill_requirements.evidence_count` equals the cumulative
   total at publish time
8. `required_depth` outside `[0.0, 1.0]` raises `Pydantic ValidationError`
   before DB write
9. `demand_weight` below `0.1` raises `Pydantic ValidationError` before DB write
10. invalid `role_id` FK causes transaction rollback with no committed version row
11. returned version integer matches `role_requirement_versions.version` of the
    new row

---

## Process

1. Read all referenced input files before writing any code.
2. Output an implementation plan covering:
   - cumulative evidence read strategy
   - mapped depth input contract and `required_depth` aggregation
   - `frequency_share` and `demand_weight` computation
   - evidence summary writer insert flow and duplicate handling
   - transaction structure for the publisher
   - FK and uniqueness constraint handling
   - test database seeding strategy for all 11 test cases
   - return value contract from publisher to orchestrator
   - explicit note that concurrent publishes are unsupported in MVP
3. Wait for explicit approval of the plan before generating any file.
