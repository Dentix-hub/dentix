"""System and admin schemas."""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date

from .tenant import SubscriptionPayment


class AuditLog(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    target_username: Optional[str] = None
    performed_by_username: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True)


class SystemSetting(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True)


class SupportMessageBase(BaseModel):
    subject: str
    message: str
    priority: str = "normal"


class SupportMessageCreate(SupportMessageBase):
    pass


class SupportMessage(SupportMessageBase):
    id: int
    user_id: int
    tenant_id: int
    status: str = "unread"
    created_at: datetime
    username: Optional[str] = None
    clinic_name: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True)


class NotificationBase(BaseModel):
    title: str
    content: str
    type: str = "info"
    is_global: bool = True
    tenant_id: Optional[int] = None


class NotificationCreate(NotificationBase):
    pass


class Notification(NotificationBase):
    id: int
    created_at: datetime
    is_read: bool = False

    model_config = ConfigDict(
        from_attributes=True)


class FeatureFlag(BaseModel):
    id: int
    key: str
    description: Optional[str] = None
    is_global_enabled: bool
    rollout_percentage: int

    model_config = ConfigDict(
        from_attributes=True)


class FeatureFlagCreate(BaseModel):
    key: str
    description: Optional[str] = None
    is_global_enabled: bool = False
    rollout_percentage: int = 0


class TenantFeature(BaseModel):
    id: int
    tenant_id: int
    feature_key: str
    is_enabled: bool

    model_config = ConfigDict(
        from_attributes=True)


class AdminDashboardStats(BaseModel):
    total_tenants: int
    active_tenants: int
    expired_tenants: int
    total_revenue: float
    monthly_revenue: dict
    plan_distribution: dict
    recent_payments: List[SubscriptionPayment]


class DailySystemStats(BaseModel):
    date: date
    total_tenants: int = 0
    active_tenants: int = 0
    new_tenants: int = 0
    total_revenue: float = 0.0
    api_error_rate: float = 0.0

    model_config = ConfigDict(
        from_attributes=True)


class BackgroundJob(BaseModel):
    id: int
    job_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    triggered_by: str
    tenant_id: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True)
