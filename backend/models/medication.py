from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, column
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base
from rls.schemas import Permissive, ConditionArg, Command


class SavedMedication(Base):
    __tablename__ = "saved_medications"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    strength = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    default_dose = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant")
