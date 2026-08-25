# DENTIX Canonical API Contract Inventory

## 1. Overview
The DENTIX API is organized around domain-driven resource routers mounted under `/api/v1`.

All API responses follow consistent envelope structures:
- Success: `{"success": true, "data": ...}` or standard typed Pydantic schema response.
- Error: `{"detail": str | dict}` with standard HTTP error status codes (400, 401, 403, 404, 410, 422, 429, 500).

---

## 2. Core Domain Routers

| Domain Tag | Route Prefix | Core Models | Key Operations |
|---|---|---|---|
| `Authentication` | `/api/v1/auth` | `User`, `UserSession` | Login, 2FA verify, logout, refresh |
| `Patients` | `/api/v1/patients` | `Patient`, `Attachment` | CRUD, search normalization, history |
| `Clinical` | `/api/v1/treatments` | `Treatment`, `ToothStatus`, `Prescription` | Dental charting, sessions, pricing |
| `Appointments` | `/api/v1/appointments`| `Appointment` | Booking, rescheduling, cancellation |
| `Finance` | `/api/v1/accounting` | `Payment`, `Expense`, `SalaryPayment` | Cash register, payroll, revenue |
| `Inventory` | `/api/v1/inventory` | `Material`, `StockItem`, `Batch` | Stock tracking, sessions, usage |
| `Administration` | `/api/v1/admin` | `Tenant`, `TenantSubscription` | Tenant provisioning, manual renewal |
| `Observability` | `/metrics`, `/health` | N/A | Prometheus scraping, synthetic uptime |

---

## 3. Permanently Retired Surfaces (`410 Gone`)
- `POST /api/v1/settings/backup/restore` -> `410 Gone` (ADR §4)
- `GET /api/v1/settings/backup/download` -> `410 Gone` (ADR §4)
- `POST /api/v1/system/backup/restore` -> `410 Gone` (ADR §4)
- `GET /api/v1/system/backup/download` -> `410 Gone` (ADR §4)
- `POST /api/v1/auth/debug/apply-migration` -> `410 Gone`
