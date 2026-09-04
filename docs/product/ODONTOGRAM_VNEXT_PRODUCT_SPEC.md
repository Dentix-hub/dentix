<!-- CLASSIFICATION: PRODUCT-SPEC -->
# DENTIX Odontogram & Unified Clinical Workflow Product Specification

> **Document Classification**: `PRODUCT-SPEC`
> **Status**: ACTIVE PRODUCT SPECIFICATION
> **Authority**: `PROJECT_STANDARDS.md` (Product & Clinical Architecture)
> **Development Lifecycle**: `docs/engineering/DEVELOPMENT_WORKFLOW.md`
> **Legacy Extraction Source**: `docs/DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md` (Historical Requirement Source; Non-authoritative for current development lifecycle)
> **Traceability Matrix**: [ODONTOGRAM_TRACEABILITY_MATRIX.md](ODONTOGRAM_TRACEABILITY_MATRIX.md)
> **Historical Execution Reference**: `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md`

---

## 1. Product Direction & Scope

This specification defines the functional, clinical, and anatomical requirements for the DENTIX Odontogram and Unified Clinical Workflow (vNext), extracted directly from the historical requirement source (`docs/DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md`).

### Core Product Direction: Native Renderer + Root Extension + Data-Driven Rules
1. **Preserve Established Chart Identity**: Maintain the clean, minimalist visual style and overall spatial layout of the Dentix chart; do not redesign from scratch.
2. **First Anatomy Extension (Roots)**: Add anatomically correct dental roots while keeping crowns visually aligned.
3. **Strict Separation of Concerns**: Decouple the rendering engine from clinical persistence. The renderer component consumes pure projection DTOs and emits user action intents.
4. **Data-Driven Visual Rules**: Condition styling (caries, crowns, endodontic treatments, restorations, missing teeth) is governed by declarative rule registries.
5. **Multi-Instance and Dual-Chart Support**: Render two independent chart instances (e.g. historical baseline vs. current status) with zero state leakage.
6. **Mobile and Internationalization Parity**: Native responsiveness across desktop, tablet, and mobile with full bidirectional support for LTR (English) and RTL (Arabic) layouts.

Implementation lifecycle is governed strictly by `docs/engineering/DEVELOPMENT_WORKFLOW.md`.

---

## 2. Preserved Clinical & Architectural Invariants

All odontogram and clinical workflow implementations must adhere strictly to these non-negotiable boundaries:

1. **Chart Identity**: Preserve the Dentix chart visual identity; do not replace native SVG components with third-party charting libraries.
2. **Clinical Source of Truth**: Renderer state is **never** the clinical source of truth; persistent clinical state resides exclusively in the database and service layer.
3. **Canonical Schema Ownership**: UI DTOs or package-specific types must not become the canonical clinical schema. Clinical data models are defined in backend schemas.
4. **Minimal Dependencies**: Utilize native React, SVG primitives, and CSS; avoid introducing heavy external graphics packages.
5. **Domain Logic Placement**: Clinical domain logic (treatment rules, pricing, session continuity) belongs in backend services, not in UI rendering components.
6. **Historical Data Preservation**: Existing clinical data must never be overwritten or discarded. Legacy data is transformed deterministically with zero data loss.
7. **No Auto-Booking Invariant (G11-M08)**: Appointment integration must **NEVER** auto-book an appointment without explicit, confirmed user action.
8. **Tenant Isolation**: All clinical findings, work items, and treatment plans must enforce strict tenant separation at the database level.
9. **Modal De-emphasis**: Replace disruptive, monolithic modal dialogs with seamless, chairside surface selection and inline inspectors.
10. **Inventory Deduction Timing**: Consumable materials must never be deducted upon plan creation; deduction occurs strictly at the actual-use point associated with the care session.
11. **Financial Parity Gate**: Legacy billing and payment sources must be preserved in shadow mode; live financial cutover is prohibited prior to exact verified parity.

---

## 3. Part I — Chart & Odontogram Anatomical Foundation (Phases A0–A17)

Part I establishes the anatomical rendering engine and clinical visualization capabilities:

| Phase | Source Phase Title | Scope | Acceptance |
|---|---|---|---|
| **A0** | Baseline Revalidation and Freeze | *Classification: Process setup (A0-M01..M03: Historical Mechanics; A0-M04: Architecture Constraint).* A0-M01: Revalidate current `main`; A0-M02: Create execution docs folder; A0-M03: Record baseline metadata; A0-M04: Create explicit scope lock note | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A1** | Final Chart Architecture Lock | *Classification: Architecture Constraints (A1-M01..M03) & Product Requirements (A1-M04).* A1-M01: Write chart direction ADR; A1-M02: Define chart architectural layers; A1-M03: Define renderer non-responsibilities; A1-M04: Define future readiness targets | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A2** | Frontend Chart Module Scaffold | A2-M01: Create feature directory; A2-M02: Create subfolders; A2-M03: Create entry workspace component; A2-M04: Create temporary demo route | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A3** | Anatomy Registry Foundation | A3-M01: Create anatomy registry file; A3-M02: Define anatomy model shape; A3-M03: Define permanent dentition keys; A3-M04: Define primary dentition keys; A3-M05: Define mixed-dentition compatibility note | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A4** | Crown Outline Integration | A4-M01: Inventory current crown outlines; A4-M02: Normalize crown shape access; A4-M03: Preserve current visual style | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A5** | Root Anatomy Definition | A5-M01: Create root outline model; A5-M02: Add single-root anterior definitions; A5-M03: Add premolar root definitions; A5-M04: Add molar root definitions; A5-M05: Add primary tooth root definitions; A5-M06: Keep root style visually aligned | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A6** | Surface Geometry Foundation | A6-M01: Create surface code constants; A6-M02: Define per-tooth clickable surface geometry; A6-M03: Support anterior surface model; A6-M04: Support posterior surface model; A6-M05: Add hover/focus/selected states | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A7** | Renderer Contract | A7-M01: Create renderer adapter interface; A7-M02: Define input DTO contract; A7-M03: Define output interaction intents; A7-M04: Prevent persistence leakage | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A8** | Projection DTO for Demo Use | A8-M01: Create demo DTO schema; A8-M02: Define tooth visual state shape; A8-M03: Define target subshape; A8-M04: Add sample DTO fixtures | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A9** | Visual Rule Registry | A9-M01: Create visual rule registry file; A9-M02: Add lifecycle rules; A9-M03: Add finding rules; A9-M04: Add procedure rules; A9-M05: Add layer mapping | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A10** | Root Layer Rendering | A10-M01: Add root layer renderer; A10-M02: Handle single-root teeth; A10-M03: Handle premolars; A10-M04: Handle molars; A10-M05: Handle primary teeth; A10-M06: Prevent root overlap artifacts | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A11** | Notation and Labels | A11-M01: Support current notation display mode; A11-M02: Add notation abstraction; A11-M03: Verify label placement after roots | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A12** | Demo Clinical Scenarios | A12-M01: Create adult dentition fixture; A12-M02: Create primary dentition fixture; A12-M03: Create mixed dentition fixture; A12-M04: Create caries-on-surface fixture; A12-M05: Create MOD restoration fixture; A12-M06: Create RCT fixture; A12-M07: Create crown fixture; A12-M08: Create missing tooth fixture; A12-M09: Create implant fixture; A12-M10: Create bridge fixture; A12-M11: Create simultaneous existing + planned fixture | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A13** | Multi-Instance and History Compare | A13-M01: Create dual-chart page; A13-M02: Ensure state isolation; A13-M03: Ensure independent layer filtering; A13-M04: Ensure read-only multi-instance support | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A14** | Basic UI Layer | A14-M01: Create chart shell header; A14-M02: Create simple legend; A14-M03: Create simple inspector panel; A14-M04: Create simple selection summary; A14-M05: Keep UI intentionally simple | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A15** | Mobile, RTL, and Accessibility | A15-M01: Verify chart on desktop; A15-M02: Verify chart on tablet width; A15-M03: Verify chart on mobile width; A15-M04: Add quadrant-friendly mobile behavior; A15-M05: Verify Arabic RTL layout; A15-M06: Verify English LTR layout; A15-M07: Add keyboard focus states; A15-M08: Add accessible labels where practical | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A16** | Testing | *Classification: Evidence & Handoff Requirements (A16-M01..M07).* A16-M01: Add anatomy registry coverage test; A16-M02: Add renderer smoke test; A16-M03: Add multi-instance isolation test; A16-M04: Add root rendering snapshot or visual regression test; A16-M05: Add mixed dentition render test; A16-M06: Add RTL render test; A16-M07: Add mobile render test if tooling allows | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |
| **A17** | Evidence and Handoff Package | *Classification: Evidence Deliverables (A17-M01..M05) & Historical Mechanics (A17-M06..M07).* A17-M01: Capture desktop screenshots; A17-M02: Capture mobile screenshots; A17-M03: Capture RTL screenshots; A17-M04: Capture history-compare screenshots; A17-M05: Write Codex completion report; A17-M06: Write handoff package for Gemini; A17-M07: Hard stop | Acceptance defined per item in ODONTOGRAM_TRACEABILITY_MATRIX.md. |

---

## 4. Part II — Unified Clinical Workflow VNext (Phases G0–G16)

Part II integrates the anatomical renderer into live clinical, diagnostic, treatment planning, and operational workflows:

| Phase | Source Phase Title | Scope | Acceptance |
|---|---|---|---|
| **G0** | Revalidation Before Full VNext | *Classification: Historical Execution Mechanics (G0-M01..M05).* G0-M01: Pull latest `main`; G0-M02: Pull Codex chart branch; G0-M03: Compare chart branch against handoff docs; G0-M04: Write Gemini kickoff note; G0-M05: Confirm no contract drift before backend work starts | kickoff note committed. |
| **G1** | Additive Clinical Core Schema | G1-M01: Create `clinical_work_items`; G1-M02: Add work item constraints and indexes; G1-M03: Create `clinical_work_item_targets`; G1-M04: Add target validation rules; G1-M05: Create `clinical_treatment_plans`; G1-M06: Create `clinical_treatment_plan_phases`; G1-M07: Create `clinical_treatment_plan_items`; G1-M08: Create `clinical_events`; G1-M09: Create `clinical_event_targets`; G1-M10: Create `care_sessions`; G1-M11: Create `care_session_steps`; G1-M12: Create `care_observations`; G1-M13: Create `workflow_templates`; G1-M14: Create `next_visit_requests`; G1-M15: Create `clinical_attachment_links`; G1-M16: Add RLS policies to every new tenant table; G1-M17: Add migration; G1-M18: Add schema tests | migration applies cleanly and tests pass. |
| **G2** | Canonical Catalog, Taxonomy, and Workflow Templates | G2-M01: Define canonical procedure codes; G2-M02: Define canonical finding codes; G2-M03: Define tooth lifecycle codes; G2-M04: Define treatment lifecycle codes; G2-M05: Create procedure category model; G2-M06: Create procedure subcategory model; G2-M07: Map core procedures to categories; G2-M08: Map findings to supported target types; G2-M09: Create RCT template v1; G2-M10: Create crown template v1; G2-M11: Create bridge template v1; G2-M12: Create composite template v1; G2-M13: Create extraction template v1; G2-M14: Create denture template v1; G2-M15: Add template versioning rules; G2-M16: Add catalog tests | catalog and templates exist, validated, and tested. |
| **G3** | Deterministic Legacy Mapping Engine | G3-M01: Create migration package scaffold; G3-M02: Implement treatment procedure mapping; G3-M03: Implement treatment status mapping; G3-M04: Implement tooth notation mapping; G3-M05: Implement treatment-to-work-item mapping; G3-M06: Implement treatment-to-event mapping; G3-M07: Implement tooth-status mapping; G3-M08: Implement legacy treatment-session mapping; G3-M09: Preserve old free-text sessions; G3-M10: Implement exact lab-link mapping; G3-M11: Mark ambiguous duplicates only; G3-M12: Add idempotency tests; G3-M13: Add tenant isolation tests | deterministic mapper works and source rows remain untouched. |
| **G4** | Controlled Backfill | G4-M01: Add dry-run mode; G4-M02: Add tenant-scoped execution; G4-M03: Add batch processing; G4-M04: Add resume checkpointing; G4-M05: Backfill treatments; G4-M06: Backfill tooth-status events; G4-M07: Backfill legacy care sessions; G4-M08: Backfill exact lab relationships; G4-M09: Backfill deterministic attachment links only; G4-M10: Verify record counts; G4-M11: Verify old data unchanged; G4-M12: Verify inventory unchanged; G4-M13: Verify payments unchanged; G4-M14: Generate backfill report | parity and invariance checks pass. |
| **G5** | Projection Layer and Real Chart Data | G5-M01: Create clinical projection service; G5-M02: Add `as_of` support; G5-M03: Add tooth summary projection; G5-M04: Add work-item summary projection; G5-M05: Add patient clinical workspace aggregate; G5-M06: Add legacy read fallback; G5-M07: Add feature flag; G5-M08: Add shadow-read comparison; G5-M09: Add projection caching; G5-M10: Add performance benchmark | chart can render from real projected data. |
| **G6** | Chart Integration to the Codex Renderer | G6-M01: Replace demo DTOs with projection-backed DTOs; G6-M02: Keep renderer contract stable or document changes precisely; G6-M03: Connect chart workspace to real patient data; G6-M04: Preserve multi-instance capability; G6-M05: Preserve mobile and RTL behavior; G6-M06: Add projection-to-renderer integration tests | real data renders through the Codex chart foundation. |
| **G7** | Command/API Layer | G7-M01: Create command service; G7-M02: Add work item create API; G7-M03: Add work item update API; G7-M04: Add finding create API; G7-M05: Add bulk finding API; G7-M06: Add procedure create API; G7-M07: Add bulk procedure API; G7-M08: Add event correction API; G7-M09: Add workspace read API; G7-M10: Add tooth detail API; G7-M11: Add history API; G7-M12: Add permission enforcement; G7-M13: Add tenant security tests; G7-M14: Add API contract tests; G7-M15: Add idempotency keys; G7-M16: Add optimistic concurrency handling | APIs are safe, tested, and bounded. |
| **G8** | Zero-Friction Charting UX | G8-M01: Add tooth selection state; G8-M02: Add quick action launcher; G8-M03: Add tooth-first flow; G8-M04: Add procedure-first flow; G8-M05: Add sticky tool mode; G8-M06: Add multi-select; G8-M07: Add direct surface interaction; G8-M08: Add favorites; G8-M09: Add recents; G8-M10: Add search; G8-M11: Add smart defaults; G8-M12: Add undo stack; G8-M13: Add consequence-aware remove; G8-M14: Measure click budget; G8-M15: De-emphasize old giant modal | common tasks hit the click-budget targets. |
| **G9** | First-Class Treatment Plans | G9-M01: Create treatment plan service; G9-M02: Add plan create API; G9-M03: Add phase CRUD/reorder; G9-M04: Add work item membership API; G9-M05: Support shared work items across plans; G9-M06: Add plan lifecycle states; G9-M07: Add accept-plan flow; G9-M08: Preserve alternatives; G9-M09: Add plan overlay to chart; G9-M10: Add estimate projection; G9-M11: Add plan comparison UX; G9-M12: Add legacy safety rules; G9-M13: Add concurrency tests; G9-M14: Add E2E scenario | treatment plans work without duplicating care episodes. |
| **G10** | Sessions and Resume Engine | G10-M01: Create care session service; G10-M02: Add start-session command; G10-M03: Add finish-session command; G10-M04: Add step add/update API; G10-M05: Add partial-step support; G10-M06: Add repeatable-step support; G10-M07: Add observation API; G10-M08: Build minimal RCT structured UI; G10-M09: Add canal-target UI; G10-M10: Add working-length structured entry; G10-M11: Add compact finish-session sheet; G10-M12: Build resume engine; G10-M13: Add continue-treatment card; G10-M14: Add clinical summary generation; G10-M15: Preserve free notes; G10-M16: Add template deviation support; G10-M17: Add finalization audit trail; G10-M18: Add concurrent session protection; G10-M19: Migrate new writes away from free-text-only session model; G10-M20: Add RCT scenario integration test | doctor can resume treatment without reading old notes manually. |
| **G11** | Appointment Integration | G11-M01: Link session to appointment; G11-M02: Add next-visit request creation; G11-M03: Add auto-suggestion from workflow template; G11-M04: Add reception queue; G11-M05: Convert request to appointment; G11-M06: Populate appointment reason; G11-M07: Suggest duration; G11-M08: Prevent auto-booking without user action; G11-M09: Handle appointment cancellation safely; G11-M10: Handle appointment completion safely; G11-M11: Add integration tests; G11-M12: Add idempotency/race tests | reception can see what the patient needs next. |
| **G12** | Lab Integration | G12-M01: Add real FK from lab order to work item; G12-M02: Add exact legacy migration support; G12-M03: Stop using note-string linkage for new data; G12-M04: Create lab requirement definition; G12-M05: Add lab-ready trigger; G12-M06: Add one-tap lab handoff sheet; G12-M07: Allow missing optional lab data; G12-M08: Create lab order without creating duplicate treatment; G12-M09: Decouple lab price from synthetic treatment creation; G12-M10: Add lab status mapping; G12-M11: Reflect lab state in work item; G12-M12: Prevent auto-complete when lab is ready; G12-M13: Add shade/material sync rules; G12-M14: Support bridge semantics; G12-M15: Add duplicate-billing regression test; G12-M16: Add handoff idempotency | lab workflows do not duplicate patient charges. |
| **G13** | Inventory Integration | G13-M01: Distinguish material session from care session; G13-M02: Add `care_session_id` to new usage model; G13-M03: Preserve old usage data; G13-M04: Create material suggestion service; G13-M05: Prevent stock deduction at plan creation; G13-M06: Deduct at actual use point; G13-M07: Support different materials per session; G13-M08: Preserve divisible-material logic; G13-M09: Aggregate work-item material cost; G13-M10: Add migration invariance test; G13-M11: Add endo material scenario test | inventory follows care sessions without rewriting history. |
| **G14** | Finance Integration and Parity | G14-M01: Define billing policy model; G14-M02: Keep old finance source authoritative during shadow mode; G14-M03: Add work-item billing projection; G14-M04: Design `clinical_charges`; G14-M05: Preserve payments unchanged; G14-M06: Create shadow calculator; G14-M07: Run per-patient parity; G14-M08: Run per-tenant parity; G14-M09: Detect legacy lab double-charge cases; G14-M10: Add deterministic remediation workflow; G14-M11: Add doctor-share compatibility tests; G14-M12: Cut finance reads only behind flag; G14-M13: Keep payments stable; G14-M14: Add financial regression suite | no cutover before exact parity. |
| **G15** | Files and Clinical Context | G15-M01: Keep attachment storage unchanged; G15-M02: Add context links only; G15-M03: Link images to tooth; G15-M04: Link images to work item; G15-M05: Link images to care session; G15-M06: Add purpose codes; G15-M07: Show relevant images in tooth inspector; G15-M08: Show relevant images in session view; G15-M09: Add deterministic legacy link migration only | no duplicate uploads or unsafe file moves. |
| **G16** | Rollout and Controlled Cutover | G16-M01: Enable internal tenant only; G16-M02: Roll out read-only VNext; G16-M03: Enable internal writes; G16-M04: Monitor errors; G16-M05: Monitor parity; G16-M06: Pilot clinic; G16-M07: Small rollout percentage; G16-M08: Add tenant rollback toggle; G16-M09: Expand rollout gradually; G16-M10: Keep legacy compatibility during rollout; G16-M11: Observe stability window; G16-M12: Stop legacy writes only after evidence; G16-M13: Retire dead code only after stability | controlled rollout succeeds without destructive cutover risk. |

---

## 5. Traceability & Verification Contract

Every micro-task identifier from the historical master plan is cataloged in the comprehensive traceability matrix:

* **Complete Matrix**: See [ODONTOGRAM_TRACEABILITY_MATRIX.md](ODONTOGRAM_TRACEABILITY_MATRIX.md) for the exhaustive 327-item register.
* **Traceability Totals**:
  - `ACTIVE_PRODUCT_REQUIREMENT`: **259 items**
  - `ARCHITECTURE_CONSTRAINT`: **21 items**
  - `HISTORICAL_EXECUTION_MECHANIC`: **11 items**
  - `EVIDENCE_OR_HANDOFF_REQUIREMENT`: **36 items**
  - **Total Accounted For**: **327 items** (100% accounted for; 0 items unmapped or discarded).
* **Automated Verification**: The integrity, correct naming, ID ranges, classifications, and absence of unsourced semantics are validated deterministically by `backend/tests/test_odontogram_traceability.py`.
