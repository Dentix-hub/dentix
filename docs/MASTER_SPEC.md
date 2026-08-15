# DENTIX Finance V2
## Deep UI/UX Redesign, Information Architecture, Data Correctness, and Implementation Plan

**Project:** DENTIX  
**Module:** Billing / Finance  
**Plan type:** Production redesign and refactor plan  
**Research date:** 15 August 2026  
**Primary goal:** Rebuild the existing Billing experience into a fast, clear, reliable, permission-aware dental finance workspace without breaking existing clinic workflows, tenant isolation, financial calculations, or API contracts unnecessarily.

---

# 1. Executive Recommendation

The current Billing area should not receive another visual facelift. It should be rebuilt as **Finance V2**, with a new information architecture, new route structure, new query/data architecture, and a much stricter definition of financial semantics.

The redesign should answer the clinic owner's most important financial questions within seconds:

1. How much did the clinic produce?
2. How much cash was actually collected?
3. How much was spent?
4. What is still owed by patients?
5. What is owed to doctors and employees?
6. What happened financially today?
7. Which patients, doctors, procedures, and expense categories are driving the numbers?

The new experience should feel like a professional dental finance workspace rather than a group of unrelated tables.

The recommended top-level information architecture is:

- **Overview**
- **Patient Accounts**
- **Payments**
- **Expenses**
- **Compensation**
  - Doctors
  - Payroll
- **Activity**
- **Reports**

This is intentionally different from the current structure of Doctors / Staff / Expenses / Summary / Payments. The new organization follows user jobs rather than implementation history.

The redesign must be **frontend-first but not frontend-only**. Several correctness and API issues should be resolved before or during UI implementation, because a premium interface that presents inconsistent numbers is worse than the current interface.

---

# 2. Scope and Non-Goals

## 2.1 In scope

- Complete Billing/Finance information architecture redesign.
- Complete desktop and mobile UI redesign.
- Reorganization of Finance routes and page hierarchy.
- Replacement of the current monolithic Billing orchestrator.
- React Query based loading, caching, invalidation, pagination, and prefetching.
- Consistent financial metric definitions.
- Patient receivables and balance-focused workflows using existing treatment/payment data.
- Payments management.
- Expense management.
- Doctor compensation views.
- Employee payroll views.
- Read-only unified financial activity feed.
- Financial reporting views.
- Role/permission-aware UI behavior.
- Arabic/English, RTL/LTR, currency, and date behavior.
- Accessibility and responsive behavior.
- Performance improvements.
- Migration and regression strategy.

## 2.2 Explicitly not assumed

The redesign must **not assume capabilities that the current data model does not contain**.

Do not pretend the following exist unless backend work explicitly adds them:

- Payment methods such as Cash / Card / Wallet on ordinary patient payments.
- A complete invoice entity/workflow.
- Doctor settlement/payment history.
- A true double-entry general ledger.
- Bank reconciliation.
- Refund workflows.
- Tax/VAT accounting.
- Insurance claim accounting beyond currently implemented functionality.

These may be future Finance V3 capabilities, but they should not be faked in Finance V2.

---

# 3. What Was Audited in DENTIX

The redesign is based on a code-level review of the current DENTIX Finance/Billing implementation, not only screenshots or assumptions.

## 3.1 Frontend areas reviewed

- `frontend/src/pages/Billing.jsx`
- Existing Billing tabs and feature components.
- Expenses tab.
- Payments tab.
- Salaries tab.
- Staff compensation tab.
- Financial summary tab.
- Doctor revenue table.
- Doctor revenue details modal.
- Frontend financial/accounting API client.
- Frontend package dependencies relevant to implementation.

## 3.2 Backend areas reviewed

- Accounting endpoints.
- Payment endpoints.
- Expense endpoints.
- Financial/statistics endpoints.
- Financial visibility / permission behavior.
- Financial model definitions.
- Salary payment model and endpoints.
- Doctor compensation calculations.
- Lab cost integration.
- Existing accounting-related service structure.

## 3.3 Product and design research reviewed

The recommendations were cross-checked against patterns from:

### Dental practice management products
- Dentrix / Dentrix Ascend.
- CareStack.
- Curve Dental.
- Dental practice reporting and revenue-cycle workflows.

### Modern finance products
- Stripe Dashboard.
- Xero.
- QuickBooks-style financial dashboards and cash-flow conventions.

### UX and design-system guidance
- Nielsen Norman Group usability guidance.
- Carbon Design System data-table and pagination guidance.
- WCAG accessibility requirements.
- W3C bidirectional/RTL guidance.
- MDN international number/date formatting APIs.
- Academic dashboard design-pattern research.

The purpose of this research is not to copy another product. It is to identify mature interaction patterns for high-frequency financial work and adapt them to a dental clinic context.

---

# 4. Current-State Diagnosis

# 4.1 The current page is structurally overloaded

`Billing.jsx` currently behaves as a central controller for too many unrelated responsibilities.

It manages multiple states for:

- Financial statistics.
- Payments.
- Expenses.
- Lab orders.
- Staff revenue.
- Comprehensive statistics.
- Active top-level tab.
- Expense sub-tab.
- Expense modal.
- Staff modal.
- Date range.
- Salary month.
- Salary data.

This makes the page harder to reason about, harder to test, and more expensive to extend.

## Consequence

A redesign implemented on top of this page would produce better-looking components while preserving the underlying complexity.

**Recommendation:** Replace it with a lightweight Finance route layout and page-specific feature modules.

---

# 4.2 The initial data-loading strategy is wasteful

The current Billing entry loads several datasets together, including financial stats, payments, expenses, lab orders, staff revenue, and comprehensive stats.

This happens even when the user only intends to view one part of the module.

Mutation flows such as adding/deleting an expense can trigger broad reload behavior rather than invalidating only the affected datasets.

## Why this matters

As clinic data grows, this architecture creates:

- Slower initial navigation.
- More network traffic.
- More server work.
- More loading-state complexity.
- Higher probability of stale or racing data.

## Target

Each route should request only the data required by that route.

Example:

- Opening Overview → overview queries only.
- Opening Payments → payments query only.
- Opening Payroll → payroll query only.
- Opening Doctor details → that doctor's data only.

Adjacent routes may be prefetched after the current view becomes stable.

---

# 4.3 The current navigation reflects code grouping, not user mental models

Current top-level concepts include Doctors, Staff, Expenses, Summary, and Payments, while Salaries are hidden inside Expenses.

This creates conceptual inconsistencies:

- Staff configuration is separate from Staff payroll.
- Salary payments are treated as a child of Expenses.
- Summary and operational work are mixed at the same hierarchy level.
- Patient debt/receivables is not a first-class workflow.

## Better mental model

Users think about finance in terms of:

- What is happening overall?
- Who owes us money?
- What money came in?
- What money went out?
- What do we owe our team?
- What happened in the ledger/activity history?
- What can I analyze or report?

Finance V2 should use those questions as the navigation model.

---

# 4.4 The Summary mixes metric scopes

The current comprehensive statistics endpoint accepts a period, but the outstanding balance value is calculated as actual current debt across the clinic rather than necessarily debt created inside the selected period.

This is not inherently wrong, but presenting it beside period-scoped values without an explicit label can mislead users.

Example of ambiguous presentation:

- Revenue — This month
- Collected — This month
- Expenses — This month
- Outstanding — all-time current balance

A user can reasonably assume all four use the same date scope.

## Recommendation

Every metric must carry a clearly defined scope.

Examples:

- `Collected · Aug 1–15`
- `Expenses · Aug 1–15`
- `Current patient balance · All time`

If a true period receivables metric is later needed, implement it separately rather than silently reinterpreting the existing number.

---

# 4.5 There is a potential deduction semantic inconsistency

In the reviewed comprehensive statistics implementation, net profit subtracts doctor dues, staff dues, total expenses, and lab costs. However, the returned total-deductions aggregation should be checked carefully because lab costs are handled separately and can be omitted from one aggregate while still being included in net profit.

## Recommendation

Before building Finance V2 KPI cards, create a formal **Financial Metric Contract** and write automated tests around it.

No KPI should be calculated independently in multiple frontend components.

---

# 4.6 Doctor finance currently risks inconsistent calculations

The Doctor Revenue list and Doctor Revenue Details perform related calculations in frontend code, with slightly different semantic inputs.

The list derives commission from a base involving collected revenue minus lab costs, while the details view derives a net revenue value from treatment data and lab costs before calculating compensation.

Even if both currently produce acceptable results for common cases, this is a dangerous architecture.

## Rule for Finance V2

**The backend owns financial truth.**

The frontend may format and visualize a number, but it should not invent authoritative compensation formulas.

The doctor summary endpoint should return explicit server-computed fields such as:

- gross_production
- collected_amount
- patient_discounts
- lab_cost
- commission_base
- commission_rate
- commission_amount
- fixed_salary_component
- total_doctor_due

The UI should display these values and explain them.

---

# 4.7 Doctor details currently performs redundant loading

The current doctor flow fetches doctor details before opening the details component, while the details component independently requests the same data.

## Recommendation

Use one ownership model:

- Route opens.
- Detail page/hook owns the query.
- Cached list data may seed placeholder/initial data.
- No duplicate detail request.

---

# 4.8 Payments UI underuses backend capabilities

The current payments UI is essentially a table with patient, date, amount, and notes.

The backend already supports pagination parameters and permission-aware filtering, while the frontend API currently behaves more like a simple bulk request.

Finance V2 should expose scalable server-side pagination/filtering rather than relying on a growing client-side list.

---

# 4.9 Expenses combine different sources without enough provenance

Current frontend behavior merges manual expenses and lab orders into a single expense-like array.

This can be useful visually, but it introduces two UX risks:

1. Users may not understand which records are manually editable/deletable and which are generated by another workflow.
2. Lab values may be double-counted if a future aggregate treats both source sets independently.

## Recommendation

Every financial record shown in a unified view must have a **source/type**.

Examples:

- Manual expense.
- Laboratory cost.
- Salary payment.
- Patient payment.

Source badges should be subtle but available, and deletion/edit actions should depend on source behavior.

---

# 4.10 Frontend API surface and backend routes need reconciliation

The frontend accounting client exposes account-tree / journal / trial-balance style calls, while the reviewed backend accounting router primarily exposes doctor, staff, comprehensive-statistics, and salary operations.

## Recommendation

Perform an API contract reconciliation before Finance V2 implementation:

- Remove dead client methods if obsolete.
- Implement missing endpoints only if they are actually required.
- Do not build UI around endpoints that are merely declared in a client file.

---

# 4.11 Complex work is trapped in a large modal

Doctor finance details currently uses a very large modal with its own tabs and settings.

Large modal workspaces create several problems:

- Browser back/forward navigation is weak.
- Deep links are impossible or awkward.
- Refreshing loses context.
- Mobile behavior is harder.
- Long financial data is squeezed inside overlay constraints.
- Nested tabs inside modal increase cognitive load.

## Recommendation

Doctor finance details should be a proper routed page on desktop and mobile.

Use drawers/sheets only for short contextual tasks such as:

- Add expense.
- Record salary payment.
- Change compensation settings.
- View a lightweight transaction detail.

---

# 5. Research Synthesis: What Mature Products Do Well

# 5.1 Dental systems prioritize actionable financial visibility

Dental practice platforms such as Dentrix emphasize real-time dashboards and smart reporting around practice performance. Modern dental platforms also increasingly centralize operational and financial information rather than forcing users to piece together separate reports.

## DENTIX implication

Finance Overview should not be a decorative analytics dashboard. It should be an operational landing page from which users can immediately investigate:

- Collections.
- Patient balances.
- Expenses.
- Provider performance.
- Team obligations.
- Recent financial activity.

---

# 5.2 Payment analysis should support “what, when, and who”

Dental reporting systems commonly expose payment analysis by date and type and provide transaction-level detail.

## DENTIX implication

Even before payment-method support exists, every payment row should make the following immediately understandable:

- Who paid / which patient account.
- How much.
- When.
- Which doctor or context if applicable.
- Notes or reason if present.
- Who recorded it where audit data is available.

Later, if payment methods are added to the data model, method becomes an additional filter—not a fabricated field today.

---

# 5.3 Financial SaaS separates overview from transaction investigation

Stripe, Xero, and accounting products typically give users a summary layer and then let them drill into transaction/activity detail.

This is superior to showing every possible detail on the dashboard.

## DENTIX implication

Overview should show answers and exceptions, while Payments/Expenses/Activity should handle detailed operational investigation.

---

# 5.4 Progressive disclosure reduces complexity

Nielsen Norman Group guidance supports progressive disclosure for improving learnability and efficiency and reducing errors in complex interfaces.

## DENTIX implication

Do not display every compensation setting, every financial formula, every expense field, and every report control at once.

Examples:

- Doctor card shows due amount first; detailed formula lives one level deeper.
- Expense row shows amount/category/date; notes and audit data appear in detail.
- Advanced filters live under an expandable filter panel on small screens.
- Compensation settings are opened only when the user chooses Manage compensation.

---

# 5.5 Data tables should support tasks, not merely display rows

Mature design systems treat tables as interactive work surfaces with sorting, pagination, selection/action behavior, accessible headers, keyboard interaction, and responsive alternatives.

## DENTIX implication

Every financial table should define:

- Primary entity column.
- Primary amount column.
- Date/time.
- Status/source where relevant.
- Row action model.
- Sorting behavior.
- Filtering behavior.
- Pagination behavior.
- Empty state.
- Mobile representation.

Avoid generic horizontal-scroll tables as the default mobile solution.

---

# 5.6 Dashboard design should preserve hierarchy

Research on dashboard patterns shows that dashboards are more effective when they deliberately balance summary, comparison, trends, and drill-down rather than presenting an unstructured collection of cards.

## DENTIX implication

Use a three-level hierarchy:

1. **Headline financial health.**
2. **Drivers and exceptions.**
3. **Recent activity / drill-down.**

Do not build a 12-card KPI wall.

---

# 6. Finance V2 Product Principles

Every design and engineering decision should be tested against these principles.

## Principle 1 — Financial truth before visual polish

A beautiful wrong number is unacceptable.

## Principle 2 — One metric, one definition

`Collected`, `Revenue`, `Outstanding`, `Doctor due`, and `Net` must have documented definitions.

## Principle 3 — Cash and production are different concepts

Never visually imply that treatment production equals money collected.

## Principle 4 — The period scope is always visible

Users should never wonder what dates a number represents.

## Principle 5 — All-time balances are labeled as all-time

Current debt is a balance-sheet-like value, not automatically a period metric.

## Principle 6 — Overview answers; detail pages explain

The dashboard should not become a reporting spreadsheet.

## Principle 7 — Common actions are close to context

Record payment from patient account. Add expense from expenses. Pay salary from payroll.

## Principle 8 — Permission restrictions are part of UX

Do not present unusable controls to users who cannot perform them.

## Principle 9 — Mobile is a first-class workflow

Receptionists/owners may use phones. Mobile should not be a shrunken desktop table.

## Principle 10 — Every money movement has provenance

Users should know where a financial entry came from.

## Principle 11 — Avoid hidden calculations

When a doctor due is derived, provide an understandable breakdown.

## Principle 12 — Fast navigation is part of perceived quality

Route-specific queries, caching, skeletons, and stable layout are UX requirements.

---

# 7. Proposed Information Architecture

```text
Finance
├── Overview
├── Patient Accounts
├── Payments
├── Expenses
├── Compensation
│   ├── Doctors
│   └── Payroll
├── Activity
└── Reports
```

## Why Compensation is grouped

Doctors and employees are both clinic obligations, but their calculation models differ. Grouping them under Compensation preserves a clear top-level structure while keeping separate specialist workflows.

## Why Patient Accounts comes before Payments

A payment is an event. A patient account represents the ongoing relationship between:

- treatment production,
- payments,
- discounts/adjustments where available,
- current outstanding balance.

Clinic staff often think “who owes us money?” before “show every payment.”

## Why Activity exists

Activity is a cross-source chronological financial feed. It is not a general ledger. Its job is traceability and operational awareness.

## Why Reports is separate

Reports answer analytical questions and often use wider date ranges. Operational pages should remain fast and task-oriented.

---

# 8. Route Architecture

Recommended nested routes:

```text
/finance
/finance/overview
/finance/patient-accounts
/finance/patient-accounts/:patientId
/finance/payments
/finance/expenses
/finance/compensation
/finance/compensation/doctors
/finance/compensation/doctors/:doctorId
/finance/compensation/payroll
/finance/activity
/finance/reports
```

Legacy `/billing` should remain temporarily and redirect to `/finance/overview`.

Do not break saved links during migration.

---

# 9. Global Finance Shell

# 9.1 Header

Desktop header:

```text
Finance                                           [Date range] [⋯]
Understand collections, costs, balances and team compensation
```

Do not repeat the global app header unnecessarily.

## Header rules

- Page title is stable.
- Current global finance period is visible where the page uses it.
- A custom period can be encoded in query parameters.
- Page-specific primary action appears on the right.

Examples:

- Payments → `Record payment` only if the product allows this workflow here.
- Expenses → `Add expense`.
- Payroll → no generic Add button; actions belong to employee rows.

---

# 9.2 Finance navigation

Desktop: horizontal sub-navigation or compact secondary sidebar depending existing DENTIX shell width.

Recommended horizontal tabs when width permits:

```text
Overview   Patient Accounts   Payments   Expenses   Compensation   Activity   Reports
```

Mobile: horizontally scrollable semantic tabs or a compact section selector, not a seven-item bottom navigation.

Finance is a module; its internal destinations should not compete with the application's main mobile navigation.

---

# 9.3 Shared date-range behavior

Use presets:

- Today
- Yesterday
- This week
- This month
- Last month
- Custom

Avoid adding unnecessary presets.

Persist selection in URL:

```text
?from=2026-08-01&to=2026-08-15
```

Benefits:

- Browser back works.
- Refresh preserves state.
- Links are shareable internally.
- QA can reproduce views.

For current/all-time balances, show a scope badge and do not let a date filter incorrectly imply period scoping.

---

# 10. Screen Specification — Overview

# 10.1 Goal

Give the owner/admin a trustworthy financial snapshot and direct paths to investigate important issues.

# 10.2 Layout hierarchy

## Section A — Headline metrics

Use four primary metrics, not a large wall of cards:

1. **Production / Revenue**
2. **Collected**
3. **Expenses**
4. **Net cash contribution / Net result**

The exact fourth label must match the approved metric formula. Do not casually call a cash-derived number “profit” if the underlying accounting basis does not support formal profit calculation.

Each card contains:

- Metric label.
- Formatted amount.
- Scope/date.
- Optional comparison versus previous equivalent period.
- Small semantic hint.
- Click/drill-down destination where useful.

Example:

```text
Collected
EGP 35,200
Aug 1–15
↑ 8.4% vs previous period
```

Avoid oversized icons and saturated gradients.

---

# 10.3 Section B — Current obligations and receivables

Compact “Needs attention” area:

- Current patient balance.
- Doctor compensation due.
- Payroll remaining for selected month.
- Pending/uncategorized expenses if such concept later exists.

Each row should be actionable.

Example:

```text
Patient balances                 EGP 68,450     23 patients   →
Doctor compensation              EGP 21,700      4 doctors    →
Payroll remaining                EGP 12,000      3 employees  →
```

This should not look like four more decorative cards.

---

# 10.4 Section C — Collection and expense trend

One primary chart only.

Recommended first version:

- Collected.
- Expenses.

Daily granularity for shorter ranges; weekly/monthly aggregation for longer ranges.

Do not automatically place production, collections, expenses, lab, payroll, and net all on one chart.

Chart behavior:

- Tooltips show exact localized amount/date.
- Legend is keyboard accessible where possible.
- RTL layout is tested.
- Color is not the only differentiator.
- Avoid animation that delays reading.

---

# 10.5 Section D — Breakdown

Use one contextual breakdown based on clinic needs, such as Expenses by category or Collections by doctor.

Do not show every available visualization simultaneously.

An owner should be able to switch breakdown dimension, but the default should remain stable.

---

# 10.6 Section E — Recent financial activity

Show 8–12 recent events:

```text
+ EGP 1,500  Patient payment      Ahmed Hassan    Today 4:35 PM
- EGP   800  Laboratory cost      Zirconia crown  Today 2:10 PM
- EGP   350  Manual expense       Materials       Today 1:40 PM
- EGP 2,500  Salary payment       Mona Ali         Yesterday
```

Every event includes source/type.

Primary action: `View all activity`.

---

# 11. Screen Specification — Patient Accounts

# 11.1 Why this screen matters

The current Billing structure underrepresents receivables. Patient debt is one of the most actionable financial workflows in a dental clinic.

This screen should answer:

- Which patients currently owe money?
- How much does each patient owe?
- When was their most recent financial activity?
- Which balances are largest?
- Can staff quickly open the patient's account and record/follow up payment?

# 11.2 Header metrics

Keep concise:

- Total current patient balance — explicitly `All time/current`.
- Number of patients with balance.
- Optional average balance only if useful in actual clinic testing.

Avoid weak vanity KPIs.

# 11.3 Controls

- Search patient.
- Sort by highest balance / most recent activity / patient name.
- Optional minimum balance filter.
- Optional doctor filter if permission/data semantics support it.

# 11.4 Desktop table

Columns:

- Patient.
- Current balance.
- Last payment.
- Last treatment/financial activity.
- Responsible doctor where meaningful.
- Action.

The current balance should be visually dominant.

# 11.5 Mobile list

```text
Ahmed Mohamed
Balance: EGP 3,250
Last payment: Aug 12
[Open account]
```

No seven-column sideways table.

# 11.6 Patient account detail

This should preferably reuse/extend the existing patient page financial area rather than create a duplicate patient record system.

Recommended financial timeline:

```text
Aug 15  Payment                    +1,500
Aug 12  Root canal treatment      +2,000 due
Aug 10  Payment                    +500
...
Current balance                   3,250
```

Important: define whether positive/negative visual signs represent clinic receivable versus cash movement and keep the convention consistent.

# 11.7 Backend need

If DENTIX does not already have a performant endpoint for “all patients with current balance,” create a dedicated paginated receivables endpoint rather than downloading every patient and calculating balances in the browser.

Suggested API shape:

```text
GET /api/v1/finance/receivables
  ?search=
  &min_balance=
  &doctor_id=
  &sort=balance_desc
  &skip=0
  &limit=50
```

Response should include server-calculated current balance.

---

# 12. Screen Specification — Payments

# 12.1 Goal

Fast investigation of incoming patient money.

# 12.2 Summary strip

Recommended:

- Collected in selected period.
- Payment count.
- Optional average payment only if useful.

Do not repeat patient debt here; debt belongs primarily to Patient Accounts.

# 12.3 Filter bar

Current feasible filters:

- Search patient.
- Date range.
- Doctor if supported by visibility semantics.
- Amount range if useful.

Future only after data-model support:

- Payment method.
- Payment status.

Do not show Cash/Card filters today unless payment method becomes a real persisted field.

# 12.4 Table

Desktop columns:

- Patient.
- Amount.
- Date/time.
- Doctor/record owner where semantically correct.
- Notes preview.
- Actions.

Amount should be right/endpoint aligned consistently according to layout direction and numeric readability requirements.

# 12.5 Row interaction

Clicking a row opens a detail drawer on desktop or detail sheet/page on mobile.

Detail can include:

- Full amount.
- Patient link.
- Exact timestamp/date available.
- Doctor/user association.
- Notes.
- Audit metadata when available.
- Delete action only for users with FINANCIAL_WRITE and where business rules allow deletion.

# 12.6 Pagination

Use server-side pagination.

Recommended default: 25 or 50 rows depending density testing.

Do not fetch a large all-time payment history merely to paginate it in memory.

# 12.7 Export

Add CSV export only after the screen's filter semantics are stable.

Export should reflect active filters and permission scope.

---

# 13. Screen Specification — Expenses

# 13.1 Goal

Make clinic outgoing costs easy to enter, understand, filter, and audit.

# 13.2 Header

```text
Expenses                                 [+ Add expense]
Track clinic operating and laboratory costs
```

Primary action uses the product's primary action style—not danger red. Red is reserved for destructive meaning.

# 13.3 Summary

- Total expenses for period.
- Manual operating expenses.
- Laboratory costs.
- Optional payroll only if payroll is intentionally included in the selected financial definition; otherwise keep payroll separate and state that explicitly.

# 13.4 Category breakdown

Use category chips or a small breakdown visualization.

Possible current categories should come from actual data rather than hardcoded design assumptions.

# 13.5 Expense list

Columns:

- Expense / description.
- Source.
- Category.
- Date.
- Amount.
- Actions.

Source examples:

- Manual.
- Lab.

If lab costs are read-only in Expenses because they originate elsewhere, visually communicate that and offer `View lab order` rather than Delete.

# 13.6 Add expense interaction

Use a side panel/drawer on desktop and bottom sheet/full-screen form on mobile.

Minimum fields based on current model:

- Item/description.
- Cost.
- Category.
- Date.
- Notes.

Behavior:

- Autofocus first useful field.
- Clear required-field state.
- Numeric amount keyboard on mobile.
- Prevent double submission.
- Optimistic UI only if safe; otherwise show immediate pending state and targeted refresh.
- On success, close and show contextual confirmation.

# 13.7 Deletion

Deletion is destructive.

Confirmation must state the record and amount, e.g.:

```text
Delete “Dental supplies” — EGP 350?
This will remove the expense from financial totals.
```

Do not use generic “Are you sure?”.

---

# 14. Screen Specification — Compensation

Compensation becomes a dedicated area with two sub-destinations:

```text
Doctors | Payroll
```

This eliminates the current Staff-versus-Salaries fragmentation.

---

# 15. Compensation — Doctors

# 15.1 Goal

Explain provider financial performance and current calculated entitlement clearly.

# 15.2 Doctor list

Each row/card should show only important summary values:

- Doctor name.
- Production/revenue.
- Collected.
- Lab cost.
- Calculated doctor due.

Optional small compensation label:

`30% commission + EGP 2,000 fixed`

if configured and the viewer has permission to see it.

# 15.3 Avoid false “Paid vs Due” semantics

The reviewed model does not establish a proper doctor-settlement payment history.

Therefore Finance V2 should initially show **Calculated doctor due/entitlement**, not invent:

- Paid.
- Remaining settlement.
- Last settlement.

If doctor settlement tracking is a desired business feature, build it as a separate backend/data-model enhancement.

# 15.4 Doctor details should be a route

```text
/finance/compensation/doctors/:doctorId
```

Page structure:

### Header
Doctor identity + period + compensation rule summary.

### KPI row
- Production.
- Collected.
- Patient discounts.
- Lab costs.
- Commission base.
- Doctor entitlement.

### Entitlement explanation

Readable equation block:

```text
Collected eligible amount      EGP 20,000
Less laboratory cost          -EGP  4,000
Commission base                EGP 16,000
Commission 30%                 EGP  4,800
Fixed component                EGP  2,000
-----------------------------------------
Calculated doctor due          EGP  6,800
```

Only display formula components that match server logic.

### Cases/treatments table

Allow filtering and drill-down.

### Compensation settings

Do not keep permanent settings in the same visual hierarchy as operational financial data.

Use a `Manage compensation` action visible only with SYSTEM_CONFIG permission.

Open a focused drawer/form.

# 15.5 Server authority

Doctor entitlement must come from one backend calculation contract.

The frontend should never maintain a parallel authoritative formula.

---

# 16. Compensation — Payroll

# 16.1 Goal

Make monthly employee salary obligations and payments easy to understand.

# 16.2 Month is the main time control

Payroll is naturally month-scoped, so do not force the generic Finance day-range picker into this screen.

Header:

```text
Payroll · August 2026            [Month selector]
```

# 16.3 Summary

- Total payable.
- Paid.
- Remaining.
- Employee count.

# 16.4 Employee rows

Show:

- Employee.
- Role.
- Base/fixed compensation.
- Additional calculated component if applicable.
- Payable for month.
- Paid amount.
- Remaining.
- Status.
- Action.

Status vocabulary:

- Unpaid.
- Partially paid.
- Paid.

Do not rely only on color.

# 16.5 Pay interaction

Focused drawer/sheet:

- Employee.
- Month.
- Payable amount.
- Already paid.
- Remaining.
- Amount to pay.
- Payment date.
- Notes.

Quick choices:

- Pay remaining.
- Custom amount.

The system—not the user—determines whether the result becomes partial or fully paid where possible.

# 16.6 Compensation configuration

Staff salary/per-appointment configuration should live behind a contextual settings action rather than as a separate top-level Staff finance page.

---

# 17. Screen Specification — Activity

# 17.1 Definition

Activity is a **normalized read-only timeline of financial events**.

It is not presented as a legally complete accounting ledger unless DENTIX later implements full accounting semantics.

# 17.2 Event types in initial version

Potential sources based on current capabilities:

- Patient payment.
- Manual expense.
- Laboratory cost/payment where appropriate.
- Salary payment.

Doctor calculated entitlement is not automatically a cash transaction and should not be inserted into Activity as if money moved.

# 17.3 Filters

- Date range.
- Type/source.
- Search patient/person/description.
- User/doctor where useful and permission-safe.

# 17.4 Row design

```text
[Payment] Ahmed Hassan
EGP +1,500                               Today 4:35 PM
Patient payment · Recorded by ...
```

Outgoing movement:

```text
[Expense] Dental Materials
EGP -350                                 Today 1:40 PM
Manual expense · Supplies
```

Use signs and labels, not color alone.

# 17.5 Backend strategy

Two implementation options:

## Option A — Frontend normalization

Acceptable only for an initial small-dataset release if all relevant paginated sources can be fetched without misleading chronology.

## Option B — Recommended

Create a server-side activity endpoint that unions normalized events and handles sorting/pagination centrally.

```text
GET /api/v1/finance/activity
  ?from=
  &to=
  &types=payment,expense,lab,salary
  &search=
  &skip=
  &limit=
```

This scales better and avoids fetching N datasets to build one page.

---

# 18. Screen Specification — Reports

Reports should be intentionally analytical and should not overload Overview.

Recommended first report set:

1. Financial Summary.
2. Collections by period.
3. Expenses by category.
4. Doctor production/collection/compensation.
5. Procedure profitability where existing backend cost-analysis data is reliable.

Potential later reports:

- Aging receivables.
- Lab cost trends.
- Location comparison for multi-branch clinics.
- Cash forecast.

# 18.1 Report interaction model

Each report has:

- Clear report title.
- Scope description.
- Date/filter controls.
- Summary metrics.
- Visualization only when it improves understanding.
- Detailed table.
- Export action if implemented.

Do not create a generic dashboard builder in Finance V2.

---

# 19. Visual Design Direction

# 19.1 Overall character

Finance V2 should feel:

- Clinical.
- Calm.
- Precise.
- Professional.
- Dense enough for daily work.
- Premium without appearing artificially “AI-generated.”

# 19.2 Avoid

- Excessive gradients.
- Glassmorphism on every surface.
- Different bright color for every KPI.
- Giant rounded cards everywhere.
- Decorative icons competing with amounts.
- Oversized whitespace that reduces financial scan efficiency.
- Charts added only for visual interest.

# 19.3 Surface hierarchy

Use three levels maximum:

1. Page background.
2. Primary content surface.
3. Elevated contextual drawer/popover.

Do not put a card inside a card inside a card.

# 19.4 Typography hierarchy

Financial amount hierarchy should dominate iconography.

Example:

```text
Collected
EGP 35,200
Aug 1–15
```

Amount: strongest weight/size.  
Label: medium.  
Scope/context: subdued.

Use tabular numerals if the selected font supports them cleanly, especially in tables.

# 19.5 Semantic color

Use color carefully:

- Positive/inflow: semantic success.
- Negative/outflow/destructive: semantic danger.
- Warning/attention: amber/orange.
- Neutral financial values: normal foreground.
- Brand color: navigation and primary actions.

Not every income value must be green. In dense tables, signs and labels are often enough.

# 19.6 Borders vs shadows

Prefer subtle borders and background contrast for dense enterprise surfaces. Reserve stronger elevation for transient overlays.

---

# 20. Data Table Design System for Finance

Create one reusable `FinanceDataTable` pattern rather than separately styling every table.

Required capabilities:

- Sortable columns where appropriate.
- Server pagination.
- Sticky header on long desktop lists.
- Loading skeleton rows.
- Empty state.
- Error state with retry.
- Row click affordance.
- Context actions.
- Keyboard-operable headers/actions.
- Correct alignment for amounts.
- Responsive mobile replacement.

## 20.1 Column priority

Every table receives a priority classification:

- P1: always visible.
- P2: desktop/tablet.
- P3: wide desktop/detail only.

On mobile, render a semantic list row rather than merely hiding arbitrary columns.

---

# 21. Filters and Search

# 21.1 Filter hierarchy

Always-visible controls should be the ones users need frequently.

Example Payments:

- Search.
- Date range.

Secondary filters can live behind `Filters`:

- Doctor.
- Amount range.

This follows progressive disclosure and reduces toolbar clutter.

# 21.2 Filter state

Encode meaningful filter state in URL parameters.

Example:

```text
/finance/payments?from=2026-08-01&to=2026-08-15&doctor=12&page=2
```

# 21.3 Active filter visibility

If advanced filters are collapsed, still show active filter chips so users understand why results are limited.

---

# 22. Drawers, Sheets, Modals, and Routes

Use the following decision rule:

## Use a route when

- The user may spend significant time there.
- The view has tabs or multiple sections.
- It needs deep linking.
- Refresh/back should work.
- It contains a large table or detailed analysis.

Examples:

- Doctor finance details.
- Patient account details.
- Reports.

## Use a drawer/sheet when

- The task is short and contextual.
- User should retain background context.

Examples:

- Add expense.
- View payment detail.
- Manage compensation.
- Record salary payment.

## Use a confirmation modal when

- A destructive/critical decision requires explicit confirmation.

Do not turn every details experience into a modal.

---

# 23. Permission-Aware UX

DENTIX already distinguishes financial read/write permissions and system configuration permissions.

Finance V2 must mirror these concepts in the interface.

## 23.1 FINANCIAL_READ

Can see permitted financial data according to backend visibility rules.

## 23.2 FINANCIAL_WRITE

Controls potentially affected:

- Add expense.
- Delete expense.
- Create/delete payment where exposed.
- Record salary payments.

## 23.3 SYSTEM_CONFIG

Controls potentially affected:

- Change doctor compensation rule.
- Change staff compensation configuration.

## 23.4 Important security rule

Frontend hiding is not security.

Backend permissions remain mandatory.

The UI should hide or disable unavailable actions primarily to reduce confusion and failed requests.

## 23.5 Doctor financial visibility

Because DENTIX supports role-scoped financial visibility, every new aggregate endpoint must use the same visibility service/rules. Never create a “convenient” Finance V2 endpoint that bypasses existing provider isolation.

---

# 24. Arabic, RTL, and Internationalization

Finance screens are especially sensitive to directionality because they mix:

- Arabic labels.
- Numbers.
- Currency codes/symbols.
- Dates.
- Latin patient names.
- IDs.

# 24.1 True RTL layout

RTL must mirror structure, not simply right-align text.

Test:

- Navigation order.
- Breadcrumbs.
- Table visual order.
- Drawer anchoring.
- Pagination arrows.
- Trend arrows where semantic direction is not language direction.
- Icons with directional meaning.

# 24.2 Money formatting

Create one `formatMoney` utility based on `Intl.NumberFormat`.

Example design API:

```js
formatMoney(amount, {
  locale,
  currency: clinicCurrency || 'EGP',
  display: 'code'
})
```

Do not hand-build `amount + " EGP"` across components.

Decide product-wide whether Arabic UI displays Arabic-Indic or Latin digits and apply consistently. This is a product choice; locale defaults should not surprise existing users.

# 24.3 Date formatting

Use `Intl.DateTimeFormat` or existing project date utilities with a single locale-aware convention.

Avoid mixing:

- `15/08/2026`
- `Aug 15`
- ISO date

without contextual reason.

# 24.4 Bidirectional isolation

Mixed-direction strings such as patient names plus amounts should be tested for bidi ordering. Use semantic HTML and appropriate direction isolation where necessary.

---

# 25. Accessibility Target

Target **WCAG 2.2 AA** behavior for the Finance redesign.

Key requirements:

- Keyboard navigation for tabs, tables, filters, and row actions.
- Visible focus state.
- Sufficient color contrast.
- Touch targets at least consistent with WCAG target-size expectations.
- No information conveyed by color alone.
- Screen-reader labels for icon-only buttons.
- Correct table headers and relationships.
- Accessible error messages.
- Focus management when opening/closing drawers.
- Reduced-motion preference honored.
- Reflow/mobile views that avoid unnecessary two-dimensional scrolling.

---

# 26. Loading, Empty, Error, and Zero States

A polished finance experience requires all states, not only populated screenshots.

# 26.1 Loading

Use layout-stable skeletons that resemble final content.

Avoid replacing the entire Finance module with a full-page spinner when switching between cached routes.

# 26.2 Empty state

Examples:

Payments:

`No payments found for this period.`

Filtered state:

`No payments match these filters.`

These are different messages and should have different actions.

# 26.3 Zero-value state

`EGP 0` is not necessarily an empty state.

For example, no expenses this week is valid data and should be shown as zero.

# 26.4 Error state

Show:

- What failed.
- Retry action.
- Preserve surrounding cached data where possible.

Do not blank the entire Finance interface because one secondary chart failed.

---

# 27. Frontend Architecture

Recommended structure:

```text
frontend/src/features/finance/
│
├── routes/
│   ├── FinanceLayout.jsx
│   └── financeRoutes.js
│
├── overview/
│   ├── FinanceOverviewPage.jsx
│   ├── OverviewMetrics.jsx
│   ├── CashFlowChart.jsx
│   ├── ObligationsPanel.jsx
│   └── RecentActivity.jsx
│
├── patientAccounts/
│   ├── PatientAccountsPage.jsx
│   ├── PatientAccountPage.jsx
│   ├── PatientAccountTable.jsx
│   └── usePatientAccounts.js
│
├── payments/
│   ├── PaymentsPage.jsx
│   ├── PaymentsTable.jsx
│   ├── PaymentDetailDrawer.jsx
│   └── usePayments.js
│
├── expenses/
│   ├── ExpensesPage.jsx
│   ├── ExpensesTable.jsx
│   ├── ExpenseFormDrawer.jsx
│   └── useExpenses.js
│
├── compensation/
│   ├── CompensationLayout.jsx
│   ├── doctors/
│   │   ├── DoctorsFinancePage.jsx
│   │   ├── DoctorFinancePage.jsx
│   │   ├── DoctorCompensationBreakdown.jsx
│   │   └── CompensationSettingsDrawer.jsx
│   └── payroll/
│       ├── PayrollPage.jsx
│       ├── PayrollTable.jsx
│       └── SalaryPaymentDrawer.jsx
│
├── activity/
│   ├── FinanceActivityPage.jsx
│   ├── ActivityList.jsx
│   └── ActivityFilters.jsx
│
├── reports/
│   ├── FinanceReportsPage.jsx
│   └── reports/
│
├── components/
│   ├── FinancePageHeader.jsx
│   ├── FinanceNav.jsx
│   ├── FinanceMetric.jsx
│   ├── FinanceDataTable.jsx
│   ├── FinanceFilterBar.jsx
│   ├── Money.jsx
│   ├── MetricScope.jsx
│   ├── SourceBadge.jsx
│   ├── AmountDelta.jsx
│   ├── DateRangeControl.jsx
│   └── FinancialEmptyState.jsx
│
├── api/
│   ├── financeApi.js
│   └── financeQueryKeys.js
│
├── hooks/
│   ├── useFinancePeriod.js
│   ├── useFinancePermissions.js
│   └── useFinanceFilters.js
│
├── model/
│   ├── financialMetrics.js
│   ├── activityNormalizer.js
│   └── financeTypes.js
│
└── utils/
    ├── formatMoney.js
    ├── financeDates.js
    └── financeMath.js  # display-only helpers, NOT authoritative business formulas
```

If DENTIX uses TypeScript in the target branch, use `.tsx/.ts` equivalents and typed API response contracts.

---

# 28. React Query Strategy

DENTIX already includes TanStack React Query. Use it rather than building another data layer.

# 28.1 Query keys

Example:

```js
financeKeys = {
  all: ['finance'],
  overview: (filters) => ['finance', 'overview', filters],
  receivables: (filters) => ['finance', 'receivables', filters],
  payments: (filters) => ['finance', 'payments', filters],
  expenses: (filters) => ['finance', 'expenses', filters],
  doctors: (filters) => ['finance', 'doctors', filters],
  doctor: (doctorId, filters) => ['finance', 'doctor', doctorId, filters],
  payroll: (month) => ['finance', 'payroll', month],
  activity: (filters) => ['finance', 'activity', filters],
};
```

# 28.2 Targeted invalidation

Add expense:

- Invalidate expenses for relevant period.
- Invalidate overview aggregates that include expenses.
- Invalidate activity if it includes expenses.

Do **not** automatically refetch doctor details, payments, staff compensation, and unrelated lists.

# 28.3 Stale times

Use route-appropriate stale times.

Examples as starting hypotheses, not fixed rules:

- Overview: 30–60 seconds.
- Lists: 30–60 seconds.
- Compensation config: longer unless edited.

Always measure real workflow behavior before tuning.

# 28.4 Keep previous data

When changing pagination/date filters, keep previous table data where React Query supports it to avoid unnecessary visual collapse.

# 28.5 Prefetching

After Overview stabilizes, selectively prefetch likely next destinations if network/server conditions permit.

Do not prefetch the entire Finance module.

---

# 29. Backend/API Plan

Finance V2 should minimize breaking changes but introduce purpose-built endpoints where the current shape cannot support a scalable UX.

# 29.1 P0 — Correctness contract

Before visual implementation is considered complete:

1. Document metric definitions.
2. Centralize doctor compensation calculation.
3. Verify lab-cost treatment and prevent double counting.
4. Verify total deduction semantics.
5. Explicitly distinguish current/all-time outstanding from period metrics.
6. Reconcile frontend API declarations with backend routes.

# 29.2 Recommended overview endpoint

Instead of six unrelated initial requests, create an aggregated endpoint designed for the landing page:

```text
GET /api/v1/finance/overview?from=YYYY-MM-DD&to=YYYY-MM-DD
```

Potential response:

```json
{
  "scope": {
    "from": "2026-08-01",
    "to": "2026-08-15"
  },
  "metrics": {
    "production": 0,
    "collected": 0,
    "expenses": 0,
    "net_result": 0
  },
  "balances": {
    "patient_outstanding_current": 0,
    "doctor_due": 0,
    "payroll_remaining": 0
  },
  "trend": [],
  "recent_activity": []
}
```

The endpoint should use established tenant and financial-visibility rules.

# 29.3 Payments endpoint evolution

Existing pagination should be exposed by frontend and expanded with server filters as needed.

Potential:

```text
GET /payments?from=&to=&patient_id=&doctor_id=&search=&skip=&limit=
```

Do not add `payment_method` until a persisted method field exists.

# 29.4 Expenses endpoint evolution

```text
GET /expenses?from=&to=&category=&search=&source=&skip=&limit=
```

If lab costs remain a separate domain source, consider a finance-level normalized expense endpoint rather than modifying the core expense model merely for UI convenience.

# 29.5 Receivables endpoint

Recommended new endpoint:

```text
GET /api/v1/finance/receivables
```

Server calculates balances and provides sorting/pagination.

# 29.6 Activity endpoint

Recommended for scale and correctness:

```text
GET /api/v1/finance/activity
```

Normalized event schema:

```json
{
  "id": "payment:123",
  "type": "patient_payment",
  "occurred_at": "2026-08-15T13:35:00+03:00",
  "direction": "inflow",
  "amount": 1500,
  "currency": "EGP",
  "title": "Patient payment",
  "subject": {
    "type": "patient",
    "id": 55,
    "name": "Ahmed Hassan"
  },
  "source": {
    "entity": "payment",
    "id": 123
  }
}
```

# 29.7 Doctor endpoint

Return explicit server-calculated breakdown; do not make frontend reconstruct authoritative due.

# 29.8 Doctor settlement tracking — optional backend feature

If DENTIX needs to know how much doctor compensation has actually been paid, create a real model and workflow.

Potential fields:

- doctor_id
- amount
- period/reference
- payment_date
- notes
- created_by
- tenant_id

Only then should UI display `Paid`, `Remaining`, and settlement history.

# 29.9 Payment method — optional backend feature

If clinics need cash/card/wallet/bank reporting, add a controlled enum/value in a deliberate migration. Then expose method filters and breakdowns.

Do not infer method from notes.

# 29.10 Invoice workflow — future decision

Do not call Patient Accounts “Invoices” unless a true invoice lifecycle is implemented.

A real invoice concept may require:

- invoice number.
- issue date.
- line items.
- subtotal/discount/tax.
- status.
- allocations/payments.
- void/refund behavior.
- immutable/auditable semantics.

That is a product feature, not a label change.

---

# 30. Financial Metric Contract

Create a version-controlled document and tests for every headline metric.

Minimum definitions:

## Production / Revenue

Define exactly which treatment states count and which date field determines inclusion.

## Collected

Sum of eligible patient payments within period, subject to financial visibility.

## Current outstanding

Current patient balances across all historical activity, unless explicitly scoped differently.

## Expenses

Define whether this includes:

- Manual expenses.
- Lab costs.
- Payroll.
- Other financial movements.

Do not use one label for different formulas across pages.

## Doctor due

Define exact compensation base and fixed/percentage handling.

## Net result

Define formula and avoid formal accounting labels such as Net Profit if the number does not represent complete accrual accounting profit.

---

# 31. Performance Targets

Measure in production-like data, not empty development data.

Suggested UX targets:

- Finance route shell appears immediately from app navigation.
- Cached route transition feels instant.
- Primary content skeleton begins without blank screen.
- Avoid duplicate detail requests.
- No initial loading of hidden Finance routes.
- Tables use server pagination.
- Long lists avoid excessive DOM rendering; existing `react-window` can be considered only where pagination is insufficient.
- Chart libraries are lazy-loaded if they materially affect initial bundle cost.

# 31.1 Bundle strategy

Finance reports/charts should be route-level lazy chunks where practical.

Do not load a heavy reporting visualization library on every app page merely because Finance contains one chart.

# 31.2 Network strategy

Avoid “refresh everything” mutation behavior.

Use targeted invalidation and server response updates.

---

# 32. Responsive Design

# 32.1 Desktop ≥ 1280

- Full finance nav.
- Dense tables.
- Two-column overview where appropriate.
- Side drawers for contextual tasks.

# 32.2 Tablet

- Reduce secondary columns.
- Keep critical metrics readable.
- Allow filter toolbar to wrap intentionally.

# 32.3 Mobile

- Metric cards become compact two-column or one-column blocks.
- Tables transform into semantic list rows.
- Sticky contextual primary action where useful.
- Filters open in bottom sheet.
- Forms use full-screen sheet if keyboard space requires it.
- No dependence on hover.

# 32.4 Reflow

Do not force users to horizontally pan through finance tables at standard mobile widths except for genuinely two-dimensional data where alternatives would damage meaning.

---

# 33. UX Copy and Terminology

Use one vocabulary across Arabic and English.

Recommended English terms:

- Finance
- Production
- Collected
- Current balance / Outstanding balance
- Expenses
- Doctor compensation
- Payroll
- Calculated due
- Patient Accounts
- Financial Activity

Avoid switching between:

- revenue / income / production
- due / debt / remaining
- salary / staff due / compensation

unless each term represents a different defined concept.

A bilingual glossary should be part of implementation.

---

# 34. User Roles and Primary Jobs-to-be-Done

# 34.1 Clinic owner/admin

Needs:

- Overall financial health.
- Collections vs expenses.
- Patient receivables.
- Doctor compensation.
- Payroll.
- Drill-down and reporting.

# 34.2 Accountant/financial staff

Needs:

- Detailed payment/expense lists.
- Filtering and auditability.
- Payroll operations.
- Export/reporting.

# 34.3 Receptionist

Depending permissions:

- Record/view patient payment.
- Understand patient current balance.
- Avoid broad confidential clinic financial reports if not authorized.

# 34.4 Doctor

Depending DENTIX visibility rules:

- View own relevant production/collections/compensation.
- Never automatically gain clinic-wide financial visibility.

Design and APIs must be tested separately for each role.

---

# 35. Error Prevention and Financial Safety

Financial actions deserve stronger UX protection than ordinary edits.

## 35.1 Amount inputs

- Reject invalid numeric strings.
- Prevent negative values unless business operation explicitly supports them.
- Define decimal precision.
- Show formatted preview when useful.

## 35.2 Dates

- Avoid accidental future payment date if prohibited.
- Make month context obvious in payroll.

## 35.3 Duplicate submissions

Disable action while request is pending and use idempotency support where backend supports it.

## 35.4 Destructive operations

Show specific confirmation.

## 35.5 Auditability

Preserve/create audit log entries for financial write actions.

---

# 36. Testing Strategy

# 36.1 Unit tests

Test:

- Money formatting.
- Date scope helpers.
- Activity normalization.
- URL filter serialization.
- Permission predicates.
- Display-only derived values.

Authoritative financial formulas should primarily be backend-tested.

# 36.2 Backend calculation tests

High priority:

- Doctor compensation edge cases.
- Lab cost inclusion/exclusion.
- Expenses totals.
- Salary partial payments.
- Outstanding balance semantics.
- Date-boundary behavior.
- Tenant isolation.
- Role visibility.

# 36.3 API integration tests

For every Finance endpoint:

- No auth.
- Wrong tenant.
- Read-only role.
- Write role.
- Doctor self-scope.
- Pagination.
- Empty result.
- Large result.
- Date filters.

# 36.4 Frontend integration tests

Test:

- Date range changes update query and URL.
- Filters persist on back navigation.
- Add expense refreshes only relevant data.
- Deleting expense updates totals.
- Salary payment updates status.
- Permission-hidden controls remain inaccessible.

# 36.5 End-to-end tests

Critical Playwright/Cypress flows:

1. Owner opens Finance Overview and changes period.
2. Owner finds patient with outstanding balance.
3. Authorized user records payment.
4. User adds and deletes manual expense.
5. Owner opens doctor compensation breakdown.
6. Owner updates compensation settings if permitted.
7. Payroll partial payment then full completion.
8. Activity filter by event type.
9. Doctor account sees only permitted data.
10. Receptionist cannot open unauthorized financial reports.

# 36.6 Accessibility testing

- axe automated checks.
- Keyboard-only walkthrough.
- Screen-reader spot checks.
- RTL keyboard/focus behavior.
- 200% and 400% zoom/reflow where relevant.

# 36.7 Visual regression

Capture:

- English desktop.
- Arabic desktop.
- English mobile.
- Arabic mobile.
- Dark/light theme if DENTIX supports both.
- Empty/loading/error states.

---

# 37. Analytics / UX Success Metrics

If product analytics exists, measure after rollout:

- Time from Finance entry to opening relevant patient account.
- Time to add expense.
- Time to understand doctor due breakdown.
- Number of failed/abandoned financial actions.
- Finance route load latency.
- API request count per route.
- Percentage of users using filters.
- Mobile completion rate for core actions.

Qualitative clinic testing remains essential; analytics cannot tell whether a metric label is financially misunderstood.

---

# 38. Implementation Phases

# Phase 0 — Financial Truth Audit

**Do this before redesign coding.**

Tasks:

- [ ] Define metric glossary.
- [ ] Map every existing Finance API and consumer.
- [ ] Map every payment/expense/salary/lab/doctor calculation.
- [ ] Verify outstanding balance scope.
- [ ] Verify total deductions formula.
- [ ] Verify lab costs are not double-counted.
- [ ] Compare doctor summary and detail formulas.
- [ ] Identify dead accounting API client methods.
- [ ] Document role visibility matrix.
- [ ] Add missing backend tests for financial formulas.

Deliverable:

`FINANCE_METRIC_CONTRACT.md`

Exit criteria:

Every displayed Finance KPI has a documented source and formula.

---

# Phase 1 — New Finance Foundation

Tasks:

- [ ] Create `/finance` route shell.
- [ ] Preserve `/billing` redirect.
- [ ] Create feature folder architecture.
- [ ] Build Finance navigation.
- [ ] Build shared date range control.
- [ ] Build `Money`/currency formatter.
- [ ] Build scope badge.
- [ ] Build shared metric component.
- [ ] Build shared filter bar.
- [ ] Build reusable data table pattern.
- [ ] Implement query-key factory.
- [ ] Implement permission helper.
- [ ] Add Arabic/RTL visual tests.

Do not migrate all content yet.

Exit criteria:

Empty Finance shell is production-grade and route-safe.

---

# Phase 2 — Overview V2

Backend:

- [ ] Implement/normalize Finance overview API if needed.
- [ ] Return explicitly scoped metrics.
- [ ] Return trend series.
- [ ] Return current balances with explicit semantics.
- [ ] Apply tenant and financial visibility rules.

Frontend:

- [ ] Build headline metrics.
- [ ] Build obligations/receivables section.
- [ ] Build one primary trend chart.
- [ ] Build recent activity preview.
- [ ] Add drill-down links.
- [ ] Add loading/empty/partial-error states.

Exit criteria:

Owner can understand core financial health without entering another tab.

---

# Phase 3 — Payments V2

Tasks:

- [ ] Expose server pagination in API client.
- [ ] Add server filters required by UX.
- [ ] Build search/date filter behavior.
- [ ] Build desktop table.
- [ ] Build mobile payment rows.
- [ ] Build detail drawer.
- [ ] Apply FINANCIAL_WRITE actions conditionally.
- [ ] Add audit metadata if available.
- [ ] Add route/query tests.

Exit criteria:

Payments page scales without loading all history.

---

# Phase 4 — Patient Accounts / Receivables

Tasks:

- [ ] Define patient balance contract.
- [ ] Build paginated receivables endpoint if missing.
- [ ] Add patient search/sort.
- [ ] Build outstanding summary.
- [ ] Build desktop and mobile list.
- [ ] Integrate with existing patient financial history page.
- [ ] Provide contextual Record Payment action only where permitted.

Exit criteria:

Staff can find a debtor and understand current balance in a few interactions.

---

# Phase 5 — Expenses V2

Tasks:

- [ ] Normalize expense source behavior.
- [ ] Separate manual/lab provenance.
- [ ] Define aggregation to prevent lab double-counting.
- [ ] Add server pagination/filtering.
- [ ] Build expense table/list.
- [ ] Build Add Expense drawer.
- [ ] Build specific delete confirmation.
- [ ] Use targeted React Query invalidation.

Exit criteria:

Expense operations no longer trigger broad Finance reloads.

---

# Phase 6 — Doctor Compensation V2

Backend:

- [ ] Establish single compensation calculation service.
- [ ] Return explicit breakdown fields.
- [ ] Add regression tests for all rule variants.

Frontend:

- [ ] Build doctors finance list.
- [ ] Replace giant details modal with routed page.
- [ ] Build compensation equation/breakdown.
- [ ] Build treatment/case detail table.
- [ ] Build permission-gated settings drawer.
- [ ] Remove duplicate detail request.
- [ ] Remove authoritative frontend calculation duplication.

Exit criteria:

List and detail always display the same backend-defined entitlement.

---

# Phase 7 — Payroll V2

Tasks:

- [ ] Merge Staff compensation conceptually with Salary workflow.
- [ ] Build monthly summary.
- [ ] Build payroll rows.
- [ ] Build partial/full payment interaction.
- [ ] Build compensation configuration action.
- [ ] Remove Salaries from Expenses sub-tab.
- [ ] Add role and month-boundary tests.

Exit criteria:

All employee pay operations live in one coherent workspace.

---

# Phase 8 — Financial Activity

Tasks:

- [ ] Define normalized event contract.
- [ ] Prefer server activity endpoint.
- [ ] Implement event pagination.
- [ ] Build source/type filters.
- [ ] Build desktop timeline/table hybrid.
- [ ] Build mobile activity feed.
- [ ] Link events to source records.

Exit criteria:

User can answer “what happened financially?” without visiting four pages.

---

# Phase 9 — Reports

Tasks:

- [ ] Move analytical summary views out of operational pages.
- [ ] Implement financial summary report.
- [ ] Implement collections report.
- [ ] Implement expense category report.
- [ ] Implement provider financial report.
- [ ] Evaluate existing procedure-cost API for profitability report.
- [ ] Add export only after filters/definitions stabilize.

Exit criteria:

Overview remains concise while deeper analysis remains available.

---

# Phase 10 — Legacy Removal

Only after regression and user acceptance:

- [ ] Remove old Billing tabs.
- [ ] Remove old monolithic data-loading code.
- [ ] Remove unused old modals/components.
- [ ] Remove dead API client methods.
- [ ] Keep redirect/compatibility route for a defined deprecation period.
- [ ] Update documentation.

---

# 39. Priority Matrix

## P0 — Must fix before/with redesign

- Metric correctness and definitions.
- Doctor calculation consistency.
- Lab double-counting protection.
- Outstanding scope labeling.
- Permission parity.
- Route-specific data loading.
- Duplicate doctor details fetch.

## P1 — Core Finance V2

- Finance shell.
- Overview.
- Patient Accounts.
- Payments.
- Expenses.
- Doctor compensation.
- Payroll.
- Responsive/RTL/accessibility.

## P2 — High-value enhancement

- Unified Activity endpoint.
- Richer reports.
- CSV exports.
- Period comparisons.

## P3 — Separate product decisions

- Payment methods.
- Doctor settlement tracking.
- Full invoice lifecycle.
- General ledger.
- Bank reconciliation.
- Advanced receivables aging.

---

# 40. What Not to Do

- Do not redesign only the CSS of `Billing.jsx`.
- Do not keep six datasets loading on every Finance entry.
- Do not create more nested tabs inside a giant page.
- Do not create fake payment-method filters.
- Do not label a patient balance list as invoices without invoice entities.
- Do not calculate doctor compensation independently in multiple React components.
- Do not merge lab expenses invisibly without source semantics.
- Do not show all-time debt beside period metrics without scope labeling.
- Do not use red as a normal Add Expense button color.
- Do not put every number in a colorful KPI card.
- Do not use horizontal mobile tables as the universal responsive solution.
- Do not create a new backend accounting system merely to achieve a visual redesign.
- Do not bypass existing DENTIX tenant/RBAC/financial visibility rules.

---

# 41. Definition of Done

Finance V2 is not complete until all of the following are true.

## Product clarity

- [ ] A clinic owner can identify collected, expenses, current balances, and compensation obligations quickly.
- [ ] Metric scopes are explicit.
- [ ] Production and collections are visually/semantically distinct.

## Correctness

- [ ] Headline metrics have backend-owned definitions.
- [ ] Doctor due is consistent across list/detail/report.
- [ ] Lab cost handling is tested against double counting.
- [ ] Outstanding semantics are documented.

## Architecture

- [ ] Old Billing monolith no longer owns all Finance data.
- [ ] Each route loads only necessary data.
- [ ] React Query targeted invalidation is implemented.
- [ ] Large lists are server paginated.

## UX

- [ ] Desktop and mobile workflows are intentionally designed.
- [ ] Long workflows use routes, short workflows use sheets/drawers.
- [ ] Filters persist via URL where appropriate.
- [ ] Empty/loading/error states are implemented.

## Permissions

- [ ] FINANCIAL_READ behavior is tested.
- [ ] FINANCIAL_WRITE behavior is tested.
- [ ] SYSTEM_CONFIG actions are gated.
- [ ] Doctor/receptionist visibility scenarios are tested.

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

- [ ] Existing financial writes still work.
- [ ] Existing patient data is untouched.
- [ ] Existing tenant isolation is preserved.
- [ ] Existing backend business rules remain unless intentionally corrected and tested.
- [ ] Legacy links redirect safely.

---

# 42. Suggested First Development Sprint

Do **not** start by coding all seven pages.

The best first sprint is:

### A. Financial correctness

1. Create metric contract.
2. Fix/lock doctor calculation semantics.
3. Verify lab and total-deduction behavior.
4. Document current outstanding semantics.

### B. Architecture foundation

5. Create `features/finance`.
6. Create nested `/finance` routes.
7. Create React Query key strategy.
8. Create `Money`, scope, header, nav, and filter primitives.

### C. First vertical slice

9. Build Finance Overview end to end.
10. Connect real backend data only.
11. Implement RTL/mobile/loading/error states.
12. Add tests.

Only after that slice is stable should the team migrate Payments, Patient Accounts, Expenses, Compensation, Activity, and Reports.

This creates a reusable system rather than seven independently redesigned screens.

---

# 43. Recommended Final Experience in One Sentence

**DENTIX Finance should behave like a focused dental financial command center: summary first, obligations second, activity third, detailed operational workflows one click away, with every number explainable and every action permission-safe.**

---

# 44. Research References

The following sources informed the design principles and competitive review. They are references, not specifications to copy.

## DENTIX

- Project repository: https://github.com/eslamemara1312-code/DENTIX

## Dental practice management / revenue-cycle patterns

- Dentrix — practice performance and analytics: https://www.dentrix.com/
- Dentrix Ascend — product/reporting resources: https://www.dentrixascend.com/
- CareStack — dental practice management and reporting: https://carestack.com/
- CareStack comparison/features overview: https://carestack.com/dental-software/compare/carestack-vs-curve-dental
- Curve Dental — cloud dental practice management: https://www.curvedental.com/

## Financial product patterns

- Stripe Dashboard / reporting documentation: https://docs.stripe.com/
- Xero analytics: https://www.xero.com/accounting-software/analytics/
- QuickBooks: https://quickbooks.intuit.com/

## UX / design systems / accessibility

- Nielsen Norman Group — Progressive Disclosure: https://www.nngroup.com/articles/progressive-disclosure/
- Nielsen Norman Group — usability heuristics for complex applications: https://www.nngroup.com/articles/usability-heuristics-complex-applications/
- Nielsen Norman Group — bottom sheet guidelines: https://www.nngroup.com/articles/bottom-sheet/
- Carbon Design System — Data Table usage: https://carbondesignsystem.com/components/data-table/usage/
- Carbon Design System — Data Table accessibility: https://carbondesignsystem.com/components/data-table/accessibility/
- Carbon Design System — Pagination: https://carbondesignsystem.com/components/pagination/usage/
- W3C WCAG guidance: https://www.w3.org/WAI/standards-guidelines/wcag/
- W3C reflow guidance: https://www.w3.org/WAI/WCAG21/Understanding/reflow.html
- MDN Intl.NumberFormat: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat
- MDN Intl.DateTimeFormat: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat
- W3C Internationalization / bidirectional text: https://www.w3.org/International/

## Dashboard research

- Bach et al., “Dashboard Design Patterns”: https://arxiv.org/abs/2205.00757

---

# 45. Final Architecture Decision Summary

| Decision | Recommendation |
|---|---|
| Module name | Finance |
| Existing `/billing` | Keep temporary redirect |
| Main landing page | Overview |
| Patient debt | First-class Patient Accounts workflow |
| Payments | Separate operational page |
| Expenses | Separate operational page with source provenance |
| Doctors + staff | Group under Compensation, separate sub-routes |
| Salaries under Expenses | Remove |
| Doctor detail | Routed page, not giant modal |
| Unified transaction view | Activity, clearly described as normalized financial activity |
| Full invoice UI | Do not add until real invoice model exists |
| Payment-method filters | Do not add until persisted field exists |
| Doctor paid/remaining settlement | Do not show until settlement model exists |
| Data loading | Route-specific React Query queries |
| Mutation refresh | Targeted invalidation |
| Large lists | Server-side pagination/filtering |
| Financial formulas | Backend is source of truth |
| Date/filter state | URL query parameters |
| RTL | True mirrored design + bidi testing |
| Currency | Centralized `Intl.NumberFormat` utility |
| Accessibility | WCAG 2.2 AA target |
| Visual style | Calm, clinical, dense, minimal semantic color |
| Rollout | Incremental vertical slices with old Billing compatibility |

