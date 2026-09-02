# Odontogram Foundation Task Tracker

Status values: `PENDING`, `IN PROGRESS`, `PASS`, `REWORK REQUIRED`, `BLOCKED`, `ACCEPTED DEVIATION`.

| Micro-task | Status | Evidence / note |
| --- | --- | --- |
| A0-M01 Revalidate current main | PASS | `BASELINE_DRIFT_REPORT.md`; fetched `origin/main@89d67010` |
| A0-M02 Create execution docs folder | PASS | Required four files plus drift report created |
| A0-M03 Record baseline metadata | PASS | `README.md`; committed in `c0e27897` |
| A0-M04 Create explicit scope lock note | PASS | `README.md`; committed in `c0e27897` |
| A1-M01 Write chart direction ADR | PASS | `ADR-001-CHART-DIRECTION.md` |
| A1-M02 Define chart architectural layers | PASS | ADR “Architectural layers” and data-flow sections |
| A1-M03 Define renderer non-responsibilities | PASS | ADR “Renderer non-responsibilities” section |
| A1-M04 Define future readiness targets | PASS | ADR “Future-readiness targets” section |
| A2-M01 Create feature directory | PASS | `frontend/src/features/clinical-chart/` |
| A2-M02 Create subfolders | PASS | `components`, `domain`, `rendering`, `fixtures`, `hooks`, `tests` |
| A2-M03 Create entry workspace component | PASS | Component test: 1/1 passed; frontend lint passed |
| A2-M04 Create temporary demo route | PASS | DEV-only `/clinical-chart/demo`; browser DOM verified with zero console errors |
| A3-M01 Create anatomy registry file | PASS | `domain/dentalAnatomyRegistry.js` exports immutable registry and lookup |
| A3-M02 Define anatomy model shape | PASS | JSDoc contract covers every required field; 10/10 focused tests passed |
| A3-M03 Define permanent dentition keys | PASS | All 32 permanent FDI positions represented and tested |
| A3-M04 Define primary dentition keys | PASS | All 20 primary FDI positions represented and tested |
| A3-M05 Define mixed-dentition compatibility note | PASS | `MIXED_DENTITION_COMPATIBILITY.md` |
| A4-M01 Inventory current crown outlines | PASS | `CROWN_OUTLINE_INVENTORY.md` |
| A4-M02 Normalize crown shape access | PASS | All 52 anatomy keys resolve; 20/20 focused chart tests passed |
| A4-M03 Preserve current visual style | PASS | User approved the retained crown style plus upper-incisor orientation and restrained lateral-incisor scaling |
| A5-M01 Create root outline model | PASS | One `0 0 50 48` coordinate system, FDI-specific refs, cervical/apex anchors, and closed cubic paths; registry tests pass |
| A5-M02 Add single-root anterior definitions | PASS | User continued after the final permanent upper-central root increase and proportional review |
| A5-M03 Add premolar root definitions | PASS | User approved canonical two-root maxillary first premolar and single-root remaining premolar rendering |
| A5-M04 Add molar root definitions | PASS | User approved unequal maxillary MB/DB/palatal and mandibular mesial/distal rendering |
| A5-M05 Add primary tooth root definitions | PASS | Primary anterior and divergent molar definitions resolve and render through the same tested registry |
| A5-M06 Keep root style visually aligned | PASS | User continued after reviewing the 52-tooth proportional metrics and final upper-central adjustment |
| A6-M01 Create surface code constants | PASS | `SURFACE_CODES` exports M, D, O, I, B, L, P; focused tests pass |
| A6-M02 Define per-tooth clickable surface geometry | PASS | Five closed clipped regions resolve for all 52 FDI teeth; 51/51 focused tests pass |
| A6-M03 Support anterior surface model | PASS | Incisor and canine geometries use incisal-compatible regions with P/L by arch |
| A6-M04 Support posterior surface model | PASS | Premolar and molar geometries use occlusal regions with mirrored M/D |
| A6-M05 Add hover/focus/selected states | PASS | User continued after pointer, keyboard, hover, focus, and selected-state behavior was presented; component regressions pass |
| A7-M01 Create renderer adapter interface | PASS | `rendering/ClinicalChartRendererAdapter.js` and stateless `ClinicalChartRenderer.jsx` are wired into the demo workspace |
| A7-M02 Define input DTO contract | PASS | Documented and validated anatomy, visual state, dentition, notation, interaction mode, layers, and callback inputs; focused tests pass 22/22 |
| A7-M03 Define output interaction intents | PASS | Neutral tooth, surface, root, and multi-select intents dispatch through generic and intent-specific callbacks; full frontend tests pass 461/461 |
| A7-M04 Prevent persistence leakage | PASS | Renderer boundary imports only anatomy/tooth utilities/current chart; no backend API, domain service, or persistence dependency; lint and production build pass |
| A8-M01 Create demo DTO schema | PASS | `domain/clinicalChartProjection.js` provides a validated, frozen, JSON-serializable version-1 demo projection; full frontend tests pass 468/468 |
| A8-M02 Define tooth visual state shape | PASS | DTO and `PROJECTION_DTO_CONTRACT.md` document lifecycle, findings, procedures, selection, disabled state, and annotations |
| A8-M03 Define target subshape | PASS | Whole-tooth, surface, anatomy-validated root, and nullable canal-placeholder targets are documented and tested |
| A8-M04 Add sample DTO fixtures | PASS | Adult baseline and complete target-coverage fixtures load through the A7 renderer boundary; focused tests pass 29/29 |
| A9-M01 Create visual rule registry file | PASS | `domain/visualRuleRegistry.js` exports immutable semantic rules, lookups, and DTO-to-instruction resolvers |
| A9-M02 Add lifecycle rules | PASS | PRESENT, MISSING, EXTRACTED, IMPACTED, and UNERUPTED render in the live A9 demo fixture |
| A9-M03 Add finding rules | PASS | CARIES is crown-surface-local, FRACTURE is a clipped crack, and PAIN uses a crown/root marker; rendering tests pass |
| A9-M04 Add procedure rules | PASS | Composite, RCT, crown, bridge, implant fixture/crown, and planned/completed extraction effects render programmatically; focused tests pass 34/34 |
| A9-M05 Add layer mapping | PASS | Stable indices enforce anatomy → lifecycle → findings → existing/completed → planned/active → selection; live browser verified 32 crowns, 32 root layers, 160 surface controls, and no document overflow |
| A10-M01 Add root layer renderer | PASS | Rendered as separate layer under crown with `data-layer="roots"`, viewBox 0 0 50 48, and proper z-order; focused tests pass 24/24 in `RootLayerRendering.test.jsx` |
| A10-M02 Handle single-root teeth | PASS | All 12 permanent incisors/canines render 1 root with apical orientation (rotate 180 on upper, unrotated on lower); tests pass |
| A10-M03 Handle premolars | PASS | Maxillary 1st premolars (14, 24) render 2 roots; maxillary 2nd and all mandibular premolars render 1 root; tests pass |
| A10-M04 Handle molars | PASS | All maxillary molars render 3 roots (MB, DB, Palatal); all mandibular molars render 2 roots (Mesial, Distal); tests pass |
| A10-M05 Handle primary teeth | PASS | All 20 primary teeth render verified roots (incisors 1 root, maxillary molars 3 divergent roots, mandibular molars 2 divergent roots); tests pass |
| A10-M06 Prevent root overlap artifacts | PASS | Root paths bounded in [0, 50] width, crowns smoothly mask cervical lines, `pointer-events-none` prevents click blocking, and 4px column separation prevents adjacent collisions; tests pass |
| A11-M01 Support current notation display mode | PASS | Default Palmer notation preserves familiar UR/UL/LL/LR and pediatric letter labels; DentalChartSVG and workspace tests pass |
| A11-M02 Add notation abstraction | PASS | `domain/toothNotation.js` exports frozen constants, label resolvers, and converters between FDI, Palmer, and Universal; 8/8 tests pass in `ToothNotationAndLabels.test.jsx` |
| A11-M03 Verify label placement after roots | PASS | Labels cleanly positioned with `-bottom-5` below root apices without overlap; dynamic header subtitle updates to active notation; tests pass |
| A12-M01 Create adult dentition fixture | PASS | Full 32 permanent adult teeth fixture loads cleanly; verified in `ClinicalDemoFixtures.test.jsx` |
| A12-M02 Create primary dentition fixture | PASS | Full 20 primary pediatric teeth fixture loads and renders cleanly; tests pass |
| A12-M03 Create mixed dentition fixture | PASS | Mixed dentition fixture with explicit FDI tooth order and permanent + primary teeth; tests pass |
| A12-M04 Create caries-on-surface fixture | PASS | Surface-targeted caries visual rules on 46-O, 16-M, 21-D verified; tests pass |
| A12-M05 Create MOD restoration fixture | PASS | Multi-surface composite restoration visual rules on M, O, D verified; tests pass |
| A12-M06 Create RCT fixture | PASS | Completed and active root canal therapy visual rules targeted to roots verified; tests pass |
| A12-M07 Create crown fixture | PASS | Completed and planned prosthetic full crown visual rules verified; tests pass |
| A12-M08 Create missing tooth fixture | PASS | Missing and extracted teeth visual rules (18, 28) verified in completed extraction fixture; tests pass |
| A12-M09 Create implant fixture | PASS | Implant fixture and implant crown visual rules replacing roots on tooth 36 verified; tests pass |
| A12-M10 Create bridge fixture | PASS | Multi-unit bridge fixture with abutment crowns (21, 23) and pontic (22) verified; tests pass |
| A12-M11 Create simultaneous existing + planned fixture | PASS | Target coverage and extraction planned/completed fixtures cover simultaneous existing and planned phases; 12/12 tests pass |
| A13-M01 Create dual-chart page | PENDING | — |
| A13-M02 Ensure state isolation | PENDING | — |
| A13-M03 Ensure independent layer filtering | PENDING | — |
| A13-M04 Ensure read-only multi-instance support | PENDING | — |
| A14-M01 Create chart shell header | PENDING | — |
| A14-M02 Create simple legend | PENDING | — |
| A14-M03 Create simple inspector panel | PENDING | — |
| A14-M04 Create simple selection summary | PENDING | — |
| A14-M05 Keep UI intentionally simple | PENDING | — |
| A15-M01 Verify chart on desktop | PENDING | — |
| A15-M02 Verify chart on tablet width | PENDING | — |
| A15-M03 Verify chart on mobile width | PENDING | — |
| A15-M04 Add quadrant-friendly mobile behavior | PENDING | — |
| A15-M05 Verify Arabic RTL layout | PENDING | — |
| A15-M06 Verify English LTR layout | PENDING | — |
| A15-M07 Add keyboard focus states | PENDING | — |
| A15-M08 Add accessible labels where practical | PENDING | — |
| A16-M01 Add anatomy registry coverage test | PENDING | — |
| A16-M02 Add renderer smoke test | PENDING | — |
| A16-M03 Add multi-instance isolation test | PENDING | — |
| A16-M04 Add root visual regression evidence | PENDING | — |
| A16-M05 Add mixed dentition render test | PENDING | — |
| A16-M06 Add RTL render test | PENDING | — |
| A16-M07 Add mobile render test if tooling allows | PENDING | — |
| A17-M01 Capture desktop screenshots | PENDING | — |
| A17-M02 Capture mobile screenshots | PENDING | — |
| A17-M03 Capture RTL screenshots | PENDING | — |
| A17-M04 Capture history-compare screenshots | PENDING | — |
| A17-M05 Write Codex completion report | PENDING | — |
| A17-M06 Write handoff package for Gemini | PENDING | — |
| A17-M07 Hard stop | PENDING | — |
