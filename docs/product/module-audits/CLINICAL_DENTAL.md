# Clinical / Dental — Forensic Module Audit

**Plan:** DENTIX PLAN 03 — EXISTING PRODUCT FORENSIC IMPROVEMENT  
**Audit date:** 2026-08-18  
**Status:** IMPLEMENTATION IN PROGRESS

## Module purpose

- **User problem:** record and maintain dental clinical status, treatment, treatment sessions, tooth status, materials consumed, and prescription-related clinical work from the patient workspace.
- **Primary users/roles:** dentists and other clinic users holding the relevant clinical/treatment permissions; exact action authority remains server-owned.
- **Current entry points:** mainly `/patients/:id`, especially the dental chart and treatment history; prescription printing also uses `/print/rx/:id`.
- **Evidence:** `frontend/src/pages/PatientDetails.jsx`, `frontend/src/shared/ui/modals/TreatmentModal.jsx`, `frontend/src/features/dental/`, `backend/routers/treatments.py`, treatment/prescription/procedure routers and services.

## Product intent review

### Current expected outcome

A permitted clinician can open a visible patient, inspect the dental chart, register or edit treatment, associate a tooth when relevant, record status/details/material use, add treatment sessions, and have the resulting clinical/stock effects persisted without leaking another patient's or tenant's information.

### Classification

- **Works and should remain:** patient-scoped treatment create/update/delete, tooth-status update, treatment sessions, procedure/pricing integration, consumed-material integration, stock-conflict handling, patient visibility and tenant/RBAC enforcement.
- **Works but UX is poor:** treatment editing is a very dense single modal, many controls are raw/unlabelled, advanced/material/session workflows compete for attention, and the shell is narrow even on large displays.
- **Visually poor/inconsistent:** hard-coded white/slate/red/blue surfaces and local radii/shadows coexist with Plan 02 semantic tokens.
- **Broken:** repeated treatment edits can produce incorrect stock reversal behavior; see P1 finding C-DENTAL-001.
- **Slow / performance-risk:** opening TreatmentModal starts an active-session query and a stock-summary request, with additional material/procedure requests during interaction. Timing is not yet measured; no performance regression claim is made without runtime evidence.
- **Permission-sensitive:** all treatment/clinical mutations and patient visibility.
- **Future feature — do not implement:** anything not already proven in current routes/capabilities, including new charting concepts, new AI clinical actions, or new treatment business rules.

## Current behavior contract

The following observable behavior must remain stable unless a separate authorized decision changes it.

### Entry / visible data

- Patient clinical work is entered from `/patients/:id`.
- Dental chart status is loaded for the current patient.
- Treatment history is loaded when relevant patient-detail tabs require it.
- The treatment editor receives patient/treatment/procedure data from the existing patient workspace.

### Create treatment

- Frontend POSTs to `/api/v1/treatments`.
- Server requires `TREATMENT_PLAN_WRITE`.
- Server verifies patient visibility before creation.
- Existing price-list/procedure pricing and price snapshot logic remains backend-owned.
- Existing stock validation/consumption remains backend-owned.
- Existing `skip_stock_check` behavior remains supported; Plan 03 does not redefine when the user may choose it.

### Edit treatment

- Frontend PUTs to `/api/v1/treatments/{id}`.
- Server requires `TREATMENT_PLAN_WRITE`.
- Server verifies treatment visibility and patient visibility.
- Existing stock associated with the treatment is reversed before applying current edited consumption.
- New material usage is then persisted and the transaction committed.

### Delete treatment

- DELETE `/api/v1/treatments/{id}` requires `CLINICAL_WRITE` and visible treatment access.
- Existing stock movements associated with the treatment are reversed before deletion.

### Tooth status

- POST `/api/v1/treatments/tooth_status` requires `CLINICAL_WRITE` and visible patient access.
- PatientDetails currently performs the treatment mutation and tooth-status mutation as separate existing calls; this audit does not merge them into a new API/business transaction.

### Treatment sessions

- POST `/api/v1/treatments/{id}/sessions` requires `TREATMENT_PLAN_WRITE` and visible treatment access.
- Client-side session UI must not alter this server contract.

### Stock conflict behavior

- `CONFIRM_OPEN_REQUIRED` remains a structured 409 path used to open the existing material-session workflow.
- Existing stock insufficiency handling may present the existing “save without stock deduction” retry using `skip_stock_check`; this audit does not silently remove or expand that capability.

### Loading / error / empty states

- Existing React Query/server errors remain authoritative.
- Specialized stock errors are intentionally rethrown from `useTreatmentOperations` so TreatmentModal can present the existing recovery workflow.
- Generic clinical failures must remain visible to the user rather than being masked.

### Mobile / RTL

- Clinical workflows must remain usable on small screens and Arabic layouts.
- No new locale/business semantics are introduced.

## Technical audit

### Frontend ownership

- `frontend/src/pages/PatientDetails.jsx`
- `frontend/src/shared/ui/modals/TreatmentModal.jsx`
- `frontend/src/features/patients/hooks/useTreatmentOperations.js`
- `frontend/src/features/dental/`
- material/session consumers under `frontend/src/features/inventory/`

### State / requests

- PatientDetails uses React Query hooks and lazy tab data loading; this is a strong existing pattern to preserve.
- TreatmentModal uses React Query for active material sessions and imperative stock-summary loading on open.
- Treatment mutation ownership remains in `useTreatmentOperations`.

### Backend ownership

- `backend/routers/treatments.py`
- `backend/services/treatment_service.py`
- `backend/services/inventory_service.py`
- patient-visibility helpers under `backend/services/patient_access_service.py`
- clinical/inventory models and schemas.

## Findings

### C-DENTAL-001 — P1 — repeated edits can accumulate treatment stock deduction

**Class:** BUG_FIX / DATA CORRECTNESS / TEST_GAP

**Evidence/root cause:**

1. Treatment consumption writes stock movements using `reference_id = TREATMENT:{treatment_id}`.
2. An edit calls `reverse_stock_by_reference(TREATMENT:{id})` and then writes the edited consumption using the same original reference.
3. `reverse_stock_by_reference` currently creates reversal rows using the fixed reference `REVERSE:TREATMENT:{id}` and returns immediately forever after it detects any existing row with that reversal reference.
4. Therefore the first edit can reverse the original consumption, but after the edited treatment creates new `TREATMENT:{id}` movements, a second edit sees the old reversal marker and skips reversing those newly-added movements.
5. The subsequent edited consumption is then deducted again, producing an incorrect stock position.

**Blast radius:** stock quantities, treatment material history/costing, repeated edit workflows.

**Required fix:** make reversal idempotent against the *current outstanding net movement* for the reference rather than treating the existence of any prior reversal as proof that all future movements under that reference are reversed.

**Constraints:** no schema change; no API change; preserve movement audit rows and existing reference naming compatibility.

**Regression required:** initial reversal, fully-balanced repeated reversal no-op, and reversal after new movements have been added under the same treatment reference.

### C-DENTAL-002 — P2 — TreatmentModal bypasses canonical overlay behavior

**Class:** UX_REFINEMENT / VISUAL_SYSTEM_ALIGNMENT / ACCESSIBILITY / TEST_GAP

`TreatmentModal.jsx` still owns a raw `fixed inset-0 ... z-50` shell, while Plan 02 established `DentixDialog` with focus trap/return, Escape, outside-click contract, scroll locking, semantic surfaces and canonical z-layer behavior.

**Required fix:** migrate only the TreatmentModal shell to the canonical dialog and preserve the exact payload/mutation/business behavior. Nested inventory/session workflows remain existing capabilities and must continue to function.

### C-DENTAL-003 — P2 — treatment form semantics are inconsistent

**Class:** ACCESSIBILITY / UX_REFINEMENT

Multiple diagnosis/tooth/notes/procedure controls are raw inputs/selects/textareas without a consistent label/error/help relationship. Several icon-only controls do not supply accessible names. The current editor is heavily Arabic-hard-coded and does not intentionally express English/RTL parity.

**Required fix:** improve labels/names and semantic tokens incrementally while avoiding a business-rule rewrite. Do not convert every control in one unsafe mass change.

### C-DENTAL-004 — P2 — treatment editor density and narrow desktop container

**Class:** UX_REFINEMENT / MOBILE

The existing treatment workflow contains tooth state, pathology/restoration state, procedure/pricing, status, advanced endodontic details, inventory consumption and sessions inside a `max-w-md` modal. This produces excessive vertical interruption and hides hierarchy.

**Decision:** use the existing large canonical dialog capability for the current treatment workflow rather than inventing a new clinical feature. Preserve progressive disclosure already present for advanced details.

### C-DENTAL-005 — P2 — tooth-select overlay is another raw clinical overlay

**Class:** ACCESSIBILITY / VISUAL_SYSTEM_ALIGNMENT / TEST_GAP

`PatientDetails.jsx` renders the tooth selector as its own `fixed inset-0` `z-[60]` overlay with no canonical focus/scroll behavior. This is in the same clinical flow and should be migrated after TreatmentModal shell regression is proven.

### C-DENTAL-006 — P2 — treatment UI lacks focused regression coverage

**Class:** TEST_GAP

Backend TreatmentService unit tests exist, but current tests mock stock reversal rather than proving repeated reversal correctness. No dedicated TreatmentModal unit test was found in the rapid search. Plan 02 overlay tests prove the shared primitive, not this clinical consumer's payload/workflow.

## UX / visual audit

- Information hierarchy is weak because almost every sub-area is cardified with similar visual weight.
- The procedure/price/material flow is clinically important but visually competes with tooth-condition controls and advanced/session content.
- Hard-coded `bg-white`, slate palettes, raw semantic red/blue/green states, arbitrary radii/shadows and local animation remain.
- Primary save/cancel actions sit at the bottom of a long scrolling modal and should remain clear without inventing a new workflow.

## Responsive / RTL audit

Validate at 320, 375, 430, 768, 1024 and 1440+ during regression.

Current risks:
- dense two-column price controls on very small widths;
- nested material/session overlays;
- long Arabic labels and clinical terms;
- physical/local z-index implementations;
- editor is Arabic-first rather than deliberately bilingual.

## Accessibility audit

Current risks:
- raw modal does not inherit Plan 02 focus trap/return and scroll-lock guarantees;
- icon-only close/remove controls need explicit accessible names;
- some raw inputs rely on placeholders rather than persistent labels;
- tab-like tooth state buttons do not provide a full canonical tab relationship;
- reduced-motion behavior is not consistently inherited by feature-local animations.

## Performance audit

**Known request behavior on treatment-editor open:**
- active material sessions query when `isOpen` is true;
- stock-summary request from the modal effect;
- `getMaterials` only as a stock-summary fallback;
- additional procedure/material requests occur when corresponding interactions are used.

**Measured timing:** not yet established. No latency target is claimed without a runnable authenticated runtime measurement.

**Non-regression target:** shell/accessibility changes must not add an extra baseline network request or duplicate treatment mutation.

## Security / RBAC audit

Strengths to preserve:

- create treatment: `TREATMENT_PLAN_WRITE` + patient visibility;
- update treatment: `TREATMENT_PLAN_WRITE` + treatment and patient visibility;
- delete treatment: `CLINICAL_WRITE` + treatment visibility;
- tooth status: `CLINICAL_WRITE` + patient visibility;
- treatment session/material boundaries also check permissions and visibility/tenant context.

No client-only authorization is accepted as sufficient.

## Test audit

### Existing

- TreatmentService unit coverage for creation, stock validation/consumption, update, deletion, pricing and error paths.
- Broader patient/RBAC/visibility tests exist from the recent Patient Workspace hardening.
- Plan 02 shared overlay interaction and visual regression foundation exists.

### Missing / required

- direct regression for repeated stock reversal under the same treatment reference;
- TreatmentModal consumer regression preserving save payload and specialized stock-error path after shell migration;
- tooth-selector canonical overlay regression if migrated in this module pass;
- focused AR/EN/mobile interaction validation for clinical surfaces.

## Improvement proposal before code

### Root-cause / correctness change

1. Replace the reversal service's fixed “any prior reversal means done forever” check with net outstanding calculation per stock item for a reference.
2. Keep existing `TREATMENT:{id}` and `REVERSE:TREATMENT:{id}` reference names for compatibility/audit history.
3. Add regression tests proving first reversal, idempotent no-op, and later reversal after new treatment movement.

### UI change

1. Migrate TreatmentModal shell to `DentixDialog`.
2. Keep its internal treatment/material/session state and save payload unchanged.
3. Use a larger desktop width while retaining viewport-bounded mobile scrolling.
4. Add accessible close/remove/control names and semantic surface/text/border tokens in the touched shell/critical controls.
5. Migrate the patient-detail tooth selector to `DentixDialog` only after the treatment shell regression is stable.

### API / schema impact

- API: none.
- Database schema/migration: none.
- Business-rule change: none intended.
- Internal stock reversal behavior: correctness fix restoring the already-intended “old treatment stock is reversed before edited consumption is applied.”

### Tests

- targeted backend reversal regression;
- existing TreatmentService tests;
- targeted frontend TreatmentModal test(s);
- relevant patient/clinical E2E;
- Plan 02 overlay/visual guardrails;
- full module role/tenant regression before closeout.

## Acceptance criteria

- [ ] Repeated treatment edits do not accumulate stale stock consumption.
- [ ] First reversal restores the outstanding treatment movement exactly once.
- [ ] Calling reversal again without new original movement is a no-op.
- [ ] Adding new treatment movement under the same reference can be reversed on the next edit.
- [ ] Existing treatment create/update/delete APIs and payload shapes are unchanged.
- [ ] Treatment/patient RBAC and tenant isolation are unchanged.
- [ ] Existing stock-conflict recovery behavior is preserved.
- [ ] TreatmentModal uses the canonical blocking-dialog contract without changing mutation count or save payload.
- [ ] Clinical controls touched in this pass have persistent/accessible names.
- [ ] Desktop/mobile and Arabic/English states are reviewed where applicable.
- [ ] Targeted backend/frontend tests and relevant E2E pass.
- [ ] No new design-guardrail violation is introduced.
