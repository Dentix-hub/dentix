<!-- CLASSIFICATION: ACTIVE -->
# DENTIX AI Agent Stack

## Solo Workflow Architecture

DENTIX operates on a streamlined solo-developer model:
- **Implementer**: One primary AI assistant (Gemini) handles local implementation, testing, and PR creation.
- **Reviewer & Operator**: Eslam reviews all PRs, verifies changes manually on staging, and controls production promotion.
- **HIGH_RISK Review**: Optional second-model review for sensitive changes (auth, RBAC, tenancy, finance, migrations, clinical semantics).

## Authorities & Lifecycle

All development follows `docs/engineering/DEVELOPMENT_WORKFLOW.md` as the canonical lifecycle authority and `PROJECT_STANDARDS.md` for architecture.

## Native Skills (4)

Specialist guidance is provided on-demand via 4 native skills under `.agents/skills/`:
- `dentix-security-tenancy-rbac`: Tenant isolation, RLS, auth, RBAC.
- `dentix-database-migrations`: PostgreSQL schema safety and Alembic migrations.
- `dentix-testing-verification`: Minimum sufficient verification.
- `dentix-code-review`: Review discipline for sensitive changes.
