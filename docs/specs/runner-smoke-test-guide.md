# Local Pipeline Runner Smoke Test Guide

## Purpose

Use the local runner to smoke test a CSV through the Phase 1 market pipeline before promoting a run pattern to scheduled operations. The runner exercises ingestion, validation, normalization, deduplication, role matching, skill matching, evidence aggregation, requirement publishing, SDI publishing, and decay detection.

The default mode is dry-run. It executes the full pipeline and rolls back all database writes before exit.

## Commands

Dry-run JobStreet smoke test:

```bash
uv run python -m src.runner --csv-path apps/data-pipeline/tests/ingestion/fixtures/05-2026_jobstreet_dataset.csv --source jobstreet --dry-run
```

Equivalent dry-run command, relying on the default mode:

```bash
uv run python -m src.runner --csv-path apps/data-pipeline/tests/ingestion/fixtures/05-2026_jobstreet_dataset.csv --source jobstreet
```

Live run with persistent writes:

```bash
uv run python -m src.runner --csv-path apps/data-pipeline/tests/ingestion/fixtures/05-2026_jobstreet_dataset.csv --source jobstreet --live
```

Only use `--live` against an intended database. Dry-run wraps the full run in one transaction and rolls it back after the report is emitted.

## Flags

- `--csv-path`: Required path to the local CSV file.
- `--source`: Required source adapter. Use `jobstreet` for scraped JobStreet files. Use `canonical` only for files already matching the canonical `RawJobPosting` CSV contract.
- `--dry-run`: Runs all stages and rolls back writes before exit. This is the default.
- `--live`: Explicit opt-in for persistent database writes.

## Report Fields

- `rows_read_from_source_csv`: Physical rows loaded from the source CSV.
- `rows_passing_adapter_mapping`: Rows successfully mapped from source columns into canonical pipeline input fields.
- `rows_passing_raw_job_posting_validation`: Rows accepted by the canonical `RawJobPosting` validation contract.
- `rows_rejected_by_validation`: Rows rejected before downstream stages.
- `top_validation_rejection_reasons`: Up to five most frequent rejection reasons.
- `rows_surviving_deduplication`: Valid rows left after deterministic deduplication.
- `rows_matched_to_canonical_role`: Deduplicated rows matched to a seeded career role.
- `rows_unmatched_to_any_role`: Deduplicated rows with no role match.
- `unmatched_source_role_examples`: Up to five source role strings for taxonomy review.
- `skill_matches_produced`: Canonical skill matches emitted by deterministic matching.
- `evidence_rows_written_to_pipeline_skill_evidence_summary`: Role-skill evidence summary rows written for the run.
- `role_skill_pairs_meeting_cumulative_evidence_threshold`: Role-skill pairs with cumulative evidence at or above the publishing threshold.
- `role_skill_requirements_rows_published`: Prepared role-skill requirement rows published for the new version.
- `sdi_snapshots_rows_published`: SDI snapshot rows published for the new version.
- `skill_decay_signals_rows_published_or_activated`: Decay signal rows published as active.
- `terminal_pipeline_job_status`: Final job state, one of `complete`, `partial`, or `failed`.

## Confidence Score

The report labels its score as `structural_pipeline_confidence`.

Formula:

```txt
structural_pipeline_confidence =
  0.35 * validation_pass_rate
+ 0.35 * role_match_rate
+ 0.30 * skill_match_rate
```

Inputs:

```txt
validation_pass_rate = rows_passing_raw_job_posting_validation / rows_read_from_source_csv
role_match_rate = rows_matched_to_canonical_role / rows_surviving_deduplication
skill_match_rate = min(skill_matches_produced / rows_surviving_deduplication, 1.0)
```

The recommended manual-review threshold is `0.80`. A score below `0.80` means the pipeline shape is weak enough that an operator should review source mapping, seeded role aliases, seeded skill aliases, and matcher behavior before trusting the output.

## Structural Confidence Is Not Intelligence Quality

Structural confidence answers: did rows flow through the expected stages, and did the pipeline produce prepared outputs at plausible coverage?

It does not answer: are the taxonomy and matcher complete enough to represent the market correctly?

When confidence is low, review unmatched roles and low skill coverage. Known JobStreet examples that may require taxonomy expansion or alias review include:

- `Systems Analyst`
- `Cybersecurity Engineer`
- `IT Support`

Even with a high structural score, sample published role-skill requirements should be reviewed for semantic fit before relying on them for product intelligence.
