---
trigger: always_on
---

# Dentix Deployment Rules

> Project-scoped rule for ECC agents working on Dentix.

## Before ANY Work
1. Read `DENTIX_MEMORY.md` — understand project state and open issues
2. Read `WORKFLOW_RULES.md` — understand environments and deploy rules

## Commit Convention
- `feat:` — New features
- `fix:` — Bug fixes
- `refactor:` — Code restructuring
- `docs:` — Documentation changes
- `test:` — Test additions/fixes
- `chore:` — Maintenance tasks

## Database Rules
- **ALWAYS** PostgreSQL — **NEVER** SQLite
- **ALWAYS** use Alembic for schema changes — never raw SQL on production
- **ALWAYS** use async sessions (`get_async_db`) — never sync
- Connection uses Supabase PgBouncer on port 6543
- Pool size is intentionally small (3+2) — do not increase

## Deployment Rules
- Local: `docker compose -f docker-compose.dev.yml up --build`
- Staging: `python scripts/deployment/deploy.py --env staging`
- Production: `python scripts/deployment/deploy.py --env production`
- **NEVER** push directly to `main`
- **NEVER** deploy without tests passing

## After ANY Change
- Append a summary entry to `DENTIX_MEMORY.md` → `CHANGES LOG` section
- If a bug was found, add to `OPEN ISSUES`
- If a bug was fixed, move from `OPEN ISSUES` to `RESOLVED` with evidence
