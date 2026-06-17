from sqlalchemy import Column, Integer, String, JSON, DateTime, BigInteger, Index, column
from sqlalchemy.sql import func
from .base import Base
from rls.schemas import Permissive, ConditionArg, Command


class DomainEvent(Base):
    """
    Transactional Outbox Table for Domain Events.
    Events are written here within the same transaction as business data changes,
    then a background worker reads them and publishes to Celery/Redis/External APIs.
    """
    __tablename__ = "domain_events"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, index=True, nullable=True) # nullable for system events
    event_type = Column(String(255), nullable=False) # e.g. "appointment.created"
    aggregate_type = Column(String(255), nullable=False) # e.g. "appointment"
    aggregate_id = Column(String(255), nullable=False) # e.g. "123"

    payload = Column(JSON, nullable=False)

    status = Column(String(50), nullable=False, default="pending") # pending | processing | completed | failed
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)

    error_message = Column(String, nullable=True)

    available_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_domain_events_pending', 'status', 'available_at'),
    )
