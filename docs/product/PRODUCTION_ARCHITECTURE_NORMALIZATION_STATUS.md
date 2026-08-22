# Dentix Production Architecture Normalization — Closeout Status

**Closeout date:** 2026-08-22  
**Scope:** final production architecture normalization plan.  
**Rule:** executable runtime/configuration and executable verification outrank this summary if they later diverge.

## Final status

**COMPLETE / PRODUCTION PROMOTED**

The normalization plan has completed through production promotion. The final release was merged through protected `main` in PR #61 at commit `205af784ed29eb804713357241472e4c37a59e76` after the complete release gate set passed on the exact `staging` release head.

## Phase matrix

| Phase | Status | Verified outcome | Ongoing rule |
|---|---|---|---|
| Phase 0 — deployment inventory / proof of use | **PASS** | Active and retired deployment surfaces are traced; executable sources remain authoritative. | Re-run consumer tracing before future destructive deployment cleanup. |
| Phase 0B — production migration startup contract | **PASS** | Startup delegates once to `backend.scripts.preflight_migrations`; PostgreSQL fresh/existing/recovery contracts are tested. | Do not introduce a second startup migration authority. |
| Phase 1 — live public frontend surface verification | **PASS** | Public SPA/assets are on Vercel; `/api/*` routes to the Hugging Face production backend. | Re-verify mutable external bindings before topology changes. |
| Phase 2 — deployment ambiguity cleanup | **PASS** | Obsolete DigitalOcean/manual deploy, Caddy/self-hosted compose, stale backend Dockerfile/Procfile and unused GHCR publication were retired; active dev support was preserved. | Keep only evidence-backed deployment surfaces. |
| Phase 3 — Python dependency normalization | **PASS** | `pyproject.toml` + `uv.lock` are canonical and frozen reproducibility is enforced; legacy requirements files were retired. | Keep active consumers on frozen uv resolution. |
| Phase 4 — production container hardening | **PASS** | Canonical production image is multi-stage, non-root UID 1000, and validated in CI. | Preserve required runtime backup/file tooling when minimizing the image. |
| Phase 5 — stale asset / PWA reproduction | **PASS** | Deterministic stale-hash reproduction and browser recovery regression gates are permanent. | Keep HTML/SW/recovery behavior covered when changing Vite/PWA deployment. |
| Phase 6 — adversarial security forensic audit | **PASS** | File containment, session/reset invalidation, BOLA/IDOR substitution, tenant isolation, and full-history secret scanning are regression-tested. Historical signing credentials were rotated and precisely dispositioned. | Keep exact-fingerprint secret dispositions and adversarial tests intact. |
| Phase 7 — RLS / CI structural safeguards | **PASS** | Runtime tenant-model parity, `subscription_payments` RLS, restricted-role behavior, and pooled-session concurrency are permanently tested. | Keep runtime tenant tables aligned with the canonical RLS contract. |
| Phase 8 — documentation truth normalization | **PASS** | Canonical workflow/deployment/source-map/classification documentation is aligned with executable truth. | Historical documents remain historical. |
| Phase 9 — final staging / production promotion | **PASS** | Platform branch protection was verified, history divergence was reconciled without force/history rewrite, all release gates passed, and PR #61 promoted `staging` to protected `main`. | Preserve protected promotion paths and strict required checks. |

## Platform branch protection — verified

The executable platform gate verified both `main` and `staging` as protected. Applicable rules include:

- pull-request-only changes;
- required status checks;
- strict up-to-date required-status-check policy;
- required review-thread resolution;
- non-fast-forward / force-push prevention;
- branch deletion prevention.

The gate passed after `Require branches to be up to date before merging` was enabled for both protected branches. Branch Governance also continues to enforce the supported direction of travel: scoped branches integrate into `staging`, while production promotion to `main` comes from `staging`, `release/*`, or `hotfix/*`.

## Historical secret remediation — complete

The history-aware scan identified a historical high-entropy `SECRET_KEY` candidate. The remediation path treated it as compromised without rewriting shared Git history:

1. production and staging signing keys were rotated separately;
2. `ENCRYPTION_KEY` was preserved;
3. persisted encryption continues to use `ENCRYPTION_KEY` directly;
4. patient-search HMAC derivation prefers dedicated/encryption key material before `SECRET_KEY`;
5. the known historical finding is dispositioned only by its exact Gitleaks fingerprint;
6. the history scanner remains self-testing and fails on new untriaged findings.

## Safe main/staging reconciliation — complete

Before release, `main` contained one production-only payment-date commit while `staging` contained the newer normalized line. Repository inspection showed the payment-date behavior had already been superseded functionally on `staging` with newer DateTimePicker hardening and regression coverage.

The histories were reconciled without force push or history rewrite. PR #60 recorded the `main` ancestry while preserving the validated `staging` tree exactly; the reconciliation itself had zero file changes. After that, `staging` contained all `main` ancestry and the final release PR #61 was a clean protected promotion to `main`.

After the production merge, `main` contains one additional release merge commit while the `main` and `staging` file trees are identical. A direct `main -> staging` ancestry-only PR was intentionally rejected by Branch Governance because that direction is not an allowed staging integration path; the governance rule was preserved rather than weakened for cosmetic history symmetry.

## Final release evidence

PR #61 passed the release gate set on the exact release head before merge, including:

- frozen Python dependency reproducibility;
- backend tests and coverage;
- PostgreSQL production migration preflight and finance smoke;
- restricted-role RLS and pooled-session concurrency;
- Bandit and dependency vulnerability checks;
- frontend lint, build, and unit tests;
- Playwright critical path and visual regression;
- mobile/responsive acceptance;
- stale-deployment recovery;
- design-system guardrails;
- history-aware secret scanning;
- GitHub platform branch protection verification;
- production container build validation.

The protected production merge completed in PR #61 at `205af784ed29eb804713357241472e4c37a59e76`.

Post-release external verification established:

- Vercel production deployment `smartclinic-v2plus` reached **READY** on the exact production merge SHA;
- `https://www.dentixs.app/` returned HTTP 200 and served the production SPA;
- `https://www.dentixs.app/api/v1/health` returned HTTP 200 with `status=healthy` and application version `2.0.5`, confirming the public Vercel-to-Hugging-Face API path was healthy after promotion.

The connected GitHub workflow reader used during closeout exposes PR-triggered runs rather than the post-merge `push` run, so this document does not claim direct inspection of that specific push-triggered Actions execution. The production deployment and public health checks above provide independent post-release runtime evidence.

## Closeout decision

The production architecture normalization plan is closed as **COMPLETE**. Future changes must preserve the normalized deployment topology, protected branch promotion path, frozen dependency contract, RLS/tenant isolation gates, full-history secret scanning, stale-deployment recovery coverage, and production container validation.