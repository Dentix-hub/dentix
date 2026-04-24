from datetime import timezone
from .base import (
    Base,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Text,
    ForeignKey,
    relationship,
    Index,
    datetime,
)
from sqlalchemy import Boolean


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("idx_appointment_doctor_date", "doctor_id", "date_time"),
        Index("idx_appointment_tenant_date", "patient_id", "date_time"), # Indirect via patient join usually, but useful if denormalized or for patient history
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    doctor_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )  # Multi-Doctor Support
    price_list_id = Column(
        Integer, ForeignKey("price_lists.id"), nullable=True, index=True
    )  # Multi Price List
    date_time = Column(DateTime, index=True)
    status = Column(String, default="Scheduled")
    notes = Column(Text, nullable=True)

    # Soft Delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

    # Optimistic Locking: prevents double-booking race conditions
    version_id = Column(Integer, default=1, nullable=False)

    __mapper_args__ = {
        "version_id_col": version_id,
    }

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("User")


class ToothStatus(Base):
    __tablename__ = "tooth_status"

    id = Column(Integer, primary_key=True, index=True)
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
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    tooth_number = Column(Integer, nullable=True)
    diagnosis = Column(String)
    procedure = Column(String)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    cost = Column(Float, default=0.0)  # Legacy: final cost after discount
    discount = Column(Float, default=0.0)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    canal_count = Column(Integer, nullable=True)
    canal_lengths = Column(String, nullable=True)
    sessions = Column(Text, nullable=True)
    complications = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    # Multi Price List Support
    price_list_id = Column(
        Integer, ForeignKey("price_lists.id"), nullable=True, index=True
    )
    unit_price = Column(Float, nullable=True)  # Price at time of treatment (snapshot)
    price_snapshot = Column(
        Text, nullable=True
    )  # JSON: {"list_name", "price", "discount"}

    patient = relationship("Patient", back_populates="treatments")
    treatment_sessions = relationship("TreatmentSession", back_populates="treatment", cascade="all, delete-orphan")


class TreatmentSession(Base):
    __tablename__ = "treatment_sessions"

    id = Column(Integer, primary_key=True, index=True)
    treatment_id = Column(Integer, ForeignKey("treatments.id"), index=True)
    session_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    treatment = relationship("Treatment", back_populates="treatment_sessions")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    medications = Column(Text)
    notes = Column(Text, nullable=True)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="prescriptions")


class Laboratory(Base):
    __tablename__ = "laboratories"

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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lab_orders = relationship("LabOrder", back_populates="laboratory")
    payments = relationship("LabPayment", back_populates="laboratory")


class LabOrder(Base):
    __tablename__ = "lab_orders"
    __table_args__ = (
        Index("idx_laborder_doctor_date", "doctor_id", "order_date"),
        Index("idx_laborder_tenant_date", "tenant_id", "order_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    laboratory_id = Column(Integer, ForeignKey("laboratories.id"), index=True)
    work_type = Column(String)
    tooth_number = Column(String, nullable=True)
    shade = Column(String, nullable=True)
    material = Column(String, nullable=True)
    cost = Column(Float, default=0.0)
    price_to_patient = Column(Float, default=0.0)
    status = Column(String, default="pending")
    notes = Column(Text, nullable=True)
    order_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    delivery_date = Column(DateTime, nullable=True)
    received_date = Column(DateTime, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    patient = relationship("Patient", back_populates="lab_orders")
    laboratory = relationship("Laboratory", back_populates="lab_orders")
    doctor = relationship("User", back_populates="lab_orders")


class Procedure(Base):
    __tablename__ = "procedures"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    price = Column(Float)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
