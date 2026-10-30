# Material learning history and archive recovery

## Reproduced symptom and causes

The supplied staging screenshot reports HTTP 400 at
`material_learning_logs.calculation_data.learning_updates.procedure_id`.
PR #324 (merged as `94769aa`) covered deleted **treatments**, but a learning
calculation also contains catalogue **procedure** IDs as JSON object keys.

`crud.procedure.delete_procedure` deletes the tenant-owned catalogue row and
its live price/weight rules, while intentionally retaining material-learning
audit logs. A regression using that real deletion path failed before this fix
with the exact screenshot error. This is evidence for a supported reproduction;
the affected clinic database and backup were not accessed.

A second cause was verified on disposable PostgreSQL: the procedures tenant RLS
policy hides `tenant_id IS NULL` global catalogue entries. The previous shared
reference resolver used that restricted connection, so even valid global IDs
could be rejected or misclassified as absent. The resolver now reads **only IDs
of NULL-owner procedures** through the existing isolated system connection.
Clinic-owned procedures never enter that allowlist. No RLS policy is changed.

## Recovery rules and review boundaries

- Only canonical positive PostgreSQL integer keys with finite `old`, `observed`
  and `new` calculation values qualify as learning snapshots. Unknown fields,
  invalid keys, booleans, non-numeric values and infinities are rejected.
- Export and preview preserve complete snapshots. Missing catalogue IDs are
  historical within this audit field only. They cannot authorize a live SQL
  foreign key, a weight rule, a price-list item or a clinical event reference.
- Restore remaps live tenant procedures and independently verified global IDs
  normally. For absent snapshot procedures it reserves fresh sequence values
  without inserting procedure rows, preserving the calculation values and
  preventing accidental links to another clinic, restored data or future IDs.
- Repeated restore/export cycles remain valid. Sequence gaps are expected, as
  for the existing deleted-treatment mechanism; allocation failures roll back.
- No schema/migration, envelope version, encryption key, authentication rule,
  financial calculation or learning algorithm changes are included.
- The PostgreSQL regression generates a real learning log using a synthetic
  privileged legacy connection, including global entries, then uses restricted
  tenant connections for deletion/export/preview/restore. Current learning
  service visibility of global templates under tenant RLS is pre-existing
  behavior outside this archive change; no assertion was removed to hide it.
- Legacy JSON downloads omit learning/weight tables. Their existing rejection
  when those tables contain live data remains covered, preventing data loss.

## Verification

Final commands used the existing `/home/ubuntu/dentix/.venv/bin/python`
environment, with PostgreSQL tests on a disposable database migrated to the
existing head `e2b3c4d5e6f7` and the restricted `dentix_ci_app` role:

```text
python -m pytest backend/tests/test_archive_learning_history.py backend/tests/test_archive_deleted_treatments.py backend/tests/test_tenant_archive.py backend/tests/test_tenant_backup_api.py backend/tests/test_backup_restore_fk.py backend/tests/test_backup_disconnect_scope.py backend/tests/test_rbac.py -q --tb=short --show-capture=no --disable-warnings -o log_level=WARNING
PASS: 81 passed, 0 failed, 0 skipped (exit 0)

python -m pytest backend/ci_tests/test_tenant_archive_restore_pg.py backend/ci_tests/test_restore_transaction_gate_pg.py backend/ci_tests/test_tenant_data_operations_rls.py backend/ci_tests/test_drive_backup_operations_pg.py -q --tb=short --show-capture=no --disable-warnings --confcutdir=backend/ci_tests
PASS: 12 passed, 0 failed, 0 skipped (exit 0)

ruff check --config ruff.toml backend/services/tenant_archive_embedded_refs.py backend/services/tenant_archive_import.py backend/services/tenant_restore_coordinator.py backend/tests/test_archive_learning_history.py backend/ci_tests/test_tenant_archive_restore_pg.py
PASS: All checks passed (exit 0)
git diff --check
PASS (exit 0)
```

Full suites were not repeated; CI remains the integration authority. Existing
deprecation/tracer warnings did not fail either command. Targeted PostgreSQL
coverage includes two complete encrypted
preview/confirm/restore cycles using old/current supported schema headers,
unmodified calculation values, live and global reference remapping, an old ID
occupied by another tenant, future ID allocation, unchanged live weights,
credentials/commissions, global read-only behavior, rollback and tenant gates.

The new PostgreSQL test lives in the existing `test_tenant_archive_restore_pg.py`
file already selected by CI. Existing test assertions and CI files are unchanged.

## Staging acceptance after delivery and deployment

1. On the affected clinic, download an encrypted `.dentix` archive and confirm
   the screenshot error no longer appears.
2. Preview that downloaded file; verify record counts and staff mapping.
3. Preview the previously failing encrypted same-clinic archive with its original
   keys as well, if available.
4. Trigger one manual Drive backup and verify its operation completes.

These checks do not require confirming a restore on real clinic data. A live
restore is a separate destructive operation requiring explicit authorization.
