# DENTIX Remediation Architectural Decisions

## 1. Safe Configuration Defaults
| Control | Mode / Default | Rationale |
|---|---|---|
| `SUBSCRIPTION_ENFORCEMENT_MODE` | `off` | Prevent accidental lockout on unconfigured systems. |
| `SUBSCRIPTION_WORKER_ENABLED` | `false` | Prevent automated tenant mutations without explicit activation. |
| `RATE_LIMIT_MODE` | `off` | Safe local default; tested via mocks and unit suites. |
| `METRICS_EXPOSURE_MODE` | `off` | Expose `/metrics` only when explicitly authenticated. |
| `ALERT_DISPATCH_ENABLED` | `false` | Prevent unauthorized outbound HTTP calls during local testing. |
| `ERROR_AGGREGATION_ENABLED` | `false` | Local mock verification only; external aggregation held in H-05. |
| `BACKUP_SCHEDULER_ENABLED` | `false` | Local offline backups executed via guarded CLI scripts. |
| `EXTERNAL_AI_PHI_MODE` | `deny` | Fail closed on clinical text/voice processing unless deidentified. |
| `GEOIP_MODE` | `off` | Non-blocking async resolution; disabled by default to avoid outbound telemetry. |
| `RAG_MODE` | `off` | Direct tenant isolation required before activation. |

## 2. Subscription Management Policy
- Manual renewal only by authorized tenant / platform administrators.
- No electronic collection, card tokenization, or payment gateway SDKs.
- Clinical history reads remain permanently accessible (`expired_read_only` state).

## 3. Five Direct Ownership Tables
- `ToothStatus`
- `Prescription`
- `Attachment`
- `MaterialSession`
- `StockMovement`
All 5 tables receive explicit `tenant_id` columns, FKs, NOT NULL constraints, and `FORCE ROW LEVEL SECURITY`.

## 4. Database HTTP Surfaces and Deprecation Policy (Phase P02)
- **Elimination of Raw SQL / Full DB Endpoints**: All HTTP surfaces that stream raw SQL database dumps (`pg_dump`/raw SQLite files) or accept arbitrary raw `.sql` files for database restoration are permanently disabled.
- **HTTP Contract**:
  - `GET /api/v1/settings/backup/download` returns `HTTP 410 Gone`.
  - `POST /api/v1/settings/backup/upload` rejecting `.sql` returns `HTTP 410 Gone`.
  - `POST /api/v1/system/restore` returns `HTTP 410 Gone`.
  - `GET /api/v1/system/backup` returns `HTTP 410 Gone`.
- **Approved Safe Alternatives**:
  - **Tenant Export/Import**: `GET /api/v1/settings/backup/export` (clinic-scoped JSON) and `POST /api/v1/settings/backup/upload` (accepting `.json` only) remain supported for tenant data portability.
  - **Guarded CLI Tooling**: Platform-level backups and disaster recovery operations are performed strictly via local, guarded CLI commands with strict target checks (`scripts/backup/`) in Phase P08.
## 5. Attachment Note Schema Truth and Alignment (Phase P04)
- **Problem**: Historical Alembic revision `c9d0e1f2a3b4_repair_legacy_attachments_schema.py` ensures the `attachments` table contains a nullable `note` column, but `Attachment` in `backend/models/patient.py` and schemas in `backend/schemas/patient.py` lacked the `note` attribute.
- **Decision**: Formally align the SQLAlchemy ORM model and Pydantic schemas to include `note: Optional[str] = None` / `sa.Text, nullable=True`. This eliminates ORM-migration drift and provides consistent metadata support for clinical attachments across all tenants.
