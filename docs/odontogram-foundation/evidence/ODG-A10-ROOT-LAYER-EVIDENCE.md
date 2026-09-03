# ODG-A10 / Issue #126 — Stable Independent Root Layer Evidence

## Execution record

- Wave: ODG-L1
- Mode: STANDARD
- Risk: `clinical-ui`
- Execution: `SERIAL_ONLY`
- Protected baseline: `origin/staging@4eda190da409b5334f163563b27599d1f6c74be5`
- Scope outcome: the canonical root renderer and geometry were already present on the protected baseline. This ticket hardens and closes A10 with focused renderer coverage, full-family visual evidence, and tracker disposition; no production renderer or crown geometry was changed.

## Acceptance disposition

- A10-M01 — PASS: the root is a separate `aria-hidden` SVG sibling rendered before the crown.
- A10-M02 — PASS: permanent and primary anterior representatives render a single root.
- A10-M03 — PASS: maxillary first premolars render two roots; other premolar representatives render one.
- A10-M04 — PASS: maxillary permanent molars render three roots; mandibular permanent molars render two.
- A10-M05 — PASS: adult and primary modes render 32/32 and 20/20 root/crown pairs respectively.
- A10-M06 — PASS: every scaled path coordinate remains within the `50 x 48` root viewport, with a fixed 50-pixel tooth slot and no measured adjacent overlap.

## Focused T1

Command:

```text
npm.cmd run test -- src/features/clinical-chart/tests/rootGeometry.test.js src/features/clinical-chart/tests/rootLayerRendering.test.jsx src/features/dental/DentalChartSVG.test.jsx
```

Result: PASS — 3 files, 39 tests, 10.74 seconds.

The first T1 invocation exposed a truncated new test file, not a product regression. The test-construction defect was repaired without changing production code; the authoritative rerun and the final cleanup rerun both passed.

## Visual matrix

- [Adult full chart](./A10-root-layer-full-chart.png) — SHA-256 `D32F6C90021556D87BEC60A58A73CD2DED0C489111F55308EB8473D5CA7196D1`
- [Primary full chart](./A10-root-layer-primary-chart.png) — SHA-256 `F11068A4392EA65516AE2FF7D547D2812A6AD676A93C0F577ABA26BE00C070AE`
- Adult representatives: 11/13 single-root, 14 two-root, 15 single-root, 16 three-root, 36 two-root.
- Primary representatives: 51/53/73 single-root, 55 three-root, 85 two-root.

Playwright DOM measurements:

| Matrix | Root/crown pairs | Overlap defects | Maximum center offset | Document overflow |
|---|---:|---:|---:|---|
| Adult | 32 / 32 | 0 | 0 px | false |
| Primary | 20 / 20 | 0 | 0 px | false |

Both captured matrices were visually inspected for root clipping, crown/root alignment, and adjacent-tooth overlap.

## T2 frontend gate

- `npm.cmd run test` — PASS: 107 files, 478 tests, 276.03 seconds.
- `npm.cmd run lint` — PASS: zero lint errors or warnings.
- `npm.cmd run build` — PASS: 3,946 modules transformed; application build 4.64 seconds and service-worker build 1.55 seconds.
- Baseline-only non-failing output: jsdom cross-document navigation notices, stale `caniuse-lite`, and Vite `inlineDynamicImports` deprecation warning.

## Independent wave review

Independent clinical UI review result: CLEAN / `WAVE_REVIEW_PASS`. All A10-M01 through A10-M06 criteria were confirmed, scope stayed inside the declared Issue #126 touch surface, and the protected-baseline crown renderer remained unchanged.

Unresolved findings: zero.
