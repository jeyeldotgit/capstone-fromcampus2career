# Development Roadmap

## Development Strategy

The project will be developed data-first, with thin vertical checkpoints to keep the product experience grounded.

The preferred progression is:

```txt
1. Data preparation foundation
2. Admin backend
3. Minimal admin UI
4. Student backend
5. Minimal mobile app
6. Feature expansion
7. Hardening and launch readiness
```

This order respects the product's core dependency on prepared data while still validating the user experience before too much code is built in isolation.

## Phase 1: Data Preparation Foundation

### Goal

Produce trustworthy prepared data that the application can consume quickly.

### Scope

- Create database schema and migrations.
- Seed initial career roles, skills, skill aliases, courses, and course-to-skill mappings.
- Build Python CSV ingestion pipeline.
- Validate required CSV columns and data quality rules.
- Track rejected rows.
- Clean and normalize job posting data.
- Normalize job titles, career roles, and skills.
- Deduplicate job postings.
- Extract or map skills from job descriptions.
- Compute role skill requirements.
- Compute Skill Demand Index snapshots.
- Detect baseline skill decay signals.
- Publish versioned outputs to Supabase Postgres.
- Track pipeline job status.

### Checkpoint

Given a sample CSV, the Python pipeline can publish:

- `role_skill_requirements`
- `role_requirement_versions`
- `sdi_snapshots`
- `skill_decay_signals`
- `pipeline_jobs`
- `pipeline_rejected_rows`

### Exit Criteria

- Sample CSV ingestion succeeds.
- Invalid rows are rejected with clear reasons.
- Prepared output tables are populated.
- Pipeline status is visible in the database.
- TypeScript can read the prepared output tables.

## Phase 2: Admin Backend

### Goal

Expose admin operations through the Hono API.

### Scope

- Implement Supabase Auth validation.
- Implement admin role guard.
- Build skill CRUD APIs.
- Build skill alias review APIs.
- Build career role CRUD APIs.
- Build course CRUD APIs.
- Build course-to-skill mapping APIs.
- Build dataset registration APIs.
- Build pipeline job status APIs.
- Build rejected rows APIs.
- Build role requirement review APIs.
- Build SDI snapshot review APIs.
- Add request validation schemas.
- Add integration tests for admin routes.

### Checkpoint

Admin APIs can inspect and manage the data pipeline outputs.

### Exit Criteria

- Admin-only routes reject non-admin users.
- Admin can manage taxonomy data through APIs.
- Admin can register datasets.
- Admin can view pipeline jobs and rejected rows.
- Admin can review prepared role requirements.

## Phase 3: Minimal Admin UI

### Goal

Make the data pipeline debuggable by humans.

### Scope

- Build admin login flow.
- Build admin dashboard shell.
- Build dataset list view.
- Build pipeline job detail view.
- Build rejected rows table.
- Build role requirements review screen.
- Build unknown skill aliases review screen.
- Build basic skill, role, course, and mapping management screens.

### Checkpoint

An admin can register or inspect datasets, monitor ingestion, and review prepared outputs from the UI.

### Exit Criteria

- Admin can navigate core dashboard sections.
- Admin can inspect pipeline results without querying the database manually.
- Unknown aliases and rejected rows are visible.
- Role requirements are reviewable.

## Phase 4: Student Backend

### Goal

Expose fast student-facing APIs that consume prepared data.

### Scope

- Implement student role guard.
- Build student profile APIs.
- Build course and grade entry APIs.
- Implement student skill profile computation.
- Build career role search API.
- Add role search normalization and alias matching.
- Add role search cache.
- Build target role confirmation API.
- Build skill-gap analysis fast path.
- Implement readiness score.
- Implement idempotency for skill-gap requests.
- Store skill-gap result snapshots.
- Build roadmap recommendation APIs.
- Build analysis history APIs.
- Add integration tests for student routes.

### Checkpoint

A student can call APIs to enter courses, search a role, analyze skill gaps, and receive roadmap data without Python in the request-response path.

### Exit Criteria

- Student APIs reject unauthorized access.
- Student course updates produce or trigger updated skill profiles.
- Career search returns ranked role suggestions.
- Skill-gap analysis reads prepared data and returns fast.
- Duplicate analysis requests reuse existing results.
- Roadmap recommendations are generated from gap results.

## Phase 5: Minimal Mobile App

### Goal

Prove the main student journey end to end.

### Scope

- Build login screen.
- Build profile setup screen.
- Build course and grade entry screen.
- Build career search screen.
- Build target role confirmation.
- Build skill-gap results screen.
- Build readiness score display.
- Build roadmap screen.
- Add loading, empty, error, and success states.

### Checkpoint

A student can complete the main journey end to end on mobile.

### Exit Criteria

- Student can log in.
- Student can complete profile.
- Student can enter courses and grades.
- Student can search and confirm a target role.
- Student can view skill-gap analysis.
- Student can view roadmap recommendations.

## Phase 6: Feature Expansion

### Goal

Improve usefulness, visibility, and product polish.

### Scope

- Add roadmap progress tracking.
- Add skill decay alerts.
- Add Expo push notifications.
- Add richer admin analytics.
- Improve role search ranking.
- Improve mobile empty/error/loading states.
- Add better admin filters and tables.
- Add optional LLM explanation enrichment.
- Add recommendation catalog management.
- Add analysis history UI.

### Checkpoint

The product supports both the main student workflow and operational admin workflow with useful supporting features.

### Exit Criteria

- Students can track roadmap progress.
- Students can see relevant decay alerts.
- Admins can manage recommendation catalog.
- Notifications work for important updates.
- Optional enrichment does not block core results.

## Phase 7: Hardening and Launch Readiness

### Goal

Prepare the application for realistic usage and early production.

### Scope

- Add Sentry to mobile, API, and admin dashboard.
- Ensure Python Cloud Run Jobs write useful logs.
- Review Supabase logs and slow queries.
- Add Upstash rate limits.
- Add cache hit/miss monitoring.
- Run 1,000 concurrent career search test.
- Run 1,000 concurrent skill-gap analysis test.
- Test duplicate analysis requests.
- Test pipeline failure recovery.
- Review database indexes.
- Review RLS and service-role key usage.
- Review privacy and data retention.
- Finalize deployment checklist.

### Checkpoint

The system remains responsive under simulated concurrent usage and has clear failure handling.

### Exit Criteria

- No Python calls happen in required student request-response flows.
- No raw job posting scans happen during student requests.
- Load tests meet acceptable latency targets.
- Pipeline failures are visible and recoverable.
- Core flows have error handling and retry behavior.
- Security review issues are resolved or tracked.

