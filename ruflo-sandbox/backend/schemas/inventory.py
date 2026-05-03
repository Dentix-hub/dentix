from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class WarehouseType(str, Enum):
    MAIN = "MAIN"
    CLINIC = "CLINIC"


class MaterialType(str, Enum):
    DIVISIBLE = "DIVISIBLE"
    NON_DIVISIBLE = "NON_DIVISIBLE"


# --- MATERIAL CATEGORY ---
class MaterialCategoryCreate(BaseModel):
    name_en: str
    name_ar: str
    default_type: str = "DIVISIBLE"
    default_unit: str = "g"


class MaterialCategoryOut(BaseModel):
    id: int
    name_en: str
    name_ar: str
    default_type: str = "DIVISIBLE"
    default_unit: str = "g"

    class Config:
        from_attributes = True


# --- WAREHOUSE ---
class WarehouseBase(BaseModel):
    name: str = Field(..., title="Warehouse Name")
    type: WarehouseType = Field(default=WarehouseType.MAIN)


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseRead(WarehouseBase):
    id: int
    tenant_id: int

    class Config:
        from_attributes = True


# --- MATERIAL ---
class MaterialBase(BaseModel):
    name: str
    type: str  # Was MaterialType, but DB has categories like 'Restorative'
    base_unit: str
    alert_threshold: int = 10
    packaging_ratio: float = 1.0
    standard_price: Optional[float] = 0.0
    category_id: Optional[int] = None
    brand: Optional[str] = None


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None  # Relaxed to match MaterialBase
    base_unit: Optional[str] = None
    alert_threshold: Optional[int] = None
    packaging_ratio: Optional[float] = None
    standard_price: Optional[float] = None
    category_id: Optional[int] = None
    brand: Optional[str] = None


class MaterialRead(MaterialBase):
    id: int
    tenant_id: int
    category: Optional[MaterialCategoryOut] = None

    class Config:
        from_attributes = True


# --- BATCH ---
class BatchBase(BaseModel):
    batch_number: str
    expiry_date: date
    supplier: Optional[str] = None
    cost_per_unit: float = 0.0


class BatchCreate(BatchBase):
    material_id: int


class BatchRead(BatchBase):
    id: int
    material_id: int
    tenant_id: int
    created_at: datetime

    material: Optional[MaterialRead] = None

    class Config:
        from_attributes = True


# --- STOCK ITEM ---
class StockItemBase(BaseModel):
    warehouse_id: int
    batch_id: int
    quantity: float


class StockItemRead(StockItemBase):
    id: int
    tenant_id: int
    batch: Optional[BatchRead] = None
    warehouse: Optional[WarehouseRead] = None

    class Config:
        from_attributes = True


# --- MATERIAL SESSION ---
class MaterialSessionBase(BaseModel):
    stock_item_id: int
    status: str = "ACTIVE"
    remaining_est: float = 1.0


class MaterialSessionCreate(MaterialSessionBase):
    pass


class MaterialSessionRead(MaterialSessionBase):
    id: int
    opened_at: datetime
    doctor_id: Optional[int] = None
    stock_item: Optional[StockItemRead] = None

    class Config:
        from_attributes = True


# --- COMPOSITE READ MODELS (For Dashboard) ---
class MaterialStockSummary(BaseModel):
    material_id: int
    material_name: str
    material_type: str
    brand: Optional[str] = None
    total_quantity: float
    unit: str
    alert_status: str  # OK, LOW, CRITICAL
    batches_count: int
    packaging_ratio: Optional[float] = 1.0
    standard_price: Optional[float] = 0.0


class ConsumptionItem(BaseModel):
    material_id: int
    quantity: float
    batch_id: Optional[int] = None


class StockReceiveRequest(BaseModel):
    material_id: int
    warehouse_id: int
    quantity: float
    batch: BatchBase


class StockTransferRequest(BaseModel):
    stock_item_id: int
    target_warehouse_id: int
    quantity: float


class StockMovementRead(BaseModel):
    id: int
    stock_item_id: int
    change_amount: float
    reason: str
    performed_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class SessionCloseRequest(BaseModel):
    total_consumed: Optional[float] = (
        None  # Optional - will be auto-calculated from treatments if not provided
    )


class ProcedureWeightBase(BaseModel):
    procedure_id: int
    material_id: Optional[int] = None
    category_id: Optional[int] = None
    weight: float = 1.0


class ProcedureWeightUpdate(BaseModel):
    procedure_name: str  # Use name for easier UI mapping
    material_id: Optional[int] = None
    category_id: Optional[int] = None
    weight: float


class ProcedureName(BaseModel):
    name: str

    class Config:
        from_attributes = True


class ProcedureWeightRead(ProcedureWeightBase):
    id: int
    tenant_id: Optional[int] = None
    current_average_usage: float = 0.0
    sample_size: int = 0
    procedure: Optional[ProcedureName] = None
    category: Optional[MaterialCategoryOut] = None

    class Config:
        from_attributes = True


# --- TREATMENT MATERIAL USAGE ---
class TreatmentMaterialUsageCreate(BaseModel):
    material_id: int
    session_id: Optional[int] = None
    weight_score: float = 1.0
    quantity_used: Optional[float] = None
    is_manual_override: bool = False


class TreatmentMaterialUsageOut(BaseModel):
    id: int
    treatment_id: int
    material_id: int
    session_id: Optional[int] = None
    weight_score: float
    quantity_used: Optional[float] = None
    cost_calculated: Optional[float] = None
    is_manual_override: bool
    tenant_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- SUGGESTED MATERIAL (Resolution Engine Response) ---
class SuggestedMaterial(BaseModel):
    category_id: int
    category_name_en: str
    category_name_ar: str
    material_id: Optional[int] = None
    material_name: Optional[str] = None
    material_type: str  # DIVISIBLE / NON_DIVISIBLE
    base_unit: str
    weight: float = 1.0
    suggested_quantity: Optional[float] = None
    confidence: float = 0.8
    reason: str = "Standard Protocol"
    has_active_session: bool = False
    session_id: Optional[int] = None
    brand: Optional[str] = None
    alternatives: List["SuggestedMaterialAlternative"] = []


class SuggestedMaterialAlternative(BaseModel):
    id: int
    name: str
    brand: Optional[str] = None
    in_stock: bool = True
