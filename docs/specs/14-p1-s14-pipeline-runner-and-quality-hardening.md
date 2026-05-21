# Spec 14 — `P1-S14-pipeline-runner-and-quality-hardening`

**Spec name**  
`P1-S14-pipeline-runner-and-quality-hardening`

**Responsibility**  
Close the final Phase 1 pipeline-operability and data-quality gaps found during local JobStreet CSV smoke testing by adding a formal manual runner, source adapter, matching safeguards, and confidence reporting.

**Depends on**

- `P1-S07-pipeline-csv-validation-and-rejections`
- `P1-S08-pipeline-clean-normalize-dedupe`
- `P1-S09-pipeline-skill-mapping`
- `P1-S11-pipeline-sdi-and-decay-publish`
- `P1-S13-phase1-e2e-boundary-validation`

**Inputs**

- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [13-p1-s13-phase1-e2e-boundary-validation.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/specs/13-p1-s13-phase1-e2e-boundary-validation.md)
- Smoke-tested JobStreet fixtures in `apps/data-pipeline/tests/ingestion/fixtures`

**Files/artifacts produced**

- Manual local pipeline runner entrypoint in `apps/data-pipeline/src/main.py` or a dedicated CLI module
- JobStreet CSV adapter module that maps scraped source columns into the canonical `RawJobPosting` input contract
- Pipeline smoke report output format with stage counters and confidence score
- Tests for adapter mapping, dry-run/rollback execution, role match coverage, and skill match precision guards
- Documentation note describing how to run a local CSV pipeline smoke test safely

**In scope**

- A formal command for local/manual CSV smoke runs, for example `uv run python -m src.main --csv-path <path> --source jobstreet --dry-run`
- Safe dry-run or rollback mode that is the default for local smoke testing
- JobStreet column mapping:
  - `posting_id` -> `external_id`
  - `platform` or `source_dataset` -> `source`
  - `posted_date` -> `posted_at`
  - source-specific optional fields mapped only when compatible with existing contracts
- Month-only `posted_date` normalization, such as `2026-04` -> `2026-04-01`
- Stage counters for validation, normalization, dedupe, role matching, skill matching, evidence rows, requirement rows, SDI rows, decay rows, and terminal status
- Confidence score calculation based on explicit stage metrics
- Token-aware or boundary-aware skill alias matching safeguards for short aliases such as `Go`
- Role-matching gap report for unmatched source roles, including examples such as `Systems Analyst`, `Cybersecurity Engineer`, and `IT Support`
- Historical fixture setup or deterministic test data to prove decay detection can produce and publish a signal when enough SDI history exists

**Out of scope**

- New database migrations
- Student-owned tables or student request-response flows
- Admin UI or mobile UI changes
- Mandatory LLM-based extraction or matching
- Large-scale taxonomy redesign
- Production Cloud Run scheduling or Supabase Storage upload flow

**Implementation requirements**

- The local runner must default to non-destructive dry-run or rollback behavior.
- Persistent live DB writes must require an explicit flag that is clearly named and documented.
- The runner must not write to student-owned transactional tables.
- The JobStreet adapter must be deterministic and covered by tests.
- Runtime validation must still use the canonical `RawJobPosting` contract after adaptation.
- Skill matching must avoid substring-only false positives for short aliases and must include regression tests for known risky aliases.
- Confidence scoring must be transparent, documented, and based on emitted counters rather than opaque model confidence.
- The smoke report must clearly distinguish structural pipeline confidence from intelligence-quality confidence.
- The runner must emit enough counters to diagnose failures without manually querying the database.
- Decay validation must not require real historical production data; deterministic fixtures are acceptable.

**Observed gaps from smoke testing**

1. No committed `--csv-path` local pipeline runner exists; `src.main` currently does not execute the full pipeline.
2. JobStreet CSV files require temporary source-column mapping before the existing validator can accept them.
3. Role matching does not cover all observed source roles; sample unmatched roles include `Systems Analyst`, `Cybersecurity Engineer`, and `IT Support`.
4. Skill matching can overmatch when aliases are short or broad; `Go` is a known risk case.
5. Decay detection is structurally present but needs multi-period fixture coverage to validate an end-to-end positive decay signal.

**Exit criterion (verifiable done condition)**

1. A documented local command can run a JobStreet CSV fixture through the full Phase 1 pipeline flow in dry-run or rollback mode.
2. The command emits a structured report with stage counters, confidence score, top matched roles, top matched skills, unmatched-role examples, and terminal status.
3. Adapter tests prove JobStreet fixtures map into the canonical raw posting contract with zero unexpected validation failures.
4. Matching guard tests prove short aliases do not produce substring-only false positives.
5. Smoke tests prove the April and May JobStreet fixtures reach prepared-output publication steps in rollback mode without persistent DB writes.
6. A deterministic decay fixture produces at least one published decay signal in test mode.
7. Documentation explains when a smoke result is safe to trust structurally and when intelligence quality still needs taxonomy or matcher review.
