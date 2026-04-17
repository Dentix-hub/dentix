from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class AILog(Base):
    """
    Unified AI Log (v2) - Enforces Rule 10 & Phase 0 of AI Analytics Engine.
    Consolidates Audit + Usage + Performance metrics.

    Backward-compat aliases for legacy code that used AIUsageLog columns:
    - response_tool  → tool
    - success        → computed from status
    - response_time_ms → execution_time_ms
    - username       → resolved via user relationship
    - query          → input_text
    """

    __tablename__ = "ai_logs"

    # Core Identity
    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(
        String(50), index=True, nullable=False
    )  # UUID for request lifecycle
    tenant_id = Column(Integer, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Request Context
    intent = Column(String(100), index=True)  # e.g. "appointment_booking", "general_qa"
    tool = Column(String(100))  # e.g. "create_appointment"
    model = Column(String(50))  # e.g. "llama-3-8b"

    # Data Payload (Sanitized)
    input_text = Column(Text)  # The user's prompt
    output_text = Column(Text)  # The AI's final response
    tool_params = Column(Text)  # JSON of extracted parameters
    tool_result = Column(Text)  # JSON of execution result

    # Performance & Cost
    execution_time_ms = Column(Integer)  # Total latency
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    cost = Column(Float, default=0.0)  # Estimated cost
    confidence = Column(Float, default=1.0)  # 0.0 to 1.0

    # Status & Error Handling
    status = Column(
        String(20), index=True
    )  # SUCCESS, FAILURE, BLOCKED, NEEDS_CONFIRMATION
    error_type = Column(String(50), nullable=True)  # VALIDATION, LLM_ERROR, TOOL_ERROR
    error_details = Column(Text, nullable=True)  # Stack trace or specific message

    # Governance
    policy_check = Column(Boolean, default=True)
    scribe_mode = Column(Boolean, default=False)  # Was Medical Scribe Mode active?

    # Legacy compat columns stored for backward-compat queries (AIUsageLog fields)
    username = Column(String, nullable=True)        # cached username at log time
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # alias for timestamp

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")

    # --------------- Backward-compat properties ---------------
    @property
    def response_tool(self) -> str:
        """Compat alias for legacy AIUsageLog.response_tool → AILog.tool."""
        return self.tool

    @property
    def query(self) -> str:
        """Compat alias for legacy AIUsageLog.query → AILog.input_text."""
        return self.input_text

    @property
    def success(self) -> bool:
        """Compat alias: True when status == SUCCESS."""
        return self.status == "SUCCESS"

    @property
    def response_time_ms(self) -> float:
        """Compat alias for legacy AIUsageLog.response_time_ms → execution_time_ms."""
        return float(self.execution_time_ms or 0)
