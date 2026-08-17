# Phase 1 — New Finance Foundation

## Execution status

`VERIFIED`

## Hard prerequisite

Phase 0 VERIFIED.

## Source-of-truth sections in MASTER_SPEC.md

- §7 Proposed Information Architecture
- §8 Route Architecture
- §9 Global Finance Shell
- §19 Visual Design Direction
- §20 Data Table Design System
- §21 Filters and Search
- §22 Routes/Drawers/Sheets
- §23 Permissions
- §24 RTL/i18n
- §25 Accessibility
- §26 UI states
- §27 Frontend Architecture
- §28 React Query Strategy
- §32 Responsive Design
- §33 Terminology
- §38 Phase 1

## Phase objective

Execute only the approved work for **New Finance Foundation**. Inspect the actual repository before changing code and adapt filenames/structure to the repository without changing the product semantics in the master specification.

## Deliverables

- [x] Finance route shell + legacy redirect
- [x] Shared navigation/date/money/scope/metric/filter/table primitives
- [x] Finance query keys
- [x] Permission helper
- [x] RTL/LTR foundation tests

## Tasks

## FIN-FND-001 — Create `/finance` route shell

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Finance has a lightweight routed layout rather than another monolithic Billing controller.
- [x] AC2: The shell does not eagerly load hidden Finance route datasets.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-002 — Preserve `/billing` redirect

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Legacy `/billing` resolves safely to `/finance/overview`.
- [x] AC2: Saved links are not broken during migration.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-003 — Create feature folder architecture

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Finance implementation is organized into page-specific feature modules consistent with the approved architecture or an equivalent structure adapted to the actual repository.
- [x] AC2: Do not restructure unrelated product areas.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-004 — Build Finance navigation

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Navigation exposes Overview, Patient Accounts, Payments, Expenses, Compensation, Activity, and Reports.
- [x] AC2: Mobile uses module-level semantic tabs/selector rather than competing with the global bottom navigation.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-005 — Build shared date range control

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Presets include Today, Yesterday, This week, This month, Last month, Custom.
- [x] AC2: Meaningful period state persists in URL parameters.
- [x] AC3: All-time/current balances are not falsely implied to follow the period selector.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-006 — Build `Money`/currency formatter

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Money formatting is centralized using `Intl.NumberFormat` or the project equivalent.
- [x] AC2: Components do not hand-build amount + currency strings independently.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-007 — Build scope badge

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Metric scope is visible wherever a user could confuse period data with current/all-time values.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-008 — Build shared metric component

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Shared metric presentation supports label, amount, scope/context, and optional comparison/drill-down without forcing decorative KPI cards.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-009 — Build shared filter bar

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Frequent filters remain visible; secondary filters may use progressive disclosure.
- [x] AC2: Active hidden filters remain visible via chips/indicators.
- [x] AC3: Meaningful filter state can be represented in the URL.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-010 — Build reusable data table pattern

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Pattern supports applicable sorting, server pagination, loading, empty/error states, row actions, keyboard operation, amount alignment, and mobile semantic replacement.
- [x] AC2: Mobile is not implemented as a generic horizontally scrolling desktop table.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-011 — Implement query-key factory

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Finance query keys distinguish overview, receivables, payments, expenses, doctors, doctor detail, payroll, and activity by relevant filters.
- [x] AC2: Mutation invalidation can target only affected datasets.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-012 — Implement permission helper

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: UI permission decisions mirror FINANCIAL_READ, FINANCIAL_WRITE, SYSTEM_CONFIG and existing role visibility semantics.
- [x] AC2: Frontend gating is not treated as a replacement for backend security.

### Required evidence before VERIFIED
- [x] Exact implementation files/symbols/endpoints recorded in `IMPLEMENTATION_LEDGER.md`.
- [x] Applicable automated test/check recorded with result.
- [x] Applicable permission/tenant behavior verified.
- [x] Applicable desktop/mobile/RTL/accessibility behavior verified.
- [x] No unrelated regression introduced.

---

## FIN-FND-013 — Add Arabic/RTL visual tests

**Status:** `VERIFIED`  
**Depends on:** phase prerequisites plus any earlier task whose output this task consumes.

### Acceptance criteria
- [x] AC1: Navigation order, table order, drawer anchoring, pagination arrows, directional icons, mixed Arabic/Latin content, and key finance primitives are checked in RTL.
- [x] AC2: English LTR remains correct.

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

Empty Finance shell is production-grade and route-safe, with shared primitives ready for vertical-slice implementation.

If the exit criteria cannot be proven, do not declare the phase complete.
