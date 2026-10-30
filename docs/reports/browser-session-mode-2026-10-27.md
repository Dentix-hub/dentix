# Browser session mode — implementation handoff (2026-10-27)

Status: PARTIAL. Independent re-review remains pending. No PR, push, merge or deployment was authorized. Base staging: `94eb964`; branch: `feat/browser-session-mode`. Migration parent `1e2f3a4b5c6d`, head `ed137fa8c304`. The relaxed password policy branch remains unmerged and was not copied.

Before: login issued persistent cookies for every client, session rows used a fixed seven days, and the login/registration password controls had no visibility button. Static analysis established those facts. The new optional form field `remember_me` defaults to true for old clients; the web sends false by default. The mode is stored per session and carried in the signed 2FA token and through refresh rotation. Session cookies omit persistence attributes; persistent cookies use configured refresh lifetime (access cookie uses configured access lifetime). JWT expiry is used for the DB row. Native token response remains available. Closing a tab does not log out; browser session restoration may restore session cookies.

Tests detect the old always-persistent behavior on login, 2FA and rotation, including a forged refresh preference; existing adversarial tests cover logout, session isolation, and password-reset revocation. Login, registration and reset visibility controls have component checks. PostgreSQL fresh bootstrap uses the repository preflight; the isolated additive migration was also applied to a synthetic prior table and retained `true` for the old row. A raw upgrade from a completely empty DB failed at the historical inventory migration because core tables do not exist; the repository's preflight explicitly documents and handles this baseline.

Verification (all commands exit 0 unless noted):
- `timeout -s SIGABRT 90 .venv/bin/python -X faulthandler -m pytest -o addopts='' -q backend/tests/test_remember_me.py backend/tests/test_auth_hardened.py backend/tests/test_security_phase4.py`: 13 passed; 16 warnings, no skips.
- `timeout 90 .venv/bin/python -m pytest -o addopts='' -q backend/tests/test_auth_adversarial_phase6.py`: 9 passed, 16 warnings, no skips.
- PostgreSQL `DATABASE_URL='postgresql://dentix_ci_app@/dentix_full_test?host=/tmp&port=55432' SYSTEM_DATABASE_URL='postgresql://dentix_ci_system@/dentix_full_test?host=/tmp&port=55432' timeout 90 .venv/bin/python -m pytest -o addopts='' -q backend/ci_tests/test_auth_cookie_flow_http.py`: 4 passed, 15 warnings, no skips. Roles were synthetic NOBYPASSRLS app and BYPASSRLS system.
- `npm test -- --run src/tests/Login.test.jsx src/tests/RegisterClinic.visibility.test.jsx src/tests/reset_password.test.jsx`: 12 passed, no skips.
- `npm test -- --run src/tests/reset_password.test.jsx src/tests/api.test.js src/tests/AuthProvider.loginLifecycle.test.jsx`: 19 passed, no skips (before the final visibility assertion was added; the final three-file run above covers it).
- Targeted ESLint and Ruff: exit 0; `git diff --check`: exit 0.
- `alembic heads`: one head. PostgreSQL synthetic migration upgrade and fresh preflight: exit 0. Raw historical upgrade on empty DB: exit 1 as explained above.
- Earlier sandbox TestClient runs timed out (exit 124); stack showed the request waiting in the Starlette/AnyIO portal. Outside the prior socket restrictions the tests passed. ddtrace emitted a logging error at shutdown despite exit 0; no assertion was disabled.

Staging path (under 15 minutes): (1) log in without remember-me, reload and verify access, then close and reopen the browser with session restoration setting recorded; (2) log out and repeat with remember-me checked; (3) check 2FA login and refresh if available; (4) verify eye controls on login, registration and reset, keyboard focus and mobile layout. Chromium restart behavior was tested as described in the correction evidence below; the full staging UI click path remains pending.

Rollback: the older server does not understand stored mode and could convert a session cookie to persistent upon refresh; do not roll back to it while non-persistent sessions exist. Retain a compatible reader/refresh implementation or revoke affected sessions as an explicitly approved operational action. No backup formats changed.

Remaining plan: PR-2 requires PR-1 and the approved password-policy slice merged; later slices require their specified merged predecessors. No SMTP/Google live checks have been performed. Cumulative review, staging acceptance, and the remaining slices are pending.

## Independent review corrections

The independent review of `287be42` requested changes. The FORCE RLS 2FA lookup and provider splash defect predated this slice; the seven lineage/fixture failures were introduced by the new migration head. The 2FA endpoint now uses the audited, tenant-rebinding bootstrap after validating the signed pending scope, and rechecks active user, lockout, tenant, and 2FA enrollment. Old signed pending tokens remain compatible. An additional PostgreSQL test exposed a pre-existing flaw: pending tokens could access ordinary endpoints. The normal authentication dependency now explicitly rejects this scope. AuthProvider keeps the login component mounted while credentials and TOTP are in flight, and only shows global loading once a completed authentication starts tenant initialization. Historical fixtures now include pre-migration sessions or remove the new column before stamping; all earlier lineage and domain assertions remain.

Correction checks:
- `timeout 120 .venv/bin/python -m pytest -o addopts='' -q --tb=short backend/tests/test_migrations_lineage.py backend/tests/test_clinical_charges_schema.py backend/tests/test_clinical_core_schema.py backend/tests/services/test_inventory_migration_invariance.py backend/tests/services/test_inventory_care_session_migration.py backend/tests/services/test_lab_order_work_item_migration.py backend/tests/test_session_mode_migration.py`: 55 passed, 1 skipped, exit 0. The existing skip requires a PostgreSQL DATABASE_URL for live trigger behavior.
- `timeout 90 .venv/bin/python -m pytest -o addopts='' -q --tb=short backend/tests/test_remember_me.py backend/tests/test_auth_hardened.py backend/tests/test_auth_adversarial_phase6.py backend/tests/test_security_phase4.py`: 22 passed, exit 0.
- PostgreSQL restricted-role `backend/ci_tests/test_auth_cookie_flow_http.py`: 6 passed, 15 warnings, exit 0 after the pending-token denial fix. Both persistence modes use fresh browsers, successful TOTP, rotation, and stored session-mode assertions.
- `npm test -- --run src/tests/AuthProvider.2fa.test.jsx src/tests/AuthProvider.loginLifecycle.test.jsx src/tests/Login.test.jsx`: 16 passed, exit 0. The new test mounts the real provider and Login with delayed fake network responses.
- Targeted Ruff and ESLint: exit 0.
- Browser smoke: Playwright-launched Chromium 147.0.7727.0, headless, persistent profile, default session-restore settings, clean browser close and relaunch. A real browser sent login to a local server with synthetic PostgreSQL user: session-mode refresh cookie absent after restart; persistent-mode cookie present. This exercised HTTP cookies, not the staging UI. Session restoration enabled by a user may change the first result.

The initial browser attempt returned connection refused while the server was starting; the subsequent run passed. Local startup logged an existing restricted-role create_all ownership error before continuing; this smoke did not validate startup health as a production deployment. Independent re-review and Eslam's staging acceptance remain outstanding; no PR-2 work was started.

An intermediate PostgreSQL run after adding that denial assertion failed (4 passed, 2 failed; exit 1), proving the pre-existing token-scope flaw; the dependency correction was made afterward.
