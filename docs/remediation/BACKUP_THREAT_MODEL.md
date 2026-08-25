# DENTIX Database Backup Threat Model

| Threat | Impact | Implemented mitigation |
|---|---|---|
| Unauthorized HTTP dump/restore | Full PHI disclosure or database destruction | Raw database HTTP surfaces retired; offline CLI only |
| Artifact tampering | Corrupt or malicious restore | SHA-256 manifest plus authenticated AES-256-GCM decryption before format verification |
| Plaintext backup at rest | PHI disclosure from disk/bucket | Raw snapshot exists only as a mode-`0600` file in the operating-system temporary directory, is removed in `finally`, and the persisted artifact is encrypted |
| Credential exposure in process arguments | Password visible in process listings | PostgreSQL connection values passed through `PG*` environment variables, never URL arguments to `pg_dump`, `psql`, or `pg_restore` |
| Restore to production/wrong database | Destructive data loss | Target guard, explicit confirmation, `LOCAL_DESTRUCTIVE_TESTS=1`, and empty-target checks |
| Key stored with backup | Encryption provides no useful separation | Operational requirement to store `DENTIX_BACKUP_ENCRYPTION_KEY` in a separate approved secret store |
| False recovery confidence | Backup exists but cannot restore | Dry-run parsing plus schema-revision validation, automated multi-tenant SQLite round-trip invariants, and a mandatory PostgreSQL pre-production restore exercise |

The local test suite proves encrypted multi-tenant SQLite round-trip, attachment-hash preservation, schema-revision parity, wrong-key rejection, authenticated wrong-format rejection, and tamper rejection. It does not substitute for the still-required PostgreSQL `pg_dump`/`pg_restore` recovery exercise.
