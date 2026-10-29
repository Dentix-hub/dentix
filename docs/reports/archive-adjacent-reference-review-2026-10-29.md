# Adjacent archive reference review before delivery

Follow-up: all four findings below are now resolved locally on the same branch.
See [implementation and executed verification](archive-adjacent-reference-recovery-2026-10-29.md).
The original findings and review-time status are retained as an audit record.

Reviewed candidate: `b8b8a4c` on `fix/archive-learning-procedure-history`, based
on staging `94769aa`. The deleted-procedure learning fix remains local.
This review does not change application behavior, upload a branch, or access
the affected clinic database/backup.

**Delivery recommendation: HOLD.** Four additional defects were reproduced.
The earlier 81 backend and 12 PostgreSQL passing tests cover the original
learning-history fix; they do not establish recovery for these new scenarios.

## 1. HIGH — ordinary native care sessions make exports fail

Locations: `backend/services/tenant_archive_embedded_refs.py:9`,
`backend/services/care_session_service.py:319`,
`backend/services/care_session_material_service.py:312`.

The event validator rejects unknown `_id`/`_ids` keys. Current session, step,
observation, material-use and next-visit writers emit eleven reference names
missing from its supported mapping:

```text
session_id appointment_id provider_user_id resume_work_item_id
resume_from_session_id step_id observation_id request_id doctor_id
usage_ids material_id
```

A diagnostic probe enabled the existing rollout flag, called the real
`CareSessionService.start_session`, then exported the clinic. Export raised
`ArchiveError(section=clinical_events, field=payload.session_id,
category=unsupported_reference)`. No deletion or corrupt data is necessary.
An AST audit of actual ClinicalEvent payload constructors also located the
remaining names, including nested `items[].material_id` and list `usage_ids`.

Remediation: define explicit mappings for these emitted reference types,
including list elements, validate targets from the tenant archive, and remap
them after insertion. Cover real start/resume/step/observation/material-use/
next-visit workflows and repeated encrypted restore. Continue rejecting unknown
reference names and cross-tenant/unresolved live targets.

## 2. HIGH — next-visit request links keep old appointment IDs after restore

Locations: `backend/services/tenant_archive_import.py:106`,
`backend/services/care_session_service.py:1770`,
`backend/schemas/care_session.py:83`, `backend/crud/appointment.py:250`.

The scheduler stores the functional link as `[APPOINTMENT:<id>]` inside
`next_visit_requests.notes`. The response schema extracts
`fulfilled_appointment_id` from that token; appointment lifecycle operations
also find related requests using the token. The archive importer copies these
notes verbatim while regenerating appointment IDs.

A restricted-role PostgreSQL probe seeded the exact scheduled-request state,
performed full encrypted export, preview, confirmation and restore, and checked
the public response schema. `fulfilled_appointment_id` remained the old ID and
was different from the appointment mapping returned by restore. This can break
navigation and request reopening/completion synchronization.

Remediation: validate and remap the recognized appointment tokens in this
specific field, preserve other note text, verify same-patient/tenant targets,
and test cancel/completion/reschedule behavior after repeated restore. Do not
globally rewrite numeric strings in free-text notes.

## 3. HIGH — deleting an unprojected legacy treatment blocks stock/learning recovery

Locations: `backend/services/tenant_archive_history.py:9`,
`backend/services/treatment_service.py:655`,
`backend/services/treatment_service.py:1153`.

Historical treatment recognition requires an existing matching clinical work
item and a `procedure_cancelled` deletion event. Legacy/custom treatments can
have no canonical projection. Their ordinary deletion still preserves stock
movements, stock reversals and learning calculations, but no qualifying event
is emitted when the work item is absent.

A diagnostic probe created a custom legacy treatment with stock and learning
history, confirmed that `_sync_clinical_work_item` legitimately returned None,
and called the real `delete_treatment`. Subsequent export failed at
`stock_movements.reference_id`. Independently checking the retained learning
section also failed at `calculation_data.dist_log.treatment_id`.

Remediation: extend historical recognition using explicit, validated evidence
available for unprojected legacy deletions (including existing files), and
reserve absent IDs only for the matching historical fields. Preserve numeric
stock/learning history and strict live-FK rejection. Do not fabricate clinical
work items, drop audit logs or accept all dangling treatment references.

## 4. HIGH — deleting a lab order can orphan retained treatment events

Locations: `backend/services/lab_service.py:448`,
`backend/services/tenant_archive_history.py:17`.

`LabService.delete_lab_order` directly deletes the treatment identified by
`Link:LabOrder:<id>`. It does not use treatment deletion's clinical history
handling. If that treatment was projected, its existing events retain the
treatment ID without a supported deletion witness.

A diagnostic probe created a linked lab order/treatment, projected it through
the real treatment service, then called the real `delete_lab_order`. Export
failed at `clinical_events.payload.treatment_id` with `invalid_reference`.

Remediation: share a transaction-safe linked-treatment deletion path that
preserves cancellation evidence, reverses stock and retains clinical/financial
invariants. Keep paid-order deletion guards and rollback behavior. Also define
a bounded recovery policy for existing retained events from that path.

## Checks and evidence

Three SQLite diagnostic probes confirmed findings 1, 3 and 4 (exit 0).
One restricted-role PostgreSQL encrypted-restore diagnostic confirmed finding
2 (exit 0). These probes intentionally assert the **presence of each defect**;
their passing results are not a successful functionality or acceptance gate.
No existing test assertion was changed and no failing assertion was removed.

An initial PostgreSQL probe hit lazy-loading `MissingGreenlet` while serializing
the fixture. The fixture query was corrected to eager-load the patient, matching
normal service reads; the appointment-ID assertions were unchanged on rerun.

Reproduction files and executed-command logs are preserved outside CI under:

```text
/home/ubuntu/dentix-task-artifacts/archive-adjacent-review-20261029/
  test_archive_adjacent_review_probe.py
  test_archive_adjacent_review_pg_probe.py
  sqlite-probes.log
  postgres-probe.log
  README.md
```

Other inspected boundaries: SQL foreign-key validation, staff identity mapping,
price snapshots and price-list deactivation, stock-reference writers, attachment
metadata, legacy JSON omissions, workflow definitions and observation data.
Price-list deactivation retains its row, so it does not itself reproduce the
deleted-reference defect. Anatomical canal/root identifiers are not database
row IDs. This is a focused review, not a claim that every clinic dataset or
external Google/storage state has been tested.

## Status at the original review

Review requested by the user: completed. Overall backup repair: **PARTIAL**,
with the four findings above unaddressed. No push, PR, merge or deployment was
performed. Resolve these scenarios and convert the diagnostic reproductions to
successful behavior regressions before treating the candidate as ready to ship.
