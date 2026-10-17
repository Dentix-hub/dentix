"""
Clinical Commands Router (Slice S04).
HTTP boundary for native ClinicalWorkItem and ClinicalEvent commands and queries.
"""

from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.database import get_async_db
from backend.services.clinical_command_service import ClinicalCommandService

router = APIRouter(prefix="/patients", tags=["Clinical Commands"])


@router.post(
    "/{patient_id}/clinical-work-items",
    response_model=StandardResponse[schemas.ClinicalWorkItemRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create clinical work item",
    description="Create a native clinical work item (finding or procedure) and append a recorded event.",
)
async def create_patient_clinical_work_item(
    patient_id: int,
    payload: schemas.ClinicalWorkItemCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(
        require_permission(Permission.CLINICAL_WRITE, Permission.TREATMENT_PLAN_WRITE)
    ),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    work_item = await service.create_work_item(patient_id, payload)
    return success_response(
        data=schemas.ClinicalWorkItemRead.model_validate(work_item),
        message="Clinical work item created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/{patient_id}/clinical-work-items",
    response_model=StandardResponse[List[schemas.ClinicalWorkItemRead]],
    summary="List patient clinical work items",
    description="List active clinical work items for a patient. Excludes corrected items by default.",
)
async def list_patient_clinical_work_items(
    patient_id: int,
    include_corrected: bool = Query(default=False),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    items = await service.list_work_items(patient_id, include_corrected=include_corrected)
    return success_response(
        data=[schemas.ClinicalWorkItemRead.model_validate(item) for item in items],
    )


@router.patch(
    "/{patient_id}/clinical-work-items/{work_item_id}",
    response_model=StandardResponse[schemas.ClinicalWorkItemRead],
    summary="Update clinical work item",
    description="Update lifecycle status, notes, or targets of an existing clinical work item.",
)
async def update_patient_clinical_work_item(
    patient_id: int,
    work_item_id: int,
    payload: schemas.ClinicalWorkItemUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(
        require_permission(Permission.CLINICAL_WRITE, Permission.TREATMENT_PLAN_WRITE)
    ),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    work_item = await service.update_work_item(patient_id, work_item_id, payload)
    return success_response(
        data=schemas.ClinicalWorkItemRead.model_validate(work_item),
        message="Clinical work item updated successfully",
    )


@router.post(
    "/{patient_id}/clinical-findings",
    response_model=StandardResponse[schemas.ClinicalWorkItemRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create clinical finding",
    description="Create a dedicated clinical finding on one or more teeth/surfaces.",
)
async def create_patient_clinical_finding(
    patient_id: int,
    payload: schemas.ClinicalFindingCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    work_item = await service.create_finding(patient_id, payload)
    return success_response(
        data=schemas.ClinicalWorkItemRead.model_validate(work_item),
        message="Clinical finding created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/{patient_id}/clinical-findings/bulk",
    response_model=StandardResponse[schemas.ClinicalBulkWorkItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create clinical findings",
    description="Atomic multi-tooth bulk creation of clinical findings (1 to 50 items).",
)
async def create_patient_clinical_findings_bulk(
    patient_id: int,
    payload: schemas.ClinicalFindingBulkCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    result = await service.create_findings_bulk(patient_id, payload)
    return success_response(
        data=result,
        message=f"{result.count} clinical findings created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/{patient_id}/clinical-procedures",
    response_model=StandardResponse[schemas.ClinicalWorkItemRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create clinical procedure",
    description="Create a dedicated clinical procedure on one or more teeth/surfaces.",
)
async def create_patient_clinical_procedure(
    patient_id: int,
    payload: schemas.ClinicalProcedureCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    work_item = await service.create_procedure(patient_id, payload)
    return success_response(
        data=schemas.ClinicalWorkItemRead.model_validate(work_item),
        message="Clinical procedure created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/{patient_id}/clinical-procedures/bulk",
    response_model=StandardResponse[schemas.ClinicalBulkWorkItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create clinical procedures",
    description="Atomic multi-tooth bulk creation of clinical procedures (1 to 50 items).",
)
async def create_patient_clinical_procedures_bulk(
    patient_id: int,
    payload: schemas.ClinicalProcedureBulkCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    result = await service.create_procedures_bulk(patient_id, payload)
    return success_response(
        data=result,
        message=f"{result.count} clinical procedures created successfully",
        status_code=status.HTTP_201_CREATED,
    )

