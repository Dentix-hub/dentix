<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Odontogram & Clinical VNext — Execution Cards for Gemini Flash

**Authority Hierarchy:** `AGENTS.md` > `PROJECT_STANDARDS.md` & `docs/engineering/DEVELOPMENT_WORKFLOW.md` > `docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md` & `docs/product/ODONTOGRAM_TRACEABILITY_MATRIX.md` > `docs/product/ODONTOGRAM_EXECUTION_QUEUE.md` > this document (`docs/product/ODONTOGRAM_EXECUTION_CARDS.md`).  
**Classification:** `ACTIVE`  
**Target Executor:** Gemini Flash (one self-contained card per turn/branch).  
**Global Rules for Every Card:**
- **Shell / Env (Windows PowerShell):** Python via `.\.venv\Scripts\python.exe`; Frontend via `npm.cmd --prefix frontend`; GitHub CLI via `gh`.
- **One PR -> `staging`, then STOP.** Never merge, never promote to `main`, never push directly to `staging`/`main`, never edit `.github/workflows/*`, never poll CI in a loop.
- **Read the real code first:** Execute Step 0 of your card against `origin/staging`. If the real code contradicts the card, **STOP and report** before writing code.
- **Test Integrity:** Never weaken, skip, or delete an existing assertion to make a failing test pass. Report real exit codes for every verification command.

---

## PART I — FULL SELF-CONTAINED EXECUTION CARDS (`S00`, `S02`–`S09`)

*(Note: **S01** is Eslam's Staging Ops Runbook — see `docs/product/ODONTOGRAM_EXECUTION_QUEUE.md:Section 3.3`. It is not an agent code slice).*

---

### CARD S00 — Reclassify 5 Approved Drop Items in Traceability Matrix & Test
- **Branch:** `chore/odontogram-drop-reclassifications`
- **Delivery:** One PR -> `staging`, then STOP. **DO NOT MERGE.**
- **Rule 0:** Read the real files on `origin/staging` first (`docs/product/ODONTOGRAM_TRACEABILITY_MATRIX.md` and `backend/tests/test_odontogram_traceability.py`). If they contradict this card, **STOP and report**.
- **Matrix Items Closed (5):**
  - `G8-M12`: Add undo stack
  - `G10-M06`: Add repeatable-step support
  - `G10-M16`: Add template deviation support
  - `G11-M03`: Add auto-suggestion from workflow template
  - `G12-M14`: Support bridge semantics

#### DECISIONS (Approved by Eslam)
1. Drop `G8-M12`, `G10-M06`, `G10-M16`, `G11-M03`, and `G12-M14` from active clinic runtime implementation scope while preserving 100% lossless 327-item accounting in `docs/product/ODONTOGRAM_TRACEABILITY_MATRIX.md` and `backend/tests/test_odontogram_traceability.py`.
2. Reclassify `G8-M12`, `G10-M06`, and `G11-M03` to `HISTORICAL_EXECUTION_MECHANIC` -> destination `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md`.
3. Reclassify `G10-M16` and `G12-M14` to `ARCHITECTURE_CONSTRAINT` -> destination `PROJECT_STANDARDS.md`.
4. Do **NOT** delete any rows from `docs/product/ODONTOGRAM_TRACEABILITY_MATRIX.md` (`EXPECTED_COUNTS` total = 327 must remain intact), and do **NOT** edit `docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md` (because `test_product_spec_phases_exact_positive_equality` at `backend/tests/test_odontogram_traceability.py:461-510` enforces exact phase scope string parity with the historical source).

#### SCOPE
1. In `docs/product/ODONTOGRAM_TRACEABILITY_MATRIX.md`:
   - Line `274` (`G8-M12`): Change classification column from `` `ACTIVE_PRODUCT_REQUIREMENT` `` to `` `HISTORICAL_EXECUTION_MECHANIC` `` and destination column from `` `docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md` `` to `` `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md` ``.
   - Line `297` (`G10-M06`): Change classification to `` `HISTORICAL_EXECUTION_MECHANIC` `` and destination to `` `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md` ``.
   - Line `307` (`G10-M16`): Change classification to `` `ARCHITECTURE_CONSTRAINT` `` and destination to `` `PROJECT_STANDARDS.md` ``.
   - Line `314` (`G11-M03`): Change classification to `` `HISTORICAL_EXECUTION_MECHANIC` `` and destination to `` `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md` ``.
   - Line `337` (`G12-M14`): Change classification to `` `ARCHITECTURE_CONSTRAINT` `` and destination to `` `PROJECT_STANDARDS.md` ``.
2. In `backend/tests/test_odontogram_traceability.py`:
   - Add `"G8-M12"`, `"G10-M06"`, `"G11-M03"` to `HISTORICAL_IDS` (`lines 78-81`).
   - Add `"G10-M16"`, `"G12-M14"` to `ARCHITECTURE_IDS` (`lines 83-87`).
3. In `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`:
   - Ensure the `"Dropped Scope"` section lists the 5 dropped IDs (`G8-M12`, `G10-M06`, `G10-M16`, `G11-M03`, `G12-M14`), their new classification (`HISTORICAL_EXECUTION_MECHANIC` or `ARCHITECTURE_CONSTRAINT`), and states that `docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md` still enumerates them because `test_product_spec_phases_exact_positive_equality` forbids editing it.

#### EXCLUDE
- Any edit to `docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md`, `PROJECT_STANDARDS.md`, or `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md`.
- Any product code or database migration.

#### FILES LIKELY TOUCHED
- `docs/product/ODONTOGRAM_TRACEABILITY_MATRIX.md`
- `backend/tests/test_odontogram_traceability.py`
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`

#### STEP 0 — ASSUMPTIONS TO VERIFY BEFORE EDITING
- Inspect `backend/tests/test_odontogram_traceability.py:70-115` and `432-511`. Confirm `get_expected_classification()` maps `HISTORICAL_IDS` -> `HISTORICAL_EXECUTION_MECHANIC` (`docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md`) and `ARCHITECTURE_IDS` -> `ARCHITECTURE_CONSTRAINT` (`PROJECT_STANDARDS.md`), and confirm no other test function hardcodes the old classifications for those 5 IDs.

#### TESTS & VERIFICATION COMMANDS (Real Exit Codes Required)
- `.\.venv\Scripts\python.exe -m pytest backend/tests/test_odontogram_traceability.py backend/tests/test_check_agent_authority.py backend/tests/test_ci_classifier.py -q`
- `.\.venv\Scripts\python.exe .github/scripts/check_agent_authority.py`
- `.\.venv\Scripts\python.exe -m ruff check --config ruff.toml backend/tests/test_odontogram_traceability.py`

#### PR BODY REQUIREMENTS
- **Top Line:** `RBAC touches: NONE | Native-write flag status: N/A (docs/test reclassification only) | Migrations: NONE`
- **How to test on staging (<= 15 min):** Not visible in UI (traceability matrix and test manifest reclassification only; verified via `pytest backend/tests/test_odontogram_traceability.py`).

#### STOP CONDITIONS
- Stop if `test_odontogram_traceability.py` fails on any other assertion or if total matrix item count deviates from `327`.

#### QUEUE STATE BLOCK (Append at End of Final Response)
```text
=== QUEUE STATE ===
Slice: S00 - Reclassify 5 Approved Drop Items
Status: DONE | PARTIAL | BLOCKED
PR: <URL>
Next Slice: S01 (Eslam Staging Ops Runbook), then S02
===================
```

---

### CARD S02 — Early Read-Only Clinical Drift & Error Observer (`G16-M04`, `G16-M05`)
- **Branch:** `feat/clinical-drift-observer`
- **Delivery:** One PR -> `staging`, then STOP. **DO NOT MERGE.**
- **Rule 0:** Read the real code on `origin/staging` first. If it contradicts this card, **STOP and report**.
- **Matrix Items Closed (2):**
  - `G16-M04`: Monitor errors
  - `G16-M05`: Monitor parity

#### DECISIONS
1. Build a strictly **read-only**, super-admin-gated clinical drift and mapping-error observer service (`ClinicalDriftObserverService`) and endpoint (`GET /api/v1/admin/clinical-drift/{tenant_id}`) so Eslam can monitor legacy-vs-native parity during the `SHADOW` soak starting right after `S01`.
2. **Zero database writes:** The observer must never insert, update, or delete any row in any table.
3. Reuse `ClinicalWorkspaceService` (`backend/services/clinical_workspace_service.py`) and `map_legacy_clinical_batch` (`backend/clinical/legacy_mapping.py:1391`) to compare, per patient in a tenant:
   - Legacy `models.Treatment` (non-deleted, valid FDI tooth) count vs native `models.ClinicalWorkItem` (`kind='procedure'`, non-cancelled) count.
   - Legacy `models.ToothStatus` conditions vs native tooth lifecycle / finding projections.
   - Mapping issues / ambiguities returned by `map_legacy_clinical_batch` (`G16-M04` error monitoring).
4. Auth/RBAC: Reuse `get_super_admin` (`Permission.SYSTEM_CONFIG` + `Role.SUPER_ADMIN` or tenantless `Role.ADMIN`) from `backend/routers/admin_features.py:19-27`. Non-super-admin users receive `403`. Missing tenant returns `404`.

#### SCOPE
- **Schemas (`backend/schemas/clinical_workspace.py` or `backend/schemas/system.py`):** `PatientClinicalDriftItem`, `TenantClinicalDriftReport` (`tenant_id`, `patients_scanned`, `patients_with_drift`, `legacy_procedure_count`, `native_procedure_count`, `missing_in_native_treatment_ids`, `unmapped_issue_count`, `patient_drifts`).
- **Service (`backend/services/clinical_drift_observer_service.py` (new)):** `ClinicalDriftObserverService.compute_tenant_drift(tenant_id: int, limit_patients: int = 500, after_patient_id: int = 0) -> TenantClinicalDriftReport`. Sets `set_current_tenant_id(tenant_id)` in a `try/finally` with `clear_tenant_context(token)` (`backend/core/tenancy.py`).
- **Router (`backend/routers/admin_features.py` or `backend/routers/admin_system.py`):** `GET /admin/clinical-drift/{tenant_id}` (mounted under `/api/v1`).
- **Status Doc:** Update `G16` row in `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md` with `G16-M04`/`G16-M05` evidence.

#### EXCLUDE
- Finance/billing parity (`G14-M06..M08` — scheduled in `S34` after `clinical_charges`).
- Any mutation or auto-remediation of `clinical_work_items` or `treatments`.
- Any frontend UI changes or database migrations.

#### FILES LIKELY TOUCHED
- `backend/services/clinical_drift_observer_service.py` (new)
- `backend/schemas/clinical_workspace.py` (or `backend/schemas/system.py` + `backend/schemas/__init__.py`)
- `backend/routers/admin_features.py`
- `backend/tests/services/test_clinical_drift_observer.py` (new)
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`

#### STEP 0 — ASSUMPTIONS TO VERIFY
- Verify `get_super_admin` in `backend/routers/admin_features.py:19-27`.
- Verify `TreatmentService.find_linked_clinical_work_item` and `map_treatment_to_clinical` in `backend/services/treatment_service.py:523-536`.
- Verify `set_current_tenant_id` / `clear_tenant_context` in `backend/core/tenancy.py`.

#### TESTS REQUIRED
- Super-admin `200` on backfilled tenant -> `patients_with_drift == 0`.
- Tenant with un-backfilled treatment -> accurately reports `missing_in_native_treatment_ids` and `patients_with_drift == 1`.
- Tenant with unmapped procedure / invalid FDI -> increments `unmapped_issue_count` (`G16-M04`).
- Tenant isolation: scanning Tenant 1 never reads or reports Tenant 2 patients.
- Non-super-admin (`Role.DOCTOR`, `Role.ADMIN` with `tenant_id=1`) -> `403`.
- Non-existent `tenant_id` -> `404`.
- Zero-mutation proof: count of `Treatment`, `ClinicalWorkItem`, `ClinicalEvent`, `Payment` before == after.

#### VERIFICATION COMMANDS (Real Exit Codes Required)
- `.\.venv\Scripts\python.exe -m pytest backend/tests/services/test_clinical_drift_observer.py -q` (new)
- `.\.venv\Scripts\python.exe -m ruff check --config ruff.toml backend`
- `.\.venv\Scripts\python.exe .github/scripts/check_agent_authority.py`

#### PR BODY REQUIREMENTS
- **Top Line:** `RBAC touches: Super-admin only (get_super_admin / Permission.SYSTEM_CONFIG) on GET /api/v1/admin/clinical-drift/{tenant_id} | Native-write flag status: N/A (read-only) | Migrations: NONE`
- **How to test on staging (<= 15 min):**
  1. Authenticate as super_admin and call `GET /api/v1/admin/clinical-drift/1`.
  2. Confirm `patients_with_drift: 0` for the tenant backfilled in `S01`, and `patients_with_drift > 0` for an un-backfilled tenant.
  3. Confirm not visible in clinic UI and zero DB writes.

#### STOP CONDITIONS
- Stop if any migration is needed or if any existing table is mutated.

#### QUEUE STATE BLOCK
```text
=== QUEUE STATE ===
Slice: S02 - Early Read-Only Clinical Drift & Error Observer (G16-M04, G16-M05)
Status: DONE | PARTIAL | BLOCKED
PR: <URL>
Next Slice: S03
===================
```

---

### CARD S03 — Backfill Tooth-Status Events, Legacy Care Sessions & Invariance Assertions
- **Branch:** `feat/clinical-backfill-tooth-sessions`
- **Delivery:** One PR -> `staging`, then STOP. **DO NOT MERGE.**
- **Rule 0:** Read `scripts/backfill_clinical_work_items.py`, `backend/clinical/legacy_mapping.py`, and `backend/tests/services/test_clinical_backfill.py` on `origin/staging` first. If they contradict this card, **STOP and report**.
- **Matrix Items Closed (4):**
  - `G4-M06`: Backfill tooth-status events
  - `G4-M07`: Backfill legacy care sessions
  - `G4-M12`: Verify inventory unchanged
  - `G4-M13`: Verify payments unchanged

#### DECISIONS
1. Extend `scripts/backfill_clinical_work_items.py` (`backfill_tenant` and `TenantBackfillReport`) so that, in addition to `models.Treatment`, it deterministically backfills:
   - **`G4-M06` (`models.ToothStatus`):** Using `map_legacy_tooth_status` (`backend/clinical/legacy_mapping.py:872`), persist native `ClinicalEvent` + `ClinicalEventTarget` (and `ClinicalWorkItem` when `map_legacy_tooth_status` yields a finding draft such as `Decayed` -> `CARIES`) with `payload["provenance"] = "backfill"` and `payload["source"] = "legacy_tooth_status"`, `payload["tooth_status_id"] = ts.id`. Skip idempotently if an event with `payload["tooth_status_id"] == ts.id` already exists for that tenant/patient.
   - **`G4-M07` (`models.TreatmentSession`):** Using `map_legacy_treatment_session` (`backend/clinical/legacy_mapping.py:995`), persist `models.CareSession` (`status="completed"`, `notes` preserving free-text session notes + `[LEGACY_TREATMENT_SESSION:<id>]` provenance marker or structured lookup) for non-deleted parent treatments. Skip idempotently if already synced.
2. Dry-run (`apply=False`, the default) must report `tooth_statuses_scanned`, `tooth_statuses_created`, `tooth_statuses_already_synced`, `sessions_scanned`, `sessions_created`, `sessions_already_synced` without writing a single row.
3. Explicitly prove `G4-M12` (inventory tables `StockItem`, `StockMovement`, `TreatmentMaterialUsage` unchanged) and `G4-M13` (`Payment` rows and sums unchanged) in `backend/tests/services/test_clinical_backfill.py`.

#### SCOPE
- `scripts/backfill_clinical_work_items.py`: Extend `TenantBackfillReport` fields (backward-compatible with existing fields) and `backfill_tenant()` to process `ToothStatus` and `TreatmentSession` in batches.
- `backend/tests/services/test_clinical_backfill.py`: Add tests for `G4-M06`, `G4-M07`, idempotency on re-run, tenant isolation, dry-run zero-writes, `G4-M12` inventory invariance, and `G4-M13` payment invariance.
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`: Update `G4` row with accurate test count and `G4-M06`/`M07`/`M12`/`M13` evidence.

#### EXCLUDE
- `G4-M08` (lab relationships — requires `lab_orders.work_item_id` migration in `S27`).
- `G4-M09` (attachment links — scheduled in `S23` with `G15-M09`).
- Any schema migration or router changes.

#### FILES LIKELY TOUCHED
- `scripts/backfill_clinical_work_items.py`
- `backend/tests/services/test_clinical_backfill.py`
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`

#### STEP 0 — ASSUMPTIONS TO VERIFY
- Inspect `map_legacy_tooth_status` (`backend/clinical/legacy_mapping.py:872-994`) and `map_legacy_treatment_session` (`backend/clinical/legacy_mapping.py:995-1108`).
- Inspect `models.TreatmentSession` in `backend/models/clinical.py` and `models.CareSession` in `backend/models/clinical_core.py:383-431`.

#### TESTS REQUIRED
- Dry-run reports accurate would-create counts for treatments, tooth statuses, and sessions with `0` DB writes.
- Apply mode creates expected `ClinicalWorkItem`/`ClinicalEvent`/`CareSession` rows with backfill provenance.
- Re-running `--apply` creates `0` duplicates (`already_synced` increments).
- Tenant 1 backfill leaves Tenant 2 untouched.
- Inventory (`StockItem.quantity`, `StockMovement` count, `TreatmentMaterialUsage` count) and `Payment` (count and `SUM(amount)`) are 100% identical before and after `--apply`.

#### VERIFICATION COMMANDS (Real Exit Codes Required)
- `.\.venv\Scripts\python.exe -m pytest backend/tests/services/test_clinical_backfill.py -q`
- `.\.venv\Scripts\python.exe -m ruff check --config ruff.toml backend scripts/backfill_clinical_work_items.py`
- `.\.venv\Scripts\python.exe .github/scripts/check_agent_authority.py`

#### PR BODY REQUIREMENTS
- **Top Line:** `RBAC touches: NONE (CLI script only) | Native-write flag status: CLI gated by explicit --apply | Migrations: NONE`
- **How to test on staging (<= 15 min):**
  1. Run `python scripts/backfill_clinical_work_items.py --tenant-id 1 --json` (dry-run).
  2. Run `python scripts/backfill_clinical_work_items.py --tenant-id 1 --apply --json` twice; confirm second run reports `0` created across treatments, tooth statuses, and sessions.
  3. Confirm not visible in UI (unless tenant is switched to `VNEXT_PRIMARY`).

#### STOP CONDITIONS
- Stop if `models.CareSession` or `models.ClinicalEvent` check constraints reject mapped values; report exact constraint name.

#### QUEUE STATE BLOCK
```text
=== QUEUE STATE ===
Slice: S03 - Backfill Tooth-Status Events, Legacy Care Sessions & Invariance Assertions
Status: DONE | PARTIAL | BLOCKED
PR: <URL>
Next Slice: S04
===================
```

---

### CARD S04 — Command Service, Work Item Create/Update APIs & Permission Enforcement
- **Branch:** `feat/clinical-work-item-command-api`
- **Delivery:** One PR -> `staging`, then STOP. **DO NOT MERGE.**
- **Rule 0:** Read `backend/models/clinical_core.py`, `backend/clinical/catalog.py`, `backend/services/treatment_plan_service.py`, and `backend/routers/patients.py` on `origin/staging` first. If they contradict this card, **STOP and report**.
- **Matrix Items Closed (4):**
  - `G7-M01`: Create command service
  - `G7-M02`: Add work item create API
  - `G7-M03`: Add work item update API
  - `G7-M12`: Add permission enforcement

#### DECISIONS
1. Create `ClinicalCommandService` in `backend/services/clinical_command_service.py` (new) as the single domain service for native `ClinicalWorkItem` and `ClinicalEvent` mutations.
2. **Fail-Closed Native-Write Gate (`PD02` / `R01`):** Every mutation method in `ClinicalCommandService` MUST call `await self.ensure_native_writes_enabled()` first, which checks `await FeatureFlagService.is_feature_enabled(self.db, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, self.tenant_id)` (`"clinical_vnext_native_writes"`, `backend/services/clinical_workspace_service.py:44`). When disabled, raise `HTTPException(status_code=404, detail="Clinical native writes are disabled")`.
3. **Tenant & Doctor Visibility (`R02`):** Every method must verify patient access via `await ensure_patient_visible(self.db, user, patient_id)` (`backend/services/patient_access_service.py:11-21`, using the `_get_active_current_user` reload pattern from `backend/services/treatment_plan_service.py:63-75`). Cross-tenant or mismatched `patient_id`/`work_item_id` returns `404`.
4. **Canonical Validation & Status Rules:**
   - `kind == "finding"` -> `code` must be in `CANONICAL_FINDING_CODES` (`backend/clinical/catalog.py:59`), otherwise `422`.
   - `kind == "procedure"` -> `code` must be in `CANONICAL_PROCEDURE_CODES` (`backend/clinical/catalog.py:88`), otherwise `422`.
   - Validate `status` against `CANONICAL_TREATMENT_LIFECYCLE_CODES` imported from `backend/clinical/catalog.py:97-105` (`("proposed", "planned", "active", "completed", "cancelled")` — never a hardcoded set), otherwise `422`.
   - `PATCH` may **not** set `superseded` or `entered_in_error` (`422`; only `/correct` in `S06` can set those statuses).
   - `completed` and `cancelled` are **terminal**: any status change away from `completed` or `cancelled` on `PATCH` returns `409 Conflict`.
   - Targets (`ClinicalWorkItemTarget`) must validate `tooth_key in FDI_TOOTH_KEYS`, `target_kind in {"tooth", "surface", "root", "canal"}`, and shape rules matching `TARGET_SHAPE_CONSTRAINT` (`ck_cwit_shape` / `ck_cet_shape` in `backend/models/clinical_core.py:77-84,172,366`) before DB flush (returning `422` on invalid shape).
5. Creating or updating a `ClinicalWorkItem` atomically appends a corresponding `ClinicalEvent` (`event_type = f"{kind}_recorded"` on create, `f"{kind}_updated"` on update) + `ClinicalEventTarget` rows in the same transaction (`occurred_at = datetime.now(timezone.utc)`).
6. **RBAC (`G7-M12`):**
   - `POST /api/v1/patients/{patient_id}/clinical-work-items`: requires `Permission.CLINICAL_WRITE` or `Permission.TREATMENT_PLAN_WRITE` (`require_permission(Permission.CLINICAL_WRITE, Permission.TREATMENT_PLAN_WRITE)`).
   - `PATCH /api/v1/patients/{patient_id}/clinical-work-items/{work_item_id}`: requires `Permission.CLINICAL_WRITE` or `Permission.TREATMENT_PLAN_WRITE`.
   - `GET /api/v1/patients/{patient_id}/clinical-work-items`: requires `Permission.CLINICAL_READ` (gated by `clinical_vnext_shadow` OR `clinical_vnext_primary` OR `clinical_vnext_native_writes`).

#### SCOPE
- **Schemas (`backend/schemas/clinical_commands.py` (new) + export in `backend/schemas/__init__.py`):** `ClinicalTargetInput`, `ClinicalWorkItemCreate`, `ClinicalWorkItemUpdate` (optional `status`, `notes`, `targets`, `expected_version_id`), `ClinicalWorkItemRead`.
- **Service (`backend/services/clinical_command_service.py` (new)):** `create_work_item`, `update_work_item`, `list_work_items`.
- **Router (`backend/routers/clinical_commands.py` (new), included in `backend/main.py` with `prefix=API_V1_STR` and unversioned fallback matching `treatment_plans.router` at `backend/main.py:476-477`):**
  - `POST /patients/{patient_id}/clinical-work-items`
  - `GET /patients/{patient_id}/clinical-work-items`
  - `PATCH /patients/{patient_id}/clinical-work-items/{work_item_id}`
- **Status Doc:** Update `G7` row in `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md` with `G7-M01`, `M02`, `M03`, `M12` evidence.

#### EXCLUDE
- Bulk finding/procedure endpoints (`S05`), work-item correction/tooth detail/history endpoints (`S06`), idempotency keys (`S07`).
- Any mutation of legacy `models.Treatment`, `models.ToothStatus`, `models.Payment`, or `models.StockMovement`.
- Any schema migration or frontend UI changes.

#### FILES LIKELY TOUCHED
- `backend/schemas/clinical_commands.py` (new)
- `backend/schemas/__init__.py`
- `backend/services/clinical_command_service.py` (new)
- `backend/routers/clinical_commands.py` (new)
- `backend/main.py`
- `backend/tests/services/test_clinical_command_service.py` (new)
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`

#### STEP 0 — ASSUMPTIONS TO VERIFY
- Verify `CANONICAL_FINDING_CODES`, `CANONICAL_PROCEDURE_CODES`, and `CANONICAL_TREATMENT_LIFECYCLE_CODES` in `backend/clinical/catalog.py:53-105`.
- Verify `TARGET_SHAPE_CONSTRAINT` (`ck_cwit_shape`, `ck_cet_shape`) in `backend/models/clinical_core.py:77-84,172,366` and `ClinicalWorkItem` / `ClinicalEvent` columns at `lines 97-380`.
- Verify `require_permission` multi-permission behavior in `backend/core/permissions.py:229-262`.

#### TESTS REQUIRED
- Flag OFF (`clinical_vnext_native_writes` disabled) -> `POST` and `PATCH` return `404`.
- Flag ON -> `POST` creates `ClinicalWorkItem`, `ClinicalWorkItemTarget`, `ClinicalEvent`, `ClinicalEventTarget` for `tooth`, `surface`, `root`, and `canal` target kinds.
- `PATCH` updates `status` (`proposed -> planned -> active -> completed`), `notes`, `targets`, increments `version_id`, and appends `*_updated` event.
- `PATCH` attempting to set `status="superseded"` or `status="entered_in_error"` -> `422` (only `/correct` can set correction statuses).
- `PATCH` attempting to transition `status` away from terminal `completed` or `cancelled` (e.g. `completed -> active` or `cancelled -> planned`) -> `409 Conflict`.
- Invalid `code`, invalid `status` (e.g. `"in_progress"` or `"existing"`), invalid FDI `tooth_key`, or invalid target shape (e.g. `target_kind='surface'` with `surface_code=None`) -> `422`.
- Cross-tenant `patient_id` or `work_item_id` -> `404`; mismatched `patient_id` for `work_item_id` -> `404`; restricted doctor visibility -> `404`.
- RBAC: `Role.RECEPTIONIST` (`CLINICAL_READ` only) gets `403` on `POST`/`PATCH` and `200` on `GET`.
- Legacy invariance: `Treatment`, `Payment`, `StockMovement` counts are `0` before and after.

#### VERIFICATION COMMANDS (Real Exit Codes Required)
- `.\.venv\Scripts\python.exe -m pytest backend/tests/services/test_clinical_command_service.py -q` (new)
- `.\.venv\Scripts\python.exe -m ruff check --config ruff.toml backend`
- `.\.venv\Scripts\python.exe .github/scripts/check_agent_authority.py`

#### PR BODY REQUIREMENTS
- **Top Line:** `RBAC touches: POST/PATCH /api/v1/patients/{patient_id}/clinical-work-items require CLINICAL_WRITE or TREATMENT_PLAN_WRITE; GET requires CLINICAL_READ | Native-write flag status: Gated by clinical_vnext_native_writes (default OFF -> 404) | Migrations: NONE`
- **How to test on staging (<= 15 min):**
  1. Call `POST /api/v1/patients/1/clinical-work-items` with flag OFF -> confirm `404`.
  2. Enable `clinical_vnext_native_writes` for test tenant `1` via `/api/v1/admin/features/override`.
  3. Call `POST`, `PATCH` (`status="active"`), and `GET /api/v1/patients/1/clinical-work-items` -> confirm `200` and version increment.
  4. Confirm not visible in clinic UI unless tenant is in `VNEXT_PRIMARY`.

#### STOP CONDITIONS
- Stop if any migration is needed or if legacy `treatments` table is touched.

#### QUEUE STATE BLOCK
```text
=== QUEUE STATE ===
Slice: S04 - Command Service, Work Item Create/Update APIs & Permission Enforcement
Status: DONE | PARTIAL | BLOCKED
PR: <URL>
Next Slice: S05
===================
```

---

### CARD S05 — Finding & Procedure Single/Bulk Command APIs (`G7-M04`..`G7-M07`)
- **Branch:** `feat/clinical-findings-procedures-bulk-api`
- **Delivery:** One PR -> `staging`, then STOP. **DO NOT MERGE.**
- **Rule 0:** Read `backend/services/clinical_command_service.py` (new), `backend/routers/treatments.py:103-178`, and `backend/services/clinical_service.py:185-205,343-414` on `origin/staging` first. If they contradict this card, **STOP and report**.
- **Matrix Items Closed (4):**
  - `G7-M04`: Add finding create API
  - `G7-M05`: Add bulk finding API
  - `G7-M06`: Add procedure create API
  - `G7-M07`: Add bulk procedure API

#### DECISIONS
1. Expose dedicated patient-scoped single and multi-tooth bulk endpoints on `backend/routers/clinical_commands.py` (new) delegating to `ClinicalCommandService`:
   - `POST /api/v1/patients/{patient_id}/clinical-findings` (`G7-M04`, requires `Permission.CLINICAL_WRITE`)
   - `POST /api/v1/patients/{patient_id}/clinical-findings/bulk` (`G7-M05`, requires `Permission.CLINICAL_WRITE`)
   - `POST /api/v1/patients/{patient_id}/clinical-procedures` (`G7-M06`, requires `Permission.TREATMENT_PLAN_WRITE` or `Permission.CLINICAL_WRITE`)
   - `POST /api/v1/patients/{patient_id}/clinical-procedures/bulk` (`G7-M07`, requires `Permission.TREATMENT_PLAN_WRITE` or `Permission.CLINICAL_WRITE`)
2. **All-or-Nothing Atomicity:** Bulk endpoints accept `items: List[...]` (1 to 50 items across one or more teeth/surfaces/roots/canals) and execute in a single database transaction. If any item fails validation, zero rows are persisted (`422`).
3. **Native-Write Gate (`PD02` & Settled `D6`):** All **4 new patient-scoped endpoints** require `clinical_vnext_native_writes` enabled for the tenant (default OFF -> `404`). Do **NOT** gate existing `POST /api/v1/treatments/finding` or `POST /api/v1/treatments/symptom` (`backend/routers/treatments.py:120-177`) — they also write legacy `ToothStatus` (`Decayed`/`Fractured`) via `ClinicalService.update_tooth_status` and are the deliberate legacy->shadow sync path; leave their behaviour and permissions unchanged, and **only** replace naive `datetime.utcnow()` with `datetime.now(timezone.utc)` in `backend/services/clinical_service.py:193`.

#### SCOPE
- **Schemas (`backend/schemas/clinical_commands.py` (new)):** `ClinicalFindingCreate`, `ClinicalFindingBulkCreate` (`max_length=50`), `ClinicalProcedureCreate`, `ClinicalProcedureBulkCreate` (`max_length=50`), `ClinicalBulkWorkItemResponse`.
- **Service (`backend/services/clinical_command_service.py` (new)):** `create_finding`, `create_findings_bulk`, `create_procedure`, `create_procedures_bulk`.
- **Router & Legacy Timezone Fix (`backend/routers/clinical_commands.py` (new) & `backend/services/clinical_service.py:193`):** Add the 4 patient-scoped routes and replace naive `datetime.utcnow()` with `datetime.now(timezone.utc)` in `backend/services/clinical_service.py:193`.
- **Status Doc:** Update `G7` row in `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md` with `G7-M04`..`M07` evidence.

#### EXCLUDE
- Work-item correction, tooth detail, or history APIs (`S06`).
- Gating or altering permissions on `POST /api/v1/treatments/finding` or `/symptom`.
- Any mutation of legacy `models.Treatment`, `models.Payment`, or `models.StockMovement` from the 4 new native endpoints.

#### FILES LIKELY TOUCHED
- `backend/schemas/clinical_commands.py` (new)
- `backend/schemas/__init__.py`
- `backend/services/clinical_command_service.py` (new)
- `backend/services/clinical_service.py`
- `backend/routers/clinical_commands.py` (new)
- `backend/tests/services/test_clinical_command_service.py` (new)
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`

#### STEP 0 — ASSUMPTIONS TO VERIFY
- Run `git grep -n "recordToothFinding\|recordToothSymptom\|treatments/finding"` and report all callers (currently only the wrapper exports `recordToothFinding` and `recordToothSymptom` in `frontend/src/api/treatments.js:15-16`, with no component callers). Confirm `backend/services/clinical_service.py:193` is the exact naive `datetime.utcnow()` call.

#### TESTS REQUIRED
- Single and bulk finding creation across 3 teeth (`11`, `16`, `46`) in one request.
- Single and bulk procedure creation across multiple teeth/surfaces.
- Atomic rollback when item #3 of 3 in a bulk request has an invalid FDI tooth key (`99`) -> `422` and `0` rows in DB.
- Flag-off `404` on the 4 new patient-scoped routes; cross-tenant `404`, restricted doctor `404`, receptionist `403`.
- Legacy `/api/v1/treatments/finding` & `/symptom` remain un-gated and record timezone-aware `ClinicalEvent.occurred_at`.
- Legacy `Treatment` count == `0` for calls to the 4 new native routes.

#### VERIFICATION COMMANDS (Real Exit Codes Required)
- `.\.venv\Scripts\python.exe -m pytest backend/tests/services/test_clinical_command_service.py -q` (new)
- `.\.venv\Scripts\python.exe -m ruff check --config ruff.toml backend`
- `.\.venv\Scripts\python.exe .github/scripts/check_agent_authority.py`

#### PR BODY REQUIREMENTS
- **Top Line:** `RBAC touches: POST /api/v1/patients/{patient_id}/clinical-findings[/bulk] (CLINICAL_WRITE), /clinical-procedures[/bulk] (TREATMENT_PLAN_WRITE or CLINICAL_WRITE); legacy /treatments/finding & /symptom unchanged | Native-write flag status: 4 new routes gated by clinical_vnext_native_writes (default OFF -> 404) | Migrations: NONE`
- **How to test on staging (<= 15 min):**
  1. With `clinical_vnext_native_writes` ON for tenant `1`, `POST /api/v1/patients/1/clinical-findings/bulk` with 2 findings on teeth `16` (`M,O`) and `26` (`O`).
  2. Call `GET /api/v1/patients/1/clinical-work-items` and confirm both items + targets exist.
  3. Confirm legacy treatments and billing are unchanged.

#### STOP CONDITIONS
- Stop if existing `/treatments/finding` or `/symptom` callers break.

#### QUEUE STATE BLOCK
```text
=== QUEUE STATE ===
Slice: S05 - Finding & Procedure Single/Bulk Command APIs (G7-M04..M07)
Status: DONE | PARTIAL | BLOCKED
PR: <URL>
Next Slice: S06
===================
```

---

### CARD S06 — Work-Item Correction, Tooth Detail & Clinical History APIs (`G7-M08`, `G7-M10`, `G7-M11`)
- **Branch:** `feat/clinical-event-correction-history-api`
- **Delivery:** One PR -> `staging`, then STOP. **DO NOT MERGE.**
- **Rule 0:** Read `backend/services/clinical_workspace_service.py:213-260` and `backend/models/clinical_core.py:97-145,301-380` on `origin/staging` first. If they contradict this card, **STOP and report**.
- **Matrix Items Closed (3):**
  - `G7-M08`: Add event correction API
  - `G7-M10`: Add tooth detail API
  - `G7-M11`: Add history API

#### DECISIONS
1. **Work-Item Level Correction + Correction Event (`G7-M08` / Settled `D7` — Zero Migration, Zero Event Mutation):**
   - Real model facts (`backend/models/clinical_core.py:301-340`): `ClinicalEvent` has only `id`, `tenant_id`, `patient_id`, `work_item_id`, `care_session_id`, `event_type`, `occurred_at`, `actor_user_id`, `payload`, `notes`, `created_at` (no `entered_in_error` or self-FK columns), while `ClinicalWorkspaceService` (`backend/services/clinical_workspace_service.py:221-253`) already excludes work items whose `status` is `superseded` / `entered_in_error` / `entered-in-error`, as well as any `ClinicalEvent` attached to those `superseded_work_item_ids` or whose `event_type` is `superseded` / `entered_in_error`. The workspace reducer is **NOT** altered in this slice.
   - Endpoint: `POST /api/v1/patients/{patient_id}/clinical-work-items/{work_item_id}/correct` (gated by `clinical_vnext_native_writes` -> `404` when OFF; requires `Permission.CLINICAL_WRITE`).
   - Request body: `{mode: "entered_in_error" | "supersede", reason: str (required, max 500), replacement: ClinicalWorkItemCreate (required only for supersede), expected_version_id: int (optional)}`.
   - Modes:
     - `mode = "entered_in_error"`: set target `ClinicalWorkItem.status = "entered_in_error"`.
     - `mode = "supersede"`: set old `ClinicalWorkItem.status = "superseded"` and create the `replacement` `ClinicalWorkItem` with its `ClinicalWorkItemTarget` rows in the same transaction.
     - In **both** modes, append **ONE** new `ClinicalEvent` (`event_type = "entered_in_error"` or `"superseded"`, `work_item_id = work_item.id`, `payload` containing `{"work_item_id": work_item.id, "reason": reason, ...}` and for `supersede` `"replacement_work_item_id": new_item.id`) in the same transaction. **Never delete or update any existing `ClinicalEvent` row.**
   - Concurrency & status guards: return `409 Conflict` when the work item is already `superseded` or `entered_in_error` (explicit status check) or on `expected_version_id` mismatch / SQLAlchemy `StaleDataError` (`version_id`). Return `404` for cross-tenant, cross-patient, or restricted-doctor visibility.
   - Events without a `work_item_id` (e.g. backfilled tooth-status events) are **NOT** correctable via work-item correction: if a caller passes a missing/unlinked reference or attempts to correct an unlinked event, return `422` with a clear message (`"Standalone events without a clinical work item cannot be corrected via work-item correction"`).
2. **Tooth Detail API (`G7-M10`):** `GET /api/v1/patients/{patient_id}/clinical-teeth/{tooth_key}` (requires `Permission.CLINICAL_READ`):
   - Validates `tooth_key in FDI_TOOTH_KEYS` (`422` otherwise).
   - Returns projected tooth summary (from `ClinicalWorkspaceService`), active & historical `ClinicalWorkItem`s targeting `tooth_key`, `ClinicalEvent` timeline targeting `tooth_key`, and legacy `Treatment` / `ToothStatus` records for that tooth.
3. **Patient Clinical History API (`G7-M11`):** `GET /api/v1/patients/{patient_id}/clinical-events` (requires `Permission.CLINICAL_READ`):
   - Returns paginated chronological clinical event log (`occurred_at DESC, id DESC`) for the patient. Query parameter `include_entered_in_error: bool = False` means **"include events of corrected (`entered_in_error` / `superseded`) work items and correction events"** (excluded when `False`, returned when `True`).

#### SCOPE
- **Schemas (`backend/schemas/clinical_commands.py` (new)):** `ClinicalWorkItemCorrectionCreate`, `ClinicalWorkItemCorrectionResponse`, `ClinicalEventRead`, `ClinicalToothDetailRead`.
- **Service (`backend/services/clinical_command_service.py` (new)):** `correct_work_item`, `get_tooth_detail`, `list_patient_events`.
- **Router (`backend/routers/clinical_commands.py` (new)):**
  - `POST /patients/{patient_id}/clinical-work-items/{work_item_id}/correct`
  - `GET /patients/{patient_id}/clinical-teeth/{tooth_key}`
  - `GET /patients/{patient_id}/clinical-events`
- **Status Doc:** Update `G7` row in `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`.

#### EXCLUDE
- Idempotency key middleware (`S07`).
- Altering `ClinicalWorkspaceService` reduction semantics (`backend/services/clinical_workspace_service.py`).
- Frontend UI changes (`S08`–`S11`) or any schema migration.

#### FILES LIKELY TOUCHED
- `backend/schemas/clinical_commands.py` (new)
- `backend/schemas/__init__.py`
- `backend/services/clinical_command_service.py` (new)
- `backend/routers/clinical_commands.py` (new)
- `backend/tests/services/test_clinical_command_service.py` (new)
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`

#### STEP 0 — ASSUMPTIONS TO VERIFY
- Inspect `ClinicalEvent` in `backend/models/clinical_core.py:301-340` (confirm columns: `id`, `tenant_id`, `patient_id`, `work_item_id`, `care_session_id`, `event_type`, `occurred_at`, `actor_user_id`, `payload`, `notes`, `created_at`) and confirm `ClinicalWorkspaceService` reduction in `backend/services/clinical_workspace_service.py:221-253` excludes work items with `status` in `("superseded", "entered-in-error", "entered_in_error")` and their attached events.

#### TESTS REQUIRED
- Both correction modes (`mode="entered_in_error"` sets `status="entered_in_error"` + appends `entered_in_error` event; `mode="supersede"` sets old item `status="superseded"`, creates replacement work item + targets, and appends `superseded` event with `replacement_work_item_id`).
- Double-correcting an already `entered_in_error` or `superseded` work item -> `409 Conflict`.
- Stale `expected_version_id` / `StaleDataError` -> `409 Conflict`.
- Workspace snapshot in `VNEXT_PRIMARY` (`GET /api/v1/patients/{patient_id}/clinical-workspace`) automatically excludes the corrected work item (and includes the replacement work item for `supersede`).
- History API (`GET /api/v1/patients/{patient_id}/clinical-events`): default (`include_entered_in_error=False`) excludes events of corrected work items; `include_entered_in_error=True` returns the original events and the correction event.
- Zero `ClinicalEvent` rows deleted or updated; zero `Treatment`, `Payment`, or `StockMovement` delta.
- `GET .../clinical-teeth/16` returns tooth summary, work items, and events for Tooth `16` only; invalid FDI `99` returns `422`.
- Cross-tenant, cross-patient, and restricted-doctor visibility -> `404`; flag OFF on `POST .../correct` -> `404`.

#### VERIFICATION COMMANDS (Real Exit Codes Required)
- `.\.venv\Scripts\python.exe -m pytest backend/tests/services/test_clinical_command_service.py backend/tests/test_clinical_workspace_snapshot.py -q` (new)
- `.\.venv\Scripts\python.exe -m ruff check --config ruff.toml backend`
- `.\.venv\Scripts\python.exe .github/scripts/check_agent_authority.py`

#### PR BODY REQUIREMENTS
- **Top Line:** `RBAC touches: POST /api/v1/patients/{patient_id}/clinical-work-items/{work_item_id}/correct (CLINICAL_WRITE); GET /clinical-teeth/{tooth_key} & /clinical-events (CLINICAL_READ) | Native-write flag status: POST gated by clinical_vnext_native_writes (default OFF -> 404) | Migrations: NONE`
- **How to test on staging (<= 15 min):**
  1. Call `GET /api/v1/patients/1/clinical-teeth/16` and `GET /api/v1/patients/1/clinical-events`.
  2. With `clinical_vnext_native_writes` ON for tenant `1`, create a finding work item, then call `POST .../clinical-work-items/{wi_id}/correct` with `mode="entered_in_error"`; confirm correction event is returned in history with `include_entered_in_error=true` and work item is excluded from active workspace projection.

#### STOP CONDITIONS
- Stop if any `ClinicalEvent` row is deleted or mutated.

#### QUEUE STATE BLOCK
```text
=== QUEUE STATE ===
Slice: S06 - Work-Item Correction, Tooth Detail & Clinical History APIs (G7-M08, G7-M10, G7-M11)
Status: DONE | PARTIAL | BLOCKED
PR: <URL>
Next Slice: S07
===================
```

---

### CARD S07 — Command Layer Tenant Security, Contract, Idempotency & Concurrency (`G7-M13`..`G7-M16`)
- **Branch:** `feat/clinical-command-idempotency-concurrency`
- **Delivery:** One PR -> `staging`, then STOP. **DO NOT MERGE.**
- **Rule 0:** Read `backend/services/clinical_command_service.py` (new), `backend/routers/clinical_commands.py` (new), and `backend/services/treatment_plan_service.py:20-24,475-485` on `origin/staging` first. If they contradict this card, **STOP and report**.
- **Matrix Items Closed (4):**
  - `G7-M13`: Add tenant security tests
  - `G7-M14`: Add API contract tests
  - `G7-M15`: Add idempotency keys
  - `G7-M16`: Add optimistic concurrency handling

#### DECISIONS
1. **Race-Safe Idempotency Keys (`G7-M15`, Zero-Migration):**
   - Support optional `Idempotency-Key` HTTP header (or `idempotency_key` field in payload, max 128 chars) on all `POST` endpoints in `backend/routers/clinical_commands.py` (new) (`create_work_item`, `create_finding`, `create_findings_bulk`, `create_procedure`, `create_procedures_bulk`, `correct_work_item`).
   - **PostgreSQL Transaction Advisory Lock (`R05`):** Before performing the idempotency lookup, inside the same database transaction, execute `SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))` with `lock_key = f"{self.tenant_id}:{key}"` when `self.db.bind is not None and self.db.bind.dialect.name == "postgresql"` (no-op on SQLite). This serializes concurrent requests with the same `(tenant_id, key)` without requiring a schema migration.
   - Store `"idempotency_key": key` and `"request_fingerprint": fingerprint` inside `ClinicalEvent.payload` (`JSON` column at `backend/models/clinical_core.py:318`). Before creating a new work item/event, if `idempotency_key` is provided, query `ClinicalEvent` for `(tenant_id, patient_id, payload["idempotency_key"] == key)`:
     - If found with matching request fingerprint (`kind`, `code`, `targets` / correction payload), return the existing `ClinicalWorkItem` / correction result idempotently (`200`).
     - If found with a **different** request payload/fingerprint for the same key, raise `409 Conflict` (`"Idempotency key already used with different parameters"`).
2. **Optimistic Concurrency (`G7-M16`):**
   - Require or validate `expected_version_id: Optional[int]` on `PATCH /patients/{patient_id}/clinical-work-items/{work_item_id}` and `POST /patients/{patient_id}/clinical-work-items/{work_item_id}/correct`.
   - If `expected_version_id is not None and work_item.version_id != expected_version_id`, or if SQLAlchemy raises `StaleDataError`, rollback safely (re-preserving primitive IDs per `R04`) and raise `409 Conflict`.
3. **Comprehensive Security & Contract Suite (`G7-M13`, `G7-M14`):**
   - Prove tenant isolation, cross-patient `404`, doctor visibility mode (`ALL_ASSIGNED` / `APPOINTMENTS_ONLY`), role matrix (`SUPER_ADMIN`, `ADMIN`, `DOCTOR`, `NURSE`, `RECEPTIONIST`, `ASSISTANT`, `GUEST`), and `StandardResponse` contract across every `G7` endpoint.

#### SCOPE
- `backend/services/clinical_command_service.py` (new) & `backend/routers/clinical_commands.py` (new): Add `Idempotency-Key` header extraction, PostgreSQL `pg_advisory_xact_lock(hashtextextended(...))` guard, payload fingerprint verification, and `expected_version_id` / `StaleDataError` -> `409` handling.
- `backend/tests/services/test_clinical_command_security_and_contracts.py` (new): Dedicated test suite for `G7-M13`, `G7-M14`, `G7-M15`, `G7-M16` including concurrent same-key race test.
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`: Mark `G7` as **DONE** with full evidence (`G7-M01`..`G7-M16`).

#### EXCLUDE
- Any database schema migration (uses `ClinicalEvent.payload` JSON + PostgreSQL `pg_advisory_xact_lock`).
- Frontend UI changes (`S08`).

#### FILES LIKELY TOUCHED
- `backend/schemas/clinical_commands.py` (new)
- `backend/services/clinical_command_service.py` (new)
- `backend/routers/clinical_commands.py` (new)
- `backend/tests/services/test_clinical_command_security_and_contracts.py` (new)
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`

#### STEP 0 — ASSUMPTIONS TO VERIFY
- Verify how `ClinicalEvent.payload` is queried in `backend/services/treatment_service.py:236-268` (`_find_linked_clinical_work_item`) so portable SQLite + PostgreSQL JSON lookup works identically in unit tests and staging.

#### TESTS REQUIRED
- Replaying `POST` with identical `Idempotency-Key` and body returns same IDs and creates `0` extra rows.
- Concurrency test: two simultaneous `POST` requests with the same `Idempotency-Key` and identical payload result in **exactly one** `ClinicalWorkItem` created (`count == 1`).
- Replaying `POST` with same `Idempotency-Key` and different `code` or `tooth_key` returns `409`.
- Same `Idempotency-Key` across two different tenants (`tenant_id=1` vs `tenant_id=2`) succeeds independently (tenant-scoped idempotency).
- Stale `expected_version_id` on `PATCH` and `/correct` returns `409` and does not corrupt session (`_get_active_current_user` tested after rollback).
- Full cross-tenant, cross-patient, doctor-visibility, and RBAC matrix across all `G7` endpoints.

#### VERIFICATION COMMANDS (Real Exit Codes Required)
- `.\.venv\Scripts\python.exe -m pytest backend/tests/services/test_clinical_command_service.py backend/tests/services/test_clinical_command_security_and_contracts.py -q` (new)
- `.\.venv\Scripts\python.exe -m ruff check --config ruff.toml backend`
- `.\.venv\Scripts\python.exe .github/scripts/check_agent_authority.py`

#### PR BODY REQUIREMENTS
- **Top Line:** `RBAC touches: Full security & contract test suite across all G7 endpoints | Native-write flag status: Gated by clinical_vnext_native_writes (default OFF -> 404) | Migrations: NONE`
- **How to test on staging (<= 15 min):**
  1. Send `POST /api/v1/patients/1/clinical-work-items` twice (and concurrently) with header `Idempotency-Key: test-key-001` -> confirm identical work item ID returned and only 1 row created.
  2. Send `PATCH` with `expected_version_id: 999` -> confirm `409 Conflict`.

#### STOP CONDITIONS
- Stop if JSON querying on `ClinicalEvent.payload` fails on SQLite test fixtures; use portable filter logic matching `TreatmentService._find_linked_clinical_work_item`.

#### QUEUE STATE BLOCK
```text
=== QUEUE STATE ===
Slice: S07 - Command Layer Tenant Security, Contract, Idempotency & Concurrency (G7-M13..M16)
Status: DONE | PARTIAL | BLOCKED
PR: <URL>
Next Slice: S08
===================
```

---

### CARD S08 — Chart Tooth Selection State, Multi-Select & Direct Surface Interaction (`G8-M01`, `G8-M06`, `G8-M07`)
- **Branch:** `feat/chart-selection-inspector-surfaces`
- **Delivery:** One PR -> `staging`, then STOP. **DO NOT MERGE.**
- **Rule 0:** Read `frontend/src/pages/PatientDetails.jsx:100-185,468-597`, `frontend/src/features/clinical-chart/components/ClinicalChartRenderer.jsx`, `frontend/src/features/clinical-chart/components/ClinicalChartInspector.jsx`, and `frontend/src/features/clinical-chart/adapters/workspaceSnapshotAdapter.js` on `origin/staging` first. If they contradict this card, **STOP and report**.
- **Matrix Items Closed (3):**
  - `G8-M01`: Add tooth selection state
  - `G8-M06`: Add multi-select
  - `G8-M07`: Add direct surface interaction

#### DECISIONS
1. In `PatientDetails.jsx` (**Chart** tab), clicking a tooth or surface on `ClinicalChartRenderer` must **select** the tooth/surface inline and display a chairside selection bar + `ClinicalChartInspector` panel instead of immediately popping open the giant `TreatmentModal`!
2. Provide a clear `"Record Treatment / تسجيل علاج"` action inside the selection bar / inspector that opens `TreatmentModal` pre-populated with the selected tooth and toggled surfaces (`M`, `D`, `O`, `I`, `B`, `L`, `P`), so existing legacy treatment entry continues to work seamlessly (`0` workflow regressions).
3. **Multi-Select (`G8-M06`):** Add a `"Multi-Select / تحديد متعدد"` toggle (and `Shift+Click` / `Ctrl+Click` support on desktop) allowing the doctor to select multiple teeth simultaneously (e.g., `[16, 17, 18]`), showing selected tooth badges and a `"Clear Selection"` button.
4. **Direct Surface Interaction (`G8-M07`):** Clicking surfaces directly on the SVG crown or in the inline surface pill bar toggles multiple surfaces (`['M', 'O', 'D']`) on the active tooth selection state.
5. Full Arabic RTL and English LTR i18n (`frontend/src/locales/ar/translation.json` and `frontend/src/locales/en/translation.json`) and keyboard/touch accessibility (`min-h-11` touch targets per design system guardrails).

#### SCOPE
- `frontend/src/pages/PatientDetails.jsx`: Add `selectedTeeth` (`string[]`), `selectedSurfacesByTooth` (`Record<string, string[]>`), and `isMultiSelectMode` (`boolean`) states; pass selection state to `adaptWorkspaceSnapshotToRenderer` / `ClinicalChartRenderer`; render inline chairside selection summary + surface toggles + `"Record Treatment"` trigger.
- `frontend/src/features/clinical-chart/adapters/workspaceSnapshotAdapter.js` & `ClinicalChartRenderer.jsx`: Support highlighting multiple selected teeth (`selectedToothKeys`) and selected surfaces (`selectedSurfaces`) alongside single `selectedToothKey`.
- `frontend/src/locales/ar/translation.json` & `frontend/src/locales/en/translation.json`: Add translation keys.
- `frontend/src/features/clinical-chart/tests/ChartSelectionAndSurfaces.test.jsx` (new): Add unit/integration tests for single selection, multi-tooth selection, multi-surface toggling, and opening `TreatmentModal` from selection with pre-filled tooth & surfaces.
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`: Update `G8` row with `G8-M01`, `G8-M06`, `G8-M07` evidence.

#### EXCLUDE
- Quick action launcher, favorites, recents, search (`S09`), sticky tool mode (`S10`).
- Any backend changes or migrations.

#### FILES LIKELY TOUCHED
- `frontend/src/pages/PatientDetails.jsx`
- `frontend/src/features/clinical-chart/adapters/workspaceSnapshotAdapter.js`
- `frontend/src/features/clinical-chart/components/ClinicalChartRenderer.jsx`
- `frontend/src/locales/ar/translation.json`
- `frontend/src/locales/en/translation.json`
- `frontend/src/features/clinical-chart/tests/ChartSelectionAndSurfaces.test.jsx` (new)
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`

#### STEP 0 — ASSUMPTIONS TO VERIFY
- Inspect existing tests in `frontend/src/pages/PatientDetails.chartRoots.test.jsx` and `frontend/src/features/clinical-chart/tests/` to see what assertions exist on clicking a tooth in `PatientDetails.jsx`. Ensure existing tests are updated only if they asserted immediate modal opening, or keep double-click / action button compatibility so no test is weakened.

#### TESTS REQUIRED
- Clicking Tooth `16` selects Tooth `16` visually (`aria-pressed` / `data-selected="true"`) and shows inline inspector with Tooth `16`.
- Clicking surfaces `M` and `O` on Tooth `16` accumulates `['M', 'O']` in selection state; clicking `"Record Treatment"` opens `TreatmentModal` pre-populated with Tooth `16` and surfaces `['M', 'O']`.
- Multi-select mode selects Teeth `14`, `15`, `16` together and clears cleanly.
- RTL/LTR rendering and `check-design-system-guardrails.mjs` pass.

#### VERIFICATION COMMANDS (Real Exit Codes Required)
- `npm.cmd --prefix frontend run test -- --run src/features/clinical-chart/tests/ src/pages/PatientDetails.chartRoots.test.jsx`
- `npm.cmd --prefix frontend run lint`
- `npm.cmd --prefix frontend run build`
- `node frontend/scripts/check-design-system-guardrails.mjs --diff-base=origin/staging`
- `.\.venv\Scripts\python.exe .github/scripts/check_agent_authority.py`

#### PR BODY REQUIREMENTS
- **Top Line:** `RBAC touches: NONE (frontend UX only) | Native-write flag status: N/A | Migrations: NONE`
- **How to test on staging (<= 15 min):**
  1. Open any patient -> **Chart** tab.
  2. Click Tooth `16` -> confirm tooth highlights and inline selection bar appears with surface pills (`M, D, O, B, L`).
  3. Toggle surfaces `M` and `O`, then click `"Record Treatment"` -> confirm `TreatmentModal` opens with Tooth `16` and `MO` selected.
  4. Toggle `"Multi-Select"` -> click Teeth `16`, `17`, `18` -> confirm all 3 teeth highlight.

#### STOP CONDITIONS
- Stop if `check-design-system-guardrails.mjs` reports any violation or if `a16RegressionGate.test.jsx` snapshots break.

#### QUEUE STATE BLOCK
```text
=== QUEUE STATE ===
Slice: S08 - Chart Tooth Selection State, Multi-Select & Direct Surface Interaction (G8-M01, G8-M06, G8-M07)
Status: DONE | PARTIAL | BLOCKED
PR: <URL>
Next Slice: S09
===================
```

---

### CARD S09 — Chart Quick Action Launcher, Favorites, Recents, Search & Smart Defaults (`G8-M02`, `G8-M08`..`G8-M11`)
- **Branch:** `feat/chart-quick-action-launcher`
- **Delivery:** One PR -> `staging`, then STOP. **DO NOT MERGE.**
- **Rule 0:** Read `frontend/src/pages/PatientDetails.jsx`, `frontend/src/hooks/usePatientDetails.js`, and `backend/clinical/catalog.py` on `origin/staging` first. If they contradict this card, **STOP and report**.
- **Matrix Items Closed (5):**
  - `G8-M02`: Add quick action launcher
  - `G8-M08`: Add favorites
  - `G8-M09`: Add recents
  - `G8-M10`: Add search
  - `G8-M11`: Add smart defaults

#### DECISIONS
1. Build `ChartQuickActionLauncher.jsx` in `frontend/src/features/clinical-chart/components/ChartQuickActionLauncher.jsx` (new), displayed inline in the **Chart** tab whenever one or more teeth are selected (or opened via keyboard shortcut `/` or `Alt+K`).
2. **Favorites (`G8-M08`) & Recents (`G8-M09`):**
   - Provide default clinic favorites mapped to canonical `ProcedureCode` and `FindingCode` members (`backend/clinical/catalog.py:53-76`): `Composite Restoration / REST_COMPOSITE`, `Root Canal Treatment / ENDO_RCT`, `Crown Restoration / PROS_CROWN`, `Surgical Extraction / SURG_EXTRACTION`, `Dental Caries / CARIES`, `Tooth Fracture / FRACTURE`, `Dental Pain / PAIN` (plus clinic procedures from `useProcedures()`).
   - Allow doctors to star/unstar favorites and automatically track the last 5 used actions in tenant/user-scoped `localStorage` (`dentix_chart_favorites_${tenantId}_${userId}`, `dentix_chart_recents_${tenantId}_${userId}`).
3. **Instant Search (`G8-M10`):** Filter procedures and findings by Arabic or English name or canonical code in real time.
4. **Smart Defaults Derived from Catalog `allowed_target_kinds` (`G8-M11` & Decision `D5` / `PD03`):**
   - Surface-vs-whole-tooth behaviour **MUST** be derived from `ProcedureDefinition.allowed_target_kinds` (`backend/clinical/catalog.py:247`) and `FindingDefinition.allowed_target_kinds` (`backend/clinical/catalog.py:364`) — **never hardcoded procedure lists**.
   - Specifically:
     - When `allowed_target_kinds` contains `'tooth'` and does **not** contain `'surface'` (i.e. `ENDO_RCT`, `PROS_CROWN`, `PROS_BRIDGE`, `IMPLANT_FIXTURE`, `IMPLANT_CROWN`, `SURG_EXTRACTION`, `PROS_DENTURE`, `PAIN`), `target_kind` defaults to `'tooth'` (no surface required; applies in 1 click).
     - When `'surface'` is in `allowed_target_kinds` (`REST_COMPOSITE` where `allowed_target_kinds == ('surface',)` at `catalog.py:276`, or `CARIES`/`FRACTURE` where `allowed_target_kinds == ('tooth', 'surface')` at `catalog.py:379,385`), if the user already clicked surfaces on the tooth (`S08`), reuse those surfaces (`target_kind='surface'`); if no surface was clicked yet, open an inline 1-click surface pill popover pre-selecting `'O'` on posterior teeth (`4`–`8`) and `'I'` on anterior teeth (`1`–`3`) so `ck_cwit_shape` (`TARGET_SHAPE_CONSTRAINT` at `backend/models/clinical_core.py:77-84,172`) is always satisfied.
5. **Safe Write Routing (Respecting Coexistence & Flags):**
   - When `clinical_vnext_native_writes` is enabled in `useTenantFeatures()`, findings and native procedures can dispatch to the `G7` endpoints (`S05`); when `clinical_vnext_native_writes` is OFF (the default for all clinics today), selecting a procedure from the quick launcher either dispatches through `POST /api/v1/treatments` / `POST /api/v1/treatments/multi-procedure` with smart defaults (using the clinic's `procedures` catalog fee) or opens `TreatmentModal` pre-filled with the chosen procedure, tooth, surfaces, and default price so **legacy billing and inventory remain 100% intact**.

#### SCOPE
- `frontend/src/features/clinical-chart/components/ChartQuickActionLauncher.jsx` (new)
- `frontend/src/pages/PatientDetails.jsx`: Integrate `ChartQuickActionLauncher` with `selectedTeeth` and `selectedSurfacesByTooth` from `S08`.
- `frontend/src/locales/ar/translation.json` & `frontend/src/locales/en/translation.json`: Arabic & English labels.
- `frontend/src/features/clinical-chart/tests/ChartQuickActionLauncher.test.jsx` (new): Tests for search, favorites toggle, recents persistence, catalog-driven `allowed_target_kinds` smart defaults (posterior `'O'` vs anterior `'I'` vs whole-tooth `'tooth'`), and action dispatch.
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`: Update `G8` row with `G8-M02`, `G8-M08`..`M11` evidence.

#### EXCLUDE
- Sticky tool mode (`S10`), consequence-aware remove & click-budget telemetry (`S11`).
- Any backend migration.

#### FILES LIKELY TOUCHED
- `frontend/src/features/clinical-chart/components/ChartQuickActionLauncher.jsx` (new)
- `frontend/src/pages/PatientDetails.jsx`
- `frontend/src/locales/ar/translation.json`
- `frontend/src/locales/en/translation.json`
- `frontend/src/features/clinical-chart/tests/ChartQuickActionLauncher.test.jsx` (new)
- `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`

#### STEP 0 — ASSUMPTIONS TO VERIFY
- Inspect `useProcedures()` (`frontend/src/pages/PatientDetails.jsx:6,77`) and `useTreatmentOperations` (`frontend/src/features/patients/hooks/useTreatmentOperations.js`) to see how procedures and treatment saves are invoked in `PatientDetails.jsx`.
- Verify `ProcedureDefinition.allowed_target_kinds` and `FindingDefinition.allowed_target_kinds` in `backend/clinical/catalog.py:242-396`.

#### TESTS REQUIRED
- Rendering favorites and recents when a tooth is selected.
- Searching in Arabic and English filters the launcher list.
- Starring/unstarring a procedure updates favorites; executing an action prepends it to recents.
- Smart defaults driven by `allowed_target_kinds` assign `'O'` on Tooth `16`, `'I'` on Tooth `11` for surface-capable definitions (`REST_COMPOSITE`, `CARIES`, `FRACTURE`), and `'tooth'` target kind for non-surface definitions (`SURG_EXTRACTION`, `PROS_CROWN`, `ENDO_RCT`).
- RTL/LTR and design-system guardrails pass.

#### VERIFICATION COMMANDS (Real Exit Codes Required)
- `npm.cmd --prefix frontend run test -- --run src/features/clinical-chart/tests/ChartQuickActionLauncher.test.jsx` (new)
- `npm.cmd --prefix frontend run lint`
- `npm.cmd --prefix frontend run build`
- `node frontend/scripts/check-design-system-guardrails.mjs --diff-base=origin/staging`
- `.\.venv\Scripts\python.exe .github/scripts/check_agent_authority.py`

#### PR BODY REQUIREMENTS
- **Top Line:** `RBAC touches: NONE (frontend UI using existing RBAC-protected endpoints) | Native-write flag status: Respects tenant feature flags; legacy billing path preserved by default | Migrations: NONE`
- **How to test on staging (<= 15 min):**
  1. Open a patient -> **Chart** tab -> click Tooth `16`.
  2. In the Quick Action Launcher, search for a procedure, star it as a favorite, and click it.
  3. Confirm smart defaults pre-fill Tooth `16` (`O` surface for `REST_COMPOSITE`, whole tooth for `PROS_CROWN`/`SURG_EXTRACTION`) and recent list updates.

#### STOP CONDITIONS
- Stop if any change bypasses legacy billing/inventory when `clinical_vnext_native_writes` is OFF.

#### QUEUE STATE BLOCK
```text
=== QUEUE STATE ===
Slice: S09 - Chart Quick Action Launcher, Favorites, Recents, Search & Smart Defaults (G8-M02, G8-M08..M11)
Status: DONE | PARTIAL | BLOCKED
PR: <URL>
Next Slice: S10
===================
```

---

## PART II — CONDENSED EXECUTION BRIEFS (`S10`–`S36`) — `EXPAND JUST-IN-TIME`

Each brief below locks the architectural boundaries, exact matrix items, dependencies, gotchas, decisions, and migration/flag rules. Before dispatching any of `S10`–`S36` to Flash, expand the brief into the full Part I template against the latest `origin/staging` head.

---

### S10 — Tooth-First Flow, Procedure-First Flow & Sticky Tool Mode (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/chart-sticky-tool-flows` · **Deps:** `S09` · **Size:** `M` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (3):** `G8-M03` (Add tooth-first flow), `G8-M04` (Add procedure-first flow), `G8-M05` (Add sticky tool mode).
- **Goal & Decisions:** Support both (1) **Tooth-First Flow** (select tooth/surfaces -> click launcher action -> applies immediately) and (2) **Procedure-First & Sticky Tool Flow** (select procedure/finding in launcher -> toggle `"Sticky Mode / وضع التكرار"` -> click multiple teeth sequentially on `ClinicalChartRenderer` to apply or queue batch items; `Esc` or toggle button exits sticky mode). Applies `D5`/`PD03` (surface vs whole-tooth behaviour derived from `ProcedureDefinition.allowed_target_kinds` / `FindingDefinition.allowed_target_kinds` in `backend/clinical/catalog.py:247,364`). Translations in `frontend/src/locales/ar/translation.json` and `frontend/src/locales/en/translation.json`.
- **Gotchas:** Ensure sticky mode displays a prominent active-tool banner above the chart and does not accidentally fire when scrolling on mobile touch screens.

### S11 — Consequence-Aware Remove, Click-Budget Telemetry & Giant Modal De-emphasis (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/chart-click-budget-consequence-remove` · **Deps:** `S10` · **Size:** `M` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (3):** `G8-M13` (Add consequence-aware remove), `G8-M14` (Measure click budget), `G8-M15` (De-emphasize old giant modal).
- **Goal & Decisions:** (1) When removing/cancelling a work item or treatment from the chart inspector, inspect whether it is attached to an active treatment plan phase (`plan_items`) or has completed sessions/payments, and display a consequence warning modal before removal (`G8-M13`). (2) Add deterministic unit/integration click-counter assertions proving single-finding, multi-tooth finding, and single-procedure entry complete in `<= 3` clicks (`G8-M14`). (3) Make the inline quick launcher + inspector the primary chairside path and relegate `TreatmentModal` to a secondary `"Advanced / Classic Entry"` button (`G8-M15`). Closes Phase `G8`.

### S12 — Treatment Plan Phase Reorder/Edit & Chart Plan Overlay (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/clinical-plans-reorder-chart-overlay` · **Deps:** `S08` · **Size:** `M` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (2):** `G9-M03` (Add phase CRUD/reorder), `G9-M09` (Add plan overlay to chart).
- **Goal & Decisions:** (1) Complete `G9-M03` in `TreatmentPlanService` (`backend/services/treatment_plan_service.py`) and `backend/routers/treatment_plans.py`: add `PATCH /patients/{patient_id}/clinical-plans/{plan_id}/phases/{phase_id}` (rename/update notes) and `POST /patients/{patient_id}/clinical-plans/{plan_id}/phases/reorder` (reorder `phase_order` atomically using a temporary negative offset inside the transaction so `uq_ctpp_plan_phase_order` at `backend/models/clinical_core.py:251` never collides), plus `DELETE .../phases/{phase_id}` (allowed only in `draft`/`proposed` plans -> `409` otherwise). (2) In `TreatmentPlansCard.jsx` & `PatientDetails.jsx`, add `"Overlay on Chart"` toggle per plan/phase that highlights planned teeth on `ClinicalChartRenderer` colour-coded by phase (`G9-M09`).
- **Flag & RBAC:** Gated by `clinical_treatment_plans` (`404` when off); `TREATMENT_PLAN_WRITE` for mutations, `CLINICAL_READ` for reads.

### S13 — Treatment Plan Dynamic Estimate Projection (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/clinical-plans-dynamic-estimates` · **Deps:** `S12` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (1):** `G9-M10` (Add estimate projection).
- **Goal & Decisions:** Apply **D2** and **PD04**: Compute dynamic fee estimates on-the-fly per plan item, per phase (`phase_estimated_total`), and per plan (`plan_estimated_total`) without adding any DB price column (zero migrations; storing an immutable snapshot would require a migration and is deferred per D2). Resolve fees using patient's `default_price_list_id` (`PriceListItem`) first, falling back to `models.Procedure.cost` (`backend/services/treatment_service.py:42-90`). Display badges in `TreatmentPlansCard.jsx` explicitly labeled `"Estimate / تقديري"`.
- **Gotchas:** Never create `Treatment`, `Payment`, or `ClinicalCharge` rows when computing or viewing estimates.

### S14 — Treatment Plan Comparison UX (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/clinical-plans-comparison-ux` · **Deps:** `S12`, `S13` · **Size:** `M` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (1):** `G9-M11` (Add plan comparison UX).
- **Goal & Decisions:** In `TreatmentPlansCard.jsx`, when a patient has `>= 2` non-cancelled treatment plans, show a `"Compare Plans / مقارنة الخطط"` button opening a side-by-side comparison view (desktop columns / mobile carousel) showing Plan A vs Plan B status badges, phase count, shared vs unique procedures (`ClinicalWorkItem.id`), target teeth, and dynamic estimate totals (`S13`), with a direct `"Accept Plan"` button for `proposed` plans.

### S15 — Treatment Plan Legacy Safety Rules (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/clinical-plans-legacy-safety` · **Deps:** `S13` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (1):** `G9-M12` (Add legacy safety rules).
- **Goal & Decisions:** Enforce and prove via service guards and invariant tests that creating, editing, reordering, estimating, proposing, accepting, completing, or cancelling a `ClinicalTreatmentPlan`: (1) never writes to `treatments`, `treatment_sessions`, `payments`, `stock_movements`, `treatment_material_usages`, or `lab_orders`; (2) never duplicates `ClinicalWorkItem` rows when a procedure is shared across Plan A and Plan B (`G9-M05`); and (3) never alters legacy patient billing balances in `backend/crud/billing.py`.

### S16 — Treatment Plan Concurrency Hardening (`EXPAND JUST-IN-TIME`)
- **Branch:** `test/clinical-plans-concurrency` · **Deps:** `S12`, `S13` · **Size:** `S` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (1):** `G9-M13` (Add concurrency tests).
- **Goal & Decisions:** Extend `backend/tests/services/test_treatment_plan_service.py` with concurrent async session tests covering simultaneous phase reorder (`uq_ctpp_plan_phase_order`), simultaneous phase creation retry exhaustion (`409`), simultaneous item attachment (`uq_ctpi_phase_work_item` -> `409`), and simultaneous plan transition (`StaleDataError` on `version_id` -> `409`), verifying zero `MissingGreenlet` errors after `rollback()`.

### S17 — Treatment Plan E2E Acceptance Scenario (`EXPAND JUST-IN-TIME`)
- **Branch:** `test/clinical-plans-e2e-scenario` · **Deps:** `S14`, `S15`, `S16` · **Size:** `S` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (1):** `G9-M14` (Add E2E scenario).
- **Goal & Decisions:** Add end-to-end backend + frontend scenario tests exercising the full `G9` lifecycle: create shared procedure work items -> create Option A (Crown) and Option B (Bridge/Extraction) plans -> add phases & items -> reorder phases -> project dynamic estimates -> overlay on chart -> compare Option A vs Option B -> propose & accept Option A -> verify Option A locked (`409` on add/remove) and Option B preserved (`proposed`). Mark `G9` **DONE** in `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md`.

### S18 — Care Session Service, Start/Finish Commands & Concurrency Lock (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/care-sessions-lifecycle` · **Deps:** `S07` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (4):** `G10-M01` (Create care session service), `G10-M02` (Add start-session command), `G10-M03` (Add finish-session command), `G10-M18` (Add concurrent session protection).
- **Goal & Decisions:** Create `CareSessionService` (`backend/services/care_session_service.py` (new)) and router `backend/routers/care_sessions.py` (new) mounted under `/api/v1/patients/{patient_id}/care-sessions`. Gated by `clinical_vnext_native_writes` (`404` when off). Apply **D3 (`G10-M18`)**: A patient may have at most **one** `CareSession` with `status == 'in_progress'` at a time; starting a second session while one is `in_progress` returns `409 Conflict` with the active session's ID. Support statuses `in_progress -> paused | completed | cancelled` and `paused -> in_progress | completed | cancelled`. Map `StaleDataError` (`CareSession.version_id` at `backend/models/clinical_core.py:400`) to `409`.

### S19 — Care Session Steps, Observations, Free Notes & Finalization Audit (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/care-session-steps-observations` · **Deps:** `S18` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (5):** `G10-M04` (Add step add/update API), `G10-M05` (Add partial-step support), `G10-M07` (Add observation API), `G10-M15` (Preserve free notes), `G10-M17` (Add finalization audit trail).
- **Goal & Decisions:** Add endpoints to `backend/routers/care_sessions.py` (new) for: (1) adding/updating `CareSessionStep` (`backend/models/clinical_core.py:434-476`, statuses `pending`, `in_progress`, `partial`, `completed`, `skipped`), including template initialization from `backend/clinical/workflow_templates.py` (`WorkflowTemplateDefinition`, `WorkflowStepDefinition`, `get_latest_template`, `list_templates`, `CANONICAL_WORKFLOW_TEMPLATES`); (2) recording `CareObservation` (`backend/models/clinical_core.py:479-520`, `key`, `value_json`, `tooth_key`, `surface_code`, `root_id`, `canal_id`); (3) preserving free-text notes on both `CareSession.notes` and `CareSessionStep.notes` (`G10-M15`); and (4) logging session completion via `log_admin_action` + appending a `ClinicalEvent` (`G10-M17`).
- **Gotchas:** Respect PostgreSQL triggers `trg_css_session_work_item_patient` and `trg_co_step_care_session_match` (`backend/scripts/preflight_migrations.py:185-188`): `work_item_id` on a step/observation must belong to the same `patient_id` as the `CareSession`, and `step_id` on a `CareObservation` must belong to the same `care_session_id` (`422`/`404` in service before flush).

### S20 — Chairside RCT Structured UI, Canal Targets, Working Lengths & Finish Sheet (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/chairside-rct-structured-ui` · **Deps:** `S19` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (4):** `G10-M08` (Build minimal RCT structured UI), `G10-M09` (Add canal-target UI), `G10-M10` (Add working-length structured entry), `G10-M11` (Add compact finish-session sheet).
- **Goal & Decisions:** Build `CareSessionDrawer.jsx` in `frontend/src/features/clinical-chart/components/CareSessionDrawer.jsx` (new): (1) minimal structured RCT panel allowing canal selection (`MB`, `MB2`, `ML`, `D`, `P`, `B`, `L`, `C`) tied to `root_id` from `dentalAnatomyRegistry.js` (`G10-M08`, `G10-M09`); (2) structured working-length (mm), master apical file (MAF), and irrigant entry stored as `CareObservation` rows (`G10-M10`); and (3) a compact 1-screen Finish-Session sheet (`G10-M11`) summarizing completed/partial steps and free notes. Shown only when `clinical_vnext_native_writes` is enabled for the tenant.

### S21 — Care Session Resume Engine, Continue-Treatment Card, Summary & RCT E2E (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/care-session-resume-engine` · **Deps:** `S20` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (5):** `G10-M12` (Build resume engine), `G10-M13` (Add continue-treatment card), `G10-M14` (Add clinical summary generation), `G10-M19` (Migrate new writes away from free-text-only session model), `G10-M20` (Add RCT scenario integration test).
- **Goal & Decisions:** (1) Add `GET /api/v1/patients/{patient_id}/care-sessions/resumable` returning any `in_progress`/`paused` `CareSession` plus `active` `ClinicalWorkItem` rows (`status == "active"`) with their last completed/partial steps and canal observations (`G10-M12`). (2) Render `ContinueTreatmentCard.jsx` at the top of the **Chart** tab (`G10-M13`) so the doctor can resume multi-visit RCT in 1 click without reading old free-text notes. (3) Generate a deterministic structured summary string on session finish (`G10-M14`) and route new session writes through `CareSession` when `clinical_vnext_native_writes` is ON (`G10-M19`). (4) Add multi-visit RCT integration test (`G10-M20`). Closes Phase `G10`.

### S22 — Session-to-Appointment Link & Chairside Next-Visit Request Creation (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/next-visit-requests-chairside` · **Deps:** `S18`, `S20` · **Size:** `M` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (5):** `G11-M01` (Link session to appointment), `G11-M02` (Add next-visit request creation), `G11-M06` (Populate appointment reason), `G11-M07` (Suggest duration), `G11-M08` (Prevent auto-booking without user action).
- **Goal & Decisions:** (1) Allow `POST /api/v1/patients/{patient_id}/care-sessions` to link an existing `appointment_id` (`CareSession.appointment_id` at `backend/models/clinical_core.py:394`, validating appointment belongs to same `tenant_id` and `patient_id` matching trigger `trg_care_sessions_appointment_id_parent_patient`, `G11-M01`). (2) Add `POST /api/v1/patients/{patient_id}/next-visit-requests` (`NextVisitRequest` at `backend/models/clinical_core.py:542-580`) and integrate into the Finish-Session sheet (`S20`) with populated `reason` (`G11-M06`) and duration presets (`15, 30, 45, 60, 90` min, `G11-M07`). (3) Strictly enforce `G11-M08`: creating a `NextVisitRequest` NEVER inserts a row into `appointments`.

### S23 — Attachment Context Link Service, Purpose Codes & Legacy Link Backfill (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/clinical-attachment-links-service` · **Deps:** `S07`, `S18` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (5):** `G15-M01` (Keep attachment storage unchanged), `G15-M02` (Add context links only), `G15-M06` (Add purpose codes), `G15-M09` (Add deterministic legacy link migration only), `G4-M09` (Backfill deterministic attachment links only).
- **Goal & Decisions:** Build `ClinicalAttachmentLinkService` and routes (`POST/GET/DELETE /api/v1/patients/{patient_id}/clinical-attachment-links`) using `models.ClinicalAttachmentLink` (`backend/models/clinical_core.py:582-630`). Keep existing file upload/storage (`backend/routers/upload.py`, `backend/routers/attachments.py`) 100% untouched (`G15-M01`). Enforce `PD05` `purpose_code` allowlist (`G15-M06`), verify `attachment_id`, `work_item_id`, `care_session_id`, and `clinical_event_id` all belong to `(tenant_id, patient_id)` (`404` otherwise, matching `trg_clinical_attachment_links_*_parent_patient` triggers), and extend `scripts/backfill_clinical_work_items.py` to deterministically link legacy attachments only when an explicit tooth/treatment token is unambiguous (`G15-M09`, `G4-M09`).

### S24 — Tooth Inspector & Care Session Diagnostic Image Viewers (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/clinical-attachment-context-ui` · **Deps:** `S20`, `S23` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (5):** `G15-M03` (Link images to tooth), `G15-M04` (Link images to work item), `G15-M05` (Link images to care session), `G15-M07` (Show relevant images in tooth inspector), `G15-M08` (Show relevant images in session view).
- **Goal & Decisions:** Add UI controls in **Files** tab (`PatientFiles.jsx`), **Chart Tooth Inspector** (`S08`), and **Care Session Drawer** (`S20`) to link/unlink existing patient attachments to a tooth (`G15-M03`), work item (`G15-M04`), or care session (`G15-M05`) with a purpose badge, and display linked X-rays/photos directly inside the tooth inspector (`G15-M07`) and active session drawer (`G15-M08`). Closes Phase `G15`.

### S25 — Reception Next-Visit Queue, Conversion to Appointment & Safety Lifecycle (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/reception-next-visit-queue` · **Deps:** `S22` · **Size:** `M` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (6):** `G11-M04` (Add reception queue), `G11-M05` (Convert request to appointment), `G11-M09` (Handle appointment cancellation safely), `G11-M10` (Handle appointment completion safely), `G11-M11` (Add integration tests), `G11-M12` (Add idempotency/race tests).
- **Goal & Decisions:** (1) Add `GET /api/v1/next-visit-requests` (tenant-scoped reception queue, requires `Permission.APPOINTMENT_READ`) and `POST /api/v1/next-visit-requests/{request_id}/schedule` (requires `Permission.APPOINTMENT_CREATE`, converts a `requested` item into a confirmed `models.Appointment` only upon explicit receptionist submission, setting `NextVisitRequest.status = 'scheduled'` and storing `[APPOINTMENT:<id>]` in `notes` per `PD06` — zero migrations). (2) Handle appointment cancellation (reverts linked `NextVisitRequest.status` to `'requested'`, `G11-M09`) and completion (`status = 'completed'`, `G11-M10`). (3) Add concurrency lock so two receptionists converting the same `NextVisitRequest` simultaneously cannot double-book (`409`, `G11-M12`). Closes Phase `G11`.

---

### S26 — `[MIGRATION 1/3]` Inventory Usage `care_session_id` Schema & History Preservation (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/migration-inventory-care-session-link` · **Deps:** `S18` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** **YES**
- **Exact Matrix Items (3):** `G13-M01` (Distinguish material session from care session), `G13-M02` (Add `care_session_id` to new usage model), `G13-M03` (Preserve old usage data).
- **Schema & Migration Specification (`PD07`, `R03`):**
  1. Create Alembic revision revising `1a2b3c4d5e6f` (`backend/alembic/versions/`):
     - Add nullable column `care_session_id INTEGER REFERENCES care_sessions(id) ON DELETE SET NULL` and nullable column `work_item_id INTEGER REFERENCES clinical_work_items(id) ON DELETE SET NULL` to `treatment_material_usages` (`backend/models/inventory.py:289-326`).
     - Alter `treatment_material_usages.treatment_id` to `nullable=True` and add `CheckConstraint("treatment_id IS NOT NULL OR care_session_id IS NOT NULL", name="ck_tmu_treatment_or_care_session_required")`.
     - Add index `ix_tmu_tenant_care_session` on `(tenant_id, care_session_id)`.
     - On PostgreSQL (`bind.dialect.name == "postgresql"`), install `trg_treatment_material_usages_care_session_id_parent_tenant` (`dentix_assert_parent_tenant('care_sessions', 'care_session_id', 'true')`) and `trg_treatment_material_usages_work_item_id_parent_tenant`.
  2. Update `backend/scripts/preflight_migrations.py` (`CHILD_TENANT_RELATIONSHIPS`) in lockstep so `test_clinical_core_schema.py:717` and `test_preflight_postgres_contract.py` pass!
- **Production-Snapshot Rehearsal Note:** Must be rehearsed on a restored PostgreSQL staging dump (`python -m backend.scripts.preflight_migrations`) before merge. Zero existing rows in `treatment_material_usages` are modified (`G13-M03`).

### S27 — `[MIGRATION 2/3]` Lab Order `work_item_id` FK, Legacy Link Backfill & Optional Data (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/migration-lab-order-work-item-fk` · **Deps:** `S26` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** **YES**
- **Exact Matrix Items (5):** `G12-M01` (Add real FK from lab order to work item), `G12-M02` (Add exact legacy migration support), `G12-M03` (Stop using note-string linkage for new data), `G12-M07` (Allow missing optional lab data), `G4-M08` (Backfill exact lab relationships).
- **Schema & Migration Specification (`R03`):**
  1. Create Alembic revision revising `S26` head:
     - Add nullable `work_item_id INTEGER REFERENCES clinical_work_items(id) ON DELETE SET NULL` to `lab_orders` (`backend/models/clinical.py:326-360`).
     - Add index `ix_lab_orders_tenant_work_item` on `(tenant_id, work_item_id)`.
     - On PostgreSQL, install `trg_lab_orders_work_item_id_parent_tenant` (`dentix_assert_parent_tenant('clinical_work_items', 'work_item_id', 'true')`) and `trg_lab_orders_work_item_id_parent_patient` (`dentix_assert_parent_patient('clinical_work_items', 'work_item_id', 'true')`).
  2. Update `backend/scripts/preflight_migrations.py` (`CHILD_TENANT_RELATIONSHIPS` & `CLINICAL_G1_DIRECT_PARENT_PATIENT_RELATIONSHIPS`) in lockstep.
  3. Extend `scripts/backfill_clinical_work_items.py` (`G4-M08`, `G12-M02`) using `resolve_exact_lab_link` (`backend/clinical/legacy_mapping.py:1109`) to populate `lab_orders.work_item_id` when an exact `[LAB_ORDER:<id>]` token exists.
  4. Update `backend/schemas/clinical.py` (`LabOrderCreate` / `LabOrder`) to accept optional `work_item_id` and allow missing optional `shade`/`material`/`tooth_number` (`G12-M03`, `G12-M07`).

---

### S28 — Lab Requirement Definition, Ready Trigger, One-Tap Handoff & Non-Duplicating Billing (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/lab-handoff-decoupled-billing` · **Deps:** `S20`, `S27` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (6):** `G12-M04` (Create lab requirement definition), `G12-M05` (Add lab-ready trigger), `G12-M06` (Add one-tap lab handoff sheet), `G12-M08` (Create lab order without creating duplicate treatment), `G12-M09` (Decouple lab price from synthetic treatment creation), `G12-M16` (Add handoff idempotency).
- **Goal & Decisions:** (1) Define lab requirement metadata on prosthetic catalog procedures (`PROS_CROWN`, `PROS_BRIDGE`, `IMPLANT_CROWN`, `PROS_DENTURE` in `backend/clinical/catalog.py` / `backend/clinical/workflow_templates.py`, `G12-M04`) and trigger a `"Lab Handoff Ready"` state when the preparation/impression step completes (`G12-M05`). (2) Add `POST /api/v1/patients/{patient_id}/clinical-work-items/{work_item_id}/lab-handoff` and a 1-tap `LabHandoffSheet.jsx` drawer (`G12-M06`) that creates a `models.LabOrder` linked via `work_item_id` **without** creating any synthetic `models.Treatment` row (`G12-M08`, `G12-M09`) and enforces idempotency so double-submitting returns the existing `LabOrder` (`G12-M16`).

### S29 — Lab Status Mapping, Work-Item Badge Notification & Duplicate-Billing Regression (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/lab-status-sync-and-badges` · **Deps:** `S28` · **Size:** `M` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (5):** `G12-M10` (Add lab status mapping), `G12-M11` (Reflect lab state in work item), `G12-M12` (Prevent auto-complete when lab is ready), `G12-M13` (Add shade/material sync rules), `G12-M15` (Add duplicate-billing regression test).
- **Goal & Decisions:** Apply **D4**: Real `LabOrder.status` values used by `backend/routers/laboratories.py` and `backend/services/lab_service.py` are `pending`, `in_progress`, and `completed` (free string column, default `"pending"`). Map `LabOrder.status` (`G12-M10`) to a read-only `lab_status` indicator on the linked `ClinicalWorkItem` summary (`G12-M11`): show the `"Lab Ready"` badge **only** when `LabOrder.status == "completed"`; any other status string (`"pending"`, `"in_progress"`, or custom strings) is mapped as `unmapped` (shown neutral in the UI, never an error). **NEVER** auto-transition `ClinicalWorkItem.status` to `completed` (`G12-M12` — it remains `active`). Sync `shade`/`material` updates between the work item observation and the open lab order (`G12-M13`), and add regression tests proving lab order creation + delivery adds `0` duplicate patient treatment charges (`G12-M15`). Closes Phase `G12`.

### S30 — Point-of-Care Material Suggestion, Session Deduction & Cost Aggregation (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/care-session-material-consumption` · **Deps:** `S20`, `S26` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (6):** `G13-M04` (Create material suggestion service), `G13-M05` (Prevent stock deduction at plan creation), `G13-M06` (Deduct at actual use point), `G13-M07` (Support different materials per session), `G13-M08` (Preserve divisible-material logic), `G13-M09` (Aggregate work-item material cost).
- **Goal & Decisions:** (1) Create `MaterialSuggestionService` suggesting materials by procedure code and step (`G13-M04`). (2) Enforce that creating/accepting a `ClinicalTreatmentPlan` or `proposed`/`planned` `ClinicalWorkItem` deducts **zero** inventory (`G13-M05`). (3) Deduct stock and record `TreatmentMaterialUsage` (linked via `care_session_id` and `work_item_id` from `S26`) only when a `CareSession` records actual material consumption (`G13-M06`), supporting distinct materials across Session 1 vs Session 2 of a multi-visit work item (`G13-M07`), preserving divisible-material weight calculations (`G13-M08`), and exposing aggregated material cost across all sessions of a `ClinicalWorkItem` (`G13-M09`).

### S31 — Inventory Migration Invariance & Multi-Visit Endo Material Scenario Tests (`EXPAND JUST-IN-TIME`)
- **Branch:** `test/inventory-care-session-scenarios` · **Deps:** `S30` · **Size:** `S` · **Risk:** `NORMAL` · **Migration:** `No`
- **Exact Matrix Items (2):** `G13-M10` (Add migration invariance test), `G13-M11` (Add endo material scenario test).
- **Goal & Decisions:** Add automated test suites proving (1) all pre-existing `TreatmentMaterialUsage` rows (`treatment_id` populated, `care_session_id=None`) retain identical `quantity_used` and `cost_calculated` (`G13-M10`), and (2) a 2-session RCT work item deducts irrigants/files in Session 1 and gutta-percha/sealer in Session 2 with exact work-item material cost aggregation (`G13-M11`). Closes Phase `G13`.

---

### S32 — `[MIGRATION 3/3]` Billing Policy Model & `clinical_charges` Ledger Table (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/migration-clinical-charges-table` · **Deps:** `S27` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** **YES**
- **Exact Matrix Items (2):** `G14-M01` (Define billing policy model), `G14-M04` (Design `clinical_charges`).
- **Schema & Migration Specification (`D1`, `R03`, `R05`):**
  1. Add `ClinicalCharge` model (`__tablename__ = "clinical_charges"`) in `backend/models/clinical_core.py` (or `backend/models/financial.py`) and create an Alembic revision revising `S27` head:
     - Columns: `id` (PK), `tenant_id` (FK `tenants.id`, NOT NULL), `patient_id` (FK `patients.id`, NOT NULL), `work_item_id` (FK `clinical_work_items.id`, NOT NULL), `care_session_id` (FK `care_sessions.id`, nullable), `doctor_id` (FK `users.id`, nullable), `legacy_treatment_id` (FK `treatments.id`, nullable, for parity mapping), `amount` (`Numeric(14, 2)`, NOT NULL, `>= 0`), `discount` (`Numeric(14, 2)`, NOT NULL, default `0.00`, `>= 0`, `<= amount`), `status` (`String(32)`, NOT NULL, default `'pending'`, `IN ('pending', 'invoiced', 'voided')`), `notes` (`Text`, nullable), `version_id` (`Integer`, default `1`), `created_at`, `updated_at`.
     - Partial unique index or unique constraint preventing duplicate active (`status != 'voided'`) charges for the same `(tenant_id, work_item_id)`.
     - On PostgreSQL: `ENABLE/FORCE ROW LEVEL SECURITY`, `clinical_charges_tenant_policy`, `dentix_assert_parent_tenant` triggers for `patient_id`, `work_item_id`, `care_session_id`, `doctor_id`, and `dentix_assert_parent_patient` triggers for `work_item_id` and `care_session_id`.
  2. Update `backend/scripts/preflight_migrations.py` (`RLS_TABLES`, `CHILD_TENANT_RELATIONSHIPS`, `CLINICAL_G1_DIRECT_PARENT_PATIENT_RELATIONSHIPS`) in lockstep.
- **Production-Snapshot Rehearsal Note:** Rehearse on a restored staging PostgreSQL dump (`python -m backend.scripts.preflight_migrations`) before merge.

### S33 — Pending Clinical Charge Projection, Reception Invoice Action & Flagged Finance Read (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/clinical-charges-projection-reception` · **Deps:** `S32` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (4):** `G14-M02` (Keep old finance source authoritative during shadow mode), `G14-M03` (Add work-item billing projection), `G14-M05` (Preserve payments unchanged), `G14-M12` (Cut finance reads only behind flag).
- **Goal & Decisions:** Apply **D1**:
  1. When a native `ClinicalWorkItem` (`kind='procedure'`) transitions to `completed` (or its finishing `CareSession` completes) on a tenant with `clinical_vnext_native_writes` enabled, create a `ClinicalCharge` row with `status='pending'` and fee resolved from the patient's price list / procedure catalog (`G14-M03`).
  2. Expose reception endpoints (`GET /api/v1/patients/{patient_id}/clinical-charges` requiring `Permission.RECEIVABLE_READ` and `POST /api/v1/patients/{patient_id}/clinical-charges/{charge_id}/approve-invoice` requiring `Permission.FINANCIAL_WRITE` or `Permission.PAYMENT_CREATE`) so reception reviews pending clinical charges and confirms invoicing (`D1`).
  3. **Authoritative Finance Rule (`G14-M02`, `G14-M05`, `G14-M12`):** Introduce feature flag `FEATURE_FLAG_CLINICAL_FINANCE_READS = "clinical_vnext_finance_reads"` (default **OFF**). While OFF (including during `LEGACY_ONLY` and `SHADOW` modes), `backend/crud/billing.py`, `reporting.py`, `dashboard.py`, and `payments.py` read exclusively from legacy `models.Treatment` and `models.Payment`.

### S34 — Shadow Finance Calculator & Per-Patient / Per-Tenant Financial Parity (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/shadow-finance-parity-calculator` · **Deps:** `S02`, `S33` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (3):** `G14-M06` (Create shadow calculator), `G14-M07` (Run per-patient parity), `G14-M08` (Run per-tenant parity).
- **Goal & Decisions:** Build `FinanceParityService` (`backend/services/finance_parity_service.py` (new)) and super-admin endpoints (`GET /api/v1/admin/finance-parity/{tenant_id}` and `GET /api/v1/admin/finance-parity/{tenant_id}/patients/{patient_id}`):
  - Computes legacy net charges `SUM(Treatment.cost - Treatment.discount)` vs shadow VNext charges (`ClinicalCharge` + backfilled work-item fee projection), payment totals (`SUM(Payment.amount)`), and net receivable balance per patient (`G14-M07`) and aggregated per tenant (`G14-M08`).
  - Strictly read-only (`0` writes).

### S35 — Legacy Lab Double-Charge Detector, Doctor-Share Compatibility & Finance Regression Suite (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/finance-lab-double-charge-and-regression` · **Deps:** `S29`, `S34` · **Size:** `M` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (5):** `G14-M09` (Detect legacy lab double-charge cases), `G14-M10` (Add deterministic remediation workflow), `G14-M11` (Add doctor-share compatibility tests), `G14-M13` (Keep payments stable), `G14-M14` (Add financial regression suite).
- **Goal & Decisions:** (1) Add a deterministic detector (`G14-M09`) and admin review/remediation report (`G14-M10`) identifying patients where a `LabOrder` (`price_to_patient > 0`) AND a synthetic `Treatment` on the same tooth/date both billed the patient. (2) Add doctor-commission / revenue-share compatibility tests (`G14-M11`) against `backend/routers/accounting.py` and `accounting_decimal.py`, payment stability tests (`G14-M13`), and the full financial regression suite (`G14-M14`). Closes Phase `G14`.

### S36 — Controlled Rollout Toggle, Read-Only VNext Mode & Legacy Compatibility Hardening (`EXPAND JUST-IN-TIME`)
- **Branch:** `feat/clinical-rollout-toggle-hardening` · **Deps:** `S21`, `S24`, `S25`, `S31`, `S35` · **Size:** `S` · **Risk:** `HIGH_RISK` · **Migration:** `No`
- **Exact Matrix Items (4):** `G16-M01` (Enable internal tenant only), `G16-M02` (Roll out read-only VNext), `G16-M08` (Add tenant rollback toggle), `G16-M10` (Keep legacy compatibility during rollout).
- **Goal & Decisions:** Add end-to-end rollout mode verification and admin rollback helper (`POST /api/v1/admin/clinical-rollout/{tenant_id}/rollback` that atomically disables `clinical_vnext_native_writes`, `clinical_vnext_primary`, and `clinical_vnext_shadow` for a tenant, returning it to `LEGACY_ONLY` in 1 call, `G16-M08`). Verify `G16-M01` (single internal tenant activation without affecting other tenants), `G16-M02` (`VNEXT_PRIMARY` read-only mode with `clinical_vnext_native_writes=False`), and `G16-M10` (legacy `Treatment` writes continue syncing into native tables while compatibility mode is active). Update `docs/product/ODONTOGRAM_IMPLEMENTATION_STATUS.md` for all in-release phases.
