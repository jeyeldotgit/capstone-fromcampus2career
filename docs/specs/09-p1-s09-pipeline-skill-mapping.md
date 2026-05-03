# Spec 09 — `P1-S09-pipeline-skill-mapping`

**Spec name**  
`P1-S09-pipeline-skill-mapping`

**Responsibility**  
Implement deterministic skill extraction or alias-based mapping from normalized postings to canonical `skills`.

**Depends on**

- `P1-S04-seed-taxonomy-base`
- `P1-S08-pipeline-clean-normalize-dedupe`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [08-p1-s08-pipeline-clean-normalize-dedupe.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/08-p1-s08-pipeline-clean-normalize-dedupe.md)

**Files/artifacts produced**

- Skill mapping module(s) in `apps/data-pipeline/src/intelligence` or `src/normalization`
- Alias lookup helper(s) using seeded taxonomy data
- Unit tests for exact/alias matches and unknown skill handling

**In scope**

- Canonical skill ID resolution from normalized textual signals
- Deterministic handling path for unknown or unmapped terms
- Output structure required for requirement aggregation stage

**Out of scope**

- CSV header validation and row rejection
- Deduplication implementation
- Role requirement version publishing
- TypeScript read/query contracts

**Implementation requirements**

- Mapping must rely on deterministic rules, not mandatory LLM inference
- Alias matching must use seeded alias tables consistently
- Unknown-skill behavior must be explicit and test-covered

**Exit criterion (verifiable done condition)**

1. Fixture postings map to expected canonical skill IDs.
2. Tests verify alias-based mapping and unmapped-term behavior.
3. Mapping output contains all fields required by aggregation/publishing stages.
4. No prepared-table writes happen in this stage.
