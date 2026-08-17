# Phase 8 — Financial Activity

## Execution status

`NOT_STARTED`

## Hard prerequisite

Phases 0 and 1 VERIFIED; source event contracts must be stable.

## Source-of-truth sections in MASTER_SPEC.md

- §17 Activity
- §29.6 Activity endpoint
- §20/21 shared patterns
- §23 Permissions
- §36 tests
- §38 Phase 8

## Phase objective

Execute only the approved work for **Financial Activity**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- Normalized activity contract
- Paginated activity source/endpoint
- Desktop + mobile Activity UI
- Activity filter/permission tests

## Tasks

## FIN-ACT-001 — Define normalized event contract

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Activity is explicitly defined as a normalized read-only financial event timeline, not a legally complete accounting ledger.
- [ ] AC2: Event schema includes source/type, occurred time, direction, amount/currency, subject, and source reference as supported.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-ACT-002 — Prefer server activity endpoint

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Server-side normalization is used when needed for correct cross-source chronology and scalable pagination.
- [ ] AC2: Frontend normalization is accepted only if small-dataset constraints do not mislead chronology.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-ACT-003 — Implement event pagination

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Activity does not require loading all source histories into the browser.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-ACT-004 — Build source/type filters

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Filters include date range, type/source, search and user/doctor only where useful and permission-safe.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-ACT-005 — Build desktop timeline/table hybrid

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Desktop view clearly communicates inflow/outflow, type/source, subject, and timestamp without relying on color alone.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-ACT-006 — Build mobile activity feed

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Mobile retains the same semantic information in a readable feed without horizontal table dependency.

### Required evidence before VERIFIED
- [ ] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [ ] Applicable automated test/check recorded with result.
- [ ] Applicable permission/tenant behavior verified.
- [ ] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [ ] No unrelated regression introduced.

---

## FIN-ACT-007 — Link events to source records

**Status:** `NOT_STARTED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [ ] AC1: Where a source record is navigable, user can drill into it without Activity pretending to own the underlying business record.

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

User can answer “what happened financially?” without visiting four pages, while Activity remains clearly a normalized operational timeline.

If the exit criteria cannot be proven, do not declare the phase complete.
