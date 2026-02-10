from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
import time


class SessionState(BaseModel):
    """Holds the conversational context for a user session."""

    active_patient_id: Optional[int] = None
    active_patient_name: Optional[str] = None
    last_intent: Optional[str] = None
    last_ui_action: Optional[str] = None  # e.g., 'show_appointments'
    temp_data: Dict[str, Any] = Field(default_factory=dict)
    pending_confirmation: Optional[Dict[str, Any]] = None
    last_updated: float = Field(default_factory=time.time)


class StateManager:
    """
    Manages session states.
    For Phase 2, we use in-memory dictionary.
    Future: Redis.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def get_session(self, tenant_id: int, user_id: int) -> SessionState:
        key = self._get_key(tenant_id, user_id)
        if key not in self._sessions:
            self._sessions[key] = SessionState()
        return self._sessions[key]

    def update_session(self, tenant_id: int, user_id: int, updates: Dict[str, Any]):
        session = self.get_session(tenant_id, user_id)
        session_data = session.model_dump()
        session_data.update(updates)
        session_data["last_updated"] = time.time()

        # Re-validate and save
        self._sessions[self._get_key(tenant_id, user_id)] = SessionState(**session_data)

    def _get_key(self, tenant_id: int, user_id: int) -> str:
        return f"{tenant_id}:{user_id}"


# Singleton
state_manager = StateManager()
