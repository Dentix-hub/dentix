# Dentix Modal Reduction Audit — Plan 02 Phase 7

Status: **AUDIT COMPLETE; migrations pending**

This audit classifies current modal-like workflows by task complexity. It does not change routes, API calls, mutations or product behavior.

## Decision model

| Workflow class | Default target |
|---|---|
| confirmation | `DentixConfirmDialog` |
| small focused task | `DentixDialog`; mobile may use `DentixBottomSheet` |
| contextual preview/details | `DentixPopover` for small anchored context, otherwise `DentixDrawer` |
| medium form | `DentixDrawer`; mobile `DentixBottomSheet`/fullscreen sheet |
| complex form | dedicated/fullscreen workspace preferred; compatibility wrapper allowed during migration |
| multi-step / nested workflow | dedicated workspace or controlled full-screen experience; avoid stacked independent modals |

## Current workflow classification

| Current implementation | Class | Target decision | Behavior constraints |
|---|---|---|---|
| `shared/ui/ConfirmDialog.jsx` | confirmation | `DentixConfirmDialog` | Preserve confirm/cancel call semantics; add async/loading safely. |
| `features/finance/expenses/components/DeleteExpenseModal.jsx` | confirmation | `DentixConfirmDialog` | Preserve deletion permission/API and destructive copy. |
| browser-native archive confirm in patient critical path | confirmation | separate product decision | Do not replace in Plan 02 unless tested behavior is intentionally migrated. |
| `shared/ui/modals/KeyboardShortcutsModal.jsx` | small informational task | `DentixDialog` | Preserve shortcut copy/i18n. |
| `shared/ui/modals/PaymentModal.jsx` | small form | `DentixDialog` desktop; sheet candidate mobile | Preserve payment payload/date conversion exactly. |
| `features/inventory/components/TrackSessionModal.jsx` | small/medium task | `DentixDialog` or drawer depending nested context | Must participate in parent overlay stack. |
| `shared/ui/SupportModal.jsx` | medium form | `DentixDrawer`; sheet/fullscreen on narrow screens | Preserve `submitFeedback`, success/error behavior and external support link. |
| `features/inventory/components/AddWarehouseModal.jsx` | medium form | `DentixDrawer` | Preserve inventory mutation/validation. |
| patient edit modal(s) | medium form | `DentixDrawer` | Preserve patient field permissions/validation and current save payload. |
| `features/finance/compensation/components/DoctorSettingsDrawer.jsx` | medium form | canonical `DentixDrawer` | Keep existing route/state and compensation semantics. |
| `features/finance/payroll/components/StaffSettingsDrawer.jsx` | medium form | canonical `DentixDrawer` | Preserve payroll/staff settings behavior. |
| `features/finance/payments/components/PaymentDetailDrawer.jsx` | contextual preview/details | canonical `DentixDrawer` | Preserve read/detail actions. |
| `features/inventory/components/WarehouseDetailsModal.jsx` | contextual details | `DentixDrawer` | Preserve stock/detail behavior. |
| `features/inventory/components/MaterialDetailsModal.jsx` | contextual details | `DentixDrawer` | Preserve inventory state/actions. |
| `shared/ui/modals/PrescriptionModal.jsx` | medium/complex form | drawer/fullscreen-mobile; dedicated-page candidate only with separate approval | Preserve saved-medication lookup and print payload. |
| `shared/ui/modals/TreatmentModal.jsx` | complex + nested workflow | dedicated/fullscreen workspace is the design target; compatibility overlay initially | **No route/business change in Plan 02.** Preserve treatment payload, inventory consumption, session behavior and nested TrackSession workflow. |
| `GlobalLabOrdersModal.jsx` | data workspace in modal | drawer or dedicated-page candidate | No route change without explicit approval. |
| `CommandPalette.jsx` / SuperAdmin command palette | global command overlay | canonical dialog/command surface | Preserve keyboard navigation and routing commands. |
| `GlobalSearch.jsx` results | anchored search results | `DentixPopover`/combobox pattern | Preserve server-backed search/navigation. |
| `NotificationBell.jsx` dropdown | anchored notification list | `DentixPopover`/menu-list pattern | Preserve polling/read/dismiss behavior. |
| `PatientSelect.jsx` options | combobox popup | `DentixSelect`/combobox wrapper | Preserve search threshold, recent list and quick-add. |
| `DateTimePicker.jsx` | date selection overlay | `DentixDatePicker`; modal/sheet mode as space requires | Preserve date-only/month/datetime output contracts. |

## Anti-patterns to remove gradually

- `fixed inset-0` feature-local backdrops.
- feature-local `z-50`, `z-[100]`, `z-[9999]` escalation.
- body scroll locking outside shared overlay infrastructure.
- nested overlays with independent Escape/outside-click ownership.
- large forms placed in dialogs only because a modal component already exists.

## Migration order

1. canonical overlay primitives + tests;
2. KeyboardShortcuts/ConfirmDialog (low risk);
3. PaymentModal + representative finance/inventory drawers;
4. DateTimePicker/PatientSelect popup infrastructure;
5. command/search/notification popovers;
6. Support/prescription medium forms;
7. Treatment/large lab workflows only after compatibility tests and a separately reviewed container decision.

Phase 7 audit is complete when this classification is accepted; implementation remains coupled to Phases 5/6/8/12.