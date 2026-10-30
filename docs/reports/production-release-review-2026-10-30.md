<!-- CLASSIFICATION: ACTIVE -->
# Production release — final cumulative technical review, 2026-10-30

**Technical result: PASS for promotion with existing rollout settings preserved.**
Reviewer: Codex, cumulative main-to-staging review in the release session.
Eslam's acceptance is recorded by the protected review/merge of this review-record PR.
This document records technical review; it does not claim production is deployed,
that every optional integration is configured, or that clinical rollout flags were enabled.

## Reviewed revisions and scope

- Production/main: `1b7c1bdc98246611feee96dffa3d9298a4a9cd43`.
- Reviewed staging: `ebb98e44ff4bad8a2de773eb220fd5d8fecbb02d`.
- Validated PR #329 head: `ac8fd45154ae7c072d571e7e8d106af59de90bf6`.
- The PR head and merged staging have identical Git trees. The cumulative diff
  contains 571 files, including 20 new Alembic files; no existing migration file
  is edited. Main's authoritative `.github/workflows/cd.yml` is byte-identical.
- Scope includes all clinical-plan slices S00–S36 and subsequent auth, financial,
  archive/restore, runtime and marketing changes. HIGH_RISK PRs specifically
  considered include #284–287, #315–317, #324–326 and #329. Unlabelled changes in
  the same sensitive boundaries were also included; labels alone did not define scope.

## Review coverage

| Boundary | Evidence reviewed and conclusion |
| --- | --- |
| Auth, RBAC and tenancy | `backend/routers/auth/dependencies.py`, `backend/routers/auth/login.py`, `backend/services/auth_bootstrap.py`, `backend/crud/auth.py`, `backend/routers/users.py`, `backend/core/tenant_scope.py`: pending-2FA tokens are rejected for normal API access; tenant binding, active identity checks, server permissions and patient visibility are retained. JSON user registration preserves the older query fallback. The captured production snapshot has zero normalized username/email collision groups. |
| Clinical commands, plans and sessions | `backend/services/clinical_command_service.py`, `backend/services/treatment_plan_service.py`, `backend/services/care_session_service.py`, `backend/services/care_session_material_service.py` and their routers: patient/tenant reference checks, rollout gates, conflict/version handling, idempotency and transactional stock boundaries were reviewed. Plan status changes do not themselves invoice or deduct stock. |
| Finance, laboratory and inventory | `backend/services/lab_service.py`, `backend/routers/laboratories.py`, `backend/services/clinical_charge_service.py`, `backend/services/finance_summary_service.py`, `backend/services/accounting_service.py`, `backend/services/treatment_service.py`: cash-basis laboratory payment changes are intentional product scope. Linked treatment/order handling and stock transaction boundaries were reviewed. The reproduced financial concurrency blocker was fixed in #329; see below. |
| Clinic archives and restore | `backend/routers/tenant_backups.py`, `backend/services/tenant_restore_preview.py`, `backend/services/tenant_restore_coordinator.py` and archive validation/import modules: authenticated encryption, tenant/installation binding, actor/digest/single-use confirmation, current-password reauthentication, restore write coordination, rollback and historical reference fixes were reviewed. |
| Google, Drive and outbox | `backend/routers/clinic_google.py`, connection/OAuth/attempt services and protected Drive image operations: browser/state/PKCE/account/generation binding, clinic-admin checks and bounded protected retrieval were reviewed. Missing provider configuration is surfaced. Live provider acceptance is not claimed. |
| Frontend, public pages and PWA | Shared treatment payload/save hooks, plan/session integration, static `/ar` and `/en`, HF/Vercel routes and SW exclusions were reviewed with their tests. Public pages use fictional product captures. Existing app root/login, API proxy and explicit SW update acceptance remain intact. |
| Migration and release | New migration lineage, unchanged applied migrations, production-snapshot rehearsal, authoritative CD and exact-revision CI/staging-smoke evidence were reviewed. Branch protections and owner review remain part of promotion. |

No remaining verified Critical/High code finding was identified in this review
following #329. This is a review conclusion with the verification limits below,
not a guarantee that no defect can exist.

## Closed financial blocker — PR #329

Concurrent cost reduction and payment creation could both succeed and leave paid
100 against a final order cost of 50. A deterministic real PostgreSQL probe and
then a committed regression test reproduced the failure before correction.

[PR #329](https://github.com/Dentix-hub/dentix/pull/329) makes both HTTP and service
cost editors lock the same tenant-scoped order as payment creation/allocation.
Locked reads refresh cached ORM values after waiting. Accounting formulas,
permissions and payloads are unchanged; no migration was added.

Executed local gates: **26 restricted-role PostgreSQL checks + 77 targeted
lab/RBAC/visibility/atomic-write regressions PASS, 0 skipped**. The PostgreSQL
matrix covers two editors, four payment/allocation paths, both lock orderings,
preloaded ORM objects and progress on independent orders. The baseline regression
failed on the previous code; no assertion was weakened. Ruff and diff checks pass.

## CI and staging evidence

- [Final PR #329 CI](https://github.com/Dentix-hub/dentix/actions/runs/40984476800):
  all nine jobs succeeded, including backend/security, frontend, E2E, tenant
  concurrency, responsive, stale-deployment recovery, frozen dependencies and
  production container validation. An older superseded/cancelled run is not
  counted as a pass.
- [Merged staging CI](https://github.com/Dentix-hub/dentix/actions/runs/41011570048)
  and [governance](https://github.com/Dentix-hub/dentix/actions/runs/41011570104)
  succeeded for `ebb98e44ff4bad8a2de773eb220fd5d8fecbb02d`.
- Exact-revision `Dentix CD - HF staging smoke` is success:
  [staging CD](https://github.com/Dentix-hub/dentix/actions/runs/41011588522).
  Production deployment was skipped. CD runs its authoritative workflow from
  main; the staging commit status identifies the deployed staging revision.
- Live staging readiness is HTTP 200; `/ar` and `/en` return static marketing HTML.
  Production remains on the old main implementation. `/build-info.json` currently
  returns HTML, so it was not accepted as runtime SHA evidence; provenance here
  comes from CD and the exact-commit smoke status.

This review-record PR changes documentation only. It does not require another
local full backend/frontend run of unchanged application code; its own protected
CI/governance and the subsequent exact staging smoke remain authoritative.

## Production recovery evidence and attachment disposition

A production PostgreSQL 17.6 logical snapshot was captured at
`2026-10-30T00:27:06.877667+00:00` in a consistent read-only snapshot. The encrypted
archive and a separate recovery key were delivered privately for download.
No archive, recovery key, connection secret, filename identifying a patient or
patient content is committed here.

- The full logical dump includes non-system schemas and object ownership/ACL/RLS;
  PostgreSQL roles were exported separately without role passwords.
- Encrypted-archive integrity, actual decryption/extraction and per-file SHA-256
  verification passed. All 86 public application tables restored, and every row
  count matched the exported snapshot.
- The unchanged migration preflight advanced a private restored copy from
  `1a2b3c4d5e6f` to `e2b3c4d5e6f7`, exit 0. Before/after fingerprints retained every
  existing row/value on the old columns of 85 tables, excluding the intentionally
  advanced Alembic row. One feature-flag row was added; public base tables grew
  from 86 to 91.
- Managed Supabase schemas/extensions were archived but their complete platform
  restoration was not tested. The local migration owner was superuser, so the
  rehearsal does not establish the production migration role's DDL privileges.
- DB dumps do not contain external file bytes or hosting secrets. One existing
  canonical local attachment reference was found. Eslam explicitly confirmed the
  attachment is not important and instructed continuation on 2026-10-30. Its bytes
  are outside this release recovery scope; its DB record is retained unchanged.
  Physical existence was not claimed. No other attachment reference was present
  in that snapshot; `storage.objects` contained zero rows.
- Temporary plaintext exports, restored databases and the decrypted connection
  file were removed after verification. The original encrypted recovery copy remains.

Refresh the platform snapshot near actual cutover if production writes occurred
since the delivered snapshot, and retain both recovery generations.

## Release conditions and remaining operational verification

1. Preserve current clinical rollout flags. The captured source has no clinical
   flag records/tenant overrides and unknown flags fail closed. Promotion ships
   all code; it does not automatically enable native clinical/finance modes.
2. Preserve authentication, JWT/encryption/backup keys, OAuth/SMTP/provider
   configuration, tenant boundaries, domains and API rewrites. Do not rotate
   persistent keys or activate global clinical flags as a deployment side effect.
3. Live SMTP delivery and Google OAuth/Drive round trips remain **NOT VERIFIED**.
   Do not claim those optional integrations production-accepted until configured
   and smoke-tested in a designated test clinic. See the cumulative workflows handoff.
4. Regenerate the promotion candidate from the then-current validated staging
   revision, including this review record. Stale PR #233 and the cf6378a local
   candidate must not be merged as the current release. Keep authoritative CD
   unchanged and use the existing reconciliation/protection contract.
5. After owner acceptance and required checks, verify the production revision,
   readiness, Arabic/English pages, alias/404 behavior, robots/sitemap,
   authentication/PWA and representative clinic workflows. A successful CI or
   staging deploy is not a successful production deployment.
