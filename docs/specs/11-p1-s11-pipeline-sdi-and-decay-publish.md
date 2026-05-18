# Spec 11 — `P1-S11-pipeline-sdi-and-decay-publish`

**Spec name**  
`P1-S11-pipeline-sdi-and-decay-publish`

**Responsibility**  
Compute and publish SDI snapshots and baseline skill-decay signals for the latest published requirement version.

**Depends on**

- `P1-S03-db-schema-prepared-intelligence`
- `P1-S10-pipeline-role-requirements-publish`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [10-p1-s10-pipeline-role-requirements-publish.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/10-p1-s10-pipeline-role-requirements-publish.md)
- `job_postings` rows produced by prior ingestion and normalization stages, filtered to
  the current dataset/window for SDI frequency, recency, and growth inputs
- Historical `sdi_snapshots` rows for decay slope calculation

**Files/artifacts produced**

- SDI computation module in `apps/data-pipeline/src/intelligence`
- Decay detection module in `apps/data-pipeline/src/intelligence`
- Publishing module updates in `apps/data-pipeline/src/publishing` for `sdi_snapshots` and `skill_decay_signals`
- Integration tests for version linkage and numeric bounds

**In scope**

- SDI calculation logic and snapshot generation
- Baseline decay signal detection and confidence scoring
- Writes to prepared output tables using requirement-version linkage

**Out of scope**

- Requirement aggregation logic
- CSV ingestion validation
- TypeScript read-layer interfaces
- Admin or student API endpoints
- `pipeline_jobs` terminal status or `output_version` writes; this remains owned
  by `P1-S06-pipeline-job-orchestration`
- Terminal `app_events` emission; this remains owned by
  `P1-S06-pipeline-job-orchestration`

**Context notes**

- `P1-S06` owns pipeline job finalization. S11 publish functions must return the
  requirement version integer they published against so the orchestrator can store
  it as `pipeline_jobs.output_version`.
- S11 must not write to `pipeline_jobs` or `app_events` directly.
- S11 does not create a new `role_requirement_versions` row. It publishes SDI
  and decay rows linked to the latest requirement version produced by S10.

**Implementation requirements**

- Numeric outputs must be deterministic for identical input fixtures
- Published rows must reference the relevant requirement version
- Constraints for date/version uniqueness must be respected
- The publish entrypoint must return a non-null integer `output_version`, equal
  to the requirement version used for the published SDI and decay rows
- SDI computation must derive `frequency_share`, `recency_score`, and
  `growth_score` from posting-level data in `job_postings` for the current
  dataset/window, following the formula in `arch.md` Section 9
- Decay detection must read historical `sdi_snapshots` across prior requirement
  versions to compute the rolling SDI slope
- Same-day `sdi_snapshots` reruns must be deterministic and idempotent. If an
  incoming `(role_id, skill_id, snapshot_date)` row already exists with the same
  `demand_index` and `requirement_version`, the publisher may treat it as
  already published. If the existing row differs, the publisher must raise a
  conflict rather than silently overwriting immutable published intelligence.
- Decay publishing must deactivate prior active `skill_decay_signals` for the
  same `(role_id, skill_id)` in the same transaction as inserting the new active
  signal row

**Exit criterion (verifiable done condition)**

1. A successful run publishes rows to both `sdi_snapshots` and `skill_decay_signals`.
2. Tests assert published numeric ranges and required non-null fields.
3. Tests confirm all published rows have valid requirement-version linkage.
4. Tests confirm the publish entrypoint returns a non-null integer
   `output_version` consumable by the S06 orchestrator.
5. Tests confirm S11 does not write to `pipeline_jobs` or `app_events`.
6. Tests confirm same-day SDI reruns do not create duplicate
   `(role_id, skill_id, snapshot_date)` rows and raise a conflict when incoming
   values differ from the existing row.
7. Tests confirm rerunning decay for the same `(role_id, skill_id)` leaves only
   one active `skill_decay_signals` row.
8. No TypeScript or UI-layer logic is implemented in this spec.
