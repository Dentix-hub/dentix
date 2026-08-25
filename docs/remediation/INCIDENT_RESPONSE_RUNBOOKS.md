# DENTIX Incident Response Runbooks

## Runbook 1: Database Connection Saturation (`IR-DB-001`)

### Symptoms
- Endpoints return `503 Service Unavailable` or `TimeoutError`.
- High CPU/connection count reported by PostgreSQL / PgBouncer.

### Resolution Steps
1. Verify active connection count:
   ```sql
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   ```
2. Identify long-running transactions:
   ```sql
   SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC;
   ```
3. Terminate hanging background queries if safe:
   ```sql
   SELECT pg_cancel_backend(pid);
   ```

---

## Runbook 2: Authentication Brute Force / High Failures (`IR-SEC-002`)

### Symptoms
- `ALERT-SEC-01` triggers.
- Spike in `POST /api/v1/auth/login` returning `401 Unauthorized`.

### Resolution Steps
1. Query top offending source IPs from `SecurityService.get_security_stats()`.
2. Verify rate limiter is dropping excess requests (`429 Too Many Requests`).
3. Add temporary IP block via admin interface or `SecurityService.block_ip(ip, "Brute force attack", minutes=120)`.

---

## Runbook 3: Outbox Processing Delay (`IR-WORKER-003`)

### Symptoms
- Domain events remain in `pending` or `processing` status past `PROCESSING_LEASE_SECONDS`.
- Notifications or background sync jobs are delayed.

### Resolution Steps
1. Check status of background daemon via `uv run python -m backend.workers.run --workers events`.
2. Verify stale events are reclaimed by `EventService.recover_stale_processing()`.
3. Check worker logs for unhandled exception traces.
