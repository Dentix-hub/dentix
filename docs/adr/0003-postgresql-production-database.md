# ADR 0003 — PostgreSQL production database contract

Status: ACCEPTED  
Date verified: 2026-08-18

## Evidence

- `backend/database.py`
- `backend/main.py`
- `backend/alembic/`
- `.github/workflows/ci.yml`
- `backend/services/backup_service.py`

## Context

Dentix requires `DATABASE_URL`, has PostgreSQL-specific RLS policies and production migration behavior, and CI exercises the backend against PostgreSQL. Some database code retains SQLite compatibility branches for non-production contexts.

## Decision

PostgreSQL is the production database contract. Production schema changes are migration-driven. SQLite compatibility code is not evidence of a supported production deployment topology.

Provider-specific host names are dynamic configuration and are not part of this ADR.

## Consequences

- Production features may rely on PostgreSQL capabilities such as RLS.
- Migrations must be reviewed as part of schema changes.
- Documentation must not hardcode a database provider unless executable deployment config requires it.

## Non-goals

This ADR does not remove test/development compatibility code and does not change the current database provider/account.
