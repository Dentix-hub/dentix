# DENTIX PROJECT MEMORY

_Agent-agnostic. Append-only. Read this file before any work on Dentix._
_Last updated: 2026-06-22_

---

## 🔴 OPEN ISSUES

| ID    | Issue                              | Discovered | Attempted Fix                          | Status         |
|-------|------------------------------------|-----------|----------------------------------------|----------------|
| E-001 | subscription_plan MissingGreenlet  | 2025-03   | 3x claimed fixed, not confirmed        | NEEDS EVIDENCE |
| E-002 | Dashboard 13 queries on cache miss | 2025-05   | Prompt authored, outcome unknown       | PENDING        |

---

## ✅ RESOLVED

_Migrated from HERMES_STATE.md on 2026-06-22_

| ID    | Issue                                        | Fix Summary                                                                                                                       | Date    |
|-------|----------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|---------|
| R-001 | Logger duplication conflict                  | Deleted `frontend/src/lib/logger.js`, dynamic import `utils/logger` in `ErrorBoundary.jsx`                                        | 2025-Q4 |
| R-002 | Firebase credentials in workspace            | Deleted `firebase-service-account.json`, updated `.gitignore`/`.dockerignore`, switched to env var loading                        | 2025-Q4 |
| R-003 | Tokens leaked in login response body         | Moved access/refresh tokens to httpOnly cookies with restricted path and shorter lifetimes                                        | 2025-Q4 |
| R-004 | Cookie SameSite breaking external links      | Set `_COOKIE_SAMESITE` to `"lax"`                                                                                                 | 2025-Q4 |
| R-005 | `success_response(success=False)` crash      | Replaced with `error_response(...)` in `verify_reset_token`                                                                       | 2025-Q4 |
| R-006 | Legacy Celery patterns in workers            | Migrated outbox + subscription checker to Prefect tasks/flows, deleted Celery verification tests                                  | 2025-Q4 |
| R-008 | Default access token too long                | Reduced to 15 minutes in `backend/auth.py`                                                                                        | 2025-Q4 |
| R-009 | Sync engine exports causing issues           | Removed sync `engine` and `SessionLocal` from `database.py` exports, re-routed health check to `async_engine`                    | 2025-Q4 |
| R-010 | Legacy `backend/backup_service.py`           | Deleted root-level file to prevent import confusion with services package                                                         | 2025-Q4 |
| R-011 | Legacy Celery test file                      | Deleted `backend/tests/verify_celery_config.py`                                                                                   | 2025-Q4 |
| R-012 | Treatment model missing soft delete          | Added `is_deleted` and `deleted_at` to `Treatment` model + migration `da377f438006`                                              | 2025-Q4 |
| R-013 | Missing tenant isolation tests               | Implemented 5 integration tests in `test_tenant_isolation.py` (cross-tenant reads, updates, RLS registry, admin bypass, context) | 2025-Q4 |

---

## 📋 CHANGES LOG

_Append new entries at TOP. One entry per meaningful change._

### [2026-06-22] — Local Self-Contained Database Setup
- **What**: Added local PostgreSQL database service to docker-compose.dev.yml and configured local connection strings
- **Why**: Enable fully isolated local development without touching production/staging databases
- **Files**: `docker-compose.dev.yml`, `.env`, `.env.dev.example`, `scripts/dev/start-local.ps1`
- **Agent**: Gemini 3.5 Flash
- **Risk**: None — dev environment safety enhancement

### [2026-06-22] — DevOps Infrastructure Overhaul
- **What**: Created DENTIX_MEMORY.md, WORKFLOW_RULES.md, docker-compose.dev.yml, ECC rules
- **Why**: Standardize dev environment, agent workflow, and project memory
- **Files**: `DENTIX_MEMORY.md`, `WORKFLOW_RULES.md`, `docker-compose.dev.yml`, `.env.dev.example`, `.agent/rules/dentix/`
- **Agent**: Opus (plan) + Gemini (execute)
- **Risk**: None — additive changes only

---

## 🏛️ KEY DECISIONS

| Decision                                           | Rationale                                                           | Date       |
|----------------------------------------------------|---------------------------------------------------------------------|------------|
| Shared DB + RLS (not separate schemas)             | Simpler migrations, rls library support                             | 2024       |
| contextvars for super_admin bypass                 | Module globals = cross-tenant leak in async                         | 2025-04    |
| No tenant_id NOT NULL migration yet                | Requires data audit first                                           | 2025-05    |
| Prefect over Celery                                | Celery fully removed; Prefect is simpler for current scale          | 2025-Q4    |
| JWT in httpOnly cookies (not response body)        | Security best practice — prevents XSS token theft                   | 2025-Q4    |
| Supabase PgBouncer (port 6543) with minimal pool   | pool_size=3, max_overflow=2 to avoid PgBouncer circuit breaker      | 2025-Q4    |
| Stay on DigitalOcean (not HuggingFace for prod)    | HF cold starts unacceptable; DO stays until stable revenue          | 2026-06    |
| Domain on name.com (dentixs.app)                   | Managed DNS, Caddy handles SSL via ACME                             | 2024       |
