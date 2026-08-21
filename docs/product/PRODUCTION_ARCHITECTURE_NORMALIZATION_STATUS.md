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
| Phase 6 — adversarial security forensic audit | **PARTIAL / RELEASE BLOCKED** | File path containment, server-side logout/reset-session invalidation, HTTP BOLA/IDOR substitution, token/reset abuse cases, and tenant boundary behavior are regression-tested; Bandit/Safety gates pass on validated heads. | Resolve the historical `SECRET_KEY` finding safely; do not allowlist it or rotate blindly. See blockers below. |
| Phase 7 — RLS / CI structural safeguards | **PASS** | Runtime tenant-model parity is mechanically checked; missing `subscription_payments` RLS was fixed by forward migration; restricted-role read/write tests and pooled-session concurrency gate are permanent. | Keep runtime tenant tables mechanically aligned with the canonical RLS contract. |
| Phase 8 — documentation truth normalization | **PASS when this closeout is on `staging`** | Canonical workflow, deployment, source-map, classification, and this status document are normalized to current executable truth. | Historical documents remain historical; do not mass-rewrite them to look current. |
| Phase 9 — final staging / production promotion | **BLOCKED** | Staging has extensive green CI/security evidence and the release governance path is documented. | Resolve all release blockers below, re-run complete staging acceptance, then use a clean `staging -> main` PR or the documented `release/*` reconciliation procedure if branches remain diverged. |

## Security evidence now enforced

The normalized staging line includes executable coverage for the following security boundaries:

- server-side logout revokes active access/refresh sessions rather than only clearing browser cookies;
- password-reset tokens are single-use/expiry checked and reset revokes existing sessions;
- prior reset-token invalidation is committed before a new Firebase/SMTP reset path is delivered;
- local upload paths use resolved component-aware containment and reject parent, sibling-prefix and symlink escapes;
- authenticated file serving requires a persisted attachment and tenant/patient visibility;
- Tenant-A authentication cannot read/mutate real Tenant-B IDs across sensitive patient, appointment, treatment, payment, file and user/doctor HTTP routes covered by the adversarial matrix;
- PostgreSQL `NOBYPASSRLS` tenant isolation is exercised under concurrent pooled `AsyncSessionLocal` reuse, including A → B → A reuse and a no-tenant leakage probe;
- runtime tenant-scoped SQLAlchemy tables are mechanically compared with the canonical PostgreSQL RLS contract.

Passing these tests is evidence for the covered boundaries, not a claim that all future code is automatically secure.

## RELEASE BLOCKER 1 — historical secret remediation

A history-aware Gitleaks investigation identified one non-allowlisted historical high-entropy `SECRET_KEY` candidate in a document committed in ancestry shared by both `main` and `staging`.

The finding must be treated as potentially compromised until remediation is proved. It is intentionally **not** converted into a false-positive allowlist.

Safe remediation is blocked on runtime key-topology proof because `backend/utils/patient_search_normalization.py` derives patient phone blind-index HMAC material from the first available value among:

1. `PATIENT_SEARCH_HMAC_KEY`
2. `ENCRYPTION_KEY`
3. `SECRET_KEY`

If production currently falls back to `SECRET_KEY`, blindly rotating that value can invalidate persisted `phone_search_hash` values and break exact-phone lookup. The repository does not prove that production has a dedicated `PATIENT_SEARCH_HMAC_KEY` configured.

Before production promotion:

1. verify the actual staging and production key topology without copying secret values into logs/docs;
2. if patient search depends on `SECRET_KEY`, establish a dedicated stable patient-search HMAC key and plan/recompute persisted blind indexes under controlled migration/maintenance logic;
3. rotate/revoke the exposed signing secret everywhere it may have been used;
4. invalidate existing sessions/tokens as required by the rotation;
5. decide explicitly whether shared Git history must be rewritten, understanding that this is destructive and requires coordinated branch/clone remediation;
6. rerun a full-history secret scan and require zero untriaged findings.

Do **not** satisfy this blocker by allowlisting the candidate or by deleting only the current working-tree document; neither removes the value from shared Git history.

## RELEASE BLOCKER 2 — platform branch protection enforcement is unverified

Repository workflow code validates allowed PR source/target paths, but workflow code cannot by itself prevent a direct push or force push.

During Phase 8 verification, the classic GitHub branch API reported `protected=false` for both `main` and `staging`. The available repository connector could not inspect modern GitHub rulesets, so this evidence does **not** prove that the branches are unprotected; it proves that effective platform enforcement is currently **unverified** from available evidence.

Before production promotion, verify in GitHub settings/rulesets that the intended controls are actually enforced for `main` and `staging`, including PR-only changes, required status checks, no force pushes, and unresolved-review protection according to `GIT_RELEASE_GOVERNANCE.md`.

## RELEASE CONDITION — main/staging history must be reconciled safely

A Phase 8 compare showed `main` and `staging` in a **diverged** state rather than a clean fast-forward relationship. Ahead/behind counts are intentionally not frozen here because they are dynamic.

At release time:

1. compare current `main` and `staging` again;
2. if a normal `staging -> main` PR is clean, use it;
3. if historical divergence/conflicts remain, create a documented `release/*` branch from current `main` and reconcile only the validated staging release content;
4. preserve main-authoritative `.github/workflows/cd.yml` unless an intentional CD change is independently in scope;
5. never force-merge or rewrite shared branch history simply to make promotion convenient;
6. run the complete main-targeted CI suite on the exact release revision before merge.

## Phase 9 is not authorized yet

Do not promote the normalization release to production until both release blockers are resolved and the final staging/release revision has fresh green evidence. Required final evidence includes, at minimum:

- backend tests + coverage;
- Bandit and dependency security checks;
- frozen dependency reproducibility;
- PostgreSQL migration/preflight and RLS gates, including concurrency;
- frontend lint/build/unit tests;
- Playwright critical path + visual regression;
- responsive/mobile web acceptance;
- stale-deployment recovery gate;
- production container build;
- staging deployment health/application smoke;
- verified platform branch/ruleset enforcement;
- clean history-aware secret scan after remediation.

After a production merge/deployment, verify the production backend health endpoint and representative public UI/API flows before declaring the overall normalization plan complete.
