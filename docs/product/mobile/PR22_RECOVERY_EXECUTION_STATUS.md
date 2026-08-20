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

Their combined content is assembled in `test/mobile-recovery-integration` for a single final staging validation. This branch is a temporary **mobile recovery release candidate**; it is not a permanent branch.

## Included verification infrastructure

- responsive Playwright projects for 320x640, Arabic RTL 390x844, English 412x915, and tablet 768x1024;
- mobile overflow assertions;
- overlay viewport and opacity assertions;
- mobile sidebar/focus checks;
- appointments non-drag status path checks;
- inventory mobile fallback coverage;
- existing critical-path and visual-regression coverage remains authoritative and must also pass.

## Verified recovery findings

- the responsive matrix reached 24/24 passing checks after replacing a raw mouse-coordinate sidebar test with a locator/actionability-safe RTL interaction; the product sidebar behavior itself was not weakened;
- the three patient-workspace visual differences were reviewed from the Playwright failure artifact and matched the intended recovered responsive UI;
- only those three reviewed PNG baselines were regenerated and committed through Git LFS;
- the temporary baseline-refresh workflow was removed immediately after the reviewed images were committed;
- local GitHub Actions PostgreSQL now sets `DB_SSL_MODE=disable` in the permanent CI/mobile test jobs, preventing the sync SQLAlchemy engine from requesting SSL against the local non-SSL test service while leaving production database behavior unchanged;
- the obsolete `develop` CI push trigger and the temporary mobile-integration push trigger were removed so the workflow matches the governed `main` / `staging` branch model.

## Visual baseline policy

The historical PR #22 PNGs were never copied blindly. The replacement baselines were generated from the recovered UI only after the actual/expected/diff images were reviewed. Future visual changes remain subject to the normal 1% screenshot-difference threshold unless an intentional UI change is reviewed and its baseline explicitly accepted.

## Current state

`RELEASE_CANDIDATE_PENDING_FINAL_PR_CI`

The candidate can enter `staging` only after the final PR head passes Dentix Branch Governance, Dentix Design System Guardrails, Dentix CI, Playwright critical path, visual regression, production container validation, and Dentix Mobile Responsive Gate.

## After merge

- close PR #22 as superseded;
- treat `staging` as the only source of truth for the recovered mobile behavior;
- delete/sunset temporary recovery branches when branch-ref deletion is available and no open PR depends on them;
- keep mobile responsive acceptance as a permanent release gate.