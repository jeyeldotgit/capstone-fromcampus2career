# Development Specification

## 1. Engineering Principles

The system follows a split-responsibility model:

```txt
Python prepares data.
TypeScript serves the app.
Supabase Postgres is the contract between them.
```

Core rules:

- Python must stay in the data engineering layer.
- TypeScript owns user-facing APIs, product logic, mobile, and admin.
- Student request-response flows must never call Python directly.
- Heavy data processing must happen offline.
- User-facing features must consume prepared, versioned data.
- Core scoring must be deterministic and testable.
- LLM usage must be optional and non-blocking.
- Cache improves speed but does not replace the database as source of truth.

## 2. Repository Structure

Target structure:

```txt
from-campus-to-career/
  apps/
    mobile/
    api/
    admin/
    data-pipeline/
  packages/
    shared/
    database/
    config/
  docs/
  PRD.md
  HLD.md
  LLD.md
  arch.md
  dev-roadmap.md
  dev-spec.md
```

Responsibilities:

- `apps/mobile`: React Native Expo student app.
- `apps/api`: Hono TypeScript API.
- `apps/admin`: TypeScript admin dashboard.
- `apps/data-pipeline`: Python data engineering pipeline.
- `packages/shared`: shared TypeScript types and schemas.
- `packages/database`: schema, migrations, seed data, and database utilities.
- `packages/config`: shared TypeScript configuration.

## 3. Development Workflow

Default workflow:

```txt
create issue
-> create branch
-> implement feature
-> add tests
-> update docs if needed
-> open pull request
-> review
-> merge
```

Work should be delivered in small vertical slices whenever possible:

```txt
schema
-> API
-> domain logic
-> tests
-> minimal UI
-> docs update
```

## 4. Git Branch Strategy

Primary branches:

```txt
main
develop
```

Branch meanings:

- `main`: stable and deployable.
- `develop`: integration branch for active development.

Feature branches:

```txt
feature/*
fix/*
chore/*
docs/*
spike/*
```

Examples:

```txt
feature/api-auth-middleware
feature/python-csv-ingestion
feature/admin-taxonomy-crud
feature/student-skill-profile
feature/career-role-search
feature/skill-gap-fast-path
feature/mobile-profile-setup
fix/skill-gap-idempotency
chore/github-actions-ci
docs/update-architecture-stack
spike/pgvector-role-search
```

## 5. GitHub Issues

Issue labels:

```txt
area:mobile
area:api
area:admin
area:data-pipeline
area:database
area:infra
area:docs
type:feature
type:bug
type:chore
type:test
type:spike
priority:p0
priority:p1
priority:p2
```

Milestones:

```txt
M1: Data Preparation Foundation
M2: Admin Backend
M3: Minimal Admin UI
M4: Student Backend
M5: Minimal Mobile App
M6: Feature Expansion
M7: Hardening and Launch Readiness
```

Issue template:

```md
## Goal

What outcome should this issue produce?

## Scope

- Item 1
- Item 2
- Item 3

## Acceptance Criteria

- Criterion 1
- Criterion 2
- Criterion 3

## Notes

Technical context, links, or constraints.
```

Example issue:

```md
# Implement career role search API

## Goal

Students can type a free-text career target and receive ranked role suggestions.

## Scope

- Add `GET /api/v1/careers/search`
- Normalize query
- Match exact title, alias, and keyword
- Return confidence score and match type
- Cache normalized query result

## Acceptance Criteria

- Returns ranked roles for known aliases.
- Returns safe empty results for unknown queries.
- Does not call LLM in the default path.
- Has unit tests for matching logic.
- Has integration test for route auth and response shape.
```

## 6. Pull Request Standard

PRs should include:

- summary of changes
- linked issue
- screenshots for UI changes
- test results
- migration notes if database changes exist
- rollout or risk notes for sensitive changes

PR checklist:

```md
- [ ] Linked issue
- [ ] Tests added or updated
- [ ] Typecheck passes
- [ ] Lint passes
- [ ] Migrations added if needed
- [ ] Docs updated if behavior changed
- [ ] No service keys exposed to client
- [ ] User-facing request path stays fast
```

## 7. Git Commit Structure

Commits should follow a lightweight Conventional Commits style.

Format:

```txt
type(scope): short imperative summary
```

Examples:

```txt
feat(api): add career role search endpoint
feat(data): ingest market dataset CSV
feat(mobile): add profile setup screen
fix(api): reuse existing skill-gap result by version
test(data): cover rejected row publishing
docs(arch): add ERD to main architecture
chore(ci): add typecheck workflow
```

Allowed commit types:

```txt
feat
fix
docs
test
refactor
chore
ci
perf
style
revert
```

Recommended scopes:

```txt
api
mobile
admin
data
db
shared
infra
ci
docs
auth
cache
roadmap
skills
careers
```

Commit rules:

- Use the imperative mood, such as `add`, `fix`, `update`, or `remove`.
- Keep the first line under 72 characters when reasonable.
- Reference the GitHub issue in the body when useful.
- Keep unrelated changes in separate commits.
- Do not include secrets, generated local files, or unrelated formatting churn.
- Use `BREAKING CHANGE:` in the commit body if a change breaks an API, schema, or contract.

Example with issue reference:

```txt
feat(api): add skill-gap fast path

Reads prepared student skill profiles and role requirements to compute
gap scores without calling the Python pipeline.

Closes #42
```

Example breaking change:

```txt
refactor(db): rename role requirement version table

BREAKING CHANGE: role_requirement_versions replaces market_versions.
Python publishing and TypeScript readers must use the new table.
```

## 8. Definition of Done

A feature is done when:

- API route is implemented if needed.
- Request and response schemas are validated.
- Database migration is added if schema changed.
- Domain logic has unit tests.
- Important route behavior has integration tests.
- UI has loading, empty, error, and success states where applicable.
- Auth and role permissions are enforced.
- Logs or errors are observable where needed.
- Documentation is updated when behavior, architecture, or schema changes.

For data pipeline features:

- sample input is covered by tests
- invalid rows are handled
- rejected rows are recorded
- pipeline job status is updated
- output version is published
- TypeScript consumer can read the output

For user-facing fast path features:

- no Python call happens during required request-response
- no raw job posting scan happens during request-response
- cache and idempotency behavior is defined
- failure behavior is understandable to the user

## 9. Testing Requirements

TypeScript unit tests:

- role matching
- skill depth calculation
- readiness scoring
- gap scoring
- roadmap ranking
- cache key generation

TypeScript integration tests:

- auth middleware
- admin route authorization
- profile routes
- course routes
- career search route
- skill-gap analysis route
- roadmap routes

Python unit tests:

- CSV parsing
- row validation
- normalization
- deduplication
- skill extraction or mapping
- SDI computation
- decay detection

Python integration tests:

- sample CSV ingestion
- rejected row publishing
- role requirement publishing
- SDI snapshot publishing
- pipeline job status updates

Load tests:

- 1,000 concurrent career search requests
- 1,000 concurrent skill-gap analysis requests
- repeated duplicate analysis requests
- cache hit and cache miss scenarios

## 10. Performance Requirements

Career role search:

```txt
Target: 100ms-800ms for normal queries
```

Skill-gap analysis:

```txt
Target: 100ms-1s when prepared data is available
```

Concurrency:

```txt
System must support simulated 1,000 concurrent career searches.
System must support simulated 1,000 concurrent skill-gap requests.
```

Required constraints:

- Do not call Python in the student request path.
- Do not call LLMs for normal career search.
- Do not scan raw job postings during skill-gap analysis.
- Use prepared tables and versioned result reuse.

## 11. Environment and Secrets

Secrets must never be committed.

API secrets:

```txt
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
DATABASE_URL
UPSTASH_REDIS_REST_URL
UPSTASH_REDIS_REST_TOKEN
SENTRY_DSN
```

Python pipeline secrets:

```txt
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
DATABASE_URL
SUPABASE_STORAGE_BUCKET
SENTRY_DSN
```

Mobile app public config:

```txt
EXPO_PUBLIC_SUPABASE_URL
EXPO_PUBLIC_SUPABASE_ANON_KEY
EXPO_PUBLIC_API_BASE_URL
```

Only public keys should be shipped to the mobile app.

## 12. Deployment Expectations

Early deployment targets:

- Mobile app: Expo / EAS
- API: Hono on selected TypeScript serverless runtime
- Admin dashboard: Vercel or Cloudflare Pages
- Database/Auth/Storage: Supabase
- Cache/rate limit: Upstash Redis
- Python jobs: Google Cloud Run Jobs
- Scheduling: Cloud Scheduler
- CI/CD: GitHub Actions
- Observability: Sentry, Supabase Logs, Google Cloud Logging

Deployment rules:

- `main` must remain deployable.
- migrations must be reviewed before deployment.
- pipeline jobs must publish versioned outputs.
- failed jobs must not overwrite latest valid prepared data.
- production secrets must be managed by provider secret storage.
