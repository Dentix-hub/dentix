# DENTIX PLAN 03 — Task Ledger

**Plan:** EXISTING PRODUCT FORENSIC IMPROVEMENT  
**Branch:** `refactor/plan-03-existing-product-forensic-improvement`  
**Base:** `staging`  
**Execution start:** 2026-08-18  
**Status:** IN PROGRESS

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
| Capture external environment caveats | DONE | `Vercel – dentix-staging` currently reports build-rate-limit failure; `Vercel – smartclinic-v2plus` reports success. This is recorded as deployment environment state, not treated as a product-module defect. |

## Program ledger

| Phase / module | Audit | Behavior contract | Proposal | Implementation | Regression | Status |
|---|---|---|---|---|---|---|
| Global rapid scoring pass | IN PROGRESS | N/A | N/A | `CURRENT_PRODUCT_QUALITY_SCORECARD.md` | N/A | IN PROGRESS |
| Patients | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Appointments | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| Clinical / Dental | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
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

## Severity rules

- `P0`: security/data corruption/critical outage.
- `P1`: broken core workflow or severe UX correctness.
- `P2`: important usability/performance/consistency.
- `P3`: polish/technical debt.

P0/P1 always outrank polish.

## Execution notes

1. Plan 02 deliberately left measurable legacy UI debt; Plan 03 migrates it only when a module is under active audit.
2. Recent Patient Workspace V2 and Finance V2 work provide stronger starting baselines than several older modules; the global scorecard may therefore change the default module order.
3. Deployment provider rate limiting is tracked separately and must not be "fixed" by product code changes.
