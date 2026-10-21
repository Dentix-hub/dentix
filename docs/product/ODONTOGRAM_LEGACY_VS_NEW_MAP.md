<!-- CLASSIFICATION: ARCHITECTURAL_REFERENCE -->
# DENTIX Odontogram — Legacy vs. VNext Control Inventory & Entry-Point Map (U3.1)

**Classification:** Active Architectural Reference  
**Created:** 2026-10-20 (Task U3 — UX Stabilization)  
**Author:** Pair-programmed by Gemini Flash & Eslam for DENTIX  
**Purpose:** Comprehensive inventory of all odontogram, treatments, and plans controls across the legacy stack and the clinical vNext stack. Maps entry points to `TreatmentModal`, establishes cache invalidation contracts for subsequent slices (S30–S36), and provides proposed cutover fates for Eslam's final decision.

---

## 1. Clinical Control Inventory (Chart, Treatments & Plans Tabs)

Every control below exists in `origin/staging` and has been verified against actual codebase locations (`file:line`).

> [!IMPORTANT]
> **Proposed Cutover Fates:** Fates marked as `[PROPOSAL]` (`keep`, `hide`, `remove`) are architectural recommendations submitted for Eslam's review and decision. No legacy controls are deleted or disabled within this UX stabilization milestone.

| # | Control Name & Location | Component (`file:line`) | What it Writes | Gating Feature Flag | Proposed Cutover Fate | Notes / Rationale |
|---|---|---|---|---|---|---|
| **C01** | **Quick Action Launcher (Findings)**<br>Chairside drawer / sticky bar | `ChartQuickActionLauncher.jsx:260-310`<br>`PatientDetails.jsx:465-495` | `Native Finding` (Native ON)<br>or `Tooth Condition` (`updateToothStatus`, Native OFF) | None (Always visible when chart open) | **`keep`** [PROPOSAL] | Primary chairside rapid-entry path for caries, fracture, and pain observations. |
| **C02** | **Quick Action Launcher (Procedures)**<br>Chairside drawer / sticky bar | `ChartQuickActionLauncher.jsx:315-420`<br>`PatientDetails.jsx:475-535`<br>`QuickTreatmentSheet.jsx` | `Native Procedure` (Native ON)<br>or `QuickTreatmentSheet` (Flow B, Native OFF & non-canonical fallback) | None (Always visible when chart open) | **`keep`** [PROPOSAL] | Displays clinic's real procedures, prices & chart swatches (U1, U4C). Feeds `buildTreatmentPrefill` -> `QuickTreatmentSheet` (escalating to `TreatmentModal` on "More details" or errors per U4D). |
| **C03** | **Plan Item "Perform now" Button**<br>Plan phase items list | `PlanItemRow.jsx:80-92`<br>`PatientDetails.jsx:538-570` | `TreatmentModal` with `clinical_work_item_id` (U2) | `!clinical_vnext_native_writes` & `plan.status === 'accepted'` | **`keep`** [PROPOSAL] | Enables executing planned care items directly through legacy billing and linking them to `ClinicalWorkItem`. |
| **C04** | **Plan Chart Overlay Toggle**<br>Plan & Phase card header | `PlanCard.jsx:110-125`<br>`PlanPhaseCard.jsx:135-155`<br>`DentalChartSVG.jsx:355-375` | Read-only UI state (`usePatientPlanOverlay`) | `clinical_treatment_plans` | **`keep`** [PROPOSAL] | Highlights planned teeth, phase colors, and completion status (`✓` / `●`) on odontogram (U2.4). |
| **C05** | **Plan Comparison Modal**<br>Plans card header button | `TreatmentPlansCard.jsx:382-392`<br>`PlanComparisonModal.jsx:1-240` | Read-only UI state / Plan acceptance | `clinical_treatment_plans` (>=2 plans) | **`keep`** [PROPOSAL] | Side-by-side alternative plan comparison and direct acceptance. |
| **C06** | **Chairside Selection Bar "Record Treatment"**<br>Floating chart bar | `ChairsideSelectionBar.jsx:50-70`<br>`usePatientChartSelection.js:203-220` | `TreatmentModal` with selected tooth & surfaces | None (Triggered by tooth selection) | **`keep`** [PROPOSAL] | Explicit path to open modal for selected tooth/surfaces. |
| **C07** | **Tooth Select Modal (Tooth Picker)**<br>Modal shortcut ('t' hotkey) | `ToothSelectModal.jsx:1-85`<br>`usePatientChartSelection.js:65-82` | `TreatmentModal` with selected tooth | None | **`hide`** [PROPOSAL] | Duplicative once odontogram interaction and quick launcher are intuitive; proposal to hide or keep as accessible fallback. |
| **C08** | **New Treatment Button ("+ New Treatment")**<br>Treatments tab header | `usePatientRecordActions.js:93-100`<br>`PatientDetails.jsx:430-440` | `TreatmentModal` (unlinked manual create) | None | **`keep`** [PROPOSAL] | Required for recording non-chart treatments, general consultations, or administrative entries. |
| **C09** | **Treatment Row Edit Action**<br>Treatments table action menu | `usePatientRecordActions.js:133-140`<br>`PatientDetails.jsx:430-440` | `TreatmentModal` (edit mode) | None | **`keep`** [PROPOSAL] | Editing performed treatment notes, complications, or discounts. |
| **C10** | **Treatments Table Empty State CTA**<br>Treatments tab empty container | `PatientDetails.jsx:980-985` | `TreatmentModal` (unlinked manual create) | None | **`keep`** [PROPOSAL] | Onboarding CTA when patient has zero treatments recorded. |
| **C11** | **Legacy Tooth Condition Segmented Control**<br>Inside TreatmentModal | `TreatmentModal.jsx:483-515` | `updateToothStatus` (`Decayed`, `Filled`, etc.) | None | **`hide`** [PROPOSAL] | Redundant with clinical findings recorded through quick launcher; proposal to deprecate in Cutover. |
| **C12** | **1-Tap Lab Handoff Sheet**<br>Inspector / Session Finish | `LabHandoffSheet.jsx:27-120`<br>`ClinicalChartInspector.jsx:120-145` | `LabOrder` linked to work item (`S28`) | None | **`keep`** [PROPOSAL] | Dispatches lab orders without duplicate synthetic treatments (R06). |
| **C13** | **Care Session Start / Finish Bar**<br>Chairside session header | `CareSessionActiveBanner.jsx:1-120`<br>`FinishCareSessionSheet.jsx:1-180` | `CareSession` & `CareSessionStep` | `clinical_vnext_shadow` / `primary` | **`keep`** [PROPOSAL] | Multi-step clinical procedure tracking and handoff. |

---

## 2. `QuickTreatmentSheet` & `TreatmentModal` Entry-Point Architecture

There are **7 verified entry points** that record treatments in the frontend. All chart-driven entry points (1–4) pass through the centralized `buildTreatmentPrefill` helper (U3.2), and both `QuickTreatmentSheet` and `TreatmentModal` construct their request body via the shared `buildTreatmentPayload` helper (U4D):

- **Quick Action Launcher (Flow B)** opens the compact **`QuickTreatmentSheet`** (`DentixBottomSheet`), which escalates to `TreatmentModal` when the clinician taps **More details** or when a stock shortage, open-session conflict, or `CLINICAL_LINK_*` validation error requires advanced handling.
- **Plan Item "Perform now" (U2.3)**, **Chairside Selection ("Advanced Entry")**, **Tooth Picker**, **Header "+ New Treatment"**, and **Treatment Edit** open **`TreatmentModal`** directly.

```
                                    ┌────────────────────────┐
                                    │  Quick Action Launcher │ (Flow B -> QuickTreatmentSheet)
                                    └───────────┬────────────┘
                                                │ (More details / error escalation)
                                    ┌───────────▼────────────┐
                                    │ Plan Item "Perform now"│ (U2.3)
                                    └───────────┬────────────┘
                                                │
                                    ┌───────────▼────────────┐
                                    │ Chairside Selection Bar│
                                    └───────────┬────────────┘
                                                │
                                    ┌───────────▼────────────┐
                                    │ Tooth Picker ('t' key) │
                                    └───────────┬────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │     buildTreatmentPrefill()     │ (U3.2)
                               └────────────────┬────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │  QuickTreatmentSheet (Flow B)   │
                               │               │ (escalation)    │
                               │               ▼                 │
                               │         TreatmentModal          │
                               │  (Context Header Banner U3.3)   │
                               └─────────────────────────────────┘
                                                ▲
                                                │
                      ┌─────────────────────────┴────────────────────────┐
                      │                                                  │
          ┌───────────┴────────────┐                        ┌────────────┴───────────┐
          │   Header / Action Menu │                        │  Treatments Empty CTA  │
          │  "+ New Treatment"     │                        │  "+ Add Treatment"     │
          │ (usePatientRecordActions)                       │  (PatientDetails:982)  │
          └────────────────────────┘                        └────────────────────────┘
```

### Entry-Point Matrix

| Entry Point | Trigger Action | Location (`file:line`) | Source Label (`prefill_source`) | Target UI Surface | Prefill Payload Built | Passes U1.3 / U3.2 Resolver? |
|---|---|---|---|---|---|:---:|
| **1. Quick Launcher** | Click clinic procedure in launcher drawer | `PatientDetails.jsx:520-535` | `'quick_launcher'` | **`QuickTreatmentSheet`** (escalates to `TreatmentModal`) | `tooth_number` (Palmer), `procedure` (name), `surface`, `surfaces`, `target_kind`, `default_price_list_id` | **YES** (`buildTreatmentPrefill` + `buildTreatmentPayload`) |
| **2. Plan Item Perform** | Click "Perform now" on accepted plan item | `PatientDetails.jsx:538-570` | `'plan_item'` | `TreatmentModal` | `tooth_number` (Palmer), `procedure` (matched name), `clinical_work_item_id`, `plan_title`, `plan_id`, `work_item_code`, `surface`, `surfaces` | **YES** (`buildTreatmentPrefill` + `buildTreatmentPayload`) |
| **3. Chairside Selection** | Click "Record Treatment" on selection bar | `usePatientChartSelection.js:203-220` | `'chart_selection'` | `TreatmentModal` | `tooth_number` (Palmer), `surface`, `surfaces`, `target_kind`, `default_price_list_id` | **YES** (`buildTreatmentPrefill` + `buildTreatmentPayload`) |
| **4. Tooth Picker** | Select tooth in modal ('t' hotkey) | `usePatientChartSelection.js:65-82` | `'tooth_picker'` | `TreatmentModal` | `tooth_number` (Palmer), `target_kind: 'tooth'`, `default_price_list_id` | **YES** (`buildTreatmentPrefill` + `buildTreatmentPayload`) |
| **5. Header "+ New Treatment"** | Click "+ New Treatment" in treatments header | `usePatientRecordActions.js:93-100` | `'manual'` | `TreatmentModal` | Fresh unlinked treatment skeleton from `getInitialTreatment()` | No (Unlinked manual entry) |
| **6. Treatment Row Edit** | Click "Edit" on treatment row in history table | `usePatientRecordActions.js:133-140` | `null` (Edit mode) | `TreatmentModal` | Existing treatment database row (`editingTreatmentId` set) | No (Edit existing) |
| **7. Table Empty State CTA** | Click "+ Add First Treatment" in empty list | `PatientDetails.jsx:980-985` | `'manual'` | `TreatmentModal` | Fresh unlinked treatment skeleton from `getInitialTreatment()` | No (Unlinked manual entry) |

---

## 3. Query Invalidation Rule for Future Slices (S30–S36)

To prevent cache drift and UI desynchronization, any mutation that alters clinical state MUST consume the centralized helper:

```javascript
import { invalidatePatientClinicalQueries } from '@/features/patients/utils/invalidatePatientClinicalQueries';
```

### Invalidation Scope
Invoking `invalidatePatientClinicalQueries(queryClient, patientId)` systematically purges:
1. `queryKeys.patientClinicalWorkspace(patientId)` — odontogram projection, warnings, domain coverages.
2. `queryKeys.patientClinicalPlans(patientId)` — treatment plan list, phases, item progress counters.
3. `queryKeys.patientTreatments(patientId)` — performed treatment ledger rows.
4. `queryKeys.patientTeeth(patientId)` — tooth-level condition and odontogram statuses.
5. `queryKeys.activeCareSession(patientId)` & `queryKeys.resumableCareSession(patientId)` — active chairside workflows.
6. `['plan-overlay', patientId]` — visual chart overlay caches.

### Mandate for Slices S30–S36:
- **S30 (Material Consumption / BOM Deduct-at-Use):** Must invoke upon material consumption record.
- **S31 (Migration Invariance / Endo Scenarios):** Must invoke upon canal step recording.
- **S32 (Clinical Charges & Ledger Invariance):** Must invoke upon work completion and charge generation.
- **S33–S34 (Billing Parity):** Must invoke upon invoice and ledger allocation sync.

---

## 4. Known Architectural Limitations & Boundaries

1. **Custom Procedures Without Canonical Mapping (Billing-Only):**
   - Procedures created in clinic settings whose names do not exist in `LEGACY_PROCEDURE_ALLOWLIST` return `canonical_code: null` (U1.1).
   - In Quick Action Launcher, these display a **"Billing Only"** tag.
   - Recording them creates a normal legacy `Treatment` and bills correctly, but they do NOT sync to `ClinicalWorkItem` and cannot satisfy canonical plan items (R01/PD02).

2. **Multi-Tooth Plan Items:**
   - Plan items spanning multiple teeth (e.g. `PROS_BRIDGE`, `PROS_DENTURE`) do NOT show the "Perform now" button in U2.3.
   - They require manual completion or multi-tooth handling in a subsequent release.

3. **Pre-Deployment Historical Treatments:**
   - Treatments recorded before U2 deployment were created as standalone work items.
   - They are NOT retroactively linked to existing plan items (non-goal U2.6).

---

## 5. Architectural Recommendations Submitted for Eslam's Decision

1. **Legacy Tooth Condition Buttons in TreatmentModal (`selectedToothCondition`):**
   - *Proposal:* Hide in Cutover. Finding recording in `ChartQuickActionLauncher` provides structured multi-surface clinical semantics with superior audit trails.
2. **Tooth Picker Dialog (`ToothSelectModal`):**
   - *Proposal:* Keep strictly as an accessible keyboard fallback ('t' key), but deprecate prominent visual triggers in favor of direct chart clicks.
3. **Chart Click on Empty Tooth:**
   - *Proposal:* Maintain existing behavior opening `TreatmentModal` with prefilled tooth number and context header banner (`prefill_source: 'chart_selection'`).
