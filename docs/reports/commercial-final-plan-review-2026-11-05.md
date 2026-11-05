# Commercial controls — final code review and staging handoff

**Code delivery: pending the final verification below. Commercial launch: PARTIAL.** This review covers the cumulative commercial-completion branch against staging `c4c7eb5998039bdadffc23bff31f65d0464d091b`. It does not certify production, an uninspected staging database, or a real AI provider. The owner authorized GitHub delivery to staging; merge, deployment and promotion remain separate decisions.

## Approved scope

The November 3 commercial-controls plan and subsequent owner decisions require capacity-first plans: Essential 200 EGP / 2 active login accounts / 2 AI requests per clinic-local day; Professional 400 / 5 / 10; Business 1000 / 15 / 30. Accepted capabilities are shared. Billing is a calendar month; trial is Professional / 14 days / no card; paid grace is seven days and unpaid trial has none. Preserve trial remainder, account/clinical/financial history and security disables. Lower-tier activation requires explicit seat reduction and takes effect at renewal. Collection is manual; do not advertise a live gateway, patient/storage caps, portal, branches, telehealth or custom domains.

The original planning artifact is `/home/ubuntu/dentix-task-artifacts/DENTIX-commercial-controls-plan-2026-11-03.md`. Its PR-01–PR-11 requirements are mapped below so this handoff can be reviewed on GitHub without treating earlier “100% complete” messages as evidence.

## Final review: Spec axis

These defects were reproduced before correction. Each is closed by code and regression tests, subject to normal PR CI and staging acceptance.

| ID / severity | Requirement and confirmed defect | Correction and evidence |
|---|---|---|
| F01 HIGH | PR-04 persisted tenant deny must affect actual access. `async_resolve_restrictions_and_overrides` read nonexistent `is_enabled`, caught the exception and discarded the real `override_value` policy. A stored clinical deny still allowed direct patient creation. | Read allow/deny/inherit, canonicalize keys, retain expiry and tenant scope. `backend/services/entitlement_service.py`; `test_commercial_final_review.py::test_persisted_clinical_deny_blocks_direct_patient_api` and stored allow/deny/expiry test. |
| F02 HIGH | PR-09 emergency stop must remain hard in OFF/OBSERVE. Both the decision engine and adapter write flags could mask it. | Emergency decisions deny in every mode; flags follow canonical decisions. Direct POST denies while authorized patient GET still succeeds in all three modes. `commercial_decision.py`, `entitlement_service.py`; parametrized emergency API/flag tests. |
| F03 HIGH | PR-02 unknown/missing plan and rollout denial must not create enforced rights. Adapter write flags could remain true despite the canonical denial. | Clinical/billing/appointment and operational flags derive from actual decisions. Clinical rollout does not disable independent billing. `test_enforced_write_flags_follow_canonical_decision`; shadow-mode regression preserves ordinary observation semantics. |
| F04 MEDIUM | PR-04 preserve explicit false feature values and reject string truthiness. Saving an object policy converted it to an array and could interpret malformed values as enabled. | Strict true checks for recognized and custom keys; editing an object retains explicit false values, legacy arrays remain compatible. `planFeatureUtils.js`, PlansManager; `planFeatureUtils.test.js`. |
| F05 HIGH | PR-06 task 11 / PR-11 task 2 require amount and exact before/after periods before confirmation. Manual receipt previously wrote immediately. | Read-only Super Admin preview runs the same grant against a detached projection, returns amount/current/future dates, and binds a five-minute quote to tenant/target-plan state. Commit rechecks state/cap under the tenant lock. Preview fields are excluded from durable receipt fingerprints, preserving retries. No new storage. `SubscriptionService`, `admin_subscriptions.py`, `FinancePage`; `test_subscription_payment_preview.py`, FinancePage confirmation/reload tests. |
| F06 MEDIUM | A required price-impact preview must not silently fall through to saving when its request fails. | Keep the form and refuse save on preview failure. PlansManager regression proves the mutation callback is not called. |
| F07 HIGH | PR-11 task 5 prohibits delete-to-undo financial history. Subscription receipt DELETE still removed the row, leaving renewal replay pointing at a missing receipt. | Retain guarded route and missing-record 404, refuse finalized receipt deletion with 409, remove the destructive clinic-subscription receipt button. No new refund behavior is invented. PostgreSQL test verifies receipt, period and retry survive the attempted delete. This intentionally supersedes the old UI test that expected destructive receipt deletion; replacement asserts preservation, not a weakened financial check. |
| F08 HIGH | PR-06/PR-11 also apply to the older manual-extension adapter. Its browser generated a new key on every retry and did not preview, making a lost response capable of granting a second extension. | Add read-only preview to the existing guarded renewal adapter, reuse canonical grant/state quote logic, preserve identity across retry/reload, and require a documented reason for the new quoted support-extension flow. The UI distinguishes free support days from paid calendar-month collection. `subscription_renewal_service.py`, TenantsPage; PostgreSQL preview/replay test and `TenantsPageRenewal.test.jsx`. Legacy unquoted dated/day API adapters stay compatible and audited; they are not presented as paid receipts. |

## Final review: Standards axis

| ID / severity | Invariant and confirmed defect | Correction and evidence |
|---|---|---|
| T01 HIGH | AGENTS.md §2 server authorization and clinical integrity: emergency/override lookup exceptions silently became an empty policy, allowing new operations. A PostgreSQL query error can also poison subsequent history reads in the same transaction. | Fail closed for new capabilities. Each real async policy read has a savepoint so a failed SELECT does not abort the history transaction. SQLite fault tests and actual PostgreSQL invalid-cast injections prove denial plus a usable subsequent tenant-scoped read. `test_commercial_final_review.py::test_postgres_policy_failure_does_not_poison_history_transaction`. |

**Finding count: Spec 8 (worst HIGH), Standards 1 (worst HIGH); all nine corrected locally.** No unresolved reproduced code finding from this final pass is intentionally hidden as a runtime-only item.

## Whole-plan coverage and remaining acceptance

“Implemented/tested” below refers to local source and executed automated evidence. It does not mean a capability was observed deployed. All database examples are synthetic; no patient content appears in this report.

| Card | Local implementation / automated evidence | Remaining acceptance |
|---|---|---|
| PR-01 AI authorization | Canonical patient visibility, stale session/confirmation checks, clinic-wide AI_CHAT AND REPORT_READ; `test_pr01_f1_ai_patient_visibility.py`, `test_pr01_f2_financial_authorization.py`, `test_pr01_stale_session_context.py`. Valid-plan fixtures retain their security assertions. | Owner browser/API check on deployed candidate; real provider transport separately. |
| PR-02 decision engine | `commercial_registry.py`, `commercial_decision.py`, `entitlement_service.py`, request-time `subscription_period.py`; `test_commercial_decision_pr02.py`, new direct-API emergency/override/missing-plan tests. | Actual deployed enforcement mode and rollout configuration. |
| PR-03 diagnostics | `entitlement_diagnostics_service.py`; typed authoritative seat and AI ledger snapshot, read-only window inspection; `test_commercial_diagnostics_pr03.py`, `test_commercial_plan_completion.py`. | Compare displayed values with authorized staging read-only configuration. |
| PR-04 audited policy | SubscriptionService, commercial override/action services, plan revision checks and real override loading; `test_commercial_policy_pr04.py`, `test_commercial_completion.py`, final stored-policy tests. | Owner verifies saved policy, audit and immediate effective access on synthetic staging clinic. |
| PR-05 seats | `account_admission_service.py`, account create/reactivate adapters, pending lower-cap admission; `test_account_admission_pr05.py`, PostgreSQL completion tests. No automatic user deletion/disable. | Deployed app-role admission/activation smoke and actual assigned caps. |
| PR-06 lifecycle | Shared detached/noncommitting grant, calendar anchor, paid-in-trial resolver, manual receipt replay, safe scheduled lower plan, canonical worker and registration trial policy; lifecycle/calendar/webhook/completion/payment-preview tests. | Actual trial setting and synthetic registration, manual collection, future assignment and history smoke. |
| PR-07 AI accounting | `ai_quota_service.py`; tenant lock, reservation ledger, clinic-local window, stable actor/operation fingerprint, consumed/reserved/uncertain states; `test_ai_accounting_pr07.py`, actual PostgreSQL concurrent acquisition tests. | Exact deployed migration/RLS/config and shared budget smoke. |
| PR-08 provider/tool integration | Chat, direct analysis, financial analysis and Scribe adapters; deterministic no-provider release, server-owned child linkage, normalized tool allowlist enforced in executor and discovery; `test_ai_provider_integration_pr08.py`, completion/PR-01/executor/confirmation tests. | Bounded authorized non-PII live-provider test. Provider mocks establish authorization/accounting, not model availability. |
| PR-09A/B/C business enforcement | Clinical/appointment, finance/export, inventory/lab/backup gates, history exceptions and backup exclusions; `test_clinical_appointments_pr09a.py`, `test_financial_commercial_pr09b.py`, `test_operations_commercial_pr09c.py`, subscription lockout and final policy tests. | Synthetic deployed route/workflow checks under ENFORCE and existing history visibility. |
| PR-10 clients | Canonical entitlement snapshot/navigation, AI remaining/reset state, no plan-name grant fallback, approved marketing and maintained PWA; `pr10CommercialFrontendConsistency.test.jsx`, AIChatQuota and SEO tests. Flutter remains frozen by the approved plan; no new shipped-mobile support claim. | Candidate-revision browser/PWA/offline/error checks; no unsupported mobile promise. |
| PR-11 Super Admin | Catalog/trial/emergency/override/reconciliation/tool controls; causal audit undo; manual payment quote and immutable receipts. Valid retired contracts and security disable remain preserved. Launch acceptance, completion and new preview tests. | Actual catalog/config inventory, explicitly approved tenant mapping, owner acceptance and exact-revision CI/CD smoke. |

No fresh migration/schema change, plan seeding into live databases, bulk clinic mapping, production record mutation or real-provider spending is performed here. Existing valid retired contracts stay valid. OFF/OBSERVE is diagnostic rollout, never evidence that paid enforcement is enabled.

## Executed verification

The first delivery full pass found one existing grace unit fixture with no linked plan expecting an allowed write. This is the fail-open behavior F03 removes. Its positive grace assertions are unchanged; it now supplies a valid plan, and a new paired grace/missing-plan regression asserts denial. The initial frontend full run had 1,201 passes and one i18n parity test timeout at five seconds while build/tests competed for resources; isolated i18n passed without changing its timeout/assertions. Final command results and source boundaries are recorded below after execution. Logs/JUnit/coverage live outside Git in `/home/ubuntu/dentix-task-artifacts/plan-recheck-20261105/`. Overlapping suites are not added together. Earlier full results and their exact code boundary remain in `commercial-plan-gap-fixes-2026-11-05.md`.

## Owner staging path (under 15 minutes, synthetic data)

1. Check exact deployed revision, commercial mode and real catalog/caps. Read diagnostics and reconciliation inventory; do not run a seed or bulk mapping as a check.
2. In Finance, select a synthetic clinic/plan. Preview amount and current/future dates. Cancel once: no receipt or period change. Confirm once, replay the same interrupted operation and verify one receipt/one period; finalized receipts offer no Delete action.
3. Open clinic detail and check trial remainder/future assignment, seats, daily AI consumed/reserved/uncertain/remaining and reset time. Use prearranged isolated fixtures for time boundaries rather than altering live dates.
4. Save a clinical deny with a reason. Direct synthetic creation must deny; previously authorized history must read. Reset to inherit and verify the normal role workflow resumes.
5. Preview/save emergency stop and verify affected new work denies; lifting it must not grant unrelated RBAC access or reactivate a security-disabled clinic.
6. Attempt lower-plan selection with too many active accounts: reject without deleting/disabling anyone. Explicitly reduce synthetic accounts, then verify the accepted future plan/end before payment confirmation.
7. Inspect the same action in audit and test a permitted nonfinancial reversal. A superseded action must conflict. Refund/correction remains a separate financial operation.
8. Inspect reconciliation selections and changed plan tools; unselected/valid/retired clinics remain untouched. A disabled tool must deny before its handler/provider.

## Manual collection and recovery procedure

Before charging, confirm the actual clinic, target plan, amount/currency, payer, collection date, receipt reference and reason in the form/notes. Preview before committing. The application retains the operation identity across interrupted attempts in the same browser session/reload without storing form PII. Retry that same operation after a lost response; never invent a new receipt to test whether the first succeeded. If browser operation identity is unavailable, inspect recorded receipts/audit first and reconcile through support before submitting a distinct new operation. A changed real receipt is a new deliberate transaction. A stale/expired quote requires a fresh preview. A final receipt is immutable; refunds and financial corrections need their separately approved process and must not be simulated with DELETE, date edits, archive restore or generic policy undo. Never remove clinical history to resolve a seat/cap/payment problem.

## Remaining launch gates — UNVERIFIED until actually executed

- Authorized read-only current staging plan/trial/override/mode inventory, including legacy/null/zero/orphan records, followed by owner-approved mappings/cohort activation where needed.
- CI, migration/RLS checks and CD health/browser smoke on the exact integrated staging revision. Local PostgreSQL tests do not certify hosted database roles/settings.
- Owner staging acceptance, bounded authorized synthetic live-provider smoke and credential/model availability. No real patient data may be sent for this check.
- Cumulative stronger-model main...staging review and explicit owner approval before any later promotion. This feature-branch review is not that cumulative production gate.
- A feature is marketed only after its own deployed acceptance; advanced excluded features and online checkout remain deferred.

**Prioritized handoff:** review and integrate this code through staging first; then verify actual catalog/enforcement and owner workflows; then provider and release gates. Do not open paid sales or promote to main solely because local/CI tests pass.
