# Product Requirements Document

## 1. Product Overview

**Product Name:** From Campus to Career

From Campus to Career is a career-readiness platform for Filipino university students, especially students in BSIT, BSCS, and other computing-related programs. The product helps students understand how their completed courses and grades translate into practical skills, how those skills compare with their target career, and what actions they should take next.

The system combines prepared labor-market intelligence, university course-skill mappings, and student academic records to generate fast, explainable skill-gap analysis and roadmap recommendations.

## 2. Problem Statement

Many students know the job title they want, but they do not clearly know:

- which skills are required for that career
- which of their current skills are strong enough
- which skills are missing or weak
- which certifications, projects, or internships would help most
- which skills may be losing market relevance over time

Existing job boards show openings, but they do not convert labor-market data into student-specific guidance. This product closes that gap by preparing career and skill intelligence in advance, then serving fast, personalized insights through the app.

## 3. Target Users

**Primary users:** Filipino university students, especially BSIT, BSCS, and computing-related students.

**Secondary users:** Academic advisers, career support staff, and administrators who maintain course mappings, skill taxonomies, and labor-market datasets.

**Tertiary users:** Project evaluators, researchers, and institutions that need a reproducible system for skill-gap analysis.

## 4. Goals and Non-Goals

### Goals

- Help students identify skill gaps for a target career.
- Translate courses and grades into estimated skill depth.
- Provide fast skill-gap analysis even under concurrent usage.
- Recommend certifications, projects, internships, or learning actions.
- Detect skills that are declining in labor-market relevance.
- Give administrators tools to maintain accurate career, skill, and course data.
- Separate data preparation from user-facing request-response flows.
- Keep user-facing features fast by consuming precomputed, versioned data.

### Non-Goals

- The product will not be a general-purpose job board.
- The product will not guarantee employment outcomes.
- The product will not make final academic or career decisions for students.
- The product will not rely on LLMs as the source of truth for final analysis.
- The product will not run heavy market-data processing during normal student requests.

## 5. Core User Journeys

### Student Journey

1. A student creates an account using a university email.
2. The student completes their profile with program, university, and graduation details.
3. The student enters completed courses and grades.
4. The system computes or updates the student's skill profile.
5. The student types a target career in free text.
6. The system returns matched career roles using precomputed role aliases, keywords, and search indexes.
7. The student confirms a target career role.
8. The system compares the student's skill profile against precomputed role requirements.
9. The student views skill gaps, readiness score, and roadmap recommendations.
10. The student tracks recommendations and receives updated insights when data changes.

### Admin Journey

1. An admin signs in with an authorized account.
2. The admin manages career roles, skills, aliases, courses, and course-to-skill mappings.
3. The admin uploads or registers job-market datasets.
4. The Python data pipeline ingests, cleans, normalizes, and analyzes the dataset.
5. The system stores prepared, versioned market intelligence in the database.
6. The admin reviews unknown skills, role requirements, SDI results, and decay signals.
7. The student-facing application consumes the prepared data through fast TypeScript services.

## 6. MVP Scope

The MVP must include:

- Student registration and login through Supabase Auth.
- Student profile setup.
- Course and grade entry.
- Admin-managed course catalog.
- Admin-managed skill taxonomy.
- Admin-managed course-to-skill mappings.
- Free-text career intent input.
- Career role matching using prepared role data.
- Skill profile generation from courses and grades.
- Skill-gap analysis against a confirmed target role.
- Readiness score for the target role.
- Personalized roadmap recommendations.
- Admin CSV upload or dataset registration.
- Python-based data preparation for market intelligence.
- Prepared role skill requirements stored in Supabase Postgres.
- Basic analysis history.
- Basic pipeline/job status tracking for admins.

## 7. Post-MVP Scope

Post-MVP features may include:

- Skill decay alerts for students.
- Semester-by-semester readiness history.
- Career affinity indicator across multiple roles.
- Internship recommendations from live or curated sources.
- Push notifications through Firebase Cloud Messaging.
- LLM-assisted explanation text for recommendations.
- Advanced admin analytics.
- Institution-level reports.
- More advanced role matching using embeddings or vector search.
- Automated data quality checks for uploaded datasets.
- More detailed audit logs for admin changes.

## 8. Functional Requirements

### Student Features

- Students must be able to register, log in, and log out.
- Students must be able to create and update their profile.
- Students must be able to add, edit, and remove courses and grades.
- Students must be able to type a target career in free text.
- Students must receive ranked career role suggestions.
- Students must confirm the target role before skill-gap analysis.
- Students must be able to run skill-gap analysis.
- Students must see required skills, current skill depth, and gap score.
- Students must see an overall readiness score for the selected role.
- Students must receive recommended roadmap items.
- Students must be able to mark roadmap items as completed.
- Students must be able to view past analysis results.

### Admin Features

- Admins must be able to manage users and roles.
- Admins must be able to manage career roles.
- Admins must be able to manage skills and skill aliases.
- Admins must be able to review unknown or unverified skill aliases.
- Admins must be able to manage the course catalog.
- Admins must be able to map courses to skills with depth weights.
- Admins must be able to upload or register CSV datasets.
- Admins must be able to trigger or monitor data ingestion.
- Admins must be able to review role skill requirements.
- Admins must be able to review Skill Demand Index outputs.
- Admins must be able to review skill decay signals.
- Admins must be able to manage recommendation templates and catalogs.

### Data Engineering Features

- The Python data pipeline must ingest CSV datasets from Supabase Storage or a configured source.
- The pipeline must validate required columns and data quality rules.
- The pipeline must clean and normalize job titles, skills, and role labels.
- The pipeline must deduplicate job postings.
- The pipeline must extract or map skills from job descriptions.
- The pipeline must compute role skill requirements.
- The pipeline must compute Skill Demand Index snapshots.
- The pipeline must detect declining skill demand trends.
- The pipeline must write versioned, app-ready outputs to Supabase Postgres.
- The pipeline must record rejected rows, errors, and processing status.

## 9. Non-Functional Requirements

### Performance

- Career role suggestions should usually return within 100ms to 800ms.
- Skill-gap analysis should usually return within 100ms to 1 second when precomputed data is available.
- The system should support thousands of concurrent student requests by keeping heavy processing outside the user-facing request path.

### Scalability

- User-facing services must scale independently from data preparation pipelines.
- The API must use cache, idempotency, and precomputed read models where appropriate.
- The system must avoid scanning raw job postings during student requests.
- The system must support rate limiting and backpressure during traffic spikes.

### Reliability

- User-facing requests must not depend on Python pipelines being actively available.
- If a data pipeline fails, the app should continue serving the latest valid prepared data.
- Pipeline outputs must be versioned so the app can distinguish current and stale data.
- Failed pipeline runs must be visible to admins.

### Security and Privacy

- Authentication must use Supabase Auth.
- Authorization must enforce student and admin roles.
- Students must only access their own profile and analysis data.
- Admin actions must be restricted to authorized users.
- Backend services must avoid exposing service keys to the client.
- Sensitive data must be handled according to applicable institutional and privacy requirements.

### Maintainability

- TypeScript must own the software/product layer.
- Python must own only the data engineering layer.
- Database schema and versioned tables must act as the contract between Python and TypeScript.
- Shared contracts must be tested to prevent pipeline output from breaking app consumption.

## 10. Data and Intelligence Requirements

The system must maintain prepared data that can be consumed quickly by the application.

### Core Prepared Data

- career roles
- career role aliases
- skill taxonomy
- skill aliases
- course catalog
- course-to-skill mappings
- student skill profiles
- role skill requirements
- Skill Demand Index snapshots
- skill decay signals
- recommendation catalog
- roadmap templates
- cached skill-gap results

### Data Versioning

The system should track versions for:

- student skill profile
- role skill requirements
- market intelligence snapshot
- skill-gap analysis result

Skill-gap results should be reusable when the student profile version and role requirement version have not changed.

## 11. User-Facing Performance Expectations

The product must feel responsive even when many students use it at the same time.

### Career Intent Flow

Free-text role parsing should use a tiered approach:

1. Normalize text.
2. Check exact role and alias matches.
3. Check cached query results.
4. Search precomputed role keywords and indexes.
5. Use embeddings or LLM fallback only for ambiguous cases.

The system should not call an LLM for every student query.

### Skill-Gap Flow

Skill-gap analysis should use this fast path:

1. Validate the student session.
2. Check for a cached analysis result.
3. Read the student's precomputed skill profile.
4. Read precomputed role skill requirements.
5. Compute deterministic gap and readiness scores.
6. Store a result snapshot.
7. Return the result.

The system must not ingest job postings, extract market skills, compute SDI, detect decay, or call an LLM during the required skill-gap response.

### Concurrent Usage Scenario

When 1,000 students request skill-gap analysis at the same time:

- the API should treat the requests as fast read-and-compare operations
- duplicate requests should be deduplicated using idempotency keys or versioned cache keys
- cached results should be returned when available
- the database should read from prepared tables instead of raw datasets
- slower enrichment work should happen asynchronously after the core result is returned

## 12. Success Metrics

### Product Metrics

- Daily active users
- Weekly active users
- Profile completion rate
- Course entry completion rate
- Career intent submission rate
- Career role confirmation rate
- Skill-gap analysis completion rate
- Roadmap engagement rate
- Percentage of users returning after one week

### Performance Metrics

- Time to first analysis
- Career role suggestion latency
- Skill-gap analysis latency
- API p95 latency
- Cache hit rate
- Concurrent analysis success rate

### Data Pipeline Metrics

- Dataset ingestion success rate
- Rejected row count
- Unknown skill alias count
- Pipeline processing time
- Market snapshot freshness
- Skill requirement version freshness

### Admin Metrics

- Admin correction rate for unknown skills
- Course-to-skill mapping completion rate
- Reviewed alias percentage
- Failed pipeline recovery time

## 13. Risks and Assumptions

### Risks

- Poor dataset quality may reduce recommendation accuracy.
- Incomplete course-to-skill mappings may weaken student skill profiles.
- Overuse of LLMs could increase cost and latency.
- Python and TypeScript contracts may drift without strong schema discipline.
- Supabase limits may become a bottleneck as usage grows.
- Free-tier infrastructure may not support production traffic indefinitely.

### Assumptions

- Admins or project maintainers can provide initial course, skill, and role data.
- Job-market datasets are available through CSV uploads or curated sources.
- Students are willing to enter courses and grades.
- Precomputed market intelligence can be refreshed periodically rather than on every request.
- Deterministic scoring is acceptable as the authoritative result source.
- LLMs are optional enhancers, not required for core correctness.

## 14. Acceptance Criteria

The MVP is considered acceptable when:

- A student can register, log in, complete a profile, and enter courses and grades.
- An admin can manage skills, roles, courses, and course-to-skill mappings.
- An admin can upload or register a CSV dataset for ingestion.
- The Python data pipeline can produce role skill requirements from prepared market data.
- The TypeScript API can consume prepared data from Supabase Postgres.
- A student can type a target role and receive ranked suggestions.
- A student can confirm a role and receive a skill-gap analysis result.
- The result includes required skills, student depth, gap score, readiness score, and roadmap recommendations.
- The skill-gap response does not depend on live Python processing.
- The system can reuse cached or versioned results when inputs have not changed.
- Admins can see pipeline status and failed ingestion details.
- Core user-facing flows remain responsive under simulated concurrent requests.

