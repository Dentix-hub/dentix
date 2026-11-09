# Reviewed catalog setup and staging inventory — 2026-11-06

Code implementation: verified locally; hosted application remains PARTIAL. Hosted data application is pending explicit owner authorization. No production data has been queried or mutated by this task.

## Confirmed gap

PR #367 merged to staging at `6251abd`. Its CD run `42128322599` synchronized the new code and passed health, but production-like smoke failed at new-clinic registration with missing configured trial. Public staging JavaScript contains the new Commercial controls panel. Existing plans were deliberately preserved by the empty-catalog-only bootstrap; they were never a verified approved launch catalog.

Authorized connected Supabase **read-only** inventory of `Dentix-app-staging` confirmed five legacy plans: trial (0 EGP), basic (500), pro (1000), enterprise (2500), VIP (0). None of the three exact launch names exists, and no saved future-trial settings exist. Aggregate references: 174 active + 4 trial on legacy pro, two active + one expired on VIP, one active unanchored platform/clinic row (not automatically classified). No clinic names, user identities, patient records or clinical content were read for this inventory. Existing contracts must not be changed through an inferred name mapping.

## Change

- Add Super Admin-only GET `/api/v1/admin/subscriptions/catalog-setup-preview` and POST `/catalog-setup`.
- Preview returns exactly which approved plans would be added, which records remain unchanged, current/proposed future-trial policy, conflicts and a SHA256 snapshot of actual configuration plus the approved template.
- Apply requires a reason and the exact snapshot. It serializes setup confirmations on PostgreSQL, locks existing catalog/policy rows, refuses changed state or conflicting existing named plans/defaults, and creates only missing plans. Existing records are not repriced, retired, assigned or deleted.
- Reuse the existing trial policy command with a noncommitting option; catalog additions, Professional/14-day future policy and both audit records commit together. Failure rolls everything back. No tenant subscription/date/history/account is changed. Completed/stale confirmations refuse rather than repeat the command.
- Normalize array/object grants semantically while preserving raw explicit false metadata. Malformed values cannot authorize a setup overwrite.
- Expose **Setup & controls / التهيئة والضوابط** directly on `/admin/finance`, and reuse the same setup component on `/admin/settings`. Repair controls remain available if another diagnostics request fails. No layout redesign or new commercial feature is implied.

No migrations, database models, CI workflows, existing prices/receipts or financial calculations were changed. Existing trial-policy API callers keep their default commit behavior.

## Proposed hosted operation — NOT APPLIED

Create Essential 200 EGP / 2 accounts / 2 AI per clinic day; Professional 400 / 5 / 10; Business 1000 / 15 / 30. All use calendar-month billing and the existing approved capability set, with no patient cap. Configure Professional, 14 days, no card, for future registrations. Preserve all five legacy rows and every existing subscription/date/receipt. Retiring old offers or moving existing clinics is a separate reviewed action; setup never infers it.

This proposal requires a fresh server preview/validation at execution. A concurrent change or a pre-existing conflicting exact launch name requires review, not overwrite. Deployment retry and bounded live-provider smoke remain separate operations; a health endpoint alone is not acceptance.

## Verification

Executed commands/logs are in `/home/ubuntu/dentix-task-artifacts/catalog-setup-20261106/`.

- Before implementation: 3 HTTP regressions failed because preview/apply routes did not exist.
- Focused backend/auth/policy/lifecycle: 48 passed, including real PostgreSQL concurrency and rollback. Two simultaneous confirmations yield one success and one 409. Injected audit-store failure rolls back all newly created plans, trial policy and audits, preserving the old contract/date.
- A regression first reproduced false object metadata being incorrectly flagged as drift; semantic grant comparison preserves explicit false values.
- Frontend: 21 passed across four files, including direct Finance navigation, explicit confirmation, conflict blocking and stale-preview rejection. Production/PWA/marketing build passed. Ruff and changed-file ESLint passed; design diff has zero new guarded violations. No test assertion, timeout, role check, RLS rule or migration was weakened.

## Owner staging path (under 15 minutes after authorized integration)

1. Open `/admin/finance` as Super Admin and select **التهيئة والضوابط**.
2. Enter a documented setup reason, then preview. Verify 200/400/1000, 2/5/15, 2/10/30, Professional/14, and the preserved legacy list. Opening/refreshing preview must not mutate anything.
3. Cancel once. Reopen and confirm only after approving the displayed changes. If someone edited catalog/trial settings meanwhile, expect conflict and refresh.
4. Verify the plans list refreshes and the future-trial selector references Professional. Review `COMMERCIAL_CATALOG_SETUP` and `TRIAL_POLICY_UPDATE` audit entries.
5. Verify one pre-existing contract still has its original plan and end date. Missing/invalid rollout enforcement is still shown; this setup does not silently enable ENFORCE or remap clinics.
6. Obtain explicit authorization for any synthetic hosted registration/smoke or deployment retry; record the exact staging revision and actual result. Production remains outside this operation.

## Review

Spec: completes the missing supervised initialization UI/command, not automatic conversion of paid contracts. Standards: existing auth/tenant isolation and financial preservation retained; no new tenant-scoped table. Existing schemas/API additions are compatible. No known failing focused test remains; hosted application and deployment acceptance are not claimed until executed.
