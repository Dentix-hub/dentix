# ODG-A15 Responsive, RTL/LTR, and Accessibility Evidence

Status: **PASS**

## Scope

- Final Part I dual-chart workspace only.
- Desktop, tablet, and mobile layouts.
- Arabic RTL and English LTR.
- Mobile quadrant navigation.
- Keyboard focus and practical accessible labels.

## Automated verification

### Focused component and renderer regression

Command:

```powershell
npm.cmd run test -- src/features/clinical-chart/tests/ClinicalChartWorkspace.test.jsx src/features/clinical-chart/tests/ClinicalChartVisualRendering.test.jsx src/features/clinical-chart/tests/ClinicalChartRendererAdapter.test.jsx --reporter=dot
```

Result: **PASS — 3 files, 27 tests, 0 failures.**

### Targeted lint

Command:

```powershell
npm.cmd exec -- eslint src/features/clinical-chart/ClinicalChartWorkspace.jsx src/features/clinical-chart/components/ClinicalChartComparisonCard.jsx src/features/clinical-chart/components/ClinicalChartInspector.jsx src/features/clinical-chart/components/ClinicalChartWorkspaceShell.jsx src/features/clinical-chart/components/clinicalChartWorkspaceCopy.js src/features/clinical-chart/tests/ClinicalChartWorkspace.test.jsx --report-unused-disable-directives --max-warnings 0
```

Result: **PASS — exit code 0.**

### Browser matrix

Command:

```powershell
npm.cmd exec -- playwright test e2e/odontogram-part1.spec.ts --config=playwright.config.js --project=chromium --reporter=list
```

Result: **PASS — 3 tests, 0 failures.**

The browser matrix asserts:

- 1440 x 1000 desktop Arabic RTL, two read-only charts, and no document overflow.
- 768 x 1024 tablet English LTR after the in-feature language switch, and no document overflow.
- 390 x 844 mobile Arabic RTL with visible quadrant navigation, keyboard focus, and no document overflow.

## Visual evidence

- [Desktop Arabic RTL](./A15-desktop-ar-rtl.png)
- [Tablet English LTR](./A15-tablet-en-ltr.png)
- [Mobile Arabic RTL](./A15-mobile-ar-rtl.png)

## Acceptance disposition

| Criterion | Result | Evidence |
| --- | --- | --- |
| A15-M01 Desktop usable | PASS | 1440 x 1000 browser assertion and screenshot |
| A15-M02 Tablet usable | PASS | 768 x 1024 browser assertion and screenshot |
| A15-M03 Mobile usable | PASS | 390 x 844 browser assertion and screenshot |
| A15-M04 Quadrant-friendly mobile | PASS | Four accessible quadrant controls scroll the requested FDI quadrant into view |
| A15-M05 Arabic RTL | PASS | Default feature locale is Arabic with `dir="rtl"` |
| A15-M06 English LTR | PASS | Language control switches the same feature to English with `dir="ltr"` |
| A15-M07 Keyboard focus visible | PASS | Language, select, checkbox, and quadrant controls expose feature-scoped focus rings |
| A15-M08 Accessible labels | PASS | Navigation, legend, inspector, filters, and language controls have practical accessible names |

The renderer remains read-only and projection-only. No API, persistence, schema, workflow, or global design-system change was introduced.
