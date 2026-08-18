# ADR 0004 — Layered tenant isolation

Status: ACCEPTED  
Date verified: 2026-08-18

## Evidence

- `backend/middleware/tenant.py`
- `backend/core/tenancy.py`
- `backend/database.py`
- `backend/core/tenant_scope.py`
- `backend/alembic/versions/bf6c75e1c3d3_add_rls_policies.py`
- tenant-isolation/RLS tests under `backend/tests/`

## Context

Older architecture text described Dentix isolation primarily as automatic ORM filtering. Current implementation also registers PostgreSQL Row-Level Security policies for a defined set of tenant tables and uses tenant-aware async sessions/context.

## Decision

Tenant isolation is defense-in-depth:

1. request/session tenant context,
2. ORM query criteria for mapped tenant entities,
3. PostgreSQL RLS for registered tenant tables,
4. explicit controlled bypass for super-admin/system operations.

No single layer should be documented as the entire isolation model.

## Consequences

- New tenant-owned tables require isolation review, not just a `tenant_id` column.
- Bypass paths are security-sensitive and must remain explicit/tested.
- Service/router visibility rules may further restrict data inside the tenant boundary.

## Non-goals

This ADR does not assert that every table is tenant-owned or RLS-enabled; the migrations/registry are the executable truth for coverage.
