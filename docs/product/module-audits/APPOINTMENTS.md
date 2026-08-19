# Appointments — Forensic Module Audit

**Plan:** DENTIX PLAN 03 — EXISTING PRODUCT FORENSIC IMPROVEMENT  
**Audit date:** 2026-08-18  
**Status:** IMPLEMENTATION IN PROGRESS

## Product intent review

### Primary users

Clinic users with appointment permissions, including owner/admin/reception workflows and doctor-scoped scheduling behavior enforced by the server.

### Current user goal / expected outcome

Open `/appointments`, see the permitted schedule, switch between calendar/list/board views, create a booking for an existing patient (or use the existing quick-patient flow), change appointment time/status, and cancel/delete an appointment with accurate success/failure feedback.

### Existing capabilities that must remain

- calendar, list and Kanban/board views;
- patient preselection from `/appointments?patient_id=...`;
- quick patient creation inside the booking dialog;
- appointment create/update/status/delete endpoints;
- doctor-scoped reads for doctor-role users;
- existing date/time picker and weekly-calendar drag/drop behavior;
- appointment status set currently exposed by the product;
- tenant timezone/business-date statistics already implemented by `getDateInTimeZone` / `selectAppointmentsForBusinessDate`;
- server-owned RBAC and tenant isolation.

No new scheduling capability is introduced by Plan 03.

## Current behavior contract

### Entry / data

- UI route: `/appointments`.
- GET `/api/v1/appointments` requires `APPOINTMENT_READ`.
- Doctor-role reads are scoped to `current_user.id` by the router/CRUD query.
- Default client page requests cached appointment/patient data through React Query hooks.

### Create

- POST `/api/v1/appointments` requires `APPOINTMENT_CREATE`.
- Patient must exist in the current tenant.
- `tenant_id` is injected from the authenticated user, not accepted as client authority.
- Existing exact-time doctor conflict behavior remains unchanged.
- Existing quick-create-patient flow remains a separate patient mutation followed by selection.

### Update time/details

- PUT `/api/v1/appointments/{id}` requires `APPOINTMENT_UPDATE`.
- Update must affect only a visible/current-tenant appointment.
- A missing/not-visible appointment must not be reported as a successful update.
- Calendar drag/drop continues to send the existing `date_time` update contract.

### Status

- PUT `/api/v1/appointments/{id}/status` requires `APPOINTMENT_UPDATE`.
- A successful response must mean the appointment status was actually changed.
- Concurrent update conflict remains HTTP 409.

### Delete/cancel

- DELETE `/api/v1/appointments/{id}` requires `APPOINTMENT_CANCEL`.
- Existing behavior is soft deletion in CRUD.
- A successful response must mean a current-tenant appointment was actually soft-deleted.

### Loading/error/empty

- Existing skeleton and empty state stay.
- Mutations must surface a failure instead of false success.

### Mobile / RTL

- Calendar/list/board must remain horizontally/vertically navigable at mobile widths.
- Booking dialogs use the canonical Dentix dialog foundation and DateTimePicker.
- Arabic/English and tenant business-date semantics must be preserved.

## Technical audit

### Frontend

- `frontend/src/pages/Appointments.jsx`
- `frontend/src/hooks/useAppointments*` / appointment API
- `frontend/src/shared/ui/WeeklyCalendar`
- shared `Modal`, `ConfirmDialog`, `DateTimePicker`, `PatientSelect`.

Server state is mostly hook-backed, but create/status/delete still mix direct API functions plus explicit refetch with React Query mutations. This is consistency debt, not by itself a correctness reason to rewrite the page.

### Backend

- `backend/routers/appointments.py`
- `backend/crud/appointment.py`
- `backend/services/appointment_service.py` (separate service path used by other capabilities; current UI router still uses CRUD)
- appointment/patient/user models and appointment schemas.

## Findings

### APPT-001 — P1 — full appointment update converts intended 404 to 500

`update_appointment()` raises HTTP 404 when CRUD returns `None`, but its broad `except Exception` catches that HTTPException, logs it as a backend error, and returns HTTP 500 (`Backend Error: 404: Appointment not found`).

**Impact:** stale/not-visible appointment updates are reported as server failures; client error recovery and monitoring are incorrect.

**Fix:** preserve HTTPException before the generic error handler. No API/schema/business-rule change.

### APPT-002 — P1 — status endpoint can return success when no appointment was changed

`crud.update_appointment_status()` returns `None` for missing/not-current-tenant rows. The router ignores the return value and always returns a success envelope.

**Impact:** false-green core workflow; user may believe a status transition occurred when it did not.

**Fix:** check the returned appointment, rollback the pending audit entry if absent, and return 404.

### APPT-003 — P1 — delete endpoint can return success when no appointment was deleted

`crud.delete_appointment()` returns `None` for missing/not-current-tenant rows. The router ignores the result and always returns success.

**Impact:** false-green destructive workflow.

**Fix:** check the result, rollback the pending audit entry if absent, and return 404.

### APPT-004 — P2 — appointment page has accessibility debt in icon/destructive controls

View-switch icon buttons and appointment delete icon buttons rely on `title`, icon shape, or hover reveal instead of robust accessible names/visible keyboard treatment.

**Decision:** keep this recorded for a focused UI pass; do not let it delay APPT-001/002/003.

### APPT-005 — P2 — page mixes React Query mutation ownership with direct API + refetch

Create/status/delete use direct API calls plus manual refetch while drag/drop uses mutation hooks. This increases mutation/invalidation inconsistency risk.

**Decision:** no mass state-management rewrite without a reproduced defect. Preserve behavior in this pass.

### APPT-006 — P2 — list/board date rendering must be verified against tenant timezone semantics

The page correctly uses tenant-timezone helpers for business-date stats, while list/card presentation uses `new Date(...).toLocaleString(...)` and drag/drop trims an offset string. These paths require runtime timezone regression, not speculative rewriting.

**Decision:** preserve current date-time contract until an evidence-backed mismatch is reproduced.

### APPT-007 — P3 — Kanban visual tokens remain partly legacy

Board/card surfaces still contain hard-coded white/slate/translucent shadows/radii. This is visual-system debt, lower priority than scheduling correctness.

## UX / visual audit

- Calendar is the default and highest-information view; this is appropriate for scheduling.
- Three view modes add flexibility but their icon-only controls need stronger accessibility state.
- Empty state and primary new-booking action are clear.
- Booking uses a canonical modal and the existing DateTimePicker, avoiding another local date overlay.
- Kanban columns/cards are visually heavier and less tokenized than the Plan 02 baseline.
- Destructive action discoverability depends on hover in board view, which is weak for keyboard/touch contexts.

## Responsive / RTL audit

Risks to validate:
- board horizontal scrolling at 320/375/430;
- long translated status labels;
- mobile DateTimePicker / keyboard interaction;
- list table horizontal overflow;
- locale formatting in date/time display;
- drag/drop keyboard behavior.

## Accessibility audit

- DnD has a KeyboardSensor and sortable keyboard coordinates: preserve.
- View controls need `aria-label` / selected state.
- Icon-only delete controls need accessible names and keyboard-visible treatment.
- Booking textarea should have an explicit label association.
- Shared Modal/ConfirmDialog/DateTimePicker already inherit Plan 02 overlay behavior.

## Performance audit

- Main page loads appointments and patients in parallel through cached hooks.
- `patients.find(...)` is repeated per row/card; acceptable at current default page size but O(n*m) if data grows substantially.
- No latency regression is claimed without runtime measurement.
- Correctness fixes below add no network request and no client render work.

## Security / RBAC audit

Verified boundaries to preserve:
- read: `APPOINTMENT_READ`;
- create: `APPOINTMENT_CREATE` plus current-tenant patient validation;
- update/status: `APPOINTMENT_UPDATE`;
- delete: `APPOINTMENT_CANCEL`;
- doctor role receives doctor-scoped appointment list;
- mutation CRUD verifies appointment patient belongs to the current tenant before mutating.

The application must not infer authorization from client visibility alone.

## Test audit

### Existing

- frontend `Appointments.test.jsx` covers page/calendar rendering and opening new-booking flow;
- appointment service tests exist;
- critical Playwright path and broader CI exist;
- Plan 02 overlay tests cover shared dialog mechanics.

### Missing critical coverage

- router preserves 404 for update-not-found;
- status-not-found is not falsely successful;
- delete-not-found is not falsely successful;
- pending audit state is rolled back on no-op status/delete.

## Improvement proposal before code

1. Add focused router regression tests for APPT-001/002/003.
2. In `update_appointment`, re-raise `HTTPException` before generic logging/500 handling.
3. In status/delete routes, inspect CRUD return value; if `None`, rollback pending audit work and raise 404; otherwise preserve the existing success envelope.
4. Do not alter schemas, route names, payloads, status vocabulary, timezone conversion or appointment business rules.
5. Run backend suite/security, frontend/build, critical E2E and visual gate before closing the module.

## API / schema impact

- API path/payload shape: none.
- Database schema: none.
- Business rules: none.
- Error semantics: corrected so an already-defined not-found condition is no longer converted/falsely reported as success/500.

## Acceptance criteria

- [ ] Missing/not-visible full update returns 404, not 500.
- [ ] Missing/not-visible status update returns 404, not success.
- [ ] Missing/not-visible delete returns 404, not success.
- [ ] No false pending audit write is committed for a missing target.
- [ ] Existing successful create/update/status/delete contracts are unchanged.
- [ ] RBAC/tenant checks remain server-owned.
- [ ] Frontend build/tests pass.
- [ ] Backend tests/security pass.
- [ ] Critical E2E and visual regression pass.
