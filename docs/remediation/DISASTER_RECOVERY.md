# DENTIX Disaster Recovery & Restoration Procedure

## 1. Safety Guardrails & Policy
- All raw database backup and restore operations are strictly performed via offline CLI tooling (`scripts/ops/guarded_backup.py` and `scripts/ops/guarded_restore.py`).
- No HTTP routes allow uploading raw SQL dumps or triggering global database drops.
- Restorations must always verify SHA-256 integrity manifests prior to applying any database changes.

---

## 2. Step-by-Step Restoration Procedure

### Step 1: Place Application into Maintenance Mode
Ensure application servers are stopped or routing traffic to maintenance pages to prevent concurrent writes.

### Step 2: Verify Backup Integrity
Run the guarded restore script in verification mode:
```bash
python scripts/ops/guarded_restore.py backups/offline/dentix_backup_YYYYMMDD_HHMMSSZ.sql
```
Expected output: `[PASS] Integrity check passed. SHA-256: <checksum>`.

### Step 3: Execute Guarded Restore
Apply the verified backup with the explicit destructive confirmation flag:
```bash
python scripts/ops/guarded_restore.py backups/offline/dentix_backup_YYYYMMDD_HHMMSSZ.sql --confirm-destructive-restore
```

### Step 4: Run Post-Restore Health Checks
1. Run blank DB migrations test suite: `uv run pytest backend/tests/test_migrations_lineage.py`
2. Validate system metrics: `GET /metrics` and `GET /health`
