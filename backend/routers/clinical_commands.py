"""
Clinical Commands Router (Slice S04).
HTTP boundary for native ClinicalWorkItem and ClinicalEvent commands and queries.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Query, status
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(
        require_permission(Permission.CLINICAL_WRITE, Permission.TREATMENT_PLAN_WRITE)
    ),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    work_item = await service.create_work_item(patient_id, payload, idempotency_key=idempotency_key)
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    work_item = await service.create_finding(patient_id, payload, idempotency_key=idempotency_key)
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_WRITE)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    result = await service.create_findings_bulk(patient_id, payload, idempotency_key=idempotency_key)
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    work_item = await service.create_procedure(patient_id, payload, idempotency_key=idempotency_key)
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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.TREATMENT_PLAN_WRITE)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    result = await service.create_procedures_bulk(patient_id, payload, idempotency_key=idempotency_key)
    return success_response(
        data=result,
        message=f"{result.count} clinical procedures created successfully",
        status_code=status.HTTP_201_CREATED,
    )


# ---------------------------------------------------------------------------
# Slice S06: Correction, Tooth Detail & History Endpoints (G7-M08, G7-M10, G7-M11)
# ---------------------------------------------------------------------------


@router.post(
    "/{patient_id}/clinical-work-items/{work_item_id}/correct",
    response_model=StandardResponse[schemas.ClinicalWorkItemCorrectionResponse],
    summary="Correct clinical work item",
    description="Correct a clinical work item via entered_in_error or supersede mode. Clinical only.",
)
async def correct_patient_clinical_work_item(
    patient_id: int,
    work_item_id: int,
    payload: schemas.ClinicalWorkItemCorrectionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(
        require_permission(Permission.TREATMENT_PLAN_WRITE)
    ),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    result = await service.correct_work_item(
        patient_id, work_item_id, payload, idempotency_key=idempotency_key
    )
    return success_response(
        data=result,
        message=f"Clinical work item corrected successfully ({payload.mode})",
    )


@router.get(
    "/{patient_id}/clinical-teeth/{tooth_key}",
    response_model=StandardResponse[schemas.ClinicalToothDetailRead],
    summary="Get clinical tooth detail",
    description="Get tooth summary, work items, events, and legacy treatments for a single tooth.",
)
async def get_patient_clinical_tooth_detail(
    patient_id: int,
    tooth_key: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    result = await service.get_tooth_detail(patient_id, tooth_key)
    return success_response(data=result)


@router.get(
    "/{patient_id}/clinical-events",
    response_model=StandardResponse[List[schemas.ClinicalEventRead]],
    summary="List patient clinical events",
    description="List raw clinical event audit log for a patient. Excludes corrected items by default.",
)
async def list_patient_clinical_events(
    patient_id: int,
    include_entered_in_error: bool = Query(default=False),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    service = ClinicalCommandService(db, current_user.tenant_id, current_user)
    items = await service.list_patient_events(
        patient_id, include_entered_in_error=include_entered_in_error
    )
    return success_response(data=items)

