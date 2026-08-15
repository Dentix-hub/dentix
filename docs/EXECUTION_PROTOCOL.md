# DENTIX Finance V2 — Execution Protocol

## 1. Role

You are the implementation agent for an existing production application. Your job is to implement the approved Finance V2 specification **without silently changing product semantics**.

`MASTER_SPEC.md` is the product/design source of truth. The current phase file is the execution source of truth. When an execution file is more explicit about sequencing/status/evidence, follow it; when product meaning is involved, defer to `MASTER_SPEC.md`.

## 2. Before touching code

For every task batch:

1. Read the entire current phase file.
2. Read the relevant source sections listed by that phase in `MASTER_SPEC.md`.
3. Inspect the real repository and current implementation.
4. Identify exact files, routes, APIs, tests, models, permissions, and data flows involved.
5. Check dependencies in `IMPLEMENTATION_LEDGER.md`.
6. Set selected tasks to `IN_PROGRESS` before implementation.

Never assume example filenames in the plan exist unchanged. Adapt to the actual repository while preserving the specification.

## 3. Batch size

Default to **1–5 tightly related task IDs** per implementation batch. Do not consume the entire phase in one uncontrolled pass if it contains independent concerns.

A batch may be larger only when tasks are inseparable and all can be verified together.

## 4. Allowed task states

Only these states are valid:

- `NOT_STARTED`
- `IN_PROGRESS`
- `PARTIAL`
- `BLOCKED`
- `VERIFIED`

Rules:

- `PARTIAL` never counts as completion.
- `BLOCKED` must include the exact missing decision/dependency/evidence.
- `VERIFIED` requires implementation evidence **and** verification evidence.
- Never mark a requirement verified merely because code “looks correct.”

## 5. Evidence contract

Every `VERIFIED` ledger row must contain enough evidence to let a different reviewer reproduce the conclusion:

- exact changed file(s),
- relevant symbol/route/endpoint when useful,
- test/check name or command,
- result,
- any manual/visual verification required by the task.

If a test cannot be run, state that explicitly and keep the task `PARTIAL` or `BLOCKED` unless another approved verification method proves every acceptance criterion.

## 6. Financial correctness gate

Never invent or normalize financial meaning in the frontend.

When a task touches Production/Revenue, Collected, Outstanding, Expenses, Doctor due, payroll, lab cost, or Net result:

- use `FINANCE_METRIC_CONTRACT.md`,
- keep authoritative formulas backend-owned,
- preserve tenant/role visibility,
- distinguish period metrics from current/all-time balances,
- stop and mark `BLOCKED` if the actual code/data model cannot support the claimed semantic safely.

Do not “make the UI work” by manufacturing financial data.

## 7. Product capability gate

The following are **not implementation gaps** in Finance V2 unless separately approved:

- payment methods on ordinary patient payments,
- complete invoice lifecycle,
- doctor settlement/payment history,
- true double-entry ledger,
- bank reconciliation,
- refunds,
- tax/VAT accounting,
- unsupported insurance accounting,
- advanced receivables aging.

See `DO_NOT_IMPLEMENT.md`.

## 8. Architecture rules

- Do not merely restyle `Billing.jsx`.
- Do not keep the monolithic “load everything” Finance entry pattern.
- Prefer route-owned queries and targeted React Query invalidation.
- Do not duplicate authoritative doctor compensation calculations in React.
- Do not load large all-time lists to paginate them in memory when server pagination is required.
- Long financial workspaces use routes; short contextual tasks use drawers/sheets; destructive decisions use confirmations.
- Keep legacy compatibility until replacement behavior is verified.

## 9. Permissions and security

Frontend hiding is not security.

Every changed or new financial endpoint/action must preserve actual backend authorization and existing tenant/financial visibility semantics. Explicitly verify relevant scenarios for:

- FINANCIAL_READ,
- FINANCIAL_WRITE,
- SYSTEM_CONFIG,
- owner/admin,
- doctor self-scope,
- receptionist restrictions,
- wrong tenant / tenant isolation.

## 10. UI/UX verification

For applicable tasks verify:

- desktop,
- tablet where behavior changes,
- mobile,
- Arabic RTL,
- English LTR,
- loading,
- empty,
- valid zero-value,
- error/partial-error,
- keyboard/focus,
- accessible labels/meaning not color-only,
- mixed Arabic/Latin/numeric content.

Do not claim responsive/accessibility/RTL completion because the component compiles.

## 11. Required regression discipline

Before closing a phase, run all available checks relevant to the repository, including as applicable:

- backend unit/calculation tests,
- API integration tests,
- frontend unit/integration tests,
- typecheck,
- lint,
- production build,
- E2E flows,
- accessibility checks,
- visual/RTL checks.

Then inspect the final git diff for:

- unrelated changes,
- deleted behavior,
- duplicate code paths,
- accidental API/schema changes,
- temporary/debug code,
- broad refetches,
- permissions regressions.

## 12. Phase gate

A phase may be declared complete only when:

1. every task in that phase is `VERIFIED`;
2. zero tasks are `NOT_STARTED`, `IN_PROGRESS`, `PARTIAL`, or `BLOCKED`;
3. the phase exit criteria are explicitly proven;
4. relevant regression checks pass;
5. `CURRENT_STATE.md` is updated;
6. the ledger contains concrete evidence;
7. a requirement-by-requirement final audit finds no missing acceptance criterion.

If any condition is false, do **not** say DONE/COMPLETE/FINISHED.

## 13. Independent audit

At the end of each phase, perform a fresh audit from the specification rather than from memory of what you changed.

For each task output internally or in the work log:

```text
TASK_ID — VERIFIED / PARTIAL / FAIL / BLOCKED
Acceptance criteria checked:
Evidence:
Regression impact:
```

Any `PARTIAL` or `FAIL` reopens the task.

## 14. Completion language

You may only say a phase is complete when its phase gate passes. You may only say Finance V2 is complete when the global Definition of Done in `MASTER_SPEC.md` is satisfied and Phase 10/regression acceptance has passed.
