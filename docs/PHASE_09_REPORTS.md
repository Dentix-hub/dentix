# Phase 9 — Reports

## Execution status

`NOT_STARTED`

## Hard prerequisite

Financial metric contracts and relevant operational source APIs are stable; Phases 0 and 1 VERIFIED.

## Source-of-truth sections in MASTER_SPEC.md

- §18 Reports
- §29 backend contracts as applicable
- §31 performance
- §36 tests
- §38 Phase 9

## Phase objective

Execute only the approved work for **Reports**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- Finance Reports workspace
- Approved initial reports
- Optional export only after semantics stabilize
- Report correctness/permission tests

## Tasks

## FIN-RPT-001 — Move analytical summary views out of operational pages

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Overview remains concise/operational; deeper analytical views live in Reports.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-RPT-002 — Implement financial summary report

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Report has clear title, scope, filters, summary metrics, visualization only when useful, and detailed table.
- [ ] AC2: Metrics reuse approved definitions.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-RPT-003 — Implement collections report

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Collections report uses the approved Collected definition and permission scope.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-RPT-004 — Implement expense category report

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Expense report uses approved expense/source semantics and avoids lab double-counting.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-RPT-005 — Implement provider financial report

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Provider report uses backend-defined production/collection/compensation semantics and visibility rules.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-RPT-006 — Evaluate existing procedure-cost API for profitability report

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Profitability report is implemented only if existing backend cost-analysis data is reliable enough for the claimed metric.
- [ ] AC2: If not reliable, record it as deferred rather than fabricating a number.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-RPT-007 — Add export only after filters/definitions stabilize

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Any CSV/export reflects active filters and permission scope.
- [ ] AC2: Export is not used to compensate for unstable report semantics.

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

Overview remains concise while approved deeper analysis is available and financially consistent.

If the exit criteria cannot be proven, do not declare the phase complete.
