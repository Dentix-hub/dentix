from .base import (
    Base,
    Integer,
    String,
    DateTime,
    ForeignKey,
    relationship,
    datetime,
    timezone,
    Boolean,
    Mapped,
    mapped_column,
    UniqueConstraint,
)
from backend.core.security import EncryptedString
from rls.schemas import Permissive, ConditionArg, Command
from sqlalchemy import column
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User



class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "file_number", name="uq_patients_tenant_file_number"
        ),
    )

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    age: Mapped[int] = mapped_column(Integer)
    phone: Mapped[str] = mapped_column(EncryptedString, index=True)  # Encrypted
    email: Mapped[str | None] = mapped_column(EncryptedString, nullable=True, index=True)  # Encrypted
    address: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)  # Encrypted
    medical_history: Mapped[str] = mapped_column(EncryptedString)  # Encrypted
    notes: Mapped[str] = mapped_column(EncryptedString)  # Encrypted
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    # Doctor assignment (Multi-Doctor Support)
    assigned_doctor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    assigned_doctor: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_doctor_id])

    # Default Price List (Multi Price List Support)
    default_price_list_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("price_lists.id"), nullable=True)

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"))
    file_path: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="attachments")
