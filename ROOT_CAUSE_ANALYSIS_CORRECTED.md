# Corrected Root Cause Analysis: Inventory Cost Reports Returning Zero or Empty Data

## Executive Summary

The original report is directionally correct: inventory cost reports can return zero because the reporting/learning path depends on `TreatmentMaterialUsage.quantity_used`, and that field is not reliably populated.

However, the deeper root cause is broader than `session_id` being `NULL` in `POST /treatments/{id}/materials`.

The main treatment save flow used by the frontend sends materials inside `POST /treatments` / `PUT /treatments/{id}` as `consumedMaterials`. That flow consumes or validates stock, but it does not create linked `TreatmentMaterialUsage` rows for the learning/reporting engine. In addition, the frontend strips `session_id` and `weight_score` before saving the treatment, so even when the material suggestion UI has the right data, the backend does not receive it through the main treatment endpoint.

Result: stock/session operations may appear to work, but the learning table that cost reports depend on is empty, incomplete, or contains rows with `session_id = NULL` and `quantity_used = NULL`.

---

## Corrected Root Cause

There are two related data-flow breaks:

1. The frontend's main treatment save path removes material metadata:
   - `session_id`
   - `weight_score`
   - `is_manual_override`
   - `material_type`

2. The backend's main treatment create/update service consumes stock from `consumedMaterials`, but does not persist matching `TreatmentMaterialUsage` rows.

The endpoint `POST /treatments/{id}/materials` can create `TreatmentMaterialUsage`, but the current frontend treatment modal primarily uses `POST /treatments` / `PUT /treatments/{id}`, not that separate materials endpoint.

---

## Evidence From Code

### 1. Frontend Collects Correct Session Data

File: `frontend/src/features/inventory/MaterialConsumptionPanel.jsx`

The material suggestion panel stores `session_id` from the backend suggestion response:

```jsx
initial[sugg.category_id] = {
    material_id: materialId,
    weight: sugg.weight,
    quantity: sugg.material_type === 'NON_DIVISIBLE' ? 1 : null,
    material_type: sugg.material_type,
    has_active_session: sugg.has_active_session,
    session_id: sugg.session_id,
    is_manual_override: false
};
```

So the UI layer can hold the active session linkage.

### 2. Treatment Modal Drops That Data Before Save

File: `frontend/src/shared/ui/modals/TreatmentModal.jsx`

The panel passes `session_id` and `weight_score` into `consumedMaterials`:

```jsx
const formatted = materials.map(m => ({
    material_id: m.material_id,
    quantity: m.material_type === 'NON_DIVISIBLE' ? m.quantity : m.weight,
    weight_score: m.weight,
    is_manual_override: m.is_manual_override,
    session_id: m.session_id,
    category_id: m.category_id
}));
```

But `handleSave()` then sanitizes `consumedMaterials` down to only:

```jsx
const cleanedMaterials = (consumedMaterials || [])
    .map(m => ({
        material_id: m.material_id || m.id,
        quantity: Number.isFinite(parseFloat(m.quantity)) ? parseFloat(m.quantity) : 1
    }))
    .filter(m => m.quantity > 0 && m.material_id);
```

This removes the fields needed by the learning/reporting path.

### 3. Main Frontend Save Uses `/treatments`, Not `/treatments/{id}/materials`

File: `frontend/src/api/treatments.js`

```js
export const createTreatment = (data) => api.post('/api/v1/treatments', data);
export const updateTreatment = (id, data) => api.put(`/api/v1/treatments/${id}`, data);
```

The separate API helper exists:

```js
export const saveTreatmentMaterials = (treatmentId, materials) =>
    api.post(`/api/v1/treatments/${treatmentId}/materials`, materials);
```

But it is not the main treatment save path used by `TreatmentModal`.

### 4. Backend Treatment Schema Cannot Accept Session Metadata

File: `backend/schemas/clinical.py`

```python
class ConsumedMaterialItem(BaseModel):
    material_id: int
    quantity: float
```

This schema does not include:

- `session_id`
- `weight_score`
- `is_manual_override`
- `material_type`

Even if the frontend sent those fields, the current typed shape does not model them for treatment create/update.

### 5. Backend Treatment Service Consumes Stock Only

File: `backend/services/treatment_service.py`

The create/update flow calls:

```python
self.consume_treatment_stock(
    created_treatment.id,
    treatment_data.consumedMaterials or [],
    patient_id=treatment_data.patient_id
)
```

`consume_treatment_stock()` calls `inventory_service.consume_stock()`, but does not create `TreatmentMaterialUsage`.

Therefore, the learning/reporting table can remain empty even though the treatment saves successfully.

### 6. The Separate Materials Endpoint Can Save Learning Rows, But Is Not Defensive

File: `backend/routers/treatments.py`

```python
usage = inv_models.TreatmentMaterialUsage(
    treatment_id=treatment_id,
    material_id=item.material_id,
    session_id=item.session_id,
    weight_score=item.weight_score,
    quantity_used=item.quantity_used,
    is_manual_override=item.is_manual_override,
    tenant_id=tenant_id,
)
```

This endpoint accepts `session_id = None`. If it is used without a session id, it creates orphaned records that cannot be matched during session close.

### 7. Learning Service Requires `session_id`

File: `backend/services/inventory_learning_service.py`

```python
treatment_usages = (
    self.db.query(inv_models.TreatmentMaterialUsage)
    .filter(
        inv_models.TreatmentMaterialUsage.session_id == session_id,
        inv_models.TreatmentMaterialUsage.material_id == material_id,
    )
    .all()
)
```

Later, it only updates records found in `usage_map`:

```python
usage_rec = usage_map.get(t.id)
if not usage_rec:
    continue

usage_rec.quantity_used = actual_quantity
```

So no linked usage row means no `quantity_used`, no cost calculation, and no reliable learning update.

### 8. Cost Engine Depends On Learning Data

File: `backend/services/cost_engine.py`

The procedure cost report first tries `ProcedureMaterialWeight.current_average_usage`, then falls back to `TreatmentMaterialUsage.quantity_used`:

```python
actual_usage_stats = (
    self.db.query(func.avg(TreatmentMaterialUsage.quantity_used))
    .filter(
        TreatmentMaterialUsage.material_id == w.material_id,
        TreatmentMaterialUsage.tenant_id == self.tenant_id,
        TreatmentMaterialUsage.quantity_used.isnot(None),
    )
    .scalar()
)
```

If neither source has data, `actual_usage` becomes `0.0`, and material cost appears as zero.

---

## Important Distinction: Which Reports Are Affected?

### Procedure Cost Analysis

Affected directly.

This uses `CostEngine.calculate_procedure_cost()` and depends on learning data or `TreatmentMaterialUsage.quantity_used`.

### General Procedure Cost Analysis

Affected directly.

This reuses `CostEngine.calculate_procedure_cost()` for each procedure.

### Profitability / Material COGS

Affected, but through a different mechanism.

File: `backend/services/inventory_service.py`

`get_cogs_summary()` counts only stock movements with:

```python
StockMovement.reason.in_(["USAGE", "EXPIRED"])
```

It explicitly excludes `SESSION_OPEN`.

For `DIVISIBLE` materials, opening a session deducts the full package with reason `SESSION_OPEN`. Later per-treatment usage inside an active session is virtual and does not create `USAGE` movements:

```python
if session and mat_type in ("DIVISIBLE", "REUSABLE"):
    remaining_to_consume = 0
    continue
```

Therefore, profitability material COGS can also be zero for divisible materials, even if physical stock was reduced at session open.

---

## Corrected Impact Assessment

| Area | Status | Explanation |
|---|---|---|
| Treatment save | Partially working | Treatment record saves; stock validation/consumption runs |
| Non-divisible stock deduction | Mostly working | Uses direct `USAGE` movements |
| Divisible stock deduction | Partially working | Package is deducted on `SESSION_OPEN`, but per-treatment usage is virtual |
| `TreatmentMaterialUsage` creation | Broken in main flow | Main treatment create/update does not persist learning rows |
| `session_id` linkage | Broken/incomplete | Frontend has it but strips it; separate endpoint accepts null |
| Session close learning | Broken when no linked rows | Requires `TreatmentMaterialUsage.session_id == session_id` |
| Procedure cost reports | Broken/zero | No learned usage or actual quantity data |
| Profitability material COGS | Incomplete for divisible materials | `SESSION_OPEN` excluded from COGS and virtual usage creates no `USAGE` movement |

---

## Recommended Fix

### Fix A: Preserve Material Metadata In Frontend

Update `TreatmentModal.jsx` so `cleanedMaterials` keeps:

```js
{
  material_id,
  quantity,
  session_id,
  weight_score,
  is_manual_override,
  material_type,
  category_id
}
```

Do not reduce materials to only `material_id` and `quantity`.

### Fix B: Extend Backend Schema

Update `ConsumedMaterialItem` in `backend/schemas/clinical.py`:

```python
class ConsumedMaterialItem(BaseModel):
    material_id: int
    quantity: float
    session_id: Optional[int] = None
    weight_score: float = 1.0
    is_manual_override: bool = False
    material_type: Optional[str] = None
```

### Fix C: Persist `TreatmentMaterialUsage` In Main Treatment Flow

After creating/updating a treatment, the backend should upsert usage rows for `treatment_data.consumedMaterials`.

For divisible/reusable materials:

- `session_id`: use provided value or auto-resolve active session
- `weight_score`: use provided value
- `quantity_used`: keep `None` until session close

For non-divisible materials:

- `quantity_used`: set to actual quantity immediately
- `cost_calculated`: calculate if unit cost is available

### Fix D: Make Backend Defensive

When `session_id` is missing for a divisible material, backend should try to find an active session by:

- tenant
- material
- doctor
- patient when available

If no active session exists, either:

- reject with a clear error for divisible materials, or
- save the row but mark it as unresolved and exclude it from learning until resolved

Rejecting is safer for data quality.

### Fix E: Revisit COGS For Divisible Materials

Choose one accounting rule:

1. Count `SESSION_OPEN` as COGS when package is opened.
2. Count allocated `TreatmentMaterialUsage.cost_calculated` when session closes.

Do not count both.

The current implementation excludes `SESSION_OPEN` and does not reliably create allocated treatment usage, which causes material COGS to be understated.

---

## Backfill Plan

For existing data:

1. Identify treatments with stock movements but no `TreatmentMaterialUsage`.
2. Reconstruct non-divisible usage from `StockMovement.reference_id = "TREATMENT:{id}"`.
3. For divisible materials, link treatments to sessions by:
   - treatment date between `opened_at` and `closed_at`
   - same doctor
   - same tenant
   - same material
4. Populate:
   - `session_id`
   - `weight_score` from procedure material weights or default `1.0`
   - `quantity_used` if the session is already closed and total consumption can be allocated
5. Recompute `ProcedureMaterialWeight.current_average_usage` and `sample_size`.

---

## Diagnostic Queries

### Missing Learning Rows

```sql
SELECT t.id, t.procedure, t.date
FROM treatments t
LEFT JOIN treatment_material_usages tmu ON tmu.treatment_id = t.id
WHERE t.status = 'Done'
  AND tmu.id IS NULL;
```

### Orphaned Usage Rows

```sql
SELECT id, treatment_id, material_id, session_id, quantity_used
FROM treatment_material_usages
WHERE session_id IS NULL
  AND quantity_used IS NULL;
```

### Closed Sessions With No Allocated Usage

```sql
SELECT ms.id, ms.stock_item_id, ms.opened_at, ms.closed_at
FROM material_sessions ms
LEFT JOIN treatment_material_usages tmu ON tmu.session_id = ms.id
WHERE ms.status = 'CLOSED'
GROUP BY ms.id
HAVING COUNT(tmu.id) = 0;
```

### Cost Engine Data Availability

```sql
SELECT
    material_id,
    COUNT(*) AS usage_rows,
    COUNT(quantity_used) AS rows_with_quantity,
    AVG(quantity_used) AS avg_quantity
FROM treatment_material_usages
GROUP BY material_id;
```

---

## Final Verdict

The original report is partially correct but incomplete.

Correct statement:

> Reports return zero because the treatment material learning data is not reliably persisted or linked to material sessions. The main treatment save path strips `session_id`/`weight_score` and does not create `TreatmentMaterialUsage` rows, while the learning service and cost engine depend on those rows being present and later populated with `quantity_used`.

The fix should not be frontend-only. The backend must own data integrity by persisting treatment material usage during the main treatment create/update flow and by validating or resolving `session_id` for divisible materials.
