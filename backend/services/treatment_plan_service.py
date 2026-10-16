"""
Clinical Treatment Plan Service (Slice G9a).

Manages patient-level treatment plans with sequential phases.
Enforces:
- Tenant isolation and patient visibility scoping (404 on mismatch).
- Feature flag gate (fail-closed 404 when disabled).
- Single default phase ("Phase 1", phase_order 0, draft) on plan creation.
- Creator attribution (created_by_user_id).
- Status locked to 'draft' in this slice.
"""

from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.services.feature_service import FeatureFlagService
from backend.services.patient_access_service import ensure_patient_visible
from backend.core.config import is_clinical_treatment_plans_enabled

FEATURE_KEY_TREATMENT_PLANS = "clinical_treatment_plans"


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

        # 3. Reload with eager phases
        stmt = (
            select(models.ClinicalTreatmentPlan)
            .where(
                models.ClinicalTreatmentPlan.id == plan.id,
                models.ClinicalTreatmentPlan.tenant_id == self.tenant_id,
            )
            .options(selectinload(models.ClinicalTreatmentPlan.phases))
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
            .options(selectinload(models.ClinicalTreatmentPlan.phases))
            .order_by(
                models.ClinicalTreatmentPlan.created_at.desc(),
                models.ClinicalTreatmentPlan.id.desc(),
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
