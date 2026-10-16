"""
Clinical Treatment Plan Service (Slices G9a & G9b).

Manages patient-level treatment plans with sequential phases and procedure membership.
Enforces:
- Tenant isolation and patient visibility scoping (404 on mismatch).
- Feature flag gate (fail-closed 404 when disabled).
- Single default phase ("Phase 1", phase_order 0, draft) on plan creation.
- Creator attribution (created_by_user_id).
- Status locked to 'draft' in this slice.
- Phase creation with sequential phase_order and retry on ordering race.
- Procedure/work-item attachment with non-cancelled validation and 409 duplicate check.
- Work items shared across alternative plans without duplicating care episodes (G9-M05).
- Unlink item leaves underlying ClinicalWorkItem untouched.
"""

from typing import List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend import models, schemas
from backend.core.config import is_clinical_treatment_plans_enabled
from backend.services.feature_service import FeatureFlagService
from backend.services.patient_access_service import ensure_patient_visible

FEATURE_KEY_TREATMENT_PLANS = "clinical_treatment_plans"


def _eager_plan_options():
    return (
        selectinload(models.ClinicalTreatmentPlan.phases)
        .selectinload(models.ClinicalTreatmentPlanPhase.items)
        .selectinload(models.ClinicalTreatmentPlanItem.work_item)
        .selectinload(models.ClinicalWorkItem.targets)
    )


class TreatmentPlanService:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        current_user: Optional[models.User] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.current_user = current_user

    async def is_enabled(self) -> bool:
        """
        Check if treatment plans are enabled.
        Priority:
        1. Config flag / environment variable override.
        2. Per-tenant feature flag mechanism via FeatureFlagService.
        """
        if is_clinical_treatment_plans_enabled():
            return True
        if self.tenant_id:
            return await FeatureFlagService.is_feature_enabled(
                self.db, FEATURE_KEY_TREATMENT_PLANS, self.tenant_id
            )
        return False

    async def ensure_enabled(self) -> None:
        """Enforce server-side 404 when disabled."""
        if not await self.is_enabled():
            raise HTTPException(
                status_code=404,
                detail="Treatment plans feature is disabled",
            )

    async def _verify_patient(self, patient_id: int) -> None:
        """Validate patient exists within tenant and is visible to current user."""
        if self.current_user:
            await ensure_patient_visible(self.db, self.current_user, patient_id)
        else:
            stmt = select(models.Patient).where(
                models.Patient.id == patient_id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
            patient = (await self.db.execute(stmt)).scalar_one_or_none()
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")

    async def _get_plan_and_verify(
        self, patient_id: int, plan_id: int
    ) -> models.ClinicalTreatmentPlan:
        """Validate plan exists, belongs to tenant and patient."""
        await self.ensure_enabled()
        await self._verify_patient(patient_id)

        stmt = select(models.ClinicalTreatmentPlan).where(
            models.ClinicalTreatmentPlan.id == plan_id,
            models.ClinicalTreatmentPlan.tenant_id == self.tenant_id,
            models.ClinicalTreatmentPlan.patient_id == patient_id,
        )
        plan = (await self.db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Treatment plan not found")
        return plan

    async def _get_phase_and_verify(
        self, patient_id: int, plan_id: int, phase_id: int
    ) -> Tuple[models.ClinicalTreatmentPlan, models.ClinicalTreatmentPlanPhase]:
        """Validate plan and phase exist and belong together within tenant/patient."""
        plan = await self._get_plan_and_verify(patient_id, plan_id)

        stmt = select(models.ClinicalTreatmentPlanPhase).where(
            models.ClinicalTreatmentPlanPhase.id == phase_id,
            models.ClinicalTreatmentPlanPhase.tenant_id == self.tenant_id,
            models.ClinicalTreatmentPlanPhase.plan_id == plan.id,
        )
        phase = (await self.db.execute(stmt)).scalar_one_or_none()
        if not phase:
            raise HTTPException(status_code=404, detail="Treatment plan phase not found")
        return plan, phase

    async def create_plan(
        self,
        patient_id: int,
        plan_data: schemas.ClinicalTreatmentPlanCreate,
    ) -> models.ClinicalTreatmentPlan:
        await self.ensure_enabled()
        await self._verify_patient(patient_id)

        clean_title = plan_data.title.strip()
        if not clean_title:
            raise HTTPException(status_code=422, detail="Title cannot be empty")

        clean_notes = plan_data.notes.strip() if plan_data.notes else None

        # 1. Create plan
        plan = models.ClinicalTreatmentPlan(
            tenant_id=self.tenant_id,
            patient_id=patient_id,
            title=clean_title,
            status="draft",
            notes=clean_notes,
            created_by_user_id=self.current_user.id if self.current_user else None,
        )
        self.db.add(plan)
        await self.db.flush()

        # 2. Decision 2: Creating a plan also creates ONE default phase (phase_order 0, localized "Phase 1")
        default_phase = models.ClinicalTreatmentPlanPhase(
            tenant_id=self.tenant_id,
            plan_id=plan.id,
            phase_order=0,
            name="Phase 1",
            status="draft",
            notes=None,
        )
        self.db.add(default_phase)
        await self.db.commit()

        # 3. Reload with eager phases and items
        stmt = (
            select(models.ClinicalTreatmentPlan)
            .where(
                models.ClinicalTreatmentPlan.id == plan.id,
                models.ClinicalTreatmentPlan.tenant_id == self.tenant_id,
            )
            .options(_eager_plan_options())
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def list_plans(
        self,
        patient_id: int,
    ) -> List[models.ClinicalTreatmentPlan]:
        await self.ensure_enabled()
        await self._verify_patient(patient_id)

        stmt = (
            select(models.ClinicalTreatmentPlan)
            .where(
                models.ClinicalTreatmentPlan.tenant_id == self.tenant_id,
                models.ClinicalTreatmentPlan.patient_id == patient_id,
            )
            .options(_eager_plan_options())
            .execution_options(populate_existing=True)
            .order_by(
                models.ClinicalTreatmentPlan.created_at.desc(),
                models.ClinicalTreatmentPlan.id.desc(),
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_candidate_work_items(
        self,
        patient_id: int,
        plan_id: int,
    ) -> List[models.ClinicalWorkItem]:
        """
        Amendment A: Return patient's non-cancelled ClinicalWorkItems for selector.
        Tenant and patient scoped.
        """
        await self._get_plan_and_verify(patient_id, plan_id)

        stmt = (
            select(models.ClinicalWorkItem)
            .where(
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
                models.ClinicalWorkItem.patient_id == patient_id,
                models.ClinicalWorkItem.status != "cancelled",
            )
            .options(selectinload(models.ClinicalWorkItem.targets))
            .order_by(
                models.ClinicalWorkItem.created_at.desc(),
                models.ClinicalWorkItem.id.desc(),
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def add_phase(
        self,
        patient_id: int,
        plan_id: int,
        data: schemas.ClinicalTreatmentPlanPhaseCreate,
    ) -> models.ClinicalTreatmentPlanPhase:
        """
        Add a new phase to the plan.
        Auto-assigns next phase_order, validates name, retries on ordering race.
        """
        plan = await self._get_plan_and_verify(patient_id, plan_id)

        clean_name = data.name.strip()
        if not clean_name:
            raise HTTPException(status_code=422, detail="Phase name cannot be empty")
        if len(clean_name) > 255:
            raise HTTPException(status_code=422, detail="Phase name cannot exceed 255 characters")
        clean_notes = data.notes.strip() if data.notes else None

        async def _attempt_insert() -> models.ClinicalTreatmentPlanPhase:
            max_order_stmt = select(func.max(models.ClinicalTreatmentPlanPhase.phase_order)).where(
                models.ClinicalTreatmentPlanPhase.tenant_id == self.tenant_id,
                models.ClinicalTreatmentPlanPhase.plan_id == plan.id,
            )
            max_order = (await self.db.execute(max_order_stmt)).scalar()
            next_order = (max_order + 1) if max_order is not None else 0

            phase = models.ClinicalTreatmentPlanPhase(
                tenant_id=self.tenant_id,
                plan_id=plan.id,
                phase_order=next_order,
                name=clean_name,
                status="draft",
                notes=clean_notes,
            )
            self.db.add(phase)
            await self.db.commit()
            self.db.expire(plan, ["phases"])

            stmt_reload = (
                select(models.ClinicalTreatmentPlanPhase)
                .where(
                    models.ClinicalTreatmentPlanPhase.id == phase.id,
                    models.ClinicalTreatmentPlanPhase.tenant_id == self.tenant_id,
                )
                .options(
                    selectinload(models.ClinicalTreatmentPlanPhase.items)
                    .selectinload(models.ClinicalTreatmentPlanItem.work_item)
                    .selectinload(models.ClinicalWorkItem.targets)
                )
            )
            return (await self.db.execute(stmt_reload)).scalar_one()

        try:
            return await _attempt_insert()
        except IntegrityError:
            await self.db.rollback()
            try:
                return await _attempt_insert()
            except IntegrityError:
                await self.db.rollback()
                raise HTTPException(status_code=409, detail="Concurrent phase order conflict")

    async def add_work_item_to_phase(
        self,
        patient_id: int,
        plan_id: int,
        phase_id: int,
        data: schemas.ClinicalTreatmentPlanItemCreate,
    ) -> models.ClinicalTreatmentPlanItem:
        """
        Amendment B & C: Link existing ClinicalWorkItem into a treatment plan phase.
        Validates work item belongs to same tenant & patient, status != 'cancelled'.
        Duplicate work item in same phase -> 409.
        Multi-plan sharing allowed (same work item in multiple plans).
        """
        plan, phase = await self._get_phase_and_verify(patient_id, plan_id, phase_id)

        stmt_wi = (
            select(models.ClinicalWorkItem)
            .where(
                models.ClinicalWorkItem.id == data.work_item_id,
                models.ClinicalWorkItem.tenant_id == self.tenant_id,
                models.ClinicalWorkItem.patient_id == patient_id,
            )
        )
        work_item = (await self.db.execute(stmt_wi)).scalar_one_or_none()
        if not work_item:
            raise HTTPException(status_code=404, detail="Work item not found for patient")
        if work_item.status == "cancelled":
            raise HTTPException(
                status_code=422,
                detail="Cancelled work item cannot be added to a treatment plan phase",
            )

        stmt_dup = select(models.ClinicalTreatmentPlanItem).where(
            models.ClinicalTreatmentPlanItem.tenant_id == self.tenant_id,
            models.ClinicalTreatmentPlanItem.phase_id == phase.id,
            models.ClinicalTreatmentPlanItem.work_item_id == work_item.id,
        )
        if (await self.db.execute(stmt_dup)).scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Work item is already attached to this phase")

        clean_notes = data.notes.strip() if data.notes else None

        async def _attempt_insert() -> models.ClinicalTreatmentPlanItem:
            max_order_stmt = select(func.max(models.ClinicalTreatmentPlanItem.item_order)).where(
                models.ClinicalTreatmentPlanItem.tenant_id == self.tenant_id,
                models.ClinicalTreatmentPlanItem.phase_id == phase.id,
            )
            max_order = (await self.db.execute(max_order_stmt)).scalar()
            next_order = (max_order + 1) if max_order is not None else 0

            item = models.ClinicalTreatmentPlanItem(
                tenant_id=self.tenant_id,
                phase_id=phase.id,
                work_item_id=work_item.id,
                item_order=next_order,
                status="planned",
                notes=clean_notes,
            )
            self.db.add(item)
            await self.db.commit()
            self.db.expire(phase, ["items"])

            stmt_reload = (
                select(models.ClinicalTreatmentPlanItem)
                .where(
                    models.ClinicalTreatmentPlanItem.id == item.id,
                    models.ClinicalTreatmentPlanItem.tenant_id == self.tenant_id,
                )
                .options(
                    selectinload(models.ClinicalTreatmentPlanItem.work_item)
                    .selectinload(models.ClinicalWorkItem.targets)
                )
            )
            return (await self.db.execute(stmt_reload)).scalar_one()

        try:
            return await _attempt_insert()
        except IntegrityError:
            await self.db.rollback()
            # Double check if duplicate work item was committed concurrently
            if (await self.db.execute(stmt_dup)).scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Work item is already attached to this phase")
            # Retry once for order collision
            try:
                return await _attempt_insert()
            except IntegrityError:
                await self.db.rollback()
                raise HTTPException(status_code=409, detail="Concurrent item conflict in phase")

    async def remove_work_item_from_phase(
        self,
        patient_id: int,
        plan_id: int,
        phase_id: int,
        item_id: int,
    ) -> None:
        """
        Unlink item from phase. Removes ClinicalTreatmentPlanItem row.
        Underlying ClinicalWorkItem is untouched.
        """
        plan, phase = await self._get_phase_and_verify(patient_id, plan_id, phase_id)

        stmt_item = select(models.ClinicalTreatmentPlanItem).where(
            models.ClinicalTreatmentPlanItem.id == item_id,
            models.ClinicalTreatmentPlanItem.tenant_id == self.tenant_id,
            models.ClinicalTreatmentPlanItem.phase_id == phase.id,
        )
        item = (await self.db.execute(stmt_item)).scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Treatment plan item not found")

        await self.db.delete(item)
        await self.db.commit()
        self.db.expire(phase, ["items"])
