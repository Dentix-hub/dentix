# Dentix Deployment Artifact Disposition

**Baseline reviewed:** `staging` at `b9860167a1147fe7527a181dbb8d320d7155d345`  
**Review date:** 2026-08-21  
**Scope:** production/development deployment surfaces and their proven consumers.

This file records the disposition decisions made during the production architecture normalization. Runtime/executable sources remain authoritative if later changes make this inventory stale.

## Current canonical deployment surfaces

| Artifact | Disposition | Evidence / responsibility |
|---|---|---|
| `Dockerfile` | **ACTIVE — canonical production container** | Built by CI and consumed by the Hugging Face Docker Spaces synchronized by the canonical CD workflow. |
| `.github/workflows/cd.yml` | **ACTIVE — canonical backend CD** | Deploys tested `staging` and `main` revisions to the configured Hugging Face staging/production Spaces and performs backend health verification. |
| `.github/workflows/ci.yml` production-container job | **ACTIVE — build validation only** | Builds the root production image from the tested revision. No external registry publication is required by the current deployment topology. |
| `frontend/vercel.json` | **ACTIVE — canonical repository-controlled frontend routing** | Routes `/api/:path*` to the Hugging Face production backend before the SPA fallback. Vercel project/domain bindings themselves are external configuration. |
| `scripts/deployment/startup.sh` | **ACTIVE — canonical container startup** | Runs the production migration preflight once, then execs the application command. |
| `backend/scripts/preflight_migrations.py` | **ACTIVE — canonical migration/preflight contract** | Owns fresh bootstrap/existing-schema Alembic handling and PostgreSQL RLS verification. |
| `pyproject.toml` + `uv.lock` | **ACTIVE — canonical Python dependency source** | CI and active production/development container installs use the frozen uv lock. |

## Current supporting development surfaces

| Artifact | Disposition | Evidence / responsibility |
|---|---|---|
| `docker-compose.dev.yml` | **ACTIVE SUPPORTING — local development** | Explicit local composition for backend, workers, Redis, and PostgreSQL. |
| `Dockerfile.do` | **ACTIVE SUPPORTING — local development image** | Referenced by `docker-compose.dev.yml` for backend and worker services. It is not a legacy production Dockerfile. |

## Retired legacy deployment surfaces

The following files were removed after repository consumer tracing showed that they represented an obsolete self-hosted/DigitalOcean/GHCR path rather than the current Hugging Face/Vercel topology.

| Retired artifact | Reason for retirement |
|---|---|
| `Caddyfile` | Self-hosted TLS/reverse-proxy contract. Current public frontend/domain delivery is externally managed by Vercel and API routing is represented by `frontend/vercel.json`. |
| `docker-compose.yml` | Old production-like self-hosted stack that built `Dockerfile.do` and ran Caddy. It was not the canonical local development compose and was not used by current CD. |
| `docker-compose.production.yml` | Self-hosted immutable-image stack requiring `DENTIX_IMAGE`, Caddy, and host-managed volumes. No current deployment consumer was found. |
| `scripts/deployment/deploy.py` | Manual deployment manager containing obsolete Hugging Face Git-copy logic and a hard-coded DigitalOcean SSH/SCP production path. Current CD is GitHub Actions → Hugging Face sync. |
| `backend/Dockerfile` | Stale pip/requirements/gunicorn production image with no current executable consumer; root `Dockerfile` is the canonical production image. |
| `Procfile` | Unused gunicorn deployment entry point with no current executable consumer. |

## GHCR disposition

Repository tracing found GitHub Container Registry publication only in the CI publisher itself and found no current runtime/deployment consumer of the published image. The canonical CD workflow synchronizes tested source revisions directly to Hugging Face Docker Spaces.

Therefore:

- GHCR publication was retired;
- `docker-compose.production.yml` / `DENTIX_IMAGE` were retired with the self-hosted path;
- root `Dockerfile` production-image build validation remains mandatory in CI.

This intentionally preserves production container verification without maintaining an unused artifact-distribution channel.

## Frontend/domain boundary

External verification on 2026-08-21 showed that the Vercel project `smartclinic-v2plus` owns the `dentixs.app` and `www.dentixs.app` domain bindings, while `dentix-staging` is a separate Vercel preview/staging project. Those bindings are mutable external state and are not asserted through a deleted Caddy configuration.

Repository-controlled routing is intentionally narrower and testable: `frontend/vercel.json` must route `/api/:path*` to the Hugging Face production backend before the SPA fallback. The frontend deployment contract tests assert that executable rule.

## Deferred dependency compatibility cleanup

The following compatibility files are **not** part of this deployment-surface cleanup and must be handled in a separate dependency closeout change after confirming all remaining consumers/documentation:

- `requirements.txt`
- `backend/requirements.txt`
- `backend/requirements_root.txt`

The canonical dependency source is already `pyproject.toml` + `uv.lock`; keeping dependency-file retirement separate prevents deployment cleanup from silently changing local/test bootstrap behavior.

## Safety rule for future deployment changes

Do not add a second production deployment path merely because a provider-specific artifact is convenient. A new production surface must identify its real consumer, owner, promotion flow, rollback behavior, secrets/config boundary, and CI validation before it is treated as canonical.
