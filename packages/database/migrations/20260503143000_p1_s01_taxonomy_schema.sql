create extension if not exists pgcrypto;

create table "skills" (
  "id" uuid primary key default gen_random_uuid(),
  "name" text not null,
  "category" text,
  "is_active" boolean not null default true,
  "created_at" timestamptz not null default now(),
  constraint "skills_name_unique" unique ("name"),
  constraint "skills_name_non_empty_chk" check (char_length(btrim("name")) > 0)
);

create table "career_roles" (
  "id" uuid primary key default gen_random_uuid(),
  "title" text not null,
  "description" text,
  "is_active" boolean not null default true,
  "created_at" timestamptz not null default now(),
  constraint "career_roles_title_unique" unique ("title"),
  constraint "career_roles_title_non_empty_chk" check (char_length(btrim("title")) > 0)
);

create table "courses" (
  "id" uuid primary key default gen_random_uuid(),
  "code" text not null,
  "title" text not null,
  "units" integer,
  "description" text,
  "is_active" boolean not null default true,
  "created_at" timestamptz not null default now(),
  constraint "courses_code_unique" unique ("code"),
  constraint "courses_code_non_empty_chk" check (char_length(btrim("code")) > 0),
  constraint "courses_title_non_empty_chk" check (char_length(btrim("title")) > 0),
  constraint "courses_units_non_negative_chk" check ("units" is null or "units" >= 0)
);

create table "market_datasets" (
  "id" uuid primary key default gen_random_uuid(),
  "file_path" text not null,
  "source" text,
  "status" text not null,
  "uploaded_by" uuid,
  "created_at" timestamptz not null default now(),
  constraint "market_datasets_file_path_non_empty_chk" check (char_length(btrim("file_path")) > 0),
  constraint "market_datasets_status_non_empty_chk" check (char_length(btrim("status")) > 0),
  constraint "market_datasets_source_non_empty_when_present_chk" check ("source" is null or char_length(btrim("source")) > 0)
);

create table "skill_aliases" (
  "id" uuid primary key default gen_random_uuid(),
  "skill_id" uuid,
  "alias" text not null,
  "normalized_alias" text not null,
  "source" text,
  "reviewed" boolean not null default false,
  "created_at" timestamptz not null default now(),
  constraint "skill_aliases_skill_id_fkey" foreign key ("skill_id") references "skills"("id"),
  constraint "skill_aliases_alias_unique" unique ("alias"),
  constraint "skill_aliases_normalized_alias_unique" unique ("normalized_alias"),
  constraint "skill_aliases_alias_non_empty_chk" check (char_length(btrim("alias")) > 0),
  constraint "skill_aliases_normalized_alias_non_empty_chk" check (char_length(btrim("normalized_alias")) > 0),
  constraint "skill_aliases_normalized_alias_consistency_chk" check ("normalized_alias" = lower(regexp_replace(btrim("alias"), '[[:space:]]+', ' ', 'g'))),
  constraint "skill_aliases_reviewed_requires_skill_id_chk" check ((not "reviewed") or "skill_id" is not null)
);

create table "career_role_aliases" (
  "id" uuid primary key default gen_random_uuid(),
  "role_id" uuid not null,
  "alias" text not null,
  "normalized_alias" text not null,
  "created_at" timestamptz not null default now(),
  constraint "career_role_aliases_role_id_fkey" foreign key ("role_id") references "career_roles"("id"),
  constraint "career_role_aliases_alias_unique" unique ("alias"),
  constraint "career_role_aliases_normalized_alias_unique" unique ("normalized_alias"),
  constraint "career_role_aliases_alias_non_empty_chk" check (char_length(btrim("alias")) > 0),
  constraint "career_role_aliases_normalized_alias_non_empty_chk" check (char_length(btrim("normalized_alias")) > 0),
  constraint "career_role_aliases_normalized_alias_consistency_chk" check ("normalized_alias" = lower(regexp_replace(btrim("alias"), '[[:space:]]+', ' ', 'g')))
);

create table "course_skills" (
  "id" uuid primary key default gen_random_uuid(),
  "course_id" uuid not null,
  "skill_id" uuid not null,
  "depth_weight" numeric(3,2) not null default 1.0,
  "created_at" timestamptz not null default now(),
  constraint "course_skills_course_id_fkey" foreign key ("course_id") references "courses"("id"),
  constraint "course_skills_skill_id_fkey" foreign key ("skill_id") references "skills"("id"),
  constraint "course_skills_course_id_skill_id_unique" unique ("course_id", "skill_id"),
  constraint "course_skills_depth_weight_range_chk" check ("depth_weight" > 0 and "depth_weight" <= 1)
);

create index "skill_aliases_skill_id_idx" on "skill_aliases" ("skill_id");
create index "career_role_aliases_role_id_idx" on "career_role_aliases" ("role_id");
create index "course_skills_skill_id_idx" on "course_skills" ("skill_id");
create index "course_skills_course_id_idx" on "course_skills" ("course_id");
create index "market_datasets_status_created_at_idx" on "market_datasets" ("status", "created_at");

