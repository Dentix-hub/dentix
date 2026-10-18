<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Odontogram & Clinical VNext Implementation Status

**Authority:** `docs/engineering/DEVELOPMENT_WORKFLOW.md`  
**Classification:** `ACTIVE`  
**Last Updated:** 2026-10-16 (Post Slice 3)  
**Status Reference Invariant:** This document is the single authoritative implementation status reference for all Odontogram Foundation (A0–A17) and Clinical VNext (G0–G16) phases across DENTIX, updated incrementally per slice.

---

## 1. Status Summary

- **Total Phases Tracked:** 35 (A0–A17, G0–G16)
- **DONE:** 24 phases (A0–A17, G0–G3, G5–G6)
- **PARTIAL:** 5 phases (G4, G7, G8, G9, G16)
- **SCHEMA_ONLY:** 3 phases (G10, G11, G15)
- **NOT_STARTED:** 3 phases (G12, G13, G14)

---

## 2. Phase-by-Phase Implementation Status Ledger

| Phase | Phase Title | Status | Evidence (File[:line], Tests, PR) |
|---|---|:---:|---|
| **A0** | Baseline Revalidation and Freeze | **DONE** | `docs/odontogram-foundation/evidence/`, `docs/engineering/DEVELOPMENT_WORKFLOW.md`, PR #222 |
| **A1** | Final Chart Architecture Lock | **DONE** | `PROJECT_STANDARDS.md:Section 5`, `docs/engineering/CLINICAL_CHART_DISPOSITION.md`, PR #222 |
| **A2** | Frontend Chart Module Scaffold | **DONE** | `frontend/src/features/clinical-chart/` module tree, `tests/smoke.test.jsx`, PR #222 |
| **A3** | Anatomy Registry Foundation | **DONE** | `frontend/src/features/clinical-chart/domain/dentalAnatomyRegistry.js:1-120`, `dentalAnatomyRegistry.test.js`, PR #222 |
| **A4** | Crown Outline Integration | **DONE** | `frontend/src/features/clinical-chart/rendering/crownGeometry.js:1-72`, `crownGeometry.test.js`, PR #222 |
| **A5** | Root Anatomy Definition | **DONE** | `frontend/src/features/clinical-chart/rendering/rootGeometry.js:1-110`, `rootGeometry.test.js`, PR #222 |
| **A6** | Surface Geometry Foundation | **DONE** | `frontend/src/features/clinical-chart/rendering/surfaceGeometry.js:1-85`, `surfaceGeometry.test.js`, PR #222 |
| **A7** | Renderer Contract | **DONE** | `frontend/src/features/clinical-chart/rendering/ClinicalChartRendererAdapter.js:1-240`, `ClinicalChartRendererAdapter.test.jsx`, PR #222 |
| **A8** | Projection DTO for Demo Use | **DONE** | `frontend/src/features/clinical-chart/domain/clinicalChartProjection.js:1-115`, `clinicalChartProjection.test.js`, PR #222 |
| **A9** | Visual Rule Registry | **DONE** | `frontend/src/features/clinical-chart/domain/visualRuleRegistry.js:1-150`, `visualRuleRegistry.test.js`, PR #222 |
| **A10** | Root Layer Rendering | **DONE** | `frontend/src/features/dental/DentalChartSVG.jsx:398-460`, `features/clinical-chart/tests/rootLayerRendering.test.jsx`, PR #222 |
| **A11** | Notation and Labels | **DONE** | `frontend/src/features/clinical-chart/domain/chartNotation.js:1-71`, `chartNotation.test.js`, PR #222 |
| **A12** | Demo Clinical Scenarios | **DONE** | `frontend/src/features/clinical-chart/fixtures/a12ScenarioFixtures.js:1-200`, `workspaceSnapshotAdapter.test.js`, PR #222 |
| **A13** | Multi-Instance and History Compare | **DONE** | `frontend/src/features/clinical-chart/components/ClinicalChartComparisonCard.jsx:1-80`, `a16RegressionGate.test.jsx`, PR #222 |
| **A14** | Basic UI Layer | **DONE** | `frontend/src/features/clinical-chart/ClinicalChartWorkspace.jsx:1-55`, `ClinicalChartInspector.jsx`, PR #222 |
| **A15** | Mobile, RTL, and Accessibility | **DONE** | `frontend/src/features/clinical-chart/ClinicalChartWorkspace.jsx:18-55`, `DentalChartSVG.jsx:210-250`, PR #222 |
| **A16** | Testing | **DONE** | `frontend/src/features/clinical-chart/tests/a16RegressionGate.test.jsx`, `backend/tests/test_odontogram_traceability.py`, PR #222 |
| **A17** | Evidence and Handoff Package | **DONE** | `docs/odontogram-foundation/evidence/`, `docs/engineering/DEVELOPMENT_WORKFLOW.md`, PR #222 |
| **G0** | Revalidation Before Full VNext | **DONE** | `docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md:1-50`, PR #222 |
| **G1** | Additive Clinical Core Schema | **DONE** | `backend/models/clinical_core.py:97-590`, migration `f4a5b6c7d8e9`, `test_clinical_core_schema.py`, PR #222 |
| **G2** | Canonical Catalog, Taxonomy, & Templates | **DONE** | `backend/clinical/catalog.py:1-120`, `backend/clinical/workflow_templates.py:1-150`, `test_clinical_catalog.py`, PR #222 |
| **G3** | Deterministic Legacy Mapping Engine | **DONE** | `backend/clinical/legacy_mapping.py:1-140`, `treatment_service.py:189-224`, `test_clinical_legacy_mapping.py`, PR #222 & PR #226 |
| **G4** | Controlled Backfill | **PARTIAL** | Treatment, tooth-status, and session backfill tool extended and tested (`scripts/backfill_clinical_work_items.py:1-617`, `backend/tests/services/test_clinical_backfill.py` (14 tests), PR #227 & PR #237); tooth-status (`G4-M06`), care session (`G4-M07`), inventory invariance (`G4-M12`), and payment invariance (`G4-M13`) implemented in S03; lab (`G4-M08` in S27) and attachment link (`G4-M09` in S23) backfill slices pending. |
| **G5** | Projection Layer & Real Chart Data | **DONE** | `backend/services/clinical_workspace_service.py:1-1017`, `backend/tests/test_clinical_workspace_snapshot.py`, `backend/routers/patients.py:217-232`, PR #222 |
| **G7** | Command / API Layer | **PARTIAL** | Command service, work item mutation APIs, single/bulk finding & procedure APIs, and RBAC permission enforcement implemented (`G7-M01`..`G7-M07`, `G7-M12`: `backend/services/clinical_command_service.py`, `backend/routers/clinical_commands.py`, `backend/services/clinical_service.py:193`, `backend/tests/services/test_clinical_command_service.py`, PR #238 & PR #239); legacy treatment sync via `backend/services/treatment_service.py:260-470`; correction/history (`S06`) and idempotency/concurrency (`S07`) slices pending. |
| **G8** | Zero-Friction Charting UX | **PARTIAL** | `frontend/src/features/dental/DentalChartSVG.jsx:320-380` (surface selector), `TreatmentModal.jsx:210-310`, `PatientDetails.jsx:659` (modal chart via PR #228); quick action launcher / sticky tool mode not started. |
| **G9** | First-Class Treatment Plans | **PARTIAL** | Minimal treatment plans create & list (Slice G9a, PR #230), phases & procedure membership (Slice G9b), and lifecycle transitions & hardening (Slice G9c: M06 lifecycle states, M07 accept flow with zero side effects, M08 alternative plan preservation): `backend/models/clinical_core.py:189-280`, `backend/services/treatment_plan_service.py:33-40,240-300,435-492`, `backend/routers/treatment_plans.py:133-161`, `frontend/src/features/clinical-plans/TreatmentPlansCard.jsx`, `backend/tests/services/test_treatment_plan_service.py` (26 tests, 94% coverage), `frontend/src/tests/TreatmentPlansCard.test.jsx` (13 tests). Pricing/estimates calculation and chart canvas overlay remain pending. |
| **G10** | Sessions and Resume Engine | **SCHEMA_ONLY** | `backend/models/clinical_core.py:383-500` (`CareSession`, `CareSessionStep`, `CareObservation`), migration `f4a5b6c7d8e9`; service, router, and UI not yet implemented. |
| **G11** | Appointment Integration | **SCHEMA_ONLY** | `backend/models/clinical_core.py:542-575` (`NextVisitRequest`), migration `f4a5b6c7d8e9`; appointment integration service, reception queue, and suggestion UI not yet implemented. |
| **G12** | Lab Integration | **NOT_STARTED** | `backend/models/clinical.py:326` (`LabOrder` has no `work_item_id` foreign key); direct work item link and decoupling not implemented. |
| **G13** | Inventory Integration | **NOT_STARTED** | `backend/models/inventory.py:289` (`TreatmentMaterialUsage` references `material_sessions.id`, not `care_sessions.id`). |
| **G14** | Finance Integration and Parity | **NOT_STARTED** | `clinical_charges` table does not exist in schema, models, or migrations (`git grep clinical_charges` returns 0). |
| **G15** | Files and Clinical Context | **SCHEMA_ONLY** | `backend/models/clinical_core.py:582-615` (`ClinicalAttachmentLink`), migration `f4a5b6c7d8e9`; link API and attachment context UI not yet implemented. |
| **G16** | Rollout and Controlled Cutover | **PARTIAL** | `backend/services/clinical_workspace_service.py:42-44,997-1017` (supports `LEGACY_ONLY`, `SHADOW`, `VNEXT_PRIMARY` via `FeatureFlagService`), `PatientDetails.jsx:446-456`; read-only clinical drift & error observer implemented (`G16-M04`, `G16-M05`: `backend/services/clinical_drift_observer_service.py`, `GET /api/v1/admin/clinical-drift/{tenant_id}`, `backend/tests/services/test_clinical_drift_observer.py`). |

---

## 3. Implementation State Legend

- **`DONE`**: Model, service, router/API, frontend component (where applicable), and automated tests are fully implemented and verified on `staging`.
- **`PARTIAL`**: Core backend projection or UI interaction is active, but sub-features (e.g. standalone command APIs or quick-action launchers) remain pending.
- **`SCHEMA_ONLY`**: Database tables, constraints, Alembic migrations, and RLS policies exist in `backend/models/clinical_core.py`, but no domain service, router endpoints, or UI workflows have been built.
- **`NOT_STARTED`**: Neither active schema nor runtime implementation exists in the codebase.

---

## 4. Dropped Scope (Confirmed Drops — Reclassified in Slice `S00`)

The following 5 matrix items are confirmed drops (per decision PD00 decided by Eslam on 2026-10-17) for removal from active clinic runtime scope and have been reclassified to `HISTORICAL_EXECUTION_MECHANIC` in `docs/product/ODONTOGRAM_TRACEABILITY_MATRIX.md` and `backend/tests/test_odontogram_traceability.py` in slice `S00` (note: `docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md` still enumerates them because `test_product_spec_phases_exact_positive_equality` in `backend/tests/test_odontogram_traceability.py:461-510` forbids editing it):

| Matrix ID | Matrix Title | Classification (`S00`) | Destination Document |
|---|---|---|---|
| `G8-M12` | Add undo stack | `HISTORICAL_EXECUTION_MECHANIC` | `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md` |
| `G10-M06` | Add repeatable-step support | `HISTORICAL_EXECUTION_MECHANIC` | `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md` |
| `G10-M16` | Add template deviation support | `HISTORICAL_EXECUTION_MECHANIC` | `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md` |
| `G11-M03` | Add auto-suggestion from workflow template | `HISTORICAL_EXECUTION_MECHANIC` | `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md` |
| `G12-M14` | Support bridge semantics | `HISTORICAL_EXECUTION_MECHANIC` | `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md` |

*(Note: Per PD00 decided by Eslam on 2026-10-17, all 5 confirmed drop items are reclassified to `HISTORICAL_EXECUTION_MECHANIC` targeting `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md` (no edits to `PROJECT_STANDARDS.md`). S00 recomputes the matrix summary to: ACTIVE 254 / ARCHITECTURE 21 / HISTORICAL 16 / EVIDENCE 36 = 327. Note: no special bridge semantics — a bridge is recorded as one work item with multiple tooth targets via S08 multi-select; revisit if lab/billing needs it).*

