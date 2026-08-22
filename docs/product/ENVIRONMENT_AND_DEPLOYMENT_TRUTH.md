# Dentix Environment and Deployment Truth

This file documents deployment facts verified from executable repository configuration or the connected hosting platform. It intentionally does not duplicate secret values.

## Precedence

1. `.github/workflows/ci.yml`, dedicated verification workflows, and `.github/workflows/cd.yml`
2. executable deployment/build config such as the root `Dockerfile`, startup/preflight code, and `frontend/vercel.json`
3. externally verified hosting/domain bindings when the fact cannot be derived from the repository
4. development compose/Docker/env definitions
5. this document and `WORKFLOW_RULES.md`
6. historical deployment notes

## Environments

### Local development

Repository-supported local development uses `docker-compose.dev.yml` and/or direct backend/frontend development commands. `Dockerfile.do` is an active supporting development image because the development compose file builds the backend and workers from it.

Python dependency truth is `pyproject.toml` + `uv.lock`; active CI/container paths use frozen `uv` resolution.

### Staging

Verified repository-controlled backend flow:

1. Work is promoted to `staging` through the documented scoped-branch PR path.
2. Repository CI/security gates test the revision.
3. Successful tested revisions are handled by `Dentix CD`.
4. CD synchronizes the tested tree to the Hugging Face staging Space identified by `HF_STAGING_SPACE`.
5. CD health-checks `STAGING_BACKEND_URL`.

Connected Vercel verification on 2026-08-21 also confirmed a separate `dentix-staging` project. The production custom domain is not assigned to that project.

### Production backend

Verified repository-controlled flow:

1. Production code is on `main`.
2. Repository CI tests the production revision.
3. `Dentix CD` verifies the tested revision is still current `main`.
4. CD synchronizes the tested tree to the Hugging Face production Space identified by `HF_PRODUCTION_SPACE`.
5. CD health-checks `PRODUCTION_BACKEND_URL`.

The canonical production container is the root `Dockerfile`. It is validated by CI as a non-root multi-stage runtime image. The canonical migration/bootstrap authority is `backend.scripts.preflight_migrations`, invoked exactly once by `scripts/deployment/startup.sh` before Uvicorn starts.

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
- Current `.github/workflows/ci.yml` targets `main` and `staging`; no permanent `develop` branch is part of the current model.
- `.github/workflows/branch-governance.yml` validates allowed PR source/target paths, but repository workflow code is not a substitute for GitHub platform branch/ruleset enforcement.
- During this normalization closeout, the classic branch API reported `protected=false` for both `main` and `staging`. The available connector could not verify modern repository rulesets, so effective platform protection remains **UNVERIFIED** rather than being inferred either way.
- Before production promotion, verify that platform settings/rulesets actually enforce PR-only changes, required status checks, no force push, and the release governance requirements.
- `main` and `staging` were also observed to be historically diverged during Phase 8 verification. Do not force-merge them. Re-check current divergence at release time and use the documented `release/*` reconciliation procedure when direct `staging -> main` promotion is not clean.

## Database / migration / tenant-isolation truth

- `backend/database.py` requires `DATABASE_URL`.
- PostgreSQL is the production database contract.
- `scripts/deployment/startup.sh` delegates migration/bootstrap once to `python -m backend.scripts.preflight_migrations`.
- `backend.scripts.preflight_migrations` owns existing-versioned upgrades, fresh database bootstrap/resume, Alembic-head verification, schema checks, and PostgreSQL RLS invariant verification.
- Historical Alembic revisions remain historical records and are not rewritten to normalize startup.
- Runtime tenant isolation is layered: application visibility/scoping plus PostgreSQL RLS for the canonical tenant-scoped table contract.
- `.github/workflows/rls-concurrency.yml` permanently tests pooled-session A/B tenant reuse using a restricted `NOBYPASSRLS` role and the production async session path.
- Backend adversarial HTTP tests substitute real Tenant-B identifiers while authenticated as Tenant A across sensitive patient, appointment, treatment, payment, file, and user routes.

## Stale deployment / PWA verification

`.github/workflows/stale-deployment-recovery.yml` is a permanent regression gate that builds two real frontend versions, proves hashed entry assets change and stale Version-A assets fail against Version B, then verifies the existing browser preload recovery avoids a reload loop. Runtime API caching remains separate from this asset-recovery behavior.

## Deployment secret/key names referenced by executable workflow

Names may be documented; values must not be copied:

- `HF_TOKEN`
- `HF_STAGING_SPACE`
- `STAGING_BACKEND_URL`
- `HF_PRODUCTION_SPACE`
- `PRODUCTION_BACKEND_URL`

Application/runtime secrets such as `SECRET_KEY`, encryption keys, and patient-search HMAC material are external configuration and must never be copied into this document.

## Retired deployment surfaces

Phase 2 completed consumer tracing and retired the obsolete self-hosted/deployment path. The authoritative artifact-by-artifact record is [`DEPLOYMENT_ARTIFACT_DISPOSITION.md`](DEPLOYMENT_ARTIFACT_DISPOSITION.md).

Retired surfaces include the old DigitalOcean/manual deployment script, Caddy/self-hosted production compose files, the stale backend Dockerfile/Procfile path, GHCR publication, and the legacy requirements compatibility files after their consumers were removed.

Active supporting development infrastructure remains `docker-compose.dev.yml` + `Dockerfile.do`; neither should be confused with the retired production surfaces.

## Production-promotion blockers at normalization closeout

Architecture/runtime normalization being validated does **not** automatically authorize production promotion. See [`PRODUCTION_ARCHITECTURE_NORMALIZATION_STATUS.md`](PRODUCTION_ARCHITECTURE_NORMALIZATION_STATUS.md) for current closeout blockers.

In particular, a history-aware secret scan identified a historical high-entropy `SECRET_KEY` candidate in shared branch ancestry. It is intentionally not allowlisted. Safe remediation requires runtime key-topology proof because patient-phone blind-index HMAC derivation can fall back to `SECRET_KEY` when no dedicated search/encryption key is configured. Production rotation or history rewriting must not be performed blindly.
