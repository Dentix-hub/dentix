from datetime import timezone
from .base import (
    Base,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Text,
    Date,
    Boolean,
    ForeignKey,
    relationship,
    Index,
    datetime,
)
from sqlalchemy import column
from rls.schemas import Permissive, ConditionArg, Command


class Payment(Base):
    __tablename__ = "payments"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    amount = Column(Float)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    notes = Column(Text, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    patient = relationship("Patient", back_populates="payments")

    @property
    def patient_name(self):
        return self.patient.name if self.patient else None

    @property
    def patient_file_number(self):
        return (self.patient.file_number if self.patient else None) or self.patient_id


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (Index("idx_expense_tenant_date", "tenant_id", "date"),)

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String)
    cost = Column(Float)
    category = Column(String)
    date = Column(Date, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    notes = Column(String, nullable=True)


class SalaryPayment(Base):
    __tablename__ = "salary_payments"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    month = Column(String, index=True)
    amount = Column(Float, default=0.0)
    payment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_partial = Column(Boolean, default=False)
    days_worked = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    user = relationship("User", back_populates="salary_payments")


class LabPayment(Base):
    __tablename__ = "lab_payments"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    laboratory_id = Column(Integer, ForeignKey("laboratories.id"), index=True)
    amount = Column(Float)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    notes = Column(Text, nullable=True)
    method = Column(String, default="Cash")  # Cash, Bank Transfer, etc.
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    laboratory = relationship("Laboratory", back_populates="payments")
