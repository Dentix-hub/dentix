# Flutter Client Freeze Policy

**Status:** Active — part of the PWA-primary mobile program (Master Plan 2026-08-24, Phase 0 / PR-PWA-10).
**Scope:** `dentix_mobile/`

## Decision

The React/Vite PWA is the primary mobile client under development. The Flutter
client (`dentix_mobile/`) is **frozen as a feature surface**:

- **Allowed** (without architecture exception):
  - security fixes;
  - build-system / toolchain fixes (SDK, Gradle, dependency resolution);
  - dependency upgrades required by repository governance or CI health;
  - crash or data-loss regression fixes.
- **Not allowed** without an explicit architecture exception:
  - new patient / finance / inventory features duplicated from the web product;
  - visual redesigns implemented separately in Flutter;
  - new backend endpoints consumed only by Flutter.

## Do not delete

`dentix_mobile/` and its history must be retained during the PWA hardening
program. Retirement is a separate, explicit decision made only after the PWA
passes the final mobile-primary acceptance gate.

## Mandatory safety blocker before any production-native resume

The Flutter client installs a global `RetryInterceptor` that retries transport
failures **without restricting by HTTP method**. A non-idempotent request
(`POST /payments`, stock movements, treatment writes) that fails after server
commit can therefore be replayed by automatic retry.

Before Flutter may carry production write traffic again:

1. Restrict automatic retry to safe/idempotent methods (`GET`, `HEAD`) unless a
   retried call carries a tested idempotency-key contract.
2. Add regression tests proving a lost response cannot duplicate payments,
   stock movements, treatments, or destructive actions.
3. Audit token-refresh retry/queue behavior for concurrent 401 handling.
4. Verify feature parity and RBAC behavior against the same backend contracts
   used by the web frontend.

## CI

Mobile CI remains active for build/regression health. Path-based filtering of
mobile workflows may be considered later **only if it does not weaken existing
branch-protection guarantees**.

## Escalation path

Native/mobile-specific work resumes only if one of the documented hard
escalation triggers in the master plan applies (full offline clinical sync,
unsupported device integration, regulatory APIs unavailable to web, etc.).
"More native feel" alone is not a trigger.
