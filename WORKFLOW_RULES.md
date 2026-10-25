# DENTIX WORKFLOW RULES

_Environment and deployment reference. Lifecycle, branching, review and promotion rules: docs/engineering/DEVELOPMENT_WORKFLOW.md._

> Current-truth entry point: [`PROJECT_TRUTH.md`](PROJECT_TRUTH.md). When this file conflicts with Git refs, `.github/workflows/`, runtime config, or migrations, the executable source wins.

---

## Environment and Deployment Ownership

| Environment | Branch / context | Repository-controlled deployment truth |
|---|---|---|
| local | any working branch | `docker-compose.dev.yml` and direct dev commands/config |
| staging | `staging` | successful `Dentix CI` → `.github/workflows/cd.yml` staging job → tested revision pushed to the configured Hugging Face staging Space → health check |
| production | `main` | successful `Dentix CI` → `.github/workflows/cd.yml` production job → current tested `main` snapshot pushed to the configured Hugging Face production Space → health check |

The actual Space identifiers, backend URLs, domain bindings, and credentials are dynamic external configuration/secrets. Do not copy them into this file. See [`docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md`](docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md).

`frontend/vercel.json` on `main` is executable production frontend routing configuration. External Vercel project/domain settings remain outside repository truth unless represented by code/config in the repository.

---

## Local Development

```bash
# Start local services

docker compose -f docker-compose.dev.yml up --build

# Stop local services

docker compose -f docker-compose.dev.yml down

# Backend dependency sync / tests
uv sync --frozen
uv run pytest <relevant paths> -q
# full suite only when explicitly requested (see DEVELOPMENT_WORKFLOW §4 Plan-Level Full Run): uv run pytest backend/tests/ -q

# Frontend development
cd frontend && npm run dev

# Frontend tests/build
cd frontend && npm run test
cd frontend && npm run build
```

Use environment files/templates for local values. Never copy production/staging secrets into local documentation.

---

## Staging Promotion

See docs/engineering/DEVELOPMENT_WORKFLOW.md §5.

---

## Production Notes

- Database schema changes must use reviewed Alembic migrations; production application startup does not own ad-hoc schema mutation/seeding.
- If `staging` and `main` are historically diverged, follow `docs/product/GIT_RELEASE_GOVERNANCE.md`: use a documented `release/*` reconciliation branch created from current `main`; never force-merge or rewrite shared branch history just to promote a release.

The retired `scripts/deployment/deploy.py`, self-hosted compose/Caddy path, and GHCR publisher are not current deployment mechanisms. See [`docs/product/DEPLOYMENT_ARTIFACT_DISPOSITION.md`](docs/product/DEPLOYMENT_ARTIFACT_DISPOSITION.md).

---

## Git Branch Rules

See docs/product/GIT_RELEASE_GOVERNANCE.md.

---

## NEVER DO

1. Never push directly to `main` as part of the documented release process.
2. Never bypass required CI/review for production promotion.
3. Never hardcode secrets in code or docs.
4. Never modify the production database schema manually; use Alembic migrations.
5. Never treat SQLite compatibility code as a production database topology; PostgreSQL is the production contract.
6. Tenant isolation, RBAC and security invariants: AGENTS.md §2
7. Never invent a deployment branch/target when the intended one is unavailable.
8. Never force-merge or rewrite shared `main`/`staging` history merely to reconcile a release.

Historical decisions about Celery/Prefect or particular providers are not current operational rules unless confirmed by runtime/config. Current background-worker ownership is documented from `backend/main.py` and `backend/workers/` in the truth map.

---

## Agent Command Mapping

| User intent | Agent action |
|---|---|
| local development | use the repo's development compose/direct commands |
| deploy/promote staging | work through `staging`, current CI, and current CD workflow; do not substitute a retired deployment path |
| deploy/promote production | use reviewed `staging -> main` promotion when clean; otherwise follow the documented `release/*` reconciliation rule; never force-merge |
| backend tests | narrowest relevant tests first (`uv run pytest <paths> -q`); CI is the authoritative gate |
| frontend tests/build | use scripts defined in `frontend/package.json` and CI as the final executable reference |
| create migration | use Alembic only when a schema change is explicitly in scope |
| apply migration | production startup delegates once to `backend.scripts.preflight_migrations`; follow target-environment deployment procedure |

---

## Canonical File Responsibilities

| Source | Responsibility |
|---|---|
| `PROJECT_TRUTH.md` | current truth entry point and precedence |
| `PROJECT_STANDARDS.md` | engineering governance |
| `WORKFLOW_RULES.md` | human operational rules; executable sources still win |
| `.github/workflows/ci.yml` | core CI gates/tool versions/thresholds |
| `.github/workflows/rls-concurrency.yml` | real PostgreSQL pooled-session tenant isolation gate |
| `.github/workflows/stale-deployment-recovery.yml` | stale hashed-asset/PWA recovery gate |
| `.github/workflows/mobile-responsive.yml` | responsive/mobile acceptance gate |
| `.github/workflows/cd.yml` | repository-controlled staging/production backend deployment flow |
| `Dockerfile` | canonical production container build |
| `docker-compose.dev.yml` + `Dockerfile.do` | active local-development composition/image |
| `pyproject.toml` + `uv.lock` | canonical Python dependency source |
| `scripts/deployment/startup.sh` + `backend/scripts/preflight_migrations.py` | production startup and migration/preflight contract |
| `backend/database.py` + `backend/alembic/` | database/session/RLS/migration implementation truth |
| `frontend/src/App.jsx` | current web route tree |
| `frontend/vercel.json` | repository-controlled Vercel routing behavior |
| `docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md` | verified human-readable environment/deployment map |
| `docs/product/DEPLOYMENT_ARTIFACT_DISPOSITION.md` | active/retired deployment artifact decisions |
| `docs/product/PRODUCTION_ARCHITECTURE_NORMALIZATION_STATUS.md` | normalization closeout status and unresolved release blockers |
| `DENTIX_MEMORY.md` | historical project memory, not current truth |
| `docs/product/CURRENT_STATE.md` | current plan/task state card |
