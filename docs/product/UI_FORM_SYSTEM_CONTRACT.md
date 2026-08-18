# Dentix Form System Contract — Plan 02 Phase 8

Status: **TARGET CONTRACT — representative migration pending**

## Field anatomy

Every field pattern must support, when applicable:

1. visible label linked to the control;
2. optional help text;
3. required/optional state;
4. input/control;
5. unit/prefix/suffix where meaningful;
6. validation/error text linked with `aria-describedby`;
7. `aria-invalid` on invalid controls;
8. read-only and disabled states that are visually distinct and semantically correct.

Placeholder text is not a label.

## Validation timing

- Validate structural requirements on submit and after a user has interacted with a field.
- Avoid disruptive error messages on untouched fields.
- Server validation remains authoritative for business rules.
- When the server rejects a field, keep the user's values and map the error to the field when possible.
- Form-level/server errors appear in an error summary/Alert when they cannot be mapped to one field.

## Save behavior

- Primary save action has an explicit loading state.
- Disable duplicate submission while a save is in flight.
- Do not clear the form until success is established.
- Preserve current API payload shape and idempotency behavior.
- Destructive actions are visually and semantically distinct from save.

## Dirty / cancel behavior

- Forms that can lose meaningful edits should expose dirty state to the container.
- Closing/cancelling a dirty medium/complex form requires an intentional discard policy.
- Do not introduce a new confirmation that changes an existing workflow without product review; first expose the capability in the shared contract.

## Data-type patterns

### Date
- Date-only values remain date-only strings where current contracts use them.
- Do not silently convert date-only values to UTC timestamps.
- Display uses clinic/user locale while payload semantics remain unchanged.

### Datetime
- Display timezone and payload timezone behavior must be explicit.
- Existing endpoint contracts are preserved during UI migration.

### Month
- Month-only controls emit the existing `YYYY-MM` contract unless the endpoint contract changes separately.

### Currency / money
- Numeric value and currency/unit are separate concepts.
- Input must make decimals/negative rules explicit from business logic.
- Displayed money uses a shared formatter; parsing must not depend on localized display punctuation without tests.

### Phone
- Keep display direction `ltr` for phone numbers even inside RTL forms.
- Do not change normalization/business validation in a UI-only refactor.

### Number / quantity
- Show units when clinically/financially important.
- `min`, `max`, `step` are driven by real rules, not aesthetic convenience.

### Select
- Native select is preferred when simple and sufficient.
- Searchable/large option sets use the canonical combobox/select wrapper.
- Selected value, disabled options, empty state and keyboard behavior must be testable.

## Layout patterns

- compact field row: related low-risk fields only;
- standard form group: label + control + help/error;
- section: meaningful semantic grouping, not a card by default;
- sticky action footer only for long drawers/fullscreen forms where it improves safe completion;
- mobile forms use one-column flow unless paired values clearly benefit from grouping.

## Representative form audit

| Area | Existing examples | Main Plan 02 risks | Migration requirement |
|---|---|---|---|
| Patient | create/edit patient, patient details edits | mixed raw/shared inputs; permission-sensitive fields | shared field semantics without changing doctor/receptionist visibility/edit rules |
| Appointment | appointment create/edit + DateTimePicker | date/time semantics, patient combobox, mobile overlay | preserve appointment payload/conflict rules |
| Treatment | `TreatmentModal`, sessions/material consumption | complex nested workflow, double-submit, units | container migration only after overlay stack; preserve clinical/inventory mutations |
| Payment | PaymentModal + Finance V2 payment forms | money parsing/date semantics, duplicate implementations | canonical money/date/button patterns; preserve payment API |
| Expense | Finance V2 add/delete expense | money/date/category validation | shared field/actions + canonical destructive confirmation |
| Inventory | warehouse/material/session forms | units/quantity/batches/nested overlays | explicit units and canonical drawer/dialog; preserve stock semantics |
| Lab | lab order forms/global orders | status/date/cost fields | standard sections + date/money patterns; preserve lifecycle |
| User | UsersManager/user forms | role/permission meaning | shared controls; never weaken RBAC |
| Settings/Admin | price lists, insurance, tenant/system settings | dense forms + high-risk config | standard groups, save progress/error summary; preserve admin authorization |

## Phase 8 implementation gates

Phase 8 becomes DONE only when the shared field contract is implemented in primitives and verified on representative Patient, Appointment, Treatment, Payment, Expense, Inventory, Lab, User and Settings/Admin surfaces without contract regressions.