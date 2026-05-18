alter table "role_requirement_versions"
add column "is_current" boolean not null default false;

alter table "role_skill_requirements"
add constraint "role_skill_requirements_requirement_version_fkey"
foreign key ("requirement_version") references "role_requirement_versions"("version");
