# Spec 13 — `P1-S13-phase1-e2e-boundary-validation`

**Spec name**  
`P1-S13-phase1-e2e-boundary-validation`

**Responsibility**  
Create a cross-runtime acceptance suite that verifies complete Phase 1 behavior from sample CSV ingestion through TypeScript read compatibility.

**Depends on**

- `P1-S07-pipeline-csv-validation-and-rejections`
- `P1-S11-pipeline-sdi-and-decay-publish`
- `P1-S12-typescript-read-model-contracts`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [11-p1-s11-pipeline-sdi-and-decay-publish.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/11-p1-s11-pipeline-sdi-and-decay-publish.md)
- [12-p1-s12-typescript-read-model-contracts.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/12-p1-s12-typescript-read-model-contracts.md)

**Files/artifacts produced**

- End-to-end contract test harness spanning Python pipeline and TypeScript read layer
- Shared sample CSV fixture(s) for positive and invalid-row scenarios
- CI command/task entry that runs Phase 1 acceptance checks
- Documentation note describing expected checkpoint assertions

**In scope**

- End-to-end verification of ingestion success path and rejected-row path
- Assertions for publication of `role_skill_requirements`, `role_requirement_versions`, `sdi_snapshots`, `skill_decay_signals`, `pipeline_jobs`, and `pipeline_rejected_rows`
- Assertions that TypeScript can read prepared outputs after publish

**Out of scope**

- New schema design
- New seed-domain expansion
- New pipeline algorithms
- Admin UI or mobile feature development

**Implementation requirements**

- Tests must use deterministic fixtures and no mandatory LLM dependency
- Acceptance flow must fail clearly when any checkpoint table is missing or empty
- Boundary test must validate both data publication and TypeScript consumption

**Exit criterion (verifiable done condition)**

1. One runnable acceptance command validates full Phase 1 checkpoint outputs.
2. Test confirms invalid rows are rejected with explicit reasons.
3. Test confirms TypeScript read layer successfully reads published prepared outputs.
4. Test confirms pipeline job status is recorded and visible for the run.
