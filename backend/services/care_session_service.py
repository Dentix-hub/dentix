"""
Care Session Service (Slice S18).
Domain service for chairside CareSession lifecycle commands and queries (G10-M01, G10-M02, G10-M03, G10-M18).

Enforces:
- Tenant isolation and patient visibility scoping (404 on mismatch).
- Fail-closed feature flag gate: clinical_vnext_native_writes (404 when disabled).
- Concurrency protection (Decision D3 / G10-M18): strictly one active ('in_progress') CareSession per patient.
- Advisory transaction lock on PostgreSQL (pg_advisory_xact_lock) for serialization.
- Optimistic locking (StaleDataError) and IntegrityError mapped to 409 Conflict.
- Direct parent patient verification for appointment_id (preventing cross-patient appointment link).
- Append-only ClinicalEvent audit logging for session lifecycle events.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService
from backend.services.patient_access_service import ensure_patient_visible

ALLOWED_SESSION_TRANSITIONS = {
    "in_progress": {"paused", "completed", "cancelled"},
    "paused": {"in_progress", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


class CareSessionService:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        current_user: Optional[models.User] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user
        self.current_user_id = getattr(current_user, "id", None)

    async def _get_active_current_user(self) -> Optional[models.User]:
        """Reload user if expired or detached from AsyncSession per R04."""
        if not self.current_user or not self.current_user_id:
            return self.current_user
        state = inspect(self.current_user, raiseerr=False)
        if state and (state.expired or state.detached or bool(state.expired_attributes)):
            stmt = select(models.User).where(
                models.User.id == self.current_user_id,
                models.User.tenant_id == self.tenant_id,
            )
            reloaded = (await self.db.execute(stmt)).scalar_one_or_none()
            if reloaded:
                self.current_user = reloaded
        return self.current_user

    async def is_native_writes_enabled(self) -> bool:
        """Check if native writes feature flag is enabled for this tenant."""
        return await FeatureFlagService.is_feature_enabled(
            self.db, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, self.tenant_id
        )

    async def ensure_native_writes_enabled(self) -> None:
        """Fail-closed gate when clinical_vnext_native_writes is OFF (404)."""
        if not await self.is_native_writes_enabled():
            raise HTTPException(
                status_code=404,
                detail="Clinical native writes are disabled",
            )

    async def _verify_patient(self, patient_id: int) -> None:
        """Verify patient exists and is visible to the current user."""
        user = await self._get_active_current_user()
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        await ensure_patient_visible(self.db, user, patient_id)

    async def _acquire_advisory_lock(self, key: str) -> None:
        """
        Acquire PostgreSQL transaction-level advisory lock (R05).
        Serializes concurrent requests for the same (tenant_id, key).
        No-op on SQLite.
        """
        bind = getattr(self.db, "bind", None)
        if bind is None and hasattr(self.db, "get_bind"):
            try:
                bind = self.db.get_bind()
            except Exception:
                bind = None
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name == "postgresql":
            lock_key = f"{self.tenant_id}:{key}"
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )

    async def _verify_appointment(self, patient_id: int, appointment_id: int) -> models.Appointment:
        """Validate appointment belongs to the same tenant and patient."""
        stmt = select(models.Appointment).where(
            models.Appointment.id == appointment_id,
            models.Appointment.tenant_id == self.tenant_id,
            models.Appointment.patient_id == patient_id,
            models.Appointment.is_deleted.is_(False),
        )
        appt = (await self.db.execute(stmt)).scalar_one_or_none()
        if not appt:
            raise HTTPException(
                status_code=404,
                detail="Appointment not found or does not belong to patient",
            )
        return appt

    async def start_session(
        self, patient_id: int, data: schemas.CareSessionCreate
    ) -> models.CareSession:
        """
        Start a new care session for a patient (G10-M02).
        Enforces Decision D3 (G10-M18): strictly one active ('in_progress') care session per patient.
        Returns 409 Conflict if another session is already in_progress.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        if data.appointment_id is not None:
            await self._verify_appointment(patient_id, data.appointment_id)

        # Acquire concurrency lock for patient care sessions (R05)
        await self._acquire_advisory_lock(f"care_session:{patient_id}")

        # D3 guard: check if active session already exists for this patient
        stmt = select(models.CareSession).where(
            models.CareSession.tenant_id == self.tenant_id,
            models.CareSession.patient_id == patient_id,
            models.CareSession.status == "in_progress",
        )
        existing_active = (await self.db.execute(stmt)).scalars().first()
        if existing_active:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"An active care session is already in progress for this patient (session {existing_active.id})",
                    "active_session_id": existing_active.id,
                },
            )

        now = datetime.now(timezone.utc)
        user = await self._get_active_current_user()
        session = models.CareSession(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            appointment_id=data.appointment_id,
            provider_user_id=user.id if user else None,
            status="in_progress",
            started_at=now,
            notes=data.notes,
        )
        self.db.add(session)

        try:
            await self.db.flush()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict",
            ) from exc

        # Audit event
        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session.id,
            event_type="care_session_started",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "session_id": session.id,
                "appointment_id": session.appointment_id,
                "provider_user_id": session.provider_user_id,
                "status": "in_progress",
            },
            notes=session.notes,
        )
        self.db.add(event)

        try:
            await self.db.commit()
            await self.db.refresh(session)
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict during commit",
            ) from exc

        return session

    async def finish_session(
        self, patient_id: int, session_id: int, data: schemas.CareSessionFinish
    ) -> models.CareSession:
        """
        Finish an active/paused care session (G10-M03).
        Marks session as 'completed' and records finished_at.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = await self.get_session(patient_id, session_id)
        if session.status not in ("in_progress", "paused"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot finish care session with status '{session.status}'",
            )

        now = datetime.now(timezone.utc)
        user = await self._get_active_current_user()
        session.status = "completed"
        session.finished_at = now
        if data.notes:
            if session.notes:
                session.notes = f"{session.notes}\n{data.notes}"
            else:
                session.notes = data.notes

        try:
            await self.db.flush()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict during finish",
            ) from exc

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session.id,
            event_type="care_session_finished",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "session_id": session.id,
                "status": "completed",
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "finished_at": now.isoformat(),
            },
            notes=data.notes,
        )
        self.db.add(event)

        try:
            await self.db.commit()
            await self.db.refresh(session)
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict during finish commit",
            ) from exc

        return session

    async def transition_session(
        self, patient_id: int, session_id: int, data: schemas.CareSessionTransition
    ) -> models.CareSession:
        """
        Transition care session to another status (paused, in_progress, completed, cancelled).
        Enforces Decision D3: if transitioning to 'in_progress', ensures no other session is in_progress.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = await self.get_session(patient_id, session_id)
        from_status = session.status
        to_status = data.to_status

        allowed = ALLOWED_SESSION_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid session status transition from '{from_status}' to '{to_status}'",
            )

        # D3 guard when transitioning back to in_progress
        if to_status == "in_progress":
            await self._acquire_advisory_lock(f"care_session:{patient_id}")
            stmt = select(models.CareSession).where(
                models.CareSession.tenant_id == self.tenant_id,
                models.CareSession.patient_id == patient_id,
                models.CareSession.status == "in_progress",
                models.CareSession.id != session.id,
            )
            other_active = (await self.db.execute(stmt)).scalars().first()
            if other_active:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": f"An active care session is already in progress for this patient (session {other_active.id})",
                        "active_session_id": other_active.id,
                    },
                )

        now = datetime.now(timezone.utc)
        user = await self._get_active_current_user()
        session.status = to_status
        if to_status == "completed":
            session.finished_at = now

        if data.notes:
            if session.notes:
                session.notes = f"{session.notes}\n{data.notes}"
            else:
                session.notes = data.notes

        try:
            await self.db.flush()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict during status transition",
            ) from exc

        event_type = (
            "care_session_resumed"
            if (from_status == "paused" and to_status == "in_progress")
            else f"care_session_{to_status}"
        )
        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session.id,
            event_type=event_type,
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "session_id": session.id,
                "from_status": from_status,
                "to_status": to_status,
            },
            notes=data.notes,
        )
        self.db.add(event)

        try:
            await self.db.commit()
            await self.db.refresh(session)
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict during status transition commit",
            ) from exc

        return session

    async def get_session(self, patient_id: int, session_id: int) -> models.CareSession:
        """Retrieve a care session by ID with tenant and patient scoping."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = select(models.CareSession).where(
            models.CareSession.id == session_id,
            models.CareSession.tenant_id == self.tenant_id,
            models.CareSession.patient_id == patient_id,
        )
        session = (await self.db.execute(stmt)).scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Care session not found")
        return session

    async def get_active_session(self, patient_id: int) -> Optional[models.CareSession]:
        """Retrieve the currently active ('in_progress') care session for a patient, if any."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = (
            select(models.CareSession)
            .where(
                models.CareSession.tenant_id == self.tenant_id,
                models.CareSession.patient_id == patient_id,
                models.CareSession.status == "in_progress",
            )
            .order_by(models.CareSession.id.desc())
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def list_sessions(
        self, patient_id: int, status: Optional[str] = None
    ) -> List[models.CareSession]:
        """List care sessions for a patient with optional status filtering."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = select(models.CareSession).where(
            models.CareSession.tenant_id == self.tenant_id,
            models.CareSession.patient_id == patient_id,
        )
        if status:
            stmt = stmt.where(models.CareSession.status == status)

        stmt = stmt.order_by(models.CareSession.created_at.desc(), models.CareSession.id.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
