from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Any]] = None


class AIQueryRequest(BaseModel):
    text: str
    context: List[Message] = []
    last_patient_name: Optional[str] = None
    voice_mode: bool = False
    scribe_mode: bool = False  # If True, prioritize clinical documentation
    idempotency_key: Optional[str] = None


class AIQueryResponse(BaseModel):
    success: bool
    message: str
    tool: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    latency: float = 0.0
    error: Optional[str] = None
    risk_level: Optional[str] = None
    suggestions: Optional[List[str]] = None
