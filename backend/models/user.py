from .base import (
    Base,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    Text,
    Date,
    ForeignKey,
    relationship,
    datetime,
    timezone,
    Mapped,
    mapped_column,
)
from datetime import date
from decimal import Decimal
from rls.schemas import Permissive, ConditionArg, Command
from sqlalchemy import CheckConstraint, column


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "commission_percent >= 0 AND commission_percent <= 100",
            name="ck_users_commission_percent_range",
        ),
        CheckConstraint("fixed_salary >= 0", name="ck_users_fixed_salary_nonnegative"),
        CheckConstraint(
            "per_appointment_fee >= 0",
            name="ck_users_appointment_fee_nonnegative",
        ),
    )

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, index=True)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)

    # Enterprise Security Fields
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_failed_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    account_locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    otp_secret: Mapped[str | None] = mapped_column(String, nullable=True)

    # Session Security
    active_session_id: Mapped[str | None] = mapped_column(String, nullable=True)

    role: Mapped[str] = mapped_column(String, default="doctor")
    permissions: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)
    fcm_token: Mapped[str | None] = mapped_column(String, nullable=True)

    # Doctor Visibility Settings
    patient_visibility_mode: Mapped[str] = mapped_column(String, default="all_assigned")
    can_view_other_doctors_history: Mapped[bool] = mapped_column(Boolean, default=False)

    # Compensation settings
    commission_percent: Mapped[Decimal] = mapped_column(
        Numeric(7, 4), default=Decimal("0.0000")
    )
    fixed_salary: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00")
    )
    per_appointment_fee: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00")
    )
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Status Fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tenant = relationship("Tenant", back_populates="users")
    lab_orders = relationship("LabOrder", back_populates="doctor")
    salary_payments = relationship("SalaryPayment", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
    notifications_read = relationship("NotificationRead", back_populates="user")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user = relationship("User", back_populates="password_reset_tokens")


class LoginHistory(Base):
    __tablename__ = "login_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    ip_address: Mapped[str] = mapped_column(String, index=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user = relationship("User")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    device_info: Mapped[str | None] = mapped_column(String, nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user = relationship("User", backref="sessions")
