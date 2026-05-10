alter table "skills"
  add column if not exists "code" text,
  add column if not exists "notes" text;

alter table "skill_aliases"
  add column if not exists "code" text,
  add column if not exists "notes" text;

alter table "career_roles"
  add column if not exists "code" text,
  add column if not exists "category" text;

alter table "career_role_aliases"
  add column if not exists "code" text;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'skills_code_unique'
  ) then
    alter table "skills"
      add constraint "skills_code_unique" unique ("code");
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conname = 'skill_aliases_code_unique'
  ) then
    alter table "skill_aliases"
      add constraint "skill_aliases_code_unique" unique ("code");
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conname = 'career_roles_code_unique'
  ) then
    alter table "career_roles"
      add constraint "career_roles_code_unique" unique ("code");
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conname = 'career_role_aliases_code_unique'
  ) then
    alter table "career_role_aliases"
      add constraint "career_role_aliases_code_unique" unique ("code");
  end if;
end
$$;

do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'skills'
      and column_name = 'code'
      and is_nullable = 'YES'
  ) then
    alter table "skills"
      alter column "code" set not null;
  end if;

  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'skill_aliases'
      and column_name = 'code'
      and is_nullable = 'YES'
  ) then
    alter table "skill_aliases"
      alter column "code" set not null;
  end if;

  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'career_roles'
      and column_name = 'code'
      and is_nullable = 'YES'
  ) then
    alter table "career_roles"
      alter column "code" set not null;
  end if;

  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'career_role_aliases'
      and column_name = 'code'
      and is_nullable = 'YES'
  ) then
    alter table "career_role_aliases"
      alter column "code" set not null;
  end if;
end
$$;

/*
Rollback SQL:

alter table "career_role_aliases" drop constraint if exists "career_role_aliases_code_unique";
alter table "career_roles" drop constraint if exists "career_roles_code_unique";
alter table "skill_aliases" drop constraint if exists "skill_aliases_code_unique";
alter table "skills" drop constraint if exists "skills_code_unique";

alter table "career_role_aliases" drop column if exists "code";
alter table "career_roles" drop column if exists "category";
alter table "career_roles" drop column if exists "code";
alter table "skill_aliases" drop column if exists "notes";
alter table "skill_aliases" drop column if exists "code";
alter table "skills" drop column if exists "notes";
alter table "skills" drop column if exists "code";
*/
