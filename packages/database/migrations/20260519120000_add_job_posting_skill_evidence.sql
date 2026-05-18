create table "job_postings" (
  "id" uuid primary key default gen_random_uuid(),
  "dataset_id" uuid not null,
  "source" text not null,
  "title" text not null,
  "company" text not null,
  "raw_text" text not null,
  "role_id" uuid not null,
  "posted_at" date not null,
  "ingested_at" timestamptz not null default now(),
  constraint "job_postings_dataset_id_fkey" foreign key ("dataset_id") references "market_datasets"("id"),
  constraint "job_postings_role_id_fkey" foreign key ("role_id") references "career_roles"("id"),
  constraint "job_postings_source_title_company_posted_at_unique" unique ("source", "title", "company", "posted_at"),
  constraint "job_postings_source_non_empty_chk" check (char_length(btrim("source")) > 0),
  constraint "job_postings_title_non_empty_chk" check (char_length(btrim("title")) > 0),
  constraint "job_postings_company_non_empty_chk" check (char_length(btrim("company")) > 0),
  constraint "job_postings_raw_text_non_empty_chk" check (char_length(btrim("raw_text")) > 0)
);

create table "job_posting_skills" (
  "id" uuid primary key default gen_random_uuid(),
  "job_posting_id" uuid not null,
  "role_id" uuid not null,
  "skill_id" uuid not null,
  "normalized_depth" numeric(5,4),
  "created_at" timestamptz not null default now(),
  constraint "job_posting_skills_job_posting_id_fkey" foreign key ("job_posting_id") references "job_postings"("id"),
  constraint "job_posting_skills_role_id_fkey" foreign key ("role_id") references "career_roles"("id"),
  constraint "job_posting_skills_skill_id_fkey" foreign key ("skill_id") references "skills"("id"),
  constraint "job_posting_skills_posting_role_skill_unique" unique ("job_posting_id", "role_id", "skill_id"),
  constraint "job_posting_skills_normalized_depth_range_chk" check (
    "normalized_depth" is null or ("normalized_depth" >= 0 and "normalized_depth" <= 1)
  )
);

create index "job_postings_dataset_role_posted_at_idx" on "job_postings" ("dataset_id", "role_id", "posted_at");
create index "job_postings_role_posted_at_idx" on "job_postings" ("role_id", "posted_at");
create index "job_posting_skills_role_skill_idx" on "job_posting_skills" ("role_id", "skill_id");
create index "job_posting_skills_skill_id_idx" on "job_posting_skills" ("skill_id");
