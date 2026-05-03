# Spec 00 - `P1-S00-db-environment-bootstrap`

**Spec name**  
`P1-S00-db-environment-bootstrap`

**Responsibility**  
Provision and verify the live Supabase database environment plus runtime wiring required before any schema, seed, or pipeline work starts.

**Depends on**  
None.

**Inputs**  
- [dev-roadmap.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/dev-roadmap.md)
- [LLD.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/docs/LLD.md)
- [AGENTS.md](/c:/Users/BEBELABS/Documents/FromCampus2Career/AGENTS.md)
- Existing env templates: [root .env.example](/c:/Users/BEBELABS/Documents/FromCampus2Career/.env.example), [API .env.example](/c:/Users/BEBELABS/Documents/FromCampus2Career/apps/api/.env.example), [Pipeline .env.example](/c:/Users/BEBELABS/Documents/FromCampus2Career/apps/data-pipeline/.env.example)

**Files/artifacts produced**  
- Environment bootstrap runbook in `packages/database` docs path (for example `MIGRATIONS.md` or `README.md`)
- Local `.env` files created from templates (not committed)
- Verified connection configuration for:
  - API runtime (`apps/api`)
  - Data pipeline runtime (`apps/data-pipeline`)
- Migration runner setup notes (commands, required tools, and expected outputs)

**In scope**  
- Supabase project selection or creation and acquisition of connection credentials
- `DATABASE_URL`, `SUPABASE_URL`, and service-role key wiring for local development
- Connectivity checks from TypeScript and Python runtimes to the same database
- Documented migration execution path and rollback safety notes

**Out of scope**  
- Creating application tables or constraints
- Seeding taxonomy or course data
- Implementing any ingestion, normalization, or publish stage code
- Implementing TypeScript read repositories or API endpoints

**Implementation requirements**  
- Credentials must be sourced from secure provider settings and never committed
- Setup instructions must be deterministic and executable by a new engineer
- Verification must confirm both runtimes point to the same target database
- Migration runner instructions must clearly distinguish local vs live execution

**Exit criterion (verifiable done condition)**  
1. A documented setup flow provisions or selects a Supabase database and configures required env values.
2. API runtime starts with configured DB env and passes health check.
3. Python pipeline runtime loads settings and confirms DB connectivity without placeholder credentials.
4. A migration command path is documented and validated against the configured environment.

