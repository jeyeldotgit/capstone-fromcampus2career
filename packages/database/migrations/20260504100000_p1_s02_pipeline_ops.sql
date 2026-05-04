create table "pipeline_jobs" (
  "id" uuid primary key default gen_random_uuid(),
  "dataset_id" uuid not null,
  "job_type" text not null,
  "status" text not null default 'pending',
  "processed_rows" integer not null default 0,
  "rejected_rows" integer not null default 0,
  "output_version" integer,
  "error_message" text,
  "started_at" timestamptz not null default now(),
  "finished_at" timestamptz,
  "created_at" timestamptz not null default now(),
  constraint "pipeline_jobs_dataset_id_fkey" foreign key ("dataset_id") references "market_datasets"("id"),
  constraint "pipeline_jobs_job_type_non_empty_chk" check (char_length(btrim("job_type")) > 0),
  constraint "pipeline_jobs_status_valid_chk" check ("status" in ('pending', 'running', 'complete', 'failed', 'partial')),
  constraint "pipeline_jobs_processed_rows_non_negative_chk" check ("processed_rows" >= 0),
  constraint "pipeline_jobs_rejected_rows_non_negative_chk" check ("rejected_rows" >= 0),
  constraint "pipeline_jobs_output_version_positive_chk" check ("output_version" is null or "output_version" > 0),
  constraint "pipeline_jobs_error_message_non_empty_when_present_chk" check ("error_message" is null or char_length(btrim("error_message")) > 0),
  constraint "pipeline_jobs_finished_at_after_started_at_chk" check ("finished_at" is null or "finished_at" >= "started_at"),
  constraint "pipeline_jobs_terminal_state_fields_chk" check (
    (
      "status" in ('pending', 'running')
      and "finished_at" is null
    )
    or (
      "status" in ('complete', 'partial', 'failed')
      and "finished_at" is not null
    )
  ),
  constraint "pipeline_jobs_output_version_terminal_state_chk" check (
    "output_version" is null or "status" in ('complete', 'partial')
  )
);

create table "pipeline_rejected_rows" (
  "id" uuid primary key default gen_random_uuid(),
  "pipeline_job_id" uuid not null,
  "row_number" integer not null,
  "raw_payload" jsonb not null,
  "reason" text not null,
  "created_at" timestamptz not null default now(),
  constraint "pipeline_rejected_rows_pipeline_job_id_fkey" foreign key ("pipeline_job_id") references "pipeline_jobs"("id"),
  constraint "pipeline_rejected_rows_pipeline_job_id_row_number_unique" unique ("pipeline_job_id", "row_number"),
  constraint "pipeline_rejected_rows_row_number_positive_chk" check ("row_number" > 0),
  constraint "pipeline_rejected_rows_reason_non_empty_chk" check (char_length(btrim("reason")) > 0)
);

create index "pipeline_jobs_dataset_id_created_at_idx" on "pipeline_jobs" ("dataset_id", "created_at");
create index "pipeline_jobs_status_created_at_idx" on "pipeline_jobs" ("status", "created_at");
create index "pipeline_jobs_output_version_idx" on "pipeline_jobs" ("output_version");
create index "pipeline_rejected_rows_pipeline_job_id_idx" on "pipeline_rejected_rows" ("pipeline_job_id");
