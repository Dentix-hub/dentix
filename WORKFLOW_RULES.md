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

# Backend tests
pytest backend/tests/ -v --tb=short

# Frontend development
cd frontend && npm run dev

# Frontend tests/build
cd frontend && npm run test
cd frontend && npm run build
```

Use environment files/templates for local values. Never copy production/staging secrets into local documentation.

---

## Staging Promotion

1. Work on a scoped feature/fix/chore branch.
2. Run relevant local checks.
3. Merge/review into `staging` according to repository policy.
4. Let `Dentix CI` test the exact staging revision.
5. Let `Dentix CD` deploy only after successful CI.
6. Verify the staging health/application behavior before production promotion.

Do not use an undocumented fallback deployment branch if `staging` is unavailable.

---

## Production Promotion

1. Production changes must be reviewed and promoted to `main`; do not push directly to `main`.
2. CI must pass for the production revision.
3. `.github/workflows/cd.yml` verifies that the tested revision is current `main` before deployment.
4. The production CD job creates/pushes the deployment snapshot and performs its health check.
5. Database schema changes must use reviewed Alembic migrations; production application startup does not own ad-hoc schema mutation/seeding.

The old `python scripts/deployment/deploy.py --env ...` commands are not the canonical deployment mechanism and must not be used as current truth.

---

## Git Branch Rules

| Action | Branch pattern / target | Commit example |
|---|---|---|
| Feature work | `feature/*` | `feat: description` |
| Bug fix | `fix/*` | `fix: description` |
| Documentation/maintenance | `chore/*` or scoped existing convention | `docs: description` / `chore: description` |
| Ready for shared testing | `staging` | reviewed merge into staging |
| Ready for production | `main` | reviewed promotion after staging verification |

Plan 01 branch inspection found `staging` and `main`; it did **not** find an active `develop` branch. `.github/workflows/ci.yml` still contains a `develop` push trigger, which is a documented cleanup candidate rather than evidence that the branch is active.

---

## NEVER DO

1. Never push directly to `main`.
2. Never bypass required CI/review for production promotion.
3. Never hardcode secrets in code or docs.
4. Never modify the production database schema manually; use Alembic migrations.
5. Never treat SQLite compatibility code as a production database topology; PostgreSQL is the production contract.
6. Never treat frontend route guards as the only authorization control; backend RBAC is authoritative.
7. Never weaken tenant isolation, RLS, CSRF, session, or permission behavior as part of unrelated work.
8. Never invent a deployment branch/target when the intended one is unavailable.

Historical decisions about Celery/Prefect or particular providers are not current operational rules unless confirmed by runtime/config. Current background-worker ownership is documented from `backend/main.py` and `backend/workers/` in the truth map.

---

## Agent Command Mapping

| User intent | Agent action |
|---|---|
| local development | use the repo's development compose/direct commands |
| deploy/promote staging | work through `staging`, current CI, and current CD workflow; do not substitute a legacy script |
| deploy/promote production | promote reviewed code to `main`, then current CI/CD; never direct-push `main` |
| backend tests | `pytest backend/tests/ -v --tb=short` (or narrower relevant tests first) |
| frontend tests/build | use scripts defined in `frontend/package.json` and CI as the final executable reference |
| create migration | use Alembic only when a schema change is explicitly in scope |
| apply migration | use the current Alembic/deployment procedure for the target environment |

---

## Canonical File Responsibilities

| Source | Responsibility |
|---|---|
| `PROJECT_TRUTH.md` | current truth entry point and precedence |
| `PROJECT_STANDARDS.md` | engineering governance |
| `WORKFLOW_RULES.md` | human operational rules; executable sources still win |
| `.github/workflows/ci.yml` | CI triggers/gates/tool versions/thresholds |
| `.github/workflows/cd.yml` | repository-controlled staging/production deployment flow |
| `docker-compose.dev.yml` | local development composition |
| `docker-compose.production.yml` | production container composition/validation where referenced by CI |
| `backend/database.py` + `backend/alembic/` | database/session/migration implementation truth |
| `frontend/src/App.jsx` | current web route tree |
| `frontend/vercel.json` | branch-specific Vercel routing behavior |
| `docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md` | verified human-readable environment/deployment map |
| `DENTIX_MEMORY.md` | historical project memory, not current truth |
