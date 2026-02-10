"""
Async Patients Router (v2)
Handles patient CRUD operations using async database operations.

This is the async version of patients.py for gradual migration.
Mount under /v2/patients or replace original once tested.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas
from ..crud import patient_async as crud
from ..database import get_async_db
from .auth import get_current_user

router = APIRouter(prefix="/patients", tags=["Patients (Async)"])


@router.post("/", response_model=schemas.Patient)
async def create_patient(
    patient: schemas.PatientCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Create a new patient."""
    return await crud.create_patient(
        db=db, patient=patient, tenant_id=current_user.tenant_id
    )


@router.get("/search", response_model=List[schemas.Patient])
async def search_patients(
    q: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Search patients by name or phone."""
    return await crud.search_patients(db, query=q, tenant_id=current_user.tenant_id)


@router.get("/", response_model=List[schemas.Patient])
async def read_patients(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all patients for current tenant."""
    return await crud.get_patients(db, current_user.tenant_id, skip=skip, limit=limit)


@router.get("/{patient_id}", response_model=schemas.Patient)
async def read_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get a specific patient by ID."""
    db_patient = await crud.get_patient(
        db, patient_id=patient_id, tenant_id=current_user.tenant_id
    )
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient


@router.put("/{patient_id}", response_model=schemas.Patient)
async def update_patient(
    patient_id: int,
    patient: schemas.PatientCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Update a patient's information."""
    result = await crud.update_patient(
        db, patient_id, patient, tenant_id=current_user.tenant_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return result


@router.delete("/{patient_id}", response_model=schemas.Patient)
async def delete_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Delete a patient."""
    result = await crud.delete_patient(db, patient_id, tenant_id=current_user.tenant_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return result


# --- Patient Sub-Resources ---
@router.get("/{patient_id}/tooth_status", response_model=List[schemas.ToothStatus])
async def get_patient_tooth_status(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get dental chart for a patient."""
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return await crud.get_tooth_status(db, patient_id, current_user.tenant_id)


@router.get("/{patient_id}/attachments", response_model=List[schemas.Attachment])
async def get_patient_attachments(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all attachments for a patient."""
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return await crud.get_patient_attachments(db, patient_id, current_user.tenant_id)


@router.get("/{patient_id}/prescriptions", response_model=List[schemas.Prescription])
async def get_patient_prescriptions(
    patient_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all prescriptions for a patient."""
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return await crud.get_prescriptions(db, patient_id, current_user.tenant_id)
