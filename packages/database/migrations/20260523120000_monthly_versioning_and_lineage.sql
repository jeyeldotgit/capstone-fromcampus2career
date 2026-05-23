alter table "role_requirement_versions"
add column "period_month" date,
add column "period_revision" integer;

with ranked_versions as (
  select
    "version",
    date_trunc('month', "computed_at")::date as backfilled_period_month,
    row_number() over (
      partition by date_trunc('month', "computed_at")::date
      order by "version"
    )::integer as backfilled_period_revision
  from "role_requirement_versions"
)
update "role_requirement_versions" versions
set
  "period_month" = ranked_versions.backfilled_period_month,
  "period_revision" = ranked_versions.backfilled_period_revision
from ranked_versions
where versions."version" = ranked_versions."version";

with ranked_current_versions as (
  select
    "version",
    row_number() over (
      partition by "period_month"
      order by "version" desc
    ) as current_rank
  from "role_requirement_versions"
  where "is_current" = true
)
update "role_requirement_versions" versions
set "is_current" = false
from ranked_current_versions ranked
where versions."version" = ranked."version"
  and ranked.current_rank > 1;

alter table "role_requirement_versions"
alter column "period_month" set not null,
alter column "period_revision" set not null;

alter table "role_requirement_versions"
add constraint "role_requirement_versions_period_revision_positive_chk"
check ("period_revision" > 0),
add constraint "role_requirement_versions_period_month_start_chk"
check (date_trunc('month', "period_month"::timestamp)::date = "period_month");

create unique index "role_requirement_versions_period_month_revision_unique"
on "role_requirement_versions" ("period_month", "period_revision");

create unique index "role_requirement_versions_current_period_month_unique"
on "role_requirement_versions" ("period_month")
where "is_current" = true;

create table "role_requirement_version_datasets" (
  "requirement_version" integer not null,
  "dataset_id" uuid not null,
  "linked_at" timestamptz not null default now(),
  constraint "role_requirement_version_datasets_requirement_version_fkey"
    foreign key ("requirement_version") references "role_requirement_versions"("version"),
  constraint "role_requirement_version_datasets_dataset_id_fkey"
    foreign key ("dataset_id") references "market_datasets"("id"),
  constraint "role_requirement_version_datasets_version_dataset_unique"
    unique ("requirement_version", "dataset_id")
);

create index "role_requirement_version_datasets_dataset_id_idx"
on "role_requirement_version_datasets" ("dataset_id");

insert into "role_requirement_version_datasets" ("requirement_version", "dataset_id")
select "version", "dataset_id"
from "role_requirement_versions"
on conflict ("requirement_version", "dataset_id") do nothing;

alter table "sdi_snapshots"
drop constraint if exists "sdi_snapshots_role_skill_snapshot_date_unique";

alter table "sdi_snapshots"
add constraint "sdi_snapshots_requirement_version_fkey"
foreign key ("requirement_version") references "role_requirement_versions"("version");

alter table "sdi_snapshots"
add constraint "sdi_snapshots_role_skill_snapshot_version_unique"
unique ("role_id", "skill_id", "snapshot_date", "requirement_version");

alter table "skill_decay_signals"
add constraint "skill_decay_signals_requirement_version_fkey"
foreign key ("requirement_version") references "role_requirement_versions"("version");

create view "v_current_monthly_role_skill_requirements" as
select
  requirements."id",
  requirements."role_id",
  requirements."skill_id",
  requirements."requirement_version",
  requirements."required_depth",
  requirements."demand_weight",
  requirements."evidence_count",
  versions."period_month",
  versions."period_revision",
  versions."dataset_id" as "triggering_dataset_id",
  versions."computed_at"
from "role_skill_requirements" requirements
join "role_requirement_versions" versions
  on versions."version" = requirements."requirement_version"
where versions."is_current" = true;

create view "v_current_monthly_sdi_snapshots" as
select
  snapshots."id",
  snapshots."role_id",
  snapshots."skill_id",
  snapshots."demand_index",
  snapshots."snapshot_date",
  snapshots."requirement_version",
  versions."period_month",
  versions."period_revision",
  versions."dataset_id" as "triggering_dataset_id",
  versions."computed_at"
from "sdi_snapshots" snapshots
join "role_requirement_versions" versions
  on versions."version" = snapshots."requirement_version"
where versions."is_current" = true;

create view "v_current_monthly_skill_decay_signals" as
select
  signals."id",
  signals."role_id",
  signals."skill_id",
  signals."decay_rate",
  signals."confidence",
  signals."detected_at",
  signals."requirement_version",
  signals."is_active",
  versions."period_month",
  versions."period_revision",
  versions."dataset_id" as "triggering_dataset_id",
  versions."computed_at"
from "skill_decay_signals" signals
join "role_requirement_versions" versions
  on versions."version" = signals."requirement_version"
where versions."is_current" = true;
