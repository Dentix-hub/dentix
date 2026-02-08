# PLAN-smart-costing.md - Smart Costing & AI Pricing System

## Goal
Implement a precise procedure costing engine that calculates the real-time cost of medical procedures based on inventory consumption (Bill of Materials), and integrate an AI assistant to suggest optimal pricing strategies.

## User Rules & Context
- **Inventory Cost**: Track "Unit Cost" in inventory (per batch or material).
- **Procedure Cost**: Calculate `Sum(Material Weight * Unit Cost)` using existing BOM.
- **Pricing**: Hybrid approach (Cost + AI Market Analysis).
- **UX**: Proactive AI suggestions with a toggle.

## Proposed Changes

### 1. Database Schema
#### [MODIFY] Inventory Models
- **Table**: `batches` (or `materials`)
    - Verify `cost_per_unit` exists in DB models (Already in Pydantic schema).
    - *Rationale*: Different batches have different costs. We should track FIFO or Average, but starting with Batch Cost is most accurate for "Receiving".
- **Table**: `procedures` [Virtual / Calculated]
    - No strict schema change needed if calculated on fly.

#### [MODIFY] Settings
- Add `ai_pricing_enabled` (Boolean) to Tenant Settings.

### 2. Backend Logic
#### [MODIFY] `routers/inventory.py`
- Update `receive_stock` to ensure `cost_per_unit` is saved to DB.
- Store this cost in the database `Batch` table.

#### [NEW] `services/cost_engine.py`
- `calculate_procedure_cost(procedure_id)`:
    - Fetch all `ProcedureMaterialWeight` for procedure.
    - For each material, get `current_average_cost` (weighted average of active batches) or `last_purchase_price`.
    - Formula: `Total Cost = Sum(Weight * Material_Cost_Per_Base_Unit)`.

#### [MODIFY] `routers/procedures.py` (or new `routers/financials.py`)
- Add `get_procedure_financials(procedure_id)`:
    - Returns `{ cost: 100, price: 500, margin: "80%", suggested_price: 550 }`.

#### [MODIFY] `ai/intents.py`
- Add `ANALYZE_PRICING` intent.
- Tools: `get_procedure_financials`, `analyze_market_price` (AI Logic).

### 3. Frontend Implementation
#### [MODIFY] Inventory Pages
- `ReceiveStockModal`: Ensure "Cost per Unit" field is visible and sent.
- `MaterialsTable`: Show "Avg Cost".

#### [MODIFY] Procedure Details
- Add "Financial Analysis" card.
    - Cost vs Price bar chart.
    - Net Profit indicator.
- Add "AI Suggestion" Widget.
    - "⚠️ Your margin is only 10%. Market average is 40%. Suggested Price: 150 EGP."
    - "Enable/Disable" toggle for these tips.

### 4. AI & Assistant
- Train `assistant` to answer: "How much does Root Canal cost me?"
- The assistant will call `financials.get_procedure_financials`.

## Verification Plan

### Automated Tests
- `test_cost_calculation.py`:
    - Create Material A (Cost 10).
    - Link to Procedure X (Weight 5).
    - Assert Procedure Cost == 50.
- `test_ai_pricing_intent.py`:
    - Simulate "Analyze pricing for X".
    - Check tool invocation.

### Manual Verification
1. Add stock with cost.
2. Link material to procedure via BOM.
3. Check Procedure page for calculated cost.
4. Ask Chatbot: "Analyze pricing for [Procedure Name]".
