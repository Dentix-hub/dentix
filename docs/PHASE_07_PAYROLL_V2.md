# Phase 7 — Payroll V2

## Execution status

`NOT_STARTED`

## Hard prerequisite

Phases 0 and 1 VERIFIED.

## Source-of-truth sections in MASTER_SPEC.md

- §14 Compensation structure
- §16 Payroll
- §23 Permissions
- §35 Safety
- §36 tests
- §38 Phase 7

## Phase objective

Execute only the approved work for **Payroll V2**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- Payroll page + month control
- Payroll rows/statuses
- Salary payment interaction
- Compensation config action
- Payroll role/date tests

## Tasks

## FIN-PRL-001 — Merge Staff compensation conceptually with Salary workflow

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Doctors and employee payroll remain distinct specialist workflows under Compensation.
- [ ] AC2: Staff payroll is no longer conceptually fragmented across unrelated Finance areas.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-PRL-002 — Build monthly summary

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Month is the primary payroll time control; the generic day-range picker is not forced onto payroll.
- [ ] AC2: Summary shows total payable, paid, remaining, and employee count.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-PRL-003 — Build payroll rows

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Rows show employee, role, base/fixed component, additional calculated component where applicable, payable, paid, remaining, status, and action.
- [ ] AC2: Statuses are Unpaid/Partially paid/Paid and are not communicated by color alone.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-PRL-004 — Build partial/full payment interaction

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Payment drawer/sheet shows employee, month, payable, already paid, remaining, amount, date, notes.
- [ ] AC2: Quick choices may include Pay remaining and Custom amount.
- [ ] AC3: System determines resulting partial/full status where possible.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-PRL-005 — Build compensation configuration action

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Staff salary/per-appointment configuration is contextual rather than a separate top-level staff finance page.
- [ ] AC2: Configuration is permission-gated.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-PRL-006 — Remove Salaries from Expenses sub-tab

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Payroll no longer lives as a child of Expenses in the new information architecture.
- [ ] AC2: Legacy behavior is preserved until migration is verified.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-PRL-007 — Add role and month-boundary tests

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Tests cover salary partial payments, permission scenarios, date/month boundaries, and tenant isolation where applicable.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

# Phase verification gate

Before this phase can be marked VERIFIED:

- [ ] Every task ID in this file is `VERIFIED` in `IMPLEMENTATION_LEDGER.md`.
- [ ] No task in this phase is `PARTIAL`, `BLOCKED`, `IN_PROGRESS`, or `NOT_STARTED`.
- [ ] Relevant automated tests/checks pass.
- [ ] Relevant permission and tenant-isolation scenarios pass.
- [ ] Relevant responsive/RTL/accessibility checks pass.
- [ ] Final git diff has been inspected for unrelated changes and regressions.
- [ ] `CURRENT_STATE.md` is updated.

## Exit criteria

All employee pay operations live in one coherent monthly workspace with correct partial/full payment semantics.

If the exit criteria cannot be proven, do not declare the phase complete.
