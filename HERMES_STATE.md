> ⚠️ **DEPRECATED** — This file is Hermes-session-specific.
> For project-wide memory, read **DENTIX_MEMORY.md** instead.
> All historical data has been migrated to DENTIX_MEMORY.md on 2026-06-22.

---

# HERMES_STATE — DENTIX Production Readiness Fixes

| Blocker / Issue | Status | Description |
|---|---|---|
| **BLOCK-1** | ✅ FIXED | Resolved logger duplication conflict by deleting `frontend/src/lib/logger.js` and dynamically importing `utils/logger` in `ErrorBoundary.jsx`. Built successfully. |
| **BLOCK-2** | ✅ FIXED | Deleted `firebase-service-account.json` from workspace, updated `.gitignore` and `.dockerignore`, switched loading logic to environment variables, and verified file is untracked by Git. |
| **BLOCK-3** | ✅ FIXED | Removed access/refresh tokens from login/refresh/2FA response bodies. Placed in secure httpOnly cookies with restricted pathing and shorter lifetimes. Updated `AuthProvider.jsx` to load user details directly. |
| **BLOCK-4** | ✅ FIXED | Set `_COOKIE_SAMESITE` to `"lax"` to ensure smooth navigation from external links in production environments. |
| **BLOCK-5** | ✅ FIXED | Replaced invalid `success_response(success=False, ...)` calls in `verify_reset_token` with `error_response(...)` to prevent crashes on invalid reset links. |
| **BLOCK-6** | ✅ FIXED | Migrated outbox event processor and subscription checker to Prefect tasks and flows, removed the raw loop patterns in their flow implementations, and deleted legacy Celery verification tests. |
| **BLOCK-7** | ✅ FIXED | Documented external PostgreSQL setup at the top of the compose file, and added resource limits for datadog (0.25 CPU, 256M memory) and openwa (0.50 CPU, 512M memory) services. |

## Partials

| Partial Issue | Status | Description |
|---|---|---|
| **P1** | ✅ FIXED | Default access token lifetime reduced to 15 minutes in `backend/auth.py`. |
| **P2** | ✅ FIXED | Removed sync `engine` and `SessionLocal` from `backend/database.py` exports. Re-routed health check metrics and index scripts to use `async_engine`, and localized sync helpers in debug/migration scripts. |
| **P3** | ✅ FIXED | Deleted legacy root-level `backend/backup_service.py` to prevent import confusion with the correct services package. |
| **P4** | ✅ FIXED | Deleted legacy `backend/tests/verify_celery_config.py` since Celery has been completely removed in favor of Prefect. |
| **P5** | ✅ FIXED | Added `is_deleted` and `deleted_at` to `Treatment` model in `clinical.py` and created the matching database migration `da377f438006_add_soft_delete_to_treatment.py`. |
| **P6** | ✅ FIXED | Implemented all 5 missing tenant isolation integration tests in `test_tenant_isolation.py`, covering cross-tenant reads, updates, model RLS registry, admin bypass, and session contexts. |
