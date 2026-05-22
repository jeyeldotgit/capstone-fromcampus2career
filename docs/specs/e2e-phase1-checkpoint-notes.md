# Phase 1 E2E Checkpoint Notes

## Test Database Setup

Provision an isolated Postgres database for the acceptance run, then apply the committed Drizzle SQL migrations through Phase 1 and load the existing taxonomy seeds. The suite expects these seeded aliases to exist:

- career role alias `data analytics specialist`
- skill alias `python3`
- skill alias `sql queries`

Set `DATABASE_URL` before running the suite. For local development, `scripts/run-e2e.sh` also reads `DATABASE_URL` from `apps/data-pipeline/.env` when the variable is not already exported.

Run the full acceptance suite:

```sh
bash scripts/run-e2e.sh
```

The command runs Python first and TypeScript second. It exits non-zero if either suite fails.

## Checkpoints

The Python suite runs both deterministic fixtures in one database:

- `valid_postings.csv`: 10 valid rows, terminal status `complete`
- `mixed_postings.csv`: 10 valid rows plus 2 rejected rows, terminal status `partial`

Expected checkpoint assertions:

1. `pipeline_jobs`
   Valid run: `status = complete`, `processed_rows = 10`, `rejected_rows = 0`, `output_version` is non-null.
   Mixed run: `status = partial`, `processed_rows = 10`, `rejected_rows = 2`, `output_version` is non-null.

2. `pipeline_rejected_rows`
   Valid run: exactly `0` rows for the job.
   Mixed run: exactly `2` rows for the job: row `11` has `EMPTY_REQUIRED_FIELD:company`, row `12` has `EMPTY_REQUIRED_FIELD:url`.

3. `app_events`
   Both runs: exactly one `pipeline.ingestion.completed` row for the job, with payload status matching the terminal job status and payload output version matching `pipeline_jobs.output_version`.

4. `role_requirement_versions`
   Both runs: exactly one version row for the producing dataset.
   Valid run: its version matches the valid job output version and is no longer current after the mixed publish.
   Mixed run: its version matches the mixed job output version and is current.

5. `role_skill_requirements`
   Valid run: exactly `2` rows for the valid output version, both with `evidence_count = 5`.
   Mixed run: exactly `2` rows for the mixed output version, both with cumulative `evidence_count = 10`.

6. `pipeline_skill_evidence_summary`
   Both runs: exactly `2` rows for the job, one per published role-skill pair, each with current-run `evidence_count = 5` and `threshold_met = true`.

7. `sdi_snapshots`
   Both runs: exactly `2` current-run rows for the output version, each with `demand_index` in `[0.0, 1.0]`.

8. `skill_decay_signals`
   Valid run: exactly `2` rows for the valid output version; they become inactive after the mixed publish.
   Mixed run: exactly `2` rows for the mixed output version, each active with `decay_rate` and `confidence` in `[0.0, 1.0]`.

## TypeScript Read Verification

The TypeScript suite does not rerun the pipeline and does not modify tables. It reads the valid and mixed outputs written by Python, then parses:

- every returned `role_skill_requirements` row through `RoleSkillRequirementSchema`
- every returned `sdi_snapshots` row through `SdiSnapshotSchema`
- active decay rows through `SkillDecaySignalSchema`

It also asserts that S12 read repository query builders and repository source files do not reference `job_postings` or `jobPostings`.

## Status Meanings

`complete` means the pipeline published a new output version and recorded zero rejected rows.

`partial` means the pipeline published a new output version and recorded one or more rejected rows.

`failed` means a fatal error prevented successful publish. A failed job must not be treated as a readable prepared-output version.

## Known Limitation

Concurrent role-requirement publish is not supported in the MVP. Version allocation still assumes one active publish transaction at a time.
