alter table "skill_aliases"
  drop constraint if exists "skill_aliases_reviewed_requires_skill_id_chk";

alter table "career_role_aliases"
  add column if not exists "reviewed" boolean not null default true;

alter table "market_datasets"
  add column if not exists "source_url" text;

alter table "market_datasets"
  drop constraint if exists "market_datasets_source_url_non_empty_when_present_chk";

alter table "market_datasets"
  add constraint "market_datasets_source_url_non_empty_when_present_chk"
  check ("source_url" is null or char_length(btrim("source_url")) > 0);

alter table "skill_decay_signals"
  drop constraint if exists "skill_decay_signals_decay_rate_range_chk";

update "skill_decay_signals"
set "decay_rate" = -abs("decay_rate")
where "decay_rate" > 0;

alter table "skill_decay_signals"
  add constraint "skill_decay_signals_decay_rate_range_chk"
  check ("decay_rate" >= -1 and "decay_rate" <= 0);
