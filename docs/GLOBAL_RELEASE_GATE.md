# Finance V2 — Global Release Gate

This file is a release-level checklist. It does not replace per-phase verification.

## Product clarity
- [ ] Owner can identify collected, expenses, current balances, and compensation obligations quickly.
- [ ] Metric scopes are explicit.
- [ ] Production and collections are visually and semantically distinct.

## Correctness
- [x] Headline metrics have backend-owned definitions. Evidence: `backend/routers/accounting.py` and `backend/tests/test_financial_truth.py`.
- [x] Doctor due is consistent across list/detail/report. Evidence: shared `AccountingService` calculations and financial truth tests.
- [x] Lab cost handling is tested against double counting. Evidence: `backend/tests/test_financial_truth.py`.
- [x] Outstanding semantics are documented. Evidence: `docs/FINANCE_METRIC_CONTRACT.md`.

## Architecture
- [x] Old Billing monolith no longer owns all Finance data.
- [x] Each route loads only necessary data. Evidence: bounded per-source financial activity queries.
- [x] React Query targeted invalidation is implemented.
- [x] Large lists are server paginated. Evidence: patient and expense response contracts plus full-page report retrieval tests.

## UX
- [ ] Desktop and mobile workflows are intentionally designed.
- [ ] Long workflows use routes; short workflows use sheets/drawers.
- [ ] Filters persist via URL where appropriate.
- [ ] Empty/loading/error states are implemented.

## Permissions
- [x] FINANCIAL_READ behavior is tested.
- [x] FINANCIAL_WRITE behavior is tested.
- [x] SYSTEM_CONFIG actions are gated.
- [x] Doctor/receptionist visibility scenarios are tested.

## Internationalization
- [ ] Arabic RTL is visually audited.
- [ ] English LTR is visually audited.
- [ ] Money formatting is centralized.
- [ ] Date formatting is centralized.
- [ ] Mixed Arabic/Latin names and numbers are tested.

## Accessibility
- [ ] Keyboard navigation works.
- [ ] Visible focus is present.
- [ ] Contrast passes target.
- [ ] Icon buttons are labeled.
- [ ] Financial meaning does not depend on color.
- [ ] Mobile/reflow does not require unnecessary horizontal scrolling.

## Regression
- [x] Existing financial writes still work. Evidence: full backend and frontend regression suites.
- [x] Existing patient data is untouched.
- [x] Existing tenant isolation is preserved. Evidence: tenant isolation and financial truth tests.
- [x] Existing backend business rules remain unless intentionally corrected and tested.
- [x] Legacy links redirect safely.

## Release rule

Finance V2 is not `DONE` until every applicable item above has evidence and all release-target phase gates pass.
