create table "app_events" (
  "id" uuid primary key default gen_random_uuid(),
  "event_type" text not null,
  "aggregate_type" text not null,
  "aggregate_id" uuid,
  "payload" jsonb not null,
  "status" text not null default 'pending',
  "available_at" timestamptz not null default now(),
  "processed_at" timestamptz,
  "error_message" text,
  "created_at" timestamptz not null default now(),
  constraint "app_events_status_valid_chk" check (
    "status" in ('pending', 'processing', 'processed', 'failed')
  )
);

create index "app_events_status_available_at_idx" on "app_events" ("status", "available_at");
create index "app_events_aggregate_type_aggregate_id_idx" on "app_events" ("aggregate_type", "aggregate_id");
