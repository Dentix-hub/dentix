"""AI Quota and Reservation Accounting Service.

PR-07: Proves that 2/10/30 are hard shared-tenant admission limits before routing real requests through them.
- Clinic-local quota window with stable UTC boundaries across timezone edits
- Atomic PostgreSQL row-level locks and conditional reservation
- Isolation from caller clinical/financial sessions
- Idempotency with fingerprint conflict detection and actor scope safety
- Conservative UNCERTAIN state on provider timeout/crash with auditable reconciliation
- Independence from diagnostic AILogs
- Preservation across clinic business archive restores and plan upgrades/downgrades
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Dict, Generator, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_engine, engine
from backend import models

_SyncSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
from backend.models.ai_accounting import (
    AIQuotaWindow,
    AIReservation,
    ALLOWED_TRANSITIONS,
    ReservationStatus,
)
from backend.utils.tenant_time import (
    DEFAULT_TENANT_TIMEZONE,
    resolve_timezone,
    tenant_day_utc_bounds_naive,
    tenant_local_date,
)


class AIQuotaError(Exception):
    """Base error for AI Quota operations."""
    pass


class AIQuotaExhaustedError(AIQuotaError):
    """Raised when tenant daily AI quota is exhausted."""
    def __init__(self, tenant_id: int, limit: int, admitted: int, window_id: int | None = None):
        super().__init__(
            f"Tenant {tenant_id} daily AI quota exhausted: {admitted}/{limit} requests admitted."
        )
        self.tenant_id = tenant_id
        self.limit = limit
        self.admitted = admitted
        self.window_id = window_id


class IdempotencyConflictError(AIQuotaError):
    """Raised when an idempotency key is reused with a different request payload."""
    pass


class ScopeMismatchError(AIQuotaError):
    """Raised when an idempotency key or reservation is replayed across actors or tenants."""
    pass


class ReservationNotFoundError(AIQuotaError):
    """Raised when the specified reservation does not exist."""
    pass


class InvalidReservationTransitionError(AIQuotaError):
    """Raised when attempting an unauthorized status transition."""
    pass


class QuotaStoreUnavailableError(AIQuotaError):
    """Raised when the quota storage layer fails (fails closed)."""
    pass


def _as_utc_naive(dt: datetime | None) -> datetime:
    """Normalize a datetime to UTC naive datetime."""
    if dt is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def compute_request_fingerprint(payload: Any) -> str:
    """Compute a deterministic SHA-256 fingerprint for a request payload."""
    if payload is None:
        raw = b""
    elif isinstance(payload, bytes):
        raw = payload
    elif isinstance(payload, str):
        raw = payload.strip().encode("utf-8")
    else:
        try:
            raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        except Exception:
            raw = str(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@contextmanager
def isolated_accounting_session() -> Generator[Session, None, None]:
    """Provide a dedicated, isolated database session for accounting transactions.

    This ensures accounting mutations never hold database locks over provider network
    dispatches and never commit caller clinical/financial changes on a shared session.
    """
    session = _SyncSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class AIQuotaService:
    """Canonical service for clinic-local AI daily quota reservation and accounting."""

    @staticmethod
    def get_effective_ai_daily_limit(session: Session, tenant_id: int, now_utc: datetime | None = None) -> int:
        """Resolve the current effective daily AI request limit for the tenant.

        Essential: 2, Professional: 10, Business: 30.
        Defaults to 0 if inactive, missing, or AI disabled.
        """
        tenant = session.get(models.Tenant, tenant_id)
        if not tenant or not tenant.is_active:
            return 0

        plan_id = tenant.plan_id
        if tenant.future_plan_id and tenant.future_plan_start_date and _as_utc_naive(tenant.future_plan_start_date) <= _as_utc_naive(now_utc):
            plan_id = tenant.future_plan_id
        plan = session.get(models.SubscriptionPlan, plan_id) if plan_id else None

        if plan is None or not plan.is_ai_enabled:
            return 0
        return max(0, int(plan.ai_daily_limit or 0))

    @staticmethod
    def cached_analysis(reservation):
        if reservation.status != ReservationStatus.CONSUMED.value:
            return None
        try:
            payload = json.loads(reservation.reconciliation_notes or "null")
        except (ValueError, TypeError):
            return None
        if isinstance(payload, dict) and payload.get("kind") == "analysis_result_v1" and isinstance(payload.get("message"), str):
            return payload["message"]
        return None

    @classmethod
    def get_or_create_active_window(
        cls,
        session: Session,
        tenant_id: int,
        now_utc: datetime | None = None,
        for_update: bool = False,
    ) -> AIQuotaWindow:
        """Retrieve the active quota window covering now_utc, or create a stable one.

        Boundaries remain stable through mid-day timezone edits; a changed timezone
        applies at the next window transition so no second budget is created mid-day.
        """
        now_naive = _as_utc_naive(now_utc)

        # 1. Look for existing window covering now_naive: [start_utc, end_utc)
        query = session.query(AIQuotaWindow).filter(
            AIQuotaWindow.tenant_id == tenant_id,
            AIQuotaWindow.start_utc <= now_naive,
            now_naive < AIQuotaWindow.end_utc,
        )
        if for_update:
            query = query.with_for_update().populate_existing()
        window = query.first()
        if window:
            return window

        # 2. Check tenant timezone snapshot
        tenant = session.get(models.Tenant, tenant_id)
        tz_name = (tenant.timezone if tenant and tenant.timezone else DEFAULT_TENANT_TIMEZONE).strip()
        resolve_timezone(tz_name)

        # 3. Compute tenant local date and start/end UTC bounds for the day
        local_date = tenant_local_date(tz_name, now_utc=now_naive)
        start_utc, end_utc = tenant_day_utc_bounds_naive(tz_name, local_date=local_date, now_utc=now_naive)

        # 4. Check the latest existing window to prevent mid-day overlaps on timezone shifts
        latest_query = (
            session.query(AIQuotaWindow)
            .filter(AIQuotaWindow.tenant_id == tenant_id)
            .order_by(AIQuotaWindow.end_utc.desc())
        )
        if for_update:
            latest_query = latest_query.with_for_update().populate_existing()
        latest_window = latest_query.first()
        if latest_window:
            # If current time is still before the latest window ended, use it
            if now_naive < latest_window.end_utc:
                return latest_window
            # If the new window start is before latest_window.end_utc, clamp to latest end
            if start_utc < latest_window.end_utc:
                start_utc = latest_window.end_utc

        try:
            with session.begin_nested():
                new_window = AIQuotaWindow(
                    tenant_id=tenant_id,
                    local_date=local_date,
                    start_utc=start_utc,
                    end_utc=end_utc,
                    timezone=tz_name,
                    reserved_count=0,
                    consumed_count=0,
                    uncertain_count=0,
                    created_at=now_naive,
                    updated_at=now_naive,
                )
                session.add(new_window)
                session.flush()
            return new_window
        except IntegrityError:
            # If raced concurrently, query the created window
            query = session.query(AIQuotaWindow).filter(
                AIQuotaWindow.tenant_id == tenant_id,
                AIQuotaWindow.local_date == local_date,
            )
            if for_update:
                query = query.with_for_update().populate_existing()
            existing = query.first()
            if existing:
                return existing
            raise

    @classmethod
    def reserve_quota(
        cls,
        session: Session,
        tenant_id: int,
        user_id: Optional[int],
        operation: str,
        payload: Any,
        idempotency_key: Optional[str] = None,
        parent_reservation_id: Optional[str] = None,
        now_utc: Optional[datetime] = None,
    ) -> AIReservation:
        """Atomically reserve quota for a logical AI request.

        - Idempotent deduplication if same idempotency key and same fingerprint.
        - Conflict error if same idempotency key with different payload.
        - Scope mismatch error if replayed by another actor.
        - Parent linkage: confirmations and secondary provider retries consume zero extra units.
        - Enforces tenant daily limit (2 / 10 / 30) atomically using PostgreSQL row lock.
        """
        now_naive = _as_utc_naive(now_utc)
        fingerprint = compute_request_fingerprint(payload)
        if parent_reservation_id:
            idempotency_key = "child_" + compute_request_fingerprint([parent_reservation_id, user_id, operation, fingerprint])

        try:
            tenant = session.query(models.Tenant).filter(
                models.Tenant.id == tenant_id
            ).with_for_update().populate_existing().one_or_none()
            if tenant is None:
                raise QuotaStoreUnavailableError("Tenant is unavailable")
            if idempotency_key:
                existing = session.query(AIReservation).filter(
                    AIReservation.tenant_id == tenant_id,
                    AIReservation.idempotency_key == idempotency_key,
                ).populate_existing().first()
                if existing:
                    if existing.user_id != user_id:
                        raise ScopeMismatchError("Reservation belongs to another actor")
                    if existing.operation != operation or existing.request_fingerprint != fingerprint:
                        raise IdempotencyConflictError("Idempotency key payload or operation changed")
                    existing.is_replay = True
                    session.commit()
                    return existing
            # 1. Parent reservation linkage (confirmation or tool work)
            if parent_reservation_id:
                parent = (
                    session.query(AIReservation)
                    .filter(AIReservation.reservation_id == parent_reservation_id)
                    .first()
                )
                if parent and parent.tenant_id == tenant_id and parent.user_id == user_id:
                    # If parent already reserved or consumed, this secondary action adds 0 units
                    if parent.status in (ReservationStatus.RESERVED.value, ReservationStatus.CONSUMED.value):
                        child_reservation = AIReservation(
                            reservation_id=str(uuid4()),
                            tenant_id=tenant_id,
                            window_id=parent.window_id,
                            user_id=user_id,
                            operation=operation,
                            request_fingerprint=fingerprint,
                            idempotency_key=idempotency_key,
                            parent_reservation_id=parent_reservation_id,
                            status=ReservationStatus.RESERVED.value,
                            units=0,
                            created_at=now_naive,
                            updated_at=now_naive,
                            finalized_at=now_naive,
                            reconciliation_notes="Linked secondary action; zero units consumed.",
                        )
                        session.add(child_reservation)
                        session.commit()
                        return child_reservation

            # 2. Idempotency Key Check
            if idempotency_key:
                existing = (
                    session.query(AIReservation)
                    .filter(
                        AIReservation.tenant_id == tenant_id,
                        AIReservation.idempotency_key == idempotency_key,
                    )
                    .first()
                )
                if existing:
                    # Scope check: same tenant + actor
                    if existing.user_id != user_id:
                        raise ScopeMismatchError(
                            f"Idempotency key '{idempotency_key}' cannot be replayed by a different actor."
                        )
                    # Fingerprint check: same payload
                    if existing.request_fingerprint != fingerprint:
                        raise IdempotencyConflictError(
                            f"Idempotency key '{idempotency_key}' reused with a different request payload."
                        )
                    existing.is_replay = True
                    return existing

            # 3. Active Window & Atomic Reservation Lock
            locked_window = cls.get_or_create_active_window(
                session, tenant_id=tenant_id, now_utc=now_naive, for_update=True
            )

            # 4. Check Capacity
            limit = cls.get_effective_ai_daily_limit(session, tenant_id, now_utc=now_naive)
            total_admitted = locked_window.reserved_count + locked_window.consumed_count + locked_window.uncertain_count

            if total_admitted >= limit:
                raise AIQuotaExhaustedError(
                    tenant_id=tenant_id,
                    limit=limit,
                    admitted=total_admitted,
                    window_id=locked_window.id,
                )

            # 5. Insert Reservation Row
            reservation = AIReservation(
                reservation_id=str(uuid4()),
                tenant_id=tenant_id,
                window_id=locked_window.id,
                user_id=user_id,
                operation=operation,
                request_fingerprint=fingerprint,
                idempotency_key=idempotency_key,
                parent_reservation_id=parent_reservation_id,
                status=ReservationStatus.RESERVED.value,
                units=1,
                created_at=now_naive,
                updated_at=now_naive,
            )
            session.add(reservation)
            locked_window.reserved_count += 1
            locked_window.updated_at = now_naive

            session.commit()
            reservation.is_replay = False
            return reservation

        except (AIQuotaExhaustedError, IdempotencyConflictError, ScopeMismatchError):
            session.rollback()
            raise
        except OperationalError as exc:
            session.rollback()
            raise QuotaStoreUnavailableError(f"Database operational error during quota reservation: {exc}") from exc
        except Exception:
            session.rollback()
            raise

    @classmethod
    def finalize_reservation(
        cls,
        session: Session,
        reservation_id: str,
        status: ReservationStatus | str,
        error_reason: Optional[str] = None,
        reconciliation_notes: Optional[str] = None,
        now_utc: Optional[datetime] = None,
    ) -> AIReservation:
        """Finalize or update a reservation state idempotently."""
        now_naive = _as_utc_naive(now_utc)
        if hasattr(status, "value"):
            target_status = status.value
        else:
            target_status = str(status).upper()

        try:
            reservation = (
                session.query(AIReservation)
                .filter(AIReservation.reservation_id == reservation_id)
                .with_for_update()
                .first()
            )
            if not reservation:
                raise ReservationNotFoundError(f"Reservation '{reservation_id}' not found.")

            # Idempotent replay if status matches
            if reservation.status == target_status:
                return reservation

            # Validate state transition
            allowed = ALLOWED_TRANSITIONS.get(reservation.status, set())
            if target_status not in allowed:
                raise InvalidReservationTransitionError(
                    f"Cannot transition reservation from '{reservation.status}' to '{target_status}'."
                )

            # Lock quota window to adjust counters
            window = (
                session.query(AIQuotaWindow)
                .filter(AIQuotaWindow.id == reservation.window_id)
                .with_for_update()
                .populate_existing()
                .one()
            )

            units = reservation.units
            old_status = reservation.status

            if old_status == ReservationStatus.RESERVED.value:
                window.reserved_count = max(0, window.reserved_count - units)
                if target_status == ReservationStatus.CONSUMED.value:
                    window.consumed_count += units
                elif target_status == ReservationStatus.UNCERTAIN.value:
                    window.uncertain_count += units
                elif target_status == ReservationStatus.RELEASED.value:
                    # Released: units returned to available capacity!
                    pass

            elif old_status == ReservationStatus.UNCERTAIN.value:
                # Reconciling an uncertain reservation
                window.uncertain_count = max(0, window.uncertain_count - units)
                if target_status == ReservationStatus.CONSUMED.value:
                    window.consumed_count += units
                elif target_status == ReservationStatus.RELEASED.value:
                    # Released: capacity returned!
                    pass

            reservation.status = target_status
            reservation.updated_at = now_naive
            reservation.finalized_at = now_naive
            if error_reason:
                reservation.error_reason = error_reason[:255]
            if reconciliation_notes:
                existing_notes = reservation.reconciliation_notes or ""
                sep = " | " if existing_notes else ""
                try:
                    typed_result = json.loads(reconciliation_notes)
                except (ValueError, TypeError):
                    typed_result = None
                if isinstance(typed_result, dict) and typed_result.get("kind") in {"scribe_result_v1", "analysis_result_v1"}:
                    reservation.reconciliation_notes = reconciliation_notes
                else:
                    reservation.reconciliation_notes = f"{existing_notes}{sep}{reconciliation_notes}"

            window.updated_at = now_naive
            session.commit()
            return reservation

        except (ReservationNotFoundError, InvalidReservationTransitionError):
            session.rollback()
            raise
        except OperationalError as exc:
            session.rollback()
            raise QuotaStoreUnavailableError(f"Database operational error during finalization: {exc}") from exc
        except Exception:
            session.rollback()
            raise

    @classmethod
    def reconcile_uncertain_reservation(
        cls,
        session: Session,
        reservation_id: str,
        resolution: str,
        notes: str,
        actor_id: Optional[int] = None,
    ) -> AIReservation:
        """Super Admin or reconciliation worker resolves an UNCERTAIN reservation."""
        if resolution not in (ReservationStatus.CONSUMED.value, ReservationStatus.RELEASED.value):
            raise ValueError(f"Invalid reconciliation resolution '{resolution}'. Must be CONSUMED or RELEASED.")
        audit_note = f"Reconciled to {resolution} by actor {actor_id or 'system'}: {notes}"
        return cls.finalize_reservation(
            session=session,
            reservation_id=reservation_id,
            status=resolution,
            reconciliation_notes=audit_note,
        )

    @classmethod
    async def read_window_usage(cls, db: AsyncSession, tenant, now_utc=None) -> Dict[str, Any]:
        """Read a snapshot without creating a window or committing caller state."""
        from backend.services.subscription_period import resolve_subscription_period

        now = _as_utc_naive(now_utc)
        window = (await db.execute(select(AIQuotaWindow).where(
            AIQuotaWindow.tenant_id == tenant.id,
            AIQuotaWindow.start_utc <= now, AIQuotaWindow.end_utc > now,
        ).order_by(AIQuotaWindow.end_utc.desc()))).scalars().first()
        period = resolve_subscription_period(tenant, now)
        plan = tenant.__dict__.get("future_plan") if period.future_started else tenant.__dict__.get("subscription_plan")
        limit = getattr(plan, "ai_daily_limit", 0) or 0
        limit = max(0, limit) if plan and plan.is_ai_enabled and tenant.plan_id else 0
        tz = window.timezone if window else (tenant.timezone or DEFAULT_TENANT_TIMEZONE)
        start, end = (window.start_utc, window.end_utc) if window else tenant_day_utc_bounds_naive(tz, now_utc=now)
        if not window:
            latest = (await db.execute(select(AIQuotaWindow).where(
                AIQuotaWindow.tenant_id == tenant.id,
            ).order_by(AIQuotaWindow.end_utc.desc()))).scalars().first()
            if latest and latest.end_utc > start:
                start = latest.end_utc
        reserved = window.reserved_count if window else 0
        consumed = window.consumed_count if window else 0
        uncertain = window.uncertain_count if window else 0
        admitted = reserved + consumed + uncertain
        return {"quota_source": "ai_quota_windows", "reserved_count": reserved,
                "consumed_count": consumed, "uncertain_count": uncertain,
                "admitted_count": admitted, "daily_limit": limit,
                "remaining_quota": max(0, limit - admitted),
                "start_utc": start.isoformat() + "Z", "end_utc": end.isoformat() + "Z",
                "timezone": tz, "is_exhausted": admitted >= limit}

    @classmethod
    def get_window_usage(
        cls,
        session: Session,
        tenant_id: int,
        now_utc: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Return truthful billing-grade quota window usage for Super Admin and tenant detail."""
        now_naive = _as_utc_naive(now_utc)
        window = cls.get_or_create_active_window(session, tenant_id=tenant_id, now_utc=now_naive)
        limit = cls.get_effective_ai_daily_limit(session, tenant_id, now_utc=now_naive)

        admitted = window.admitted_count
        remaining = max(0, limit - admitted)

        return {
            "window_id": window.id,
            "tenant_id": window.tenant_id,
            "local_date": window.local_date.isoformat(),
            "start_utc": window.start_utc.isoformat(),
            "end_utc": window.end_utc.isoformat(),
            "timezone": window.timezone,
            "reserved_count": window.reserved_count,
            "consumed_count": window.consumed_count,
            "uncertain_count": window.uncertain_count,
            "admitted_count": admitted,
            "daily_limit": limit,
            "remaining_quota": remaining,
            "is_exhausted": bool(admitted >= limit),
            "quota_source": "ai_quota_windows",
        }

    @classmethod
    async def async_reserve_quota(
        cls,
        bind: Any,
        tenant_id: int,
        user_id: Optional[int],
        operation: str,
        payload: Any,
        idempotency_key: Optional[str] = None,
        parent_reservation_id: Optional[str] = None,
        now_utc: Optional[datetime] = None,
    ) -> AIReservation:
        """Reserve quota asynchronously in an isolated session."""
        target_bind = bind.bind if hasattr(bind, "bind") else (bind or async_engine)
        async with AsyncSession(bind=target_bind, expire_on_commit=False) as session:
            return await session.run_sync(
                lambda s: cls.reserve_quota(
                    session=s,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    operation=operation,
                    payload=payload,
                    idempotency_key=idempotency_key,
                    parent_reservation_id=parent_reservation_id,
                    now_utc=now_utc,
                )
            )

    @classmethod
    async def async_finalize_reservation(
        cls,
        bind: Any,
        reservation_id: str,
        status: Any,
        error_reason: Optional[str] = None,
        reconciliation_notes: Optional[str] = None,
        now_utc: Optional[datetime] = None,
    ) -> AIReservation:
        """Finalize reservation asynchronously in an isolated session."""
        target_bind = bind.bind if hasattr(bind, "bind") else (bind or async_engine)
        async with AsyncSession(bind=target_bind, expire_on_commit=False) as session:
            return await session.run_sync(
                lambda s: cls.finalize_reservation(
                    session=s,
                    reservation_id=reservation_id,
                    status=status,
                    error_reason=error_reason,
                    reconciliation_notes=reconciliation_notes,
                    now_utc=now_utc,
                )
            )
