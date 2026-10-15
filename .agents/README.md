<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Agent Skills

This directory contains repository-scoped skills used by supported AI coding runtimes.

## Skill Catalog (4 Native Skills)

| Skill | Trigger | Purpose |
|---|---|---|
| `dentix-security-tenancy-rbac` | Auth / RBAC / tenancy / RLS / clinical PII / finance | Tenant isolation, PostgreSQL RLS, server-side RBAC, authentication boundaries, clinical/privacy/finance access control |
| `dentix-database-migrations` | Schema / migration / data-integrity | PostgreSQL schema safety, SQLAlchemy models, Alembic migrations, irreversible data operations |
| `dentix-testing-verification` | Verification gate selection | Minimum sufficient verification for a diff; CI as integration authority |
| `dentix-code-review` | HIGH_RISK review / explicit request | Severity-graded code review for sensitive or release-critical changes |

## Activation Discipline

Do not preload skills. Load only on trigger:

- **Auth / RBAC / Tenancy / RLS**: `dentix-security-tenancy-rbac`
- **Migrations / schema**: `dentix-database-migrations`
- **Verification selection**: `dentix-testing-verification`
- **HIGH_RISK / sensitive review**: `dentix-code-review`

## Authoring Rules

- Keep the native skill surface minimal. A native skill is justified only when it contains recurring DENTIX-specific knowledge or safety constraints not adequately provided by general engineering capability, `AGENTS.md`, or `PROJECT_STANDARDS.md`.
- One skill = one primary responsibility.
- Do not duplicate rules already enforced in root `AGENTS.md`.
- Do not add generic language or framework skills.
