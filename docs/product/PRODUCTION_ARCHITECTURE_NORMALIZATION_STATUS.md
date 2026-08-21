# Dentix Production Architecture Normalization — Closeout Status

**Closeout date:** 2026-08-22  
**Scope:** final production architecture normalization plan.  
**Rule:** executable runtime/configuration and executable verification outrank this summary if they later diverge.

This document records what the normalization work has proved and what still blocks production promotion. It is not itself a production-promotion authorization.

## Status legend

- **PASS** — implementation and required verification are present on `staging`.
- **PARTIAL / BLOCKED** — verified work exists, but a mandatory unresolved item remains.

## Phase matrix

| Phase | Status | Verified outcome | Remaining action |
|---|---|---|---|
| Phase 0 — deployment inventory / proof of use | **PASS** | Active and retired deployment surfaces are traced in `DEPLOYMENT_ARTIFACT_DISPOSITION.md`. | Re-run consumer tracing before future destructive cleanup. |
| Phase 0B — production migration startup contract | **PASS** | `scripts/deployment/startup.sh` delegates once to `backend.scripts.preflight_migrations`; PostgreSQL fresh/existing/recovery contracts are tested. | Do not introduce a second startup migration authority. |
| Phase 1 — live public frontend surface verification | **PASS** | Public SPA/assets were externally verified on Vercel; `/api/*` routes to the Hugging Face production backend. | Re-verify mutable external bindings before topology changes. |
| Phase 2 — deployment ambiguity cleanup | **PASS** | Obsolete DigitalOcean/manual deploy, Caddy/self-hosted compose, stale backend Dockerfile/Procfile and unused GHCR publication were retired; active dev compose/image preserved. | None for the normalized topology. |
| Phase 3 — Python dependency normalization | **PASS** | `pyproject.toml` + `uv.lock` are canonical; frozen reproducibility is enforced; legacy requirements files were retired. | Keep active consumers on frozen uv resolution. |
| Phase 4 — production container hardening | **PASS** | Root production Docker image uses a multi-stage non-root runtime and CI builds the real image. | Preserve required runtime file/backup dependencies. |
| Phase 5 — stale asset / PWA reproduction | **PASS** | Permanent Version-A → Version-B stale-hash reproduction and browser preload-recovery regression gate exist. | Keep the gate when changing Vite/PWA deployment. |
| Phase 6 — adversarial security forensic audit | **PARTIAL — final secret-scan closeout pending** | File containment, server-side logout/reset invalidation, HTTP BOLA/IDOR substitution, token/reset abuse cases and tenant boundaries are regression-tested. The historical production `SECRET_KEY` was rotated on 2026-08-22 after independent `ENCRYPTION_KEY` presence was verified without exposing values. | Verify/rotate the signing secret in any other runtime where the historical value may still be active (especially staging), then make the full-history secret scan green with an exact documented historical fingerprint disposition. |
| Phase 7 — RLS / CI safeguards | **PASS** | Runtime tenant-model parity, `subscription_payments` RLS, restricted-role read/write tests and pooled-session concurrency are permanent gates. | Keep runtime tenant tables aligned with the canonical RLS contract. |
| Phase 8 — documentation truth normalization | **PASS when this closeout is on `staging`** | Canonical workflow, deployment, source-map, classification and closeout documents are normalized to executable truth. | Keep historical documents historical. |
| Phase 9 — final staging / production promotion | **BLOCKED** | Staging has extensive green CI/security evidence and a documented reconciliation path. | Resolve the remaining secret-scan/runtime verification and platform branch-protection blockers, then run fresh final staging/release acceptance. |

## Security evidence now enforced

The normalized staging line includes executable coverage for:

- server-side logout revocation of active access/refresh sessions;
- password-reset single-use/expiry behavior and session revocation;
- committed invalidation of prior reset tokens before a new reset path is delivered;
- resolved component-aware upload containment, including parent/sibling-prefix/symlink escapes;
- authenticated file serving with persisted attachment and tenant/patient visibility checks;
- Tenant-A tokens substituting real Tenant-B IDs across sensitive patient, appointment, treatment, payment, file and user/doctor routes;
- PostgreSQL `NOBYPASSRLS` isolation under concurrent pooled `AsyncSessionLocal` reuse, including A → B → A and no-tenant leakage probes;
- mechanical parity between runtime tenant-scoped SQLAlchemy tables and the canonical PostgreSQL RLS contract.

Passing these tests is evidence for the covered boundaries, not a claim that all future code is automatically secure.

## Historical secret remediation status

A history-aware Gitleaks investigation found one high-entropy historical `SECRET_KEY` candidate in ancestry shared by `main` and `staging`. Four other findings were individually proved false positives and were fingerprint-allowlisted; the signing-key candidate was not.

### Production rotation completed

On 2026-08-22 the production Hugging Face Space configuration was visually verified to contain **separate** `ENCRYPTION_KEY` and `SECRET_KEY` secrets. No secret values were copied into the repository, logs, or chat. The production `SECRET_KEY` was then replaced by the operator.

This rotation does **not** rotate persisted data encryption:

- `backend/core/security.py` uses `ENCRYPTION_KEY` directly for Fernet encryption/decryption and does not fall back to `SECRET_KEY` in production encryption handling;
- `backend/utils/patient_search_normalization.py` chooses patient-search HMAC material in this order: `PATIENT_SEARCH_HMAC_KEY`, then `ENCRYPTION_KEY`, then `SECRET_KEY`;
- because production has a separate `ENCRYPTION_KEY`, replacing only `SECRET_KEY` does not change existing Fernet ciphertext compatibility or the existing phone-search HMAC key material;
- JWT/session tokens signed with the old signing secret are intentionally invalidated by the rotation.

### Remaining secret work before production promotion

1. verify whether the historical signing secret is still active in the staging Space or any other runtime; rotate it there if necessary, using a value different from production;
2. keep `ENCRYPTION_KEY` unchanged unless an explicit data-key rotation/migration is separately planned;
3. update the history-scan gate so the now-rotated historical credential is disposed by an exact documented fingerprint rather than a broad rule/path allowlist;
4. rerun a full-history scan and require zero **untriaged** findings;
5. do not rewrite shared `main`/`staging` history merely to remove a rotated credential unless a separate coordinated history-rewrite decision is explicitly made.

## Platform branch protection remains a release blocker

Repository workflow code validates allowed PR source/target paths, but workflow code cannot by itself prevent a direct push or force push.

The classic GitHub branch API reports `protected=false` for both `main` and `staging`. During this closeout, a direct commit also appeared on `staging` while a docs PR was open, demonstrating that the current actor is able to advance `staging` outside the PR path. The available connector cannot inspect modern GitHub rulesets, so exact ruleset configuration is not visible here; effective PR-only enforcement must therefore be verified/fixed in GitHub settings before Phase 9.

Required platform controls are documented in `GIT_RELEASE_GOVERNANCE.md`: PR-only changes, required checks, no force pushes, and unresolved-review protection for the permanent branches.

## Main/staging history must be reconciled safely

`main` and `staging` have been observed in a diverged state rather than a clean fast-forward relationship. At release time:

1. compare current `main` and `staging` again;
2. use a normal `staging -> main` PR if it is clean;
3. otherwise create a documented `release/*` branch from current `main` and reconcile only validated staging release content;
4. preserve main-authoritative `.github/workflows/cd.yml` unless an intentional CD change is independently in scope;
5. never force-merge or rewrite shared branch history simply for convenience;
6. run the complete main-targeted CI suite on the exact release revision before merge.

## Phase 9 is not authorized yet

Before production promotion require fresh evidence for backend/coverage/security, frozen dependencies, PostgreSQL preflight/RLS/concurrency, frontend build/tests, Playwright critical path/visual regression, responsive/mobile acceptance, stale-deployment recovery, production container build, staging deployment health, platform branch protection, and a clean history-aware secret scan with no untriaged findings.

After production merge/deployment, verify the production backend health endpoint and representative public UI/API flows before declaring the overall normalization plan complete.
