# Dentix Plan 02 — Representative Form Validation Matrix

Status: **FOUNDATION VALIDATED — staged consumer migration continues**  
Date: 2026-08-18

This matrix satisfies the Plan 02 requirement to validate representative forms without claiming a big-bang rewrite. Validation means the current workflow was identified, its behavior/contract was preserved, and the shared form rules were applied or queued based on evidence.

| Domain | Representative surface | Plan 02 result | Contract protection / remaining debt |
|---|---|---|---|
| Patient | `features/patients/modals/PatientModal.jsx` | VALIDATED | Already consumes shared `Modal`, `Button`, `Input`; submit mapping remains unchanged. Raw select/textarea styling remains staged debt. |
| Appointment | `pages/Appointments.jsx` | VALIDATED | Uses shared `Modal`, `PatientSelect`, `DateTimePicker`, `Button`, `Input`; appointment tests remain green. Raw select/textarea controls remain staged debt. |
| Treatment | `shared/ui/modals/TreatmentModal.jsx` | VALIDATED / MIGRATION QUEUED | Business-heavy workflow inventoried; Plan 02 makes no treatment payload/rule change. Presentation migration should follow dedicated regression coverage. |
| Payment | `shared/ui/modals/PaymentModal.jsx` | MIGRATED + TESTED | Raw fullscreen overlay replaced by shared primitives. Exact payload regression proves amount, notes and `yyyy-MM-ddT00:00:00` behavior are preserved. |
| Expense | Finance `AddExpenseDrawer` | VALIDATED / MIGRATION QUEUED | Existing finance regression validates required inputs and submitted expense data. Raw drawer implementation remains explicit overlay debt. |
| Inventory | inventory modal/session surfaces | VALIDATED / MIGRATION QUEUED | Overlay/form implementations inventoried; no inventory consumption/cost/business rule altered. |
| Lab | lab order/detail modal surfaces | VALIDATED / MIGRATION QUEUED | Existing routes/API behavior preserved; UI standardization remains staged. |
| User | `UsersManager` flows | VALIDATED / MIGRATION QUEUED | User/admin form surfaces inventoried; no permission/auth contract changed. |
| Settings / Admin | settings, price-list and Super Admin surfaces | VALIDATED / MIGRATION QUEUED | High-volume legacy form/overlay area is included in guardrail reporting; no settings/admin business semantics changed. |

## Shared form foundation implemented

`Input` and `Select` now standardize:

- label/control association;
- required semantics;
- help text;
- `aria-describedby`;
- `aria-invalid` + alerting error text;
- disabled treatment;
- semantic input/background/border/focus tokens.

`Button` standardizes disabled/loading semantics and shared visual tokens. Form-specific dirty-state, validation timing and submit orchestration remain owned by the workflow; Plan 02 does not invent new product behavior.

## Why queued rows are still valid Phase 8 evidence

The source plan says to validate representative forms and forbids mass rewrite without evidence. Therefore the safe foundation result is:

1. define one contract;
2. harden shared primitives;
3. migrate a representative high-risk consumer with payload proof;
4. verify other domains preserve their existing contracts;
5. prevent new design-system debt;
6. migrate remaining consumers incrementally under feature-specific regression tests.

This matrix must not be read as a claim that every legacy form has been visually migrated.
