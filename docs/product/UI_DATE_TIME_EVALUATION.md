# Dentix Plan 02 — Date/Time Component Evaluation

Status: **DECISION RECORDED — retain current implementation for this foundation pass**  
Date: 2026-08-18

## Scope

Plan 02 required a correctness/accessibility audit of the shared `DateTimePicker`, explicit regression coverage for the transparent-popup bug class, and an evidence-based evaluation of React Aria / `@internationalized/date`.

## Existing semantics that must not change

The current shared component intentionally exposes different value semantics by mode:

- `date` → `yyyy-MM-dd`
- `month` → `yyyy-MM`
- `datetime` → ISO datetime string via `Date#toISOString()`

These values flow into existing appointment, finance and other feature contracts. A component-library migration is therefore not a purely visual dependency swap.

## Regression evidence

`frontend/src/shared/ui/DateTimePicker.test.jsx` reproduces the popup-surface defect class and asserts an explicit opaque popup content surface. The broader Plan 02 Playwright suite also verifies an opaque canonical dialog surface in a real Chromium session while exercising RTL/reduced-motion interaction behavior.

## React Aria / @internationalized/date decision

**Do not migrate in Plan 02.**

Reasons:

1. Current value semantics are already embedded in product workflows and need deliberate contract-by-contract migration if ever changed.
2. The existing implementation uses installed Headless UI/date-fns infrastructure; introducing another date stack would increase bundle/runtime/dependency surface.
3. The high-risk transparency regression is already fixed/covered without a dependency migration.
4. Plan 02 explicitly forbids fashionable dependency migration without evidence of reduced complexity, better correctness/accessibility and stable runtime impact.
5. No evidence collected in this pass demonstrated that a full migration would reduce risk more than it would introduce.

This is not a permanent rejection. A future migration can be proposed only with a mode-by-mode compatibility matrix, keyboard/RTL evidence, payload snapshots, timezone tests and bundle/runtime comparison.

## Current known debt

The date picker still contains historical Headless UI/internal layer styling, including legacy high z-index usage. It remains behind the `DateTimePicker` / `DentixDatePicker` shared-UI boundary and is covered by the no-new-debt guardrail strategy. Migrating its internals is a staged cleanup, not authorization to change date/time business semantics.

## Result

Phase 6 is **DONE** for Plan 02: semantics audited, transparent-popup regression locked, dependency migration evaluated on evidence, and product behavior preserved.
