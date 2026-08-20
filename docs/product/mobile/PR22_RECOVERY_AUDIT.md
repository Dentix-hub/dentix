# PR #22 Mobile Recovery Audit

## Decision

PR #22 (`fix/mobile-ux-responsive-forensic`) is superseded as a direct merge candidate. Its useful work has been recovered onto the current governed `staging` baseline through scoped branches and assembled in `test/mobile-recovery-integration` for final validation.

## Baseline

- Original PR #22 head: `0cb3d704577da3d80b66e3ae3a032eeee4436452`
- Governed staging baseline used for final recovery: `118221cd7a00117e42701c8aaf59754a5afb2eea`
- Original PR #22 was 43 commits ahead and 12 commits behind staging at audit start.
- The old branch must not be merged, rebased-and-merged, or wholesale cherry-picked.

## Recovered scopes

1. `fix/mobile-shell-current`
   - responsive shell / `dvh`
   - banners in normal flow
   - compact global search and notifications
   - manual `index.css` reconciliation preserving opaque semantic surfaces

2. `fix/mobile-shared-primitives`
   - Modal / Dialog / BottomSheet
   - DateTimePicker + test
   - PageHeader / TabGroup

3. `fix/mobile-appointments`
   - phone-first list
   - non-drag status path
   - dedicated drag handle
   - contained Kanban and create flow

4. `fix/mobile-inventory`
   - inventory route shell
   - stock mobile cards/actions
   - Add Material and Receive Stock flows

5. `fix/mobile-patient-clinical`
   - Patient Details
   - PatientInfoCard
   - DentalChartSVG

6. `fix/mobile-dashboard-tables`
   - Dashboard responsive behavior
   - AdvancedTable mobile-card fallback

7. `fix/mobile-labs`
   - Labs responsive workflow

8. `test/mobile-responsive-gate`
   - Playwright 320x640
   - Arabic RTL 390x844
   - English 412x915
   - Tablet 768x1024
   - overflow, overlay bounds/opacity, focus, sidebar and workflow assertions

## Deliberate handling

- `frontend/src/index.css` was manually reconciled rather than replaced so newer opaque surface fixes remain intact.
- Historical visual PNG baselines from PR #22 were not copied. Visual references must be regenerated only from accepted UI.
- `.github/workflows/ci.yml` was not replaced by the stale PR copy; responsive coverage lives in the dedicated mobile gate.

## Release rule

`test/mobile-recovery-integration` may be merged to `staging` only after current PR-triggered Dentix CI and the Mobile Responsive Gate pass. External deployment-provider quota/rate-limit failures are recorded separately and are not treated as code success.

## Close condition for PR #22

After the recovered release candidate is merged into `staging` and its automated checks succeed, PR #22 should be closed as superseded with a reference to the replacement staging merge.