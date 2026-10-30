# Pre-production authentication PR-A evidence

Base: staging `0c412782`; branch: `fix/new-user-login`. No remote delivery authorized.

## Reproduction

A detached baseline worktree ran ten targeted HTTP cases: five admin registrations
followed by login, and five existing users (with email) followed by login.
Result: **9 failed, 1 passed**, pytest exit 1. Registration failed in all five
cases on `users.email NOT NULL`. For existing rows, trailing space, `أحمد`,
`فاطمة`, and `مصطفى` failed login; mixed case passed. Synthetic users only.

## Approved schema and compatibility

Revision `1e2f3a4b5c6d`, parent `0d1e2f3a4b5c`, makes `users.email` nullable.
PostgreSQL ALTER preserves the existing unique index. SQLite uses Alembic batch
alteration. Downgrade checks for NULLs first and raises a clear error without
changing data. No existing production users are rewritten. Empty/whitespace-only
emails normalize to NULL through the ORM validator, including import/create/update.

Login messages, five-attempt lockout, tenant/RLS bootstrap and JWT contents are
unchanged. Only the identity SQL expression changes. New test users have zero
failed attempts and no lockout. Production account lockouts were not inspected.

## User.email audit

| Site | Before | After |
| --- | --- | --- |
| `models/user.py:User.email` | required string | optional string, trim and blank-to-NULL validator |
| `crud/auth.py:create_user` | email dropped | email preserved from schema |
| `crud/auth.py:get_user_by_email` | unconditional `.lower()` | absent/blank guard; trimmed case-insensitive lookup |
| `crud/auth.py:get_user`, `services/auth_bootstrap.py:_identity_stmt` | asymmetric stored identity normalization | explicit non-NULL email + shared SQL normalization |
| `routers/users.py:register_user` | no email input | optional JSON email, duplicate check |
| `routers/users.py:update_user_me` | truthy values only | explicit field can clear email; duplicate check |
| `routers/users.py:update_user` | no duplicate email check | duplicate check; ORM blank-to-NULL normalization |
| `routers/auth/security.py:setup_2fa` | email as TOTP account name | email or username |
| `routers/system_admin.py:update_super_admin_profile` | blank ignored | explicit field can clear; uniqueness checked only for non-empty email |
| `services/admin_service.py:global_search` | literal `None` in subtitle | empty display fallback |
| `routers/support.py:create_feedback` | queued email even when absent | stores feedback, queues delivery only with an address |

Reviewed without unnecessary changes: login response dictionaries (three paths),
`security_service.py`, admin tenant/user responses, and AI admin dictionaries
serialize None as JSON null; search `User.email.ilike(...)` safely excludes NULL;
system-admin display already guards `.split`; password-reset EmailStr requests
match actual addresses only, and retain the same generic response for no match.

The existing super-admin profile test now sends `{}` for a truly empty update;
its rejection assertion remains. A separate test verifies the newly approved
explicit blank-email clear behavior.

## Verification

- `pytest` on `test_new_user_login.py`, `test_optional_user_email.py`,
  `test_migrations_lineage.py`, `test_2fa_route_contract.py`,
  `test_users_me_standardized.py`, `test_users_admin_boundary.py`, and
  `test_super_admin_profile.py`: **37 passed**, exit 0.
- `vitest run src/api/admin.subscriptionPayments.test.js`: **2 passed**, exit 0.
- Targeted Ruff and `git diff --check`: exit 0.
- Disposable PostgreSQL: production preflight exit 0; real Alembic upgrade from
  previous head, two NULL user inserts, rejection of duplicate non-NULL email,
  guarded downgrade rejection, successful downgrade after removal of synthetic
  NULL rows, and re-upgrade all passed; indexes unchanged. Disposable DB/role removed.
- SQLite test executes migration up/down/up, multiple NULLs, duplicate rejection,
  NOT NULL restoration, and unique-index preservation.
- An earlier targeted invocation passed assertions but exited 134 during ddtrace
  shutdown. The final invocation used unbuffered Python with tracing/telemetry
  disabled and returned exit 0. No application tracing configuration changed.

No production database, email delivery, or deployed-client checks were performed.
The report CLI prints counts only; matching username tuples remain internal.

## Plan-level findings and targeted follow-up

The single combined full run found six migration-test failures introduced by the
new head: two pinned-head expectations and four partial SQLite fixtures that
reached head without a `users` table. Fixtures now include a legacy NOT NULL
email column and unique index; pinned-head checks assert the new revision and
its parent while retaining every old lineage assertion. No domain/data assertions
were removed, relaxed or skipped. The migration still fails on a truly missing
production users table and still refuses unsafe downgrade.

Targeted recheck of the five affected migration test files plus optional-email
and lineage tests: **61 passed, 1 skipped**, exit 0. The sole skip is the existing
live PostgreSQL clinical-trigger test; this recheck uses SQLite. The full suite
was not repeated, as requested.

Manual staging path after approval (under 15 minutes):
1. As clinic admin, add two users without email, including `أحمد` or `فاطمة`.
2. Log in with the typed usernames and passwords; confirm no lockout.
3. Verify JSON registration preserves full name and patient visibility mode.
4. Add a user with email, reject a duplicate, then clear the address on update.
5. Set up TOTP for a no-email account; confirm the QR account label is its username.

Rollback: revert application changes if needed. Schema downgrade requires all
NULL addresses to be resolved with valid unique addresses first; never invent
addresses or delete accounts just to make downgrade run.

## Final full validation before PR-A delivery

At Eslam's explicit request, PR-B was rebased onto PR-A and the documented
registration line was reconciled. The entire backend and Vitest suites were
executed again on combined revision `f873f6abc845e2f92dbbaac48e8438e11aa9b9e5`,
sequentially to avoid resource contention, followed by ESLint and Vite build:

- Full backend: **1431 passed, 0 failed, 4 skipped**, exit 0.
- Full Vitest: **988 passed, 0 failed, 0 skipped; 151 files passed**, exit 0.
- Full ESLint: **0 errors, 0 warnings**, exit 0.
- Vite production build: **PASS**, exit 0.

The four existing backend skips are the refresh-flow TestClient limitation,
one PostgreSQL clinical-trigger test and two PostgreSQL preflight tests.
No tests/assertions/timeouts were weakened and no new skips were added. The
earlier full run's failures and targeted rechecks remain recorded above and in
the PR-B report; the green result here comes from new complete suite runs.
Only PR-A remote delivery is approved. PR-B remains local; no merge is authorized.
