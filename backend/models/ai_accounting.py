"""AI Quota and Reservation Accounting Models.

PR-07: Additive tenant-scoped usage and reservation ledger for atomic AI quota
admission, independent of diagnostic AILogs.
"""

from __future__ import annotations

from datetime import datetime, timezone
import enum
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    column,
)
from sqlalchemy.orm import relationship

from backend.database import Base
from rls.schemas import Command, ConditionArg, Permissive


class ReservationStatus(str, enum.Enum):
    RESERVED = "RESERVED"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"
    UNCERTAIN = "UNCERTAIN"


ALLOWED_TRANSITIONS = {
    ReservationStatus.RESERVED.value: {
        ReservationStatus.RESERVED.value,
        ReservationStatus.CONSUMED.value,
        ReservationStatus.RELEASED.value,
        ReservationStatus.UNCERTAIN.value,
    },
    ReservationStatus.UNCERTAIN.value: {
        ReservationStatus.UNCERTAIN.value,
        ReservationStatus.CONSUMED.value,
        ReservationStatus.RELEASED.value,
    },
    ReservationStatus.CONSUMED.value: {
        ReservationStatus.CONSUMED.value,
    },
    ReservationStatus.RELEASED.value: {
        ReservationStatus.RELEASED.value,
    },
}


class AIQuotaWindow(Base):
    """Clinic-local daily quota window.

    Persists UTC start/end boundaries with a tenant timezone snapshot.
    Its boundaries remain stable through a mid-day timezone edit.
    """

    __tablename__ = "ai_quota_windows"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "local_date", name="uq_ai_quota_windows_tenant_local_date"
        ),
        CheckConstraint(
            "start_utc < end_utc", name="ck_ai_quota_windows_bounds"
        ),
        CheckConstraint(
            "reserved_count >= 0", name="ck_ai_quota_windows_reserved_nonneg"
        ),
        CheckConstraint(
            "consumed_count >= 0", name="ck_ai_quota_windows_consumed_nonneg"
        ),
        CheckConstraint(
            "uncertain_count >= 0", name="ck_ai_quota_windows_uncertain_nonneg"
        ),
    )

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    local_date = Column(Date, nullable=False, index=True)
    start_utc = Column(DateTime, nullable=False)
    end_utc = Column(DateTime, nullable=False)
    timezone = Column(String(64), nullable=False)

    reserved_count = Column(Integer, nullable=False, default=0)
    consumed_count = Column(Integer, nullable=False, default=0)
    uncertain_count = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    tenant = relationship("Tenant")
    reservations = relationship("AIReservation", back_populates="window", cascade="all, delete-orphan")

    @property
    def admitted_count(self) -> int:
        return int(self.reserved_count + self.consumed_count + self.uncertain_count)

    def remaining_quota(self, limit: int) -> int:
        return max(0, limit - self.admitted_count)


class AIReservation(Base):
    """Tenant-scoped AI reservation row.

    Tracks logical request identifier, idempotency key, request fingerprint,
    scope (tenant + actor + operation), parent linkage, status lifecycle,
    and auditable reconciliation notes.
    """

    __tablename__ = "ai_reservations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_ai_reservations_tenant_idempotency"
        ),
        CheckConstraint(
            "status IN ('RESERVED', 'CONSUMED', 'RELEASED', 'UNCERTAIN')",
            name="ck_ai_reservations_status",
        ),
        CheckConstraint(
            "units >= 0", name="ck_ai_reservations_units_nonneg"
        ),
    )

    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reservation_id = Column(String(36), nullable=False, unique=True, index=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    window_id = Column(
        Integer,
        ForeignKey("ai_quota_windows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    operation = Column(String(64), nullable=False, index=True)
    request_fingerprint = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), nullable=True, index=True)
    parent_reservation_id = Column(String(36), nullable=True, index=True)

    status = Column(String(32), nullable=False, default=ReservationStatus.RESERVED.value, index=True)
    units = Column(Integer, nullable=False, default=1)

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    finalized_at = Column(DateTime, nullable=True)
    error_reason = Column(String(255), nullable=True)
    reconciliation_notes = Column(Text, nullable=True)

    tenant = relationship("Tenant")
    window = relationship("AIQuotaWindow", back_populates="reservations")
    user = relationship("User")
