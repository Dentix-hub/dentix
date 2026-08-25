# DENTIX Remediation Architectural Surfaces Inventory

**Inventory Timestamp**: 2026-08-25T00:44:30Z  
**Method**: Automated static inspection via Python AST / filesystem indexing.  

---

## 1. Backend Routers
- **Total Routers**: 54 router modules under `backend/routers/`
- **Key Domains**:
  - Auth & Admin: `auth/`, `admin_doctors.py`, `admin_security.py`, `password_reset.py`
  - Tenancy & Administration: `admin/tenants.py`, `tenants.py`, `tenant_config.py`
  - Clinical: `patients.py`, `dental.py`, `treatments.py`, `prescriptions.py`, `appointments.py`, `dental_history.py`
  - Operational & Finance: `invoices.py`, `payments.py`, `expenses.py`, `pricing.py`, `reports.py`, `analytics.py`
  - Inventory & Labs: `inventory.py`, `lab_cases.py`, `suppliers.py`, `medications.py`
  - AI & Voice: `ai_dental.py`, `scribe.py`
  - Infrastructure: `backup.py`, `upload.py`, `notifications.py`, `push_subscriptions.py`, `system.py`

## 2. ORM Data Models
- **Total Model Files**: 14 modules under `backend/models/`
- **Models**:
  - `user.py`: User, Role, Permission, UserRole
  - `tenant.py`: Tenant, TenantConfig, TenantSubscription, SubscriptionPlan
  - `patient.py`: Patient, MedicalHistory, PatientNote, PatientDocument
  - `dental.py`: ToothStatus, DentalChart, TreatmentPlan
  - `treatment.py`: Treatment, TreatmentMaterialUsage
  - `prescription.py`: Prescription, PrescriptionItem
  - `inventory.py`: Material, Batch, StockItem, MaterialSession, StockMovement, Supplier
  - `billing.py`: Invoice, Payment, Expense, PriceList, DoctorCompensation
  - `appointment.py`: Appointment, AppointmentSlot
  - `attachment.py`: Attachment, AttachmentMetadata
  - `laboratory.py`: LabCase, LabOrder
  - `system.py`: AuditLog, SystemError, SystemNotification, PushSubscription
  - `event.py`: OutboxEvent

## 3. Database Migrations
- **Total Migrations**: 38 version files under `backend/alembic/versions/`
- **Current Head**: `e3a4b5c6d7e8`

## 4. Background Workers & Lifetime Surfaces
- **Worker Modules**: 5 modules under `backend/workers/`
  - `event_processor.py`: Outbox event dispatcher
  - `subscription_checker.py`: Subscription status evaluator
  - `handlers.py`: Domain event handlers
  - `prefect_worker.py`: Orchestrator bridge
  - `run.py`: Worker CLI runner

## 5. Frontend Critical Surfaces
- **Total Page Components**: 38 `.jsx` files under `frontend/src/pages/`
- **Core Clinical & Business Pages**:
  - `Dashboard.jsx`
  - `Patients.jsx`, `PatientDetails.jsx`
  - `Appointments.jsx`
  - `Treatments.jsx`, `Prescriptions.jsx`
  - `InventoryPage.jsx`
  - `FinancePage.jsx`, `InvoicesPage.jsx`, `PaymentsPage.jsx`
  - `AnalyticsPage.jsx`
  - `TenantsPage.jsx`, `SettingsPage.jsx`, `BackupPage.jsx`

## 6. External AI & Egress Callers
- `backend/services/ai_service.py`: LLM reasoning, voice scribe, image segmentation.
- `backend/google_drive_client.py`: OAuth client for cloud tenant export.
- `backend/services/web_push_service.py`: VAPID push notifications.

## 7. Database HTTP Surfaces Inventory (Phase P02)
| Route / Endpoint | Router File | Method | Original Functionality | Target State (P02) |
|---|---|---|---|---|
| `/api/v1/settings/backup/download` | `backend/routers/settings.py` | `GET` | Full DB SQLite/pg_dump download over HTTP | **410 Gone** (Disabled for security) |
| `/api/v1/settings/backup/upload` (`.sql`) | `backend/routers/settings.py` | `POST` | Raw SQL restore via psql/SQLite overwrite | **410 Gone** (Disabled for security) |
| `/api/v1/system/restore` | `backend/routers/system_admin.py` | `POST` | File-based full restore (stub returned 501) | **410 Gone** (Disabled for security) |
| `/api/v1/system/backup` | `backend/routers/system_admin.py` | `GET` | Streamed JSON backup of all tenants/users | **410 Gone** (Cross-tenant dump removed) |
| `/api/v1/settings/backup/export` | `backend/routers/settings.py` | `GET` | Tenant-scoped JSON export | **Retained** (Safe tenant isolation) |
| `/api/v1/settings/backup/upload` (`.json`) | `backend/routers/settings.py` | `POST` | Tenant-scoped JSON restore | **Retained** (Safe tenant isolation) |
| `/api/v1/settings/backup/status` | `backend/routers/settings.py` | `GET` | Tenant backup frequency/timestamp status | **Retained** |
| `/api/v1/settings/backup/auth` | `backend/routers/settings.py` | `GET` | Google Drive OAuth init | **Retained** |
| `/api/v1/settings/backup/callback` | `backend/routers/settings.py` | `GET/POST` | Google Drive OAuth callback | **Retained** |
| `/api/v1/settings/backup/now` | `backend/routers/settings.py` | `POST` | Trigger manual tenant backup | **Retained** |
