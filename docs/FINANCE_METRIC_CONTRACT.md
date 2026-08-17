# DENTIX Finance V2 — Financial Metric Contract & Truth Audit
**Version:** 2.0.0  
**Phase:** Phase 0 — Financial Truth Audit  
**Status:** AUTHORITATIVE SPECIFICATION & AUDIT BASELINE  
**Date:** 2026-08-15  

---

## 1. Executive Summary & Purpose

This contract establishes the single source of truth for all financial calculations, metric definitions, API endpoints, role permissions, and database formulas across DENTIX Finance V2.

### Core Principles
1. **Backend Owns Financial Truth**: The backend is authoritative for all calculations. Frontend components must only format and display server-calculated numbers.
2. **Explicit Scope Transparency**: Every metric must clearly state its scope (Period-Scoped vs. All-Time).
3. **No Double-Counting**: Lab costs and expense aggregations must maintain distinct provenance.
4. **Tenant & Provider Isolation**: All financial metrics strictly enforce multi-tenant isolation and doctor-level visibility rules.

---

## 2. Metric Glossary & Semantic Definitions (FIN-TRUTH-001, FIN-TRUTH-004)

| Metric Name | Display Label (EN / AR) | Scope | Authoritative Backend Formula / Source | Notes & Guardrails |
|---|---|---|---|---|
| **Gross Production** | Gross Production<br>إجمالي الإنتاج | Period | `SUM(Treatment.cost)` for `Treatment.date` in period, where `Treatment.is_deleted = false` and `Patient.is_deleted = false` | Before patient discounts. Reflects total nominal value of procedures performed. |
| **Patient Discounts** | Discounts<br>الخصومات | Period | `SUM(Treatment.discount)` for `Treatment.date` in period, where `Treatment.is_deleted = false` | Sum of all discounts granted on treatments performed in the period. |
| **Net Invoiced (Revenue)** | Net Production / Revenue<br>صافي الإنتاج / الإيراد المحتسب | Period | `SUM(Treatment.cost - Treatment.discount)` for `Treatment.date` in period | Represents actual billed value to patients for clinical work performed. |
| **Collected (Cash In)** | Collected<br>التحصيلات النقدية | Period | `SUM(Payment.amount)` for `Payment.date` in period, where `Patient.is_deleted = false` | Actual cash/payments received from patients during the selected period. |
| **Current Patient Debt (All-Time)** | Outstanding Balance<br>المستحقات المتبقية للعيادة | **All-Time** | `MAX(0, All-Time Net Invoiced - All-Time Payments)` | **Never period-scoped**. Represents actual total uncollected debt across patient accounts. |
| **Period Balance** | Period Balance<br>فارق الفترة | Period | `Period Net Invoiced - Period Collected` | Difference between work billed and cash received in the period. May be positive or negative. |
| **Manual Expenses** | Direct Expenses<br>المصروفات المباشرة | Period | `SUM(Expense.cost)` for `Expense.date` in period | Clinic overhead, utilities, supplies, maintenance logged in `expenses` table. |
| **Lab Costs** | Laboratory Costs<br>تكاليف المعامل | Period | `SUM(LabOrder.cost)` for `LabOrder.order_date` in period | Manufacturing and lab order costs logged in `lab_orders` table. |
| **Doctor Commission Base** | Commission Base<br>وعاء العمولة | Period | `Doctor Collected Amount - Doctor Lab Cost` | Net collected revenue attributable to doctor minus lab costs incurred for doctor's orders. |
| **Doctor Commission** | Commission Amount<br>قيمة العمولة | Period | `MAX(0, Doctor Commission Base) * (User.commission_percent / 100)` | Variable performance compensation. |
| **Doctor Fixed Salary** | Fixed Salary<br>الراتب الثابت | Monthly | `User.fixed_salary` | Fixed monthly compensation component. |
| **Total Doctor Due** | Total Doctor Due<br>مستحقات الطبيب | Period / Month | `Doctor Commission Amount + Doctor Fixed Salary` | Total compensation earned by the doctor for the period. |
| **Staff Dues** | Staff Compensation<br>مستحقات الموظفين | Period / Month | `Fixed Salary + (Per Appointment Fee * Total Appointments)` | Compensation for non-doctor clinic staff (assistants, receptionists). |
| **Total Deductions** | Total Deductions<br>إجمالي الاستقطاعات | Period | `Total Doctor Dues + Total Staff Dues + Manual Expenses + Lab Costs` | Total operational outflow and compensation commitments. |
| **Net Operational Result** | Net Cash Result<br>صافي الدخل التشغيلي | Period | `Total Collected - Total Deductions` | Cash-basis operational result (`Collected - Total Deductions`). Avoids formal accrual GAAP labels. |

---

## 3. Existing Finance API & Consumer Map (FIN-TRUTH-002)

| Backend Route | HTTP Method | Service / Handler | Required Permissions | Frontend Consumer(s) | Status in V2 |
|---|---|---|---|---|---|
| `/api/v1/accounting/doctor-revenue` | GET | `AccountingService.get_doctor_revenue_analytics` | `FINANCIAL_READ` | `DoctorRevenue.jsx`, `Billing.jsx` | Kept; will serve V2 Doctors Compensation list |
| `/api/v1/accounting/doctor-details/{id}` | GET | `AccountingService.get_doctor_details_data` | `FINANCIAL_READ` | `DoctorRevenueDetails.jsx` | Kept & enhanced with explicit compensation fields |
| `/api/v1/accounting/staff-compensation/{id}` | PUT | `AccountingService.update_staff_compensation_settings` | `SYSTEM_CONFIG` | `DoctorRevenueDetails.jsx`, `StaffSalariesTab.jsx` | Kept for compensation updates |
| `/api/v1/accounting/staff-revenue` | GET | `AccountingService.get_staff_list_revenue` | `FINANCIAL_READ` | `StaffSalariesTab.jsx` | Kept for Staff compensation |
| `/api/v1/accounting/comprehensive-stats` | GET | `AccountingService.get_comprehensive_stats` | `FINANCIAL_READ` | `DashboardTab.jsx`, `Billing.jsx` | Kept; foundation for `/finance/overview` |
| `/api/v1/accounting/patients-report` | GET | `AccountingService.get_patients_report` | `FINANCIAL_READ` | API client | Foundation for Patient Accounts / Receivables V2 |
| `/api/v1/accounting/patient-report-details/{id}` | GET | `AccountingService.get_patient_financial_details` | `FINANCIAL_READ` | API client | Patient statement / financial drill-down |
| `/api/v1/accounting/salaries` | GET | `AccountingService.get_salary_status_for_month` | `FINANCIAL_READ` | `StaffSalariesTab.jsx` | Kept for Payroll V2 |
| `/api/v1/accounting/salaries` | POST | `AccountingService.process_salary_payment` | `FINANCIAL_WRITE` | `StaffSalariesTab.jsx` | Kept for recording salary payments |
| `/api/v1/accounting/salaries/{id}` | DELETE | `AccountingService.remove_salary_payment` | `FINANCIAL_WRITE` | `StaffSalariesTab.jsx` | Kept for deleting salary records |
| `/api/v1/accounting/staff/{id}/hire-date` | PUT | `AccountingService.update_employee_hire_date` | `SYSTEM_CONFIG` | `StaffSalariesTab.jsx` | Kept for salary proration calculation |
| `/api/v1/payments` | GET | `FinancialVisibilityService.get_visible_payments_query` | `FINANCIAL_READ` | `PaymentsTab.jsx` | Kept; upgraded with server-side pagination/filtering |
| `/api/v1/payments` | POST | `BillingService.create_payment` | `FINANCIAL_WRITE` | Patient details, Payment modals | Kept for recording patient payments |
| `/api/v1/payments/{id}` | DELETE | `crud.delete_payment` | `FINANCIAL_WRITE` | `PaymentsTab.jsx` | Kept for payment void/delete |
| `/api/v1/payments/today/payments` | GET | `BillingService.get_today_payments_list` | `FINANCIAL_READ` | Dashboard, Billing | Kept for daily summary |
| `/api/v1/payments/today/debtors` | GET | `BillingService.get_today_debtors_list` | `FINANCIAL_READ` | Dashboard, Billing | Kept for daily debtors |
| `/api/v1/expenses` | GET | `crud.get_expenses` | `FINANCIAL_READ` | `ExpensesTab.jsx` | Kept; upgraded with pagination & source provenance |
| `/api/v1/expenses` | POST | `crud.create_expense` | `FINANCIAL_WRITE` | `ExpensesTab.jsx` | Kept for recording manual expenses |
| `/api/v1/expenses/{id}` | DELETE | `crud.delete_expense` | `FINANCIAL_WRITE` | `ExpensesTab.jsx` | Kept for deleting expenses |
| `/api/v1/expenses/stats` | GET | `crud.get_financial_stats` | `FINANCIAL_READ` | `Dashboard.jsx`, `billing.js` | Kept for high-level widget stats |
| `/api/v1/financials/procedure/{id}/analysis` | GET | `CostEngine.calculate_procedure_cost` | `FINANCIAL_READ` | Procedure pricing UI | Kept for procedure BOM / cost engine |
| `/api/v1/financials/procedures/analysis` | GET | `CostEngine.calculate_all_procedures_costs` | `FINANCIAL_READ` | Reports / Pricing analysis | Kept for clinic-wide procedure profitability |

---

## 4. Dead Accounting API Client Methods (FIN-TRUTH-008)

The following methods currently declared in `frontend/src/api/financials.js` have **no corresponding backend endpoints** and represent unused legacy or placeholder general-ledger declarations:

1. `getAccounts(type)` (`/api/v1/accounting/accounts`)
2. `getAccountsTree()` (`/api/v1/accounting/accounts/tree`)
3. `createAccount(data)` (`/api/v1/accounting/accounts`)
4. `updateAccount(id, data)` (`/api/v1/accounting/accounts/{id}`)
5. `deleteAccount(id)` (`/api/v1/accounting/accounts/{id}`)
6. `getAccountBalance(id, date)` (`/api/v1/accounting/accounts/{id}/balance`)
7. `getAccountLedger(id, params)` (`/api/v1/accounting/accounts/{id}/ledger`)
8. `getJournals()` (`/api/v1/accounting/journals`)
9. `getJournalEntries(params)` (`/api/v1/accounting/journal-entries`)
10. `createJournalEntry(data)` (`/api/v1/accounting/journal-entries`)
11. `getJournalEntry(id)` (`/api/v1/accounting/journal-entries/{id}`)
12. `updateJournalEntry(id, data)` (`/api/v1/accounting/journal-entries/{id}`)
13. `postJournalEntry(id, data)` (`/api/v1/accounting/journal-entries/{id}/post`)
14. `voidJournalEntry(id, data)` (`/api/v1/accounting/journal-entries/{id}/void`)
15. `getTrialBalance(date)` (`/api/v1/accounting/reports/trial-balance`)

### Action:
- **Do not invent backend routes** for these methods during Finance V2.
- **Do not build any UI around them**.
- These dead methods will be safely removed in **Phase 10 (FIN-LEG-004)**.

---

## 5. Calculation Reconciliation & Deductions Architecture (FIN-TRUTH-003, FIN-TRUTH-005, FIN-TRUTH-006)

### 5.1 Deductions Formula Reconciliation
In `AccountingService.get_comprehensive_stats`, deductions and net profit are calculated as follows:

$$\text{Total Deductions} = \text{Doctor Dues} + \text{Staff Dues} + \text{Manual Expenses} + \text{Lab Costs}$$

$$\text{Net Profit} = \text{Total Collected} - \text{Total Deductions}$$

### 5.2 Lab Cost Provenance & Double-Counting Safeguard
- **Source 1: Lab Orders (`lab_orders` table)**: Authoritative source for dental laboratory work linked to patients and doctors.
- **Source 2: Manual Expenses (`expenses` table)**: Intended only for general clinic overhead (Rent, Utilities, Consumables, Salaries, Maintenance).
- **Double-Counting Guard**:
  - `total_lab_costs` in financial summaries is aggregated strictly from `models.LabOrder.cost`.
  - Manual expenses in `models.Expense` must NOT include duplicate entries for lab order invoices.
  - In Finance V2 UI, expense categories will explicitly guide users, and unified expense tables will display source badges (`Lab Order` vs. `Manual Expense`).

---

## 6. Doctor Compensation Calculation Contract (FIN-TRUTH-007)

### 6.1 Authoritative Formula
Doctor compensation is strictly cash-collection based with lab deductions:

$$\text{Commission Base} = \text{Collected Payments for Doctor's Treatments} - \text{Lab Costs for Doctor's Orders}$$

$$\text{Commission Amount} = \max(0, \text{Commission Base}) \times \frac{\text{Commission \%}}{100}$$

$$\text{Total Doctor Due} = \text{Commission Amount} + \text{Fixed Salary}$$

### 6.2 Frontend/Backend Resolution
- **Prior Issue**: `DoctorRevenueDetails.jsx` previously computed production-based net revenue (`treatments.net - lab_orders.cost`) inside React, while `DoctorRevenue.jsx` used collection-based values.
- **V2 Contract**: The backend is authoritative. All doctor views (Overview, List, and Detail Page) will display server-computed fields:
  - `gross_cost`
  - `patient_discount`
  - `revenue` (Net Billed)
  - `collected` (Cash Received)
  - `lab_cost`
  - `commission_base`
  - `commission_percent`
  - `commission_amount`
  - `fixed_salary`
  - `total_due`

---

## 7. Role Visibility & Permission Matrix (FIN-TRUTH-009)

| Role / Permission | Overview & KPIs | Patient Accounts / Receivables | Payments List | Expenses | Doctor Compensation | Staff / Payroll | Financial Reports |
|---|---|---|---|---|---|---|---|
| **Owner / Admin / Super Admin** | Full Access | Full Access | Full Access | Full Access (Read/Write) | All Doctors (Read/Config) | All Staff (Read/Write/Config) | Full Access |
| **Accountant** | Full Read | Full Read | Full Read | Full Read | All Doctors (Read Only) | All Staff (Read Only) | Full Read |
| **Doctor (Self-Scope)** | Scoped to assigned patients only | Scoped to assigned patients only | Scoped to assigned patients only | Hidden / No Access | Self Doctor Due only; others hidden | Hidden / No Access | Hidden / No Access |
| **Doctor (Cross-Scope Override)** *(when `can_view_other_doctors_history=true`)* | All Patient Finances | All Patient Finances | All Patient Finances | Hidden / No Access | Self Doctor Due only | Hidden / No Access | Hidden / No Access |
| **Receptionist / Assistant** | Hidden / No Access | Outstanding View only (for payment collection) | Read / Record Payment (if `FINANCIAL_WRITE` granted) | Hidden / No Access | Hidden / No Access | Hidden / No Access | Hidden / No Access |

### Multi-Tenant Isolation Rule
Every financial query and mutation must enforce `tenant_id == current_user.tenant_id`. Cross-tenant data leakage is strictly blocked at the ORM/RLS layer.
