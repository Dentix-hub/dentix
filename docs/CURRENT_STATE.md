# DENTIX Finance V2 — Current State

Update this file at every phase checkpoint. Do not use chat history as the source of execution state.

## Current phase

`RELEASE_HARDENING` — `PARTIAL`

Finance V2 implementation is present on `integration/final-consolidation`. The integrated code has passed the automated merge-candidate gate against the current `main`; applicable manual release-gate checks remain outstanding and must not be represented as verified without evidence.

## Implementation status

- Phases 0 through 10: implementation present.
- Finance V2 has been consolidated with the latest production CI/deployment lineage and the native Dentix Agent Stack.
- Automated post-consolidation verification: **PASSED** on PR #8 merge candidate for integration head `a6c9748`.
- Manual UX / i18n / accessibility / responsive release verification: **PENDING**.

## Post-consolidation automated evidence

GitHub Actions run #450 tested PR #8's merge candidate (`b931888`) against the then-current `main` and passed all four CI jobs:

- **Frontend Tests — PASS**
  - `npm ci`: PASS.
  - Production Vite/PWA build: PASS (`built in 10.31s`).
  - 20 discovered frontend test files: all PASS.
  - `frontend/src/tests/api.test.js`: 13/13 PASS, including R6 forgot/reset/verify password-reset API contract coverage.
- **Backend Tests + Security — PASS**
  - Pytest: 278 passed, 1 skipped.
  - Backend coverage: 54.25% (required gate: 52%).
  - Financial truth/activity/payroll/RBAC/tenant-isolation tests: PASS.
  - Bandit: PASS with no blocking high-severity findings.
  - Safety: PASS with 0 vulnerabilities reported for Python dependencies.
- **E2E Critical Path (Playwright) — PASS**
  - Isolated E2E setup: 1 passed.
  - Production critical path: 1 passed.
- **Validate / Publish Production Container — PASS**
  - Production Compose validation: PASS.
  - Pull-request production image build and revision validation: PASS.
  - Publish/deploy steps correctly skipped because the event was a pull request.

A subsequent repository-hygiene commit removes the malformed legacy `scripts/deployment/.hf-deploy-staging` gitlink that produced checkout cleanup warnings. The current PR head must therefore complete its newly triggered CI run before merge; the evidence above remains valid for the product code and the prior merge candidate, but the final head must also be green.

## Current integrated-branch changes

- Finance V2 was cherry-picked after resolving five semantic conflicts.
- The native Dentix Agent Stack was cherry-picked on top of Finance V2.
- `frontend/src/tests/api.test.js` retains the newer CI-compatible test baseline and restores R6 password-reset API contract coverage.
- The malformed `.hf-deploy-staging` gitlink was removed; `.gitignore` already ignores `.hf-deploy-*/` staging artifacts.
- `docs/GLOBAL_RELEASE_GATE.md` remains authoritative for unchecked manual UX, i18n, accessibility, and responsive items.

## Remaining blockers before merge to `main`

1. Final CI run on the current PR head must be green after the repository-hygiene/documentation commits.
2. Applicable manual release-gate items for desktop/mobile, Arabic/English, accessibility, and responsive behavior remain unchecked unless separately evidenced.
3. Frontend dependency installation currently reports 23 npm audit findings (1 low, 4 moderate, 17 high, 1 critical). The Finance/Agent consolidation did not change `frontend/package.json` or `frontend/package-lock.json`, so these findings are pre-existing rather than introduced by this PR; they require a separate dependency-security remediation rather than an unreviewed `npm audit fix --force`.
4. External Vercel checks are currently failing because of Vercel build-rate limits, not because the GitHub production build failed.

## External integration note

Repository code search contains no CodeRabbit configuration after Agent Stack normalization, but GitHub still reports a successful `CodeRabbit` external status check. That indicates the GitHub App/integration remains connected outside the repository files and must be disconnected in repository/organization integration settings if complete CodeRabbit removal is required.

## Known decisions / contracts produced during execution

- Metric glossary, formulas, API mappings, dead methods, and RBAC matrix: `docs/FINANCE_METRIC_CONTRACT.md`.
- Automated backend financial truth tests: `backend/tests/test_financial_truth.py`.
- Route tree shell (`/finance/*`) + `/billing` backward compatibility redirect in `frontend/src/App.jsx`.
- Shared foundation primitives in `frontend/src/features/finance/` (`Money`, `ScopeBadge`, `MetricCard`, `DateRangePicker`, `FilterBar`, `DataTable`, `queryKeys`, `useFinancePermissions`).
- Overview V2: `HeadlineMetrics`, `ObligationsSection`, `FinancialTrendChart`, `RecentActivityPreview`, `OverviewPage`.
- Payments V2: `usePayments`, `PaymentDetailDrawer`, `RecordPaymentModal`, `PaymentsPage`.
- Patient Accounts V2: `usePatientAccounts`, `PatientStatementDrawer`, `PatientAccountsPage`.
- Expenses V2: `useExpenses`, `AddExpenseDrawer`, `DeleteExpenseModal`, `ExpensesPage`.
- Doctor Compensation V2: `useDoctorCompensation`, `useDoctorDetails`, `DoctorCompensationEquation`, `DoctorSettingsDrawer`, `DoctorCompensationPage`, `DoctorDetailPage`.
- Payroll V2: `usePayroll`, `MonthPicker`, `SalaryPaymentDrawer`, `StaffSettingsDrawer`, `PayrollPage`.
- Financial Activity V2: `useFinancialActivity`, `ActivityTypeBadge`, `ActivityPage`.
- Reports V2: `useReports`, report view components, `ReportsPage`.
- Legacy Billing redirect: `frontend/src/pages/Billing.jsx` and `frontend/src/App.jsx`.

## Release rule

Do not change this document to `COMPLETED` / `VERIFIED` merely because automated CI is green. Only mark applicable manual release-gate items verified when evidence exists. Any remaining unchecked applicable item keeps the release state `PARTIAL`.

## Next allowed action

Wait for the current PR-head CI run to complete. If it is green, perform/accept the remaining manual release-gate review before converting PR #8 from draft and merging to `main`.
