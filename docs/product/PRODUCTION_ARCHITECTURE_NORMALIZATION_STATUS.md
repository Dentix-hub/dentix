# Dentix Production Architecture Normalization — Closeout Status

**Re-audit date:** 2026-08-22  
**Scope:** final production architecture normalization plan.  
**Rule:** executable runtime/configuration and executable verification outrank this summary if they later diverge.

## Current status

**ACCEPTANCE CLOSEOUT IN PROGRESS — PRODUCTION REMAINS HEALTHY**

The architecture normalization was already promoted to production in PR #61 and the production service remains healthy. A stricter re-audit against the original plan's literal Definition of Done found several evidence gaps that must be closed before the program is again labeled `COMPLETE`:

1. canonical documentation still contained stale branch-protection / secret-remediation blocker language;
2. production-container CI built the canonical image but did not start that image as the final non-root user;
3. authentication coverage did not contain an explicit expired-refresh-token test;
4. Phase 9 staging verification stopped at health/CI evidence instead of an executable production-like deployed-staging smoke covering the required business/security paths;
5. Phase 5 needed additional evidence against the real Vercel serving surface, not only a deterministic local A→B reproduction.

Those gaps are being closed through the normal scoped-branch → protected `staging` → protected `main` path. No bypass, force push, history rewrite, Finance V2 redesign, schema redesign, Gunicorn change, worker tuning, or unrelated product work is included.

## Phase matrix

| Phase | Status | Evidence / remaining closeout |
|---|---|---|
| Phase 0 — deployment inventory / proof of use | **PASS** | Active and retired deployment surfaces are traced in `DEPLOYMENT_ARTIFACT_DISPOSITION.md`. |
| Phase 0B — production migration startup contract | **PASS** | Startup delegates once to `backend.scripts.preflight_migrations`; PostgreSQL fresh/existing/interrupted-bootstrap contracts are tested. |
| Phase 1 — live public frontend surface | **PASS** | Public SPA/assets are externally verified on Vercel; `/api/*` reaches Hugging Face production. |
| Phase 2 — deployment ambiguity cleanup | **PASS** | Obsolete self-hosted/DigitalOcean/Gunicorn/GHCR production surfaces were retired while active development support was preserved. |
| Phase 3 — Python dependency normalization | **PASS** | `pyproject.toml` + `uv.lock` are canonical; frozen reproducibility is enforced. |
| Phase 4 — production container hardening | **RE-AUDIT CLOSEOUT** | Image is already multi-stage/non-root UID 1000. `Dentix CI` now additionally starts the canonical image against PostgreSQL and proves startup/preflight, health, runtime UID, writable paths, and source-tree write denial. Must pass on the final staging/release head. |
| Phase 5 — stale asset/PWA | **RE-AUDIT CLOSEOUT** | Permanent deterministic A→B stale-hash + browser recovery gate exists. Real Vercel serving-surface evidence is being added before final closeout. |
| Phase 6 — adversarial security | **RE-AUDIT CLOSEOUT** | Tenant/RBAC/IDOR/file/session/reset/history-secret tests already exist; explicit refresh-token expiry coverage has now been added and must pass on the final head. |
| Phase 7 — RLS / CI structural safeguards | **PASS** | Metadata parity, `subscription_payments` RLS, restricted-role behavior, and pooled-session concurrency are permanent gates. |
| Phase 8 — documentation truth | **RE-AUDIT CLOSEOUT** | `ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md`, `TRUTH_SOURCE_MAP.md`, and `PROJECT_TRUTH.md` are being corrected to current executable/platform truth. |
| Phase 9 — staging / production verification | **RE-AUDIT CLOSEOUT** | CD now performs production-like Playwright smoke against deployed HF staging after health. Final production promotion and post-release verification still must be repeated after staging passes. |

## Existing production evidence

The previous protected production promotion remains valid runtime evidence:

- PR #61 promoted the normalized staging line to protected `main` at `205af784ed29eb804713357241472e4c37a59e76` after the release gates passed;
- PR #64 later promoted the documentation-only closeout to `main` at `ec3b77e3319ed2747bcfe038d4f07a7c9aabec0f`;
- Vercel production reached `READY` on the current `main` revision;
- `https://www.dentixs.app/` returned HTTP 200;
- `https://www.dentixs.app/api/v1/health` returned HTTP 200 with `status=healthy`, version `2.0.5`;
- GitHub reports both `main` and `staging` protected, and the executable platform-protection gate verifies PR-only changes, required checks, strict up-to-date policy, review-thread resolution, non-fast-forward prevention, and deletion prevention;
- production and staging signing keys were rotated separately after the historical high-entropy `SECRET_KEY` candidate was treated as compromised; `ENCRYPTION_KEY` was preserved; full-history Gitleaks scanning remains enforced with exact-fingerprint dispositions only.

These facts show there is no current production outage. The re-opened status is about satisfying the original acceptance contract exactly.

## Acceptance-closeout changes

The scoped closeout implementation adds only evidence/gates and documentation truth:

- explicit expired refresh-token rejection test in `backend/tests/test_auth_adversarial_phase6.py`;
- canonical Docker runtime smoke inside `.github/workflows/ci.yml`;
- remote-only staging Playwright config `frontend/playwright.staging.config.ts`;
- deployed HF staging production-like smoke `frontend/e2e/staging-deployment-smoke.spec.ts`;
- CD enforcement that runs that smoke after HF staging health;
- corrected canonical truth documents.

The staging smoke self-provisions an isolated staging clinic at runtime and verifies:

- health and authentication/session;
- patient create/read;
- appointment create/list;
- payment create/list;
- file upload and authenticated access behavior where local storage is active, or authenticated attachment visibility when external storage is configured;
- representative RBAC enforcement by proving a normal clinic admin cannot access the super-admin tenant endpoint;
- protected frontend routes `/patients`, `/appointments`, and `/billing`;
- absence of failed asset/PWA requests or relevant preload/service-worker console errors.

## Final closeout conditions

This file may return to **COMPLETE / PRODUCTION PROMOTED** only after all of the following are evidenced on the acceptance-closeout line:

1. all protected PR CI/security/RLS/mobile/stale/history/platform gates are green;
2. canonical production-container runtime smoke passes;
3. explicit expired-refresh-token coverage passes;
4. the exact tested revision is promoted to HF staging and the new production-like staging smoke passes;
5. stale-asset behavior is re-verified with evidence tied to the actual Vercel production serving surface in addition to the permanent deterministic recovery gate;
6. the reviewed staging line is promoted through protected `main` without bypass;
7. production health and public frontend/API routing are re-verified after that promotion;
8. canonical documentation is updated with the final evidence and contains no stale blocker claim.

Until those conditions are met, treat the application as **healthy production with normalization acceptance closeout still in progress**, not as a failed migration and not as fully closed.