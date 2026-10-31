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

from copy import deepcopy
from datetime import date, datetime, timezone
import re
from typing import Any, List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from backend import models, schemas
from backend.clinical.workflow_templates import get_latest_template
from backend.clinical.step_identity import historical_step_identity
from backend.models.clinical_core import FDI_TOOTH_KEYS
from backend.services.clinical_workspace_service import FEATURE_FLAG_CLINICAL_NATIVE_WRITES
from backend.services.feature_service import FeatureFlagService
from backend.services.patient_access_service import ensure_patient_visible
from backend.services.tenant_time_service import get_tenant_timezone
from backend.utils.audit_logger import log_admin_action
from backend.utils.tenant_time import tenant_day_utc_bounds_naive

ALLOWED_SESSION_TRANSITIONS = {
    "in_progress": {"paused", "completed", "cancelled"},
    "paused": {"in_progress", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

ALLOWED_STEP_STATUSES = {"pending", "in_progress", "partial", "completed", "skipped"}


class CareSessionPresentation:
    """
    Presentation wrapper for a CareSession that provides projected/effective
    observation response copies/DTOs without mutating underlying persistence entities.
    """
    def __init__(self, raw_session: models.CareSession, observations: list):
        self._raw = raw_session
        self.observations = observations
        if hasattr(raw_session, "summary"):
            self.summary = raw_session.summary

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("_raw", "observations", "summary"):
            super().__setattr__(name, value)
        else:
            setattr(self._raw, name, value)

    def __repr__(self) -> str:
        return f"<CareSessionPresentation id={getattr(self, 'id', None)} status={getattr(self, 'status', None)}>"


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
        Supports multi-procedure association (care_session_procedures), historical past visit recording,
        and procedure-scoped step/observation carryover without deduplicating repeated occurrences.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        if data.appointment_id is not None:
            await self._verify_appointment(patient_id, data.appointment_id)

        # Collect and validate all associated work item IDs
        associated_wi_ids = list(getattr(data, "work_item_ids", []) or [])
        if data.resume_work_item_id is not None and data.resume_work_item_id not in associated_wi_ids:
            associated_wi_ids.append(data.resume_work_item_id)
        resume_wi_ids = getattr(data, "resume_work_item_ids", []) or []
        for r_id in resume_wi_ids:
            if r_id not in associated_wi_ids:
                associated_wi_ids.append(r_id)

        for wi_id in associated_wi_ids:
            await self._verify_work_item(patient_id, wi_id)

        now = datetime.now(timezone.utc)
        user = await self._get_active_current_user()

        is_historical = bool(getattr(data, "is_historical", False))
        actual_visit_date = getattr(data, "actual_visit_date", None)
        if is_historical:
            if not actual_visit_date:
                raise HTTPException(status_code=422, detail="Historical care session requires actual_visit_date")
            if actual_visit_date > now:
                raise HTTPException(status_code=422, detail="Historical visit date cannot be in the future")

        # Acquire concurrency lock for patient care sessions (R05)
        await self._acquire_advisory_lock(f"care_session:{patient_id}")

        # D3 guard: check if active session already exists for this patient (only applies to non-historical active sessions)
        if not is_historical:
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

        session_status = "completed" if is_historical else "in_progress"
        session_started = actual_visit_date if is_historical else now
        session_finished = actual_visit_date if is_historical else None

        session = models.CareSession(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            appointment_id=data.appointment_id,
            provider_user_id=user.id if user else None,
            status=session_status,
            started_at=session_started,
            finished_at=session_finished,
            actual_visit_date=actual_visit_date or now,
            recorded_by_user_id=user.id if user else None,
            is_historical=is_historical,
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

        # Create CareSessionProcedure rows for all associated procedures with populated template snapshot
        from backend.services.workflow_template_service import WorkflowTemplateService
        tpl_service = WorkflowTemplateService(self.db, self.tenant_id, self.current_user)
        for wi_id in associated_wi_ids:
            wi = await self.db.get(models.ClinicalWorkItem, wi_id)
            tpl_dict = None
            proc_code = getattr(wi, "code", None)
            if proc_code:
                tpl_dict = await tpl_service.get_active_template_for_procedure(proc_code)
            session_proc = models.CareSessionProcedure(
                tenant_id=self.tenant_id,
                care_session_id=session.id,
                work_item_id=wi_id,
                template_snapshot=tpl_dict,
                template_version=tpl_dict.get("version") if tpl_dict else None,
                created_at=now,
            )
            self.db.add(session_proc)

        # Continuation / carryover support
        if data.resume_work_item_id is not None or data.resume_from_session_id is not None or associated_wi_ids:
            source_session_ids = []
            if data.resume_from_session_id is not None:
                source_session_ids = [data.resume_from_session_id]
            else:
                target_check_wis = associated_wi_ids if associated_wi_ids else ([data.resume_work_item_id] if data.resume_work_item_id else [])
                for wi_id in target_check_wis:
                    source_session_stmt = (
                        select(models.CareSessionStep.care_session_id)
                        .join(models.CareSession, models.CareSession.id == models.CareSessionStep.care_session_id)
                        .where(
                            models.CareSessionStep.tenant_id == self.tenant_id,
                            models.CareSession.patient_id == patient_id,
                            models.CareSessionStep.work_item_id == wi_id,
                            models.CareSession.id != session.id,
                        )
                        .order_by(models.CareSession.started_at.desc(), models.CareSession.id.desc())
                        .limit(1)
                    )
                    s_id = (await self.db.execute(source_session_stmt)).scalar_one_or_none()
                    if s_id is None:
                        source_obs_stmt = (
                            select(models.CareObservation.care_session_id)
                            .join(models.CareSession, models.CareSession.id == models.CareObservation.care_session_id)
                            .where(
                                models.CareObservation.tenant_id == self.tenant_id,
                                models.CareObservation.patient_id == patient_id,
                                models.CareObservation.work_item_id == wi_id,
                                models.CareSession.id != session.id,
                            )
                            .order_by(models.CareSession.started_at.desc(), models.CareSession.id.desc())
                            .limit(1)
                        )
                        s_id = (await self.db.execute(source_obs_stmt)).scalar_one_or_none()
                    if s_id is not None and s_id not in source_session_ids:
                        source_session_ids.append(s_id)

            if source_session_ids:
                prior_steps_query = (
                    select(models.CareSessionStep)
                    .where(
                        models.CareSessionStep.tenant_id == self.tenant_id,
                        models.CareSessionStep.care_session_id.in_(source_session_ids),
                    )
                    .order_by(
                        models.CareSessionStep.step_order.asc(),
                        models.CareSessionStep.id.asc(),
                    )
                )
                prior_steps = (await self.db.execute(prior_steps_query)).scalars().all()

                remaining_prior_steps = [
                    s for s in prior_steps
                    if s.status not in ("completed", "omitted", "skipped", "cancelled")
                ]

                new_order = 1
                for p_step in remaining_prior_steps:
                    # Filter by associated procedures if specified
                    if associated_wi_ids and p_step.work_item_id and p_step.work_item_id not in associated_wi_ids:
                        continue

                    # Maintain procedure-scoped work_item_id without overwriting with another procedure's ID
                    target_wi_id = p_step.work_item_id or data.resume_work_item_id

                    new_step = models.CareSessionStep(
                        tenant_id=self.tenant_id,
                        care_session_id=session.id,
                        work_item_id=target_wi_id,
                        step_order=new_order,
                        step_code=p_step.step_code,
                        logical_step_code=p_step.logical_step_code or p_step.step_code,
                        occurrence_number=p_step.occurrence_number,
                        template_step_id=p_step.template_step_id,
                        is_repeat=p_step.is_repeat,
                        repeat_reason=p_step.repeat_reason,
                        title=p_step.title,
                        status="pending" if p_step.status == "in_progress" else p_step.status,
                        started_at=None,
                        completed_at=None,
                        notes=f"[Resumed from Step #{p_step.step_order}] {p_step.notes or ''}".strip() if p_step.notes else None,
                    )
                    self.db.add(new_step)
                    new_order += 1

                obs_query = (
                    select(models.CareObservation)
                    .where(
                        models.CareObservation.tenant_id == self.tenant_id,
                        models.CareObservation.patient_id == patient_id,
                        models.CareObservation.care_session_id.in_(source_session_ids),
                        models.CareObservation.is_superseded == False,  # noqa: E712
                    )
                    .order_by(models.CareObservation.recorded_at.asc(), models.CareObservation.id.asc())
                )
                prior_obs = (await self.db.execute(obs_query)).scalars().all()

                seen_carried_sources = set()
                for p_obs in prior_obs:
                    if associated_wi_ids and p_obs.work_item_id and p_obs.work_item_id not in associated_wi_ids:
                        continue

                    # Resolve measurement through provenance and effective correction chain
                    effective_obs = await self._resolve_effective_observation_chain(p_obs)
                    if effective_obs.is_superseded:
                        continue

                    seen_key = (
                        effective_obs.observation_code,
                        effective_obs.tooth_key,
                        effective_obs.canal_id,
                        effective_obs.id,
                    )
                    if seen_key in seen_carried_sources:
                        continue
                    seen_carried_sources.add(seen_key)

                    target_obs_wi = effective_obs.work_item_id or p_obs.work_item_id or data.resume_work_item_id
                    src_session_id = effective_obs.reference_source_session_id or effective_obs.care_session_id
                    src_date = effective_obs.reference_source_date or effective_obs.recorded_at or effective_obs.created_at

                    carried_obs = models.CareObservation(
                        tenant_id=self.tenant_id,
                        patient_id=patient_id,
                        care_session_id=session.id,
                        work_item_id=target_obs_wi,
                        observation_code=effective_obs.observation_code,
                        tooth_key=effective_obs.tooth_key,
                        structured_value=dict(effective_obs.structured_value or {}),
                        notes=f"[Reference from Session {src_session_id}] {effective_obs.notes or ''}".strip() if effective_obs.notes else None,
                        recorded_by_user_id=user.id if user else None,
                        is_superseded=False,
                        reference_source_session_id=src_session_id,
                        reference_source_date=src_date,
                        reference_source_observation_id=effective_obs.id,
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

        # F15, R3-01, R3-02: Persist historical steps and observations with stable clinical identities
        if is_historical:
            step_order = 1
            assigned_occurrences: dict[Tuple[Optional[int], str], int] = {}
            for raw_s in (getattr(data, "historical_steps", None) or []):
                s = raw_s if isinstance(raw_s, dict) else raw_s.model_dump()
                raw_code = str(s.get("step_code") or "").strip()
                title = str(s.get("title") or raw_code or f"step_{step_order}").strip()
                wi_id = s.get("work_item_id") or (associated_wi_ids[0] if associated_wi_ids else None)
                if wi_id is not None:
                    await self._verify_work_item(patient_id, wi_id)

                # R3-02: Derive stable semantic identifiers rather than collapsing distinct activities by positional indices
                is_positional = bool(re.match(r"^step_\d+$", raw_code, re.IGNORECASE))
                logical_hint = (s.get("logical_step_code") or "").strip()
                if logical_hint:
                    logical_code = logical_hint
                elif raw_code and not is_positional:
                    logical_code = raw_code
                else:
                    logical_code = historical_step_identity(title)

                step_code = raw_code if raw_code and not is_positional else logical_code

                # Resolve occurrence number with continuity
                occ_key = (wi_id, logical_code)
                occ_num = s.get("occurrence_number")
                if occ_num is None or occ_num <= 0:
                    if occ_key not in assigned_occurrences:
                        if wi_id is not None:
                            occ_stmt = select(func.coalesce(func.max(models.CareSessionStep.occurrence_number), 0)).where(
                                models.CareSessionStep.tenant_id == self.tenant_id,
                                models.CareSessionStep.work_item_id == wi_id,
                                func.coalesce(models.CareSessionStep.logical_step_code, models.CareSessionStep.step_code) == logical_code,
                            )
                            max_db_occ = (await self.db.execute(occ_stmt)).scalar_one()
                            assigned_occurrences[occ_key] = max_db_occ
                        else:
                            assigned_occurrences[occ_key] = 0

                    assigned_occurrences[occ_key] += 1
                    occ_num = assigned_occurrences[occ_key]
                    is_rep = occ_num > 1
                else:
                    is_rep = occ_num > 1
                    assigned_occurrences[occ_key] = max(assigned_occurrences.get(occ_key, 0), occ_num)

                h_step = models.CareSessionStep(
                    tenant_id=self.tenant_id,
                    care_session_id=session.id,
                    work_item_id=wi_id,
                    step_order=s.get("step_order") or step_order,
                    step_code=step_code,
                    logical_step_code=logical_code,
                    occurrence_number=occ_num,
                    is_repeat=is_rep,
                    title=title,
                    status=s.get("status", "completed"),
                    notes=s.get("notes"),
                    started_at=actual_visit_date,
                    completed_at=actual_visit_date,
                    created_at=now,
                )
                self.db.add(h_step)
                step_order += 1

            for raw_obs in (getattr(data, "historical_observations", None) or []):
                obs = raw_obs if isinstance(raw_obs, dict) else raw_obs.model_dump()
                obs_code = str(obs.get("observation_code") or "measurement").strip()
                wi_id = obs.get("work_item_id") or (associated_wi_ids[0] if associated_wi_ids else None)
                if wi_id is not None:
                    await self._verify_work_item(patient_id, wi_id)

                tooth_key = obs.get("tooth_key")
                if tooth_key is not None:
                    if tooth_key not in FDI_TOOTH_KEYS:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Invalid tooth key '{tooth_key}'. Must be valid FDI notation (11-48, 51-85).",
                        )

                # Canonical structured value normalization (R3-01)
                structured_val = dict(obs.get("structured_value") or {})
                surface_code = obs.get("surface_code") or structured_val.get("surface_code")
                root_id = obs.get("root_id") or structured_val.get("root_id")
                canal_id = obs.get("canal_id") or structured_val.get("canal_id")

                if surface_code:
                    structured_val["surface_code"] = surface_code
                if root_id:
                    structured_val["root_id"] = root_id
                if canal_id:
                    structured_val["canal_id"] = canal_id

                # Normalize numeric length_mm for working length observations
                if obs_code == "working_length":
                    if "length_mm" not in structured_val or structured_val.get("length_mm") is None:
                        val = obs.get("value") or structured_val.get("value")
                        if val is not None:
                            try:
                                structured_val["length_mm"] = float(val)
                            except (ValueError, TypeError):
                                pass

                h_obs = models.CareObservation(
                    tenant_id=self.tenant_id,
                    patient_id=patient_id,
                    care_session_id=session.id,
                    work_item_id=wi_id,
                    observation_code=obs_code,
                    tooth_key=tooth_key,
                    structured_value=structured_val,
                    notes=obs.get("notes"),
                    recorded_by_user_id=user.id if user else None,
                    is_superseded=False,
                    recorded_at=now,
                    created_at=now,
                )
                self.db.add(h_obs)

            try:
                await self.db.flush()
            except (IntegrityError, StaleDataError) as exc:
                await self.db.rollback()
                await self._get_active_current_user()
                raise HTTPException(
                    status_code=409,
                    detail="Concurrent care session conflict during historical data entry",
                ) from exc

        # Audit event
        event_payload = {
            "session_id": session.id,
            "appointment_id": session.appointment_id,
            "provider_user_id": session.provider_user_id,
            "status": session.status,
            "is_historical": session.is_historical,
            "actual_visit_date": session.actual_visit_date.isoformat() if session.actual_visit_date else None,
            "work_item_ids": associated_wi_ids,
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

        # F03, F10, R2-03, R2-05: Durable persistence of procedure documentation and strict typed validation
        draft_stmt = select(models.CareSessionDraft).where(
            models.CareSessionDraft.tenant_id == self.tenant_id,
            models.CareSessionDraft.patient_id == patient_id,
            models.CareSessionDraft.care_session_id == session.id,
            models.CareSessionDraft.author_user_id == user.id,
        )
        draft = (await self.db.execute(draft_stmt)).scalars().first()
        draft_data = draft.draft_payload if draft and isinstance(draft.draft_payload, dict) else {}

        for proc in (session.procedures or []):
            wi_id = proc.work_item_id
            proc_note_key = f"proc_notes_{wi_id}"
            if proc_note_key in draft_data and draft_data[proc_note_key]:
                proc.procedure_notes = str(draft_data[proc_note_key]).strip()

            proc_na_key = f"proc_next_action_{wi_id}"
            if proc_na_key in draft_data and draft_data[proc_na_key]:
                proc.next_action = str(draft_data[proc_na_key]).strip()

            custom_prefix = f"proc_custom_{wi_id}_"
            custom_values = {}
            for k, v in draft_data.items():
                if k.startswith(custom_prefix):
                    field_id = k[len(custom_prefix):]
                    custom_values[field_id] = v

            snapshot = proc.template_snapshot or {}
            custom_fields_def = snapshot.get("custom_fields") or []
            known_field_ids = {f.get("field_id") for f in custom_fields_def if f.get("field_id")}

            # Validate unknown custom field identifiers when template snapshot defines fields
            if known_field_ids:
                for fid in custom_values:
                    if fid not in known_field_ids:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Unknown custom field '{fid}' for procedure #{wi_id}",
                        )

            for field_def in custom_fields_def:
                fid = field_def.get("field_id")
                flabel = field_def.get("label", fid)
                is_req = field_def.get("is_required", False)
                ftype = field_def.get("field_type")
                val = custom_values.get(fid)

                if is_req:
                    if val is None or (isinstance(val, str) and not val.strip()):
                        raise HTTPException(
                            status_code=422,
                            detail=f"Required custom field '{flabel}' ({fid}) is missing for procedure #{wi_id}",
                        )

                # Validate typed values when present
                if val is not None and not (isinstance(val, str) and not val.strip()):
                    if ftype == "number":
                        try:
                            float(str(val).strip())
                        except (ValueError, TypeError):
                            raise HTTPException(
                                status_code=422,
                                detail=f"Custom field '{flabel}' ({fid}) must be a valid number",
                            )
                    elif ftype == "choice":
                        choices = field_def.get("choices") or []
                        if choices:
                            str_choices = [str(c).strip() for c in choices]
                            if str(val).strip() not in str_choices:
                                raise HTTPException(
                                    status_code=422,
                                    detail=f"Custom field '{flabel}' ({fid}) has invalid choice '{val}'. Allowed: {choices}",
                                )
                    elif ftype == "date":
                        val_str = str(val).strip()
                        try:
                            datetime.fromisoformat(val_str.replace("Z", "+00:00"))
                        except ValueError:
                            try:
                                from datetime import date
                                date.fromisoformat(val_str)
                            except ValueError:
                                raise HTTPException(
                                    status_code=422,
                                    detail=f"Custom field '{flabel}' ({fid}) must be a valid date (YYYY-MM-DD)",
                                )
                    elif ftype == "boolean":
                        if not isinstance(val, bool) and str(val).lower() not in ("true", "false", "1", "0", "yes", "no"):
                            raise HTTPException(
                                status_code=422,
                                detail=f"Custom field '{flabel}' ({fid}) must be a boolean",
                            )

            if custom_values:
                updated_snapshot = dict(proc.template_snapshot or {})
                updated_snapshot["custom_field_values"] = custom_values
                proc.template_snapshot = updated_snapshot

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

        # G11-M02: Create chairside next-visit request(s) if specified
        if getattr(data, "next_visit_requests", None):
            for req in data.next_visit_requests:
                await self._create_next_visit_request_internal(
                    patient_id=patient_id,
                    data=req,
                    session=session,
                )
        elif getattr(data, "next_visit_request", None) is not None:
            await self._create_next_visit_request_internal(
                patient_id=patient_id,
                data=data.next_visit_request,
                session=session,
            )

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

        logical_code = (data.logical_step_code or data.step_code or "").strip()
        occurrence_number = data.occurrence_number
        is_repeat = data.is_repeat

        if occurrence_number is None or occurrence_number <= 0:
            if data.work_item_id is not None:
                occ_stmt = select(func.coalesce(func.max(models.CareSessionStep.occurrence_number), 0)).where(
                    models.CareSessionStep.tenant_id == self.tenant_id,
                    models.CareSessionStep.work_item_id == data.work_item_id,
                    func.coalesce(models.CareSessionStep.logical_step_code, models.CareSessionStep.step_code) == logical_code,
                )
            else:
                occ_stmt = select(func.coalesce(func.max(models.CareSessionStep.occurrence_number), 0)).where(
                    models.CareSessionStep.tenant_id == self.tenant_id,
                    models.CareSessionStep.care_session_id == session_id,
                    func.coalesce(models.CareSessionStep.logical_step_code, models.CareSessionStep.step_code) == logical_code,
                )
            max_occ = (await self.db.execute(occ_stmt)).scalar_one()
            if max_occ > 0:
                occurrence_number = max_occ + 1
                is_repeat = True
            else:
                occurrence_number = 1
                is_repeat = bool(data.is_repeat)
        else:
            if is_repeat is None:
                is_repeat = occurrence_number > 1

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
            logical_step_code=logical_code,
            occurrence_number=occurrence_number,
            template_step_id=data.template_step_id,
            is_repeat=bool(is_repeat),
            repeat_reason=data.repeat_reason,
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

        from backend.services.workflow_template_service import WorkflowTemplateService
        tpl_service = WorkflowTemplateService(self.db, self.tenant_id, self.current_user)
        if await tpl_service.is_template_deactivated(data.template_code):
            raise HTTPException(
                status_code=400,
                detail=f"Workflow template '{data.template_code}' is deactivated for this clinic",
            )
        tpl_dict = await tpl_service.get_active_template_for_procedure(data.template_code)
        if not tpl_dict:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow template '{data.template_code}' not found",
            )

        # Associate template snapshot with the procedure in this care session
        if data.work_item_id is not None:
            csp_stmt = select(models.CareSessionProcedure).where(
                models.CareSessionProcedure.tenant_id == self.tenant_id,
                models.CareSessionProcedure.care_session_id == session_id,
                models.CareSessionProcedure.work_item_id == data.work_item_id,
            )
            csp = (await self.db.execute(csp_stmt)).scalar_one_or_none()
            if not csp:
                csp = models.CareSessionProcedure(
                    tenant_id=self.tenant_id,
                    care_session_id=session_id,
                    work_item_id=data.work_item_id,
                    created_at=datetime.now(timezone.utc),
                )
                self.db.add(csp)
            if csp.template_snapshot is None:
                csp.template_snapshot = tpl_dict
                csp.template_version = tpl_dict.get("version")
            else:
                # F06: Retain frozen recorded snapshot
                tpl_dict = csp.template_snapshot

        # Find current max step_order
        stmt = select(func.coalesce(func.max(models.CareSessionStep.step_order), 0)).where(
            models.CareSessionStep.tenant_id == self.tenant_id,
            models.CareSessionStep.care_session_id == session_id,
        )
        base_order = (await self.db.execute(stmt)).scalar_one()

        created_steps: List[models.CareSessionStep] = []
        now = datetime.now(timezone.utc)
        raw_steps = tpl_dict.get("steps") or []
        for tpl_step in raw_steps:
            tpl_code = (tpl_step.get("step_code") if isinstance(tpl_step, dict) else tpl_step.step_code).strip()
            tpl_title = (tpl_step.get("title") if isinstance(tpl_step, dict) else tpl_step.title).strip()
            tpl_order = tpl_step.get("step_order") if isinstance(tpl_step, dict) else tpl_step.step_order
            tpl_desc = (tpl_step.get("description") if isinstance(tpl_step, dict) else tpl_step.description) or None

            occ_num = 1
            is_rep = False
            if data.work_item_id is not None:
                occ_stmt = select(func.coalesce(func.max(models.CareSessionStep.occurrence_number), 0)).where(
                    models.CareSessionStep.tenant_id == self.tenant_id,
                    models.CareSessionStep.work_item_id == data.work_item_id,
                    func.coalesce(models.CareSessionStep.logical_step_code, models.CareSessionStep.step_code) == tpl_code,
                )
                max_occ = (await self.db.execute(occ_stmt)).scalar_one()
                if max_occ > 0:
                    occ_num = max_occ + 1
                    is_rep = True

            step = models.CareSessionStep(
                tenant_id=self.tenant_id,
                care_session_id=session_id,
                work_item_id=data.work_item_id,
                step_order=base_order + tpl_order,
                step_code=tpl_code,
                logical_step_code=tpl_code,
                occurrence_number=occ_num,
                template_step_id=tpl_code,
                is_repeat=is_rep,
                title=tpl_title,
                status="pending",
                notes=tpl_desc,
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
    # Multi-Procedure Workspace Operations (Requirement 1 & 3)
    # -----------------------------------------------------------------------

    async def add_procedure_to_session(
        self, patient_id: int, session_id: int, work_item_id: int
    ) -> models.CareSessionProcedure:
        """
        Associate an existing active procedure (work item) with an active care session.
        Resolves the procedure's active workflow template and populates template_snapshot.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)
        await self._verify_work_item(patient_id, work_item_id)

        session = await self.get_session(patient_id, session_id)
        if session.status != "in_progress":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot add procedure to session with status '{session.status}'. Session must be in_progress.",
            )

        # Check if already associated
        stmt = select(models.CareSessionProcedure).where(
            models.CareSessionProcedure.tenant_id == self.tenant_id,
            models.CareSessionProcedure.care_session_id == session_id,
            models.CareSessionProcedure.work_item_id == work_item_id,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing

        from backend.services.workflow_template_service import WorkflowTemplateService
        tpl_service = WorkflowTemplateService(self.db, self.tenant_id, self.current_user)
        wi = await self.db.get(models.ClinicalWorkItem, work_item_id)
        tpl_dict = None
        proc_code = getattr(wi, "code", None)
        if proc_code:
            tpl_dict = await tpl_service.get_active_template_for_procedure(proc_code)

        session_proc = models.CareSessionProcedure(
            tenant_id=self.tenant_id,
            care_session_id=session_id,
            work_item_id=work_item_id,
            template_snapshot=tpl_dict,
            template_version=tpl_dict.get("version") if tpl_dict else None,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(session_proc)

        # F09: Initialize steps from snapshotted template for added procedure
        now = datetime.now(timezone.utc)
        if tpl_dict and tpl_dict.get("steps"):
            stmt_order = select(func.coalesce(func.max(models.CareSessionStep.step_order), 0)).where(
                models.CareSessionStep.tenant_id == self.tenant_id,
                models.CareSessionStep.care_session_id == session_id,
            )
            base_order = (await self.db.execute(stmt_order)).scalar_one()
            for idx, s in enumerate(tpl_dict["steps"]):
                step_code = (s.get("step_code") if isinstance(s, dict) else s.step_code).strip()
                step_title = (s.get("title") if isinstance(s, dict) else s.title).strip()
                step_desc = (s.get("description") if isinstance(s, dict) else s.description) or None
                step_row = models.CareSessionStep(
                    tenant_id=self.tenant_id,
                    care_session_id=session_id,
                    work_item_id=work_item_id,
                    step_code=step_code,
                    logical_step_code=step_code,
                    occurrence_number=1,
                    is_repeat=False,
                    title=step_title,
                    notes=step_desc,
                    status="pending",
                    step_order=base_order + idx + 1,
                    created_at=now,
                )
                self.db.add(step_row)

        await self.db.commit()
        stmt = (
            select(models.CareSessionProcedure)
            .options(selectinload(models.CareSessionProcedure.work_item))
            .where(models.CareSessionProcedure.id == session_proc.id)
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def remove_procedure_from_session(
        self, patient_id: int, session_id: int, work_item_id: int
    ) -> bool:
        """
        Remove a procedure selected accidentally from the current visit before work is documented.
        Enforces Decision §2.2: does NOT delete the underlying procedure or its clinical history.
        Rejects removal if any steps or observations have already been recorded/completed in this visit.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = await self.get_session(patient_id, session_id)
        if session.status != "in_progress":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot modify procedures for session with status '{session.status}'.",
            )

        # Check if any step has been started or completed
        steps_stmt = select(models.CareSessionStep).where(
            models.CareSessionStep.tenant_id == self.tenant_id,
            models.CareSessionStep.care_session_id == session_id,
            models.CareSessionStep.work_item_id == work_item_id,
        )
        steps = list((await self.db.execute(steps_stmt)).scalars().all())
        completed_or_in_progress = [s for s in steps if s.status in ("completed", "in_progress", "partial")]
        if completed_or_in_progress:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove procedure with documented clinical work in this visit. Finish or cancel steps instead.",
            )

        # Check if observations exist
        obs_stmt = select(models.CareObservation).where(
            models.CareObservation.tenant_id == self.tenant_id,
            models.CareObservation.care_session_id == session_id,
            models.CareObservation.work_item_id == work_item_id,
        )
        obs_count = len(list((await self.db.execute(obs_stmt)).scalars().all()))
        if obs_count > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove procedure with recorded observations in this visit.",
            )

        # Delete pending steps
        for s in steps:
            await self.db.delete(s)

        # Delete CareSessionProcedure
        csp_stmt = select(models.CareSessionProcedure).where(
            models.CareSessionProcedure.tenant_id == self.tenant_id,
            models.CareSessionProcedure.care_session_id == session_id,
            models.CareSessionProcedure.work_item_id == work_item_id,
        )
        csp = (await self.db.execute(csp_stmt)).scalar_one_or_none()
        if csp:
            await self.db.delete(csp)

        await self.db.commit()
        return True

    async def update_session_procedure(
        self, patient_id: int, session_id: int, work_item_id: int, data: schemas.CareSessionProcedureUpdate
    ) -> models.CareSessionProcedure:
        """Update procedure-specific notes and next action within this visit."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)
        await self._verify_work_item(patient_id, work_item_id)

        session = await self.get_session(patient_id, session_id)
        if session.status != "in_progress":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update procedure on session with status '{session.status}'. Must be in_progress.",
            )

        stmt = select(models.CareSessionProcedure).where(
            models.CareSessionProcedure.tenant_id == self.tenant_id,
            models.CareSessionProcedure.care_session_id == session_id,
            models.CareSessionProcedure.work_item_id == work_item_id,
        )
        csp = (await self.db.execute(stmt)).scalar_one_or_none()
        if not csp:
            raise HTTPException(status_code=404, detail="Care session procedure association not found")

        if data.procedure_notes is not None:
            csp.procedure_notes = data.procedure_notes.strip() if data.procedure_notes else None
        if data.next_action is not None:
            csp.next_action = data.next_action.strip() if data.next_action else None
        if data.next_action_reason_omitted is not None:
            csp.next_action_reason_omitted = data.next_action_reason_omitted.strip() if data.next_action_reason_omitted else None

        await self.db.commit()
        stmt = (
            select(models.CareSessionProcedure)
            .options(selectinload(models.CareSessionProcedure.work_item))
            .where(models.CareSessionProcedure.id == csp.id)
        )
        return (await self.db.execute(stmt)).scalar_one()

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

        # G12-M13: Sync shade and material observation to open lab orders
        if obs.work_item_id:
            from backend.clinical.shade_material_sync import sync_observation_to_open_lab_orders
            await sync_observation_to_open_lab_orders(
                self.db,
                self.tenant_id,
                obs.work_item_id,
                obs.observation_code,
                obs.structured_value,
                obs.notes,
            )

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
        include_superseded: bool = False,
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
        if not include_superseded:
            stmt = stmt.where(models.CareObservation.is_superseded == False)  # noqa: E712
        if step_id is not None:
            stmt = stmt.where(models.CareObservation.step_id == step_id)

        stmt = stmt.order_by(models.CareObservation.recorded_at.asc(), models.CareObservation.id.asc())
        result = await self.db.execute(stmt)
        observations = list(result.scalars().all())
        if not include_superseded:
            projected = []
            for obs in observations:
                if not obs.is_superseded and obs.reference_source_observation_id:
                    eff = await self._resolve_effective_observation_chain(obs)
                    if eff and eff.id != obs.id:
                        projected.append(self._build_effective_observation_dto(obs, eff))
                        continue
                projected.append(obs)
            return projected
        return observations

    # -----------------------------------------------------------------------
    # Queries
    # -----------------------------------------------------------------------

    async def get_session(
        self, patient_id: int, session_id: int, eager_load: bool = True
    ) -> Any:
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
                selectinload(models.CareSession.procedures).selectinload(models.CareSessionProcedure.work_item).selectinload(models.ClinicalWorkItem.targets),
                selectinload(models.CareSession.steps).selectinload(models.CareSessionStep.work_item).selectinload(models.ClinicalWorkItem.targets),
                selectinload(models.CareSession.observations),
                selectinload(models.CareSession.next_visit_requests),
            )
        session = (await self.db.execute(stmt)).scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Care session not found")

        projected_obs = await self._project_session_observations(session)
        pres = CareSessionPresentation(session, projected_obs)

        if session.status == "completed":
            pres.summary = self.generate_session_summary(pres)
        return pres

    async def get_active_session(self, patient_id: int) -> Optional[Any]:
        """Retrieve the currently active ('in_progress') care session for a patient, if any."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = (
            select(models.CareSession)
            .execution_options(populate_existing=True)
            .options(
                selectinload(models.CareSession.procedures).selectinload(models.CareSessionProcedure.work_item).selectinload(models.ClinicalWorkItem.targets),
                selectinload(models.CareSession.steps).selectinload(models.CareSessionStep.work_item).selectinload(models.ClinicalWorkItem.targets),
                selectinload(models.CareSession.observations),
                selectinload(models.CareSession.next_visit_requests),
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
            projected_obs = await self._project_session_observations(session)
            pres = CareSessionPresentation(session, projected_obs)
            if session.status == "completed":
                pres.summary = self.generate_session_summary(pres)
            return pres
        return None

    async def list_sessions(
        self, patient_id: int, status: Optional[str] = None
    ) -> List[Any]:
        """List care sessions for a patient with optional status filtering."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = (
            select(models.CareSession)
            .execution_options(populate_existing=True)
            .options(
                selectinload(models.CareSession.procedures)
                .selectinload(models.CareSessionProcedure.work_item)
                .selectinload(models.ClinicalWorkItem.targets),
                selectinload(models.CareSession.steps)
                .selectinload(models.CareSessionStep.work_item)
                .selectinload(models.ClinicalWorkItem.targets),
                selectinload(models.CareSession.observations),
                selectinload(models.CareSession.next_visit_requests),
            )
            .where(
                models.CareSession.tenant_id == self.tenant_id,
                models.CareSession.patient_id == patient_id,
            )
        )
        if status:
            stmt = stmt.where(models.CareSession.status == status)

        stmt = stmt.order_by(
            func.coalesce(models.CareSession.actual_visit_date, models.CareSession.started_at, models.CareSession.created_at).desc(),
            models.CareSession.id.desc(),
        )
        result = await self.db.execute(stmt)
        sessions = list(result.scalars().all())
        pres_list = []
        for s in sessions:
            projected_obs = await self._project_session_observations(s)
            pres = CareSessionPresentation(s, projected_obs)
            if s.status == "completed":
                pres.summary = self.generate_session_summary(pres)
            pres_list.append(pres)
        return pres_list

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
        obs_list = [o for o in (session.observations or []) if not getattr(o, "is_superseded", False)]
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

        # Procedure notes, next actions, and custom fields (F03)
        for proc in (session.procedures or []):
            proc_parts = []
            if proc.procedure_notes:
                proc_parts.append(proc.procedure_notes)
            if proc.next_action:
                proc_parts.append(f"Next: {proc.next_action}")
            snapshot = proc.template_snapshot or {}
            cf_values = snapshot.get("custom_field_values") or {}
            for fid, fval in cf_values.items():
                proc_parts.append(f"{fid.title()}: {fval}")
            if proc_parts:
                parts.append(" | ".join(proc_parts))

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
            # Resolve steps & observations from the latest care session for this work item
            latest_session_id = None
            step_session_ids = [s.care_session_id for s in (wi.session_steps or []) if s.care_session_id]
            obs_session_ids = [o.care_session_id for o in (wi.observations or []) if o.care_session_id]
            candidate_session_ids = list(set(step_session_ids + obs_session_ids))

            if candidate_session_ids:
                sess_stmt = (
                    select(models.CareSession.id)
                    .where(
                        models.CareSession.id.in_(candidate_session_ids),
                        models.CareSession.tenant_id == self.tenant_id,
                    )
                    .order_by(models.CareSession.started_at.desc(), models.CareSession.id.desc())
                    .limit(1)
                )
                latest_session_id = (await self.db.execute(sess_stmt)).scalar_one_or_none()

            if latest_session_id:
                steps = sorted(
                    [s for s in (wi.session_steps or []) if s.care_session_id == latest_session_id],
                    key=lambda s: s.step_order,
                )
                obs = [o for o in (wi.observations or []) if o.care_session_id == latest_session_id and not getattr(o, "is_superseded", False)]
                if not obs and wi.observations and obs_session_ids:
                    obs_sess_stmt = (
                        select(models.CareSession.id)
                        .where(
                            models.CareSession.id.in_(obs_session_ids),
                            models.CareSession.tenant_id == self.tenant_id,
                        )
                        .order_by(models.CareSession.started_at.desc(), models.CareSession.id.desc())
                        .limit(1)
                    )
                    latest_obs_sess_id = (await self.db.execute(obs_sess_stmt)).scalar_one_or_none()
                    obs = [o for o in wi.observations if o.care_session_id == latest_obs_sess_id and not getattr(o, "is_superseded", False)]
            else:
                steps = sorted(wi.session_steps or [], key=lambda s: s.step_order)
                obs = [o for o in (wi.observations or []) if not getattr(o, "is_superseded", False)]

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
                        models.CareObservation.is_superseded == False,  # noqa: E712
                    )
                    .order_by(models.CareObservation.recorded_at.asc())
                )
                alt_obs = list((await self.db.execute(alt_obs_stmt)).scalars().all())
                if alt_obs:
                    obs = alt_obs

            # Resolve effective observations through provenance & correction chain
            resolved_obs = []
            seen_obs_keys = set()
            for raw_o in obs:
                eff_o = await self._resolve_effective_observation_chain(raw_o)
                if not eff_o.is_superseded:
                    key = (eff_o.observation_code, eff_o.tooth_key, eff_o.canal_id, eff_o.id)
                    if key not in seen_obs_keys:
                        seen_obs_keys.add(key)
                        resolved_obs.append(eff_o)
            obs = resolved_obs

            # Only include work items that have either session steps, observations, or are active/in_progress procedures
            if not steps and not obs and wi.status not in ("active", "in_progress"):
                continue

            completed_steps = [s for s in steps if s.status == "completed"]
            remaining_steps = [s for s in steps if s.status not in ("completed", "omitted", "skipped", "cancelled")]

            # Group all steps for this work item across sessions by logical identity for overall procedure progress
            all_wi_steps = list(wi.session_steps or [])
            logical_steps_map = {}
            for s in sorted(all_wi_steps, key=lambda x: (x.care_session_id or 0, x.step_order or 0, x.id or 0)):
                key = (s.logical_step_code or s.step_code or s.title or f"step_{s.step_order}", s.occurrence_number or 1)
                if key not in logical_steps_map:
                    logical_steps_map[key] = []
                logical_steps_map[key].append(s)

            total_steps = len(logical_steps_map) if logical_steps_map else len(steps)
            completed_steps_count = (
                sum(1 for sl in logical_steps_map.values() if any(s.status == "completed" for s in sl))
                if logical_steps_map else len(completed_steps)
            )

            # Determine last session info
            last_session_id = latest_session_id
            last_session_at = None
            last_notes = None
            if not last_session_id:
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

            next_step_title = None
            if remaining_steps:
                next_step_title = remaining_steps[0].title
            elif logical_steps_map:
                for sl in logical_steps_map.values():
                    if not any(s.status in ("completed", "omitted", "skipped", "cancelled") for s in sl):
                        next_step_title = sl[-1].title
                        break

            summary_str = f"{wi.code} on Tooth {tooth_key or 'N/A'}: {completed_steps_count}/{total_steps} steps completed"
            if next_step_title:
                summary_str += f". Next: {next_step_title}"

            items.append({
                "work_item_id": wi.id,
                "procedure_code": wi.code,
                "tooth_key": tooth_key,
                "surface_code": surface_code,
                "title": wi.code,
                "status": wi.status,
                "total_steps": total_steps,
                "completed_steps_count": completed_steps_count,
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

    # -----------------------------------------------------------------------
    # Appointment Integration & Next-Visit Requests (Slice S22 / G11)
    # -----------------------------------------------------------------------

    async def link_appointment(
        self, patient_id: int, session_id: int, appointment_id: Optional[int]
    ) -> models.CareSession:
        """
        Link or unlink a CareSession to an existing Appointment (G11-M01).
        Verifies appointment tenant and patient ownership.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = await self.get_session(patient_id, session_id)
        if appointment_id is not None:
            await self._verify_appointment(patient_id, appointment_id)
            session.appointment_id = appointment_id
            event_type = "care_session_linked_appointment"
        else:
            session.appointment_id = None
            event_type = "care_session_unlinked_appointment"

        user = await self._get_active_current_user()
        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=session.id,
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc),
            actor_user_id=user.id if user else None,
            payload={
                "session_id": session.id,
                "appointment_id": appointment_id,
            },
        )
        self.db.add(event)
        try:
            await self.db.commit()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent care session conflict during appointment linking",
            ) from exc

        return await self.get_session(patient_id, session.id)

    async def suggest_next_visit(
        self,
        patient_id: int,
        session_id: Optional[int] = None,
        work_item_id: Optional[int] = None,
    ) -> schemas.NextVisitSuggestionRead:
        """
        Auto-suggest appointment reason and duration based on session context (G11-M06, G11-M07).
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        target_work_item_id = work_item_id
        session = None
        remaining_steps = []
        next_step_title = None

        if session_id is not None:
            session = await self.get_session(patient_id, session_id)
            steps = session.steps or []
            remaining_steps = [s for s in steps if s.status in ("pending", "partial")]
            if remaining_steps:
                next_step_title = remaining_steps[0].title
            if not target_work_item_id:
                for s in steps:
                    if s.work_item_id:
                        target_work_item_id = s.work_item_id
                        break

        work_item = None
        tooth_key = None
        proc_code = None
        proc_title = None

        if target_work_item_id is not None:
            stmt = (
                select(models.ClinicalWorkItem)
                .options(selectinload(models.ClinicalWorkItem.targets))
                .where(
                    models.ClinicalWorkItem.id == target_work_item_id,
                    models.ClinicalWorkItem.tenant_id == self.tenant_id,
                    models.ClinicalWorkItem.patient_id == patient_id,
                )
            )
            work_item = (await self.db.execute(stmt)).scalars().first()
            if work_item:
                proc_code = work_item.code
                proc_title = work_item.code
                if work_item.targets:
                    tooth_key = work_item.targets[0].tooth_key

        PROC_DISPLAY_MAP = {
            "ENDO_RCT": "Root Canal Treatment",
            "PROS_CROWN": "Crown",
            "PROS_BRIDGE": "Bridge",
            "REST_COMPOSITE": "Composite Restoration",
            "SURG_EXTRACTION": "Tooth Extraction",
            "IMPLANT_FIXTURE": "Implant Placement",
            "IMPLANT_CROWN": "Implant Crown",
            "PROS_DENTURE": "Denture",
        }
        display_proc = PROC_DISPLAY_MAP.get(proc_code, proc_title or proc_code or "Treatment")

        # Determine Reason (G11-M06) and Suggested Duration (G11-M07)
        if next_step_title:
            if tooth_key:
                reason = f"Tooth {tooth_key}: {display_proc} - {next_step_title}"
            else:
                reason = f"{display_proc} - {next_step_title}"

            if proc_code == "ENDO_RCT":
                suggested_duration = 45
            elif proc_code in ("PROS_CROWN", "PROS_BRIDGE"):
                lower_title = next_step_title.lower()
                if any(k in lower_title for k in ("prep", "scan", "impression")):
                    suggested_duration = 60
                else:
                    suggested_duration = 30
            else:
                suggested_duration = 30
        elif work_item is not None:
            if tooth_key:
                reason = f"Follow-up: Tooth {tooth_key} - {display_proc}"
            else:
                reason = f"Follow-up: {display_proc}"
            suggested_duration = 30
        elif session is not None:
            reason = f"Follow-up for Care Session #{session.id}"
            suggested_duration = 30
        else:
            reason = "Dental Follow-up Visit"
            suggested_duration = 30

        return schemas.NextVisitSuggestionRead(
            reason=reason,
            suggested_duration_minutes=suggested_duration,
            care_session_id=session_id,
            work_item_id=target_work_item_id,
            procedure_code=proc_code,
            tooth_key=tooth_key,
            next_step_title=next_step_title,
            remaining_steps_count=len(remaining_steps),
        )

    async def _create_next_visit_request_internal(
        self,
        patient_id: int,
        data: schemas.NextVisitRequestCreate,
        session: Optional[models.CareSession] = None,
    ) -> models.NextVisitRequest:
        """
        Internal creation helper.
        Enforces G11-M08: NEVER auto-books an appointment without user action.
        """
        target_session_id = session.id if session else data.care_session_id
        target_work_item_id = data.work_item_id

        if not target_work_item_id and session and session.steps:
            for s in session.steps:
                if s.work_item_id:
                    target_work_item_id = s.work_item_id
                    break

        reason = data.reason.strip() if data.reason and data.reason.strip() else None
        duration = data.suggested_duration_minutes

        if not reason:
            suggestion = await self.suggest_next_visit(
                patient_id=patient_id,
                session_id=target_session_id,
                work_item_id=target_work_item_id,
            )
            reason = suggestion.reason
            if not data.suggested_duration_minutes or data.suggested_duration_minutes == 30:
                duration = suggestion.suggested_duration_minutes

        associated_wis = list(getattr(data, "associated_work_item_ids", []) or [])
        if target_work_item_id and target_work_item_id not in associated_wis:
            associated_wis.insert(0, target_work_item_id)
        elif not target_work_item_id and associated_wis:
            target_work_item_id = associated_wis[0]

        user = await self._get_active_current_user()
        request = models.NextVisitRequest(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=target_session_id,
            work_item_id=target_work_item_id,
            associated_work_item_ids=associated_wis if associated_wis else None,
            assigned_doctor_id=getattr(data, "assigned_doctor_id", None),
            requested_by_user_id=user.id if user else None,
            reason=reason,
            suggested_duration_minutes=duration,
            preferred_time_window_start=data.preferred_time_window_start,
            preferred_time_window_end=data.preferred_time_window_end,
            status="requested",
            notes=data.notes,
        )
        self.db.add(request)
        await self.db.flush()

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=target_session_id,
            work_item_id=target_work_item_id,
            event_type="next_visit_request_created",
            occurred_at=datetime.now(timezone.utc),
            actor_user_id=user.id if user else None,
            payload={
                "request_id": request.id,
                "reason": request.reason,
                "suggested_duration_minutes": request.suggested_duration_minutes,
                "care_session_id": target_session_id,
                "work_item_id": target_work_item_id,
                "associated_work_item_ids": associated_wis if associated_wis else None,
                "assigned_doctor_id": request.assigned_doctor_id,
                "status": "requested",
            },
            notes=data.notes,
        )
        self.db.add(event)
        return request

    async def create_next_visit_request(
        self,
        patient_id: int,
        data: schemas.NextVisitRequestCreate,
        session_id: Optional[int] = None,
    ) -> models.NextVisitRequest:
        """
        Create a chairside next-visit request for reception scheduling (G11-M02).
        Enforces G11-M08: NEVER auto-books an appointment without user action.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        session = None
        target_session_id = session_id or data.care_session_id
        if target_session_id is not None:
            session = await self.get_session(patient_id, target_session_id)

        if data.work_item_id is not None:
            await self._verify_work_item(patient_id, data.work_item_id)

        request = await self._create_next_visit_request_internal(
            patient_id=patient_id,
            data=data,
            session=session,
        )

        try:
            await self.db.commit()
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent conflict during next-visit request creation",
            ) from exc

        return request

    async def list_next_visit_requests(
        self,
        patient_id: int,
        session_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[models.NextVisitRequest]:
        """List next-visit requests for a patient with optional session and status filtering."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = select(models.NextVisitRequest).where(
            models.NextVisitRequest.tenant_id == self.tenant_id,
            models.NextVisitRequest.patient_id == patient_id,
        )
        if session_id is not None:
            stmt = stmt.where(models.NextVisitRequest.care_session_id == session_id)
        if status is not None:
            stmt = stmt.where(models.NextVisitRequest.status == status)
        stmt = stmt.order_by(models.NextVisitRequest.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_next_visit_request(
        self, patient_id: int, request_id: int
    ) -> models.NextVisitRequest:
        """Retrieve a specific next-visit request with tenant and patient isolation."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        stmt = select(models.NextVisitRequest).where(
            models.NextVisitRequest.id == request_id,
            models.NextVisitRequest.tenant_id == self.tenant_id,
            models.NextVisitRequest.patient_id == patient_id,
        )
        req = (await self.db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=404, detail="Next visit request not found")
        return req

    async def list_reception_queue(
        self,
        status: Optional[str] = "requested",
        patient_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[models.NextVisitRequest]:
        """
        List next-visit requests for the reception triage queue (G11-M04).
        Scoped by tenant, ordered by preferred window or creation time.
        """
        await self.ensure_native_writes_enabled()

        stmt = (
            select(models.NextVisitRequest)
            .options(
                selectinload(models.NextVisitRequest.patient),
                selectinload(models.NextVisitRequest.care_session),
                selectinload(models.NextVisitRequest.work_item),
            )
            .where(models.NextVisitRequest.tenant_id == self.tenant_id)
        )
        if status and status.lower() != "all":
            stmt = stmt.where(models.NextVisitRequest.status == status)
        if patient_id is not None:
            stmt = stmt.where(models.NextVisitRequest.patient_id == patient_id)

        stmt = (
            stmt.order_by(
                models.NextVisitRequest.preferred_time_window_start.asc().nullslast(),
                models.NextVisitRequest.created_at.desc(),
                models.NextVisitRequest.id.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        requests = list(result.scalars().all())
        for r in requests:
            if r.patient:
                setattr(r, "patient_name", r.patient.name)
                setattr(r, "patient_phone", r.patient.phone)
        return requests

    async def get_follow_up_dashboard(
        self,
        status: Optional[str] = None,
        doctor_id: Optional[int] = None,
        due_category: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        procedure_code: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        calendar_date_from: Optional[date] = None,
        calendar_date_to: Optional[date] = None,
    ) -> schemas.FollowUpDashboardResponse:
        """
        Dashboard query engine for clinic-wide follow-ups and next-visit requests.
        Enforces tenant isolation, patient visibility, and explicit overdue/upcoming semantics.
        """
        await self.ensure_native_writes_enabled()

        user = await self._get_active_current_user()
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # F01: Enforce doctor visibility scope so hidden patients are never leaked
        from backend.services.patient_access_service import visible_patient_ids_query
        visible_ids_subq = await visible_patient_ids_query(self.db, user)

        def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        now = datetime.now(timezone.utc)
        norm_now = _normalize_dt(now)
        norm_date_from = _normalize_dt(date_from)
        norm_date_to = _normalize_dt(date_to)

        calendar_range = calendar_date_from is not None or calendar_date_to is not None
        if calendar_range:
            if date_from is not None or date_to is not None:
                raise HTTPException(status_code=422, detail="Use calendar dates or exact datetime filters, not both")
            if calendar_date_from and calendar_date_to and calendar_date_from > calendar_date_to:
                raise HTTPException(status_code=422, detail="Calendar start date must not follow the end date")
            tz_name = await get_tenant_timezone(self.db, self.tenant_id)
            if calendar_date_from:
                start, _ = tenant_day_utc_bounds_naive(tz_name, local_date=calendar_date_from)
                norm_date_from = start.replace(tzinfo=timezone.utc)
            if calendar_date_to:
                _, end = tenant_day_utc_bounds_naive(tz_name, local_date=calendar_date_to)
                norm_date_to = end.replace(tzinfo=timezone.utc)

        base_stmt = (
            select(models.NextVisitRequest)
            .options(
                selectinload(models.NextVisitRequest.patient),
                selectinload(models.NextVisitRequest.care_session),
                selectinload(models.NextVisitRequest.work_item),
                selectinload(models.NextVisitRequest.assigned_doctor),
            )
            .where(
                models.NextVisitRequest.tenant_id == self.tenant_id,
                models.NextVisitRequest.patient_id.in_(visible_ids_subq),
            )
        )

        all_requests = list((await self.db.execute(base_stmt)).scalars().all())

        counts = schemas.FollowUpDashboardCounts()
        enriched_list = []

        for req in all_requests:
            target_date = req.postponed_to_date or req.preferred_time_window_start or req.preferred_time_window_end
            norm_target_date = _normalize_dt(target_date)

            if req.status == "scheduled":
                cat = "scheduled"
            elif req.status == "stopped":
                cat = "stopped"
            elif req.status == "completed":
                cat = "completed"
            elif norm_target_date is not None:
                if norm_target_date < norm_now:
                    cat = "overdue"
                else:
                    cat = "upcoming"
            else:
                cat = "unscheduled"

            counts.total += 1
            if req.status == "requested":
                counts.requested += 1
            if cat == "overdue":
                counts.overdue += 1
            elif cat == "upcoming":
                counts.upcoming += 1
            elif cat == "unscheduled":
                counts.unscheduled += 1
            if req.status == "postponed":
                counts.postponed += 1
            elif req.status == "stopped":
                counts.stopped += 1
            elif req.status == "scheduled":
                counts.scheduled += 1

            if req.patient:
                setattr(req, "patient_name", req.patient.name)
                setattr(req, "patient_phone", req.patient.phone)
            if req.assigned_doctor:
                doc_name = req.assigned_doctor.full_name or req.assigned_doctor.username or f"Dr. #{req.assigned_doctor.id}"
                setattr(req, "assigned_doctor_name", doc_name)
            if req.work_item:
                setattr(req, "procedure_name", getattr(req.work_item, "code", None))
            setattr(req, "due_category", cat)

            # Filtering
            if status and status.lower() != "all" and req.status != status:
                continue
            if doctor_id is not None and req.assigned_doctor_id != doctor_id:
                continue
            if due_category and due_category.lower() != "all" and cat != due_category:
                continue
            if norm_date_from and norm_target_date and norm_target_date < norm_date_from:
                continue
            if norm_date_to and norm_target_date:
                # Calendar end is next local midnight (exclusive). Legacy
                # datetime filters remain exact, inclusive instant bounds.
                after_end = norm_target_date >= norm_date_to if calendar_range else norm_target_date > norm_date_to
                if after_end:
                    continue
            if procedure_code and procedure_code.lower() != "all":
                proc_name = getattr(req, "procedure_name", None) or (req.work_item.code if req.work_item else None)
                if not proc_name or proc_name.strip().upper() != procedure_code.strip().upper():
                    continue
            if search:
                s_lower = search.strip().lower()
                p_name = (req.patient.name if req.patient else "").lower()
                p_phone = (req.patient.phone if req.patient else "").lower()
                r_reason = (req.reason or "").lower()
                r_notes = (req.notes or "").lower()
                if not (s_lower in p_name or s_lower in p_phone or s_lower in r_reason or s_lower in r_notes):
                    continue

            enriched_list.append(req)

        def sort_key(r):
            cat_order = {"overdue": 0, "upcoming": 1, "unscheduled": 2, "postponed": 3, "scheduled": 4, "stopped": 5, "completed": 6}
            cat = getattr(r, "due_category", "unscheduled")
            t_date = _normalize_dt(r.postponed_to_date or r.preferred_time_window_start or r.created_at)
            return (cat_order.get(cat, 9), t_date or norm_now)

        sorted_items = sorted(enriched_list, key=sort_key)
        total_filtered = len(sorted_items)
        paged_items = sorted_items[skip : skip + limit]

        reads = [schemas.NextVisitRequestRead.model_validate(item) for item in paged_items]

        return schemas.FollowUpDashboardResponse(
            counts=counts,
            items=reads,
            total_count=total_filtered,
        )

    async def schedule_next_visit_request(
        self,
        request_id: int,
        data: schemas.NextVisitRequestSchedule,
    ) -> Tuple[models.NextVisitRequest, models.Appointment]:
        """
        Convert a chairside next-visit request into a confirmed appointment (G11-M05).
        Enforces G11-M08: never auto-books an appointment without confirmed receptionist action.
        Guards against concurrency races (G11-M12): raises 409 if already scheduled/resolved.
        """
        await self.ensure_native_writes_enabled()

        stmt = (
            select(models.NextVisitRequest)
            .options(selectinload(models.NextVisitRequest.patient))
            .where(
                models.NextVisitRequest.id == request_id,
                models.NextVisitRequest.tenant_id == self.tenant_id,
            )
        )
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        req = result.scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=404, detail="Next-visit request not found")

        await self._verify_patient(req.patient_id)

        if req.status != "requested":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot schedule next-visit request with status '{req.status}'. Only 'requested' items can be scheduled.",
            )

        if data.doctor_id is not None:
            doctor_stmt = select(models.User).where(
                models.User.id == data.doctor_id,
                models.User.tenant_id == self.tenant_id,
            )
            doctor = (await self.db.execute(doctor_stmt)).scalar_one_or_none()
            if not doctor:
                raise HTTPException(status_code=404, detail="Doctor not found")

        if data.price_list_id is not None:
            pl_stmt = select(models.PriceList).where(
                models.PriceList.id == data.price_list_id,
                models.PriceList.tenant_id == self.tenant_id,
            )
            price_list = (await self.db.execute(pl_stmt)).scalar_one_or_none()
            if not price_list:
                raise HTTPException(status_code=404, detail="Price list not found")

        duration = data.duration_minutes or req.suggested_duration_minutes or 30
        appt_notes = data.notes.strip() if data.notes and data.notes.strip() else req.reason

        appointment = models.Appointment(
            tenant_id=self.tenant_id,
            patient_id=req.patient_id,
            doctor_id=data.doctor_id,
            price_list_id=data.price_list_id,
            date_time=data.date_time,
            duration_minutes=duration,
            status="Scheduled",
            notes=appt_notes,
        )
        self.db.add(appointment)
        await self.db.flush()

        req.status = "scheduled"
        token = f"[APPOINTMENT:{appointment.id}]"
        if req.notes:
            if token not in req.notes:
                req.notes = f"{req.notes} {token}"
        else:
            req.notes = token

        user = await self._get_active_current_user()
        now = datetime.now(timezone.utc)
        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=req.patient_id,
            care_session_id=req.care_session_id,
            work_item_id=req.work_item_id,
            event_type="next_visit_request_scheduled",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "request_id": req.id,
                "appointment_id": appointment.id,
                "date_time": appointment.date_time.isoformat() if appointment.date_time else None,
                "doctor_id": appointment.doctor_id,
                "duration_minutes": duration,
                "status": "scheduled",
            },
            notes=f"Converted to Appointment #{appointment.id}",
        )
        self.db.add(event)

        try:
            await self.db.commit()
            await self.db.refresh(req)
            await self.db.refresh(appointment)
            # A newly created request can already be in the identity map.
            # Explicit refresh avoids an async lazy load after commit/refresh.
            await self.db.refresh(req, attribute_names=['patient'])
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent conflict while scheduling next-visit request",
            ) from exc

        if req.patient:
            setattr(req, "patient_name", req.patient.name)
            setattr(req, "patient_phone", req.patient.phone)
        setattr(req, "fulfilled_appointment_id", appointment.id)
        return req, appointment

    async def cancel_next_visit_request(
        self,
        request_id: int,
        reason: Optional[str] = None,
    ) -> models.NextVisitRequest:
        """
        Cancel a pending next-visit request (e.g. patient declines follow-up).
        """
        await self.ensure_native_writes_enabled()

        stmt = (
            select(models.NextVisitRequest)
            .options(selectinload(models.NextVisitRequest.patient))
            .where(
                models.NextVisitRequest.id == request_id,
                models.NextVisitRequest.tenant_id == self.tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        req = result.scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=404, detail="Next-visit request not found")

        await self._verify_patient(req.patient_id)

        if req.status == "completed":
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel an already completed next-visit request",
            )

        req.status = "cancelled"
        cancel_note = f"Cancelled: {reason.strip()}" if reason and reason.strip() else "Cancelled by front-desk"
        if req.notes:
            req.notes = f"{req.notes} ({cancel_note})"
        else:
            req.notes = cancel_note

        user = await self._get_active_current_user()
        now = datetime.now(timezone.utc)
        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=req.patient_id,
            care_session_id=req.care_session_id,
            work_item_id=req.work_item_id,
            event_type="next_visit_request_cancelled",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "request_id": req.id,
                "status": "cancelled",
                "reason": reason,
            },
            notes=cancel_note,
        )
        self.db.add(event)

        try:
            await self.db.commit()
            await self.db.refresh(req)
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            await self._get_active_current_user()
            raise HTTPException(
                status_code=409,
                detail="Concurrent conflict while cancelling next-visit request",
            ) from exc

        if req.patient:
            setattr(req, "patient_name", req.patient.name)
            setattr(req, "patient_phone", req.patient.phone)
        return req

    async def _get_next_visit_request_row(
        self, request_id: int, patient_id: Optional[int] = None, for_update: bool = False
    ) -> models.NextVisitRequest:
        stmt = (
            select(models.NextVisitRequest)
            .options(selectinload(models.NextVisitRequest.patient))
            .where(
                models.NextVisitRequest.id == request_id,
                models.NextVisitRequest.tenant_id == self.tenant_id,
            )
        )
        if patient_id is not None:
            stmt = stmt.where(models.NextVisitRequest.patient_id == patient_id)
        if for_update:
            stmt = stmt.with_for_update()
        req = (await self.db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=404, detail="Next-visit request not found")
        return req

    async def stop_next_visit_request(
        self,
        request_id: int,
        reason: str,
        patient_id: Optional[int] = None,
    ) -> models.NextVisitRequest:
        """Stop a pending next-visit reminder with an explicit reason (audited)."""
        await self.ensure_native_writes_enabled()
        req = await self._get_next_visit_request_row(request_id, patient_id=patient_id, for_update=True)
        await self._verify_patient(req.patient_id)

        if req.status in ("completed", "scheduled"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot stop next-visit request: request is already {req.status}.",
            )

        user = await self._get_active_current_user()
        now = datetime.now(timezone.utc)

        req.status = "stopped"
        req.stopped_at = now
        req.stopped_reason = reason
        req.stopped_by_user_id = user.id if user else None

        stop_note = f"Stopped: {reason.strip()}"
        req.notes = f"{req.notes} ({stop_note})" if req.notes else stop_note

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=req.patient_id,
            care_session_id=req.care_session_id,
            work_item_id=req.work_item_id,
            event_type="next_visit_request_stopped",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "request_id": req.id,
                "status": "stopped",
                "reason": reason,
            },
            notes=stop_note,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(req)
        if req.patient:
            setattr(req, "patient_name", req.patient.name)
            setattr(req, "patient_phone", req.patient.phone)
        return req

    async def postpone_next_visit_request(
        self,
        request_id: int,
        postponed_to_date: datetime,
        reason: str,
        patient_id: Optional[int] = None,
    ) -> models.NextVisitRequest:
        """Postpone a next-visit reminder with a reason and new target date (audited)."""
        await self.ensure_native_writes_enabled()
        req = await self._get_next_visit_request_row(request_id, patient_id=patient_id, for_update=True)
        await self._verify_patient(req.patient_id)

        if req.status in ("completed", "scheduled"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot postpone next-visit request: request is already {req.status}.",
            )

        user = await self._get_active_current_user()
        now = datetime.now(timezone.utc)

        req.status = "postponed"
        req.postponed_to_date = postponed_to_date
        req.postponed_reason = reason
        req.postponed_by_user_id = user.id if user else None
        req.preferred_time_window_start = postponed_to_date

        postpone_note = f"Postponed to {postponed_to_date.isoformat()}: {reason.strip()}"
        req.notes = f"{req.notes} ({postpone_note})" if req.notes else postpone_note

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=req.patient_id,
            care_session_id=req.care_session_id,
            work_item_id=req.work_item_id,
            event_type="next_visit_request_postponed",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "request_id": req.id,
                "status": "postponed",
                "postponed_to_date": postponed_to_date.isoformat(),
                "reason": reason,
            },
            notes=postpone_note,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(req)
        if req.patient:
            setattr(req, "patient_name", req.patient.name)
            setattr(req, "patient_phone", req.patient.phone)
        return req

    async def resume_next_visit_request(
        self,
        request_id: int,
        reason: Optional[str] = None,
        patient_id: Optional[int] = None,
    ) -> models.NextVisitRequest:
        """Resume an active follow-up reminder that was previously stopped or postponed."""
        await self.ensure_native_writes_enabled()
        req = await self._get_next_visit_request_row(request_id, patient_id=patient_id, for_update=True)
        await self._verify_patient(req.patient_id)

        # Transition validation under lock (Issue 9)
        if req.status in ("completed", "scheduled"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot resume next-visit request: request is already {req.status} and cannot be reopened.",
            )
        if req.status not in ("stopped", "postponed"):
            raise HTTPException(
                status_code=422,
                detail=f"Cannot resume next-visit request with status '{req.status}'. Only stopped or postponed requests can be resumed.",
            )

        user = await self._get_active_current_user()
        now = datetime.now(timezone.utc)

        req.status = "requested"
        req.stopped_at = None
        req.stopped_reason = None
        req.stopped_by_user_id = None
        req.postponed_to_date = None
        req.postponed_reason = None
        req.postponed_by_user_id = None
        # Appointment linkage is preserved

        resume_note = f"Resumed: {reason.strip()}" if reason and reason.strip() else "Resumed follow-up"
        req.notes = f"{req.notes} ({resume_note})" if req.notes else resume_note

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=req.patient_id,
            care_session_id=req.care_session_id,
            work_item_id=req.work_item_id,
            event_type="next_visit_request_resumed",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "request_id": req.id,
                "status": "requested",
                "reason": reason,
            },
            notes=resume_note,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(req)
        if req.patient:
            setattr(req, "patient_name", req.patient.name)
            setattr(req, "patient_phone", req.patient.phone)
        return req

    async def handoff_next_visit_request(
        self,
        request_id: int,
        handoff_to_user_id: int,
        reason: str,
        notes: Optional[str] = None,
        patient_id: Optional[int] = None,
    ) -> models.NextVisitRequest:
        """Handoff follow-up responsibility to another doctor in tenant (audited)."""
        await self.ensure_native_writes_enabled()
        req = await self._get_next_visit_request_row(request_id, patient_id=patient_id, for_update=True)
        await self._verify_patient(req.patient_id)

        if req.status == "completed":
            raise HTTPException(status_code=409, detail="Cannot handoff completed next-visit request.")

        # Validate recipient doctor belongs to tenant
        recipient = (await self.db.execute(
            select(models.User).where(
                models.User.id == handoff_to_user_id,
                models.User.tenant_id == self.tenant_id,
            )
        )).scalar_one_or_none()
        if not recipient:
            raise HTTPException(status_code=404, detail="Handoff recipient doctor not found in clinic")

        # Verify recipient has access to patient
        await ensure_patient_visible(self.db, recipient, req.patient_id)

        user = await self._get_active_current_user()
        now = datetime.now(timezone.utc)

        req.assigned_doctor_id = handoff_to_user_id
        req.handoff_at = now
        req.handoff_reason = reason
        req.handoff_by_user_id = user.id if user else None
        req.handoff_to_user_id = handoff_to_user_id

        handoff_note = f"Handoff to Dr. {getattr(recipient, 'name', handoff_to_user_id)}: {reason}"
        if notes:
            handoff_note += f". Instructions: {notes}"
        req.notes = f"{req.notes} ({handoff_note})" if req.notes else handoff_note

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=req.patient_id,
            care_session_id=req.care_session_id,
            work_item_id=req.work_item_id,
            event_type="next_visit_request_handed_off",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "request_id": req.id,
                "handoff_to_user_id": handoff_to_user_id,
                "reason": reason,
                "instructions": notes,
            },
            notes=handoff_note,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(req)
        if req.patient:
            setattr(req, "patient_name", req.patient.name)
            setattr(req, "patient_phone", req.patient.phone)
        return req

    # -----------------------------------------------------------------------
    # Server Drafts Management (Step 3 / Section 2.6)
    # -----------------------------------------------------------------------

    async def save_draft(
        self,
        patient_id: int,
        payload: schemas.CareSessionDraftSave,
    ) -> models.CareSessionDraft:
        """Save autosaved documentation draft with optimistic concurrency."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)
        if payload.care_session_id is not None:
            await self.get_session(patient_id, payload.care_session_id)

        user = await self._get_active_current_user()
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        now = datetime.now(timezone.utc)
        stmt = select(models.CareSessionDraft).where(
            models.CareSessionDraft.tenant_id == self.tenant_id,
            models.CareSessionDraft.patient_id == patient_id,
            models.CareSessionDraft.author_user_id == user.id,
        ).with_for_update()
        draft = (await self.db.execute(stmt)).scalar_one_or_none()

        if draft:
            if payload.expected_version_id is not None and draft.version_id != payload.expected_version_id:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": f"Draft conflict: expected version {payload.expected_version_id}, server has {draft.version_id}",
                        "current_version_id": draft.version_id,
                        "server_draft_data": draft.draft_payload,
                    },
                )
            draft.draft_payload = payload.draft_data
            draft.care_session_id = payload.care_session_id
            draft.version_id += 1
            draft.updated_at = now
        else:
            draft = models.CareSessionDraft(
                tenant_id=self.tenant_id,
                patient_id=patient_id,
                author_user_id=user.id,
                care_session_id=payload.care_session_id,
                draft_payload=payload.draft_data,
                version_id=1,
                created_at=now,
                updated_at=now,
            )
            self.db.add(draft)

        try:
            await self.db.commit()
            await self.db.refresh(draft)
        except (IntegrityError, StaleDataError) as exc:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Concurrent conflict while saving draft") from exc

        return draft

    async def get_draft(
        self,
        patient_id: int,
    ) -> Optional[models.CareSessionDraft]:
        """Recover editable draft for current author on this patient."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        user = await self._get_active_current_user()
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        stmt = select(models.CareSessionDraft).where(
            models.CareSessionDraft.tenant_id == self.tenant_id,
            models.CareSessionDraft.patient_id == patient_id,
            models.CareSessionDraft.author_user_id == user.id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def delete_draft(
        self,
        patient_id: int,
    ) -> bool:
        """Clear draft after successful finalization or discarding."""
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        user = await self._get_active_current_user()
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        stmt = select(models.CareSessionDraft).where(
            models.CareSessionDraft.tenant_id == self.tenant_id,
            models.CareSessionDraft.patient_id == patient_id,
            models.CareSessionDraft.author_user_id == user.id,
        )
        draft = (await self.db.execute(stmt)).scalar_one_or_none()
        if draft:
            await self.db.delete(draft)
            await self.db.commit()
            return True
        return False

    # -----------------------------------------------------------------------
    # Observation Amendments & Supersession (Section 2.7)
    # -----------------------------------------------------------------------

    async def _resolve_effective_observation_chain(
        self, obs: models.CareObservation
    ) -> models.CareObservation:
        """
        Resolves an observation (or carried reference) to its latest effective non-superseded observation.
        Follows local superseded_by_id amendment chains first, and if the effective measurement
        is a carried reference, follows reference_source_observation_id provenance recursively.
        """
        curr = obs
        visited = set()
        # 1. Follow amendment lineage: amendments in the current session supersede initial state
        while curr.is_superseded and curr.superseded_by_id and curr.id not in visited:
            visited.add(curr.id)
            next_stmt = select(models.CareObservation).where(
                models.CareObservation.id == curr.superseded_by_id,
                models.CareObservation.tenant_id == self.tenant_id,
            )
            next_obs = (await self.db.execute(next_stmt)).scalar_one_or_none()
            if not next_obs:
                break
            curr = next_obs

        # 2. If the effective observation is an un-amended carried reference, resolve through reference provenance
        if curr.reference_source_observation_id:
            root_stmt = select(models.CareObservation).where(
                models.CareObservation.id == curr.reference_source_observation_id,
                models.CareObservation.tenant_id == self.tenant_id,
            )
            root = (await self.db.execute(root_stmt)).scalar_one_or_none()
            if root:
                curr = await self._resolve_effective_observation_chain(root)

        return curr

    @staticmethod
    def _build_effective_observation_dto(
        reference: models.CareObservation, effective: models.CareObservation
    ) -> schemas.CareObservationRead:
        """Keep reference identity/provenance while presenting the complete effective measurement."""
        reference_data = schemas.CareObservationRead.model_validate(reference).model_dump()
        clinical_data = schemas.CareObservationRead.model_validate(effective).model_dump(
            include={
                "observation_code", "tooth_key", "structured_value", "notes",
                "surface_code", "root_id", "canal_id",
            }
        )
        return schemas.CareObservationRead.model_validate(
            {**reference_data, **deepcopy(clinical_data)}
        )

    async def _project_session_observations(
        self, session: models.CareSession
    ) -> List[Any]:
        """
        Projects effective measurements for observations attached to a care session.
        Returns a list of separate response copies/DTOs for presentation,
        keeping the underlying persistence entities completely unchanged.
        """
        if not session or not session.observations:
            return []

        projected = []
        for obs in session.observations:
            if not obs.is_superseded and obs.reference_source_observation_id:
                eff = await self._resolve_effective_observation_chain(obs)
                if eff and eff.id != obs.id:
                    projected.append(self._build_effective_observation_dto(obs, eff))
                    continue
            projected.append(obs)
        return projected

    async def amend_observation(
        self,
        patient_id: int,
        observation_id: int,
        payload: schemas.CareObservationAmend,
    ) -> models.CareObservation:
        """
        Amend a chairside observation / measurement.
        Preserves original row, sets is_superseded=True, and creates replacement observation
        referencing original. Atomically logs observation_amended ClinicalEvent.
        """
        await self.ensure_native_writes_enabled()
        await self._verify_patient(patient_id)

        user = await self._get_active_current_user()
        now = datetime.now(timezone.utc)

        stmt = select(models.CareObservation).where(
            models.CareObservation.id == observation_id,
            models.CareObservation.tenant_id == self.tenant_id,
            models.CareObservation.patient_id == patient_id,
        ).with_for_update()
        orig = (await self.db.execute(stmt)).scalar_one_or_none()
        if not orig:
            raise HTTPException(status_code=404, detail="Observation not found")

        if orig.is_superseded:
            raise HTTPException(status_code=409, detail="Observation has already been superseded by a prior amendment")

        merged_sv = dict(orig.structured_value or {})
        if payload.structured_value is not None:
            merged_sv.update(payload.structured_value)
        if payload.surface_code:
            merged_sv["surface_code"] = payload.surface_code
        if payload.root_id:
            merged_sv["root_id"] = payload.root_id
        if payload.canal_id:
            merged_sv["canal_id"] = payload.canal_id

        new_obs = models.CareObservation(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=orig.care_session_id,
            step_id=orig.step_id,
            work_item_id=orig.work_item_id,
            observation_code=payload.observation_code or orig.observation_code,
            tooth_key=payload.tooth_key or orig.tooth_key,
            structured_value=merged_sv,
            notes=f"[Amendment] {payload.reason}: {payload.notes or ''}".strip(),
            recorded_by_user_id=user.id if user else None,
            recorded_at=now,
            amendment_reason=payload.reason,
            reference_source_session_id=orig.care_session_id,
            reference_source_date=orig.recorded_at or orig.created_at,
            reference_source_observation_id=None,
        )
        self.db.add(new_obs)
        await self.db.flush()

        orig.is_superseded = True
        orig.superseded_by_id = new_obs.id
        orig.amendment_reason = payload.reason

        event = models.ClinicalEvent(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            care_session_id=orig.care_session_id,
            work_item_id=orig.work_item_id,
            event_type="observation_amended",
            occurred_at=now,
            actor_user_id=user.id if user else None,
            payload={
                "original_observation_id": orig.id,
                "replacement_observation_id": new_obs.id,
                "reason": payload.reason,
            },
            notes=payload.reason,
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(new_obs)
        return new_obs
