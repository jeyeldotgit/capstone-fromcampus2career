create table "role_requirement_versions" (
  "id" uuid primary key default gen_random_uuid(),
  "version" integer not null,
  "dataset_id" uuid not null,
  "computed_at" timestamptz not null default now(),
  constraint "role_requirement_versions_dataset_id_fkey" foreign key ("dataset_id") references "market_datasets"("id"),
  constraint "role_requirement_versions_version_unique" unique ("version"),
  constraint "role_requirement_versions_version_positive_chk" check ("version" > 0)
);

create table "role_skill_requirements" (
  "id" uuid primary key default gen_random_uuid(),
  "role_id" uuid not null,
  "skill_id" uuid not null,
  "requirement_version" integer not null,
  "required_depth" numeric(5,4) not null,
  "demand_weight" numeric(5,4) not null,
  "evidence_count" integer not null default 0,
  constraint "role_skill_requirements_role_id_fkey" foreign key ("role_id") references "career_roles"("id"),
  constraint "role_skill_requirements_skill_id_fkey" foreign key ("skill_id") references "skills"("id"),
  constraint "role_skill_requirements_role_skill_version_unique" unique ("role_id", "skill_id", "requirement_version"),
  constraint "role_skill_requirements_required_depth_range_chk" check ("required_depth" >= 0 and "required_depth" <= 1),
  constraint "role_skill_requirements_demand_weight_range_chk" check ("demand_weight" >= 0.1 and "demand_weight" <= 1),
  constraint "role_skill_requirements_evidence_count_min_chk" check ("evidence_count" >= 5)
);

create table "sdi_snapshots" (
  "id" uuid primary key default gen_random_uuid(),
  "role_id" uuid not null,
  "skill_id" uuid not null,
  "demand_index" numeric(5,4) not null,
  "snapshot_date" date not null,
  "requirement_version" integer not null,
  constraint "sdi_snapshots_role_id_fkey" foreign key ("role_id") references "career_roles"("id"),
  constraint "sdi_snapshots_skill_id_fkey" foreign key ("skill_id") references "skills"("id"),
  constraint "sdi_snapshots_role_skill_snapshot_date_unique" unique ("role_id", "skill_id", "snapshot_date"),
  constraint "sdi_snapshots_demand_index_range_chk" check ("demand_index" >= 0 and "demand_index" <= 1)
);

create table "skill_decay_signals" (
  "id" uuid primary key default gen_random_uuid(),
  "role_id" uuid not null,
  "skill_id" uuid not null,
  "decay_rate" numeric(5,4) not null,
  "confidence" numeric(5,4) not null,
  "detected_at" timestamptz not null default now(),
  "requirement_version" integer not null,
  "is_active" boolean not null default true,
  constraint "skill_decay_signals_role_id_fkey" foreign key ("role_id") references "career_roles"("id"),
  constraint "skill_decay_signals_skill_id_fkey" foreign key ("skill_id") references "skills"("id"),
  constraint "skill_decay_signals_role_skill_version_unique" unique ("role_id", "skill_id", "requirement_version"),
  constraint "skill_decay_signals_decay_rate_range_chk" check ("decay_rate" >= 0 and "decay_rate" <= 1),
  constraint "skill_decay_signals_confidence_range_chk" check ("confidence" >= 0 and "confidence" <= 1)
);

create index "role_skill_requirements_role_version_idx" on "role_skill_requirements" ("role_id", "requirement_version");
create index "role_skill_requirements_skill_version_idx" on "role_skill_requirements" ("skill_id", "requirement_version");
create index "sdi_snapshots_role_snapshot_date_idx" on "sdi_snapshots" ("role_id", "snapshot_date");
create index "sdi_snapshots_skill_snapshot_date_idx" on "sdi_snapshots" ("skill_id", "snapshot_date");
create index "skill_decay_signals_role_version_idx" on "skill_decay_signals" ("role_id", "requirement_version");
create index "skill_decay_signals_skill_version_idx" on "skill_decay_signals" ("skill_id", "requirement_version");
create index "skill_decay_signals_role_skill_active_idx" on "skill_decay_signals" ("role_id", "skill_id", "is_active");
