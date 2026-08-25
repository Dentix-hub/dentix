from .base import (
    Base,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    relationship,
    datetime,
    timezone,
    Boolean,
    Mapped,
    mapped_column,
)
from backend.core.security import EncryptedString
from rls.schemas import Permissive, ConditionArg, Command
from sqlalchemy import column
from typing import TYPE_CHECKING
from datetime import date

if TYPE_CHECKING:
    from .user import User


class Patient(Base):
    __tablename__ = "patients"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    age: Mapped[int] = mapped_column(Integer)
    phone: Mapped[str] = mapped_column(EncryptedString, index=True)
    email: Mapped[str | None] = mapped_column(EncryptedString, nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    medical_history: Mapped[str] = mapped_column(EncryptedString)
    notes: Mapped[str] = mapped_column(EncryptedString)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    name_search_normalized: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    phone_search_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_of_birth_precision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    age_recorded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tenant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=True, index=True
    )

    assigned_doctor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    assigned_doctor: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_doctor_id])

    default_price_list_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("price_lists.id"), nullable=True
    )

    @property
    def file_number(self) -> int:
        """Stable display identifier used by Finance V2 without adding a DB column."""
        return self.id

    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    treatments = relationship("Treatment", back_populates="patient", cascade="all, delete-orphan")
    tooth_statuses = relationship("ToothStatus", back_populates="patient", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="patient", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="patient", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="patient", cascade="all, delete-orphan")
    lab_orders = relationship("LabOrder", back_populates="patient", cascade="all, delete-orphan")


class Attachment(Base):
    __tablename__ = "attachments"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id"))
    file_path: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    patient = relationship("Patient", back_populates="attachments")
