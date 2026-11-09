<!-- CLASSIFICATION: ACTIVE -->
# Global session release: forced-RLS startup recovery

Status: DONE for implementation and local verification; CI, merge, deployment and live startup recovery remain pending. This follows merged PR #346. No live database credentials, configuration or data were modified.

## Observed failure and cause

The supplied startup log shows the database at `c2d3e4f5a6b7`. Release migration `d3e4f5a6b7c8` aborts while updating native-session overrides in `tenant_features`: PostgreSQL reports that the query would be affected by row-level security. Preflight selected the application's table-owning login, but table ownership does not bypass FORCE RLS. The earlier release tests ran the migration with privileged test credentials and did not cover this deployment combination.

The release migration's existing `SET LOCAL row_security = off` correctly fails rather than silently updating only visible clinics. It does not grant a bypass. Removing FORCE RLS or elevating the runtime login would weaken clinic isolation and is not the repair.

## Correction

Before running pending release data, preflight checks the existing login's actual BYPASSRLS/superuser status and exact table/sequence privileges. When the default application login is insufficient, it selects an already-configured same-database privileged connection, such as `SYSTEM_DATABASE_URL`. Alembic receives that connection explicitly; `DATABASE_URL` remains the application's runtime connection.

The single data-only release skips the unrelated role-grant/ownership preparation path. A connection with sufficient DML privileges can execute the release without owning the schema, becoming the application role or granting privileged membership to the application. Older pending DDL additionally requires inherited table-owner capabilities. Existing NOINHERIT owner membership can be used transactionally to read version bookkeeping without granting new rights.

Explicit `MIGRATION_DATABASE_URL`/`OWNER_DATABASE_URL` settings retain precedence. If explicitly configured credentials cannot execute the release, or no suitable same-database administrative login exists, preflight stops before any migration writes with a capability/configuration error. The operator must configure those explicit URLs with an appropriately privileged migration login; this fix does not invent credentials or grant BYPASSRLS.

No applied migration, RLS policy, schema, role attribute, public endpoint or clinical/financial record was changed. Already-completed release migrations are not replayed, preserving later administrative stops.

## Executed verification

A real PostgreSQL reproduction first transferred all table ownership to a NOBYPASSRLS application login, supplied a separate BYPASSRLS system login with only release DML/sequence privileges, and verified that public preflight still returned failure before the repair. After the repair the same topology successfully reaches `d3e4f5a6b7c8` and activates both synthetic clinics.

```text
PYTHONPATH=. TEST_DATABASE_URL=<local-disposable-postgres-admin-url> .venv/bin/pytest backend/tests/test_preflight_global_release_rls.py backend/tests/test_preflight_postgres_contract.py backend/tests/test_care_session_global_activation.py backend/tests/test_production_startup_contract.py backend/tests/test_preflight_restore_write_gates.py backend/tests/test_rbac.py -o addopts='' -q --tb=short --show-capture=no
42 passed, zero failed/skipped; exit 0

.venv/bin/ruff check --config ruff.toml backend/scripts/preflight_migrations.py backend/tests/test_preflight_global_release_rls.py backend/tests/test_care_session_global_activation.py
All checks passed; exit 0
git diff --check
exit 0
```

Five new real-role cases cover a working administrative login, missing login, another database, insufficient table privilege, and an explicit unsuitable owner URL. Every case verifies that the application stays NOBYPASSRLS/non-superuser, gains no system-role membership, retains table ownership, and cannot read or update another clinic. Successful release checks both overrides and revision; rejected cases retain the old revision and flag values. Existing fresh/resumable bootstrap, NOINHERIT repair, rollback, history/finance preservation and RBAC checks also pass.

Running these contracts together exposed a fixture leaking a previous database's selected migration-role environment variable into an independent activation test database. The activation fixture now clears that unrelated role before its own Alembic commands; no assertions were relaxed. Existing dependency deprecation warnings remain. All test databases and synthetic roles were disposable; no production snapshot or PII was used.

## Deployment acceptance (under 15 minutes)

1. Deploy through the existing authorized workflow with the normal database snapshot. Confirm configured migration/system credentials target the same database. If explicit migration/owner URLs are set, they must carry the required privileges; an application-only login is insufficient for this global data change.
2. For the reported default-login case, expect preflight to log selection of the configured privileged source for the pending global release. It must complete and verify head `d3e4f5a6b7c8`, then start the application.
3. Verify native sessions are enabled for two synthetic clinics, including a former opt-out, and record one multi-canal session in each. Confirm their clinical data remains separated.
4. Verify runtime application role attributes and forced tenant-feature RLS remain unchanged. Do not disable RLS or grant privileged membership to the runtime login to recover startup.
5. Repeat normal startup after the release is applied and confirm no activation replay. CI success and live recovery must be recorded separately; neither is claimed by these local results.
