# Phase 2 — Overview V2

## Execution status

`VERIFIED`

## Hard prerequisite

Phases 0 and 1 VERIFIED.

## Source-of-truth sections in MASTER_SPEC.md

- §10 Overview specification
- §26 Loading/Empty/Error/Zero states
- §29.2 Overview endpoint
- §31 Performance Targets
- §32 Responsive Design
- §36 tests
- §38 Phase 2

## Phase objective

Execute only the approved work for **Overview V2**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- [x] Overview API contract
- [x] Overview page
- [x] Trend + obligations + activity preview
- [x] Overview integration/permission/responsive tests

## Tasks

## FIN-OVR-001 — Implement/normalize Finance overview API if needed

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Overview gets a purpose-built or normalized backend contract only if current APIs cannot support the approved scalable UX.
- [x] AC2: Endpoint preserves tenant and financial visibility rules.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-002 — Return explicitly scoped metrics

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Response makes the scope of production/collected/expenses/net result explicit.
- [x] AC2: Current/all-time balances are semantically separate from period metrics.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-003 — Return trend series

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Trend data supports the approved primary chart without requiring the frontend to fetch unrelated Finance pages.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-004 — Return current balances with explicit semantics

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Patient outstanding, doctor due, and payroll remaining are named/scoped in a way that does not imply false period semantics.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-005 — Apply tenant and financial visibility rules

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Owner/admin/doctor/receptionist visibility scenarios follow existing backend rules.
- [x] AC2: No aggregate endpoint bypasses provider/tenant isolation.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-006 — Build headline metrics

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Overview shows four primary metrics: Production/Revenue, Collected, Expenses, and the approved Net result label.
- [x] AC2: Production and collections remain visually/semantically distinct.
- [x] AC3: Exact scope is visible.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-007 — Build obligations/receivables section

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Current patient balance, doctor compensation due, and payroll remaining are presented as actionable obligations/receivables rather than decorative duplicate KPI cards.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-008 — Build one primary trend chart

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Initial chart focuses on Collected and Expenses.
- [x] AC2: Tooltips are localized; color is not the only differentiator; RTL and keyboard accessibility are considered; animation does not delay reading.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-009 — Build recent activity preview

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Shows a limited recent set (target 8–12) with source/type and a path to full Activity.
- [x] AC2: Doctor calculated entitlement is not presented as a cash movement.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-010 — Add drill-down links

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Overview metrics/obligations that are actionable route to the relevant operational screen without duplicating the detailed workflow in Overview.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-OVR-011 — Add loading/empty/partial-error states

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Skeletons preserve layout.
- [x] AC2: Valid zero values remain data, not empty states.
- [x] AC3: Failure of one secondary widget does not blank the entire Finance module.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

# Phase verification gate

Before this phase can be marked VERIFIED:

- [x] Every task ID in this file is `VERIFIED` in `IMPLEMENTATION_LEDGER.md`.
- [x] No task in this phase is `PARTIAL`, `BLOCKED`, `IN_PROGRESS`, or `NOT_STARTED`.
- [x] Relevant automated tests/checks pass.
- [x] Relevant permission and tenant-isolation scenarios pass.
- [x] Relevant responsive/RTL/accessibility checks pass.
- [x] Final git diff has been inspected for unrelated changes and regressions.
- [x] `CURRENT_STATE.md` is updated.

## Exit criteria

Owner can understand core financial health without entering another tab, using real backend data and explicit financial semantics.

If the exit criteria cannot be proven, do not declare the phase complete.
