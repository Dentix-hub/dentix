# Deleted treatment history and archive recovery

## Failure reproduced

`TreatmentService.delete_treatment` calls `_sync_clinical_work_item_delete`, which
cancels the work item and appends a `procedure_cancelled` event with
`action=deleted`, `superseded=true`, `status=cancelled` and the old treatment ID.
It deliberately preserves the preceding clinical events. The billing CRUD then
hard-deletes the treatment. Stock reversals and material-learning calculations
also retain serialized treatment references.

The archive validator treated every serialized treatment reference as a live
foreign key. An ordinary create/project/delete/export sequence therefore raised
`clinical_events.payload.treatment_id`, matching the staging symptom. A new
regression executed this real deletion path and failed before the fix.

## Recovery rules

- An absent treatment is recognized as historical only when an explicit deletion
  event witnesses it for an existing procedure work item and patient of the same
  tenant. A cancellation caused by an unmapped procedure is not deletion evidence.
- Clinical events may use that evidence only within the matching patient/work-item
  context. Stock and material-learning history may refer to the witnessed deleted
  treatment. Other missing references and all SQL foreign keys remain subject to
  their existing validation; no fictitious treatment rows are introduced.
- Export preserves the original event payloads and archive column/envelope format.
  Existing encrypted archives and the legacy JSON adapter use the same rules.
- Restore regenerates live IDs as before. After live insertion, it reserves fresh
  values from the treatment sequence for historical references, without inserting
  treatment rows. Only serialized history uses this separate mapping. These
  references remain absent and cannot accidentally name another clinic's treatment,
  a restored live treatment, or the next normally created treatment.
- Sequence gaps are expected, including after a rolled-back restore, just as for
  ordinary PostgreSQL inserts. This does not create or change business records.
- No schema/migration, permission, financial calculation, live data, encryption-key
  or Google configuration change is required.

## Executed verification

- Pre-fix regression: actual treatment projection/deletion followed by export
  failed with the reported reference error.
- Targeted backend gate: **104 passed**, including archive/API, treatment and
  clinical-charge services, rollback, RBAC and the new regression/rejection cases.
- Restricted-role PostgreSQL gate: **11 passed** across archive restore, restore
  locking, tenant-operation isolation and Drive backup operation files.
- The new PostgreSQL test performs encrypted preview, confirmation and transactional
  restore twice, using supported old/current schema-revision headers. It verifies
  retained events, stock reversals and learning history, normal live treatment and
  charge remapping, unchanged amounts/commissions/credentials, another tenant with
  a colliding historical ID, future ID allocation and a second export/restore.
- The real legacy JSON export/adapter also passes preview after deletion.
- Invalid IDs/types, absent deletion proof, wrong patient/tenant evidence and live
  SQL foreign keys to missing treatments remain rejected.

All databases and records used here were disposable/synthetic. The affected live
clinic database and its backup were not accessed. The reproduced supported deletion
workflow establishes the defect and regression coverage; live staging acceptance
still requires deployment followed by a same-clinic download and preview.

## Staging acceptance

1. Download a fresh encrypted archive from the affected clinic.
2. Select it for restore preview and confirm that counts and staff mapping appear.
3. Preview the previously failing same-clinic file as well, retaining its keys.
4. Verify ordinary image access and other clinic workflows. Confirmed restore of
   live data is a separate data-replacement action; it is not needed to test preview.
