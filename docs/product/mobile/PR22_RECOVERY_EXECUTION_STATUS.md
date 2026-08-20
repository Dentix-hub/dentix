# PR #22 Recovery Execution Status

**Governed staging baseline:** `118221cd7a00117e42701c8aaf59754a5afb2eea`

## Recovered implementation

The useful PR #22 behavior has been rebuilt on the governed staging baseline through these scoped branches:

- `fix/mobile-shell-current`
- `fix/mobile-shared-primitives`
- `fix/mobile-appointments`
- `fix/mobile-inventory`
- `fix/mobile-patient-clinical`
- `fix/mobile-dashboard-tables`
- `fix/mobile-labs`
- `test/mobile-responsive-gate`

Their combined content is assembled in `test/mobile-recovery-integration` for a single final staging validation. This branch is now a temporary **mobile recovery release candidate**; it is not a permanent branch.

## Included verification infrastructure

- responsive Playwright projects for 320x640, Arabic RTL 390x844, English 412x915, and tablet 768x1024;
- mobile overflow assertions;
- overlay viewport and opacity assertions;
- mobile sidebar/focus checks;
- appointments non-drag status path checks;
- inventory mobile fallback coverage;
- existing critical-path and visual-regression coverage remains authoritative and must also pass.

## Visual baseline policy

The three historical PR #22 PNG baselines were intentionally not copied. New baselines may be generated only after accepted recovered UI is reviewed; tests must not be made green by blindly replacing snapshots.

## Current state

`RELEASE_CANDIDATE_PENDING_PR_CI`

The candidate can enter `staging` only after the PR-triggered Dentix Branch Governance, Dentix CI, Playwright/visual checks, production container validation, and Mobile Responsive Gate complete successfully.

## After merge

- close PR #22 as superseded;
- treat `staging` as the only source of truth for the recovered mobile behavior;
- delete/sunset temporary recovery branches when branch-ref deletion is available and no open PR depends on them;
- keep mobile responsive acceptance as a permanent release gate.