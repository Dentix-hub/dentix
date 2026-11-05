# Commercial plan conformance fixes — 2026-11-05

Status: **DONE locally for the reported code fixes; launch/runtime acceptance remains PARTIAL.** No push, PR, merge, deployment, live subscription mutation or live-provider spending.

## Scope and baseline

Continues `fix/commercial-controls-completion` after local commit `6712872`, based on staging `c4c7eb5`. Preserves the preceding C1–C6 completion work. Closes the ten Spec findings S01–S10 and Standards finding T01 in the independent 2026-11-05 plan-conformance report. The owner's approved capacity-only commercial design is unchanged: calendar-month Essential/Professional/Business at 200/400/1000 EGP, 2/5/15 active login accounts and 2/10/30 shared clinic-local provider requests; Professional 14-day/no-card trial; paid grace seven days; no extra trial grace; no destructive downgrade.

No database model or Alembic migration changes. Existing subscription renewal idempotency storage is reused; schema additions are compatible Pydantic API fields only. No clinical/financial history rows are removed or recalculated.

## Changes by finding

| Finding | Implemented behavior | Main code / regression evidence |
|---|---|---|
| S01 duplicate manual receipt | In enforce mode the manual HTTP adapter requires a stable operation identity or receipt reference before any mutation; stable client operation key survives retry/reload without storing form notes; tenant-locked fingerprint and durable receipt replay; a reused key with another body conflicts; receipt grant cannot be repeated through the renewal adapter | SubscriptionService.record_payment; SubscriptionRenewalService; FinancePage; test_commercial_plan_completion concurrent/HTTP/cross-adapter tests; FinancePage lost-response test |
| S02 downgrade bypass | Shared grant validates target active-account cap and preserves remaining paid time; lower target becomes a future assignment, with pending seat cap retained; no automatic account disabling/deletion | subscription_grant.py; AccountAdmissionService; over-cap payment/direct-renewal and early-lower-plan tests |
| S03 paid trial lifecycle | Same-tier and different-tier purchases both have an explicit paid-start marker; one pure resolver evaluates trial/paid/grace/expiry independently of worker timing; future plan identity/caps are loaded in HTTP/AI/admission/diagnostics | subscription_period.py; CommercialDecisionEngine; EntitlementService; worker; paid-trial and future-plan regressions |
| S04 ineffective trial setting | Atomic registration reads validated saved future-signup policy; only eligible Professional references; malformed duration fails safely; approved defaults remain Professional/14/no card; existing trials untouched | auth/register.py; SubscriptionService trial policy; real admin API + registration regression |
| S05 inaccurate usage UI | Read-only authoritative ledger snapshot includes consumed/reserved/uncertain/remaining/reset/timezone; no GET creates a quota window; typed API preserves these fields; unavailable display is not zero; refresh after chat requests | AIQuotaService.read_window_usage; entitlement diagnostics/schema; AIChat/TenantDetailPanel; service/HTTP/React tests |
| S06 admin controls missing | System → Commercial controls has future trial, dedicated emergency stop, actual catalog/mode, preview and explicit selected reconciliation; clinic drawer has reason/revision/expiry/inherit/allow/deny commercial overrides; mutations refetch effective data and surface conflicts | CommercialLaunchControls; TenantCommercialOverrides; existing guarded typed endpoints; React API-contract tests |
| S07 tool list not enforced | Strict normalized list/boolean-map policy in executor in addition to domain permission and capability checks; NULL explicitly inherits the existing tool set; malformed policy denies in enforce mode; OFF/OBSERVE retain their documented shadow behavior; editor uses actual tool registry descriptions | core/ai_tool_policy.py; executor.py; PlanAIToolPolicy; denied-handler and tool-picker tests |
| S08 calendar display | New launch plans use month unit; calendar-month pricing is explicit; legacy duration metadata is separately identified and retained for compatibility | PlansManager; existing creation/edit contract tests |
| S09 end boundary | Shared period resolver uses start-inclusive/end-exclusive end/grace boundaries | subscription_period.py; exact-grace-end regression |
| S10 known non-dispatch charged | Missing Scribe client releases reservation; demo and explicit provider-free outcomes do not consume provider quota; genuine uncertain provider outcome remains conservative | ScribeService; AIService/agent metadata; no-client/demo quota regressions |
| T01 PostgreSQL renewal crash | Aware instants are normalized to UTC-naive at persistence boundaries, matching existing columns; regular asyncpg renewal persists | subscription_grant.py; same-tier PostgreSQL renewal test |

An exhausted client can still confirm/cancel a previously admitted action through explicit buttons; backend RBAC/visibility/current-policy/confirmation checks remain authoritative. Provider-free status is server-generated, never accepted from client context.

## Additional financial defect found during final review

A real registration records its signup day as billing anchor. On November 5 signup, a fourteen-day trial ends November 19; the old first-month grant reused anchor day 5 and ended December 5, truncating the paid month. An independent red probe reproduced that exact loss. Receipt and renewal now initialize the first paid anchor from the paid start (November 19), ending December 19 with grace ending December 26. Later renewals retain the paid anchor and month-end handling. Existing live periods are not guessed or silently rewritten; legacy records require authorized receipt review. Both adapters have independent hand-worked date regressions.

## Test integrity / compatibility notes

- Original independent red probes were retained outside the repository; no assertion was weakened to conceal a defect.
- PR-06's scheduled-downgrade test said "at renewal" while its clock was still twenty days before the end. Its setup now advances to the actual renewal boundary, keeping every original assignment/cap assertion. A separate regression proves that early payment preserves the current plan and schedules the lower tier.
- PR-03's test deliberately expected an unavailable ledger while PR-07 was pending. The approved plan explicitly required replacing that temporary state. Its obsolete placeholder assertions are replaced with stronger authoritative-ledger count/reset assertions, proving historical log rows do not reduce quota. Independent UI coverage retains unavailable != zero.
- Manual clients outside enforce retain their legacy adapter behavior; they must supply a stable identity/reference before use in a paid enforce cohort. Clients with an existing provider reference remain replay-safe.
- Legacy explicit-date/day manual extensions remain compatible and audited without inventing an assigned commercial plan; separate plan/permission gates are retained. A renewal cannot shorten an existing period.
- Valid retired contracts, hard security disable, RBAC, doctor visibility and clinical-history access remain independent invariants. Ambiguous legacy trial/grace records are flagged for receipt review rather than silently rewritten.

## Verification

Executed evidence is stored outside the repository at `/home/ubuntu/dentix-task-artifacts/plan-recheck-20261105/`. Counts below are overlapping gates, not numbers to sum.

| Gate | Actual result | Evidence |
|---|---|---|
| Full backend, CI coverage threshold | **1,934 passed, 1 failed, 1 skipped**, exit 1; coverage 81.78% (required 52%) | backend-full.log / backend-full.xml / coverage.xml |
| Full frontend | **1,193 passed, 1 failed** across 180 files, exit 1 | frontend-full.log |
| Final affected backend acceptance | **140 passed**, exit 0 | backend-final-acceptance.log / backend-final-focused.xml |
| Final payment/policy/lifecycle follow-up, including first-month anchor, provider-reference conflicts, missing identity and missing-policy preview | **61 passed**, exit 0 | final-policy-2.log / final-policy.xml |
| AI executor and confirmation baseline | **21 passed**, exit 0 | ai-executor-final.log |
| Final affected UI + translation resources | **36 passed** across seven files, exit 0 | frontend-final-acceptance.log |
| Trial-policy recovery UI follow-up | **8 passed**, exit 0 | trial-recovery-ui-final.log |
| Receipt lost-response + reload UI follow-up | **4 passed**, exit 0 | receipt-reload-ui.log |
| Ruff / changed-file ESLint / whitespace | PASS | ruff-final.log / eslint-final.log / git diff --check |
| Production/PWA/marketing build | PASS | frontend-build-final.log |
| Design guardrails | Legacy report completed; committed PR-diff check recorded in handoff | design-final.log / design-diff.log |

The two full-run failures were **introduced during implementation and corrected**, not called baseline passes: the new period adapter initially interpreted an unset optional MagicMock field as a timestamp, and four new AI UI translation keys were missing. The existing Super Admin regression was retained unchanged; typed optional-date handling fixed its failure. Locale resources were added without exemptions or weakened assertions. The affected acceptance/resource tests above passed after correction. Broad full suites were not rerun after those localized corrections; normal PR CI remains required before integration. The sole existing skip is `test_auth_refresh_token`: TestClient has no request.client.host for session tracking.

The final backend policy follow-up includes 28 new regression cases, using real PostgreSQL for manual receipt replay/concurrency, renewal persistence and paid-trial state. Owner-role PG tests do not claim a new deployed restricted-role RLS certification.

## Staging owner acceptance path (under 15 minutes after authorized delivery)

Use synthetic clinics/users only and verify the deployed candidate revision first.

1. System → Commercial controls: inspect actual mode and catalog prices/caps; OFF/OBSERVE is visibly not paid-launch readiness. Do not change deployment environment settings through generic browser configuration.
2. Future trial: inspect Professional/14/no-card, preview and save with reason if authorized; register a synthetic clinic and verify its end. A settings change must not move an existing trial's end.
3. Manual receipt: select clinic/plan, check amount/date/payer/reference notes before submit. Retry the same interrupted attempt; payment row and paid end must occur once. A different real receipt is a new operation, never a deletion of the old one.
4. Trial payment: check same/different tier, preserved trial remainder, future paid start and paid end. Past-end/grace tests use isolated clock-controlled acceptance; do not edit live dates as an experiment.
5. Lower plan: reduce synthetic active login accounts explicitly first; over-cap payment/renewal must refuse. An early paid lower period leaves current rights/time and shows the future assignment; no patient/history/account is deleted.
6. Clinic detail: inspect actual seats and AI consumed/reserved/uncertain/remaining/reset. Test one authorized stubbed provider request and a repeated logical operation key.
7. Commercial override: preview allow/deny/inherit with reason/optional expiry, save, refresh effective access, and inspect audit. An allow must not override RBAC, subscription state or emergency denial.
8. Emergency control: preview/save a capability restriction with reason; new affected operation denies before provider/business work, historical clinical reads remain authorized. Lifting it does not confer unrelated permissions.
9. Reconciliation: inspect inventory and preview, explicitly select synthetic unanchored clinic/target, then confirm. Valid/retired/future contracts remain preserved; stale revision must conflict.
10. Plan tools: inspect inherited tool set; exclude one test tool and confirm executor denial before handler; restore inheritance explicitly. Domain permissions remain AND.

## Remaining release gates

Local code/test success does not establish deployed runtime readiness. No actual catalog mapping, rollout enablement, production data change or provider spend is performed by this task. Before sale: authorized current staging catalog/config inventory and cohort reconciliation, exact-revision deployment smoke, PostgreSQL restricted-role/RLS evidence, bounded authorized non-PII real-provider smoke, browser/owner acceptance, documented receipt/support recovery procedure and cumulative main...staging review. No online checkout, patient/storage limits or unimplemented advanced features are advertised.

Self-review: requested Spec S01–S10 and Standards T01 addressed, plus the additional first-paid-month anchor defect. No known failing targeted test remains. This is not a claim of independent cumulative main...staging acceptance or production readiness.
