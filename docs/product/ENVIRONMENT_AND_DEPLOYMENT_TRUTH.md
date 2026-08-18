# Dentix Environment and Deployment Truth

This file documents only repository-verified deployment facts. It intentionally does not duplicate secret values.

## Precedence

1. `.github/workflows/ci.yml` and `.github/workflows/cd.yml`
2. branch-specific executable deployment/build config (for example `frontend/vercel.json`)
3. compose/Docker/env definitions
4. this document and `WORKFLOW_RULES.md`
5. historical deployment notes

## Environments

### Local development

Repository-supported local development uses the development compose/config and/or direct backend/frontend development commands. Exact database URLs, keys, and origins belong in environment configuration, not documentation.

Evidence:
- `docker-compose.dev.yml`
- backend env/config/database code
- `frontend/vite.config.js`

### Staging

Verified repository-controlled flow:

1. Work is promoted to the `staging` branch.
2. `Dentix CI` runs for `staging` pushes.
3. On successful CI completion, `Dentix CD` checks out the tested revision.
4. The CD workflow pushes that revision to the Hugging Face staging Space identified by the `HF_STAGING_SPACE` secret.
5. The workflow health-checks the URL provided by `STAGING_BACKEND_URL`.

The actual Space identifier and URL are dynamic external configuration. Do not hardcode them into canonical docs.

### Production

Verified repository-controlled flow:

1. Production code is on `main`.
2. `Dentix CI` tests the revision.
3. `Dentix CD` verifies the tested revision is the current `main` revision.
4. The workflow creates a clean tracked-file snapshot and pushes it to the Hugging Face production Space identified by `HF_PRODUCTION_SPACE`.
5. The workflow health-checks `PRODUCTION_BACKEND_URL`.

On `main`, `frontend/vercel.json` also contains a production frontend rewrite that proxies `/api/:path*` to the current production Hugging Face API destination and serves the SPA fallback. The Vercel project/domain binding itself is external platform configuration and should not be reconstructed from an old prose document.

## Branch promotion truth

- `staging` exists and is the current test/promotion branch used by CD.
- `main` is the production branch used by CD.
- No active `develop` branch was found during the Plan 01 branch inspection, although `.github/workflows/ci.yml` still includes `develop` in its push trigger. This is a documented workflow-cleanup candidate, not changed by this documentation-only plan.
- Do not push directly to `main`; use reviewed promotion through the repository workflow.

## Database/migration deployment truth

- `backend/database.py` requires `DATABASE_URL`.
- Production schema mutation/seeding is explicitly skipped by `backend/main.py`.
- Production migrations are expected to be performed by the deployment/migration path rather than ad-hoc application startup mutation.
- PostgreSQL is the production database contract. SQLite compatibility code may exist for development/test contexts and must not be interpreted as a production deployment option.

## Deployment secret/key names referenced by executable workflow

Names may be documented; values must not be copied:

- `HF_TOKEN`
- `HF_STAGING_SPACE`
- `STAGING_BACKEND_URL`
- `HF_PRODUCTION_SPACE`
- `PRODUCTION_BACKEND_URL`

Other application secrets remain owned by environment/config definitions.

## Stale references resolved by Plan 01

- **DigitalOcean as current production**: historical, not current repository-controlled deployment truth.
- **`python scripts/deployment/deploy.py --env staging|production` as canonical deploy command**: superseded as canonical truth by `.github/workflows/cd.yml`.
- **`docker-compose.yml` described as “Production compose (DO)”**: obsolete provider-specific wording.
- **Hardcoded provider/database names in general docs**: replaced by links to executable config where practical.

## What this file intentionally does not claim

- It does not assert the current external Vercel project name, account, DNS ownership, or secret values.
- It does not assert a mobile-store deployment pipeline.
- It does not claim that every historical deployment script is safe to delete.
- It does not change CI/CD behavior.
