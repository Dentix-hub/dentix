# Dentix UI Forensic Inventory — Plan 02 Phase 1

Baseline: `staging` @ `da83541cc3a320db92cc428dbb0d9815cf229534`  
Audit date: 2026-08-18

## Scope and method

This inventory is descriptive, not a redesign. It covers the complete `frontend/src/shared/ui/` tree plus major duplicate overlay/search/modal implementations found by repository code search. Executable code wins over older design prose.

Classification vocabulary: `KEEP`, `HARDEN`, `MERGE`, `REPLACE`, `DEPRECATE`, `REMOVE_AFTER_PROOF`.

## Shared UI inventory

| Artifact | Implementation / current role | Accessibility + keyboard | RTL / theme / mobile | Tests / defects / duplicates | Classification |
|---|---|---|---|---|---|
| `Button.jsx` | Hand-rolled button; primary/secondary/outline/ghost/danger; loading/icon/sizes | Native button; disabled; no explicit `aria-busy` for loading | Logical icon margin; light/dark classes | Heavy default shadows + active scale/ripple; hard-coded red | HARDEN |
| `IconButton.jsx` | Hand-rolled icon-only button | Native button but accessible name is caller-dependent and not enforced | Mostly physical gray palette | Hard-coded gray; circular-only style | HARDEN |
| `Input.jsx` | Hand-rolled input with generated id and label linkage | Good `htmlFor`; missing automatic `aria-invalid`/error description/help contract | Logical padding; theme tokens | No help/required/read-only/dirty contract | HARDEN |
| `Select.jsx` | Native `<select>` wrapper | Native keyboard/mobile behavior; label is not linked to a generated/select id; error not described | Logical chevron placement; tokenized theme | Separate `PriceListSelector`; Headless `PatientSelect`; Radix Select dependency appears unused | HARDEN |
| `PatientSelect.jsx` | Headless UI Combobox + remote/local patient search | Headless UI supplies combobox keyboard semantics; label is visually separate; error linkage not explicit | `dir="auto"`; opaque options; logical positioning | Own absolute dropdown `z-[100]`; quick-add action embedded; duplicates canonical select/search surface | HARDEN / MERGE INTO COMBOBOX CONTRACT |
| `PriceListSelector.jsx` | Raw native select + self-fetching price-list data | Native keyboard; no label/error contract | Light-only hard-coded white/gray/blue | Duplicates `Select`; combines data loading with presentation | DEPRECATE AFTER CONSUMER MIGRATION |
| `DateTimePicker.jsx` | Headless UI Dialog + date-fns; date/datetime/month modes | Dialog semantics/focus from Headless UI; many calendar nav controls lack explicit accessible labels | Manual Arabic weekday labels; panel dark/light; modal-like on mobile/desktop | Own z-9999/overlay/motion; trigger uses translucent `bg-surface`; 12h minute state can initialize to a value not rendered in 15-minute choices; not shared overlay | REPLACE PRESENTATION THROUGH `DentixDatePicker`, PRESERVE VALUE CONTRACT |
| `Modal.jsx` | Hand-rolled `createPortal(document.body)` modal | Escape + manual Tab loop + autofocus; no trigger focus return; close button no explicit label | Opaque panel; mobile styling but centered overlay; theme aware | `z-[9999]`; scroll cleanup forces `body.style.overflow='auto'`; no nested stack; own focus implementation | REPLACE BEHIND COMPATIBILITY WRAPPER |
| `ConfirmDialog.jsx` | Composes `Modal`; raw action buttons | Inherits modal limitations | Hard-coded Arabic defaults; partial theme via modal | Sync confirm then close; no async/loading/double-submit state; raw semantic colors | HARDEN / MIGRATE TO `DentixConfirmDialog` |
| `Tooltip.jsx` | Radix Tooltip wrapper | Strong Radix keyboard/hover semantics | Theme fixed dark tooltip | Content is not placed in `TooltipPrimitive.Portal`; Provider instantiated per tooltip; own z-50 | HARDEN |
| `ToastProvider.jsx` | React Hot Toast provider | Library-managed live region behavior | `bg-surface` + blur; theme tokens | Transparent glass surface; shadow-2xl; overlaps `Toast.jsx` public API | MERGE |
| `Toast.jsx` | Thin React Hot Toast command wrapper | Library-managed | N/A | Duplicate entry surface with `ToastProvider` export | MERGE |
| `DataTable.jsx` | Simple semantic table | Native table semantics; no sort controls | Hard-coded `text-right`; translucent surface | No loading/pagination/sort/filter; overlaps `AdvancedTable` | MERGE AS SIMPLE TABLE VARIANT |
| `AdvancedTable.jsx` | TanStack Table + Virtual; client sort/filter/pagination | Headers clickable for sort, but clickable rows use `<tr onClick>` without keyboard equivalent; search is raw input | Hard-coded `text-right`; dark/light; responsive only via horizontal scroll | Header/pagination surfaces use translucency/blur; columnVisibility state exists without canonical control; duplicate table system | HARDEN AS DENSE/CAPABLE TABLE BASE |
| `TabGroup.jsx` | Hand-rolled underline/vertical/pill tabs + motion | `tablist`/`tab` + `aria-selected`; lacks roving tabindex, Arrow key handling and panel relationships | Logical placement; theme aware | Motion/shadow per variant; no shared reduced-motion contract | HARDEN |
| `GlobalSearch.jsx` | Patient remote search dropdown in app shell | Clear button labeled; result links keyboard reachable; popup/input lacks combobox/listbox relationship | `dir="auto"` for input/results; dark/light | Hand-rolled outside-click dropdown; z-50; duplicates patient combobox/search overlay behavior | HARDEN / USE POPOVER CONTRACT |
| `CommandPalette.jsx` | Hand-rolled full-screen palette + client filtering/navigation | Escape, arrows, Enter; autofocus; no focus trap/return/body-scroll stack; close icon not explicitly labeled | Uses translations, but own layout/motion | `z-[9999]`, glass surface, blur, radius 2.5rem, shadow-2xl; duplicate modal shell | REPLACE OVERLAY SHELL; KEEP COMMAND BEHAVIOR |
| `Card.jsx` | Generic titled/action card | Neutral container | Theme aware | Forces `bg-surface backdrop-blur-xl`, rounded-2xl; contributes global cardification | HARDEN |
| `StatCard.jsx` | KPI/stat card with color map | Clickable `<div>` when `onClick` exists: no keyboard/button semantics | Theme aware | Decorative corner blob; hover lift/shadow-xl/icon rotation; color names are decorative rather than semantic | HARDEN / SPLIT STATIC VS INTERACTIVE SEMANTICS |
| `PageHeader.jsx` | Page title/subtitle/breadcrumb/actions | Semantic `h1` | Responsive action stack; logical layout | Typography/actions not tied to explicit page pattern contract | KEEP + HARDEN |
| `Breadcrumb.jsx` | React Router links + direction-aware separators | `nav aria-label="breadcrumb"`; current item lacks `aria-current` | Explicit RTL separator handling; theme aware | Uses index keys | HARDEN |
| `Badge.jsx` | Status/tag pill variants | Plain text span; acceptable for status text if caller supplies context | Theme aware | Hard-coded utility palettes rather than semantic token map | HARDEN |
| `Alert.jsx` | Static alert variants | No default `role=alert/status`; icon decorative status not hidden | Light-only variant palette in current classes | Semantic variants exist but colors are hard-coded | HARDEN |
| `EmptyState.jsx` | Animated decorative empty state | Text/action composition | Theme aware | Excessive blur, gradient, huge radii, infinite floating/pulse motion; no reduced-motion contract | HARDEN |
| `LoadingSpinner.jsx` | page/inline/shimmer loaders | No default status/live text | Theme aware | Decorative ping/pulse/shimmer; no reduced-motion contract | HARDEN |
| `Skeleton.jsx` | box/text/card/table/stat skeleton family | Pure visual placeholders | Theme aware | `rounded-${rounded}` dynamic Tailwind class can be omitted by static extraction; hard-coded white surfaces | HARDEN |
| `ErrorBoundary.jsx` | Class error boundary + internal logger | Recovery buttons are native | Default fallback forces RTL/Arabic | Hard-coded gradient, shadow-2xl, raw buttons; fallback navigation uses `/dashboard` while app dashboard route is `/` | HARDEN PRESENTATION; ROUTE ISSUE REQUIRES SEPARATE BEHAVIOR REVIEW |
| `GlobalErrorFallback.jsx` | Root fallback used by App | Native refresh button | English-only copy; theme aware | Raw button; duplicated error presentation with `ErrorBoundary` | MERGE PRESENTATION |
| `BackgroundWrapper.jsx` | Global decorative fixed background blobs | Pointer-events none | dark/light | Large blurred color blobs make glass surfaces visually dependent on background decoration | HARDEN / REDUCE DECORATION |
| `ClinicDateTime.jsx` | Tenant-timezone clock/date display | `<time>` with label/title | `ar-EG` vs `en-GB`; responsive hidden until XL | Uses translucent `bg-background/70`; otherwise direction/timezone logic is strong | KEEP + VISUAL HARDEN |
| `GlobalBanner.jsx` | Fetches public global setting and renders dismissible banner | Close button lacks explicit accessible label | Translation not used for content (server-provided); layout logical | Gradient + bounce + z-50; contains data fetching in UI primitive | HARDEN |
| `SubscriptionBanner.jsx` | Derives subscription warning from tenant/auth state | Action is native button | i18n text; theme mostly white-on-semantic bg | z-50 + pulse + shadow; mixes business derivation and visual primitive | KEEP BEHAVIOR + HARDEN PRESENTATION |
| `NotificationBell.jsx` | Polling notification control + dropdown | Bell labeled; dropdown lacks menu/list semantics and Escape/focus management; notification row click is non-keyboard `<div>` | Current visible copy is Arabic; light palette dominates | Hand-rolled outside-click popup, z-50; raw destructive buttons | HARDEN / USE POPOVER-MENU CONTRACT |
| `WeeklyCalendar.jsx` + CSS | FullCalendar wrapper for scheduling | Delegates much behavior to FullCalendar | Explicit `direction` and locale; fixed 700px height | External calendar surface has separate CSS system and needs representative visual regression, not replacement | KEEP + HARDEN TOKENS |
| `MultiSessionPanel.jsx` | Treatment multi-session editor | Mixed shared Button + raw controls; textarea autofocus | Hard-coded Arabic/date-fns `ar` locale | Uses DateTimePicker; presentation/business editing intertwined | HARDEN WITH FORM CONTRACT |
| `KeyboardShortcutsModal.jsx` | Small informational modal composed from shared Modal | Inherits Modal behavior; semantic `<kbd>` | i18n used | Good candidate for first compatibility migration | MIGRATE TO CANONICAL DIALOG |
| `PaymentModal.jsx` | Small payment form + DateTimePicker | Raw unlabeled controls; hand-rolled modal has no focus trap/return | Arabic-only; light-only inner surface | Own fixed overlay/z-50; duplicates Modal and form primitives | REPLACE SHELL + FORM PRIMITIVES, PRESERVE PAYLOAD |
| `PrescriptionModal.jsx` | Medium/complex prescription editor with saved medication chooser | Raw controls; own modal lacks focus handling; nested saved-list toggle | Arabic-heavy; light-only panel | Own overlay; medium workflow with contextual chooser | REPLACE SHELL; DRAWER/DIALOG DECISION IN PHASE 7 |
| `TreatmentModal.jsx` | Large clinical workflow: treatment state, inventory, material consumption, sessions, nested session modal and mutations | Complexity makes modal keyboard/nesting correctness high risk | Arabic-heavy internal copy + many local styles | ~50 KB component; nested overlays; direct React Hot Toast; complex workflow is not a small modal | REPLACE CONTAINER PATTERN AFTER PHASE-7 DECISION; DO NOT CHANGE BUSINESS LOGIC |
| `index.js` | Shared UI barrel exports public primitives | N/A | N/A | Does not export every shared UI artifact, so public/private boundary is implicit | HARDEN PUBLIC SURFACE |
| `Modal.test.jsx` | Unit coverage for hidden/open/close/backdrop/content/Escape | No focus-return/tab-cycle/scroll restoration/nesting assertions | N/A | Useful baseline but incomplete for canonical overlay | KEEP + EXPAND |
| `StatCard.test.jsx` | Existing StatCard test file | N/A | N/A | Must be retained during visual hardening | KEEP |

## Major duplicate implementations outside the shared primitive contract

Repository search for fixed full-screen overlays found repeated local implementations in, among others:

- `frontend/src/pages/admin/PriceLists.jsx`
- `frontend/src/pages/Labs.jsx`
- `frontend/src/pages/Expenses.jsx`
- `frontend/src/pages/GlobalLabOrdersModal.jsx`
- `frontend/src/pages/UsersManager.jsx`
- `frontend/src/pages/PatientDetails.jsx`
- `frontend/src/pages/admin/TenantsPage.jsx`
- `frontend/src/features/patients/PatientScanner.jsx`
- `frontend/src/features/inventory/components/AddWarehouseModal.jsx`
- `frontend/src/features/inventory/components/WarehouseDetailsModal.jsx`
- `frontend/src/features/inventory/components/TrackSessionModal.jsx`
- `frontend/src/features/inventory/components/SmartLearningModal.jsx`
- `frontend/src/features/inventory/components/MaterialDetailsModal.jsx`
- `frontend/src/features/finance/expenses/components/DeleteExpenseModal.jsx`
- `frontend/src/features/finance/payments/components/PaymentDetailDrawer.jsx`
- `frontend/src/features/finance/compensation/components/DoctorSettingsDrawer.jsx`
- `frontend/src/features/finance/payroll/components/StaffSettingsDrawer.jsx`
- `frontend/src/features/admin/SuperAdmin/SuperAdminCommandPalette.jsx`

These are migration candidates, not authorization to rewrite them en masse. Each consumer must preserve its existing API calls, mutations, route semantics, validation, and permission behavior.

## Library boundary findings

- Headless UI is actively used by `DateTimePicker` and `PatientSelect`.
- Radix Tooltip is actively wrapped in `Tooltip.jsx`.
- Radix Dialog/Dropdown Menu/Select/Toast packages are installed, but no active source imports were established during the initial exact-import search. They must not be removed until dependency/reference proof is complete.
- React Hot Toast is actively used both through shared wrappers and directly in feature code.
- FullCalendar is a specialized scheduling dependency and should be token-integrated, not replaced by default.
- TanStack Table/Virtual are active in `AdvancedTable` and are suitable foundations for the capable data-table contract.

## Highest-risk cross-cutting defects

1. **No canonical overlay stack:** z-50, z-100 and z-9999 coexist with unrelated local focus/scroll behavior.
2. **Focus return is not guaranteed:** the shared Modal and command palette do not restore the invoking control.
3. **Scroll restoration is unsafe:** shared Modal resets body overflow to `auto`, not the prior value.
4. **Nested overlays are undefined:** Treatment, Date/Time and inventory workflows can stack independent systems.
5. **Translucent surface token is globally reusable:** `bg-surface` is not safe for every popup/content layer.
6. **RTL parity is inconsistent:** some primitives are direction-aware while several modal/error/notification surfaces force Arabic/RTL.
7. **Reduced motion is not a shared contract:** pulse, bounce, scale, rotate, blur and infinite animations are spread across primitives.
8. **Interactive non-buttons exist:** clickable table rows and interactive StatCard containers are not keyboard-equivalent.
9. **Form semantics are inconsistent:** label/error/help/required/async-save contracts differ across wrappers and raw controls.
10. **Two Playwright configs diverge:** CI explicitly calls `playwright.config.ts`; the `.js` file is non-canonical until references are proven.

## Phase 1 conclusion

There is enough reuse to evolve the UI safely, but not enough consistency to perform a visual-only global CSS flip. The safe path is compatibility-first: consolidate tokens, introduce canonical overlay/form/data contracts, migrate representative high-risk consumers, add regression coverage, then enforce new guardrails gradually.