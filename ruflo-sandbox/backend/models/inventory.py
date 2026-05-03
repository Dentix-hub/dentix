from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, Date, Float, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(String, default="MAIN")  # MAIN, CLINIC

    stock_items = relationship("StockItem", back_populates="warehouse")
    tenant = relationship("Tenant")


class MaterialCategory(Base):
    __tablename__ = "material_categories"

    id = Column(Integer, primary_key=True, index=True)
    name_en = Column(String, nullable=False, unique=True)
    name_ar = Column(String, nullable=False)
    default_type = Column(String, default="DIVISIBLE")  # DIVISIBLE / NON_DIVISIBLE
    default_unit = Column(String, default="g")

    materials = relationship("Material", back_populates="category")


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # DIVISIBLE, NON_DIVISIBLE
    base_unit = Column(String, nullable=False)  # e.g., "ml", "g", "ampoule"
    alert_threshold = Column(Integer, default=10)
    standard_price = Column(
        Float, default=0.0, nullable=True
    )  # Reference Cost (Market Price)

    category_id = Column(Integer, ForeignKey("material_categories.id"), nullable=True)
    brand = Column(String, nullable=True)  # e.g. "3M Filtek Z350"

    # Optional: packaging info for UI conversions (e.g. 1 Box = 50 Ampoules)
    packaging_ratio = Column(Float, default=1.0)

    category = relationship("MaterialCategory", back_populates="materials")
    batches = relationship("Batch", back_populates="material")
    tenant = relationship("Tenant")


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(
        Integer, ForeignKey("materials.id"), nullable=False, index=True
    )
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    batch_number = Column(String, nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    supplier = Column(String, nullable=True)
    cost_per_unit = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    material = relationship("Material", back_populates="batches")
    stock_items = relationship("StockItem", back_populates="batch")
    tenant = relationship("Tenant")


class StockItem(Base):
    __tablename__ = "stock_items"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(
        Integer, ForeignKey("warehouses.id"), nullable=False, index=True
    )
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    quantity = Column(Float, default=0.0)  # In Base Units

    warehouse = relationship("Warehouse", back_populates="stock_items")
    batch = relationship("Batch", back_populates="stock_items")
    sessions = relationship("MaterialSession", back_populates="stock_item")
    movements = relationship("StockMovement", back_populates="stock_item")
    tenant = relationship("Tenant")


class MaterialSession(Base):
    """
    Tracks usage of opened DIVISIBLE materials (e.g. opened Bond bottle).
    """

    __tablename__ = "material_sessions"

    id = Column(Integer, primary_key=True, index=True)
    stock_item_id = Column(
        Integer, ForeignKey("stock_items.id"), nullable=False, index=True
    )
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="ACTIVE")  # ACTIVE, CLOSED
    remaining_est = Column(
        Float, default=1.0
    )  # Estimated percentage or amount remaining (0.0 - 1.0 or units)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Smart Learning Fields
    closed_at = Column(DateTime, nullable=True)
    total_amount_consumed = Column(
        Float, nullable=True
    )  # Actual amount consumed when closed

    stock_item = relationship("StockItem", back_populates="sessions")
    doctor = relationship("User")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    stock_item_id = Column(
        Integer, ForeignKey("stock_items.id"), nullable=False, index=True
    )
    change_amount = Column(Float, nullable=False)  # +ve or -ve
    reason = Column(
        String, nullable=False
    )  # PURCHASE, TRANSFER, USAGE, EXPIRED, ADJUSTMENT
    reference_id = Column(String, nullable=True)  # Link to Treatment ID or Order ID
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    stock_item = relationship("StockItem", back_populates="movements")
    user = relationship("User")


class ProcedureMaterialWeight(Base):
    """
    Smart Inventory: Relative weights for procedure complexity.
    Example: Class I = 1.0, Class II = 1.5
    """

    __tablename__ = "procedure_material_weights"

    id = Column(Integer, primary_key=True, index=True)
    procedure_id = Column(
        Integer, ForeignKey("procedures.id"), nullable=False, index=True
    )
    material_id = Column(
        Integer, ForeignKey("materials.id"), nullable=True, index=True
    )
    category_id = Column(
        Integer, ForeignKey("material_categories.id"), nullable=True
    )
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)  # NULL = global default

    weight = Column(Float, default=1.0)
    current_average_usage = Column(Float, default=0.0)  # Learned average (e.g. 0.23g)

    # Optional: Confidence level or sample size
    sample_size = Column(Integer, default=0)

    # Relationships
    material = relationship("Material")
    category = relationship("MaterialCategory")
    procedure = relationship("Procedure")


class MaterialLearningLog(Base):
    """
    Audit trail for how the system calculated usage.
    """

    __tablename__ = "material_learning_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("material_sessions.id"), nullable=False)

    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    total_consumed = Column(Float, nullable=False)  # e.g. 5.0g

    # JSON Details
    calculation_data = Column(Text, nullable=True)
    # {
    #   "treatments_count": 5,
    #   "total_weight": 34.5,
    #   "unit_weight_value": 0.145,
    #   "procedure_breakdown": [...]
    # }

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TreatmentMaterialUsage(Base):
    """Links each treatment to the materials used."""

    __tablename__ = "treatment_material_usages"

    id = Column(Integer, primary_key=True, index=True)
    treatment_id = Column(Integer, ForeignKey("treatments.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("material_sessions.id"), nullable=True)

    weight_score = Column(Float, default=1.0)       # Relative weight for this procedure
    quantity_used = Column(Float, nullable=True)     # Calculated AFTER session closes (for DIVISIBLE)
    cost_calculated = Column(Float, nullable=True)   # Back-calculated cost

    is_manual_override = Column(Boolean, default=False)  # Doctor adjusted manually

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    treatment = relationship("Treatment")
    material = relationship("Material")
    session = relationship("MaterialSession")
