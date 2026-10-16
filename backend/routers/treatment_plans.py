"""
Clinical Treatment Plans Router (Slices G9a & G9b).
Provides patient-scoped endpoints for treatment plans, phases, candidate work items, and phase item membership.
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.database import get_async_db
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
    description="List all treatment plans, phases, and attached procedures for a patient.",
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


@router.get(
    "/{patient_id}/clinical-plans/{plan_id}/candidate-work-items",
    response_model=StandardResponse[List[schemas.ClinicalWorkItemSummaryRead]],
    summary="List candidate work items for treatment plan",
    description="Return patient's non-cancelled clinical work items available for attachment to plan phases.",
)
async def list_patient_clinical_plan_candidates(
    patient_id: int,
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = TreatmentPlanService(db, current_user.tenant_id, current_user)
    candidates = await service.get_candidate_work_items(patient_id, plan_id)
    return success_response(
        data=[schemas.ClinicalWorkItemSummaryRead.model_validate(w) for w in candidates],
        message="Candidate work items retrieved successfully",
    )


@router.post(
    "/{patient_id}/clinical-plans/{plan_id}/phases",
    response_model=StandardResponse[schemas.ClinicalTreatmentPlanPhaseRead],
    summary="Add phase to treatment plan",
    description="Add a sequential phase to an existing treatment plan.",
)
async def add_patient_clinical_plan_phase(
    patient_id: int,
    plan_id: int,
    payload: schemas.ClinicalTreatmentPlanPhaseCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    service = TreatmentPlanService(db, current_user.tenant_id, current_user)
    phase = await service.add_phase(patient_id, plan_id, payload)
    return success_response(
        data=schemas.ClinicalTreatmentPlanPhaseRead.model_validate(phase),
        message="Phase added successfully",
    )


@router.post(
    "/{patient_id}/clinical-plans/{plan_id}/phases/{phase_id}/items",
    response_model=StandardResponse[schemas.ClinicalTreatmentPlanItemRead],
    summary="Add work item / procedure to phase",
    description="Attach an existing clinical work item into a treatment plan phase.",
)
async def add_patient_clinical_plan_item(
    patient_id: int,
    plan_id: int,
    phase_id: int,
    payload: schemas.ClinicalTreatmentPlanItemCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    service = TreatmentPlanService(db, current_user.tenant_id, current_user)
    item = await service.add_work_item_to_phase(patient_id, plan_id, phase_id, payload)
    return success_response(
        data=schemas.ClinicalTreatmentPlanItemRead.model_validate(item),
        message="Work item added to phase successfully",
    )


@router.delete(
    "/{patient_id}/clinical-plans/{plan_id}/phases/{phase_id}/items/{item_id}",
    response_model=StandardResponse[None],
    summary="Remove work item from phase",
    description="Unlink a clinical work item from a phase without altering the underlying work item.",
)
async def remove_patient_clinical_plan_item(
    patient_id: int,
    plan_id: int,
    phase_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    service = TreatmentPlanService(db, current_user.tenant_id, current_user)
    await service.remove_work_item_from_phase(patient_id, plan_id, phase_id, item_id)
    return success_response(
        data=None,
        message="Treatment plan item removed successfully",
    )
