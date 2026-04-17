"""Authentication and user schemas."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .tenant import Tenant


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    role: Optional[str] = None
    username: Optional[str] = None
    user_status: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None
    tenant_id: Optional[int] = None


class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[str] = None
    tenant_id: Optional[int] = None
    tenant: Optional["Tenant"] = None
    last_failed_login: Optional[datetime] = None
    is_2fa_enabled: bool = False
    patient_visibility_mode: Optional[str] = "all_assigned"

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[str] = None
    patient_visibility_mode: Optional[str] = None


class UserAdminView(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool = True
    is_deleted: bool = False
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LoginHistory(BaseModel):
    id: int
    user_id: int
    ip_address: str
    user_agent: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlockedIP(BaseModel):
    id: int
    ip_address: str
    reason: Optional[str] = None
    blocked_by: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
