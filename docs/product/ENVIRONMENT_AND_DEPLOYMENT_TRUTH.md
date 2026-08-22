# Dentix Environment and Deployment Truth

This file documents deployment facts verified from executable repository configuration or connected hosting-platform evidence. It intentionally never copies secret values.

## Precedence

1. `.github/workflows/ci.yml`, dedicated verification workflows, and `.github/workflows/cd.yml`
2. executable build/startup/config such as the root `Dockerfile`, `scripts/deployment/startup.sh`, `backend/scripts/preflight_migrations.py`, and `frontend/vercel.json`
3. externally verified hosting/domain bindings when the fact cannot be derived from the repository
4. development compose/Docker/env definitions
5. this document and `WORKFLOW_RULES.md`
6. historical deployment notes

If prose conflicts with executable configuration or current platform evidence, executable/current evidence wins.

## Local development

Repository-supported local development uses `docker-compose.dev.yml` and/or direct backend/frontend development commands. `Dockerfile.do` is an active supporting development image because `docker-compose.dev.yml` builds backend/worker services from it; it is not a production deployment path.

Python dependency truth is `pyproject.toml` + `uv.lock`. Active CI and container paths use frozen `uv` resolution with Python 3.11.

## Staging

Repository-controlled staging flow:

1. scoped work is merged to protected `staging` through the documented PR path;
2. `Dentix CI` tests the exact staging revision;
3. successful staging CI is consumed by `Dentix CD`;
4. CD synchronizes the tested tree to the Hugging Face staging Space referenced by `HF_STAGING_SPACE`;
5. CD verifies `STAGING_BACKEND_URL` health;
6. CD runs the production-like staging Playwright smoke against that deployed HF staging surface.

The production-like staging smoke self-provisions an isolated test clinic at runtime and verifies authentication/session behavior, patient create/read, appointment create/list, finance payment create/list, file upload/access behavior, representative RBAC denial, protected frontend routes, frontend/API reachability, and asset/PWA error absence. The test implementation is `frontend/e2e/staging-deployment-smoke.spec.ts` and its remote-only config is `frontend/playwright.staging.config.ts`.

Connected Vercel verification also confirms a separate `dentix-staging` project exists. That project does not own the production custom domain. Repository `frontend/vercel.json` currently contains the production API rewrite, so the canonical Phase 9 staging verification target is the deployed Hugging Face staging surface rather than assuming a Vercel preview is wired to the staging backend.

## Production backend

Repository-controlled production flow:

1. production code is promoted through protected `main`;
2. `Dentix CI` tests the production revision;
3. `Dentix CD` verifies the tested revision is still current `main`;
4. CD synchronizes that tested tree to the Hugging Face production Space referenced by `HF_PRODUCTION_SPACE`;
5. CD verifies `PRODUCTION_BACKEND_URL` health.

The canonical production container is the root `Dockerfile`. It is a multi-stage Python 3.11 runtime, runs as named non-root user `dentix` with UID/GID 1000, excludes the native build toolchain from the final runtime stage, and uses only narrowly app-owned writable paths.

`Dentix CI` does not stop at a Docker build: its production-container job also starts the canonical image against PostgreSQL, executes the real startup/preflight path, verifies `/api/v1/health`, verifies the runtime identity is UID 1000 / user `dentix`, proves required mutable paths are writable, and proves the root-owned source tree is not writable by the runtime user.

The canonical migration/bootstrap authority is `backend.scripts.preflight_migrations`, invoked exactly once by `scripts/deployment/startup.sh` before Uvicorn starts.

## Production frontend / public domain

The public binding was externally verified rather than inferred from repository prose.

- production Vercel project: `smartclinic-v2plus`
- assigned custom domains: `dentixs.app` and `www.dentixs.app`
- `frontend/vercel.json` serves the SPA/static surface and rewrites `/api/:path*` to the Hugging Face production API

Verified topology:

```text
Public user
   |
   v
Vercel smartclinic-v2plus
   |-- SPA / assets / PWA files
   +-- /api/* -> Hugging Face production backend
```

The Hugging Face production image also embeds a frontend build because the root `Dockerfile` copies `frontend/dist` into backend static files. That direct-HF SPA is a secondary serving surface, not the verified custom-domain frontend binding.

Hosting bindings are mutable external state. Re-verify them before future domain-routing or stale-asset architecture changes.

## Branch promotion and platform protection

- `staging` is the integration/test branch.
- `main` is the production branch.
- `.github/workflows/ci.yml` targets `main` and `staging`; `develop` is not part of the current permanent promotion model.
- `.github/workflows/branch-governance.yml` enforces allowed PR source/target paths.
- `.github/workflows/platform-branch-protection.yml` independently verifies GitHub-side protection for both branches.

During normalization closeout, GitHub platform protection was explicitly verified for both `main` and `staging`, including:

- pull-request-only changes;
- required status checks;
- strict up-to-date required-status-check policy;
- required review-thread resolution;
- non-fast-forward / force-push prevention;
- branch deletion prevention.

Do not weaken those controls to make branch ancestry look cosmetically symmetric. Production promotion remains `staging -> main` or the documented `release/*` / `hotfix/*` path where applicable.

## Database / migrations / tenant isolation

- `backend/database.py` requires `DATABASE_URL`.
- PostgreSQL is the production database contract.
- `scripts/deployment/startup.sh` delegates migration/bootstrap once to `python -m backend.scripts.preflight_migrations`.
- preflight owns existing-versioned upgrades, fresh bootstrap/resume, Alembic-head verification, schema checks, and PostgreSQL RLS invariant verification.
- historical Alembic revisions remain immutable historical records.
- runtime tenant isolation is layered: application visibility/scoping plus PostgreSQL RLS for the canonical tenant-scoped table contract.
- `.github/workflows/rls-concurrency.yml` permanently tests pooled-session A/B reuse with a restricted `NOBYPASSRLS` role and the production async-session path.
- adversarial HTTP tests substitute real Tenant-B identifiers while authenticated as Tenant A across sensitive patient, appointment, treatment, payment, file, and user routes.

## Authentication / secret remediation

The normalization security closeout is complete:

- production and staging `SECRET_KEY` values were rotated separately after a historical high-entropy signing credential was treated as compromised;
- `ENCRYPTION_KEY` was intentionally preserved so signing-key rotation did not rotate persisted encryption material;
- patient-search HMAC derivation prefers dedicated/encryption key material before `SECRET_KEY`;
- the history-aware Gitleaks workflow scans full history and dispositions only exact known historical fingerprints;
- logout/session revocation, password-reset invalidation, access-token expiry, refresh-token rotation/replay rejection, explicit refresh-token expiry, account lockout/rate limiting, and 2FA behavior are regression-tested.

Secret values remain external configuration and must never be copied into this file.

## Stale deployment / PWA verification

`.github/workflows/stale-deployment-recovery.yml` is a permanent regression gate. It builds two real frontend versions, verifies entry hashes change, proves a Version-A asset is absent/404 on the Version-B surface, verifies the Version-B service worker does not precache the stale entry, and verifies the browser preload-recovery cooldown prevents reload loops.

Phase 9 staging smoke additionally watches the deployed HF staging frontend for failed asset/PWA requests and relevant preload/service-worker console errors on protected routes.

The public production frontend remains Vercel, so post-promotion verification must also confirm the live custom domain and `/api/*` route after release.

## Deployment secret/key names referenced by executable workflow

Names may be documented; values must not be copied:

- `HF_TOKEN`
- `HF_STAGING_SPACE`
- `STAGING_BACKEND_URL`
- `HF_PRODUCTION_SPACE`
- `PRODUCTION_BACKEND_URL`

Application/runtime secrets such as signing keys, encryption keys, provider credentials, and patient-search HMAC material remain external configuration.

## Retired deployment surfaces

The authoritative artifact-by-artifact record is [`DEPLOYMENT_ARTIFACT_DISPOSITION.md`](DEPLOYMENT_ARTIFACT_DISPOSITION.md).

Retired production surfaces include the old DigitalOcean/manual deployment script, Caddy/self-hosted production compose files, the stale backend Dockerfile/Procfile path, GHCR publication, and legacy requirements compatibility files after their consumers were removed.

Active supporting development infrastructure remains `docker-compose.dev.yml` + `Dockerfile.do`; neither is a production deployment path.

## Normalization status

The production architecture normalization was promoted to production through protected `main` and is tracked in [`PRODUCTION_ARCHITECTURE_NORMALIZATION_STATUS.md`](PRODUCTION_ARCHITECTURE_NORMALIZATION_STATUS.md).

A later acceptance re-audit found stricter Phase 4/9 verification gaps and stale Phase 8 prose. The executable closeout changes add a real runtime-container smoke, explicit refresh-token-expiry coverage, production-like HF staging smoke, and corrected canonical documentation. Final completion is determined by the status document only after those gates have passed on staging and production promotion evidence is re-verified.
