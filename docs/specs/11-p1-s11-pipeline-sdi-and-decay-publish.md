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

**Implementation requirements**

- Numeric outputs must be deterministic for identical input fixtures
- Published rows must reference the relevant requirement version
- Constraints for date/version uniqueness must be respected

**Exit criterion (verifiable done condition)**

1. A successful run publishes rows to both `sdi_snapshots` and `skill_decay_signals`.
2. Tests assert published numeric ranges and required non-null fields.
3. Tests confirm all published rows have valid requirement-version linkage.
4. No TypeScript or UI-layer logic is implemented in this spec.
