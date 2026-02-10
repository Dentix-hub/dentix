from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base


class SecurityEvent(Base):
    """
    Security Event Log (Phase 3 Requirement).
    Tracks authentication failures, blocked actions, and policy violations.
    """

    __tablename__ = "security_events"

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

    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
