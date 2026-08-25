# DENTIX Database Backup Threat Model

## 1. Threat Analysis

| Threat ID | Threat Vector | Impact | Mitigation in DENTIX |
|---|---|---|---|
| `TM-BKP-01` | Unauthorized HTTP download of database dump | Severe data breach (all tenant PHI exposed) | **ADR §4**: HTTP database raw download endpoints permanently removed (`410 Gone`). |
| `TM-BKP-02` | Unauthorized HTTP restore / database wipe | Complete data loss or malicious state tampering | HTTP restore endpoints permanently removed (`410 Gone`). |
| `TM-BKP-03` | Compromised backup archive tampering | Corrupted database restoration or backdoors | SHA-256 integrity manifest generated and verified prior to any restore. |
| `TM-BKP-04` | Credential leakage in backup process argv | Database credentials exposed in process table (`ps aux`) | Connection parameters passed via `pgpass` / environment variables, never command line args. |
| `TM-BKP-05` | Unencrypted backup archive storage | Unauthorized physical or bucket access to dumps | Off-site backups encrypted at rest with AES-256. |
