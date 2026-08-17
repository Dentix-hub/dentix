# Phase 4 — Patient Accounts / Receivables

## Execution status

`VERIFIED`

## Hard prerequisite

Phase 0 VERIFIED; Phase 1 VERIFIED.

## Source-of-truth sections in MASTER_SPEC.md

- §11 Patient Accounts
- §23 Permissions
- §29.5 Receivables endpoint
- §30 Current outstanding
- §32 Responsive
- §36 tests
- §38 Phase 4

## Phase objective

Execute only the approved work for **Patient Accounts / Receivables**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- [x] Patient balance contract
- [x] Receivables endpoint if required
- [x] Patient Accounts desktop/mobile UI
- [x] Patient finance integration + permission tests

## Tasks

## FIN-REC-001 — Define patient balance contract

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Current balance semantics are explicit and consistent with `FINANCE_METRIC_CONTRACT.md`.
- [x] AC2: Sign conventions for receivable vs cash movement are documented and used consistently.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-REC-002 — Build paginated receivables endpoint if missing

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: If no performant endpoint exists, backend provides server-calculated balances with pagination/sorting/filtering.
- [x] AC2: Endpoint respects tenant and financial visibility rules.
- [x] AC3: Do not download every patient and calculate clinic balances in the browser.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-REC-003 — Add patient search/sort

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: User can search patient and sort by highest balance, recent activity, or patient name as supported by the contract.
- [x] AC2: Optional doctor/minimum-balance filters appear only when semantics/data support them.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-REC-004 — Build outstanding summary

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Shows total current patient balance explicitly as current/all-time and count of patients with balance.
- [x] AC2: Does not present weak vanity KPIs as mandatory.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-REC-005 — Build desktop and mobile list

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Desktop prioritizes patient and current balance with last payment/activity and meaningful context.
- [x] AC2: Mobile uses semantic list rows with balance and account action rather than a horizontal table.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-REC-006 — Integrate with existing patient financial history page

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Patient account detail reuses/extends existing patient financial area where feasible instead of creating a duplicate patient-record system.
- [x] AC2: Financial timeline and current balance use consistent semantics.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-REC-007 — Provide contextual Record Payment action only where permitted

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Action appears only when product workflow and FINANCIAL_WRITE/backend rules allow it.

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

Staff can find a debtor and understand current balance in a few interactions without duplicating the patient record system.

If the exit criteria cannot be proven, do not declare the phase complete.
