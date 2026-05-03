# Spec 08 — `P1-S08-pipeline-clean-normalize-dedupe`

**Spec name**  
`P1-S08-pipeline-clean-normalize-dedupe`

**Responsibility**  
Implement deterministic cleaning, canonical normalization, and deduplication for valid job-posting rows.

**Depends on**

- `P1-S04-seed-taxonomy-base`
- `P1-S07-pipeline-csv-validation-and-rejections`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [07-p1-s07-pipeline-csv-validation-and-rejections.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/07-p1-s07-pipeline-csv-validation-and-rejections.md)

**Files/artifacts produced**

- Cleaning/normalization modules in `apps/data-pipeline/src/normalization`
- Deduplication strategy implementation in `apps/data-pipeline/src/ingestion` or `src/normalization`
- Unit tests with duplicate/variant fixture rows in `apps/data-pipeline/tests`

**In scope**

- Text cleanup and canonical normalization for titles, role hints, and skill text tokens
- Deterministic duplicate detection and stable record selection
- Structured output of normalized rows for downstream skill mapping

**Out of scope**

- CSV schema validation
- Skill extraction/mapping to canonical skill IDs
- Role requirement aggregation and publishing
- TypeScript read contracts

**Implementation requirements**

- Normalization behavior must be deterministic across repeated runs
- Deduplication criteria must be explicit and test-covered
- Stage outputs must remain typed and ready for next pipeline stage

**Exit criterion (verifiable done condition)**

1. Fixture input with known duplicates produces the expected unique normalized set.
2. Repeated execution on identical input yields byte-equivalent normalized outputs.
3. Tests cover punctuation/case variance and duplicate collision scenarios.
4. No publishing or TypeScript logic is introduced.
