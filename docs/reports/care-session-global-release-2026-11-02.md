<!-- CLASSIFICATION: ACTIVE -->
# Unified sessions: general availability

Startup recovery follow-up: a deployed table-owning NOBYPASSRLS login cannot run the global data migration under forced RLS. See [preflight credential selection and real-role verification](session-release-preflight-rls-recovery-2026-11-02.md). The release migration remains unchanged; live recovery is pending deployment of that correction.

Status: DONE for implementation and local verification. Remote CI, merge, deployment and deployed acceptance remain pending. The owner clarified that session recording is a general feature for every clinic; a manual opt-in for the affected clinic is not the intended product policy.

## Result

New data migration `d3e4f5a6b7c8`, following `c2d3e4f5a6b7`, registers or updates `clinical_vnext_native_writes` to globally enabled with 100% rollout. All pre-existing overrides for that exact key become enabled once. Existing clinics with no override, previously disabled clinics and future clinics therefore receive native sessions on the deployment that applies this revision.

Fresh databases use metadata bootstrap followed by an Alembic head stamp, so historical data migrations do not run there. Preflight now registers the same enabled global flag during fresh bootstrap. `ON CONFLICT DO NOTHING` preserves administrative decisions if bootstrap recovery runs after configuration has been changed.

This does not make the API ignore its rollout gate. Future deliberate administrative opt-outs still work and are not reset on ordinary restarts or already-current deployments. Existing server RBAC, patient visibility and tenant scoping remain enforced. No other feature, financial rollout flag, clinical history, schema or applied migration is modified.

The release migration deliberately updates all existing clinics' native-session overrides, including false overrides. This is the owner's requested replacement of the former opt-in policy. Operators who require an emergency stop after release can use the existing administrative flag/rollout controls.

## Migration execution and rollback

Use the deployment's configured privileged migration owner. PostgreSQL `SET LOCAL row_security = off` does not grant a bypass; it makes PostgreSQL reject the migration if RLS would silently filter the overrides. Runtime RLS policies and roles are unchanged. The change runs transactionally and the revision records its one-time execution.

The migration has no schema to reverse. Its downgrade intentionally keeps current configuration, including later administrative stops, rather than disabling every clinic or trying to reconstruct configuration that may since have changed. Operational rollback uses existing administrative controls; take the normal deployment database snapshot before production migration. No deployment or live configuration mutation was performed during this task.

## Executed verification

Both following selections exited 0: **81 passed, zero failed, zero skipped**. PostgreSQL ran on disposable local test databases under a synthetic migration owner, not on a clinic's runtime database.

```text
PYTHONPATH=. TEST_DATABASE_URL=<local-postgres-owner-url> .venv/bin/pytest backend/tests/test_care_session_global_activation.py backend/tests/test_preflight_postgres_contract.py::test_preflight_bootstraps_fresh_database_then_upgrades_existing backend/tests/test_preflight_postgres_contract.py::test_preflight_resumes_interrupted_fresh_bootstrap backend/tests/test_care_session_feature_discovery.py backend/tests/services/test_clinical_rollout_hardening.py backend/tests/test_rbac.py -o addopts='' -q --tb=short --show-capture=no
31 passed

PYTHONPATH=. TEST_DATABASE_URL=<preflight-initialized-local-postgres-owner-url> .venv/bin/pytest backend/tests/test_migrations_lineage.py backend/tests/test_clinical_core_schema.py backend/tests/test_clinical_charges_schema.py backend/tests/test_session_mode_migration.py backend/tests/test_production_startup_contract.py -o addopts='' -q --tb=short --show-capture=no
50 passed
```

Coverage includes absent/disabled global flags, pre-existing true/false clinic overrides, clinics with no override, future-clinic inheritance through `FeatureFlagService`, unchanged clinical narrative and finance flags, no-repeat activation on current deployments, preserved later opt-outs, downgrade policy, fresh/resumable PostgreSQL bootstrap, API discovery/save agreement, existing administrative rollback/RBAC and live PostgreSQL clinical guards.

The new activation regression failed before implementation both for missing and disabled flag rows; fresh PostgreSQL bootstrap also failed the new enabled-default assertion. Subsequent migration checks exposed two partial SQLite fixtures that stamped historical revisions without their pre-existing feature tables. The fixtures now supply those tables; all original data/upgrade/downgrade assertions remain. Head assertions were advanced by one revision while retaining the full prior ancestry. An initial live-guard run pointed at the empty maintenance database; its final run used a separate preflight-initialized test database and passed unchanged.

Targeted Ruff and `git diff --check` passed. Existing dependency deprecation warnings remain. No frontend code changed in this follow-up; the prior commit's 42 UI/i18n tests, ESLint, production/PWA build and guardrails remain recorded in the availability report, without claiming a redundant rerun here.

## PR #346 CI fixture follow-up

The [Backend Tests + Security run](https://github.com/Dentix-hub/dentix/actions/runs/41501311139/job/125469343081) reported three failures, 1,761 passes and one existing refresh-token TestClient skip; coverage reached 80.05%. All three failures were `no such table: feature_flags` in the inventory/session-link lifecycle, inventory legacy-row invariance and lab/work-item lifecycle tests. They stamp historical revisions on partial SQLite databases and then upgrade to current head without supplying their pre-existing feature configuration tables.

The same three tests reproduced the exact failure locally before the fix. The shared `legacy_clinical_schema` fixture now supplies both existing feature tables, without seeding flag data or replacing any new schema/data migration. The session-mode test uses that shared prerequisite instead of creating the tables twice. Production code, rollout migration, CI configuration and original assertions remain unchanged.

```text
PYTHONPATH=. .venv/bin/pytest backend/tests/services/test_inventory_care_session_migration.py backend/tests/services/test_inventory_migration_invariance.py backend/tests/services/test_lab_order_work_item_migration.py backend/tests/test_session_mode_migration.py backend/tests/test_migrations_lineage.py -o addopts='' -q --tb=short --show-capture=no
19 passed, zero failures/skips; exit 0

.venv/bin/ruff check --config ruff.toml backend/tests/conftest.py backend/tests/test_session_mode_migration.py
All checks passed; exit 0
git diff --check
exit 0
```

Fresh GitHub CI and deployed acceptance remain pending; the prior failed CI run is not reported as green.

## Staging acceptance (under 15 minutes)

1. Apply the normal staging deployment/preflight as the migration owner. Verify head `d3e4f5a6b7c8` and native global state enabled/100%.
2. Open two existing synthetic clinics, including one that previously had a false native-session override. Their authenticated `/api/v1/settings/features` must include `clinical_vnext_native_writes` without clinic-by-clinic activation.
3. In each clinic, record a session with notes and multiple canal lengths/file sizes/tapers. Confirm one visit with the correct data in that clinic's history. Confirm reception still cannot perform clinical writes and foreign-clinic patient IDs remain inaccessible.
4. Create a new synthetic clinic and verify it inherits session availability without an override. Existing clinical records and finance feature settings must be unchanged.
5. If testing emergency rollback, disable only a synthetic clinic through existing admin controls, confirm writes are rejected, and verify an ordinary restart does not re-enable it. Restore its desired setting explicitly afterward.
