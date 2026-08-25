# DENTIX Clinical Data Processing & AI Egress Policy

## 1. Scope & Privacy Principles
- All patient clinical records, appointments, dental charts, and billing transactions are stored locally within the tenant's PostgreSQL database with RLS enforcement.
- External AI services (e.g. Groq Whisper / LLMs) are strictly gated:
  - `AI_SERVICE_ENABLED=false` by default.
  - Zero raw Egyptian National IDs, phone numbers, or unredacted payment cards are transmitted externally.
  - De-identification pipeline strips direct identifiers prior to prompt assembly.

---

## 2. Processing Stages

| Processing Stage | Data Elements Involved | Storage Location | Egress Controls |
|---|---|---|---|
| **Clinical Charting** | Tooth condition, diagnoses, procedures | Local Tenant PostgreSQL | Zero external egress |
| **Voice Dictation** | Audio WAV / MP3 snippets | Ephemeral memory / tempfile | Deleted immediately post-transcription |
| **Financial Summaries**| Aggregated totals, category sums | Local Tenant PostgreSQL | De-identified aggregates only |
| **Audit Trail** | User actions, tenant IDs, timestamps | Append-only `audit_logs` | Local Tenant PostgreSQL |
