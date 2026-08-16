# DENTIX Finance V2 — Current State

Update this file at every phase checkpoint. Do not use chat history as the source of execution state.

## Current phase

`RELEASE_HARDENING` — `PARTIAL`

Finance V2 implementation is present on `integration/final-consolidation`, but the integrated branch must not be treated as production-verified until its current build/tests, GitHub CI, and applicable manual release-gate checks pass after consolidation with the latest `main` and Agent Stack changes.

## Implementation status

- Phases 0 through 10: implementation present.
- Historical pre-consolidation verification evidence exists in the implementation ledger and phase documents.
- Post-consolidation production verification: **IN PROGRESS**.

## Current integrated-branch evidence

- Finance V2 was cherry-picked onto the latest `main` after resolving five semantic conflicts.
- The native Dentix Agent Stack was then cherry-picked on top of Finance V2.
- `frontend/src/tests/api.test.js` retains the current CI-compatible test baseline and restores the R6 forgot/reset/verify password-reset API contract coverage.
- The release checklist in `docs/GLOBAL_RELEASE_GATE.md` remains authoritative for any unchecked manual UX, i18n, accessibility, and responsive items.

## Active blockers before merge to `main`

1. Run the current integrated branch through GitHub Actions CI.
2. Confirm frontend production build and frontend test suite pass on the integrated branch.
3. Confirm backend/security and critical E2E jobs pass on the integrated branch.
4. Complete or explicitly leave unchecked the applicable manual release-gate items for desktop/mobile, Arabic/English, accessibility, and responsive behavior.
5. Update verification counts and release evidence only from the integrated branch results; do not reuse stale pre-consolidation counts as final release proof.

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

## Historical verification note

Previous Finance-only execution reported green frontend/backend tests before this consolidation. Those results are useful historical evidence, but they are **not** the final release proof for `integration/final-consolidation` because the branch now includes the latest `main`, conflict resolutions, and Agent Stack commits.

## Next allowed action

Open a pull request from `integration/final-consolidation` to `main`, run the full CI gate on the exact integrated head, fix any failures on the integration branch, then update the release documents with the resulting evidence before merge.
