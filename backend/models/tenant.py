from .base import (
    Base,
    Column,
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
)


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    display_name_ar = Column(String)
    price = Column(Float, default=0.0)
    duration_days = Column(Integer, default=30)
    max_users = Column(Integer, nullable=True)
    max_patients = Column(Integer, nullable=True)
    features = Column(Text, nullable=True)

    # AI Limits
    is_ai_enabled = Column(Boolean, default=False)
    ai_daily_limit = Column(
        Integer, default=0
    )  # 0 = disabled (if enabled but 0, maybe unlimited? No, usually 0 means 0. -1 for unlimited)
    ai_features = Column(Text, nullable=True)  # JSON list of allowed tools/features

    is_default = Column(Boolean, default=False)  # New Default Feature
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    tenants = relationship("Tenant", back_populates="subscription_plan")
    payments = relationship("SubscriptionPayment", back_populates="plan")


class SubscriptionPayment(Base):
    __tablename__ = "subscription_payments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"))
    amount = Column(Float)
    payment_method = Column(String)
    payment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=True)
    paid_by = Column(String, nullable=True)

    tenant = relationship("Tenant", back_populates="payments")
    plan = relationship("SubscriptionPlan", back_populates="payments")


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)  # Non-unique
    logo = Column(String, nullable=True)
    subscription_status = Column(String, default="active")

    # Enterprise Subscription Fields
    grace_period_until = Column(DateTime, nullable=True)
    auto_suspend_at = Column(DateTime, nullable=True)
    payment_failed_count = Column(Integer, default=0)
    manual_override_reason = Column(String, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)

    plan = Column(String, default="trial")  # Legacy
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_revenue = Column(Float, default=0.0)

    # Backup Settings
    backup_frequency = Column(String, default="off")
    google_refresh_token = Column(String, nullable=True)
    last_backup_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)

    # Prescription Header Info
    doctor_name = Column(String, nullable=True)
    doctor_title = Column(String, nullable=True)
    clinic_address = Column(String, nullable=True)
    clinic_phone = Column(String, nullable=True)
    print_header_image = Column(String, nullable=True)
    print_footer_image = Column(String, nullable=True)

    # Soft Delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

    users = relationship("User", back_populates="tenant")
    subscription_plan = relationship("SubscriptionPlan", back_populates="tenants")
    payments = relationship(
        "SubscriptionPayment", back_populates="tenant", cascade="all, delete-orphan"
    )
