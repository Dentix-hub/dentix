<!-- CLASSIFICATION: PRODUCT PROPOSAL (A3 / F-11) — NO CODE IMPLEMENTATION -->
# Proposal: Procedure-to-Tooth-Condition Suggestions

## 1. Overview & Decision Context
As decided by Eslam (Decision A3 / F-11):
- Recording a procedure **suggests** a resulting tooth condition on the odontogram / clinical chart.
- The doctor **must confirm** the suggestion within the confirmation sheet.
- **No automatic changes** will occur behind the scenes without doctor confirmation.
- Implementation is deferred until this proposal and mapping table are explicitly approved by Eslam.

---

## 2. Existing Tooth-Condition Vocabulary (Source Code & Exact File:Line)

The DENTIX codebase currently manages tooth conditions across three architectural layers:

### A. Canonical Clinical VNext Domain (`backend/clinical/catalog.py`)
- **Tooth Lifecycle Codes** (`backend/clinical/catalog.py:38-46`):
  - `PRESENT` ("PRESENT") — Normal present tooth
  - `MISSING` ("MISSING") — Congenitally or clinically absent tooth
  - `EXTRACTED` ("EXTRACTED") — Surgically removed tooth
  - `IMPACTED` ("IMPACTED") — Impacted tooth
  - `UNERUPTED` ("UNERUPTED") — Unerupted tooth
- **Finding Codes** (`backend/clinical/catalog.py:53-59`):
  - `CARIES` ("CARIES") — Carious lesion
  - `FRACTURE` ("FRACTURE") — Structural fracture
  - `PAIN` ("PAIN") — Symptomatic pain

### B. Legacy Database & Mapping Allowlist (`backend/clinical/legacy_mapping.py` & `backend/models/clinical.py`)
- **ToothStatus Model** (`backend/models/clinical.py:69-86`):
  - `tooth_number`: Integer FDI tooth identifier
  - `condition`: Text condition string
  - `notes`: Text notes (may contain `[Surfaces: ...]`)
- **Lifecycle Allowlist** (`backend/clinical/legacy_mapping.py:513-524`):
  - `"PRESENT"`, `"Healthy"` $\rightarrow$ `PRESENT`
  - `"MISSING"`, `"Missing"` $\rightarrow$ `MISSING`
  - `"EXTRACTED"`, `"Extracted"` $\rightarrow$ `EXTRACTED`
  - `"IMPACTED"`, `"Impacted"` $\rightarrow$ `IMPACTED`
  - `"UNERUPTED"`, `"Unerupted"` $\rightarrow$ `UNERUPTED`
- **Finding Allowlist** (`backend/clinical/legacy_mapping.py:526-534`):
  - `"CARIES"`, `"Caries"`, `"Decayed"` $\rightarrow$ `CARIES`
  - `"FRACTURE"`, `"Fracture"` $\rightarrow$ `FRACTURE`
  - `"PAIN"`, `"Pain"` $\rightarrow$ `PAIN`
- **Procedure Allowlist** (`backend/clinical/legacy_mapping.py:536-545`):
  - `"REST_COMPOSITE"`, `"Filled"`, `"Composite"` $\rightarrow$ `REST_COMPOSITE`
  - `"ENDO_RCT"`, `"RootCanal"` $\rightarrow$ `ENDO_RCT`
  - `"PROS_CROWN"`, `"Crown"` $\rightarrow$ `PROS_CROWN`
  - `"SURG_EXTRACTION"` $\rightarrow$ `SURG_EXTRACTION`

### C. Frontend Odontogram & Modals
- **DentalChartSVG Visual Styles & Legend** (`frontend/src/features/dental/DentalChartSVG.jsx:81-88, 573-586`):
  - `Healthy` (سليم) — Fill `#ffffff`, Stroke `#94a3b8`
  - `Decayed` (تسوس) — Fill `#fecaca`, Stroke `#ef4444`
  - `Filled` (حشو) — Fill `#bfdbfe`, stroke `#3b82f6`
  - `Missing` (مخلوع) — Fill `#f1f5f9`, stroke `#e2e8f0`, opacity 0.3
  - `Crown` (طربوش) — Fill `#fef08a`, stroke `#eab308`
  - `RootCanal` (عصب) — Fill `#e9d5ff`, stroke `#a855f7`
- **TreatmentModal Condition Selectors** (`frontend/src/shared/ui/modals/TreatmentModal.jsx:616-701`):
  - Tab 1 (Status): `Healthy`, `Missing`, `Impacted`, `Unerupted`, `Retained Root`
  - Tab 2 (Pathology): `Decayed`, `Fractured`, `Abscess`, `Mobility`, `Pain`
  - Tab 3 (Restorations): `Filled`, `Root Canal`, `Crown`, `Bridge`, `Implant`

---

## 3. Canonical Procedure Categories & Codes (`backend/clinical/catalog.py`)

The system defines 5 procedure categories and 8 canonical procedure definitions:

1. **Category `restorative`** (`backend/clinical/catalog.py:189-194`):
   - Subcategory: `direct` (Direct Restorations)
   - Canonical Code: `REST_COMPOSITE` ("Composite Restoration")
2. **Category `endodontic`** (`backend/clinical/catalog.py:195-200`):
   - Subcategory: `root-canal` (Root Canal Therapy)
   - Canonical Code: `ENDO_RCT` ("Root Canal Treatment")
3. **Category `prosthodontic`** (`backend/clinical/catalog.py:200-205`):
   - Subcategory: `fixed` (Fixed Prosthodontics)
     - Canonical Code: `PROS_CROWN` ("Crown Restoration")
     - Canonical Code: `PROS_BRIDGE` ("Fixed Bridge")
   - Subcategory: `removable` (Removable Prosthodontics)
     - Canonical Code: `PROS_DENTURE` ("Removable Denture")
4. **Category `implantology`** (`backend/clinical/catalog.py:205-209`):
   - Subcategory: `fixture` (Implant Fixtures)
     - Canonical Code: `IMPLANT_FIXTURE` ("Implant Fixture")
   - Subcategory: `prosthetic` (Implant Prosthetics)
     - Canonical Code: `IMPLANT_CROWN` ("Implant Crown")
5. **Category `oral-surgery`** (`backend/clinical/catalog.py:210-215`):
   - Subcategory: `extraction` (Extractions)
     - Canonical Code: `SURG_EXTRACTION` ("Surgical Extraction")

---

## 4. Proposed Mapping Table: `Procedure Category -> Suggested Condition`

The suggested condition applies **only when the procedure status is `Done` (completed)**. If the procedure is saved as `Pending` (planned / in-progress), the default suggestion is `no suggestion`.

| Procedure Category / Code | Example Procedures in Clinic | Suggested Condition (Visual & DB) | Canonical Visual Code | Rationale & Clinical Rules |
| :--- | :--- | :--- | :--- | :--- |
| **`restorative`** / `REST_COMPOSITE` | Direct composite restoration, Amalgam, Glass ionomer, Temporary filling | **`Filled`** (حشو) | `REST_COMPOSITE` | Restorative procedure fills a carious cavity or defect; resolves `Decayed` or `Fractured` into `Filled`. |
| **`endodontic`** / `ENDO_RCT` | Root canal treatment, Pulpectomy, Retreatment, Apexification | **`RootCanal`** (عصب) | `ENDO_RCT` | Endodontic obturation renders the tooth endodontically treated. Overrides prior decay or pain. |
| **`prosthodontic`** / `PROS_CROWN` | Full crown (porcelain, zirconia, E-max), Veneer, Onlay | **`Crown`** (طربوش) | `PROS_CROWN` | Extra-coronal coverage places a crown over the anatomical tooth. |
| **`prosthodontic`** / `PROS_BRIDGE` | Fixed partial denture abutment / retainer | **`Crown`** (طربوش) | `PROS_CROWN` | Abutment preparation and retainer placement function visually as crowns on abutment teeth. |
| **`prosthodontic`** / `PROS_DENTURE` | Complete or partial removable acrylic/cast denture | *no suggestion* | *None* | Removable appliances do not permanently alter the underlying tooth condition. |
| **`oral-surgery`** / `SURG_EXTRACTION` | Simple extraction, Surgical extraction, Root removal | **`Missing`** (مخلوع) | `EXTRACTED` / `MISSING` | Extraction physically removes the tooth from the arch; tooth becomes absent/extracted. |
| **`implantology`** / `IMPLANT_FIXTURE` | Endosseous fixture placement | *no suggestion* (remains `Missing`) | `IMPLANT_FIXTURE` | Fixture placement occurs in an edentulous space; does not create a natural crown until prosthetic stage. |
| **`implantology`** / `IMPLANT_CROWN` | Implant-supported crown cementation / screw-retained | **`Crown`** (طربوش) | `PROS_CROWN` | Final prosthetic crown loaded on implant site. |
| **`diagnostic`** / Custom | Comprehensive examination, Periapical X-Ray, Panoramic X-Ray, Pulp vitality test | *no suggestion* (لا تغيير) | *None* | Diagnostic investigations do not alter tooth anatomical structure. |
| **`preventive` / `periodontics`** | Dental scaling, Prophylaxis, Fluoride varnish, Deep root planing | *no suggestion* (لا تغيير) | *None* | Hygiene and periodontal procedures maintain existing tooth structure without structural change. |
| **`orthodontic`** | Bracket bonding, Archwire activation, Retainer fitting | *no suggestion* (لا تغيير) | *None* | Orthodontic mechanics do not alter individual tooth pathology/restoration states. |
| **`cosmetic`** | Chairside or home teeth whitening / bleaching | *no suggestion* (لا تغيير) | *None* | Shade change without structural or restoration change. |

---

## 5. Confirmation Sheet UI Control Placement

The control will be integrated inside `QuickTreatmentSheet.jsx` (`frontend/src/features/clinical-chart/components/QuickTreatmentSheet.jsx`).

### Layout & Placement Architecture:
1. **Vertical Location**:
   - Directly below the `Status segmented control` (`Done` vs `Pending`, line 516) and above the `consumedMaterials` BOM summary (line 519).
2. **Visual Design & Components**:
   - A distinct card with border matching the procedure swatch palette (`border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-900/40 rounded-xl p-3`).
   - **Header**: Label `تحديث حالة السن في الرسم الطبي` (Update Tooth Chart Status).
   - **Doctor Confirmation Checkbox / Toggle**:
     - Checkbox: `[✓] تحديث حالة السن إلى "${suggestedConditionName}"` (e.g. `[✓] تحديث حالة السن إلى "حشو"`).
     - Color Badge: Small colored swatch preview representing the target chart status (`STATUS_STYLES[suggestedCondition]`).
   - **Multi-tooth Support**:
     - When multi-teeth are selected (`effectiveTeeth.length > 1`), displays: `تطبيق الحالة على الـ ${count} أسنان المحددة` (Apply condition to all N selected teeth).
   - **Manual Override / Dropdown**:
     - Inline dropdown permitting the doctor to select a different condition or pick "بدون تغيير" (No change) without opening the full modal.
3. **Execution Semantics**:
   - If the doctor unchecks the box $\rightarrow$ Only the treatment work-item is saved; `ToothStatus` remains untouched.
   - If the doctor leaves the box checked $\rightarrow$ When submitting, both the treatment record and the corresponding `ToothStatus` records are updated transactionally.
   - If the procedure status is set to `Pending`, the suggestion checkbox defaults to unchecked with an explanatory note: `(الإجراء قيد التنفيذ - لن يتم تغيير حالة السن حتى اكتماله)`.

---

## 6. Approvals & Decisions Recorded
- [x] Confirmed procedure category to condition mapping table (Section 4) — Approved by Eslam.
- [x] Default checkbox behavior: **Checked by default for `Done` status** (one-click confirm) — Approved by Eslam.
- [x] Confirmed UI placement inside `QuickTreatmentSheet.jsx` (Section 5) — Approved by Eslam.
