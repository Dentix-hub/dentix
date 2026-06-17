"""
Patients Router
Handles patient CRUD operations.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from .. import models, schemas, crud
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.core.limiter import limiter
from backend.utils.audit_logger import log_admin_action
from ..services.visibility_service import get_visibility_service
from ..services.patient_service import patient_service
from backend.core.response import StandardResponse, success_response

logger = logging.getLogger("smart_clinic")

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post(
    "",
    response_model=StandardResponse[schemas.Patient],
    summary="Create a new patient",
    description="Register a new patient into the current tenant. Requires authentication.",
)
@limiter.limit("10/minute")
async def create_patient(
    request: Request,
    patient: schemas.PatientCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_CREATE)),
):
    """Create a new patient (Gov-Enforced)."""
    try:
        # Assign doctor_id if not provided and user is doctor
        patient_data = (
            patient.model_copy() if hasattr(patient, "model_copy") else patient
        )
        if current_user.role == "doctor" and not getattr(
            patient_data, "assigned_doctor_id", None
        ):
            patient_data.assigned_doctor_id = current_user.id

        created_patient = await patient_service.create_patient(
            db=db,
            patient_data=patient_data,
            tenant_id=current_user.tenant_id,
            creator_role=current_user.role,
        )
        return success_response(
            data=created_patient,
            message="Patient created successfully"
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/search",
    response_model=StandardResponse[List[schemas.Patient]],
    summary="Search patients",
    description="Search patients by name or phone number. Results filtered by doctor visibility.",
)
async def search_patients(
    q: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_SEARCH)),
):
    """Search patients by name or phone (filtered by visibility)."""
    # Get visibility-filtered patients
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    visible_query = await visibility.get_visible_patient_query()

    # Apply search filter
    stmt = (
        visible_query.where(
            models.Patient.name.ilike(f"%{q}%") | models.Patient.phone.ilike(f"%{q}%")
        )
        .limit(50)
    )
    result = await db.execute(stmt)
    results = result.scalars().all()

    return success_response(data=results, message="Patients retrieved successfully")


@router.get(
    "",
    response_model=StandardResponse[List[schemas.PatientSummary]],
    summary="List patients",
    description="Get all patients visible to the current user. Doctors see only their assigned patients.",
)
async def read_patients(
    skip: int = 0,
    limit: int = 100,
    cursor: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    """Get patients for current user (filtered by visibility)."""
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    query = await visibility.get_visible_patient_query()

    if cursor is not None or limit != 100:
        # Use cursor pagination if explicitly requested or custom limit
        from backend.core.pagination import CursorParams, apply_cursor_pagination, build_cursor_response
        from backend.core.response import cursor_paginated_response

        # If cursor is given or they want cursor pagination style
        cursor_params = CursorParams(cursor=cursor, limit=limit if limit != 100 else 20)
        paginated_query = apply_cursor_pagination(query, models.Patient, cursor_params, descending=True)
        result = await db.execute(paginated_query)
        results = result.scalars().all()

        items, next_cursor, has_more = build_cursor_response(results, cursor_params.limit)
        return cursor_paginated_response(
            data=items,
            limit=cursor_params.limit,
            next_cursor=next_cursor,
            has_more=has_more,
            message="Patients retrieved successfully"
        )
    else:
        stmt = (
            query
            .order_by(models.Patient.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        results = result.scalars().all()
        return success_response(data=results, message="Patients retrieved successfully")


@router.get(
    "/{patient_id}",
    response_model=StandardResponse[schemas.Patient],
    summary="Get patient details",
    description="Get a specific patient by ID. Subject to visibility restrictions.",
)
async def read_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    """Get a specific patient by ID (with visibility check)."""
    # Check visibility permission
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    if not await visibility.can_view_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")

    db_patient = await patient_service.get_patient(db, patient_id)
    if not db_patient or db_patient.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    return success_response(data=db_patient, message="Patient retrieved successfully")


@router.put(
    "/{patient_id}",
    response_model=StandardResponse[schemas.Patient],
    summary="Update patient",
    description="Update patient information. Requires PATIENT_UPDATE permission.",
)
async def update_patient(
    patient_id: int,
    patient: schemas.PatientUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_UPDATE)),
):
    """Update a patient's information (Gov-Enforced)."""
    try:
        updated_patient = await patient_service.update_patient(
            db=db,
            patient_id=patient_id,
            updates=patient,
            tenant_id=current_user.tenant_id,
            updater_role=current_user.role,
        )
        return success_response(
            data=updated_patient,
            message="Patient updated successfully"
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        # e.g. Patient not found
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{patient_id}",
    response_model=StandardResponse[schemas.Patient],
    summary="Soft-delete patient",
    description="Soft-delete a patient record. Data is preserved but marked as deleted.",
)
async def delete_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_DELETE)),
):
    """Delete a patient."""
    # 1. Get Patient for logging (before delete)
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_name = patient.name

    # 2. Delete
    result = await crud.delete_patient(db, patient_id, tenant_id=current_user.tenant_id)

    # 3. Log Action
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="patient",
        entity_id=patient_id,
        details=f"Deleted user {patient_name}",
    )

    return success_response(data=result, message="Patient deleted successfully")


@router.delete(
    "/{patient_id}/permanent",
    response_model=StandardResponse[schemas.Patient],
    summary="Hard-delete patient",
    description="Permanently delete a patient and ALL related data. Irreversible. Requires SYSTEM_CONFIG permission.",
)
async def delete_patient_permanently(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Hard Delete a patient and all related data (Cascading).
    WARNING: This action is irreversible.
    """
    # 1. Get Patient for logging (before delete)
    # We use a custom query because get_patient might filter out soft-deleted ones
    stmt = (
        select(models.Patient)
        .where(
            models.Patient.id == patient_id,
            models.Patient.tenant_id == current_user.tenant_id,
        )
    )
    result = await db.execute(stmt)
    patient = result.scalars().first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_name = patient.name

    # 2. Delete
    res = await crud.delete_patient_permanently(
        db, patient_id, tenant_id=current_user.tenant_id
    )

    # 3. Log Action
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="hard_delete",
        entity_type="patient",
        entity_id=patient_id,
        details=f"PERMANENTLY deleted user {patient_name} and all data",
    )

    return success_response(data=res, message="Patient hard-deleted successfully")


# --- Patient Sub-Resources ---
@router.get("/{patient_id}/tooth_status", response_model=StandardResponse[List[schemas.ToothStatus]])
async def get_patient_tooth_status(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get dental chart for a patient."""
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    data = await crud.get_tooth_status(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Tooth status retrieved")


@router.get("/{patient_id}/treatments", response_model=StandardResponse[List[schemas.Treatment]])
async def get_patient_treatments(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get all treatments for a patient."""
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    data = await crud.get_treatments(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Treatments retrieved")


@router.get("/{patient_id}/payments", response_model=StandardResponse[List[schemas.Payment]])
async def get_patient_payments(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get all payments for a patient."""
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    data = await crud.get_payments(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Payments retrieved")


@router.get("/{patient_id}/attachments", response_model=StandardResponse[List[schemas.Attachment]])
async def get_patient_attachments(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_READ)),
):
    """Get all attachments for a patient."""
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    data = await crud.get_patient_attachments(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Attachments retrieved")


@router.get("/{patient_id}/prescriptions", response_model=StandardResponse[List[schemas.Prescription]])
async def get_patient_prescriptions(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.CLINICAL_READ)),
):
    """Get all prescriptions for a patient."""
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    data = await crud.get_prescriptions(db, patient_id, current_user.tenant_id)
    return success_response(data=data, message="Prescriptions retrieved")
