# Dentix Production Architecture Normalization — Closeout Status

**Closeout date:** 2026-08-22  
**Scope:** final production architecture normalization plan.  
**Rule:** executable runtime/configuration and executable verification outrank this summary if they later diverge.

This document records what the normalization work has actually proved and, equally importantly, what is still unresolved. It is not a production-promotion authorization.

## Status legend

- **PASS** — implementation and required verification are present on `staging`.
- **PARTIAL / BLOCKED** — verified work exists, but a mandatory unresolved item prevents the phase/release from being treated as fully closed.
- **NOT STARTED** — no verified implementation/evidence.

## Phase matrix

| Phase | Status | Verified outcome | Remaining action |
|---|---|---|---|
| Phase 0 — deployment inventory / proof of use | **PASS** | Active and retired deployment surfaces are traced in `DEPLOYMENT_ARTIFACT_DISPOSITION.md`; executable sources remain authoritative. | Re-run consumer tracing before any future destructive deployment cleanup. |
| Phase 0B — production migration startup contract | **PASS** | `scripts/deployment/startup.sh` delegates once to `backend.scripts.preflight_migrations`; PostgreSQL fresh/existing/recovery contracts are tested. | Do not introduce a second startup migration authority. |
| Phase 1 — live public frontend surface verification | **PASS** | Public SPA/assets were externally verified on Vercel; `/api/*` routes to the Hugging Face production backend; direct HF SPA is secondary. | Re-verify mutable external bindings before topology changes. |
| Phase 2 — deployment ambiguity cleanup | **PASS** | Obsolete DigitalOcean/manual deploy, Caddy/self-hosted compose, stale backend Dockerfile/Procfile and unused GHCR publication were retired; active dev compose/image preserved. | None for the normalized topology. |
| Phase 3 — Python dependency normalization | **PASS** | `pyproject.toml` + `uv.lock` are canonical; frozen reproducibility is enforced; legacy requirements files were retired after their consumers were removed. | Keep active consumers on frozen uv resolution. |
| Phase 4 — production container hardening | **PASS** | Root production Docker image uses a multi-stage, non-root UID 1000 runtime with only required writable paths/tooling; CI builds the real image. | Preserve runtime backup/file dependencies when minimizing the image. |
| Phase 5 — stale asset / PWA reproduction | **PASS** | Permanent Version-A → Version-B stale-hash reproduction and browser preload-recovery regression gate exist in `.github/workflows/stale-deployment-recovery.yml`. | Keep HTML/SW/recovery behavior covered when changing Vite/PWA deployment. |
| Phase 6 — adversarial security forensic audit | **PASS after PR #56 history-secret gate is green on `staging`** | File path containment, server-side logout/reset-session invalidation, HTTP BOLA/IDOR substitution, token/reset abuse cases, tenant boundary behavior, and full-history secret scanning are regression-tested. The historical signing credential was rotated in production and staging with `ENCRYPTION_KEY` preserved, then dispositioned only by its exact historical fingerprint. | Keep the history scanner self-test and exact-fingerprint dispositions intact; rotate any future leaked credential before dispositioning it. |
| Phase 7 — RLS / CI structural safeguards | **PASS** | Runtime tenant-model parity is mechanically checked; missing `subscription_payments` RLS was fixed by forward migration; restricted-role read/write tests and pooled-session concurrency gate are permanent. | Keep runtime tenant tables mechanically aligned with the canonical RLS contract. |
| Phase 8 — documentation truth normalization | **PASS** | Canonical workflow, deployment, source-map, classification, and this status document are normalized to current executable truth. | Historical documents remain historical; do not mass-rewrite them to look current. |
| Phase 9 — final staging / production promotion | **BLOCKED** | Staging has extensive green CI/security evidence and the release governance path is documented. | Configure and verify GitHub platform branch protection/rulesets, then reconcile the diverged `main`/`staging` histories through the documented release path and run final release evidence. |

## Security evidence now enforced

The normalized staging line includes executable coverage for the following security boundaries:

- server-side logout revokes active access/refresh sessions rather than only clearing browser cookies;
- password-reset tokens are single-use/expiry checked and reset revokes existing sessions;
- prior reset-token invalidation is committed before a new Firebase/SMTP reset path is delivered;
- local upload paths use resolved component-aware containment and reject parent, sibling-prefix and symlink escapes;
- authenticated file serving requires a persisted attachment and tenant/patient visibility;
- Tenant-A authentication cannot read/mutate real Tenant-B IDs across sensitive patient, appointment, treatment, payment, file and user/doctor HTTP routes covered by the adversarial matrix;
- PostgreSQL `NOBYPASSRLS` tenant isolation is exercised under concurrent pooled `AsyncSessionLocal` reuse, including A → B → A reuse and a no-tenant leakage probe;
- runtime tenant-scoped SQLAlchemy tables are mechanically compared with the canonical PostgreSQL RLS contract;
- full Git history is scanned by a pinned Gitleaks CLI after a mandatory synthetic history-only leak self-test.

Passing these tests is evidence for the covered boundaries, not a claim that all future code is automatically secure.

## Historical secret remediation — completed, pending green gate merge

The history-aware scan identified one historical high-entropy `SECRET_KEY` candidate in ancestry shared by `main` and `staging`.

Remediation evidence established the following without copying secret values into repository history or logs:

1. the production Hugging Face runtime has a separate `ENCRYPTION_KEY`;
2. persisted encryption uses `ENCRYPTION_KEY` directly;
3. patient-search HMAC key derivation prefers `PATIENT_SEARCH_HMAC_KEY`, then `ENCRYPTION_KEY`, before `SECRET_KEY`;
4. production `SECRET_KEY` was rotated while leaving `ENCRYPTION_KEY` unchanged;
5. staging `SECRET_KEY` was also rotated separately while leaving `ENCRYPTION_KEY` unchanged;
6. production health returned HTTP 200 after rotation;
7. the known historical credential is dispositioned only by its exact Gitleaks fingerprint, not by a broad rule/path exemption.

This does not erase the historical bytes from Git. The security objective is credential revocation plus precise scanner disposition, avoiding a destructive shared-history rewrite. The history-secret workflow must remain self-testing and must fail on any new untriaged finding.

## RELEASE BLOCKER — GitHub platform branch protection is absent

A dedicated Phase 9 precondition gate queried GitHub's branch metadata and applicable branch rules for both `main` and `staging`. GitHub reported:

- `protected=false` for `main`;
- `protected=false` for `staging`;
- no applicable pull-request rule;
- no required-status-checks rule;
- no non-fast-forward/force-push prevention rule;
- no branch-deletion prevention rule.

This is now a confirmed platform-state gap, not an API visibility uncertainty. Repository workflow code validates allowed PR paths, but workflow code cannot prevent a direct push or force push by itself.

Before production promotion, configure GitHub Rulesets or branch protection for both `main` and `staging` so the intended controls are actually enforced. The executable verification gate in PR #57 should pass before promotion.

## RELEASE CONDITION — main/staging history must be reconciled safely

`main` and `staging` are currently diverged rather than a clean fast-forward relationship. Ahead/behind counts are intentionally not frozen here because they are dynamic.

At release time:

1. compare current `main` and `staging` again;
2. if a normal `staging -> main` PR is clean, use it;
3. if historical divergence/conflicts remain, create a documented `release/*` branch from current `main` and reconcile only the validated staging release content;
4. preserve main-authoritative `.github/workflows/cd.yml` unless an intentional CD change is independently in scope;
5. never force-merge or rewrite shared branch history simply to make promotion convenient;
6. run the complete main-targeted CI suite on the exact release revision before merge.

## Phase 9 is not authorized yet

Do not promote the normalization release to production until platform branch enforcement is configured and verified and the final staging/release revision has fresh green evidence. Required final evidence includes, at minimum:

- backend tests + coverage;
- Bandit and dependency security checks;
- frozen dependency reproducibility;
- PostgreSQL migration/preflight and RLS gates, including concurrency;
- frontend lint/build/unit tests;
- Playwright critical path + visual regression;
- responsive/mobile web acceptance;
- stale-deployment recovery gate;
- production container build;
- history-aware secret scan;
- staging deployment health/application smoke;
- verified platform branch/ruleset enforcement.

After a production merge/deployment, verify the production backend health endpoint and representative public UI/API flows before declaring the overall normalization plan complete.
