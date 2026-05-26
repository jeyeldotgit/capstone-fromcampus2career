# Spec 16 - `P1-S16-admin-readiness-contract-patch`

**Spec name**  
`P1-S16-admin-readiness-contract-patch`

**Responsibility**  
Apply a focused contract patch after Phase 1 so MVP Admin backend routes can implement storyboard behavior without violating existing schema constraints.

**Depends on**

- `P1-S15-monthly-intelligence-versioning-and-lineage`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [arch.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/arch.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [15-p1-s15-monthly-intelligence-versioning-and-lineage.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/15-p1-s15-monthly-intelligence-versioning-and-lineage.md)

**Files/artifacts produced**

- Drizzle schema updates in `packages/database/src/schema`
- Forward-only SQL migration in `packages/database/migrations`
- Shared contract updates in `packages/shared/src/contracts`
- Python publish/parse updates for decay-rate contract compatibility
- TypeScript repository/contract tests for changed boundaries
- Documentation alignment updates in `docs/arch.md` and `docs/LLD.md`

**In scope**

- Allow dismissed skill aliases without `skill_id`
- Add review state to career role aliases
- Add `source_url` to dataset metadata contract
- Convert decay-rate contract to signed decline slope
- Align documented depth-weight range and evidence-display behavior

**Out of scope**

- New admin route implementation
- New frontend implementation
- Recommendation catalog expansion
- User-role administration features

**Implementation requirements**

- Replace `skill_aliases_reviewed_requires_skill_id_chk` with a status-safe model that permits:
  - `pending`: `reviewed = false`, `skill_id = null`
  - `approved`: `reviewed = true`, `skill_id != null`
  - `dismissed`: `reviewed = true`, `skill_id = null`
- Add `career_role_aliases.reviewed boolean not null default true`.
- Add `market_datasets.source_url text null` with non-empty check when present.
- Store `skill_decay_signals.decay_rate` as signed slope in `[-1.0000, 0.0000]`.
- Migrate existing decay-rate values to signed form without data loss.
- Keep all migrations forward-only and add tests for each changed constraint.

**Exit criterion (verifiable done condition)**

1. Migration applies cleanly and preserves existing rows.
2. Tests prove skill alias dismissal is valid and approval still requires skill linkage.
3. Tests prove career role alias review state persists and defaults correctly.
4. Tests prove dataset `source_url` contract validates and round-trips.
5. Tests prove decay-rate contract accepts signed values and rejects out-of-range values.
6. Updated docs explicitly state course depth range `0.01..1.00` and that below-threshold requirement evidence is read from evidence-summary surfaces.

