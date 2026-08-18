# Dentix — Architecture Guide

> Supporting architecture summary. [`/PROJECT_TRUTH.md`](../PROJECT_TRUTH.md) and executable code/migrations/tests take precedence.

## Backend layer map

```text
HTTP Request
    ↓
Middleware (security / tenant / CORS / logging)
    ↓
FastAPI Router (HTTP validation, auth/RBAC boundary)
    ↓
Service Layer (business workflows / coordination)
    ↓
CRUD / focused data access where used
    ↓
SQLAlchemy async/sync session boundaries + Models
    ↓
PostgreSQL production database
```

This is an ownership direction, not a claim that every legacy endpoint is already perfectly layered. See ADR 0001.

## Frontend ownership

- `frontend/src/App.jsx` owns the web route tree.
- TanStack React Query is the application server-state/cache foundation.
- Zustand is used for selected client/global UI/auth/tenant state.
- `frontend/src/shared/ui/` owns shared UI primitives; module-specific UI belongs with the feature/page that consumes it.
- `frontend/vite.config.js` owns current PWA build/service-worker behavior.

See ADR 0002.

## Multi-tenancy / isolation

Current isolation is layered:

1. request tenant context (`backend/middleware/tenant.py`, `backend/core/tenancy.py`),
2. tenant-aware DB sessions (`backend/database.py`),
3. ORM loader criteria for tenant-mapped entities (`backend/core/tenant_scope.py`),
4. PostgreSQL Row-Level Security for the tables registered by migrations,
5. explicit controlled super-admin/system bypass.

Do not describe ORM filtering alone as the complete isolation strategy. See ADR 0004 and the RLS migrations.

## RBAC

`backend/core/permissions.py` is the permission/role source of truth. Individual routers enforce permissions and may add visibility restrictions. `frontend/src/App.jsx` contains route-level role guards for some surfaces, but frontend guards are not an authorization substitute.

## Session / CSRF boundary

`backend/main.py` composes the current middleware stack. State-changing cookie-auth requests are subject to CSRF validation using the current auth helper behavior; Bearer-auth requests are handled separately by the middleware. Exempt paths are executable code and should not be manually duplicated into long-lived prose.

## Background work and observability

- `backend/main.py` starts in-process domain-event and subscription-checker workers when enabled.
- Worker/task implementations live under `backend/workers/` and `backend/tasks/`.
- Current verified observability includes internal structured/error logging, correlation/trace IDs, slow-request timing, system logs, and Prometheus instrumentation.
- Sentry is explicitly marked removed/deprecated in `backend/main.py`; old Sentry references are historical.

## Database

PostgreSQL is the production contract. `DATABASE_URL` is required. Production startup skips schema mutation/seeding; schema changes belong to reviewed migrations/deployment procedures. See ADR 0003.

## Related canonical maps

- `../PROJECT_TRUTH.md`
- `product/TRUTH_SOURCE_MAP.md`
- `product/MODULE_REGISTRY.md`
- `../docs/adr/README.md`
