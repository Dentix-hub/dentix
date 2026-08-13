---
trigger: always_on
---

# Dentix Architecture Context

> Project-scoped rule. Describes the Dentix tech stack so agents don't guess.

## Tech Stack

| Layer      | Technology                           | Notes                                      |
|------------|--------------------------------------|--------------------------------------------|
| Backend    | FastAPI + SQLAlchemy Async + Alembic | Python 3.11                                |
| Frontend   | React 18 + Vite + Tailwind CSS      | RTL/Arabic-first, PWA enabled              |
| Database   | PostgreSQL (Supabase, PgBouncer)     | Port 6543, pool_size=3                     |
| Cache      | Redis 7                             | Used for sessions and caching              |
| Workers    | Prefect                             | **NOT Celery** — Celery was fully removed  |
| Auth       | JWT in httpOnly cookies              | **NOT** in response body                   |
| Multi-tenant | RLS via `rls` library              | `tenant_id` + `contextvars`                |
| Monitoring | None (Datadog removed)              | Use container logs for now                 |
| Hosting    | DigitalOcean Droplet                | Docker Compose + Caddy + SSL               |
| Staging    | HuggingFace Spaces                  | Separate HF repo push                     |
| Domain     | dentixs.app (name.com)              | Caddy handles ACME/SSL                     |

## Key File Locations

| What                    | Path                                        |
|-------------------------|---------------------------------------------|
| FastAPI entry point     | `backend/main.py`                           |
| Database config         | `backend/database.py`                       |
| Models                  | `backend/models/`                           |
| Routers (API)           | `backend/routers/`                          |
| Services (business)     | `backend/services/`                         |
| Alembic config          | `backend/alembic.ini`                       |
| Migrations              | `backend/alembic/versions/`                 |
| Frontend source         | `frontend/src/`                             |
| Frontend API client     | `frontend/src/api/apiClient.js`             |
| Production Dockerfile   | `Dockerfile.do` (used by docker-compose.yml)|
| Dev Compose             | `docker-compose.dev.yml`                    |
| Prod Compose            | `docker-compose.yml`                        |
| Deploy script           | `scripts/deployment/deploy.py`              |
| Startup script          | `scripts/deployment/startup.sh`             |

## Common Pitfalls (from DENTIX_MEMORY.md)
1. `subscription_plan` MissingGreenlet — lazy-loaded relationship in async context
2. Dashboard fires 13 queries on cache miss — use Redis cache
3. PgBouncer with large pool_size → circuit breaker trips — keep pool_size ≤ 5
4. `asyncpg` expects `ssl=SSLContext` object, not `sslmode=require` string
