# DENTIX PLAN 02 — Execution Report

**Plan:** DESIGN SYSTEM V2 + UI REGRESSION FOUNDATION  
**Direction:** Dentix Clinical Workspace  
**Branch:** `refactor/plan-02-design-system-ui-regression`  
**Base:** `staging`  
**Execution date:** 2026-08-18  
**Status:** **DONE — foundation acceptance met; legacy migration remains staged**

## Scope result

Plan 02 established a measurable Dentix design-system and UI-regression foundation without adding product capability or changing API, database schema, routes or business rules.

The implementation deliberately avoided a repository-wide visual rewrite. Existing legacy UI remains supported while canonical primitives, tokens, tests and no-new-debt guardrails provide the migration path required by the source plan.

## Exact shared UI foundation implemented

### New canonical primitives

- `DentixDialog`
- `DentixDrawer`
- `DentixBottomSheet`
- `DentixPopover`
- `DentixMenu` / `DentixMenuItem` / `DentixMenuSeparator`

### Canonical/compatibility exports established

- `DentixConfirmDialog`
- `DentixTooltip`
- `DentixSelect`
- `DentixDatePicker`
- historical `Modal`, `ConfirmDialog`, `Select`, `Tooltip`, `DateTimePicker` remain compatibility paths

### Hardened shared primitives

- `Modal` — canonical Radix-backed blocking behavior
- `ConfirmDialog`
- `Tooltip`
- `Button`
- `Input`
- `Select`
- `DataTable`

### Representative consumer migrated

- `frontend/src/shared/ui/modals/PaymentModal.jsx`
  - raw fullscreen overlay removed;
  - shared `Modal`, `Button`, `Input`, `DateTimePicker` used;
  - existing payment payload behavior preserved and locked by unit test.

## Token implementation

`frontend/src/index.css` and `frontend/tailwind.config.js` now expose semantic roles for:

- light/dark background/surface/elevated/subtle/hover roles;
- primary/secondary/muted text;
- border/input/selected/focus/disabled/backdrop;
- radius control/card/overlay/pill;
- quiet shadow low/medium/high;
- canonical spacing aliases;
- page/section/body/label/caption/numeric/table typography;
- motion fast/standard/emphasized + reduced-motion behavior;
- z layers base/sticky/header/dropdown/popover/drawer/modal/toast/system.

Legacy glass/shadow utilities remain explicitly isolated so migration does not become a blind global change.

## Overlay behavior proven

Unit and Playwright regression coverage proves:

- opaque content surface;
- focus trapping;
- Tab / Shift+Tab containment;
- Enter / Space activation;
- Escape dismissal;
- outside click dismissal;
- trigger focus return;
- preservation/restoration of body scroll state;
- reference-counted nested modal locking;
- logical RTL drawer edge;
- mobile project coverage;
- reduced-motion behavior.

## Date/time result

The transparent-popup bug class is regression-covered. Existing mode semantics are preserved: date `yyyy-MM-dd`, month `yyyy-MM`, datetime ISO. React Aria / `@internationalized/date` was evaluated and intentionally not introduced because no evidence justified the dependency and contract risk in this foundation pass. See `UI_DATE_TIME_EVALUATION.md`.

## Visual regression foundation

Reviewed AS-IS baselines committed:

1. `patients-ar-light-visual-desktop-linux.png`
2. `patients-en-dark-visual-desktop-linux.png`
3. `patients-ar-light-visual-mobile-linux.png`

They live under `frontend/e2e/ui-regression.spec.ts-snapshots/` and are Git LFS assets. E2E CI now checks out LFS content before Playwright comparison. Baselines are not rewritten to hide post-change failures.

Golden Stage 2 baselines remain intentionally deferred until an intentional visual redesign is accepted, exactly as required by the plan.

## Design guardrails

The guardrail scanner currently reports:

- 306 source files scanned;
- 107 existing legacy findings;
- 14 arbitrary z-index findings;
- 41 arbitrary radius findings;
- 2 arbitrary shadow findings;
- 50 raw fullscreen overlay findings;
- 0 raw `createPortal` findings outside shared UI;
- 0 direct external overlay-library imports outside shared UI.

The PR workflow keeps those legacy findings report-only while **failing newly-added guarded violations**. The latest checked PR diff contains **0 new guarded violations**.

## Verification evidence before closeout documentation

Dentix CI run `32117415066` on implementation head `152c2bd1a6539381b37e9acacd0f4cce8b9d1ec7` proved:

- Frontend production build: PASS
- all 25 discovered frontend Vitest files: PASS
- backend pytest + coverage: PASS
- dependency compatibility smoke: PASS
- Bandit: PASS
- Safety: PASS
- Playwright setup: PASS
- production critical path: PASS
- visual regression: PASS
- overlay interaction regression on desktop/mobile visual projects: PASS

The final documentation/assertion commit must pass the same PR gates before merge.

## Known legacy migration backlog

Plan 02 intentionally does not claim zero legacy UI debt. Remaining work includes feature-local raw fullscreen overlays, arbitrary z/radius/shadow values, and historical date-picker internal layering. These are now measurable and prevented from growing.

Other pre-existing CI warnings observed but not caused by Plan 02 include GitHub Actions Node 20 runtime deprecation notices and npm dependency-audit findings. They require separate dependency/CI maintenance rather than being hidden inside a UI refactor.

## Product integrity statement

- New product features added: **0**
- API contract changes: **0**
- database schema changes: **0**
- business-rule changes: **0**
- fallback branches created: **0**
- visual baselines updated to conceal an unintended diff: **0**

## Final assessment

**DONE — DENTIX Plan 02 design-system/UI-regression foundation is implemented.**

The correct next state is incremental consumer migration under the new regression/guardrail system, not a big-bang rewrite.
