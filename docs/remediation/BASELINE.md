# DENTIX Remediation Baseline & Repository Authority

## 1. Repository Authority & Precedence
In accordance with `PROJECT_TRUTH.md`, `PROJECT_STANDARDS.md`, and `AGENTS.md`, authority is evaluated in this order:
1. **Executable runtime/configuration** (backend/main.py, routers, models, migrations, docker-compose).
2. **Executable verification** (backend/tests, ci_tests, vitest, rls-concurrency.yml).
3. **Current governance** (`PROJECT_STANDARDS.md`, `AGENTS.md`).
4. **Canonical truth sources** (`PROJECT_TRUTH.md`, `docs/product/`).
5. **Historical artifacts** (plans, memory files).

## 2. Identified Entry Points & Configurations
- **Repository Name**: `Dentix` (`c:\Users\es\DENTIX`)
- **Backend Entry Point**: `backend/main.py` (FastAPI `app`)
- **Frontend Entry Point**: `frontend/src/main.jsx` (React + Vite)
- **Alembic Configuration**: `backend/alembic.ini`, migrations in `backend/alembic/versions/`
- **Current Alembic Head**: `d0e1f2a3b4c5`
- **Backend Test Runner**: `uv run pytest backend/tests backend/ci_tests` with `PYTHONPATH=.`
- **Frontend Test Runner**: `npm.cmd test -- --run` (Vitest)
- **Frontend Build**: `npm.cmd run build`

## 3. Toolchain Versions
- **Python**: 3.11.15
- **uv**: 0.12.5
- **Node**: v22.22.3
- **npm**: 10.9.8
- **Docker**: 29.5.3
- **OS**: Windows (PowerShell / cmd)

## 4. Local Execution Baseline
- **Local Branch**: `local/readiness-remediation-20260825-0338`
- **Base Commit**: `e507691f` (`fix(pwa): register push_subscriptions in the canonical RLS contract`)
- **Isolation Method**: Dedicated local branch `local/readiness-remediation-20260825-0338`
- **Execution Target**: Local developer machine only (`localhost` / `127.0.0.1` / ephemeral Docker PostgreSQL)
