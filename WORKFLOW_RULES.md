# DENTIX WORKFLOW RULES

_Read this before any deployment, git operation, or environment setup._

---

## Environments

| Environment | Branch   | Deploy Method                                            | URL                                    |
|-------------|----------|----------------------------------------------------------|----------------------------------------|
| local       | any      | `docker compose -f docker-compose.dev.yml up --build`    | http://localhost:7860 (API) / http://localhost:5173 (UI) |
| staging     | staging  | `python scripts/deployment/deploy.py --env staging`      | https://dentix-dentix-staging.hf.space |
| production  | main     | `python scripts/deployment/deploy.py --env production`   | https://dentixs.app                    |

---

## Quick Reference Commands

### 🖥️ Local Development
```bash
# Start all services (backend + frontend + redis)
docker compose -f docker-compose.dev.yml up --build

# Stop all services
docker compose -f docker-compose.dev.yml down

# View backend logs
docker compose -f docker-compose.dev.yml logs -f backend

# Run backend tests
pytest backend/tests/ -v --tb=short

# Run frontend tests
cd frontend && npm run test

# Run frontend dev server standalone (without Docker)
cd frontend && npm run dev
```

### 🧪 Deploy to Staging
```bash
# Pre-requisite: tests must pass locally
pytest backend/tests/ -v --tb=short -x

# Deploy
python scripts/deployment/deploy.py --env staging
```

### 🚀 Deploy to Production
```bash
# Pre-requisite: CI passes on GitHub + staging verified manually
# NEVER deploy directly — always merge staging → main first

python scripts/deployment/deploy.py --env production
```

---

## Git Branch Rules

| Action                  | Branch        | Commit Format                          |
|-------------------------|---------------|----------------------------------------|
| Feature work            | `feature/*`   | `feat: description`                    |
| Bug fix                 | `fix/*`       | `fix: description`                     |
| Refactor                | `refactor/*`  | `refactor: description`                |
| Ready for testing       | `staging`     | Merge feature branch → staging         |
| Ready for production    | `main`        | Merge staging → main (after verify)    |

---

## ⛔ NEVER DO

1. **Never** push directly to `main` — always merge from `staging`
2. **Never** skip database migrations before deploying
3. **Never** deploy without running tests first
4. **Never** hardcode secrets in code — use `.env` or env vars
5. **Never** modify production database directly — use Alembic migrations
6. **Never** use SQLite — always PostgreSQL (Supabase)
7. **Never** use Celery — use Prefect for background tasks
8. **Never** return JWT tokens in response body — use httpOnly cookies

---

## 🗣️ Agent Instructions (Arabic Commands)

When the user says:

| User Says                              | Agent Action                                                    |
|----------------------------------------|-----------------------------------------------------------------|
| "شغل لوكل" / "local"                  | Run `docker compose -f docker-compose.dev.yml up --build`       |
| "ارفع على staging" / "deploy staging"  | Run `python scripts/deployment/deploy.py --env staging`         |
| "ارفع على main" / "deploy production"  | Run `python scripts/deployment/deploy.py --env production`      |
| "شغل tests"                           | Run `pytest backend/tests/ -v --tb=short`                       |
| "شغل frontend tests"                  | Run `cd frontend && npm run test`                               |
| "عايز migration"                       | Run `cd backend && alembic revision --autogenerate -m "desc"`   |
| "طبق migration"                       | Run `cd backend && alembic upgrade head`                        |

---

## File Responsibilities

| File                        | Purpose                              | Who Reads It           |
|-----------------------------|--------------------------------------|------------------------|
| `DENTIX_MEMORY.md`         | Project history and decisions        | ALL agents, first      |
| `WORKFLOW_RULES.md`        | This file — environment rules        | ALL agents, on deploy  |
| `docker-compose.yml`       | Production compose (DO)              | deploy.py              |
| `docker-compose.dev.yml`   | Local development compose            | Developer              |
| `.env`                     | Root env vars (local dev)            | Docker, backend        |
| `.env.dev.example`         | Template for local dev env           | Developer setup        |
| `frontend/.env.development`| Frontend dev API URL                 | Vite dev server        |
| `frontend/.env.production` | Frontend prod API URL (empty=same)   | Vite build             |
