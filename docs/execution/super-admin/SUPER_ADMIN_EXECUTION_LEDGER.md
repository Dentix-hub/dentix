# Super Admin Hardening — Authoritative Execution Ledger

Branch: `chore/super-admin-existing-capabilities-hardening`  
Audited baseline: `46584940df522e681e52fac1ec4bc3b7b206793b`  
Scope rule: repair and harden existing Super Admin capabilities only. No new product modules or features.

## Evidence policy

This file replaces the older duplicated ledger/matrix representation. The previous document contained two conflicting commit maps and a stale `MS-38 Commit: Pending` line even though a release-gate commit existed and was later superseded by additional product-code changes.

The rules below are authoritative:

1. Historical micro-step commits are recorded once, using the commit mapping from the original detailed execution sections.
2. Historical `MS-38` is **SUPERSEDED**, not pending, because product code changed after that gate.
3. A release verdict is valid only for the exact branch HEAD carrying the code being reviewed. GitHub Actions attached to an older HEAD are evidence for that older revision only.
4. The final closeout must include backend coverage/security, frontend tests/build, Playwright critical paths, production-container validation, and the repository protection/security gates on the same HEAD.
5. No merge to `main` or `staging` is performed by this execution ledger.

## Historical micro-step commit map

| Micro-step | Historical commit | Historical state |
| --- | --- | --- |
| MS-00 | `f82a15a0` | PASS |
| MS-01 | `267f6606` | PASS |
| MS-02 | `3a2560e6` | PASS |
| MS-03 | `78dfb72b` | PASS |
| MS-04 | `53486ee5` | PASS |
| MS-05 | `a852abe6` | PASS |
| MS-06 | `80f4acef` | PASS |
| MS-07 | `846f96ea` | PASS |
| MS-08 | `c6ddb868` | PASS |
| MS-09 | `0815d80a` | PASS |
| MS-10 | `b7287dcf` | PASS |
| MS-11 | `f548e938` | PASS |
| MS-12 | `a752f6b3` | PASS |
| MS-13 | `af2763c2` | PASS |
| MS-14 | `3a992e5d` | PASS |
| MS-15 | `cefa575a` | PASS |
| MS-16 | `8196ef25` | PASS |
| MS-17 | `f2423339` | PASS |
| MS-18 | `5534fea1` | PASS |
| MS-19 | `de0543ca` | PASS |
| MS-20 | `ecbc36ae` | PASS |
| MS-21 | `0b7505b2` | PASS |
| MS-22 | `c69631f7` | PASS |
| MS-23 | `c78dbbfb` | PASS |
| MS-24 | `147c89b2` | PASS |
| MS-25 | `42bf12f4` | PASS |
| MS-26 | `9c2cb383` | PASS |
| MS-27 | `2f4ef893` | PASS |
| MS-28 | `1d6c3a32` | PASS |
| MS-29 | `f563da27` | PASS |
| MS-30 | `03af0e38` | PASS |
| MS-31 | `1961e1c6` | PASS, later closeout required |
| MS-32 | `94b98f0f` | PASS, later closeout required |
| MS-33 | `7d2210e9` | PASS |
| MS-34 | `3d78c9c5` | PASS |
| MS-35 | `430cdb92` | PASS |
| MS-36 | `0ede263c` | PASS, later CI regression repaired |
| MS-37 | `b3f1bf5d` | PASS historically; release E2E evidence later corrected |
| MS-38 | `87370980` | **SUPERSEDED BY POST-GATE CHANGES** |

## Post-gate history and corrections

### Post-gate hardening

`03b0bf91` (`fix(admin): close post-gate audit gaps`) added rollout validation, typed feature updates, explicit tenant overrides, audit pagination compatibility, and master regression coverage. Additional design-system cleanup followed, reaching pre-closeout HEAD `5b57fbbb52efbdd9fdd3ba3f8ce77fe03089face`.

Because those changes occurred after historical MS-38, the old MS-38 result cannot be used as final release evidence.

### Backend CI route-uniqueness repair

A later CI failure was traced to two FastAPI handlers registered for the same method/path: `PUT /api/v1/admin/system/profile`. The stale weak `dict` handler was removed while the typed, validated `AdminProfileUpdate` handler was retained.

- `2242dcdf` — remove duplicate Super Admin profile route.
- `234f740b` — preserve unrelated formatting so the net product change remains the route deletion only.
- GitHub Actions on `234f740ba40001284e076d54f42f5125cbfd4597` passed backend coverage/security, frontend tests/build, Playwright E2E, visual regression, production-container validation, and all branch security/governance gates.

That green run proves the route-uniqueness repair, but it does **not** replace the final gate for later closeout changes.

## Final closeout scope

The branch revision containing this ledger performs the remaining evidence-backed closeout work:

- **MS-31 shared primitives:** replace the remaining hand-built FeatureManager overlay with the canonical shared `Modal`; replace the hand-built tenant detail side panel with canonical `DentixDrawer`; keep confirmation/toast flows on shared primitives.
- **MS-32 i18n:** route remaining user-facing Super Admin strings in FeatureManager, SystemPage, TenantDetailPanel, and ImpersonationBar through Arabic/English resources; use locale-aware date formatting in tenant details.
- **Design-system cleanup:** replace remaining arbitrary Super Admin overlay radius/z-index usage in the touched paths with canonical `rounded-overlay` / `z-system` tokens.
- **Feature rollout contract:** align the create-form default/reset value with the backend schema default of `0`, while preserving explicit 0–100 validation.
- **MS-37 release E2E:** correct the dormant Super Admin spec so it authenticates as an actual `super_admin`, and add the real impersonation lifecycle to the CI-executed `critical-path.spec.ts`: start -> read succeeds -> write is rejected with HTTP 403 under `read_only` -> return clears the temporary token and restores the original Super Admin cookie session.
- **Ledger reconciliation:** remove the conflicting duplicate commit matrix and stale `Pending`/`100% DONE` claims.

## Final release gate (current HEAD only)

The canonical release verdict is the GitHub Actions result attached to the **current branch HEAD at the time of review**. Required checks:

- Dentix CI
  - Frozen Dependency Reproducibility
  - Frontend Tests (lint, build, unit tests)
  - Backend Tests + Security (Ruff, migrations, PostgreSQL smoke, coverage, Bandit, Safety)
  - E2E Critical Path (including real Super Admin impersonation lifecycle)
  - UI visual regression
  - Validate Production Container
- Dentix Design System Guardrails
- Dentix Mobile Responsive Gate
- Dentix PostgreSQL RLS Concurrency Gate
- Dentix PostgreSQL HTTP IDOR Gate
- Dentix History Secret Scan
- Dentix Branch Governance / Platform Branch Protection
- Stale Deployment Recovery gate where triggered

A final PASS must never be copied forward to a newer commit. If any code or documentation is committed after a green gate, the newer HEAD must be evaluated again according to repository workflow triggers.

## Merge status

No merge is performed by this closeout. Merge readiness is determined only after all required checks for the exact final HEAD are green.
