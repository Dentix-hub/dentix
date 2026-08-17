# Phase 3 — Payments V2

## Execution status

`VERIFIED`

## Hard prerequisite

Phases 0 and 1 VERIFIED; Overview may be complete first per the recommended vertical-slice rollout.

## Source-of-truth sections in MASTER_SPEC.md

- §12 Payments
- §20 Data Table
- §21 Filters
- §23 Permissions
- §26 UI states
- §29.3 Payments endpoint
- §35 Financial Safety
- §36 tests
- §38 Phase 3

## Phase objective

Execute only the approved work for **Payments V2**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- [x] Paginated/filtered payments client contract
- [x] Desktop + mobile Payments UI
- [x] Payment detail interaction
- [x] Payments tests

## Tasks

## FIN-PAY-001 — Expose server pagination in API client

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Payments use backend pagination rather than downloading all history and paginating in memory.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-PAY-002 — Add server filters required by UX

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Supported filters cover actual persisted semantics such as patient/search, date range, doctor where valid, and optional amount range.
- [x] AC2: No payment-method or payment-status filter is fabricated without persisted model support.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-PAY-003 — Build search/date filter behavior

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Search/date changes update the query and meaningful filter state is reproducible via URL/back navigation.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-PAY-004 — Build desktop table

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Columns communicate patient, amount, date/time, doctor/record owner where semantically correct, notes preview, and actions.
- [x] AC2: Amount alignment and accessibility follow shared table rules.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-PAY-005 — Build mobile payment rows

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Mobile uses semantic rows/cards rather than a seven-column sideways table.
- [x] AC2: Core identity, amount, date, and action remain readable.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-PAY-006 — Build detail drawer

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Short payment detail opens in a contextual drawer/sheet/page appropriate to viewport.
- [x] AC2: Detail may show patient, timestamp, association, notes, audit metadata when available, and allowed actions.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-PAY-007 — Apply FINANCIAL_WRITE actions conditionally

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Create/delete actions are unavailable to users without permission and backend rules remain authoritative.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-PAY-008 — Add audit metadata if available

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Existing audit metadata is surfaced only when the backend already provides it; it is not invented.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-PAY-009 — Add route/query tests

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Tests cover pagination/filter URL behavior, permissions, empty results, large results, and relevant date handling.

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

Payments page scales without loading all history and preserves permission-safe operational workflows.

If the exit criteria cannot be proven, do not declare the phase complete.
