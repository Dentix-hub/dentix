"""
Clinical Treatment Plans Router (Slice G9a).
Provides patient-scoped endpoints for creating and listing treatment plans.
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.services.treatment_plan_service import TreatmentPlanService

router = APIRouter(prefix="/patients", tags=["Clinical Treatment Plans"])


@router.post(
    "/{patient_id}/clinical-plans",
    response_model=StandardResponse[schemas.ClinicalTreatmentPlanRead],
    summary="Create clinical treatment plan",
    description="Create a draft treatment plan and its default phase for a patient.",
)
async def create_patient_clinical_plan(
    patient_id: int,
    payload: schemas.ClinicalTreatmentPlanCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    service = TreatmentPlanService(db, current_user.tenant_id, current_user)
    plan = await service.create_plan(patient_id, payload)
    return success_response(
        data=schemas.ClinicalTreatmentPlanRead.model_validate(plan),
        message="Treatment plan created successfully",
    )


@router.get(
    "/{patient_id}/clinical-plans",
    response_model=StandardResponse[List[schemas.ClinicalTreatmentPlanRead]],
    summary="List patient clinical treatment plans",
    description="List all treatment plans and phases for a patient.",
)
async def list_patient_clinical_plans(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = TreatmentPlanService(db, current_user.tenant_id, current_user)
    plans = await service.list_plans(patient_id)
    return success_response(
        data=[schemas.ClinicalTreatmentPlanRead.model_validate(p) for p in plans],
        message="Treatment plans retrieved successfully",
    )
