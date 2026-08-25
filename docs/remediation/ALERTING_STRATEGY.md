# DENTIX Observability & Alerting Strategy

## 1. Objectives & Safety Invariants
- Provide real-time operational visibility into system health, database connection pool saturation, error rates, and backup timeliness.
- Zero PHI or patient identifying information in metrics labels or alert payloads.
- Strict timeout bounds and HMAC signatures for alert webhook dispatch.

---

## 2. Monitored Metrics & Thresholds

| Alert Identifier | Metric / Trigger | Severity | Threshold | Action Required |
|---|---|---|---|---|
| `ALERT-ERR-01` | Critical System Errors | **Critical** | > 5 errors in 15 min | Investigate error traces in `/admin/system/errors` |
| `ALERT-DB-01` | Connection Pool Exhaustion | **Critical** | Pool usage > 85% for 5 min | Check long-running queries or connection leaks |
| `ALERT-SEC-01` | Excessive Auth Failures | **High** | > 20 failed logins in 10 min | Review suspicious IP block list in SecurityService |
| `ALERT-BKP-01` | Stale Database Backup | **Critical** | Last backup > 24 hours ago | Trigger manual guarded CLI backup and verify disk space |
| `ALERT-SUB-01` | Stale Outbox Events | **Medium** | Pending events > 100 or lease age > 15 min | Verify Prefect worker daemon health |

---

## 3. Webhook Transport & HMAC Verification
When alert notifications are dispatched to external monitoring endpoints (e.g. Opsgenie, PagerDuty, Slack webhooks):
- Payload contains only aggregate metric names, severity, tenant-count, and timestamps.
- Webhook requests include `X-Dentix-Signature: sha256=<HMAC_HEX>` signed with `ALERT_WEBHOOK_SECRET`.
- HTTP timeout is strictly capped at 3.0 seconds.
