from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
# from . import BaseSchema # Removed undefined import


class SystemErrorBase(BaseModel):
    level: str = "ERROR"
    source: str = "BACKEND"
    message: str
    stack_trace: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    user_id: Optional[int] = None
    tenant_id: Optional[int] = None
    user_agent: Optional[str] = None


class SystemErrorCreate(BaseModel):
    """Untrusted browser error payload; identity and request metadata stay server-owned."""

    level: Literal["INFO", "WARNING", "ERROR", "CRITICAL"] = "ERROR"
    source: Literal["FRONTEND"] = "FRONTEND"
    message: str = Field(min_length=1, max_length=4000)
    stack_trace: Optional[str] = Field(default=None, max_length=12000)
    path: Optional[str] = Field(default=None, max_length=500)
    method: Optional[str] = Field(default=None, max_length=10)


class SystemError(SystemErrorBase):
    id: int
    created_at: datetime
    ip_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
