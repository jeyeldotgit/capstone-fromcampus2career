# Spec 10 — `P1-S10-pipeline-role-requirements-publish`

**Spec name**  
`P1-S10-pipeline-role-requirements-publish`

**Responsibility**  
Compute role-level skill requirements from mapped pipeline output and publish immutable requirement version snapshots.

**Depends on**

- `P1-S03-db-schema-prepared-intelligence`
- `P1-S06-pipeline-job-orchestration`
- `P1-S09-pipeline-skill-mapping`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [03-p1-s03-db-schema-prepared-intelligence.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/03-p1-s03-db-schema-prepared-intelligence.md)
- [09-p1-s09-pipeline-skill-mapping.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/09-p1-s09-pipeline-skill-mapping.md)

**Files/artifacts produced**

- Aggregation module for requirement computation in `apps/data-pipeline/src/intelligence`
- Publishing module for `role_requirement_versions` and `role_skill_requirements` in `apps/data-pipeline/src/publishing`
- Integration tests validating version creation and row writes

**In scope**

- Requirement aggregation per role-skill pair
- Creation of a new requirement version record
- Insert of corresponding role-skill requirement rows tied to that version
- Return of the produced requirement version as the pipeline job `output_version` handoff to orchestration

**Out of scope**

- SDI snapshot computation
- Skill decay signal computation
- TypeScript read repositories
- API endpoints or UI logic

**Implementation requirements**

- Publication must be versioned and immutable
- All requirement rows must reference a valid published version
- Publish flow must integrate with pipeline job lifecycle output version fields by returning the produced version to the orchestrator
- The orchestrator, not the publishing module, owns the terminal `pipeline_jobs` status update
- A failed publish must not produce a completed job status or a completed ingestion event

**Exit criterion (verifiable done condition)**

1. Pipeline run creates exactly one new requirement version for a publish event.
2. Requirement rows are inserted with valid role, skill, and version references.
3. Tests verify uniqueness constraints and FK integrity on published rows.
4. Publishing returns the created requirement version as `output_version` to the orchestration layer.
5. Pipeline job output version is persisted for successful publish runs through the orchestration completion path.
