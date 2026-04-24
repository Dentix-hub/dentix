from .base import (
    Base,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Text,
    Date,
    ForeignKey,
    relationship,
    datetime,
    timezone,
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(
        String, index=True
    )  # Non-unique to allow duplicates across tenants or same user
    email = Column(String, unique=True, index=True)  # Email MUST be unique now
    hashed_password = Column(String)

    # Enterprise Security Fields
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime, nullable=True)
    account_locked_until = Column(DateTime, nullable=True)
    is_2fa_enabled = Column(Boolean, default=False)
    otp_secret = Column(String, nullable=True)

    # Session Security
    active_session_id = Column(String, nullable=True)

    role = Column(String, default="doctor")
    permissions = Column(Text, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    fcm_token = Column(String, nullable=True)

    # Doctor Visibility Settings (Multi-Doctor Support)
    # ALL_ASSIGNED = see assigned patients only
    # APPOINTMENTS_ONLY = see patients with appointments only
    # MIXED = see both assigned and appointment patients
    patient_visibility_mode = Column(String, default="all_assigned")
    can_view_other_doctors_history = Column(Boolean, default=False)

    # Compensation settings
    commission_percent = Column(Float, default=0.0)
    fixed_salary = Column(Float, default=0.0)
    per_appointment_fee = Column(Float, default=0.0)
    hire_date = Column(Date, nullable=True)

    # Status Fields
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)

    tenant = relationship("Tenant", back_populates="users")
    lab_orders = relationship("LabOrder", back_populates="doctor")
    salary_payments = relationship("SalaryPayment", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
    notifications_read = relationship("NotificationRead", back_populates="user")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="password_reset_tokens")


class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    ip_address = Column(String, index=True)
    user_agent = Column(String, nullable=True)
    status = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    token_hash = Column(String, unique=True, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    device_info = Column(String, nullable=True)
    last_active_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="sessions")
