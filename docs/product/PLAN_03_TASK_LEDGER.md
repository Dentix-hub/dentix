# DENTIX PLAN 03 — Task Ledger

**Plan:** EXISTING PRODUCT FORENSIC IMPROVEMENT  
**Branch:** `refactor/plan-03-existing-product-forensic-improvement`  
**Base:** `staging`  
**Execution start:** 2026-08-18  
**Status:** PARTIAL — execution checkpoint after two accepted modules

## Scope guardrails

- Improve existing Dentix capability only.
- No net-new product features.
- Preserve API contracts, database schema, business rules, auth, RBAC, tenant isolation, and financial semantics unless an explicitly approved decision says otherwise.
- Work on one large module at a time.
- Evidence before fix; regression before module closeout.
- Do not update visual goldens to conceal accidental differences.

## Preconditions

| Precondition | Status | Evidence / note |
|---|---|---|
| Read `AGENTS.md` | DONE | Repository execution/safety rules reviewed. |
| Read `PROJECT_STANDARDS.md` | DONE | Service-layer, tenant, React Query/Zustand and shared-UI constraints reviewed. |
| Read `PROJECT_TRUTH.md` | DONE | Executable code/tests outrank documentation; unknown conflicts become BLOCKED. |
| Read `CURRENT_PRODUCT_CAPABILITIES.md` | DONE | Existing-feature boundary established. |
| Read `MODULE_REGISTRY.md` | DONE | Current module ownership/routes established. |
| Read `MODULE_AUDIT_TEMPLATE.md` | DONE | Audit output contract established. |
| Confirm Plan 02 design-system/regression foundation | DONE | Plan 02 merged to `staging`; canonical overlays/tokens/guardrails/visual regression are available. |
| Read `DENTIX_UI_PRINCIPLES.md` | GAP | File does not exist on current `staging`. Use current executable tokens/shared UI plus Plan 02 UI contracts as authoritative; `frontend/DESIGN.md` is supporting guidance only where it does not conflict. Do not invent the missing file. |
| Capture external environment caveats | DONE | Vercel comments/statuses currently report free-tier deployment build-rate limiting for both configured preview projects. This is deployment-provider state, not treated as a product-module defect. |

## Program ledger

| Phase / module | Audit | Behavior contract | Proposal | Implementation | Regression | Status |
|---|---|---|---|---|---|---|
| Global rapid scoring pass | DONE | N/A | N/A | `CURRENT_PRODUCT_QUALITY_SCORECARD.md` | N/A | DONE |
| Patients | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Appointments | DONE | DONE | DONE | DONE | PASS | DONE |
| Clinical / Dental | DONE | DONE | DONE | DONE | PASS | DONE |
| Finance / Billing / Expenses | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Dashboard / Analytics | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Labs | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Inventory | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Users / RBAC | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Settings | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| AI | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Super Admin | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Auth / Public / PWA | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Cross-product consistency | PENDING | N/A | PENDING | PENDING | PENDING | PENDING |
| Final full regression | PENDING | N/A | N/A | N/A | PENDING | PENDING |
| `EXISTING_PRODUCT_BASELINE_V1.md` | PENDING | N/A | N/A | PENDING | N/A | PENDING |

## Accepted module results

### Clinical / Dental

- Fixed P1 repeated-treatment-edit stock reversal accumulation without schema/API changes.
- Added direct reversal regressions for first reversal, idempotent no-op and new usage after prior reversal.
- Migrated TreatmentModal and its treatment stock-session child overlay to the canonical Dentix dialog foundation.
- Added consumer regression for treatment payload and `CONFIRM_OPEN_REQUIRED` recovery.
- Regression gate on code revision `b602ce0d1affaca1617f9861443851720c9026e2`: backend tests/coverage, Bandit, Safety, frontend build/tests, production critical Playwright and visual regression all passed.
- Accepted unresolved P2: patient-detail tooth selector remains a local overlay and is intentionally deferred rather than widening the already-accepted clinical change set.

### Appointments

- Fixed P1 update-not-found incorrectly becoming HTTP 500.
- Fixed P1 status mutation returning success when no tenant-visible appointment was changed.
- Fixed P1 delete mutation returning success when no tenant-visible appointment was deleted.
- No-op status/delete paths now rollback the pending audit unit instead of leaving a false successful mutation contract.
- Added focused router regressions for all three cases.
- Regression gate on code revision `968f9728850bccb136bd43dab9ac42b3b90075e8`: backend tests/coverage, Bandit, Safety, frontend build/tests, production critical Playwright and visual regression all passed.
- Accepted unresolved P2/P3: icon-control accessibility/state-management consistency and Kanban visual token debt remain documented; no unsafe mass rewrite was performed.

## Severity rules

- `P0`: security/data corruption/critical outage.
- `P1`: broken core workflow or severe UX correctness.
- `P2`: important usability/performance/consistency.
- `P3`: polish/technical debt.

P0/P1 always outrank polish.

## Execution notes

1. Plan 02 deliberately left measurable legacy UI debt; Plan 03 migrates it only when a module is under active audit.
2. Recent Patient Workspace V2 and Finance V2 work provide stronger starting baselines than several older modules; the global scorecard therefore changed the default module order.
3. Deployment provider rate limiting is tracked separately and must not be "fixed" by product code changes.
4. The Plan 03 PR remains draft. No merge is allowed while the program is PARTIAL.
