# Dentix Environment and Deployment Truth

This file documents deployment facts verified from executable repository configuration or the connected hosting platform. It intentionally does not duplicate secret values.

## Precedence

1. `.github/workflows/ci.yml` and `.github/workflows/cd.yml`
2. executable deployment/build config such as `frontend/vercel.json`
3. externally verified hosting/domain bindings when the fact cannot be derived from the repository
4. compose/Docker/env definitions
5. this document and `WORKFLOW_RULES.md`
6. historical deployment notes

## Environments

### Local development

Repository-supported local development uses `docker-compose.dev.yml` and/or direct backend/frontend development commands. `Dockerfile.do` is an active supporting development image because the development compose file builds the backend and workers from it.

### Staging

Verified repository-controlled backend flow:

1. Work is promoted to `staging`.
2. `Dentix CI` tests the revision.
3. Successful tested revisions are handled by `Dentix CD`.
4. CD synchronizes the tested tree to the Hugging Face staging Space identified by `HF_STAGING_SPACE`.
5. CD health-checks `STAGING_BACKEND_URL`.

Connected Vercel verification on 2026-08-21 also confirmed a separate `dentix-staging` project. The production custom domain is not assigned to that project.

### Production backend

Verified repository-controlled flow:

1. Production code is on `main`.
2. `Dentix CI` tests the revision.
3. `Dentix CD` verifies the tested revision is still current `main`.
4. CD synchronizes the tested tree to the Hugging Face production Space identified by `HF_PRODUCTION_SPACE`.
5. CD health-checks `PRODUCTION_BACKEND_URL`.

The canonical production container is the root `Dockerfile`. The canonical migration/bootstrap authority is `backend.scripts.preflight_migrations`, invoked exactly once by `scripts/deployment/startup.sh` before Uvicorn starts.

### Production frontend / public domain

The custom-domain binding was externally verified on 2026-08-21 rather than inferred from repository prose.

- production Vercel project: `smartclinic-v2plus`
- assigned custom domains include `dentixs.app` and `www.dentixs.app`
- `frontend/vercel.json` serves the SPA/static surface and rewrites `/api/:path*` to the Hugging Face production API destination

Verified public topology:

```text
Public user
   |
   v
Vercel smartclinic-v2plus
   |-- SPA / assets / PWA files
   +-- /api/* -> Hugging Face production backend
```

The Hugging Face production image also embeds a frontend build, but that is a secondary direct-HF serving surface, not the verified custom-domain frontend binding.

Hosting bindings are mutable external state. Re-verify them before future domain-routing or stale-asset architecture changes.

## Branch promotion truth

- `staging` is the current test/promotion branch.
- `main` is the production branch.
- Current `.github/workflows/ci.yml` targets `main` and `staging`; the previously documented `develop` CI trigger has been removed.
- Do not push directly to `main`; use the reviewed promotion path.

## Database/migration deployment truth

- `backend/database.py` requires `DATABASE_URL`.
- PostgreSQL is the production database contract.
- `scripts/deployment/startup.sh` delegates migration/bootstrap once to `python -m backend.scripts.preflight_migrations`.
- `backend.scripts.preflight_migrations` owns existing-versioned upgrades, fresh database bootstrap/resume, Alembic-head verification, schema checks, and PostgreSQL RLS invariant verification.
- Historical Alembic revisions remain historical records and are not rewritten to normalize startup.

## Deployment secret/key names referenced by executable workflow

Names may be documented; values must not be copied:

- `HF_TOKEN`
- `HF_STAGING_SPACE`
- `STAGING_BACKEND_URL`
- `HF_PRODUCTION_SPACE`
- `PRODUCTION_BACKEND_URL`

## Historical / non-canonical deployment references

- DigitalOcean as current production: historical.
- `python scripts/deployment/deploy.py --env staging|production` as the canonical deploy command: superseded by `.github/workflows/cd.yml`.
- `docker-compose.yml` as current production infrastructure: historical unless a separate active consumer is explicitly proven.

Historical deployment artifacts are not automatically safe to delete merely because they are non-canonical; Phase 0/2 disposition proof is required before destructive cleanup.
