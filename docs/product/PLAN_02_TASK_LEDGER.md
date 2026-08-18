# DENTIX Plan 02 — Execution Ledger

Plan: **DENTIX PLAN 02 — DESIGN SYSTEM V2 + UI REGRESSION FOUNDATION**  
Branch: `refactor/plan-02-design-system-ui-regression`  
Base: `staging` at `da83541cc3a320db92cc428dbb0d9815cf229534`  
Started: 2026-08-18

## Phase status

| Phase | Status | Evidence / gate |
|---|---|---|
| A. Preconditions | DONE | Plan 01 stable; governance, truth, Tailwind/CSS, shared UI, Playwright/E2E and CI inspected. `DENTIX_UI_PRINCIPLES.md` was absent at baseline. |
| 1. UI Forensic Inventory | DONE | `docs/product/UI_FORENSIC_INVENTORY.md`. |
| 2. Visual Direction Audit | DONE | `docs/product/UI_VISUAL_DIRECTION_AUDIT.md`. |
| 3. UI Principles | DONE | Root `DENTIX_UI_PRINCIPLES.md` contains the required 17 principles. |
| 4. Token Consolidation | NOT_STARTED | Code + verification required. |
| 5. Overlay Architecture | NOT_STARTED | Canonical portal/focus/scroll/nesting contract required. |
| 6. Date/Time | NOT_STARTED | Transparent-popup regression must precede risky refactor. |
| 7. Modal Reduction Audit | NOT_STARTED | Classification required; no silent route/semantic change. |
| 8. Form System Contract | NOT_STARTED | Representative forms required. |
| 9. Data Presentation | NOT_STARTED | Table/data contract required. |
| 10. Page Patterns | NOT_STARTED | Required workspace patterns. |
| 11. Visual Regression | IN_PROGRESS | AS-IS baseline must be captured before risky UI changes. |
| 12. Interaction Regression | NOT_STARTED | Keyboard/focus/scroll/nesting/mobile/RTL/reduced motion. |
| 13. Guardrails | NOT_STARTED | Detect → report → migrate → warn new → enforce. |

## Baseline invariants

- Executable code/config/tests outrank prose.
- No new product capability, silent API/schema/business-rule changes, or mass rewrite.
- Current UI mixes hand-rolled overlays, Headless UI, Radix Tooltip, React Hot Toast, FullCalendar and TanStack Table.
- `frontend/src/index.css` uses translucent surfaces and the old `frontend/DESIGN.md` explicitly endorses glassmorphism.
- `frontend/playwright.config.ts` is the CI-referenced config; the divergent `.js` config is legacy until proven otherwise.
- Existing API calls, date payload formats, treatment/payment behavior and navigation semantics remain unchanged unless separately approved.

## Completion rule

Plan 02 remains `IN_PROGRESS` until every mandatory acceptance criterion in the source plan is evidenced in repository code/tests/CI. Green build alone does not prove visual, RTL, keyboard, focus-return, mobile or screenshot correctness.