# Commercial release preparation — 2026-11-07

**Status: PARTIAL. Do not promote or open controlled paid sales yet.** Owner Super Admin acceptance is recorded from this conversation. Production inspection was read-only; all mutation rehearsals used disposable local synthetic databases. No production migration, catalog update, enforcement/privacy change, main merge or deployment was performed.

## Candidate and verified delivery

- Candidate: staging `86f80c1481c977d2c3e318034a914568f7657812`; production base: `b567150629af5c4499f085b341f6800f3d03a38f`.
- Exact-candidate staging smoke succeeded: [CD 42258229036](https://github.com/Dentix-hub/dentix/actions/runs/42258229036). Commit status was checked again on November 7. Do not infer production deployment from it.
- The actual main-to-staging tree delta is 364 files, 57,068 added / 1,902 removed lines. Divergent ancestry makes triple-dot statistics larger; use the direct tree comparison for deployment contents.
- PR #369 closed the previously reproduced downgrade/async-policy/RLS/error/audit defects; PR #370 closed charged pre-dispatch privacy denials. The earlier [readiness review](production-readiness-commercial-2026-11-06.md) and [accounting review](ai-pre-dispatch-accounting-2026-11-06.md) retain their executed local evidence. Their pending hosted claims are updated here, rather than rewriting historical reports.
- Hosted synthetic chat on the corrected candidate returned `ai_egress_denied`; its reservation was RELEASED. Same-key replay was free. Consumed/reserved/uncertain/remaining values stayed unchanged. A canonical FAILURE log was verified in that synthetic tenant only. This establishes rejection/accounting correctness, **not a successful provider response**.
- Authenticated Staging diagnostics still showed `enforcement_mode=off`, `is_shadow=true`. Production runtime environment values remain unverified. Empty database policy settings do not prove environment-variable values.

## Read-only hosted inventory

Counts below describe the captured November 7 metadata, not a permanent guarantee. An eligible clinic is active, not deleted and has a non-platform account. No patient rows, tenant names, email addresses or phone numbers were queried for this inspection.

| Evidence | Staging | Production |
|---|---:|---:|
| Alembic revision | `3b4c5d6e7f8a` | `f3c4d5e6a7b8` |
| Tenant rows | 186 | 14 |
| Eligible clinics | 185 | 8 |
| Eligible clinics over their current seat cap | 0 | 0 |
| Eligible clinics without a subscription end date | 174 | 5 |
| Approved Essential / Professional / Business catalog | Present, 200/400/1000 EGP | Absent |
| Saved future trial policy | Professional / 14 days | Absent |

Production has five active legacy `trial` clinics with no end date and three active legacy `vib` clinics. Preserve these existing records; configuring a fourteen-day trial for future registrations must not retroactively expire them. Six disabled tenant rows remain disabled. No tenant reassignment or destructive cleanup is proposed.

Production `vib` is AI-enabled with limit zero. Old main skipped numeric enforcement at zero; candidate [AIQuotaService:165](../../backend/services/ai_quota_service.py#L165) resolves it to zero admission. This affects numeric admission even while general commercial enforcement is OFF. **Owner approved 30 requests per clinic-local day for these existing contracts**, preserving their price, duration and user cap. That approval has not been applied to production.

Legacy Arabic feature labels are unrecognized commercial keys; they are not all malformed JSON. Staging old offers 1–4 are now inactive, while their linked existing contracts remain present. Retirement alone must not revoke a valid linked contract.

## Executed offline impact assessment

The projection copied captured plan, tenant, override, flag and account-count metadata into temporary local SQLite databases, then executed the current canonical entitlement, feature-flag, seat-cap and AI-limit services. It did not connect those models to a hosted database. Results cover the commercial layer; RBAC, patient visibility, provider availability and real concurrent HTTP traffic remain independent checks.

| Production scenario, eight eligible clinics | Clinical writes denied | Billing writes denied | History commercially allowed | Numeric AI limit zero |
|---|---:|---:|---:|---:|
| Captured catalog, projected ENFORCE | 8 | 8 | 8 | 3 |
| Pending migration's native-clinical activation included | 8 | 8 | 8 | 3 |
| Explicit shared legacy capability normalization proposed | 0 | 0 | 8 | 3 |
| Same proposal plus owner-approved `vib=30` | 0 | 0 | 8 | 0 |

Current Staging has 181/185 projected clinical/billing denials before normalization. Normalization reduces that to one already-expired legacy contract; history remains commercially readable for all 185. This is why flipping a global flag without reviewing existing contracts is unsafe.

The feature-normalization rows are proposals, not proof that a features-only API edit always succeeds. [SubscriptionService:261](../../backend/services/subscription_service.py#L261) validates resulting AI consistency. Unused production `pro` has AI disabled with a positive stored cap; `enterprise` has AI enabled with zero cap. Leave those unused offers unchanged in this minimal preservation proposal. Retiring or changing them needs an explicit compatible operation; do not silently invent a new AI benefit.

## Executed PostgreSQL rehearsal

`rehearse_release.py` created a uniquely named disposable database on local PostgreSQL 14. It imported the exact old-main models, installed old preflight RLS/restore guards, seeded captured commercial metadata with synthetic identities and one synthetic clinical/payment example, and stamped the captured production revision. It then executed current preflight upgrade and health verification through all eight pending revisions.

Result: **PASS**, `f3c4d5e6a7b8 → 3b4c5d6e7f8a`; 72 baseline tables became 77. Original-column hashes and counts stayed unchanged in 70 original tables; only the expected global feature-flag policy data changed. A second preflight passed without changing original-column data. The database was dropped in cleanup.

The first fixture attempts lacked PostgreSQL functions that ORM `create_all` does not install. Installing the actual old preflight guards corrected the synthetic baseline; no applied migration was edited. Production read-only metadata independently confirmed `dentix_assert_parent_tenant()` exists. Explicit fixture plan IDs also required advancing the local sequence before testing plan creation; this was fixture repair, not a production sequence change.

On that migrated local database, `rehearse_catalog_policy.py` executed actual SubscriptionService updates/creation/trial settings and the catalog preview: **PASS**. Six audit records were written, setup conflicts were zero, future trial resolved Professional/14/no-card, all fourteen original tenant rows were unchanged, and prices/durations/user/patient caps/AI-enabled flags of all five original plans were unchanged. All eight eligible clinics retained projected clinical/billing writes/history, with `trial=10` and approved `vib=30` numeric limits.

Limits: this is a synthetic 72-table baseline, **not a restored production backup** of the hosted 91-table schema. Hosted PostgreSQL is version 17. Local owner-level migration success does not verify the actual hosted migration credentials or replace restricted-role CI evidence. These rehearsals are two scripts with explicit assertions, not an invented pytest pass count.

## Follow-up preparation — November 7, 2026

Live read checks reconfirmed protected `main=b5671506` and `staging=86f80c14`, matching the deployment markers read through the Hugging Face plugin in [production](https://huggingface.co/spaces/dentix/dentix) and [Staging](https://huggingface.co/spaces/dentix/dentix-staging). Both Spaces were RUNNING and returned HTTP 200 for health and readiness, with database UP. The candidate's recorded staging-smoke status remained successful; there were no open PRs. Direct tree statistics remained 364 files, +57,068/-1,902. These observations establish revision/availability, not commercial acceptance.

A fresh production metadata SELECT reconfirmed revision `f3c4d5e6a7b8`, 91 public tables (77 owned by `postgres`, 14 by the NOBYPASSRLS app role), zero launch plans, zero saved future-trial settings, legacy trial still default and `vib` AI limit still zero. No patient rows or tenant identities were read. The native production backup/migration connection and backup encryption key are absent from this execution environment. The available Supabase tools do not expose backup listing/download, and the Hugging Face tools do not manage the running Spaces' variables/secrets. OAuth repository/inference access is not proof of those capabilities.

The previously untested preseed alternative now has a **PASS on a disposable local PostgreSQL 14 fixture**. Executed command, exit 0:

```text
/home/ubuntu/dentix/.venv/bin/python /home/ubuntu/dentix-task-artifacts/release-readiness-20261107/rehearse_preseed_followup.py
```

The fixture imported the actual old-main ORM and captured global commercial metadata with synthetic identities. It inserted the approved Essential/Professional/Business values using old-schema columns only, with all three new defaults FALSE and an audit entry. All five original plan rows and the existing default were unchanged. Repeating the preseed changed no rows or audit count. This is a local fixture operation, not a production mutation command or a newly authorized direct-SQL path.

The same run executed the repository's encrypted backup, authenticated verification and actual restore into a second empty local database. Original-column counts/hashes matched across all 71 data tables; the 72nd baseline table was Alembic bookkeeping. The restored database then passed the existing preflight upgrade/health path to `3b4c5d6e7f8a`, preserving old-column data except the expected global feature policy. This tests the synthetic recovery mechanics; **G01 remains open for a fresh hosted-production backup and isolated restore**. Its disposable synthetic encryption key was discarded and is not a production recovery key.

On the migrated restored fixture, the actual audited services normalized trial/`vib`, applied approved `vib=30`, explicitly made Professional default and applied catalog/trial setup using its current snapshot. Setup created no duplicate plans and ended conflict-free at Professional/14/no-card. All fourteen original tenant rows were unchanged; all eight eligible contracts retained projected clinical/billing/history access and the intended AI limits. Protected price/duration/seat/patient/active/AI-enabled fields were unchanged on all eight plans; unused `basic`, `pro` and `enterprise` rows were checked in full and stayed unchanged. HTTP/RBAC and genuine provider acceptance remain separate gates.

Two fixture/tooling failures preceded the successful run: database creation initially used a transaction context, and the system PostgreSQL wrapper selected `pg_dump` 17 with connection variables while selecting `pg_restore` 14 without them. The runner now uses autocommit outside that context and pins both tools to PostgreSQL 14. No application assertions or migration files were weakened or edited. A production operator must explicitly select a matching PostgreSQL 17-or-newer dump/restore pair for the hosted version; local PATH defaults are not sufficient evidence.

## Review findings — Spec axis

| ID / severity | Requirement, source and impact | Disposition |
|---|---|---|
| R01 HIGH | Capacity-first controlled sales require effective runtime enforcement. [config:28](../../backend/core/config.py#L28) defaults OFF; observed Staging is OFF. Legacy feature labels would deny all eight current production clinics under ENFORCE. | Snapshot-bound normalization proposal and executed local projection prepared. Apply only after authorization, reviewed current inventory and hosted enforcement acceptance. Do not advertise restrictions as active yet. |
| R02 HIGH | Existing contracts must survive rollout. [AIQuotaService:165](../../backend/services/ai_quota_service.py#L165) treats zero as zero; three existing contracts previously bypassed the numeric cap. | Owner approved 30/day; local service rehearsal passes. Apply the approved value before admitting production traffic to the new quota implementation. General OFF is not a rollback for this numerical difference. |
| R03 HIGH | New registrations must receive Professional/14/no-card. [register:77](../../backend/routers/auth/register.py#L77) rejects missing Professional; [catalog preview:70](../../backend/services/catalog_setup_service.py#L70) correctly refuses silently replacing the existing legacy default. | Post-migration service ordering and the old-schema preseed/recovery alternative now pass locally. Production signup ordering, authorization and hosted acceptance remain open. Preseed preserves the old default; it does not itself activate the future trial policy. |
| R04 HIGH | Selling AI capacity requires functioning authorized provider transport. Privacy-denied replay is correct but provides no real response. [privacy preparation](../../backend/services/ai_egress_policy.py#L49) remains authoritative. | Genuine bounded nonclinical provider smoke remains UNVERIFIED. Do not switch privacy mode or fabricate contractual approval to pass it. |

## Review findings — Standards axis

| ID / severity | Invariant and evidence | Disposition |
|---|---|---|
| G01 HIGH | DEVELOPMENT_WORKFLOW §3 requires a DB snapshot before production migrations. An October 30 encrypted recovery artifact is historical evidence, not a fresh cutover backup. | Fresh encrypted backup plus isolated restore verification still required. No current backup/restore certificate was obtainable through the available connector; no patient-data export was attempted. |
| G02 HIGH | Additive migration/RLS integrity requires the configured owner to control the affected objects. Production has 77 tables owned by `postgres`, 14 by the app role. App is NOBYPASSRLS and not a member of the BYPASSRLS system role. | Actual hosting OWNER/MIGRATION connection and DDL ownership capability remain UNVERIFIED. Do not widen the runtime app role or drop FORCE RLS to make deployment pass. |

**Finding count: Spec 4 (worst HIGH); Standards 2 (worst HIGH).** These are open deployment/acceptance gates, not six newly claimed code regressions. Earlier reproduced PR #369/#370 code defects are closed by merged fixes and stated evidence. This follow-up inspects commercial execution, migration/configuration and recovery boundaries; it does not claim a fresh line-by-line review of all 364 changed files.

## Concrete cutover and recovery sequence — prepared, not authorized to execute

1. Recheck exact protected staging HEAD, its successful smoke, direct production tree delta and the current metadata snapshot. Any drift invalidates this action manifest. Preserve current clinical/financial/user rows and explicit security disables.
2. Obtain a fresh encrypted production snapshot, checksum and restore evidence in an isolated restricted environment. Confirm the configured migration owner can perform the actual additive DDL/RLS operations; a successful administrator SELECT does not establish that connection's configuration.
3. Resolve signup ordering before the release window. A controlled maintenance window must keep new signup traffic closed until Professional is available. Alternatively, review and approve the old-schema preseed path now rehearsed locally: insert only absent launch plans using old-schema columns, with no existing-row/default changes and an audit entry. It still needs a reviewed production operation and fresh metadata comparison. Preseed alone does not activate the Professional/14 policy; protect the remaining configuration window. Never run the new ORM/service against the old production schema.
4. Under explicit production authorization, promote the current validated staging revision through the protected workflow. Startup's sole authoritative [preflight](../../scripts/deployment/startup.sh#L40) upgrades before Uvicorn. Do not execute raw hosted DDL from this report, stamp an existing schema, run parallel migration authorities or edit applied migrations.
5. Before reopening affected traffic, use the audited admin service with current revisions/reasons to normalize the legacy trial capabilities and explicitly clear its default, apply approved `vib=30` plus shared capabilities, create/verify the three launch plans, set Professional default and persist the future Professional/14 trial. Preserve every original tenant row, plan ID, end/grace/start date, price, duration, seat cap and security flag. The private action manifest records these exact fields. Existing trials without ends remain unchanged; review them individually rather than inventing expiry dates.
6. Re-read catalog/diagnostics and require a conflict-free snapshot. Verify all old active contracts retain intended history/access and no old clinic is automatically moved to a launch tier. Keep unused legacy offers unchanged in this proposal. Before offering **only** three public tiers, complete explicit retirement handling for unused legacy rows; the present report does not certify that operational cleanup.
7. At an authorized hosting configuration boundary, prove enforced synthetic active/expired/over-seat/AI-exhausted behavior while clinical-history reads retain RBAC/visibility checks. `SUBSCRIPTION_ENFORCEMENT_MODE` is a deployment setting; the diagnostics UI correctly cannot secretly override it. Never globally flip it while legacy normalization is incomplete.
8. With approved provider/privacy configuration and a genuine credential held in hosting secrets, run one nonclinical real-provider request and same-key replay. Verify a genuine result, one consumption unit, no redispatch on replay and no patient content. Current connectors cannot read encrypted hosting secrets or alter Space configuration; do not ask for plaintext secrets in chat.
9. Verify deployed revision/health, production frontend API routing and owner clinical workflows before opening controlled paid sales. Generic green smoke is insufficient evidence for the gates above.

Recovery: record the previous application revision and per-plan before-values. Stop affected new writes through the existing controls while preserving authorized history reads. Do not delete receipts, reservations, patients or users, and do not Alembic-downgrade production. Prefer reviewed roll-forward; restoring a whole database or reverting application code after new-schema writes requires a separately approved data-loss/compatibility assessment. OFF does not undo privacy policy, emergency restrictions or numeric quota admission. Keep additive schema when reverting code unless a separately tested recovery procedure explicitly requires otherwise.

## Evidence and access boundary

Private metadata-only snapshots, projections, scripts, logs and `production-action-manifest.json` are stored under `/home/ubuntu/dentix-task-artifacts/release-readiness-20261107/` with restrictive permissions. They are excluded from Git/bundles. The manifest is reviewable preparation, not an authorized live mutation script. No source/schema/CI change was needed for this preparation.

Available access supports authenticated metadata SELECTs and GitHub read checks. It does not provide the production native migration/backup connection or Hugging Face configuration control/provider credential. Completing these external operations requires an authorized secure operator/session and explicit production authorization. Owner UI acceptance and the legacy `vib=30` policy are already settled; do not ask the owner to repeat them.

## Operator handoff — remaining external evidence

No promotion, Space restart/configuration change, production catalog edit or provider request was executed in this follow-up. All six live gates remain open. Continue from the existing action manifest rather than starting a parallel rollout.

| Boundary | Required next evidence / action |
|---|---|
| Backup/recovery | In a secure operator session, provide the source DB connection and existing backup encryption key via secret injection. Execute `scripts/ops/guarded_backup.py` with a pinned matching client toolchain; record UTC time, revision, encrypted-artifact checksum and restricted storage location. Restore into an empty isolated target using `guarded_restore.py` and compare schema/data integrity. Never restore over production to test a backup. Supabase backup metadata alone does not establish this round trip. |
| Migration identity | Inject the existing `MIGRATION_DATABASE_URL` or `OWNER_DATABASE_URL` into the operator/hosting secret store. Use that exact connection to verify current role, native BYPASSRLS, required global-table/sequence privileges and ownership capability across affected objects. Record booleans/role identity without connection URLs or passwords. A connector's `postgres` SELECT session is not proof of the configured migration connection. Do not grant new rights to the app role. |
| Cutover/catalog | Choose the controlled signup window or review the rehearsed preseed alternative; refresh metadata and manifest before any approved action. Apply legacy normalization and `vib=30` through audited services, complete Professional/default/future-trial setup and recheck old contracts before reopening affected traffic. |
| Hosted enforcement | At the hosting configuration boundary, validate `SUBSCRIPTION_ENFORCEMENT_MODE=enforce` only after normalization, then execute synthetic active/expired/over-seat/AI-exhausted acceptance with preserved history access and existing RBAC/visibility. Record the effective runtime mode and deployed revision. |
| Provider/privacy | Configure the real `GROQ_API_KEY` in hosting secrets and confirm the approved `EXTERNAL_AI_PHI_MODE`. Contracted mode additionally requires actual approval before `EXTERNAL_AI_CONTRACT_APPROVED=true`. A Hugging Face inference credential does not validate Dentix's configured Groq transport. Run one bounded nonclinical request plus same-key replay, proving a real result, one consumption unit and no redispatch. |

Required access is an operator/session capability, not plaintext credentials in chat. A secure session was requested during the follow-up; until it is available, local preparation can be preserved but these live gates cannot truthfully be marked PASS.
