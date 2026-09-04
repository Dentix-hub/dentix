<!-- CLASSIFICATION: PRODUCT-SPEC -->
# DENTIX Odontogram & Unified Clinical Workflow Product Specification

> **Document Classification**: `PRODUCT-SPEC`
> **Status**: ACTIVE PRODUCT SPECIFICATION
> **Authority**: `PROJECT_STANDARDS.md` (Product & Clinical Architecture)
> **Development Lifecycle**: `docs/engineering/DEVELOPMENT_WORKFLOW.md`
> **Historical Execution Reference**: `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md`

---

## 1. Scope & Invariant Principles

This document defines the functional, clinical, and anatomical requirements for the DENTIX Odontogram and Unified Clinical Workflow (vNext). It extracts and preserves all clinical requirements, preserved boundaries, and acceptance criteria previously tracked in legacy wave execution documents.

Implementation work touching these specifications follows the standard DENTIX development lifecycle defined in `docs/engineering/DEVELOPMENT_WORKFLOW.md`.

---

## 2. Preserved Clinical Boundaries

All odontogram and clinical chart implementations must adhere strictly to these core boundaries:

1. **Chart Identity**: Preserve the established Dentix chart visual identity; do not redesign from zero.
2. **Clinical Source of Truth**: Renderer state is NOT the clinical source of truth; persistent clinical state lives in the database and service layer.
3. **Canonical Schema**: A package-owned or UI-owned DTO must not become the canonical clinical schema. Clinical schemas are governed by backend domain models.
4. **Dependency Minimization**: Reuse existing native DENTIX frontend primitives and SVG rendering; avoid introducing external charting/rendering packages.
5. **Separation of Concerns**: Clinical domain complexity belongs in the service/domain layer, not inside frontend render components.
6. **Data Preservation**: Never overwrite or discard existing patient clinical records; maintain historical audit trails and versioning.
7. **No Auto-Booking (G11-M08)**: Clinical appointment scheduling from chart recommendations must NEVER auto-book an appointment without explicit user action and confirmation.
8. **Scope Discipline**: Foundation rendering additions must not prematurely alter backend finance, appointments, inventory, or migration schemas without dedicated domain tasks.

---

## 3. Foundation Requirements Matrix (Part I Anatomical Engine)

| Requirement Group | Focus Area | Acceptance Criteria & Semantics |
|---|---|---|
| **A0 (A0-M01..M04)** | Baseline Integrity | Multi-quadrant coordinate system, tooth index alignment, viewport boundaries. |
| **A1 (A1-M01..M04)** | Architecture Direction | ADR compliance, layered SVG structure, isolation between crown and root vectors. |
| **A2 (A2-M01..M04)** | Route & Scaffolding | Patient chart tab mounting, responsive canvas scaling, test harness availability. |
| **A3 (A3-M01..M05)** | Anatomy Families | Anatomical correctness across incisors, canines, premolars, and molars. |
| **A4 (A4-M01..M03)** | Crown Outline Parity | Visual parity for occlusal, buccal, lingual, mesial, and distal surface outlines. |
| **A5 (A5-M01..M06)** | Root Anatomy Families | Multi-root renderers for maxillary/mandibular molars (1, 2, and 3 root systems). |
| **A6 (A6-M01..M05)** | Surface Selection | Surface-level click targets, selection states, hover feedback, active condition overlays. |
| **A7 (A7-M01..M04)** | Renderer Boundary | Decoupling rendering primitives from network state; pure functional projection. |
| **A8 (A8-M01..M04)** | Projection Contract | Deterministic projection DTO translating clinical records into tooth visual states. |
| **A9 (A9-M01..M05)** | Visual States | Clinical condition styling (caries, restorations, crowns, endodontic treatments, missing). |
| **A10 (A10-M01..M06)** | Root Layer Delivery | Full root layer integration across all 32 permanent and 20 primary teeth. |
| **A11 (A11-M01..M03)** | Notation & Labels | Dual notation support: FDI Two-Digit system and Universal Numbering System. Primary tooth lettering (A-T). |
| **A12 (A12-M01..M11)** | Fixture Matrix | Complete clinical scenario fixtures: virgin dentition, severe decay, pediatric mixed dentition, full prosthetic reconstruction. |
| **A13 (A13-M01..M04)** | Dual-Chart Compare | Isolated historical comparison mode: side-by-side view comparing baseline vs current clinical status without state bleed. |
| **A14 (A14-M01..M05)** | Shell & Inspector | Tooth inspector drawer/panel displaying selected tooth history, surface treatments, and diagnostic notes. |
| **A15 (A15-M01..M08)** | Accessibility & RTL | Full keyboard navigation, screen reader ARIA labels, RTL layout preservation in Arabic mode, tablet/mobile touch responsiveness. |
| **A16 (A16-M01..M07)** | Regression Gate | Comprehensive regression suite verifying zero visual or behavioral regressions across supported viewports and browsers. |
| **A17 (A17-M01..M07)** | Evidence & Handoff | Documented visual and clinical evidence validating clinical fidelity. |

---

## 4. Extended Clinical Workflow Requirements (Part II Domain Integration)

| Group | Module | Functional & Clinical Scope |
|---|---|---|
| **G0 (G0-M01..M05)** | Clinical Kickoff | Boundary alignment, terminology verification, domain event definition. |
| **G1 (G1-M01..M18)** | Clinical Schema & Migrations | PostgreSQL relational schema for clinical findings, tooth conditions, periodontal charting, and safe Alembic migrations. |
| **G2 (G2-M01..M16)** | Taxonomy & Templates | Standardized dental diagnostic taxonomy (ICD-10-CM / CDT codes) and quick-entry clinical diagnosis templates. |
| **G3 (G3-M01..M13)** | Clinical Data Mapper | Bidirectional mapping between legacy tooth data formats and normalized clinical schemas with data-loss prevention. |
| **G4 (G4-M01..M14)** | Migration & Backfill | Non-blocking data migration runner ensuring legacy patient records are preserved and mapped accurately. |
| **G5 (G5-M01..M10)** | Projection Service | High-performance cached projection service computing live odontogram states from clinical event history. |
| **G6 (G6-M01..M06)** | Chart Live Integration | Seamless live integration of the clinical odontogram into the patient record workspace with optimistic UI updates. |
| **G7 (G7-M01..M16)** | Clinical Commands & RBAC | Granular command endpoints for dental procedures with strict role verification (`Permission.CLINICAL_WRITE`). |
| **G8 (G8-M01..M15)** | Diagnostic Flows | Multi-step clinical diagnostic workflows (perio pocket depth recording, mobility, furcation involvement). |
| **G9 (G9-M01..M14)** | Treatment Plans | Treatment plan formulation linking odontogram conditions directly to procedure items, phases, and cost projections. |
| **G10 (G10-M01..M20)**| Endodontic / RCT Flow | Specialized root canal treatment tracking (canal length, file sizes, obturation materials, apex locator records). |
| **G11 (G11-M01..M12)**| Appointment Linkage | Procedure scheduling linkage. Invariant: User must explicitly confirm any appointment creation (no auto-booking). |
| **G12 (G12-M01..M16)**| Billing Safety Linkage | Procedure completion triggering invoice drafts; financial ledger immutability and insurance claim formatting. |
| **G13 (G13-M01..M11)**| Inventory Deductions | Automated dental material deductions linked to procedure completion (composite syringes, anesthetic carpules, burs). |
| **G14 (G14-M01..M14)**| Clinical Policy & Cutover| Audit compliance, clinic setting switches, phased rollout capability per tenant. |
| **G15 (G15-M01..M09)**| Imaging Context | Attaching radiographic X-rays and intraoral photographs directly to individual tooth or quadrant records. |
| **G16 (G16-M01..M13)**| Clinical Stability | Multi-tenant load verification, clinical emergency recovery protocols, performance verification. |

---

## 5. Requirement Preservation & Traceability

Every numbered requirement identifier (`A0-M01` through `A17-M07` and `G0-M01` through `G16-M13`) represents an invariant functional requirement. Implementation PRs must cite the corresponding requirement ID when implementing or updating clinical features.
