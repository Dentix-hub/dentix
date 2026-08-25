# DENTIX Disaster Recovery and Restoration Procedure

## Safety invariants

- Raw database backup/restore is offline CLI-only; no HTTP route may export or apply a database dump.
- Every artifact is AES-256-GCM encrypted and has a format `2.1` SHA-256 manifest containing the database engine, schema revision, cipher, non-secret key identifier, and exact artifact name/size/hash.
- `DENTIX_BACKUP_ENCRYPTION_KEY` must be URL-safe base64 decoding to exactly 32 bytes and must come from the approved secret store.
- `DENTIX_BACKUP_KEY_ID` identifies the active key version without exposing key material and is required operationally for rotation and recovery.
- Restore is dry-run verification by default. Applying a restore requires both `--confirm-destructive-restore` and `LOCAL_DESTRUCTIVE_TESTS=1`.
- The target guard permits only explicitly local/test/development targets. Restore accepts only a new/empty SQLite file or an empty PostgreSQL `public` schema.

## Backup

Set `DATABASE_URL`, `DENTIX_BACKUP_ENCRYPTION_KEY`, and `DENTIX_BACKUP_KEY_ID`, then run:

```powershell
.venv\Scripts\python.exe scripts\ops\guarded_backup.py --output-dir backups\offline
```

The command creates a `.dump.enc` artifact and a matching `.manifest.json`. Store the encryption key separately from both files. The raw dump is created with restrictive permissions in the operating-system temporary directory and removed after encryption.

## Durable scheduler

The application scheduler is disabled by default. Enabling `BACKUP_SCHEDULER_ENABLED=true` causes a singleton, durable `system.backup.requested` outbox event to be created when a backup is due. `BACKUP_SCHEDULER_INTERVAL_SECONDS` defaults to 86,400 seconds and `BACKUP_MISSED_RUN_GRACE_SECONDS` controls missed-run classification. The worker executes the same guarded backup command and records success or sanitized failure in `background_jobs`; overlapping or duplicate schedule buckets are rejected. A full-platform dump uses `BACKUP_SOURCE_DATABASE_URL` when configured and otherwise the isolated `SYSTEM_DATABASE_URL`; it never falls back to the tenant-restricted application role. `BACKUP_OUTPUT_DIR` must be durable, access-controlled storage in deployed environments.

## Verify before restore

```powershell
.venv\Scripts\python.exe scripts\ops\guarded_restore.py backups\offline\dentix_backup_YYYYMMDD_HHMMSSZ.dump.enc
```

This validates manifest metadata, artifact size/hash, AES-GCM authentication, the decrypted database format, integrity, and schema revision without changing a target database. PostgreSQL dumps are parsed with `pg_restore --list`; SQLite dumps are replayed into an in-memory database and checked with `PRAGMA integrity_check`.

## Apply to an empty guarded target

After stopping application writes and setting an explicitly local/test `DATABASE_URL`:

```powershell
$env:LOCAL_DESTRUCTIVE_TESTS = "1"
.venv\Scripts\python.exe scripts\ops\guarded_restore.py backups\offline\dentix_backup_YYYYMMDD_HHMMSSZ.dump.enc --confirm-destructive-restore
```

Run Alembic preflight, health checks, tenant isolation checks, row counts/checksums, and a clinical read-only smoke test before reopening traffic. A PostgreSQL `pg_dump`/`pg_restore` exercise is a required pre-production gate and was not executed on the local workstation used for this remediation.
