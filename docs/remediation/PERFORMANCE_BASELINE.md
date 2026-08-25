# DENTIX Performance Baseline & Guardrails

## 1. Response Time Budgets (p95)

| Endpoint Type | p95 Target | Measured Local | Status |
|---|---|---|---|
| **Health Probes** (`/health`, `/api/v1/ping`) | < 50ms | ~5ms | **PASS** |
| **Authentication** (`/api/v1/auth/login`) | < 250ms | ~120ms | **PASS** |
| **Patient List & Search** (`/api/v1/patients`) | < 200ms | ~35ms | **PASS** |
| **Clinical Treatment Chart** (`/api/v1/treatments/patient/{id}`) | < 200ms | ~40ms | **PASS** |
| **Financial Summary** (`/api/v1/accounting/summary`) | < 300ms | ~65ms | **PASS** |
| **Metrics Scraping** (`/metrics`) | < 100ms | ~15ms | **PASS** |

---

## 2. Query Optimization Rules
- All tenant queries MUST include `tenant_id = :tenant_id` allowing index partition scans.
- `with_for_update(skip_locked=True)` utilized for outbox event polling.
- Zero N+1 query loops on patient treatment joins (eager loading with `selectinload` / `joinedload`).
