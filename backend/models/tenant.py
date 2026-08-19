from .base import (
    Base,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Text,
    ForeignKey,
    relationship,
    datetime,
    timezone,
    Mapped,
    mapped_column,
)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name_ar: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_patients: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI Limits
    is_ai_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_daily_limit: Mapped[int] = mapped_column(Integer, default=0)  # 0 = disabled
    ai_features: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list of allowed tools/features

    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # New Default Feature
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    tenants = relationship("Tenant", back_populates="subscription_plan")
    payments = relationship("SubscriptionPayment", back_populates="plan")


class SubscriptionPayment(Base):
    __tablename__ = "subscription_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"))
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_plans.id"))
    amount: Mapped[float] = mapped_column(Float)
    payment_method: Mapped[str] = mapped_column(String)
    payment_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    paid_by: Mapped[str | None] = mapped_column(String, nullable=True)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    provider_status: Mapped[str | None] = mapped_column(String, nullable=True)

    tenant = relationship("Tenant", back_populates="payments")
    plan = relationship("SubscriptionPlan", back_populates="payments")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)  # Non-unique
    logo: Mapped[str | None] = mapped_column(String, nullable=True)
    subscription_status: Mapped[str] = mapped_column(String, default="active")

    # Enterprise Subscription Fields
    grace_period_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_suspend_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payment_failed_count: Mapped[int] = mapped_column(Integer, default=0)
    manual_override_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    subscription_end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    plan: Mapped[str] = mapped_column(String, default="trial")  # Legacy
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("subscription_plans.id"), nullable=True)
    domain: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Africa/Cairo",
        server_default="Africa/Cairo",
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)

    # Backup Settings
    backup_frequency: Mapped[str] = mapped_column(String, default="off")
    google_refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Prescription Header Info
    doctor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    doctor_title: Mapped[str | None] = mapped_column(String, nullable=True)
    clinic_address: Mapped[str | None] = mapped_column(String, nullable=True)
    clinic_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String, nullable=True)  # Administrative contact from registration
    print_header_image: Mapped[str | None] = mapped_column(String, nullable=True)
    print_footer_image: Mapped[str | None] = mapped_column(String, nullable=True)

    # Soft Delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    users = relationship("User", back_populates="tenant")
    subscription_plan = relationship("SubscriptionPlan", back_populates="tenants")
    payments = relationship(
        "SubscriptionPayment", back_populates="tenant", cascade="all, delete-orphan"
    )
