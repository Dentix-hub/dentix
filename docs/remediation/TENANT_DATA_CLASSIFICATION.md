# DENTIX Multi-Tenant Data Classification & RLS Matrix

## 1. Classification Overview
All tables in the DENTIX database are strictly classified into one of three tenancy scopes:

1. **Tenant-Scoped Data (Direct `tenant_id` + RLS)**:
   Rows belong strictly to a single tenant clinic. Cross-tenant access is blocked at both ORM and database engine level via PostgreSQL Row-Level Security.
2. **Global Platform Data**:
   System configuration, subscription plans, global procedures catalog, and platform admin audit records.
3. **User Identity & System Session**:
   Global authentication accounts with membership associations.

---

## 2. Table Classification Matrix

| Table Name | Model | Scope | RLS Policy Enforced | Direct `tenant_id` Column |
|---|---|---|---|---|
| `patients` | `Patient` | Tenant-Scoped | `patients_tenant_policy` | Yes |
| `treatments` | `Treatment` | Tenant-Scoped | `treatments_tenant_policy` | Yes |
| `treatment_sessions` | `TreatmentSession` | Tenant-Scoped | `treatment_sessions_tenant_policy` | Yes |
| `tooth_status` | `ToothStatus` | Tenant-Scoped | `tooth_status_tenant_policy` | Yes |
| `prescriptions` | `Prescription` | Tenant-Scoped | `prescriptions_tenant_policy` | Yes |
| `attachments` | `Attachment` | Tenant-Scoped | `attachments_tenant_policy` | Yes |
| `appointments` | `Appointment` | Tenant-Scoped | `appointments_tenant_policy` | Yes |
| `payments` | `Payment` | Tenant-Scoped | `payments_tenant_policy` | Yes |
| `expenses` | `Expense` | Tenant-Scoped | `expenses_tenant_policy` | Yes |
| `salary_payments` | `SalaryPayment` | Tenant-Scoped | `salary_payments_tenant_policy` | Yes |
| `laboratories` | `Laboratory` | Tenant-Scoped | `laboratories_tenant_policy` | Yes |
| `lab_orders` | `LabOrder` | Tenant-Scoped | `lab_orders_tenant_policy` | Yes |
| `lab_payments` | `LabPayment` | Tenant-Scoped | `lab_payments_tenant_policy` | Yes |
| `warehouses` | `Warehouse` | Tenant-Scoped | `warehouses_tenant_policy` | Yes |
| `materials` | `Material` | Tenant-Scoped | `materials_tenant_policy` | Yes |
| `batches` | `Batch` | Tenant-Scoped | `batches_tenant_policy` | Yes |
| `stock_items` | `StockItem` | Tenant-Scoped | `stock_items_tenant_policy` | Yes |
| `material_sessions` | `MaterialSession` | Tenant-Scoped | `material_sessions_tenant_policy` | Yes |
| `stock_movements` | `StockMovement` | Tenant-Scoped | `stock_movements_tenant_policy` | Yes |
| `domain_events` | `DomainEvent` | Tenant-Scoped | `domain_events_tenant_policy` | Yes |
| `push_subscriptions` | `PushSubscription` | Tenant-Scoped | `push_subscriptions_tenant_policy` | Yes |
| `tenants` | `Tenant` | Global / Multi | N/A (Tenant Root) | Primary Key `id` |
| `subscription_plans` | `SubscriptionPlan` | Global Platform | N/A | No |
| `system_settings` | `SystemSetting` | Global Platform | N/A | No |
