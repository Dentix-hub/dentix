"""
Care Session Service (Slices S18 & S19).
Domain service for chairside CareSession lifecycle, steps, and observations
(G10-M01, G10-M02, G10-M03, G10-M04, G10-M05, G10-M07, G10-M15, G10-M17, G10-M18).

Enforces:
- Tenant isolation and patient visibility scoping (404 on mismatch).
- Fail-closed feature flag gate: clinical_vnext_native_writes (404 when disabled).
- Concurrency protection (Decision D3 / G10-M18): strictly one active ('in_progress') CareSession per patient.
- Advisory transaction lock on PostgreSQL (pg_advisory_xact_lock) for serialization.
- Optimistic locking (StaleDataError) and IntegrityError mapped to 409 Conflict.
- Direct parent patient verification for appointment_id and work_item_id.
- CareSession step matching for care_observations (trigger trg_co_step_care_session_match).
- Append-only ClinicalEvent audit logging for session lifecycle, step, and observation events.
- Finalization audit trail via log_admin_action (G10-M17).
- Preservation of free-text notes across sessions, steps, and observations (G10-M15).
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.clinical.workflow_templates import get_latest_template
from backend.models.clinical_core import FDI_TOOTH_KEYS
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService
from backend.services.patient_access_service import ensure_patient_visible
from backend.utils.audit_logger import log_admin_action

ALLOWED_SESSION_TRANSITIONS = {
    "in_progress": {"paused", "completed", "cancelled"},
    "paused": {"in_progress", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

ALLOWED_STEP_STATUSES = {"pending", "in_progress", "partial", "completed", "skipped"}


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

    async def _verify_work_item(self, patient_id: int, work_item_id: int) -> models.ClinicalWorkItem:
        """Validate work item belongs to the same tenant and patient."""
        stmt = select(models.ClinicalWorkItem).where(
            models.ClinicalWorkItem.id == work_item_id,
            models.ClinicalWorkItem.tenant_id == self.tenant_id,
            models.ClinicalWorkItem.patient_id == patient_id,
        )
        wi = (await self.db.execute(stmt)).scalars().first()
        if not wi:
            raise HTTPException(
                status_code=404,
                detail="Clinical work item not found or does not belong to patient",
            )
        return wi

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

    # -----------------------------------------------------------------------
    # Care Session Lifecycle Commands (Slice S18)
    # -----------------------------------------------------------------------

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

        # G10-M12 / G10-M19: Resume carryover support
        if data.resume_work_item_id is not None or data.resume_from_session_id is not None:
            resume_wi_id = data.resume_work_item_id
            if resume_wi_id is not None:
                await self._verify_work_item(patient_id, resume_wi_id)

            # Query prior steps for this work item or session
            prior_steps_query = (
                select(models.CareSessionStep)
                .join(models.CareSession)
                .where(
                    models.CareSessionStep.tenant_id == self.tenant_id,
                    models.CareSession.patient_id == patient_id,
                )
            )
            if resume_wi_id is not None:
                prior_steps_query = prior_steps_query.where(
                    models.CareSessionStep.work_item_id == resume_wi_id
                )
            elif data.resume_from_session_id is not None:
                prior_steps_query = prior_steps_query.where(
                    models.CareSessionStep.care_session_id == data.resume_from_session_id
                )

            prior_steps_query = prior_steps_query.order_by(
                models.CareSessionStep.step_order.asc(),
                models.CareSessionStep.id.asc(),
            )
            prior_steps = (await self.db.execute(prior_steps_query)).scalars().all()

            # Carry over steps into new session
            seen_step_codes = set()
            new_order = 1
            for p_step in prior_steps:
                if p_step.step_code in seen_step_codes:
                    continue
                seen_step_codes.add(p_step.step_code)

                # Preserve completed state; if partial/in_progress, keep partial/in_progress; otherwise pending
                step_status = p_step.status
                new_step = models.CareSessionStep(
                    tenant_id=self.tenant_id,
                    care_session_id=session.id,
                    work_item_id=resume_wi_id or p_step.work_item_id,
                    step_order=new_order,
                    step_code=p_step.step_code,
                    title=p_step.title,
                    status=step_status,
                    started_at=p_step.started_at,
                    completed_at=p_step.completed_at,
                    notes=f"[Resumed from Step #{p_step.step_order}] {p_step.notes or ''}".strip() if p_step.notes else None,
                )
                self.db.add(new_step)
                new_order += 1

            # Query and carry forward canal observations
            obs_query = select(models.CareObservation).where(
                models.CareObservation.tenant_id == self.tenant_id,
                models.CareObservation.patient_id == patient_id,
            )
            if resume_wi_id is not None:
                obs_query = obs_query.where(models.CareObservation.work_item_id == resume_wi_id)
            elif data.resume_from_session_id is not None:
                obs_query = obs_query.where(models.CareObservation.care_session_id == data.resume_from_session_id)

            obs_query = obs_query.order_by(models.CareObservation.recorded_at.asc())
            prior_obs = (await self.db.execute(obs_query)).scalars().all()

            for p_obs in prior_obs:
                carried_obs = models.CareObservation(
                    tenant_id=self.tenant_id,
                    patient_id=patient_id,
                    care_session_id=session.id,
                    work_item_id=resume_wi_id or p_obs.work_item_id,
                    observation_code=p_obs.observation_code,
                    tooth_key=p_obs.tooth_key,
                    structured_value=dict(p_obs.structured_value or {}),
                    notes=f"[Carried over from Session {p_obs.care_session_id}] {p_obs.notes or ''}".strip() if p_obs.notes else None,
                    recorded_by_user_id=user.id if user else None,
                )
                self.db.add(carried_obs)

            try:
                await self.db.flush()
            except (IntegrityError, StaleDataError) as exc:
                await self.db.rollback()
                await self._get_active_current_user()
                raise HTTPException(
                    status_code=409,
                    detail="Concurrent care session conflict during step carryover",
                ) from exc

        # Audit event
        event_payload = {
            "session_id": session.id,
            "appointment_id": session.appointment_id,
            "provider_user_id": session.provider_user_id,
            "status": "in_progress",
        }
        if data.resume_work_item_id is not None:
            event_payload["resume_work_item_id"] = data.resume_work_item_id
        if data.resume_from_session_id is not None:
            event_payload["resume_from_session_id"] = data.resume_from_session_id

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session.id,
            event_type="care_session_started",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload=event_payload,
            notes=session.notes,
        )
        self.db.add(event)

        try:
            await self.db.commit()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict during commit",
            ) from exc

        return await self.get_session(patient_id, session.id)

    async def finish_session(
        self, patient_id: int, session_id: int, data: schemas.CareSessionFinish
    ) -> models.CareSession:
        """
        Finish an active/paused care session (G10-M03).
        Marks session as 'completed', records finished_at, preserves notes (G10-M15),
        and records finalization audit trail via log_admin_action and ClinicalEvent (G10-M17).
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

        # G10-M14: Deterministic clinical summary generation
        summary = self.generate_session_summary(session)
        setattr(session, "summary", summary)

        # G10-M17: Finalization audit trail via log_admin_action
        log_admin_action(
            db=self.db,
            admin_user=user,
            action="FINISH_CARE_SESSION",
            entity_type="care_session",
            entity_id=session.id,
            details=f"Care session {session.id} finished for patient {patient_id}",
            new_value={
                "status": "completed",
                "summary": summary,
                "notes": session.notes,
                "finished_at": now.isoformat(),
            },
            tenant_id=self.tenant_id,
        )

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
                "summary": summary,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "finished_at": now.isoformat(),
            },
            notes=data.notes,
        )
        self.db.add(event)

        try:
            await self.db.commit()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict during finish commit",
            ) from exc

        return await self.get_session(patient_id, session.id)

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
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict during status transition commit",
            ) from exc

        return await self.get_session(patient_id, session.id)

    # -----------------------------------------------------------------------
    # Step Operations (Slice S19 / G10-M04, G10-M05, G10-M15)
    # -----------------------------------------------------------------------

    async def add_step(
        self, patient_id: int, session_id: int, data: schemas.CareSessionStepCreate
    ) -> models.CareSessionStep:
        """
        Add a structured step to a care session (G10-M04).
        Supports partial status (G10-M05) and preserves notes (G10-M15).
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = await self.get_session(patient_id, session_id)
        if session.status in ("completed", "cancelled"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot add steps to care session with terminal status '{session.status}'",
            )

        if data.status and data.status not in ALLOWED_STEP_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid step status '{data.status}'. Allowed: {sorted(ALLOWED_STEP_STATUSES)}",
            )

        if data.work_item_id is not None:
            await self._verify_work_item(patient_id, data.work_item_id)

        step_order = data.step_order
        if step_order is None or step_order <= 0:
            stmt = select(func.coalesce(func.max(models.CareSessionStep.step_order), 0)).where(
                models.CareSessionStep.tenant_id == self.tenant_id,
                models.CareSessionStep.care_session_id == session_id,
            )
            max_order = (await self.db.execute(stmt)).scalar_one()
            step_order = max_order + 1

        now = datetime.now(timezone.utc)
        step_status = data.status or "pending"
        started_at = now if step_status == "in_progress" else None
        completed_at = now if step_status in ("completed", "partial", "skipped") else None

        step = models.CareSessionStep(
            tenant_id=self.tenant_id,
            care_session_id=session_id,
            work_item_id=data.work_item_id,
            step_order=step_order,
            step_code=data.step_code.strip(),
            title=data.title.strip(),
            status=step_status,
            started_at=started_at,
            completed_at=completed_at,
            notes=data.notes,
        )
        self.db.add(step)

        try:
            await self.db.flush()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session step conflict",
            ) from exc

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session_id,
            event_type="care_session_step_added",
            occurred_at=now,
            actor_user_id=self.current_user_id,
            payload={
                "step_id": step.id,
                "step_code": step.step_code,
                "step_order": step.step_order,
                "status": step.status,
                "work_item_id": step.work_item_id,
            },
            notes=step.notes,
        )
        self.db.add(event)

        try:
            await self.db.commit()
            await self.db.refresh(step)
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session step conflict during commit",
            ) from exc

        return step

    async def update_step(
        self,
        patient_id: int,
        session_id: int,
        step_id: int,
        data: schemas.CareSessionStepUpdate,
    ) -> models.CareSessionStep:
        """
        Update an existing care session step status, notes, title, or order (G10-M04, G10-M05, G10-M15).
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = await self.get_session(patient_id, session_id)
        if session.status in ("completed", "cancelled"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update steps of care session with terminal status '{session.status}'",
            )

        stmt = select(models.CareSessionStep).where(
            models.CareSessionStep.id == step_id,
            models.CareSessionStep.care_session_id == session_id,
            models.CareSessionStep.tenant_id == self.tenant_id,
        )
        step = (await self.db.execute(stmt)).scalars().first()
        if not step:
            raise HTTPException(status_code=404, detail="Care session step not found")

        now = datetime.now(timezone.utc)
        if data.status is not None:
            if data.status not in ALLOWED_STEP_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid step status '{data.status}'. Allowed: {sorted(ALLOWED_STEP_STATUSES)}",
                )
            if data.status == "in_progress" and not step.started_at:
                step.started_at = now
            elif data.status in ("completed", "partial", "skipped") and not step.completed_at:
                step.completed_at = now
            step.status = data.status

        if data.title is not None:
            step.title = data.title.strip()
        if data.notes is not None:
            step.notes = data.notes
        if data.step_order is not None:
            step.step_order = data.step_order

        try:
            await self.db.flush()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session step conflict during update",
            ) from exc

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session_id,
            event_type="care_session_step_updated",
            occurred_at=now,
            actor_user_id=self.current_user_id,
            payload={
                "step_id": step.id,
                "step_code": step.step_code,
                "step_order": step.step_order,
                "status": step.status,
            },
            notes=step.notes,
        )
        self.db.add(event)

        try:
            await self.db.commit()
            await self.db.refresh(step)
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session step conflict during update commit",
            ) from exc

        return step

    async def apply_template(
        self,
        patient_id: int,
        session_id: int,
        data: schemas.CareSessionTemplateApply,
    ) -> List[models.CareSessionStep]:
        """
        Initialize care session steps from a workflow template (e.g. ENDO_RCT, PROS_CROWN).
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = await self.get_session(patient_id, session_id)
        if session.status in ("completed", "cancelled"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot apply templates to care session with terminal status '{session.status}'",
            )

        if data.work_item_id is not None:
            await self._verify_work_item(patient_id, data.work_item_id)

        try:
            template = get_latest_template(data.template_code)
        except Exception as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow template '{data.template_code}' not found",
            ) from exc

        # Find current max step_order
        stmt = select(func.coalesce(func.max(models.CareSessionStep.step_order), 0)).where(
            models.CareSessionStep.tenant_id == self.tenant_id,
            models.CareSessionStep.care_session_id == session_id,
        )
        base_order = (await self.db.execute(stmt)).scalar_one()

        created_steps: List[models.CareSessionStep] = []
        now = datetime.now(timezone.utc)
        for tpl_step in template.steps:
            step = models.CareSessionStep(
                tenant_id=self.tenant_id,
                care_session_id=session_id,
                work_item_id=data.work_item_id,
                step_order=base_order + tpl_step.step_order,
                step_code=tpl_step.step_code,
                title=tpl_step.title,
                status="pending",
                notes=tpl_step.description or None,
            )
            self.db.add(step)
            created_steps.append(step)

        try:
            await self.db.flush()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent conflict while applying workflow template steps",
            ) from exc

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session_id,
            event_type="care_session_template_applied",
            occurred_at=now,
            actor_user_id=self.current_user_id,
            payload={
                "template_code": data.template_code,
                "steps_created": len(created_steps),
                "work_item_id": data.work_item_id,
            },
        )
        self.db.add(event)

        try:
            await self.db.commit()
            for s in created_steps:
                await self.db.refresh(s)
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent conflict while committing workflow template steps",
            ) from exc

        return created_steps

    async def list_steps(
        self, patient_id: int, session_id: int
    ) -> List[models.CareSessionStep]:
        """List steps of a care session ordered by step_order."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)
        await self.get_session(patient_id, session_id)

        stmt = (
            select(models.CareSessionStep)
            .where(
                models.CareSessionStep.tenant_id == self.tenant_id,
                models.CareSessionStep.care_session_id == session_id,
            )
            .order_by(models.CareSessionStep.step_order.asc(), models.CareSessionStep.id.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # Observation Operations (Slice S19 / G10-M07, G10-M15)
    # -----------------------------------------------------------------------

    async def add_observation(
        self, patient_id: int, session_id: int, data: schemas.CareObservationCreate
    ) -> models.CareObservation:
        """
        Record a structured chairside observation or measurement (G10-M07, G10-M15).
        Enforces step foreign key match (trg_co_step_care_session_match) and FDI tooth key format.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = await self.get_session(patient_id, session_id)
        if session.status in ("completed", "cancelled"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot add observations to care session with terminal status '{session.status}'",
            )

        # Step validation (matching trigger trg_co_step_care_session_match)
        if data.step_id is not None:
            stmt_step = select(models.CareSessionStep).where(
                models.CareSessionStep.id == data.step_id,
                models.CareSessionStep.care_session_id == session_id,
                models.CareSessionStep.tenant_id == self.tenant_id,
            )
            step = (await self.db.execute(stmt_step)).scalars().first()
            if not step:
                raise HTTPException(
                    status_code=404,
                    detail="Step not found or does not belong to care session",
                )

        # Work item validation
        if data.work_item_id is not None:
            await self._verify_work_item(patient_id, data.work_item_id)

        # Tooth key validation
        if data.tooth_key is not None:
            if data.tooth_key not in FDI_TOOTH_KEYS:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid tooth key '{data.tooth_key}'. Must be valid FDI notation (11-48, 51-85).",
                )

        # Build structured_value
        structured_val = dict(data.structured_value or {})
        if data.surface_code:
            structured_val["surface_code"] = data.surface_code
        if data.root_id:
            structured_val["root_id"] = data.root_id
        if data.canal_id:
            structured_val["canal_id"] = data.canal_id

        now = datetime.now(timezone.utc)
        user = await self._get_active_current_user()
        obs = models.CareObservation(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session_id,
            step_id=data.step_id,
            work_item_id=data.work_item_id,
            observation_code=data.observation_code.strip(),
            tooth_key=data.tooth_key,
            structured_value=structured_val,
            notes=data.notes,
            recorded_at=now,
            recorded_by_user_id=user.id if user else None,
        )
        self.db.add(obs)

        try:
            await self.db.flush()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care observation conflict",
            ) from exc

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session_id,
            event_type="care_observation_recorded",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "observation_id": obs.id,
                "observation_code": obs.observation_code,
                "tooth_key": obs.tooth_key,
                "step_id": obs.step_id,
                "work_item_id": obs.work_item_id,
            },
            notes=obs.notes,
        )
        self.db.add(event)

        try:
            await self.db.commit()
            await self.db.refresh(obs)
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care observation conflict during commit",
            ) from exc

        return obs

    async def list_observations(
        self,
        patient_id: int,
        session_id: int,
        step_id: Optional[int] = None,
    ) -> List[models.CareObservation]:
        """List observations of a care session with optional step filtering."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)
        await self.get_session(patient_id, session_id)

        stmt = select(models.CareObservation).where(
            models.CareObservation.tenant_id == self.tenant_id,
            models.CareObservation.patient_id == patient_id,
            models.CareObservation.care_session_id == session_id,
        )
        if step_id is not None:
            stmt = stmt.where(models.CareObservation.step_id == step_id)

        stmt = stmt.order_by(models.CareObservation.recorded_at.asc(), models.CareObservation.id.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # Queries
    # -----------------------------------------------------------------------

    async def get_session(
        self, patient_id: int, session_id: int, eager_load: bool = True
    ) -> models.CareSession:
        """Retrieve a care session by ID with tenant and patient scoping."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = select(models.CareSession).where(
            models.CareSession.id == session_id,
            models.CareSession.tenant_id == self.tenant_id,
            models.CareSession.patient_id == patient_id,
        )
        if eager_load:
            stmt = stmt.execution_options(populate_existing=True).options(
                selectinload(models.CareSession.steps).selectinload(models.CareSessionStep.work_item).selectinload(models.ClinicalWorkItem.targets),
                selectinload(models.CareSession.observations),
            )
        session = (await self.db.execute(stmt)).scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Care session not found")

        if session.status == "completed":
            setattr(session, "summary", self.generate_session_summary(session))
        return session

    async def get_active_session(self, patient_id: int) -> Optional[models.CareSession]:
        """Retrieve the currently active ('in_progress') care session for a patient, if any."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = (
            select(models.CareSession)
            .execution_options(populate_existing=True)
            .options(
                selectinload(models.CareSession.steps).selectinload(models.CareSessionStep.work_item).selectinload(models.ClinicalWorkItem.targets),
                selectinload(models.CareSession.observations),
            )
            .where(
                models.CareSession.tenant_id == self.tenant_id,
                models.CareSession.patient_id == patient_id,
                models.CareSession.status == "in_progress",
            )
            .order_by(models.CareSession.id.desc())
        )
        session = (await self.db.execute(stmt)).scalars().first()
        if session:
            if session.status == "completed":
                setattr(session, "summary", self.generate_session_summary(session))
            return session
        return None

    async def list_sessions(
        self, patient_id: int, status: Optional[str] = None
    ) -> List[models.CareSession]:
        """List care sessions for a patient with optional status filtering."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = (
            select(models.CareSession)
            .options(
                selectinload(models.CareSession.steps),
                selectinload(models.CareSession.observations),
            )
            .where(
                models.CareSession.tenant_id == self.tenant_id,
                models.CareSession.patient_id == patient_id,
            )
        )
        if status:
            stmt = stmt.where(models.CareSession.status == status)

        stmt = stmt.order_by(models.CareSession.created_at.desc(), models.CareSession.id.desc())
        result = await self.db.execute(stmt)
        sessions = list(result.scalars().all())
        for s in sessions:
            if s.status == "completed":
                setattr(s, "summary", self.generate_session_summary(s))
        return sessions

    # -----------------------------------------------------------------------
    # Summary Generation & Resume Engine (Slice S21 / G10-M12, G10-M14)
    # -----------------------------------------------------------------------

    def generate_session_summary(self, session: models.CareSession) -> str:
        """
        Deterministic template string clinical summary generator (G10-M14).
        Avoids LLM/AI inside transactional path. Produces a structured summary
        of procedure, completed/partial steps, canal measurements, and notes.
        """
        parts = []

        steps = sorted(session.steps or [], key=lambda s: s.step_order)
        completed_steps = [s for s in steps if s.status == "completed"]
        partial_steps = [s for s in steps if s.status == "partial"]
        skipped_steps = [s for s in steps if s.status == "skipped"]
        pending_steps = [s for s in steps if s.status in ("pending", "in_progress")]

        # Determine procedure title & tooth key
        tooth_str = ""
        procedure_code = None
        for s in steps:
            if getattr(s, "work_item", None):
                wi = s.work_item
                procedure_code = wi.code
                targets = getattr(wi, "targets", []) or []
                if targets:
                    tooth_str = f" on Tooth {targets[0].tooth_key}"
                break

        if not tooth_str and session.observations:
            for obs in session.observations:
                if obs.tooth_key:
                    tooth_str = f" on Tooth {obs.tooth_key}"
                    break

        header = f"{procedure_code or 'Clinical Care Session'}{tooth_str}"
        parts.append(header)

        # Steps summary
        if steps:
            step_summary = f"{len(completed_steps)}/{len(steps)} steps completed"
            completed_names = [s.title or s.step_code for s in completed_steps]
            if completed_names:
                step_summary += f" ({', '.join(completed_names)})"
            if partial_steps:
                partial_names = [f"{s.title or s.step_code} (partial)" for s in partial_steps]
                step_summary += f"; In progress: {', '.join(partial_names)}"
            if pending_steps:
                pending_names = [s.title or s.step_code for s in pending_steps]
                step_summary += f"; Remaining: {', '.join(pending_names)}"
            if skipped_steps:
                skipped_names = [s.title or s.step_code for s in skipped_steps]
                step_summary += f"; Skipped: {', '.join(skipped_names)}"
            parts.append(f"Steps: {step_summary}")

        # Observations summary (especially canal working lengths)
        obs_list = session.observations or []
        canal_obs = [
            o for o in obs_list
            if o.observation_code in ("working_length", "canal_measurement")
            or (isinstance(o.structured_value, dict) and (o.structured_value.get("length_mm") is not None or o.structured_value.get("canal_id")))
        ]
        if canal_obs:
            canal_parts = []
            for o in canal_obs:
                sv = o.structured_value or {}
                canal_id = getattr(o, "canal_id", None) or sv.get("canal_id") or getattr(o, "root_id", None) or sv.get("root_id") or "Canal"
                length = sv.get("length_mm")
                maf = sv.get("maf")
                ref = sv.get("reference_point")
                detail = f"{canal_id}: {length}mm" if length is not None else str(canal_id)
                extras = []
                if maf:
                    extras.append(f"MAF {maf}")
                if ref:
                    extras.append(f"ref {ref}")
                if extras:
                    detail += f" ({', '.join(extras)})"
                canal_parts.append(detail)
            parts.append(f"Canals: {', '.join(canal_parts)}")

        # Free-text clinical notes
        if session.notes:
            cleaned_notes = session.notes.strip()
            if cleaned_notes and not cleaned_notes.startswith("[CARE SESSION SUMMARY]"):
                parts.append(f"Notes: {cleaned_notes}")

        return " | ".join(parts)

    async def get_resumable_context(self, patient_id: int) -> dict:
        """
        Care Session Resume Engine (G10-M12).
        Returns active/paused session and active ClinicalWorkItem rows with their
        recorded steps and canal observations for one-click chairside treatment resumption.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        # 1. Query active session
        stmt_active = (
            select(models.CareSession)
            .options(
                selectinload(models.CareSession.steps),
                selectinload(models.CareSession.observations),
            )
            .where(
                models.CareSession.tenant_id == self.tenant_id,
                models.CareSession.patient_id == patient_id,
                models.CareSession.status == "in_progress",
            )
            .order_by(models.CareSession.id.desc())
        )
        active_session = (await self.db.execute(stmt_active)).scalars().first()
        if active_session:
            setattr(active_session, "summary", self.generate_session_summary(active_session))

        # 2. Query paused session
        stmt_paused = (
            select(models.CareSession)
            .options(
                selectinload(models.CareSession.steps),
                selectinload(models.CareSession.observations),
            )
            .where(
                models.CareSession.tenant_id == self.tenant_id,
                models.CareSession.patient_id == patient_id,
                models.CareSession.status == "paused",
            )
            .order_by(models.CareSession.id.desc())
        )
        paused_session = (await self.db.execute(stmt_paused)).scalars().first()
        if paused_session:
            setattr(paused_session, "summary", self.generate_session_summary(paused_session))

        # 3. Query active or resumable work items
        wi_stmt = (
            select(models.ClinicalWorkItem)
            .options(
                selectinload(models.ClinicalWorkItem.targets),
                selectinload(models.ClinicalWorkItem.session_steps),
                selectinload(models.ClinicalWorkItem.observations),
            )
            .where(
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
                models.ClinicalWorkItem.patient_id == patient_id,
                models.ClinicalWorkItem.kind == "procedure",
                models.ClinicalWorkItem.status.in_(["active", "in_progress", "proposed"]),
            )
            .order_by(models.ClinicalWorkItem.updated_at.desc(), models.ClinicalWorkItem.id.desc())
        )
        work_items = (await self.db.execute(wi_stmt)).scalars().all()

        items = []
        for wi in work_items:
            steps = sorted(wi.session_steps or [], key=lambda s: s.step_order)
            obs = list(wi.observations or [])

            tooth_key = wi.targets[0].tooth_key if wi.targets else None
            surface_code = wi.targets[0].surface_code if wi.targets else None

            # If work item has no directly linked steps or observations, check if recent session had them targeting this tooth
            if not steps and tooth_key:
                # Fallback: check care session steps or observations matching this tooth
                alt_obs_stmt = (
                    select(models.CareObservation)
                    .where(
                        models.CareObservation.tenant_id == self.tenant_id,
                        models.CareObservation.patient_id == patient_id,
                        models.CareObservation.tooth_key == tooth_key,
                    )
                    .order_by(models.CareObservation.recorded_at.asc())
                )
                alt_obs = list((await self.db.execute(alt_obs_stmt)).scalars().all())
                if alt_obs:
                    obs = alt_obs

            # Only include work items that have either session steps, observations, or are active/in_progress procedures
            if not steps and not obs and wi.status not in ("active", "in_progress"):
                continue

            completed_steps = [s for s in steps if s.status == "completed"]
            remaining_steps = [s for s in steps if s.status != "completed"]

            # Determine last session info
            last_session_id = None
            last_session_at = None
            last_notes = None
            all_records = list(steps) + list(obs)
            if all_records:
                latest_record = max(all_records, key=lambda r: getattr(r, "created_at", None) or datetime.min.replace(tzinfo=timezone.utc))
                last_session_id = getattr(latest_record, "care_session_id", None)

            if last_session_id:
                sess = (await self.db.execute(
                    select(models.CareSession).where(
                        models.CareSession.id == last_session_id,
                        models.CareSession.tenant_id == self.tenant_id,
                    )
                )).scalars().first()
                if sess:
                    last_session_at = sess.finished_at or sess.updated_at or sess.started_at
                    last_notes = sess.notes

            next_step_title = remaining_steps[0].title if remaining_steps else None
            summary_str = f"{wi.code} on Tooth {tooth_key or 'N/A'}: {len(completed_steps)}/{len(steps)} steps completed"
            if next_step_title:
                summary_str += f". Next: {next_step_title}"

            items.append({
                "work_item_id": wi.id,
                "procedure_code": wi.code,
                "tooth_key": tooth_key,
                "surface_code": surface_code,
                "title": wi.code,
                "status": wi.status,
                "total_steps": len(steps),
                "completed_steps_count": len(completed_steps),
                "completed_steps": completed_steps,
                "remaining_steps": remaining_steps,
                "observations": obs,
                "last_session_id": last_session_id,
                "last_session_at": last_session_at,
                "last_notes": last_notes,
                "summary": summary_str,
                "next_step_title": next_step_title,
            })

        has_resumable = bool(active_session or paused_session or items)

        return {
            "has_resumable": has_resumable,
            "active_session": active_session,
            "paused_session": paused_session,
            "items": items,
        }
