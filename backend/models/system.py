from datetime import timezone
from .base import (
    Base,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Numeric,
    Text,
    Date,
    Boolean,
    ForeignKey,
    relationship,
    datetime,
)
from sqlalchemy import CheckConstraint, column
import enum
from rls.schemas import Permissive, ConditionArg, Command


class ErrorLevel(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorSource(str, enum.Enum):
    BACKEND = "BACKEND"
    FRONTEND = "FRONTEND"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, index=True)
    entity_type = Column(String, index=True)
    entity_id = Column(Integer, nullable=True)
    target_user_id = Column(Integer, nullable=True)
    target_username = Column(String, nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id"), index=True)
    performed_by_username = Column(String)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    subject = Column(String)
    message = Column(Text)
    priority = Column(String, default="normal")
    status = Column(String, default="unread")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user = relationship("User")
    tenant = relationship("Tenant")


class Notification(Base):
    __tablename__ = "notifications"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: (column("tenant_id") == x) | (column("is_global") == True) | (column("tenant_id") == None),
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    type = Column(String, default="info")
    is_global = Column(Boolean, default=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    read_by = relationship(
        "NotificationRead", back_populates="notification", cascade="all, delete-orphan"
    )


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), index=True)
    read_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted = Column(Boolean, default=False)

    user = relationship("User", back_populates="notifications_read")
    notification = relationship("Notification", back_populates="read_by")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String)
    description = Column(String, nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )


class BlockedIP(Base):
    __tablename__ = "blocked_ips"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, unique=True, index=True)
    reason = Column(String, nullable=True)
    blocked_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    expires_at = Column(DateTime, nullable=True)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    is_global_enabled = Column(Boolean, default=False)
    rollout_percentage = Column(Integer, default=0)


class TenantFeature(Base):
    __tablename__ = "tenant_features"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    feature_key = Column(String, ForeignKey("feature_flags.key"), index=True)
    is_enabled = Column(Boolean)

    tenant = relationship("Tenant")
    feature = relationship("FeatureFlag")


class DailySystemStats(Base):
    __tablename__ = "daily_system_stats"
    __table_args__ = (
        CheckConstraint(
            "total_revenue >= 0", name="ck_daily_system_stats_revenue_nonnegative"
        ),
    )

    date = Column(Date, primary_key=True, index=True)
    total_tenants = Column(Integer, default=0)
    active_tenants = Column(Integer, default=0)
    new_tenants = Column(Integer, default=0)
    total_revenue = Column(Numeric(14, 2), default=0.0)
    api_error_rate = Column(Float, default=0.0)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, index=True)
    status = Column(String, default="running")
    started_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    triggered_by = Column(String, default="system")
    tenant_id = Column(Integer, nullable=True)


class SystemError(Base):
    __tablename__ = "system_errors"

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, default=ErrorLevel.ERROR, index=True)
    source = Column(String, default=ErrorSource.BACKEND, index=True)
    message = Column(Text)

    stack_trace = Column(Text, nullable=True)
    path = Column(String, nullable=True)
    method = Column(String, nullable=True)
    user_id = Column(Integer, nullable=True)
    tenant_id = Column(Integer, nullable=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        index=True,
    )
