# DENTIX WORKFLOW RULES

_Read this before any deployment, git operation, or environment setup._

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
uv run pytest backend/tests/ -v --tb=short

# Frontend development
cd frontend && npm run dev

# Frontend tests/build
cd frontend && npm run test
cd frontend && npm run build
```

Use environment files/templates for local values. Never copy production/staging secrets into local documentation.

---

## Staging Promotion

1. Work on a scoped feature/fix/chore/docs/test branch.
2. Run relevant local checks.
3. Merge/review into `staging` according to repository policy.
4. Let the repository CI/security gates test the exact staging revision.
5. Let `Dentix CD` deploy only after successful required CI.
6. Verify staging health/application behavior before production promotion.

Do not use an undocumented fallback deployment branch if `staging` is unavailable.

---

## Production Promotion

1. Production changes must be reviewed and promoted to `main`; do not push directly to `main`.
2. CI must pass for the production revision.
3. `.github/workflows/cd.yml` verifies that the tested revision is current `main` before deployment.
4. The production CD job synchronizes the tested snapshot and performs its health check.
5. Database schema changes must use reviewed Alembic migrations; production application startup does not own ad-hoc schema mutation/seeding.
6. If `staging` and `main` are historically diverged, follow `docs/product/GIT_RELEASE_GOVERNANCE.md`: use a documented `release/*` reconciliation branch created from current `main`; never force-merge or rewrite shared branch history just to promote a release.

The retired `scripts/deployment/deploy.py`, self-hosted compose/Caddy path, and GHCR publisher are not current deployment mechanisms. See [`docs/product/DEPLOYMENT_ARTIFACT_DISPOSITION.md`](docs/product/DEPLOYMENT_ARTIFACT_DISPOSITION.md).

---

## Git Branch Rules

| Action | Branch pattern / target | Commit example |
|---|---|---|
| Feature work | `feat/*` or `feature/*` | `feat: description` |
| Bug fix | `fix/*` | `fix: description` |
| Refactor | `refactor/*` | `refactor: description` |
| Documentation/maintenance | `docs/*` or `chore/*` | `docs: description` / `chore: description` |
| Tests | `test/*` | `test: description` |
| Ready for shared testing | `staging` | reviewed merge into staging |
| Ready for production | `main` | reviewed promotion after staging verification |

The permanent branch model is `staging` + `main`. There is no active permanent `develop` branch, and current `.github/workflows/ci.yml` targets `main` and `staging`.

---

## NEVER DO

1. Never push directly to `main` as part of the documented release process.
2. Never bypass required CI/review for production promotion.
3. Never hardcode secrets in code or docs.
4. Never modify the production database schema manually; use Alembic migrations.
5. Never treat SQLite compatibility code as a production database topology; PostgreSQL is the production contract.
6. Never treat frontend route guards as the only authorization control; backend RBAC is authoritative.
7. Never weaken tenant isolation, RLS, CSRF, session, or permission behavior as part of unrelated work.
8. Never invent a deployment branch/target when the intended one is unavailable.
9. Never force-merge or rewrite shared `main`/`staging` history merely to reconcile a release.

Historical decisions about Celery/Prefect or particular providers are not current operational rules unless confirmed by runtime/config. Current background-worker ownership is documented from `backend/main.py` and `backend/workers/` in the truth map.

---

## Agent Command Mapping

| User intent | Agent action |
|---|---|
| local development | use the repo's development compose/direct commands |
| deploy/promote staging | work through `staging`, current CI, and current CD workflow; do not substitute a retired deployment path |
| deploy/promote production | use reviewed `staging -> main` promotion when clean; otherwise follow the documented `release/*` reconciliation rule; never force-merge |
| backend tests | `uv run pytest backend/tests/ -v --tb=short` (or narrower relevant tests first) |
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
| `.github/workflows/postgres-rls-concurrency.yml` | real PostgreSQL pooled-session tenant isolation gate |
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
