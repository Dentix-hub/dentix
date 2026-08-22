# Dentix Project Truth

## Purpose

This file is the small, stable entry point for current Dentix truth. It does not duplicate values that are better expressed by executable configuration, migrations, route registration, or tests.

## Truth precedence

When sources disagree, use this order:

1. **Executable runtime/configuration** — application code, registered routes, database/migration code, build/deploy configuration.
2. **Executable verification** — CI workflows and tests that exercise the behavior.
3. **Current platform evidence** — GitHub rules/protection and externally verified hosting bindings/runtime health.
4. **Current governance** — `PROJECT_STANDARDS.md`, `AGENTS.md`, and corrected operational rules.
5. **Canonical inventories in `docs/product/`** — verified maps of the current product.
6. **Supporting documentation** — architecture, API, design, testing, and module-specific guides.
7. **Historical material** — plans, implementation ledgers, old state snapshots, and `DENTIX_MEMORY.md` entries.

If executable sources conflict and the correct current behavior cannot be established, record the item as `BLOCKED`; do not guess.

## Canonical truth-source map

- Full source/conflict map: [`docs/product/TRUTH_SOURCE_MAP.md`](docs/product/TRUTH_SOURCE_MAP.md)
- Documentation lifecycle/classification: [`docs/product/DOCUMENTATION_CLASSIFICATION.md`](docs/product/DOCUMENTATION_CLASSIFICATION.md)
- Current modules: [`docs/product/MODULE_REGISTRY.md`](docs/product/MODULE_REGISTRY.md)
- Current capabilities: [`docs/product/CURRENT_PRODUCT_CAPABILITIES.md`](docs/product/CURRENT_PRODUCT_CAPABILITIES.md)
- Environment/deployment: [`docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md`](docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md)
- Deployment artifact ownership/retirement: [`docs/product/DEPLOYMENT_ARTIFACT_DISPOSITION.md`](docs/product/DEPLOYMENT_ARTIFACT_DISPOSITION.md)
- Production architecture normalization closeout status: [`docs/product/PRODUCTION_ARCHITECTURE_NORMALIZATION_STATUS.md`](docs/product/PRODUCTION_ARCHITECTURE_NORMALIZATION_STATUS.md)

## Current module map

The navigable product registry is `docs/product/MODULE_REGISTRY.md`. It covers Dashboard, Patients, Appointments, Dental/Clinical, Finance, Analytics, Labs, Inventory, Users, Settings, AI, Super Admin, and Auth/Public/PWA. Capabilities that are not proven by routes/code/tests are marked `PARTIAL` or `UNKNOWN` rather than inferred.

## Security / RBAC truth links

- Permission matrix: `backend/core/permissions.py`
- Authentication/session implementation: `backend/routers/auth/`, `backend/services/auth_service.py`
- Password-reset implementation: `backend/routers/password_reset.py`
- CSRF enforcement and middleware composition: `backend/main.py`
- Tenant context/session handling: `backend/database.py`, `backend/core/tenancy.py`, `backend/middleware/tenant.py`
- ORM tenant criteria: `backend/core/tenant_scope.py`
- PostgreSQL RLS policy migrations/preflight: `backend/alembic/versions/`, `backend/scripts/preflight_migrations.py`
- Security/isolation verification: `backend/tests/`, `backend/ci_tests/`, `.github/workflows/rls-concurrency.yml`
- Full-history secret verification: `.github/workflows/history-secret-scan.yml`
- File/PHI boundary implementation: `backend/routers/upload.py`, `backend/services/file_service.py`

## Environment / deployment truth links

Use `.github/workflows/ci.yml`, dedicated verification workflows, `.github/workflows/cd.yml`, the root `Dockerfile`, `scripts/deployment/startup.sh`, `backend/scripts/preflight_migrations.py`, and environment key definitions. Repository-controlled production frontend rewrites are expressed in `frontend/vercel.json`.

External Vercel/Hugging Face bindings and secret values are mutable platform state. Use `docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md` for the last verified human-readable map, and re-verify platform state before changes that depend on it.

## Test / CI truth links

- Core CI behavior and current gates: `.github/workflows/ci.yml`
- Canonical production-container build **and runtime** smoke: `.github/workflows/ci.yml` → `Validate Production Container`
- PostgreSQL pooled-session tenant isolation: `.github/workflows/rls-concurrency.yml`
- Stale deployment/PWA recovery: `.github/workflows/stale-deployment-recovery.yml`
- Responsive/mobile web acceptance: `.github/workflows/mobile-responsive.yml`
- Branch PR-path governance: `.github/workflows/branch-governance.yml`
- GitHub-side branch/ruleset verification: `.github/workflows/platform-branch-protection.yml`
- CD, HF health, and production-like HF staging smoke: `.github/workflows/cd.yml`
- Staging smoke implementation: `frontend/e2e/staging-deployment-smoke.spec.ts`
- Backend tests: `backend/tests/`, `backend/ci_tests/`
- Frontend unit tests: `frontend/src/**/*.test.*`
- End-to-end tests: `frontend/e2e/`

## Release truth

The normalization closeout record is `docs/product/PRODUCTION_ARCHITECTURE_NORMALIZATION_STATUS.md`, and production branch reconciliation rules are in `docs/product/GIT_RELEASE_GOVERNANCE.md`.

A prior production promotion does not make later acceptance gaps disappear. Any re-audit finding that affects the plan's Definition of Done must be closed through normal scoped-branch → protected `staging` → protected `main` promotion, with staging production-like smoke and production verification repeated. Do not hide a blocker through documentation cleanup, broad allowlists, force merges, or assumptions about external platform settings.

## Documentation lifecycle rules

- `CANONICAL`: may define current truth when it does not conflict with executable sources.
- `ACTIVE_SUPPORTING`: useful explanation, but executable/canonical sources win.
- `HISTORICAL`: evidence of prior decisions or work; never current truth without re-validation.
- `ARCHIVED`: historical material moved under `docs/archive/` after references are checked.
- `OBSOLETE`: known-invalid instructions or claims retained only where history/evidence requires it.

New implementation plans are intent, not product truth. State snapshots must carry a date/status and must not silently become permanent truth documents.

## Do not duplicate dynamic values

Branch heads, deployment destinations, URLs held in secrets, environment values, package versions, route lists, coverage thresholds, and other dynamic values should link to their executable source instead of being manually copied. If a value must be shown for explanation, identify the executable source that controls it.
