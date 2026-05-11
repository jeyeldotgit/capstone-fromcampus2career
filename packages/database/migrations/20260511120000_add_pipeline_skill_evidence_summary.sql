create table "pipeline_skill_evidence_summary" (
  "id" uuid primary key,
  "dataset_id" uuid not null,
  "pipeline_job_id" uuid not null,
  "role_id" uuid not null,
  "skill_id" uuid not null,
  "evidence_count" integer not null,
  "threshold_met" boolean not null default false,
  "created_at" timestamptz not null default now(),
  constraint "pipeline_skill_evidence_summary_dataset_id_fkey" foreign key ("dataset_id") references "market_datasets"("id"),
  constraint "pipeline_skill_evidence_summary_pipeline_job_id_fkey" foreign key ("pipeline_job_id") references "pipeline_jobs"("id"),
  constraint "pipeline_skill_evidence_summary_role_id_fkey" foreign key ("role_id") references "career_roles"("id"),
  constraint "pipeline_skill_evidence_summary_skill_id_fkey" foreign key ("skill_id") references "skills"("id"),
  constraint "pipeline_skill_evidence_summary_job_role_skill_unique" unique ("pipeline_job_id", "role_id", "skill_id"),
  constraint "pipeline_skill_evidence_summary_evidence_count_non_negative_chk" check ("evidence_count" >= 0)
);

create index "pipeline_skill_evidence_summary_role_skill_idx" on "pipeline_skill_evidence_summary" ("role_id", "skill_id");
create index "pipeline_skill_evidence_summary_dataset_id_idx" on "pipeline_skill_evidence_summary" ("dataset_id");
create index "pipeline_skill_evidence_summary_pipeline_job_id_idx" on "pipeline_skill_evidence_summary" ("pipeline_job_id");
