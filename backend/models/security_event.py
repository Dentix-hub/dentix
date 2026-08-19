from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, column
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timezone
from rls.schemas import Permissive, ConditionArg, Command


class SecurityEvent(Base):
    """
    Security Event Log (Phase 3 Requirement).
    Tracks authentication failures, blocked actions, and policy violations.
    """

    __tablename__ = "security_events"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer, index=True, nullable=True
    )  # Nullable for pre-login failures
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Nullable if unknown user

    event_type = Column(
        String(50), index=True
    )  # e.g. "AUTH_FAILURE", "POLICY_VIOLATION", "RATE_LIMIT"
    severity = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL

    description = Column(Text)
    details = Column(Text)  # JSON payload

    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)

    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    user = relationship("User")
