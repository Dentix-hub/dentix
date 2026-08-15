# Phase 10 — Legacy Removal

## Execution status

`NOT_STARTED`

## Hard prerequisite

Phases required for the chosen Finance V2 release are VERIFIED; regression and user acceptance are complete.

## Source-of-truth sections in MASTER_SPEC.md

- §38 Phase 10
- §40 What Not to Do
- §41 Definition of Done
- §42 rollout guidance
- §45 Final Architecture Decision Summary

## Phase objective

Execute only the approved work for **Legacy Removal**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- Clean legacy removal diff
- Compatibility redirect
- Updated docs
- Full regression + user acceptance evidence

## Tasks

## FIN-LEG-001 — Remove old Billing tabs

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Old tabs are removed only after replacement workflows are verified and accepted.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-LEG-002 — Remove old monolithic data-loading code

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Old Billing orchestration no longer loads unrelated Finance datasets.
- [ ] AC2: Finance route-specific query architecture is the active path.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-LEG-003 — Remove unused old modals/components

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Only components proven unused after migration are removed.
- [ ] AC2: No replacement workflow is deleted by accident.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-LEG-004 — Remove dead API client methods

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Methods confirmed dead by Phase 0 reconciliation are removed without breaking consumers.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-LEG-005 — Keep redirect/compatibility route for a defined deprecation period

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Legacy `/billing` compatibility remains for the chosen migration period and points to the new Finance entry.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-LEG-006 — Update documentation

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Architecture, routes, financial metric contract, permission behavior, and migration notes reflect the implemented system.

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

Legacy Billing implementation can be retired without breaking financial writes, patient data, tenant isolation, business rules, or saved links.

If the exit criteria cannot be proven, do not declare the phase complete.
