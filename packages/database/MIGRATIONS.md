# Database Migrations

## 20260503143000_p1_s01_taxonomy_schema

- Spec: `P1-S01-db-schema-taxonomy`
- Purpose: establish Phase 1 foundational taxonomy and dataset registration schema contracts.
- Tables created:
  - `skills`
  - `skill_aliases`
  - `career_roles`
  - `career_role_aliases`
  - `courses`
  - `course_skills`
  - `market_datasets`
- Major constraints:
  - PK on all seven tables.
  - FK constraints:
    - `skill_aliases.skill_id -> skills.id` (nullable FK)
    - `career_role_aliases.role_id -> career_roles.id`
    - `course_skills.course_id -> courses.id`
    - `course_skills.skill_id -> skills.id`
  - Alias normalization checks enforced on both alias tables.
  - Deterministic uniqueness for canonical lookup fields and alias fields.
  - Domain checks for non-empty text fields and bounded `course_skills.depth_weight`.
- Explicit join indexes:
  - `skill_aliases(skill_id)`
  - `career_role_aliases(role_id)`
  - `course_skills(skill_id)`
  - `course_skills(course_id)`
  - `market_datasets(status, created_at)`
- Deferred FK note:
  - `market_datasets.uploaded_by` is intentionally nullable and does not yet reference `users(id)` in this slice to preserve empty-database reproducibility and keep scope limited to P1-S01.

