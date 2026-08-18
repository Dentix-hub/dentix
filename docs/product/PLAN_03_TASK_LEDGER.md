# DENTIX PLAN 03 — Task Ledger

**Plan:** EXISTING PRODUCT FORENSIC IMPROVEMENT  
**Branch:** `refactor/plan-03-existing-product-forensic-improvement`  
**Base:** `staging`  
**Execution start:** 2026-08-18  
**Status:** COMPLETE — merge candidate; final GitHub Actions gate required before merge

## Scope guardrails

- Improve existing Dentix capability only.
- No net-new product features.
- Preserve API contracts, database schema, business rules, auth, RBAC, tenant isolation, and financial semantics unless a proven defect requires a compatible correction.
- Evidence before fix; regression before closeout.
- P0/P1 correctness/security outrank polish.

## Preconditions

| Precondition | Status | Evidence / note |
|---|---|---|
| `AGENTS.md` | DONE | Reviewed. |
| `PROJECT_STANDARDS.md` | DONE | Reviewed. |
| `PROJECT_TRUTH.md` | DONE | Reviewed; executable code/tests remain authoritative. |
| `CURRENT_PRODUCT_CAPABILITIES.md` | DONE | Existing-feature boundary established. |
| `MODULE_REGISTRY.md` | DONE | Current module ownership/routes established. |
| `MODULE_AUDIT_TEMPLATE.md` | DONE | Audit output contract established. |
| Plan 02 foundation | DONE | Canonical overlays/tokens/guardrails/visual regression available on `staging`. |
| `DENTIX_UI_PRINCIPLES.md` | GAP | File is absent; current executable shared UI/tokens + Plan 02 contracts remain authoritative. |
| External environment caveats | DONE | Vercel preview build-rate limiting tracked separately from product defects. |

## Program ledger

| Phase / module | Audit | Behavior contract | Implementation | Regression / evidence | Status |
|---|---|---|---|---|---|
| Global rapid scoring pass | DONE | N/A | `CURRENT_PRODUCT_QUALITY_SCORECARD.md` | N/A | DONE |
| Patients | DONE | DONE | Audit-only; no new P0/P1 | Existing patient/visibility regression + final suite | DONE |
| Appointments | DONE | DONE | Missing update/status/delete correctness fixes | Focused router tests + full suite | DONE |
| Clinical / Dental | DONE | DONE | Stock reversal correctness + canonical treatment/session dialogs | Focused backend/frontend tests + full suite | DONE |
| Finance / Billing / Expenses | DONE | DONE | Tenant guard; payment/expense false-success/audit fixes | New finance regressions + final suite | DONE |
| Dashboard / Analytics | DONE | DONE | Profitability tenant attribution + global metrics exposure fix | Metrics boundary tests + full suite | DONE |
| Labs | DONE | DONE | Exact lab-order treatment linkage + atomic synchronization | Linkage regression + full suite | DONE |
| Inventory | DONE | DONE | Tenant/ID ownership boundary hardening | Inventory tenant-boundary + stock tests + full suite | DONE |
| Users / RBAC | DONE | DONE | Tenant-admin privilege-escalation hardening | User admin boundary tests + full suite | DONE |
| Settings | DONE | DONE | Global procedure protection, price/provider ownership, signed OAuth state | Settings security tests + full suite | DONE |
| AI | DONE | DONE | Per-tool domain RBAC + per-user agent session isolation | AI RBAC/session regressions + final suite | DONE |
| Super Admin | DONE | DONE | Signed Super Admin Google Drive OAuth state | Shared OAuth-state tests + final suite | DONE |
| Auth / Public / PWA | DONE | DONE | Audit-only on current auth/impersonation/PWA contracts | Existing auth/impersonation/PWA coverage + final suite | DONE |
| Cross-product consistency | DONE | N/A | Removed audited tenant-fallback/false-success classes; AI aligned with domain RBAC | Final suite | DONE |
| `EXISTING_PRODUCT_BASELINE_V1.md` | DONE | N/A | Published | N/A | DONE |
| Final full regression | DONE WHEN MERGE-CANDIDATE CHECKS ARE GREEN | N/A | N/A | GitHub Actions is source of truth | GATE |

## High-severity findings closed

### Clinical / Dental
- P1 repeated-treatment-edit stock reversal accumulation fixed.

### Appointments
- P1 missing update no longer becomes 500.
- P1 status/delete no-op no longer returns success.

### Inventory
- P0 removal of unsafe clinic fallback to tenant `1`.
- P0 cross-tenant ID ownership checks added to stock/session/smart-inventory paths.

### Users / RBAC
- P0 tenant-user privilege escalation into platform `super_admin` closed.
- Manager cannot use tenant-user administration as a privilege-escalation path.

### Labs
- P1 substring LabOrder treatment-link collision fixed.
- P1 partial order/treatment commit behavior replaced by atomic synchronization.

### Dashboard / Analytics
- P0 legacy payment attribution no longer mixes unowned NULL-tenant payments into current-tenant profitability.
- P0 process-global business counters no longer exposed as tenant business metrics.

### Settings / Backup
- P0 global procedures can no longer be mutated/deleted from tenant procedure routes.
- P0 Google Drive OAuth state is signed, short-lived and identity-bound.
- Cross-tenant price-list/provider references are rejected.

### Finance
- P0 smart-cost route no longer falls back to tenant `1`.
- P1 missing payment delete now returns 404 and clears pending audit work.
- P1 missing expense delete is rejected before a false audit commit.

### AI
- P0 `AI_CHAT` can no longer bypass financial/clinical/patient/appointment/system domain permissions.
- P1 agent state now keys by authenticated user, preventing same-tenant cross-user active-patient/session mixing.

### Super Admin
- P1 canonical Super Admin Google Drive route now uses the signed OAuth-state contract introduced by Settings hardening.

## Accepted non-blocking P2/P3 debt

- Patient-detail tooth selector remains a local overlay.
- Appointment icon-control accessibility/state-management polish and legacy Kanban token debt remain.
- Legacy visual patterns remain in some Inventory/Labs/Users/Super-Admin surfaces; broad redesign was intentionally avoided after correctness gates.
- Overlapping `admin_system` / `system_admin` compatibility routes should be consolidated later; earlier canonical route registration remains authoritative for exact duplicate method/path pairs.
- `DENTIX_UI_PRINCIPLES.md` remains missing.

## Merge rule

PR #19 must remain unmerged until its final merge-candidate revision is green for backend tests/coverage, Bandit, Safety, frontend build/tests, critical Playwright, UI visual regression and Design System Guardrails. Once those checks are green and the PR remains mergeable against `staging`, the plan is approved for merge.
