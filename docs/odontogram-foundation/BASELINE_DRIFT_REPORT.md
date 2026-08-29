# Baseline Drift Report

## Comparison

- Compared on: `2026-08-29`
- Previous checkout: `b38636bdd82ec3ebf4ab728d87f13407bcb78d4b`
- Latest fetched `origin/main`: `89d67010f361c8a2ff0437953e997283d2275037`
- Relationship before the execution branch was created: local checkout was `0` commits ahead and `4` commits behind `origin/main`.

## Relevant upstream drift

The four upstream commits changed only frontend localization coverage/resources:

- `frontend/src/i18n.resources.test.js` (added)
- `frontend/src/locales/ar/translation.json` (modified)
- `frontend/src/locales/en/translation.json` (modified)

No upstream chart, odontogram, tooth geometry, renderer, route, or dental feature file changed between the previous checkout and the fetched source-main commit. The chart plan assumptions therefore remain structurally valid. New chart labels must still use the current localization conventions when production-facing integration occurs.

## Pre-existing workspace drift

The workspace already contained uncommitted experimental chart work before A0:

- a DEV-only route change in `frontend/src/App.jsx`;
- an untracked `frontend/src/features/clinical-chart-v2/` experiment;
- generated/approved tooth assets and tooth-46 visual variants inside that experiment;
- programmatic effect prototypes and associated tests.

These files are preserved as user work and may be inventoried or selectively adapted. They are not treated as the canonical architecture because the controlling plan locks the implementation to `frontend/src/features/clinical-chart/`, a Dentix-native renderer, a root-first anatomy extension, and data-driven visual rules.

## Existing canonical chart surfaces

The fetched source-main tree contains the current Dentix chart implementation under:

- `frontend/src/features/dental/DentalChartSVG.jsx`
- `frontend/src/features/dental/v3/assets/dentalConstants.js`
- `frontend/src/features/dental/v3/assets/dentalPaths.js`
- `frontend/src/features/dental/v3/components/AdvancedTooth.jsx`
- `frontend/src/features/dental/v3/components/SidePanel.jsx`

These files are the starting inventory for A4. No backend or database drift is required for Part I.

## Verdict

**PASS WITH DOCUMENTED DRIFT.** Work may continue on the dedicated branch without rebasing user changes into `main`. Upstream localization changes are recorded and must not be overwritten.

