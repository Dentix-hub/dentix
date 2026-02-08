from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Any]] = None

class AIQueryRequest(BaseModel):
    text: str
    context: List[Message] = []
    last_patient_name: Optional[str] = None
    voice_mode: bool = False
    scribe_mode: bool = False # If True, prioritize clinical documentation

class AIQueryResponse(BaseModel):
    success: bool
    message: str
    tool: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    latency: float = 0.0
