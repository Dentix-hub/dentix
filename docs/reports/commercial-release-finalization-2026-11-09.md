# Commercial release finalization — 2026-11-09

**Status: PARTIAL — implementation and preparation complete; fresh correction validation and production cutover remain.** This supersedes the operational pending/read-only/retirement statements in [the November 7 report](commercial-release-readiness-2026-11-07.md). Existing offers remain visible. No production migration, protected-branch merge or application deployment was performed by the assistant.

The last hosted candidate is Staging `187a2a2a`; production remains `b5671506`. The correction source is `b6321cbcf501f7589f891cadb9c86df2a857c744`, tree `a659e4525960730226b7523556bef5e56b538b43`. Its independent review and local evidence below do not substitute for fresh PR CI/CD. The base candidate's [CI](https://github.com/Dentix-hub/dentix/actions/runs/42574841898) and [Staging CD/browser smoke](https://github.com/Dentix-hub/dentix/actions/runs/42634187184) passed. The Hugging Face plugin independently returned the corresponding exact Staging and production deployment markers.

## Recovery and native migration access

A fresh production logical backup at **17:10 UTC** used the existing saved recovery key and AES-256-GCM. Its authenticated encrypted artifact was actually restored into isolated PostgreSQL17. All **132 table counts/hashes**, including 91 public tables, matched the same exported read-only source snapshot. Encryption-key custody, external files/object storage, roles/passwords and deployment configuration remain separate recovery material. Refresh the snapshot at the actual deployment boundary if production writes or delay make it stale.

- Encrypted artifact: `dentix_backup_20261109_171030Z.dump.enc` (1,317,809 bytes).
- SHA-256: `cc27bf3135fced46d6b168e83e693ba4efc65bd8049144598c74daae3cf68fdc`.
- Fresh inventory, independently rechecked: **15 tenants / 9 eligible clinics**; older 14/8 figures are superseded.

The supplied native migration connection passed read-only TLS/BYPASSRLS/ownership/migration privilege probes. Additional catalog SELECT/UPDATE, settings SELECT/INSERT/UPDATE, global audit INSERT and audit-sequence USAGE probes also passed. These probes do not prove that an unreadable hosting secret contains the same value; the actual selected connection must pass deployment preflight. No production DDL, role grant or migration was executed.

## Applied production preparation

After an actual restore/preparation/upgrade rehearsal, an explicitly pinned old-schema transaction locked and checked the reviewed catalog/settings snapshot and wrote one truthful platform audit as `release-operator`, without impersonating a clinic user.

| Item | Applied state |
| --- | --- |
| Essential / Professional / Business | Active, nondefault; 200 / 400 / 1,000 EGP, 2 / 5 / 15 seats, 2 / 10 / 30 daily AI |
| Legacy `vib` | Owner-approved AI cap 30; shared capability keys normalized |
| Legacy `trial` | Shared capability keys normalized; original AI cap 10 retained |
| Future signup policy | Professional / 14 days / no card saved in existing settings |
| Existing offers | IDs, prices, durations, seats, patient caps, AI-enabled and active/publication states preserved |
| Existing contracts | No tenant reassignment, security-enable change, expiry edit or clinical/financial record mutation |
| Existing default | Legacy trial deliberately retained until corrected application production CD succeeds |

Independent Supabase reads verified all eight plans, future-trial settings and the single preparation audit. Retaining the old default avoids assigning Professional under old signup semantics, which do not establish a trial end. The corrected signup uses the explicit Professional/14 policy independently; an audited final default switch is prepared for the successful-production-CD boundary.

## Owner-approved renewal compatibility

The owner explicitly chose **“حافظ على مدة القديم؛ الجديد شهري”**. Production old durations are 14/30/30/30/**3650** days; Staging's separately reviewed fifth legacy offer is **6000** days. No existing expiry changes. The three new tiers renew by one calendar month.

Separately installation-bound approvals for the exact full eight-plan catalog were persisted and audited on production and Staging. Each stores original IDs/names/durations and a different installation UUID in existing global settings. Independent reads verified one approval audit per environment and **no applied preflight marker**. Production remains at `f3c4d5e6a7b8`; Staging remains at `3b4c5d6e7f8a`. These writes contain approval metadata only: no plan-unit, tenant-period or schema change. An initial operator SQL identifier error rejected its transaction before writes; the corrected guarded transaction succeeded.

The existing authoritative startup preflight applies the approved data-only compatibility after Alembic and before serving traffic. It locks the approval and full catalog, rejects malformed/cross-installation/incomplete/drifted cohorts, switches only approved legacy units to `day`, increments changed plan revisions, and commits a truthful audit plus approval-hash marker atomically. New tiers stay `month`. Repeated starts do not reapply the policy or override later explicit administrator edits. Hosted legacy catalogs missing approval fail closed; empty or verifiably launch-only fresh catalogs can seed and restart. No new schema or applied migration edits were introduced.

Receipt previews, payment recording, default support renewals and initial no-end assignment now use the actual stored day/month/year term. Explicit support-day/date requests keep their API. Quote identity includes unit/duration, confirmation locks the target plan, and a receipt must explicitly select the scheduled renewal plan. Both existing admin assignment routes share the original capacity/lifecycle/future-plan/downgrade guards and retain their response contracts.

## Actual restored-data rehearsal

The original full rehearsal restored the encrypted backup, applied preparation/replay, upgraded all eight pending revisions, repeated preflight, and switched Professional default through the audited subscription service. All 15 tenants and clinic/financial hashes were preserved; all nine eligible old contracts retained clinical/billing/history access and intended AI limits.

The corrected source then restored the backup again, prepared the old catalog and installation-bound approval, and executed the exact **`python -m backend.scripts.preflight_migrations` twice**. Both commands exited 0. The first produced five legacy day-unit plans/revision 2 and three monthly launch plans/revision 1. Original clinic/financial hashes and tenant rows stayed identical. A full post-upgrade snapshot was unchanged by the second exact startup. The restored database was removed afterward; the local PostgreSQL server was stopped and its entire cluster, including WAL from the restored data, was removed after verification. The authenticated encrypted backup remains intact.

Private harness failures (socket/client/module-path selection, outdated inventory, SQL driver percent handling and fixture field/constructor mistakes) were corrected with integrity assertions retained. They are not counted as source regressions or hidden as successful runs.

## Independent review and corrections

The owner explicitly authorized read-only review delegation. `gpt-6-astra` (xhigh) reported three confirmed issues before a provider usage limit interrupted it; that attempt is not recorded as complete. A replacement `gpt-6.1-terra` (xhigh) completed the risk-focused cumulative review and final correction recheck of `b6321cbc`.

| Confirmed issue | Implemented correction / regression coverage |
| --- | --- |
| Completion command overwrote its request key with a workflow tuple | Separate task key; completed/override retry returns the same event/version, one event only |
| Earlier historical visit inherited later clinical facts | Historical visits contain submitted facts; live carryover still works and source observations stay unchanged |
| Explicit continuation could copy another patient's notes | Source tenant and verified target-patient identity required before any insert, including historical requests; invalid source returns 404 |
| Provider failure or failed action replay could falsely report success | Transport failures remain UNCERTAIN; enum-only durable chat outcomes distinguish pending/success/failure/confirmation, without storing patient prompts or tool parameters |
| Missing/corrupt old receipt or nested completion could imply success | Unknown outcomes fail closed without redispatch; nested typed analysis cache survives final receipt sealing; counters change once |
| Confirmation replay lost the pending action | Same-parent live pending confirmation is preserved; expired state is not recreated; zero-provider confirmation execution is not claimed to have new end-to-end idempotency guarantees |
| Legacy renewal collapsed to a month, with alternate-route/quote gaps | Native terms, explicit scheduled-plan target, locked quote confirmation, unassigned support compatibility and shared guarded assignment as described above |

Confirmed original defects have executed failing reproductions and subsequent passing regressions. New regression harness mistakes were fixed separately, without weakening existing assertions. The review found **Spec PASS / Standards PASS, zero remaining confirmed HIGH/MEDIUM code findings in sampled scope**. One low pre-existing cumulative whitespace observation remains; the correction diff passes whitespace checks. The reviewer inspected source/tests and coordinator-produced recovery/capability certificates; it did not execute the reported suites. This sampled sensitive clinical, tenancy/RBAC/RLS, AI, subscription/finance and migration/startup boundaries, not every line of the original 375-file baseline delta. The direct main-to-source-correction tree is 380 files, +59,094/-1,963; divergent triple-dot ancestry is not a reliable deployment-content statistic.

## Verification

- Relevant AI/accounting/security/subscription tests: **142 passed**, including real-PostgreSQL accounting, tenant scope, payment preview/replay and alignment concurrency/drift/audit-rollback checks; some lifecycle/unit controls use their normal fixtures.
- Clinical subsystem checks: **86 passed**; the later focused clinical/AI gate also passed all 33 cases, including source-scope cases. Full-suite results below supersede these targeted counts.
- Full frontend: **183 files / 1,211 tests passed**, exit 0. Plan-term UI cases are included.
- Backend Ruff, frontend ESLint, production build/artifact validation and design guardrails command: **PASS**, exit 0. Existing report-only design findings are not a new clean-baseline claim.
- Full backend: **2,069 passed / 1 pre-existing skip / 0 failed**, exit 0; **82.60% coverage** against the unchanged 52% gate. The sole skip is `test_auth_refresh_token`: “Refresh endpoint requires UserSession tracking (request.client.host unavailable in TestClient)”. Its reason was separately confirmed with `-rs`; no skip/assertion was added or weakened. Existing dependency deprecation and shutdown-logger warnings did not change the successful exit code.
- Production finalizer's negative test correctly rejected successful **Staging** CD before DB connection/write (operator exit 1; guard assertion PASS).

## Remaining protected delivery and acceptance

1. Deliver the correction PR to Staging; require fresh authoritative CI, exact-revision Staging CD/smoke and owner acceptance. Earlier successful CI does not certify this diff. Stop active assistant execution after opening the PR; no CI polling loop.
2. Eslam promotes the current validated Staging revision through the protected `staging → main` workflow. The assistant never merges/promotes. Refresh the production recovery point at this boundary. Existing startup preflight is the sole production migration authority, including the approved compatibility transaction.
3. After successful production CD, run the prepared audited default finalizer. It requires successful production deployment of exact current main, inclusion of the reviewed source correction, matching production marker/readiness, deployed schema head, completed hash-bound billing alignment and conflict-free catalog/trial policy. It preserves old/new native term fields and changes only the default selection and corresponding audit/revisions.
4. Verify [production Hugging Face configuration](https://huggingface.co/spaces/dentix/dentix/settings) and bounded synthetic success/quota/replay: `EXTERNAL_AI_PHI_MODE=deidentified`, `EXTERNAL_AI_CONTRACT_APPROVED=false` (or absent). Retain existing credentials and encryption keys. Owner-authorized real-clinic processing does not invent a provider agreement; known filtering limits remain disclosed. Connected HF tools cannot mutate Space variables and no local HF credential is available.
5. General subscription enforcement currently reports OFF/shadow; daily AI quota and seats enforce independently. After corrected deployment and preserved legacy-access checks, set `SUBSCRIPTION_ENFORCEMENT_MODE=enforce` at the authorized hosting boundary and verify active/expired/over-seat/exhausted behavior plus history/RBAC access using synthetic fixtures. Do not change actual clinic dates or security disables for acceptance tests.

The private artifact directory `/home/ubuntu/dentix-task-artifacts/release-finalization-20261109/` contains encrypted backup/manifest, result certificates, reproducible preparation/rehearsal scripts, approved metadata manifests and the post-CD finalizer. Command form: `python finalize_after_production_deploy.py --production-cd-run-id <successful-production-CD-run> --apply`; not executed on production. A verified Git bundle preserves the correction branch locally before remote delivery. Secrets, plaintext backups and patient records are excluded from Git.

Optional SMTP/Drive/storage integrations, arbitrary clinical output accuracy, comprehensive de-identification and a provider contract are not certified by these technical results. They are not silently represented as completed requirements.
