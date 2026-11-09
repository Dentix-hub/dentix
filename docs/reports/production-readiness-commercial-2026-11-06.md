# Commercial production-readiness review — 2026-11-06

**Verdict: PARTIAL; current deployed candidate is NOT approved for main or paid launch.**

Scope: production `b567150629af5c4499f085b341f6800f3d03a38f` versus integrated staging `a34d2820488281c834502f203480c1ffcaa7e961`. Their direct tree diff has 360 files: 186 runtime/config, 90 tests, 64 documentation/governance, 20 generated/public artifacts. Git's triple-dot diff is much larger because the branches have divergent promotion history; it must not be confused with the actual production tree delta. This review inventories that boundary and records concrete blockers from its commercial/security execution paths. It is not an unconditional sign-off on every changed line or a substitute for owner clinical/browser acceptance.

The local correction branch starts at the exact staging candidate. No production connection, production mutation, migration edit, workflow change, enforcement-mode change, merge, deployment or remote delivery was performed for these corrections.

## Verified runtime evidence

- Exact staging revision has successful `Dentix CD - HF staging smoke`, [run 42216787853](https://github.com/Dentix-hub/dentix/actions/runs/42216787853). Its staging sync, revision/health verification and production-like browser smoke succeeded; production jobs were skipped.
- Previously approved Staging catalog initialization created plans 6/7/8 with 200/400/1000 EGP, 2/5/15 accounts and 2/10/30 AI units. Trial policy is Professional/14 days. Legacy plans and tenant-contract hashes were preserved; audit records 1423/1424 identify the connected administrative database actor honestly.
- A separate synthetic clinic was created through the real public registration route, followed by login: HTTP 201/200. It received Professional plan 7, trial status and a 14-day period. No patient or financial transaction was created by this probe.
- Authenticated self-tenant diagnostics reported `enforcement_mode=off`, `is_shadow=true`. This is actual deployed configuration, not a guessed repository default. The task did not change it.
- One logical synthetic nonclinical `/api/v1/ai/query` returned HTTP 200 with `success=false`, `error=internal_server_error`. Own-clinic diagnostic log showed PostgreSQL RLS rejecting INSERT into `ai_quota_windows`; no reservation existed. This failure happened before provider execution. **Real provider availability remains UNVERIFIED**, rather than being described as failed or passed based on this upstream failure.
- The live failure also returned SQL/parameters in the client error message. Only the synthetic clinic's diagnostic log was inspected, using an explicit tenant restriction. No real patient content was accessed.

## Spec axis

| ID | Severity / requirement | Evidence and impact | Local correction / acceptance |
|---|---|---|---|
| S01 | HIGH — approved downgrade becomes effective at renewal, after explicit seat reduction | `backend/routers/admin_tenants.py::assign_plan_to_tenant` previously replaced plan_id immediately while preserving an unexpired period. Reproduced on real PostgreSQL with Professional -> Essential and an empty account set, proving the seat check alone did not enforce timing. An unresolved future paid assignment could also be overwritten without changing the effective future grant. | Reuse the receipt grant's shared lower-tier classification; reject early direct downgrade with 409 and direct operators to existing schedule-downgrade. Refuse conflicting unresolved future assignments, including a started future assignment awaiting worker reconciliation. Positive ordinary upgrade remains supported and preserves dates; scheduling preserves current plan/dates. |
| S02 | HIGH operational launch gate — subscription restrictions must actually govern paid usage | Authenticated deployed diagnostics report OFF. A green generic smoke does not demonstrate expired/plan-denied enforcement. Preserved legacy plans contain malformed feature metadata and zero AI limits; globally enabling enforcement without inventory/reconciliation can interrupt those contracts. | No automatic mode flip or legacy repricing/mapping. Owner-reviewed cohort/catalog inventory and deployed enforcement acceptance remain required before selling controlled plans. |

## Standards axis

| ID | Severity / invariant | Evidence and impact | Local correction / regression |
|---|---|---|---|
| T01 | HIGH — server authorization must honor persisted policy | `backend/services/commercial_ai_guard.py::async_evaluate_commercial_ai_access`: async execution fetched override rows, but iteration existed only inside the synchronous else branch. A persisted AI deny returned no denial. Quota admission checks numerical limits, not this override, so it is not a substitute barrier. | Move shared result processing outside the branch. Real PostgreSQL proves deny/allow/inherit/expired/foreign-tenant behavior agrees with the synchronous guard. Direct analysis denial precedes reservation and provider boundaries. |
| T02 | HIGH — functional tenant-scoped database access with RLS intact | `backend/services/ai_quota_service.py` opened fresh plain isolated sessions without tenant binding. Live Staging and a local NOBYPASSRLS role with FORCE RLS reproduced the same quota-window INSERT failure. This was a fail-closed availability failure, not demonstrated cross-tenant disclosure. | Bind the existing `rls.tenant_id` contract on each isolated session transaction, including commits executed through run_sync. Validate the requested tenant against authenticated/session context; explicitly propagate tenant to finalization and synchronous Scribe accounting. No bypass role or RLS policy change. Restricted-role tests cover async reserve/finalize, synchronous reserve/release, foreign-tenant denial and pooled connection cleanup. |
| T03 | MEDIUM — client errors must protect internal details | `backend/services/ai_service.py::process_query` interpolated exceptions into the response. The live synthetic failure exposed SQL and parameters. `analyze_direct` also returned raw provider exceptions. | Preserve server logging/error codes while using generic client messages. Synthetic error tests cover both public service paths; direct-analysis regression failed before the correction. |
| T04 | MEDIUM — audit records must describe actual prior state | `schedule_tenant_downgrade` assigned the target before constructing old_value, so the audit claimed the new target was the old value. | Capture the previous ID before mutation. Regression verifies the first schedule records `scheduled_downgrade=None` while current contract/dates remain unchanged. |

**Finding count: Spec 2 (worst HIGH); Standards 4 (worst HIGH).** S01 and T01–T04 are corrected locally, not deployed. S02 remains an explicit operational launch gate.

## Correction boundary and compatibility

- Patient/clinical visibility algorithms, money arithmetic, approved prices, trial length, quota counting semantics and clinical-history exceptions are unchanged.
- Direct plan assignment now refuses policy-invalid operations instead of silently granting an early downgrade or conflicting future grant. The UI shows the existing server reason; authorized upgrades retain their route/response and dates.
- The RLS binding uses SET LOCAL, per-session transaction listeners and parameterized tenant values. It never sets a bypass switch, changes a database role, commits caller clinical work or leaves tenant settings on a pooled connection. Synchronous Scribe and async chat/analysis use the same accounting boundary.
- No production schema/migration is added. Local integration fixtures create and remove disposable schemas and restricted roles in an explicit test database; they are not hosted migrations.
- Existing static graph navigation is stale: it was used only to locate subscription/auth/tool entry points. All findings above were confirmed against the candidate source and executable probes, not graph line numbers or historical issues.

## Verification and evidence

Artifacts live outside Git under `/home/ubuntu/dentix-task-artifacts/promotion-review-20261106/`. They contain synthetic evidence, no real patient data. Generated synthetic credentials are private (0600), outside Git, and are not part of a bundle or this report.

- Red: persisted deny allowed (`ai-policy-red.log`); denied request reached reservation (`provider-boundary-red.log`); early downgrade succeeded (`downgrade-red.log`); restricted-role RLS INSERT failed (`accounting-rls-red.log`); direct error returned private detail (`analysis-error-red.log`).
- Backend final focused: **67 passed, 0 failed, 0 skipped**, exit 0, including **13 new PostgreSQL regressions**. Independent existing RBAC/AI-finance gate: **27 passed**, exit 0. Results are in `focused-final.xml/.log/.exit` and `security-baseline.log/.exit`. Overlapping intermediate runs are not added as unique tests.
- Frontend four-file tenant/admin gate: **11 passed**, exit 0, in `frontend.log/.exit`; build/PWA/marketing passed, exit 0, in `build.log/.exit`. Changed backend Ruff, changed frontend ESLint and whitespace checks also passed.
- PostgreSQL integration here used local PostgreSQL 14. Hosted failure was observed on PostgreSQL 17. Exact integrated-candidate CI and deployed retest remain necessary; local success is not relabeled as hosted success.
- The full unchanged application suites were not rerun merely to repeat passed candidate CI. These are focused corrective tests; fresh sensitive-change PR CI is still required.

## Staging acceptance after correction integration

1. Require current correction head to pass authoritative PR CI; integrate through staging only, then require the exact integrated revision's CD/smoke success.
2. Reuse the synthetic release-probe clinic and the same logical nonclinical AI probe. Confirm successful genuine provider response, no demo response, one accounting unit and stable replay. Initial attempt never reached the provider; do not create a second receipt or manipulate ledger rows to make the retry pass.
3. Super Admin: apply/revoke a synthetic-clinic AI deny and verify provider is not invoked while denied. Keep existing reception balances/payment recording permissions unchanged.
4. Super Admin: attempt early lower-plan assignment (409), schedule it with active accounts within cap, verify current plan/dates unchanged, and verify audit old/new state. Inspect a normal upgrade and future-paid-trial behavior.
5. Use an explicitly approved isolated enforcement acceptance setup for active/grace/expired/read-only states. Verify new mutations deny when required and authorized clinical history remains readable. Do not edit real clinic dates as a clock test or globally flip mode across legacy contracts blindly.

## Production preparation — no authorization to apply

1. Obtain authorized production read-only catalog, schema/Alembic head, app/system/owner role-contract and commercial-mode inventory. Never infer production from the separate Staging database.
2. Prepare and verify a production backup before applying pending migrations. The direct production delta includes eight historical migration files, covering care workflow/activation as well as commercial policy/lifecycle/AI tables and RLS/parent triggers. None were edited by this correction.
3. Review required production catalog/trial setup against actual rows. The setup command must preserve all existing contracts and reject conflicting named/default plans; new code does not copy Staging records or initialize a populated legacy catalog automatically. If future trial configuration is absent, account for signup availability during the authorized rollout.
4. Record owner Super Admin/clinical acceptance, bounded real-provider evidence and cumulative promotion review against the final corrected integrated tree. Current findings prohibit a blanket production approval.
5. Only after explicit promotion authorization, use the repository-approved staging -> main path (or its documented tree-identical reconciliation if required by history). Verify both production frontend routing and backend health after release. Git ancestry divergence alone was not reported as a proven merge conflict.

No online payment gateway, patient/storage cap, shipped Flutter refresh or unimplemented advanced tier capability is certified by this work.
