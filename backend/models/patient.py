from .base import (
    Base,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    relationship,
    datetime,
    timezone,
)
from sqlalchemy import Boolean
from backend.core.security import EncryptedString


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)
    phone = Column(EncryptedString, index=True)  # Encrypted
    email = Column(EncryptedString, nullable=True, index=True)  # Encrypted
    address = Column(EncryptedString, nullable=True)  # Encrypted
    medical_history = Column(EncryptedString)  # Encrypted
    notes = Column(EncryptedString)  # Encrypted
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Soft Delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    # Doctor assignment (Multi-Doctor Support)
    assigned_doctor_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )

    # Default Price List (Multi Price List Support)
    default_price_list_id = Column(Integer, ForeignKey("price_lists.id"), nullable=True)

    appointments = relationship(
        "Appointment", back_populates="patient", cascade="all, delete-orphan"
    )
    treatments = relationship(
        "Treatment", back_populates="patient", cascade="all, delete-orphan"
    )
    tooth_statuses = relationship(
        "ToothStatus", back_populates="patient", cascade="all, delete-orphan"
    )
    payments = relationship(
        "Payment", back_populates="patient", cascade="all, delete-orphan"
    )
    attachments = relationship(
        "Attachment", back_populates="patient", cascade="all, delete-orphan"
    )
    prescriptions = relationship(
        "Prescription", back_populates="patient", cascade="all, delete-orphan"
    )
    lab_orders = relationship(
        "LabOrder", back_populates="patient", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    file_path = Column(String)
    filename = Column(String)
    file_type = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="attachments")
