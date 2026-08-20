# Dentix Branch Cleanup Ledger

This ledger is evidence-based. A branch is deletable only after its work is merged/superseded, no open PR depends on it, and no deployment automation references it.

## Permanent branches — keep

- `main`
- `staging`

## Current mobile recovery — keep until staging acceptance

- `fix/mobile-ux-responsive-forensic` — PR #22 evidence only; close as superseded after recovered staging merge.
- `fix/mobile-shell-current`
- `fix/mobile-shared-primitives`
- `fix/mobile-appointments`
- `fix/mobile-inventory`
- `fix/mobile-patient-clinical`
- `fix/mobile-dashboard-tables`
- `fix/mobile-labs`
- `test/mobile-responsive-gate`
- `test/mobile-recovery-integration` — temporary combined release candidate; delete after successful staging merge and follow-up verification.
- `chore/mobile-pr22-recovery-audit` — superseded by the audit documents included in the combined release candidate once that PR merges.

## Governance state

`chore/git-release-governance` was merged to staging through PR #30 after Branch Governance, frontend, backend/security, PostgreSQL finance/RLS smoke, Playwright critical path, visual regression, and production container validation passed.

## Evidence-backed historical cleanup candidates

- `chore/finance-ci-full-suite-audit` — merged via PR #20.
- `chore/plan-01-project-truth-inventory` — merged via PR #16.
- `feat/patient-workspace-v2` — work merged through PRs #10, #11 and #12.
- `fix/cicd-authoritative-hf-sync` — merged via PR #27.
- `fix/hf-staging-lfs-deploy` — merged via PR #25.
- `fix/hf-staging-hub-sync` — merged via PR #26.
- `fix/mobile-overlay-patient-kpi-regressions` — merged via PR #23.
- `fix/opaque-floating-overlays` — merged via PR #14.
- `fix/staging-pwa-cache-refresh` — merged via PR #24.
- `refactor/plan-02-design-system-ui-regression` — merged via PR #18.
- `refactor/plan-03-existing-product-forensic-improvement` — merged via PR #19.
- `release/staging-to-main-20260820` — merged via PR #29.

## Do not delete without more evidence

- `feat/mobile-ux-responsive-forensic-pass` — no canonical merged/superseded PR has been established by the current audit.

## Repository setting gap

`main` and `staging` still require GitHub Ruleset/Branch Protection to prohibit direct and force pushes at the hosting layer. Repository workflows validate PR paths but are not a substitute for branch protection.

## Tooling limitation

The currently connected GitHub action surface does not expose deletion of Git branch refs or mutation of branch-protection/ruleset settings. Cleanup and protection must therefore be completed through a branch/ruleset-capable GitHub interface once the evidence above is final.