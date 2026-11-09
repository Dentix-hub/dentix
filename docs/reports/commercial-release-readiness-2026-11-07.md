# Commercial release preparation — 2026-11-07

**Status: PARTIAL. Do not promote or open controlled paid sales yet.** Owner Super Admin acceptance is recorded from this conversation. Production operations remain read-only. November 7 rehearsals used synthetic databases; November 9 recovery/upgrade verification used an isolated restored production snapshot, subsequently deleted. No production migration, catalog update, enforcement/privacy change, main merge or deployment was performed.

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
| R04 HIGH, partly resolved November 9 | Selling AI capacity requires functioning authorized provider transport. [privacy preparation](../../backend/services/ai_egress_policy.py#L49) remains authoritative. | Real nonclinical model transport and local AIService/quota/replay now PASS on the prepared fix. Hosted delivery/acceptance and clinical privacy remain unverified. Do not switch hosted privacy mode or fabricate contractual approval to pass it. |

## Review findings — Standards axis

| ID / severity | Invariant and evidence | Disposition |
|---|---|---|
| G01 HIGH → database recovery PASS, November 9 | DEVELOPMENT_WORKFLOW §3 requires a DB snapshot before production migrations. The October 30 artifact alone was insufficient. | Fresh AES-256-GCM production snapshot and isolated PostgreSQL 17 restore now PASS; all 132 table counts/hashes match its exported snapshot. Revalidate freshness before a later cutover. External object storage and recovery secrets remain separate from the logical DB artifact. |
| G02 HIGH, partly resolved November 9 | Additive migration/RLS integrity requires the configured owner to control the affected objects. Production has 77 tables owned by `postgres`, 14 by the app role. | The supplied native migration login passes the existing SELECT-only preflight capability probe, including BYPASSRLS, owner membership and required global-table/sequence privileges. Its installation as the actual hosting migration secret remains UNVERIFIED. Runtime app rights were unchanged. |

**Original finding count: Spec 4; Standards 2 (worst HIGH). Current unresolved gates: Spec 4; Standards 1 (hosting configuration for G02).** G01's database snapshot/restore evidence is now PASS as of November 9. These are deployment/acceptance gates, not newly claimed code regressions. Earlier reproduced PR #369/#370 code defects are closed by merged fixes and stated evidence. This follow-up does not claim a fresh line-by-line review of all 364 changed files.

## Concrete cutover and recovery sequence — prepared, not authorized to execute

1. Recheck exact protected staging HEAD, its successful smoke, direct production tree delta and the current metadata snapshot. Any drift invalidates this action manifest. Preserve current clinical/financial/user rows and explicit security disables.
2. Obtain a fresh encrypted production snapshot, checksum and restore evidence in an isolated restricted environment. Confirm the configured migration owner can perform the actual additive DDL/RLS operations; a successful administrator SELECT does not establish that connection's configuration.
3. Resolve signup ordering before the release window. A controlled maintenance window must keep new signup traffic closed until Professional is available. Alternatively, review and approve the old-schema preseed path now rehearsed locally: insert only absent launch plans using old-schema columns, with no existing-row/default changes and an audit entry. It still needs a reviewed production operation and fresh metadata comparison. Preseed alone does not activate the Professional/14 policy; protect the remaining configuration window. Never run the new ORM/service against the old production schema.
4. Under explicit production authorization, promote the current validated staging revision through the protected workflow. Startup's sole authoritative [preflight](../../scripts/deployment/startup.sh#L40) upgrades before Uvicorn. Do not execute raw hosted DDL from this report, stamp an existing schema, run parallel migration authorities or edit applied migrations.
5. Before reopening affected traffic, use the audited admin service with current revisions/reasons to normalize the legacy trial capabilities and explicitly clear its default, apply approved `vib=30` plus shared capabilities, create/verify the three launch plans, set Professional default and persist the future Professional/14 trial. Preserve every original tenant row, plan ID, end/grace/start date, price, duration, seat cap and security flag. The private action manifest records these exact fields. Existing trials without ends remain unchanged; review them individually rather than inventing expiry dates.
6. Re-read catalog/diagnostics and require a conflict-free snapshot. Verify all old active contracts retain intended history/access and no old clinic is automatically moved to a launch tier. **Owner decision, November 9: keep legacy offers as they are; do not hide or retire them.** Preserve their current publication/active state. The retirement alternative rehearsed below is withdrawn and is not part of cutover.
7. At an authorized hosting configuration boundary, prove enforced synthetic active/expired/over-seat/AI-exhausted behavior while clinical-history reads retain RBAC/visibility checks. `SUBSCRIPTION_ENFORCEMENT_MODE` is a deployment setting; the diagnostics UI correctly cannot secretly override it. Never globally flip it while legacy normalization is incomplete.
8. With approved provider/privacy configuration and a genuine credential held in hosting secrets, run one nonclinical real-provider request and same-key replay. Verify a genuine result, one consumption unit, no redispatch on replay and no patient content. Current connectors cannot read encrypted hosting secrets or alter Space configuration; do not ask for plaintext secrets in chat.
9. Verify deployed revision/health, production frontend API routing and owner clinical workflows before opening controlled paid sales. Generic green smoke is insufficient evidence for the gates above.

Recovery: record the previous application revision and per-plan before-values. Stop affected new writes through the existing controls while preserving authorized history reads. Do not delete receipts, reservations, patients or users, and do not Alembic-downgrade production. Prefer reviewed roll-forward; restoring a whole database or reverting application code after new-schema writes requires a separately approved data-loss/compatibility assessment. OFF does not undo privacy policy, emergency restrictions or numeric quota admission. Keep additive schema when reverting code unless a separately tested recovery procedure explicitly requires otherwise.

## Evidence and access boundary

Private metadata-only snapshots, projections, scripts, logs and `production-action-manifest.json` are stored under `/home/ubuntu/dentix-task-artifacts/release-readiness-20261107/` with restrictive permissions. They are excluded from Git/bundles. The manifest is reviewable preparation, not an authorized live mutation script. No source/schema/CI change was needed for this preparation.

As of November 7, access supported authenticated metadata SELECTs and GitHub read checks but lacked a native backup/migration connection. The owner supplied that connection and confirmed saving the backup key on November 9; the executed results below supersede that access limitation. Hugging Face configuration control/provider credential and explicit production promotion authorization remain separate. Owner UI acceptance and legacy `vib=30` approval are already settled; do not ask the owner to repeat them.

## Operator handoff — remaining external evidence

No promotion, Space restart/configuration change, production catalog edit or provider request was executed. The following was the November 7 handoff; the dated November 9 evidence below completes its database backup/restore and native credential checks. Continue from the existing action manifest rather than starting a parallel rollout.

| Boundary | Required next evidence / action |
|---|---|
| Backup/recovery | In a secure operator session, provide the source DB connection and existing backup encryption key via secret injection. Execute `scripts/ops/guarded_backup.py` with a pinned matching client toolchain; record UTC time, revision, encrypted-artifact checksum and restricted storage location. Restore into an empty isolated target using `guarded_restore.py` and compare schema/data integrity. Never restore over production to test a backup. Supabase backup metadata alone does not establish this round trip. |
| Migration identity | Inject the existing `MIGRATION_DATABASE_URL` or `OWNER_DATABASE_URL` into the operator/hosting secret store. Use that exact connection to verify current role, native BYPASSRLS, required global-table/sequence privileges and ownership capability across affected objects. Record booleans/role identity without connection URLs or passwords. A connector's `postgres` SELECT session is not proof of the configured migration connection. Do not grant new rights to the app role. |
| Cutover/catalog | Choose the controlled signup window or review the rehearsed preseed alternative; refresh metadata and manifest before any approved action. Apply legacy normalization and `vib=30` through audited services, complete Professional/default/future-trial setup and recheck old contracts before reopening affected traffic. |
| Hosted enforcement | At the hosting configuration boundary, validate `SUBSCRIPTION_ENFORCEMENT_MODE=enforce` only after normalization, then execute synthetic active/expired/over-seat/AI-exhausted acceptance with preserved history access and existing RBAC/visibility. Record the effective runtime mode and deployed revision. |
| Provider/privacy | Configure the real `GROQ_API_KEY` in hosting secrets and confirm the approved `EXTERNAL_AI_PHI_MODE`. Contracted mode additionally requires actual approval before `EXTERNAL_AI_CONTRACT_APPROVED=true`. A Hugging Face inference credential does not validate Dentix's configured Groq transport. Run one bounded nonclinical request plus same-key replay, proving a real result, one consumption unit and no redispatch. |

Credentials belong in the restricted operator file/secret store, not PRs or report content. Native access was supplied on November 9. Remaining hosting/acceptance gates cannot be marked PASS from the recovery evidence alone.

## Executed production recovery and native access — November 9, 2026

The owner's uploaded operator file was parsed as data, installed outside Git with mode 0600 and never printed. The uploaded backup key decoded to 32 bytes and matched the previously generated key that the owner confirmed saving. Both supplied connections authenticated as `postgres` against the production project using client TLS. PostgreSQL's backend `pg_stat_ssl` reports the pooler-to-database leg; client `ssl_in_use=true` verified the external connection. No passwords, URLs or key material are recorded here.

The existing `_release_migration_access(..., needs_ddl=True)` returned **PASS**, exit 0. Read-only checks confirmed native BYPASSRLS, owner capability for all 91 public tables across both owners, global feature/Alembic table privileges and required sequence access. This proves the supplied native login's capability; it does not prove that Hugging Face's startup has that value configured in `MIGRATION_DATABASE_URL`/`OWNER_DATABASE_URL`. Do not replace the restricted runtime app connection with this operator login.

The repository's actual `create_backup`/`verify_and_restore` functions created and authenticated a production logical dump using pinned PostgreSQL 17.11 clients. An exported read-only REPEATABLE READ snapshot was shared with `pg_dump --snapshot` through a private wrapper, so independent source counts/hashes and the dump describe the same database state. The authoritative verified artifact is:

| Field | Evidence |
|---|---|
| Snapshot time / revision | `20261109_033752Z` / `f3c4d5e6a7b8` |
| Artifact | `dentix_backup_20261109_033752Z.dump.enc` and matching `.manifest.json` |
| Encryption / key identifier | AES-256-GCM / `production-release-20261109` |
| Size / SHA-256 | 1,317,233 bytes / `0fb3ebdcaa1930e5fb15e6337f3f5a1751dfe81f79bd960aa97204076d772ec8` |
| Restricted artifact directory | `/home/ubuntu/dentix-task-artifacts/release-readiness-20261109/verified-production-backup/`, directory 0700, artifacts 0600 |
| Restored data verification | All **132 tables**, including **91 public tables**, matched source row counts and hashes |
| Restored integrity metadata | 185 public foreign keys, none unvalidated; 60 public tables retained ENABLE + FORCE RLS |

A password-protected, loopback-only isolated PostgreSQL 17.11 runtime was assembled outside the repository, including the actual Vault 0.3.1 source and vector extension. Guarded atomic restore completed successfully. An inherited source-only `PGSSLMODE=require` initially prevented the local SSL-less connection; source TLS stayed required while the local fixture used SCRAM authentication. The first comparison then found one hash mismatch in `procedure_material_weights`, with equal row counts. Investigation proved source `extra_float_digits=0` versus local default 1. Matching the verification session's serialization restored exact equality across all 132 original table assertions; a separate `float8send` binary digest also confirmed unchanged material-weight floating-point values. No values or assertions were altered to conceal a mismatch.

The existing authoritative preflight was then executed on this **real restored schema/data**, not the earlier synthetic baseline: **PASS**, `f3c4d5e6a7b8 → 3b4c5d6e7f8a`; public tables increased 91→96. Original-column hashes/counts were preserved in 130 of the 132 original tables; only Alembic bookkeeping and the reviewed global feature-flag policy changed. A second preflight/health invocation passed without further original-column changes. Local superuser ownership is a limitation of this restoration rehearsal; restricted-role CI evidence and hosted runtime acceptance remain separate.

Executed commands (each final command exit 0; these are scripts, not pytest counts):

```text
/home/ubuntu/dentix/.venv/bin/python /home/ubuntu/dentix-task-artifacts/release-readiness-20261109/finalize_recovery_verification.py
/home/ubuntu/dentix/.venv/bin/python /home/ubuntu/dentix-task-artifacts/release-readiness-20261109/rehearse_restored_production_upgrade.py
```

Private result certificates, snapshot digests and scripts remain under `/home/ubuntu/dentix-task-artifacts/release-readiness-20261109/`. The local server was stopped and its entire plaintext restored cluster deleted after verification; only encrypted database artifacts and restricted verification records remain. The logical dump deliberately excludes ownership/ACL restoration and does not contain role passwords, external encryption keys or Storage object bytes. Original ownership/grant reconstruction and hosted service operation were not certified. Preserve the owner's existing application/tenant keys and the separately saved backup key as recovery material.

GitHub protected refs and Hugging Face deployment markers were re-read: production remains `b5671506`, Staging remains `86f80c14`. There was no hosted DDL/DML, deployment, privacy/enforcement change, catalog normalization or provider dispatch. Remaining work is hosting migration-secret configuration, controlled signup/catalog ordering and legacy normalization, enforced hosted acceptance, real-provider/privacy acceptance, and final promotion review/authorization. A later cutover must obtain a fresh snapshot if the November 9 artifact is no longer current enough for its recovery window.

## Staging acceptance and retirement preparation — November 9, 2026

The owner's production Settings screenshot confirms secrets named `MIGRATION_DATABASE_URL` and `GROQ_API_KEY` exist. Their hidden values were not inspected or replaced. Presence narrows the configuration question but does not prove that the hosted migration URL equals the independently tested native connection, nor that the provider credential works. G02's remaining hosting verification is unchanged. There are no open PRs; the exact `86f80c14` candidate still has successful `Dentix CD - HF staging smoke` status.

The existing synthetic release-probe clinic was reused on Staging: no new registration, production requests, patient prompts or real-clinic changes. Login returned 200; its clinic administrator was rejected from the global catalog inventory (403), and unauthenticated entitlement diagnostics returned 401. Effective runtime diagnostics still report `enforcement_mode=off`, `is_shadow=true`, with the synthetic Professional contract. Hosted ENFORCE acceptance is therefore still unproved.

One new logical nonclinical AI request plus same-key replay was executed. The first returned `ai_egress_denied`; the replay returned the existing terminal-reservation response `request_pending` without redispatch. A tenant-restricted Staging SELECT independently confirmed exactly one matching `ai_chat` reservation in RELEASED status. Authoritative reserved/consumed/uncertain/admitted counts stayed at zero and remaining quota stayed at ten before, after the first request and after replay. Historical diagnostic log count rose 0→1→2. The initial probe compared the entire diagnostics object and reported that object unequal; these labelled historical log counts explain the difference. The original result is retained; the separate accounting certificate checks the authoritative quota fields without calling historical logs billing consumption. **Transport remains UNVERIFIED; privacy rejection is not a real provider success.**

Read-only Staging inventory confirms the three launch plans and saved Professional/14 policy. Legacy trial/basic/pro/enterprise offers are inactive, while a separate `VIP` offer remains active with zero AI capacity. The existing production approval `vib=30` does not authorize changing Staging VIP's numeric benefit. Any global enforcement test still requires reviewing linked legacy grants and expired contracts before changing the Space-wide mode.

The optional three-public-tier retirement path was executed on synthetic PostgreSQL 17 using actual `SubscriptionService`, `EntitlementService` and `AIQuotaService`: **PASS**, script exit 0. After the already-rehearsed preservation/setup sequence, all five old production-like offers (trial/basic/pro/enterprise/vib) were retired through `delete_plan`, producing five audit records. Only `is_active` and `policy_revision` changed in each old plan. Active catalog became exactly Essential/Professional/Business; all fourteen original synthetic tenant rows, eight eligible linked contracts, approved trial/vib numeric limits, future Professional/14 policy and synthetic patient/payment history remained unchanged. **The owner subsequently rejected retirement: this result is historical evidence only, and the live retirement action manifest is CANCELLED_BY_OWNER.** No hosted offer was hidden or retired by this work. It does not replace hosted HTTP/RBAC acceptance or the stronger-model cumulative promotion review.

Executed preparation commands, exit 0:

```text
/home/ubuntu/dentix/.venv/bin/python /home/ubuntu/dentix-task-artifacts/release-readiness-20261109/staging_acceptance_probe.py
/home/ubuntu/dentix/.venv/bin/python /home/ubuntu/dentix-task-artifacts/release-readiness-20261109/rehearse_legacy_catalog_retirement.py
```

The first command truthfully reports PARTIAL. The new retirement fixture initially failed to parse because its embedded SQL string was quoted incorrectly; fixing that fixture string enabled the real assertions, which were not removed or weakened. The synthetic cluster was stopped and removed after the passed run. Private result certificates and `catalog-retirement-action.json` / `staging-provider-test-action.json` are in the existing November 9 artifact directory. Neither manifest is a live mutation command.

The previously proposed next provider test was a temporary `EXTERNAL_AI_PHI_MODE=deidentified` change on `dentix/dentix-staging`, subject to explicit owner approval. This would affect every AI request in that Space. **Hold that proposal:** the owner's follow-up asks what is needed to enable AI, rather than explicitly approving Space-wide privacy changes. A subsequent source/provider review also found obsolete model IDs and limited regex-only de-identification coverage. Prefer an isolated nonclinical provider compatibility check before proposing any live egress-policy change. Production, enforcement and contractual-approval markers remain unchanged; R04 remains open.

## Owner decision and provider compatibility fix — November 9, 2026

The owner explicitly selected **keep the legacy offers as they are**. Do not hide, retire, reprice or reassign them under this preparation. No hosted retirement was ever executed. The private retirement action is cancelled; its synthetic test result is historical only.

Provider review found the routing/direct-analysis Llama defaults restricted to enterprise contracts on ordinary Groq tiers, and Scribe still using a model retired for all accounts. This adds a compatibility risk after the current privacy denial, without proving the hidden credential's account tier. See [Groq's deprecation history](https://console.groq.com/docs/deprecations).

A separate local implementation on `fix/groq-supported-models`, commit `edcfbac7`, based on the exact current Staging candidate, now shares supported fast/complex defaults across chat/direct analysis/Scribe and permits explicit account overrides. New defaults are `openai/gpt-oss-20b` / `openai/gpt-oss-120b`, listed in [Groq production models](https://console.groq.com/docs/models). Existing recorded costs and legacy analytics fallback estimates are preserved; privacy, quotas, clinical extraction rules and tenant/RBAC checks are unchanged. **37 targeted tests PASS**, including eleven new compatibility cases and real PostgreSQL privacy/accounting/replay verification; Ruff/whitespace PASS. The first regression failed before the fix. Its own report is `docs/reports/groq-model-compatibility-2026-11-09.md` on that branch; a verified bundle is stored privately. This fix has not been pushed, merged or deployed, and does not yet change `86f80c14`'s hosted behavior.

The owner subsequently supplied the separate local test credential through `/home/ubuntu/dentix-task-artifacts/groq-test.env`, installed with mode 0600 and never printed. The existing hosted secret was not replaced. The executed result below supersedes the earlier request for a test credential. The proposed Space-wide privacy change remains held.

## Genuine provider and local accounting proof — November 9, 2026

Authenticated model discovery and two fixed nonclinical calls through the prepared source's actual `_call_llm_safe` succeeded on `openai/gpt-oss-20b` and `openai/gpt-oss-120b`. Both returned the exact technical JSON marker with finish reason `stop`. No clinical/database context was present. The probe added a 1,024-completion-token bound and disabled automatic SDK retries; it did not mock the provider response or edit a Space setting.

The full local service probe exposed a reproducible false-positive denial: the generated static prompt contained bare identity-field labels (`اسم المريض` / `patient name`) that the unchanged de-identification confidence gate rejected, even with an empty synthetic clinic. A new regression failed before the fix. Only built-in literal parameter descriptions and two static schema instructions were reworded; dynamic user/history/RAG/last-entity content still goes through the full guard. The guard, permissions, tool names/keys and clinical extraction rules were not weakened. An independent AST comparison confirmed unchanged tool roles and parameter keys. The failed local certificate records zero provider dispatches and no quota charge.

After this correction, a real `AIService.process_query` call against a synthetic local PostgreSQL 17 clinic returned the technical marker, consumed one unit (remaining 10→9), and same-key replay succeeded with remaining nine and one provider invocation total. Exactly one CONSUMED reservation existed; reserved/uncertain counts remained zero. No patient rows were seeded. The local fixture's inherited DB SSL default initially required correction for its SSL-less loopback server; hosted/source TLS settings were unchanged. Synthetic servers/clusters were stopped and removed after verification.

The final fix is on local `fix/groq-supported-models` at `beff1639`, based on Staging `86f80c14`. **44 targeted tests PASS**, including eighteen new model/prompt compatibility cases and real PostgreSQL privacy/accounting tests; Ruff/whitespace PASS. Two genuine model probes plus one genuine service request used three completion calls total; replay added no provider call. This is real provider/service evidence, but it is not hosted HTTP/RBAC or clinical privacy acceptance. The branch remains unpushed and unmerged; its verified bundle and sanitized result certificates are outside Git in the existing artifact directory.

Executed real probes, exit 0:

```text
PYTHONPATH=/home/ubuntu/dentix-ai-model-compatibility /home/ubuntu/dentix/.venv/bin/python /home/ubuntu/dentix-task-artifacts/release-readiness-20261109/groq_nonclinical_provider_smoke.py
/home/ubuntu/dentix/.venv/bin/python /home/ubuntu/dentix-task-artifacts/release-readiness-20261109/groq_live_accounting_smoke.py
```

Next step is explicit remote-delivery authorization for the prepared code PR to Staging, followed by the repository's CI/review/deployment workflow and approved hosted acceptance. Production still runs the earlier revision; no production catalog, privacy, quota, migration or legacy-offer changes were performed. Clinical egress still requires an approved privacy arrangement; regex compatibility tests are not an anonymity benchmark. Main promotion and the stronger-model cumulative review remain separate required steps.
