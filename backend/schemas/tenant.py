"""Tenant and subscription schemas."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class TenantBase(BaseModel):
    name: str
    subscription_status: Optional[str] = "active"
    logo: Optional[str] = None
    plan: Optional[str] = "trial"
    is_active: Optional[bool] = True
    subscription_end_date: Optional[datetime] = None
    grace_period_until: Optional[datetime] = None
    auto_suspend_at: Optional[datetime] = None
    google_refresh_token: Optional[str] = None
    backup_frequency: Optional[str] = "off"
    last_backup_at: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    # Prescription Info
    doctor_name: Optional[str] = None
    doctor_title: Optional[str] = None
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None
    contact_phone: Optional[str] = None
    print_header_image: Optional[str] = None
    print_footer_image: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_end_date: Optional[datetime] = None
    logo: Optional[str] = None

    # Backup & System
    backup_frequency: Optional[str] = None
    google_refresh_token: Optional[str] = None

    # Prescription Info
    doctor_name: Optional[str] = None
    doctor_title: Optional[str] = None
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None
    contact_phone: Optional[str] = None
    print_header_image: Optional[str] = None
    print_footer_image: Optional[str] = None


class Tenant(TenantBase):
    id: int
    created_at: datetime
    payment_failed_count: int = 0
    manual_override_reason: Optional[str] = None
    subscription_plan: Optional["SubscriptionPlan"] = None

    model_config = ConfigDict(from_attributes=True)


class TenantWithStats(Tenant):
    total_payments: Optional[float] = 0.0
    active_users_count: Optional[int] = 0
    patients_count: Optional[int] = 0
    days_remaining: Optional[int] = 0
    current_plan_name: Optional[str] = None


class ClinicRegistration(BaseModel):
    clinic_name: str
    admin_username: str
    admin_password: str
    contact_phone: str


class SubscriptionPlanBase(BaseModel):
    name: str
    display_name_ar: str
    price: float
    duration_days: int
    max_users: Optional[int] = None
    max_patients: Optional[int] = None
    features: Optional[str] = None
    is_ai_enabled: bool = False
    ai_daily_limit: int = 0
    ai_features: Optional[str] = None
    is_default: bool = False  # New Field


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    display_name_ar: Optional[str] = None
    price: Optional[float] = None
    duration_days: Optional[int] = None
    max_users: Optional[int] = None
    max_patients: Optional[int] = None
    features: Optional[str] = None
    is_active: Optional[bool] = None
    is_ai_enabled: Optional[bool] = None
    ai_daily_limit: Optional[int] = None
    ai_features: Optional[str] = None
    is_default: Optional[bool] = None


class SubscriptionPlan(SubscriptionPlanBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPaymentBase(BaseModel):
    tenant_id: Optional[int] = None
    plan_id: Optional[int] = None
    amount: Optional[float] = 0.0
    payment_method: Optional[str] = "Unknown"
    notes: Optional[str] = None
    payment_date: Optional[datetime] = None
    paid_by: Optional[str] = None
    provider: Optional[str] = None
    provider_payment_id: Optional[str] = None
    provider_status: Optional[str] = None


class SubscriptionPaymentCreate(SubscriptionPaymentBase):
    tenant_id: int
    plan_id: int
    amount: float
    payment_method: str


class SubscriptionPayment(SubscriptionPaymentBase):
    id: int
    payment_date: datetime
    created_by: Optional[str] = None
    provider: Optional[str] = None
    provider_payment_id: Optional[str] = None
    provider_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCheckoutCreate(BaseModel):
    tenant_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    provider: str = Field(default="manual", min_length=2, max_length=50)
    success_url: Optional[str] = Field(default=None, max_length=2000)
    cancel_url: Optional[str] = Field(default=None, max_length=2000)
    currency: str = Field(default="EGP", min_length=3, max_length=3)


class SubscriptionCheckoutSession(BaseModel):
    provider: str
    provider_reference: str
    checkout_url: str
    amount: float
    currency: str = "EGP"


class SubscriptionWebhookEvent(BaseModel):
    provider: str = Field(min_length=2, max_length=50)
    provider_payment_id: str = Field(min_length=1, max_length=160)
    provider_status: str = Field(min_length=2, max_length=30)
    provider_reference: str = Field(min_length=10, max_length=120)
    amount: float = Field(gt=0)
    currency: str = Field(default="EGP", min_length=3, max_length=3)
    paid_by: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=2000)
