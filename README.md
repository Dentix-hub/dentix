---
title: Dentix — Smart Clinic Management
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 7860
---

# Dentix — Smart Clinic Management System

Dentix is a multi-tenant dental clinic management platform with clinical, scheduling, finance, inventory, administration, and AI-assisted workflows.

> **Current truth:** start with [`PROJECT_TRUTH.md`](PROJECT_TRUTH.md). Route lists, CI gates, deployment targets, environment values, model/provider choices, and other dynamic details are owned by executable config/code rather than this overview.

## Technology Overview

| Layer | Current repository foundation |
|---|---|
| Backend | FastAPI, SQLAlchemy, Alembic, Python 3.11 in CI |
| Frontend | React 18, Vite, Tailwind CSS, TanStack React Query, Zustand |
| Production database contract | PostgreSQL |
| Auth/RBAC | authenticated session/JWT implementation + granular backend permissions |
| Tenant isolation | tenant context/session scoping + ORM criteria + PostgreSQL RLS on registered tables |
| PWA | `vite-plugin-pwa` / Workbox configuration in `frontend/vite.config.js` |
| Observability | internal structured/error logging, trace IDs, system logs, request timing and Prometheus instrumentation |
| CI/CD | GitHub Actions; see `.github/workflows/` |

AI provider/model choices and deployment account values are dynamic configuration and are intentionally not copied here.

## Architecture

High-level request path:

```text
HTTP request
  → middleware/security/tenant context
  → FastAPI router + permission boundary
  → service workflow
  → CRUD/data access where applicable
  → SQLAlchemy session/model
  → PostgreSQL
```

Tenant isolation is defense-in-depth, not a single ORM filter. See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/adr/0001-service-layer-backend-boundaries.md`](docs/adr/0001-service-layer-backend-boundaries.md)
- [`docs/adr/0004-layered-tenant-isolation.md`](docs/adr/0004-layered-tenant-isolation.md)

## Product Inventory

Do not maintain another duplicated feature list here. The verified navigation and capability boundary live in:

- [`docs/product/MODULE_REGISTRY.md`](docs/product/MODULE_REGISTRY.md)
- [`docs/product/CURRENT_PRODUCT_CAPABILITIES.md`](docs/product/CURRENT_PRODUCT_CAPABILITIES.md)

Those inventories cover Dashboard, Patients, Appointments, Dental/Clinical, Finance, Analytics, Labs, Inventory, Users, Settings, AI, Super Admin, Auth/Public/PWA, and the currently partial Flutter mobile client.

## Local Development

Use the repository's current development configuration and environment templates. Canonical Python dependency truth is `pyproject.toml` + `uv.lock`.

```bash
# Backend dependencies/tests/run
uv sync --frozen
uv run pytest backend/tests/ -v --tb=short
uv run uvicorn backend.main:app --reload --port 7860

# Frontend
cd frontend
npm ci
npm run dev
npm run build
```

For composed local services, use `docker-compose.dev.yml`. `DATABASE_URL` is required by the backend; do not embed real secrets in documentation.

## Security Truth Links

- RBAC source: `backend/core/permissions.py`
- Auth implementation: `backend/routers/auth/`
- CSRF middleware: `backend/main.py` + auth login helpers
- Tenant context: `backend/core/tenancy.py`, `backend/middleware/tenant.py`
- ORM tenant scoping: `backend/core/tenant_scope.py`
- PostgreSQL RLS: `backend/alembic/versions/`
- Isolation/security tests: `backend/tests/`

Frontend route guards improve UX/navigation but do not replace backend authorization.

## Background Work

`backend/main.py` currently starts in-process domain-event and subscription-checker workers by default when `ENABLE_IN_PROCESS_WORKERS` is enabled. Additional worker/task integrations exist under `backend/workers/` and `backend/tasks/`; their presence must not be simplified into an outdated “Celery vs Prefect” claim without runtime verification.

## Backup

`backend/services/backup_service.py` contains the verified backup implementation for PostgreSQL full-system dumps and tenant JSON exports followed by Google Drive upload. UI trigger/scheduling state should be verified separately before being described as an operational guarantee.

## Testing and CI

Current executable truth is `.github/workflows/ci.yml`:

- backend tests + coverage/security checks,
- frontend production build + discovered unit tests,
- Playwright critical-path E2E,
- production container validation/build behavior.

Do not copy test counts or coverage thresholds here; they change and are owned by the workflow/test tree.

## Deployment

Current repository-controlled deployment truth is `.github/workflows/cd.yml`. See [`docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md`](docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md) and [`WORKFLOW_RULES.md`](WORKFLOW_RULES.md).

Historical DigitalOcean/deploy-script instructions are not current deployment truth.

## Documentation Map

- Truth precedence: `PROJECT_TRUTH.md`
- Documentation classification: `docs/product/DOCUMENTATION_CLASSIFICATION.md`
- Module registry: `docs/product/MODULE_REGISTRY.md`
- Capability inventory: `docs/product/CURRENT_PRODUCT_CAPABILITIES.md`
- Deployment/environment truth: `docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md`
- Architecture decisions: `docs/adr/`
- Design guidance: `frontend/DESIGN.md`

## License

See the repository license where present.
