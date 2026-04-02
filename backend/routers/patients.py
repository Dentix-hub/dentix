"""
Patients Router
Handles patient CRUD operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, crud
from .auth import get_current_user, get_db
from backend.core.permissions import Permission, require_permission
from backend.core.limiter import limiter

# Import new async dependency
# Multi-Doctor Visibility
from ..services.visibility_service import get_visibility_service

router = APIRouter(prefix="/patients", tags=["Patients"])


from ..services.patient_service import patient_service


@router.post(
    "/",
    response_model=schemas.Patient,
    summary="Create a new patient",
    description="Register a new patient into the current tenant. Requires authentication.",
)
@limiter.limit("10/minute")
def create_patient(
    request: Request,
    patient: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
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

        return patient_service.create_patient(
            db=db,
            patient_data=patient_data,
            tenant_id=current_user.tenant_id,
            creator_role=current_user.role,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search", response_model=List[schemas.Patient])
def search_patients(
    q: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Search patients by name or phone (filtered by visibility)."""
    # Get visibility-filtered patients
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    visible_query = visibility.get_visible_patient_query()

    # Apply search filter
    results = (
        visible_query.filter(
            models.Patient.name.ilike(f"%{q}%") | models.Patient.phone.ilike(f"%{q}%")
        )
        .limit(50)
        .all()
    )

    return results


@router.get("/", response_model=List[schemas.PatientSummary])
def read_patients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get patients for current user (filtered by visibility)."""
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    return (
        visibility.get_visible_patient_query()
        .order_by(models.Patient.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{patient_id}", response_model=schemas.Patient)
def read_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get a specific patient by ID (with visibility check)."""
    # Check visibility permission
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    if not visibility.can_view_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")

    db_patient = patient_service.get_patient(db, patient_id)
    if not db_patient or db_patient.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient


@router.put("/{patient_id}", response_model=schemas.Patient)
def update_patient(
    patient_id: int,
    patient: schemas.PatientUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Update a patient's information (Gov-Enforced)."""
    try:
        return patient_service.update_patient(
            db=db,
            patient_id=patient_id,
            updates=patient,
            tenant_id=current_user.tenant_id,
            updater_role=current_user.role,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        # e.g. Patient not found
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{patient_id}", response_model=schemas.Patient)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_DELETE)),
):
    """Delete a patient."""
    from ..utils.audit_logger import log_admin_action

    # 1. Get Patient for logging (before delete)
    patient = crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_name = patient.name

    # 2. Delete
    result = crud.delete_patient(db, patient_id, tenant_id=current_user.tenant_id)

    # 3. Log Action
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="patient",
        entity_id=patient_id,
        details=f"Deleted user {patient_name}",
    )

    return result


@router.delete("/{patient_id}/permanent", response_model=schemas.Patient)
def delete_patient_permanently(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Hard Delete a patient and all related data (Cascading).
    WARNING: This action is irreversible.
    """
    from ..utils.audit_logger import log_admin_action

    # Check permissions (Only Admin/SuperAdmin)
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403, detail="Only Admins can perform permanent deletion."
        )

    # 1. Get Patient for logging (before delete)
    # We use a custom query because get_patient might filter out soft-deleted ones
    patient = (
        db.query(models.Patient)
        .filter(
            models.Patient.id == patient_id,
            models.Patient.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_name = patient.name

    # 2. Delete
    result = crud.delete_patient_permanently(
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

    return result


# --- Patient Sub-Resources ---
@router.get("/{patient_id}/tooth_status", response_model=List[schemas.ToothStatus])
def get_patient_tooth_status(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get dental chart for a patient."""
    patient = crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.get_tooth_status(db, patient_id, current_user.tenant_id)


@router.get("/{patient_id}/treatments", response_model=List[schemas.Treatment])
def get_patient_treatments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all treatments for a patient."""
    patient = crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.get_treatments(db, patient_id, current_user.tenant_id)


@router.get("/{patient_id}/payments", response_model=List[schemas.Payment])
def get_patient_payments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all payments for a patient."""
    patient = crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.get_payments(db, patient_id, current_user.tenant_id)


@router.get("/{patient_id}/attachments", response_model=List[schemas.Attachment])
def get_patient_attachments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all attachments for a patient."""
    patient = crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.get_patient_attachments(db, patient_id, current_user.tenant_id)


@router.get("/{patient_id}/prescriptions", response_model=List[schemas.Prescription])
def get_patient_prescriptions(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all prescriptions for a patient."""
    patient = crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return crud.get_prescriptions(db, patient_id, current_user.tenant_id)
