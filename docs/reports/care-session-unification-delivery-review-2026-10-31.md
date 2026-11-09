<!-- CLASSIFICATION: ACTIVE -->
# Care-session workflow: delivery review, 2026-10-31

Historical review of the earlier partial delivery. Current requirement accounting and verification are maintained in [the scope-closure review](care-session-plan-completion-2026-11-01.md).

Branch: `feat/care-session-workflow-unification`, based on staging `0036704`.
Delivery scope: the implemented workflow and its regression fixes. The overall original initiative is **PARTIAL**.
CI and manual staging acceptance remain pending; this is not a production promotion review.

## Implemented scope inspected

| Area | Delivered behavior |
| --- | --- |
| Procedure status | Inline completion/reopening from treatment history; permission enforcement, optimistic versions, required correction/override reasons, pending-charge handling and invoiced-charge review warnings. |
| Multiple visits/procedures | Explicit procedure associations, procedure-scoped continuation, repeated step identities, aggregate progress and multi-procedure resume. |
| Visit history | Expandable clinical visits and actual visit dates; historical-entry backend support. Historical-entry UI remains incomplete. |
| Drafts | Server persistence, version conflicts, finish-sheet integration and protection against late recovery/save/discard crossing patient contexts. |
| Measurements | Append-only correction values, reference-chain resolution and independent DTO projections that keep effective type, tooth, canal/root/surface, notes and value consistent. |
| Follow-up | Stop, postpone, resume and doctor handoff, with server-side permissions and UI integration. |
| Recovery | Explicit archive coverage, clinical provenance and procedure-list ID remapping, stored-value exports independent of ORM projections. |

## Additional delivery-review findings fixed

1. **CRITICAL:** Fresh metadata bootstrap retained permissive package RLS policies on the two new tables. A restricted `NOBYPASSRLS` role could set `rls.bypass_rls=true` and read both clinics. Fresh bootstrap now installs canonical strict policies; migration `c2d3e4f5a6b7` removes all old policies before reinstalling strict RLS.
2. **HIGH:** Fresh bootstrap omitted four parent-tenant guards for the new tables. Bootstrap and the repair migration now install them; cross-clinic parent references are rejected even for an administrative connection.
3. **HIGH:** Restore preserved old follow-up procedure IDs and plain-integer staff/session provenance. A shared explicit reference registry now validates and remaps those columns after new IDs exist. Invalid integer/list references fail validation before replacement.
4. **HIGH:** Draft saving accepted another patient's, another clinic's or a nonexistent visit ID. Saving now verifies the visit against the current patient and tenant before mutation.
5. **MEDIUM:** The original upgrade omitted 17 indexes already declared by the models. The new additive migration brings upgrade and fresh-baseline schemas into alignment without changing existing clinical values.
6. **LOW:** Removed a duplicate test import and asserted the restored amendment value previously assigned to an unused variable.

Previously committed migrations were not edited. The repair downgrade removes its indexes while preserving strict RLS and the parent guards owned by the preceding migration.

## Verification

The final local results are recorded in the state card. PostgreSQL checks used an isolated, disposable PostgreSQL 14 cluster with synthetic data, never a clinic database.

Final gate: **211 backend passed, zero skipped**, **74 frontend passed**. Configured Ruff, ESLint, production build and both design commands exited zero. The 32-case integrity file also passed separately against a repaired former-bootstrap database.

- Backend selection: care-session unification/service/resume/appointment integration, clinical charges, tenant archive, restore gates, clinical schema, migration lineage, RBAC and `test_care_session_delivery_integrity.py`.
- The new integrity file contains 32 cases, including real PostgreSQL parent guards, restricted-role RLS, ID-changing restore, index parity and malformed-reference rejection. PostgreSQL checks execute when `TEST_DATABASE_URL` points to a preflight-initialized PostgreSQL database; otherwise those eight live cases skip explicitly.
- Fresh database initialization, staging-schema upgrade, former-bootstrap repair, and repair-migration downgrade/re-upgrade were exercised. Structural migration drift checks passed on fresh and upgraded schemas.
- Frontend selection: the ten care-session, draft, resume, status, follow-up, history and reception queue Vitest files.
- Backend quality gate: `.venv/bin/ruff check --config ruff.toml backend`.
- Frontend gates: `npm run lint`, `npm run build`, `npm run design:guardrails`, and `node scripts/check-design-system-guardrails.mjs --diff-base=origin/staging`.
- The repository-wide design inventory remains report-only with existing legacy findings; the PR diff has zero newly guarded violations.
- No live deployment URL was provided, so deployment HTTP checks and manual staging acceptance are not claimed. Full application CI remains authoritative after the PR opens.

Reproduce the backend gate with `PYTHONPATH=. .venv/bin/pytest` and these paths, followed by `-o addopts='' -q --tb=short --show-capture=no --disable-warnings`:

```text
backend/tests/services/test_care_session_workflow_unification.py
backend/tests/services/test_care_session_service.py
backend/tests/services/test_care_session_resume_and_rct_scenario.py
backend/tests/services/test_care_session_appointment_integration.py
backend/tests/services/test_clinical_charge_service.py
backend/tests/test_tenant_archive.py
backend/tests/test_preflight_restore_write_gates.py
backend/tests/test_clinical_core_schema.py
backend/tests/test_migrations_lineage.py
backend/tests/test_rbac.py
backend/tests/test_care_session_delivery_integrity.py
```

## Staging acceptance, approximately 12 minutes

Use synthetic patients and an existing test clinic with `clinical_vnext_native_writes` enabled.

1. As a doctor, open a patient with two unfinished procedures. Resume both and verify each procedure retains its own steps/template and prior measurements.
2. Complete part of one procedure, finish the visit with a next action/date, and reopen the patient. Verify visit history, remaining steps and aggregate progress; resume again without duplicating completed/skipped steps.
3. Change a procedure's status from history. Reopen it with a correction reason; check that incomplete-step completion requests require an override reason and an invoiced procedure displays the financial review warning.
4. Type finish-sheet documentation, allow autosave, close/reopen and verify recovery. Navigate to a second synthetic patient while recovery is pending; verify no documentation crosses patients.
5. In treatment history, postpone/resume a follow-up and hand it to another doctor. Verify the doctor's name and queue refresh. As reception, verify scheduling remains available while clinical management actions are hidden/denied.
6. In a disposable staging clinic, export and preview a backup containing follow-ups and corrected measurements. A restore requires the existing explicit restore confirmation; after restoring, verify procedure links and assigned doctors. Do not restore a real clinic for this smoke test.

## Original requirements still incomplete

These remain in the original scope and are not represented as deferred or complete:

1. Generic visit workspace.
2. Clinic template and custom-field editor.
3. Populated specialty template snapshots.
4. Historical-entry and correction interfaces.
5. Follow-up dashboards.
