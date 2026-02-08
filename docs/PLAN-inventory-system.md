# Smart Clinic Inventory System - Implementation Plan

## 🧠 Strategic Overview

This plan details the implementation of a comprehensive Inventory Management System for Smart Clinic. It builds upon the user's initial proposal, adding necessary technical constraints for stability, multi-tenancy, and scalability.

### 🎯 Objectives
1.  **Compliance**: Legal tracking of medical supplies (Expiry, Batch).
2.  **Accuracy**: Real-time stock visibility across Main and Clinic sub-warehouses.
3.  **Efficiency**: Automated consumption logic (FIFO) and smart learning for divisible materials.
4.  **Cost Control**: Exact per-procedure cost analysis.

---

## 🛠️ Architecture & Concepts (Refined)

### 1. Multi-Tenancy (Critical Addition)
*   **Requirement**: All inventory tables must include `tenant_id` to ensure data isolation between clinics using the SaaS platform.
*   **Implementation**: Add `tenant_id` ForeignKey to `Materials`, `Batches`, `Warehouses`, `StockItems`, etc.

### 2. Unit Strategy (Base Unit)
*   **Proposal**: To avoid complex conversions during usage, all stock is tracked in **Base Units** (Smallest Consumable Unit).
    *   *Example*: Anesthesia is bought as "Box of 50". It is entered into stock as "50 Ampoules".
    *   *Benefit*: The clinic consumes "1 Ampoule", matching the stock record perfectly.
*   **Action**: `Materials` table will have a `packaging_ratio` (default 1) to help UI convert "Boxes" to "Units" during receiving, but DB stores "Units".

### 3. Warehouse Hierarchy
*   **Main Warehouse**: The central store for the tenant. Receives shipments.
*   **Clinic/Sub Warehouse**: The operational stock at the chair-side or room level.
*   **Transfer**: Movement from Main -> Clinic is a `StockTransfer` transaction.

### 4. Divisible vs. Non-Divisible
*   **Non-Divisible**: Consumed as whole units (e.g., Gloves, Burrs, Ampoules).
*   **Divisible**: Consumed by weight/volume (e.g., Composite, Bond).
    *   **Session Logic**: A "Session" is a tracked instance of an open container (e.g., an open Bond bottle).
    *   **Consumption**: Usage is estimated/calculated from the active Session.

---

## 🗄️ Database Schema (New Models)

File: `backend/app/models/inventory.py`

### 1. `Warehouse`
| Column | Type | Notes |
| :--- | :--- | :--- |
| id | Integer | PK |
| tenant_id | Integer | FK |
| name | String | "Main Supply", "Room 1 Cabinet" |
| type | Enum | MAIN, CLINIC |

### 2. `Material`
| Column | Type | Notes |
| :--- | :--- | :--- |
| id | Integer | PK |
| tenant_id | Integer | FK |
| name | String | "3M Composite A2" |
| type | Enum | DIVISIBLE, NON_DIVISIBLE |
| base_unit | String | "g", "ml", "ampoule", "box" |
| alert_threshold | Integer | Low stock warning level |

### 3. `Batch`
| Column | Type | Notes |
| :--- | :--- | :--- |
| id | Integer | PK |
| material_id | Integer | FK |
| tenant_id | Integer | FK |
| batch_number | String | From Supplier |
| expiry_date | Date | **CRITICAL** for FIFO |
| supplier | String | |
| cost_per_unit | Float | For financial reporting |

### 4. `StockItem` (The Core Ledger)
| Column | Type | Notes |
| :--- | :--- | :--- |
| id | Integer | PK |
| warehouse_id | Integer | FK |
| batch_id | Integer | FK |
| quantity | Float | Current balance (Base Units) |
| tenant_id | Integer | FK |

### 5. `MaterialSession` (For Divisible)
| Column | Type | Notes |
| :--- | :--- | :--- |
| id | Integer | PK |
| stock_item_id | Integer | FK (Links to specific Batch in specific Warehouse) |
| opened_at | DateTime | |
| status | Enum | ACTIVE, CLOSED |
| remaining_est | Float | Estimated remaining amount |

### 6. `StockMovement` (Audit Trail)
| Column | Type | Notes |
| :--- | :--- | :--- |
| id | Integer | PK |
| stock_item_id | Integer | FK |
| change_amount | Float | +ve for add, -ve for remove |
| reason | String | "Purchase", "Transfer", "Usage", "Expired" |
| reference_id | String | Link to Procedure/Treatment ID |

---

## 🔄 Logic & Workflows

### A. FIFO Consumption (First-In, First-Out)
When a user consumes `Material X`:
1.  Find all `StockItems` for `Material X` in current `Warehouse`.
2.  Sort by `Batch.expiry_date` ASC.
3.  Deduct quantity from the first batch. If insufficient, move to next batch.
4.  **Error prevention**: If explicit Batch is selected (optional), use that. Default is auto-FIFO.

### B. Smart Learning (Phase 2)
*   **Data Collection**: Every time a session is closed (e.g., Composite finished), log: `Total Usage / Number of Procedures`.
*   **Update**: Refine "Average Usage per Procedure" in `MaterialDefaults`.

---

## 📅 Implementation Roadmap

### Phase 1: Foundation (Backend)
1.  **Models**: Create `backend/app/models/inventory.py`.
2.  **Migrations**: Generate and apply Alembic migrations.
3.  **CRUD APIs**: Create `backend/app/routers/inventory.py` (Materials, Batches, Warehouses).
4.  **Stock Logic**: Service layer for `add_stock`, `transfer_stock`, `consume_stock`.

### Phase 2: Core UI (Frontend)
1.  **Inventory Dashboard**: View stock levels, filtering by warehouse.
2.  **Receiving (In-bound)**: Form to add new Batches (Material + Batch # + Expiry).
3.  **Transfer UI**: Move stock from Main -> Clinic.

### Phase 3: Clinical Integration
1.  **Doctor's View**: "Consume Material" button or auto-deduct based on Procedure.
2.  **Session Management**: UI to "Open New Bottle" or "Finish Bottle".
3.  **Consumption Logic**: Backend trigger to deduct stock when Procedure is completed (if mapped).

### Phase 4: Intelligence & Reports
1.  **Expiry Alerts**: Background job to check dates.
2.  **Cost Reports**: "Profitability per Procedure" reports using actual batch costs.

---

## ✅ Immediate Next Steps
1.  Approve this plan.
2.  Begin **Phase 1: Foundation (Backend)**.
