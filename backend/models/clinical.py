from datetime import timezone
from .base import (
    Base,
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    Text,
    ForeignKey,
    relationship,
    Index,
    datetime,
)
from sqlalchemy import Boolean, CheckConstraint, column, text
from rls.schemas import Permissive, ConditionArg, Command


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("idx_appointment_doctor_date", "doctor_id", "date_time"),
        Index("idx_appointment_tenant_date", "patient_id", "date_time"), # Indirect via patient join usually, but useful if denormalized or for patient history
    )

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    doctor_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )  # Multi-Doctor Support
    price_list_id = Column(
        Integer, ForeignKey("price_lists.id"), nullable=True, index=True
    )  # Multi Price List
    date_time = Column(DateTime, index=True)
    duration_minutes = Column(Integer, default=30) # Default 30 mins
    status = Column(String, default="Scheduled")
    notes = Column(Text, nullable=True)

    # Soft Delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    # Optimistic Locking: prevents double-booking race conditions
    version_id = Column(Integer, default=1, nullable=False)

    __mapper_args__ = {
        "version_id_col": version_id,
    }

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("User")

    @property
    def patient_name(self):
        return self.patient.name if self.patient else "Unknown"


class ToothStatus(Base):
    __tablename__ = "tooth_status"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    tooth_number = Column(Integer)
    condition = Column(String)
    notes = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="tooth_statuses")


class Treatment(Base):
    __tablename__ = "treatments"
    __table_args__ = (
        Index("idx_treatment_doctor_date", "doctor_id", "date"),
        Index("idx_treatment_patient_date", "patient_id", "date"),
        CheckConstraint("cost >= 0", name="ck_treatments_cost_nonnegative"),
        CheckConstraint("discount >= 0", name="ck_treatments_discount_nonnegative"),
        CheckConstraint("discount <= cost", name="ck_treatments_discount_not_above_cost"),
    )

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    tooth_number = Column(Integer, nullable=True)
    diagnosis = Column(String)
    procedure = Column(String)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    cost = Column(Numeric(14, 2), default=0.0)  # Total before discount
    discount = Column(Numeric(14, 2), default=0.0)
    date = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )
    canal_count = Column(Integer, nullable=True)
    canal_lengths = Column(String, nullable=True)
    sessions = Column(Text, nullable=True)
    complications = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="Done")  # Pending, In Progress, Done
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Multi Price List Support
    price_list_id = Column(
        Integer, ForeignKey("price_lists.id"), nullable=True, index=True
    )
    unit_price = Column(Numeric(14, 2), nullable=True)  # Price at treatment time
    price_snapshot = Column(
        Text, nullable=True
    )  # JSON: {"list_name", "price", "discount"}

    patient = relationship("Patient", back_populates="treatments")
    treatment_sessions = relationship("TreatmentSession", back_populates="treatment", cascade="all, delete-orphan")


class TreatmentSession(Base):
    __tablename__ = "treatment_sessions"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    treatment_id = Column(Integer, ForeignKey("treatments.id"), index=True)
    session_date = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    notes = Column(Text, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    treatment = relationship("Treatment", back_populates="treatment_sessions")


class Prescription(Base):
    __tablename__ = "prescriptions"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    medications = Column(Text)
    notes = Column(Text, nullable=True)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    patient = relationship("Patient", back_populates="prescriptions")


class Laboratory(Base):
    __tablename__ = "laboratories"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    email = Column(String, nullable=True)
    specialties = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    lab_orders = relationship("LabOrder", back_populates="laboratory")
    payments = relationship("LabPayment", back_populates="laboratory")


class LabOrder(Base):
    __tablename__ = "lab_orders"
    __table_args__ = (
        Index("idx_laborder_doctor_date", "doctor_id", "order_date"),
        Index("idx_laborder_tenant_date", "tenant_id", "order_date"),
        CheckConstraint("cost >= 0", name="ck_lab_orders_cost_nonnegative"),
        CheckConstraint(
            "price_to_patient >= 0", name="ck_lab_orders_patient_price_nonnegative"
        ),
    )

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    laboratory_id = Column(Integer, ForeignKey("laboratories.id"), index=True)
    work_type = Column(String)
    tooth_number = Column(String, nullable=True)
    shade = Column(String, nullable=True)
    material = Column(String, nullable=True)
    cost = Column(Numeric(14, 2), default=0.0)
    price_to_patient = Column(Numeric(14, 2), default=0.0)
    status = Column(String, default="pending")
    notes = Column(Text, nullable=True)
    order_date = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )
    delivery_date = Column(DateTime, nullable=True)
    received_date = Column(DateTime, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    patient = relationship("Patient", back_populates="lab_orders")
    laboratory = relationship("Laboratory", back_populates="lab_orders")
    doctor = relationship("User", back_populates="lab_orders")


class Procedure(Base):
    __tablename__ = "procedures"

    # REGRESSION (2026-06-20): `name` was `unique=True` (globally unique across the
    # whole table), which collided with the multi-tenant model — `tenant_id` is
    # nullable and `or_(tenant_id == X, tenant_id.is_(NULL))` filtering is used in
    # crud/procedure.py and 7+ other places (global-catalog + tenant-override pattern).
    # A naive UniqueConstraint('tenant_id','name') would NOT catch duplicate globals,
    # because in Postgres NULL != NULL for unique constraints. Hence two partial
    # unique indexes (Postgres-only feature; partial uniqueness is an INDEX, not a
    # table CONSTRAINT):
    #   - tenant-scoped rows: name unique within a tenant
    #   - global rows (tenant_id IS NULL): name unique among globals
    __table_args__ = (
        Index(
            "uq_procedures_tenant_name",
            "tenant_id", "name",
            unique=True,
            postgresql_where=text("tenant_id IS NOT NULL"),
        ),
        Index(
            "uq_procedures_global_name",
            "name",
            unique=True,
            postgresql_where=text("tenant_id IS NULL"),
        ),
        CheckConstraint("price >= 0", name="ck_procedures_price_nonnegative"),
    )

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Numeric(14, 2))
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
