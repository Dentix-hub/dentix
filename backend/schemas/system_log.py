from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
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

class SystemErrorCreate(SystemErrorBase):
    pass

class SystemError(SystemErrorBase):
    id: int
    created_at: datetime
    ip_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
