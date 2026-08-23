"""Patients Router — HTTP boundary for patient workflows."""

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, models, schemas
from ..services.invoice_service import InvoiceService
from ..services.patient_service import patient_service
from ..services.patient_search_service import PatientSearchService
from ..services.visibility_service import get_visibility_service
from backend.core.limiter import limiter
from backend.core.permissions import Permission, require_permission
from backend.core.response import CursorPaginatedResponse, StandardResponse, cursor_paginated_response, success_response
from backend.database import get_async_db
from backend.utils.audit_logger import log_admin_action

logger = logging.getLogger("smart_clinic")
router = APIRouter(prefix="/patients", tags=["Patients"])


async def _ensure_patient_visible(db: AsyncSession, current_user: schemas.User, patient_id: int) -> None:
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    if not await visibility.can_view_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")


def _parse_recent_ids(raw_ids: str) -> list[int]:
    if not raw_ids.strip():
        return []
    parsed: list[int] = []
    for raw in raw_ids.split(","):
        token = raw.strip()
        if not token:
            continue
        if not token.isdigit():
            raise HTTPException(status_code=400, detail="Invalid patient IDs")
        patient_id = int(token)
        if patient_id > 0 and patient_id not in parsed:
            parsed.append(patient_id)
        if len(parsed) == 10:
            break
    return parsed


@router.post("", response_model=StandardResponse[schemas.Patient], summary="Create a new patient")
@limiter.limit("10/minute")
async def create_patient(
    request: Request,
    patient: schemas.PatientCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_CREATE)),
):
    try:
        patient_data = patient.model_copy()
        if current_user.role == "doctor" and not patient_data.assigned_doctor_id:
            patient_data.assigned_doctor_id = current_user.id
        created_patient = await patient_service.create_patient(
            db=db, patient_data=patient_data, tenant_id=current_user.tenant_id,
            creator_role=current_user.role,
        )
        return success_response(data=created_patient, message="Patient created successfully")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/directory/recent",
    response_model=StandardResponse[List[schemas.PatientDirectoryItem]],
    summary="Recently viewed patient summaries",
)
async def recent_patient_directory(
    ids: str = Query("", max_length=128),
    q: str = "",
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    service = PatientSearchService(db, current_user.tenant_id, current_user)
    results = await service.get_recent(_parse_recent_ids(ids), q=q)
    return success_response(data=results, message="Recent patients retrieved successfully")


@router.get(
    "/directory",
    response_model=CursorPaginatedResponse[schemas.PatientDirectoryItem],
    summary="Patient directory",
)
async def patient_directory(
    q: str = "",
    cursor: Optional[str] = None,
    limit: int = Query(30, ge=1, le=100),
    scope: Literal["all", "today", "mine"] = "all",
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    service = PatientSearchService(db, current_user.tenant_id, current_user)
    return await service.get_directory(q=q, cursor=cursor, limit=limit, scope=scope)


@router.get("/search", response_model=StandardResponse[List[schemas.Patient]], summary="Search patients")
async def search_patients(
    q: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_SEARCH)),
):
    service = PatientSearchService(db, current_user.tenant_id, current_user)
    results = await service.legacy_search(q=q, limit=50)
    return success_response(data=results, message="Patients retrieved successfully")


@router.get("", response_model=StandardResponse[List[schemas.PatientSummary]], summary="List patients")
async def read_patients(
    skip: int = 0,
    limit: int = 100,
    cursor: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    query = await visibility.get_visible_patient_query()
    if cursor is not None or limit != 100:
        from backend.core.pagination import CursorParams, apply_cursor_pagination, build_cursor_response
        cursor_params = CursorParams(cursor=cursor, limit=limit if limit != 100 else 20)
        paginated_query = apply_cursor_pagination(query, models.Patient, cursor_params, descending=True)
        result = await db.execute(paginated_query)
        items, next_cursor, has_more = build_cursor_response(result.scalars().all(), cursor_params.limit)
        return cursor_paginated_response(
            data=items, limit=cursor_params.limit, next_cursor=next_cursor,
            has_more=has_more, message="Patients retrieved successfully",
        )
    result = await db.execute(query.order_by(models.Patient.id.desc()).offset(skip).limit(limit))
    return success_response(data=result.scalars().all(), message="Patients retrieved successfully")


@router.get("/{patient_id}", response_model=StandardResponse[schemas.Patient], summary="Get patient details")
async def read_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    await _ensure_patient_visible(db, current_user, patient_id)
    db_patient = await patient_service.get_patient(db, patient_id)
    if not db_patient or db_patient.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    return success_response(data=db_patient, message="Patient retrieved successfully")


@router.put("/{patient_id}", response_model=StandardResponse[schemas.Patient], summary="Update patient")
async def update_patient(
    patient_id: int,
    patient: schemas.PatientUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_UPDATE)),
):
    await _ensure_patient_visible(db, current_user, patient_id)
    try:
        updated_patient = await patient_service.update_patient(
            db=db, patient_id=patient_id, updates=patient,
            tenant_id=current_user.tenant_id, updater_role=current_user.role,
        )
        return success_response(data=updated_patient, message="Patient updated successfully")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{patient_id}", response_model=StandardResponse[schemas.Patient], summary="Soft-delete patient")
async def delete_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_DELETE)),
):
    await _ensure_patient_visible(db, current_user, patient_id)
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient_name = patient.name
    result = await crud.delete_patient(db, patient_id, tenant_id=current_user.tenant_id)
    log_admin_action(
        db=db, admin_user=current_user, action="archive", entity_type="patient",
        entity_id=patient_id, details=f"Archived patient {patient_name}",
    )
    return success_response(data=result, message="Patient archived successfully")


@router.delete("/{patient_id}/permanent", response_model=StandardResponse[schemas.Patient], summary="Hard-delete patient")
async def delete_patient_permanently(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    result = await db.execute(
        select(models.Patient).where(
            models.Patient.id == patient_id,
            models.Patient.tenant_id == current_user.tenant_id,
        )
    )
    patient = result.scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient_name = patient.name
    res = await crud.delete_patient_permanently(db, patient_id, tenant_id=current_user.tenant_id)
    log_admin_action(
        db=db, admin_user=current_user, action="hard_delete", entity_type="patient",
        entity_id=patient_id, details=f"PERMANENTLY deleted patient {patient_name} and all data",
    )
    return success_response(data=res, message="Patient hard-deleted successfully")


@router.get("/{patient_id}/tooth_status", response_model=StandardResponse[List[schemas.ToothStatus]])
async def get_patient_tooth_status(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    await _ensure_patient_visible(db, current_user, patient_id)
    data = await crud.get_tooth_status(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Tooth status retrieved")


@router.get("/{patient_id}/treatments", response_model=StandardResponse[List[schemas.Treatment]])
async def get_patient_treatments(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    await _ensure_patient_visible(db, current_user, patient_id)
    data = await crud.get_treatments(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Treatments retrieved")


@router.get("/{patient_id}/payments", response_model=StandardResponse[List[schemas.Payment]])
async def get_patient_payments(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.RECEIVABLE_READ)),
):
    await _ensure_patient_visible(db, current_user, patient_id)
    data = await crud.get_payments(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Payments retrieved")


@router.get(
    "/{patient_id}/invoice",
    response_model=StandardResponse[schemas.PatientInvoice],
    summary="Authoritative printable invoice (server-computed)",
)
async def get_patient_invoice(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    await _ensure_patient_visible(db, current_user, patient_id)
    service = InvoiceService(db, current_user.tenant_id)
    invoice = await service.get_patient_invoice(patient_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return success_response(data=invoice, message="Invoice retrieved successfully")


@router.get("/{patient_id}/attachments", response_model=StandardResponse[List[schemas.Attachment]])
async def get_patient_attachments(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    await _ensure_patient_visible(db, current_user, patient_id)
    data = await crud.get_patient_attachments(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Attachments retrieved")


@router.get("/{patient_id}/prescriptions", response_model=StandardResponse[List[schemas.Prescription]])
async def get_patient_prescriptions(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    await _ensure_patient_visible(db, current_user, patient_id)
    data = await crud.get_prescriptions(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Prescriptions retrieved")
