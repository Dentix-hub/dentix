# Phase 6 — Doctor Compensation V2

## Execution status

`NOT_STARTED`

## Hard prerequisite

Phase 0 VERIFIED (doctor compensation contract specifically); Phase 1 VERIFIED.

## Source-of-truth sections in MASTER_SPEC.md

- §4.6–4.7 doctor calculation/loading diagnosis
- §15 Compensation — Doctors
- §22 Route vs Drawer
- §23 Permissions
- §29.7 Doctor endpoint
- §30 Doctor due
- §36 tests
- §38 Phase 6

## Phase objective

Execute only the approved work for **Doctor Compensation V2**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- Single backend compensation contract + tests
- Doctors finance list
- Routed doctor detail
- Settings drawer
- No duplicate authoritative calculation/fetch

## Tasks

## FIN-DOC-001 — Establish single compensation calculation service

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Backend is the single authoritative source for doctor entitlement calculations.
- [ ] AC2: Frontend does not independently own a competing formula.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-DOC-002 — Return explicit breakdown fields

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Backend exposes the approved breakdown fields needed to explain entitlement, such as production/collected/discount/lab/commission base/rate/amount/fixed component/total due where applicable.
- [ ] AC2: Only fields that match actual server logic are shown.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-DOC-003 — Add regression tests for all rule variants

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Tests cover supported fixed/percentage/mixed rule variants and relevant edge cases.
- [ ] AC2: List/detail/report cannot silently diverge.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-DOC-004 — Build doctors finance list

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Each row/card prioritizes doctor, production/revenue, collected, lab cost, and calculated doctor due.
- [ ] AC2: Compensation rule summary is shown only when configured and permitted.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-DOC-005 — Replace giant details modal with routed page

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Doctor finance detail is reachable via `/finance/compensation/doctors/:doctorId` or equivalent routed path.
- [ ] AC2: Refresh/back/deep-link behavior works; long analysis is not trapped in a giant modal.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-DOC-006 — Build compensation equation/breakdown

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Readable breakdown explains how backend-defined entitlement was derived.
- [ ] AC2: It does not invent paid/remaining/last settlement semantics without a settlement model.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-DOC-007 — Build treatment/case detail table

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Cases/treatments support relevant filtering/drill-down while preserving backend calculation authority.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-DOC-008 — Build permission-gated settings drawer

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Manage compensation is available only with SYSTEM_CONFIG and opens a focused contextual form.
- [ ] AC2: Backend permission checks remain mandatory.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-DOC-009 — Remove duplicate detail request

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Doctor detail query has one ownership model; cached list data may seed UI but duplicate network fetch patterns are removed.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-DOC-010 — Remove authoritative frontend calculation duplication

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Any frontend code that recomputes authoritative doctor due is removed/reduced to display-only helpers.

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

Doctor list and detail always display the same backend-defined entitlement, with explainable breakdown and no fabricated settlement state.

If the exit criteria cannot be proven, do not declare the phase complete.
