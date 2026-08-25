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
