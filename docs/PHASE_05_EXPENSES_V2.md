# Phase 5 — Expenses V2

## Execution status

`VERIFIED`

## Hard prerequisite

Phases 0 and 1 VERIFIED.

## Source-of-truth sections in MASTER_SPEC.md

- §13 Expenses
- §20/21 shared table/filter rules
- §23 Permissions
- §29.4 Expenses endpoint
- §35 Financial Safety
- §28.2 Targeted invalidation
- §36 tests
- §38 Phase 5

## Phase objective

Execute only the approved work for **Expenses V2**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- [x] Normalized expense semantics
- [x] Paginated/filtered Expenses UI
- [x] Add/delete interactions
- [x] Targeted invalidation + regression tests

## Tasks

## FIN-EXP-001 — Normalize expense source behavior

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Every expense-like record exposes enough provenance to distinguish its source and allowed actions.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-EXP-002 — Separate manual/lab provenance

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Manual and lab-originated costs are visibly distinguishable.
- [x] AC2: Lab-originated rows do not expose invalid edit/delete behavior if their source workflow is read-only here.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-EXP-003 — Define aggregation to prevent lab double-counting

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Expense totals have an explicit inclusion contract for manual expenses, lab, payroll, and other movements.
- [x] AC2: Automated tests protect against double-counting lab costs.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-EXP-004 — Add server pagination/filtering

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Expense lists scale using server pagination/filtering where needed.
- [x] AC2: Filters use real categories/source values rather than hardcoded unsupported assumptions.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-EXP-005 — Build expense table/list

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Desktop communicates description, source, category, date, amount, and actions.
- [x] AC2: Mobile representation remains semantic and readable.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-EXP-006 — Build Add Expense drawer

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Desktop uses contextual drawer; mobile uses sheet/full-screen form as needed.
- [x] AC2: Fields follow current model: item/description, cost, category, date, notes.
- [x] AC3: Required/numeric states are clear; duplicate submission is prevented; success uses contextual confirmation.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-EXP-007 — Build specific delete confirmation

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Confirmation identifies the record and amount and explains financial impact rather than using generic “Are you sure?”.
- [x] AC2: Destructive action is permission-gated.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-EXP-008 — Use targeted React Query invalidation

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Expense mutation invalidates relevant expenses plus affected overview/activity data only.
- [x] AC2: Unrelated doctor/payment/staff data is not broadly refetched.

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

Expense operations no longer trigger broad Finance reloads and source provenance prevents misleading totals/actions.

If the exit criteria cannot be proven, do not declare the phase complete.
