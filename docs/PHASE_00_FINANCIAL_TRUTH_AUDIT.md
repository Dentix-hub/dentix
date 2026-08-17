# Phase 0 — Financial Truth Audit

## Execution status

`VERIFIED`

## Hard prerequisite

None. This phase is a hard prerequisite for all implementation phases.

## Source-of-truth sections in MASTER_SPEC.md

- §4.4–4.10 Current-State Diagnosis
- §23 Permission-Aware UX
- §29.1 P0 — Correctness contract
- §30 Financial Metric Contract
- §36.2–36.3 Backend/API tests
- §38 Phase 0

## Phase objective

Execute only the approved work for **Financial Truth Audit**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- [x] FINANCE_METRIC_CONTRACT.md
- [x] API/consumer map
- [x] Financial calculation map
- [x] Role visibility matrix
- [x] Backend correctness tests

## Tasks

## FIN-TRUTH-001 — Define metric glossary

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Each headline metric has one documented definition and scope.
- [x] AC2: Production/Revenue, Collected, Current outstanding, Expenses, Doctor due, and Net result are explicitly defined.
- [x] AC3: Period-scoped metrics are distinguished from current/all-time balances.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-TRUTH-002 — Map every existing Finance API and consumer

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Existing frontend Finance/accounting client methods are mapped to real backend routes or marked obsolete.
- [x] AC2: No Finance V2 UI is built around a client method that lacks a supporting backend contract.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-TRUTH-003 — Map every payment/expense/salary/lab/doctor calculation

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Each current calculation source and consumer is documented.
- [x] AC2: Duplicate or conflicting authoritative calculation paths are identified before redesign coding.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-TRUTH-004 — Verify outstanding balance scope

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Current outstanding semantics are documented as current/all-time unless the backend explicitly supports another scope.
- [x] AC2: UI guidance cannot present an all-time balance as if it were period-scoped.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-TRUTH-005 — Verify total deductions formula

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: The total-deductions aggregation is reconciled with the net-result calculation.
- [x] AC2: Any difference in inclusion of lab costs or other components is resolved or explicitly documented.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-TRUTH-006 — Verify lab costs are not double-counted

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Manual expenses and lab-originated costs have explicit source semantics.
- [x] AC2: Automated tests cover aggregation paths where lab costs could otherwise be counted twice.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-TRUTH-007 — Compare doctor summary and detail formulas

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Doctor list and detail semantics are compared against the same intended compensation contract.
- [x] AC2: Any frontend-owned authoritative compensation formula is identified for removal/centralization.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-TRUTH-008 — Identify dead accounting API client methods

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Declared frontend methods with no required backend implementation are identified.
- [x] AC2: Dead methods are scheduled for removal only when safe; missing endpoints are not invented unless required by the approved V2 workflow.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-TRUTH-009 — Document role visibility matrix

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: FINANCIAL_READ, FINANCIAL_WRITE, SYSTEM_CONFIG, doctor self-scope, receptionist restrictions, and tenant isolation are mapped.
- [x] AC2: New aggregate endpoints are required to preserve existing visibility rules.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-TRUTH-010 — Add missing backend tests for financial formulas

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Tests cover doctor compensation edge cases, lab inclusion/exclusion, expense totals, salary partial payments, outstanding semantics, date boundaries, tenant isolation, and role visibility where applicable.
- [x] AC2: Relevant test suite passes before Phase 0 is VERIFIED.

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

Every displayed Finance KPI has a documented source and formula. `FINANCE_METRIC_CONTRACT.md` exists and relevant financial correctness tests pass.

If the exit criteria cannot be proven, do not declare the phase complete.
