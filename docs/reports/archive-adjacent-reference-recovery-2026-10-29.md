# Recovery of the four adjacent archive reference defects

The four findings in `archive-adjacent-reference-review-2026-10-29.md` are
resolved locally on `fix/archive-learning-procedure-history`, together with
the original deleted-procedure learning fix. No live clinic database, backup,
Google account or encryption key was accessed or rewritten.

## Implemented behavior

1. Native session events now explicitly map session/appointment/provider,
   resume, step, observation, next-visit request, doctor and material IDs.
   `usage_ids` is validated and remapped element by element, including nested
   material entries. Unknown fields ending in `_id`/`_ids` remain rejected.
2. Scheduler-generated `[APPOINTMENT:<id>]` tokens are validated against the
   archived appointment's tenant and patient. Restore defers and remaps these
   tokens after ID allocation, preserving all other note text. Ordinary
   numbers and anatomical canal/root identifiers are not rewritten.
3. Missing treatment IDs in inventory history qualify only with bounded
   evidence: fully netted same-tenant stock use/reversal groups, or a complete
   finite calculation from a closed material session whose material/stock/
   batch ownership matches. Incomplete, active, inconsistent or foreign-owner
   snapshots do not qualify. This evidence never authorizes clinical event
   references or live SQL foreign keys.
4. Existing lab-generated clinical history can retain absent treatment IDs
   only in the same patient/procedure-work-item context, with matching
   canonical code and identical generated `Link:LabOrder:<id>` provenance on
   both the event and work item. Those notes are immutable historical text,
   not operational lab links. This recovers old direct-deletion archives
   without inventing cancellation events or recreating treatment rows.
5. Future lab-order deletion, through both the service and router, uses the
   established treatment deletion path with `commit=False`. Stock reversals,
   usage cleanup, clinical cancellation and order deletion share one caller
   transaction. Both `TREATMENT` and `TREATMENT_MATERIALS` stock references
   are reversed. Existing paid-order, visibility and permission guards remain.
   The authenticated actor is passed through by the router; internal/system
   callers retain a nullable actor and explicit tenant audit attribution.
6. The real PostgreSQL scheduling workflow exposed an async lazy-load failure
   after refreshing a newly created request. Scheduling now explicitly loads
   its patient relationship before returning the response.

Historical treatments continue using reserved sequence values with no inserted
treatment rows. The new evidence is included in both preflight and import,
so repeated export/restore cycles cannot bind history to newly allocated live
IDs. No schema, migration, archive envelope, clinical rollout or financial
calculation change is included.

## Executed final verification

All commands used the existing `/home/ubuntu/dentix/.venv/` environment.
PostgreSQL tests used a disposable database migrated to `e2b3c4d5e6f7`, with
the restricted app role and the separate existing system role for synthetic
seed data. No assertion in an existing test was changed.

```text
python -m pytest backend/tests/test_archive_adjacent_recovery.py backend/tests/test_archive_deleted_treatments.py backend/tests/test_archive_learning_history.py backend/tests/test_tenant_archive.py backend/tests/test_tenant_backup_api.py backend/tests/test_backup_restore_fk.py backend/tests/test_backup_disconnect_scope.py backend/tests/test_rbac.py backend/tests/services/test_treatment_service.py backend/tests/services/test_lab_service.py backend/tests/test_lab_finance_linkage_audit.py backend/tests/test_lab_debt_l1.py backend/tests/services/test_care_session_service.py backend/tests/services/test_care_session_appointment_integration.py backend/tests/services/test_care_session_material_consumption.py backend/tests/services/test_care_session_resume_and_rct_scenario.py -q --tb=short --show-capture=no --disable-warnings -o log_level=WARNING
PASS: 214 passed, 0 failed, 0 skipped; exit 0.

python -m pytest backend/ci_tests/test_tenant_archive_restore_pg.py backend/ci_tests/test_restore_transaction_gate_pg.py backend/ci_tests/test_tenant_data_operations_rls.py backend/ci_tests/test_drive_backup_operations_pg.py backend/ci_tests/test_treatment_lab_atomic_pg.py backend/ci_tests/test_cross_tenant_http_postgres.py -q --tb=short --show-capture=no --disable-warnings --confcutdir=backend/ci_tests
PASS: 15 passed, 0 failed, 0 skipped; exit 0.

ruff check --config ruff.toml backend
PASS: All checks passed; exit 0.
git diff --check
PASS; exit 0.
```

The PostgreSQL regression performs real start/step/observation/material-use/
finish/resume/request/scheduling operations, followed by two encrypted preview,
confirmation and restore cycles using old/current supported schema headers.
It checks event and list IDs, restored appointment tokens, unchanged stock,
usage cost, commissions and credentials, absent historical treatment rows,
and request reopening after cancelling the restored appointment. Existing
coverage also exercises other-tenant collisions, live FK rejection and rollback.

New local regressions cover both lab deletion entry points, existing legacy
lab history, and a fault after treatment deletion but before order deletion.
Rolling back that fault restores both objects and the original clinical event;
there is no intermediate commit. Negative cases reject incomplete reversals,
wrong tenant/material/patient, malformed snapshots, missing targets and unknown
reference types. The earlier diagnostic probes remain separately preserved
as review evidence; they are not used as successful functionality tests.

Full suites were not repeated; CI remains the integration authority. Existing
deprecation/tracer warnings did not fail the final commands.

## Final pre-delivery review

The cumulative diff was reviewed against the current staging head `94769aa`.
No schema, CI or governance file changed, and no existing test assertion was
weakened. A new regression reproduced an overly strict historical-snapshot
check: the learning writer can retain zero-weight distribution entries while
another entry gives the calculation a positive total. The recognition rule now
permits finite non-negative entry weights while still requiring a positive
total and rejecting the existing negative-weight/incomplete-evidence cases.

After this correction the final commands above were rerun: 214 backend tests
and 15 PostgreSQL tests passed with real exit 0. An initial PostgreSQL rerun
collided with fixed tenant fixture IDs in the previously used disposable
database. A fresh disposable database was migrated to the existing head and
the entire 15-test gate passed without changing any assertion or deleting
old fixture data. Targeted test counts are functionality evidence; CI owns
coverage acceptance. No remaining actionable blocker was found in this review.

## Remaining delivery boundary

Local implementation, review and targeted verification: **DONE**. PR delivery
is authorized; deployment and affected-clinic acceptance remain pending. After delivery
and deployment, download and preview a fresh same-clinic `.dentix` archive,
preview the previously failing encrypted file, and trigger one manual Drive
backup. A confirmed restore on real clinic data is a separate destructive action
and is not required for download/preview acceptance.

Recovery still fails closed for genuinely corrupt data without the supported
evidence above. It never silently drops history, repairs balances or guesses
another patient's or clinic's operational relationships.
