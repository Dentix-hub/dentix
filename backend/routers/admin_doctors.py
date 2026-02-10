"""
Doctor Settings Router (Admin Only)

Allows admin to manage doctor visibility settings.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..models import User
from .auth import get_current_user, get_db
from ..core.permissions import PatientVisibilityMode

router = APIRouter(prefix="/admin/doctors", tags=["Admin - Doctors"])


class DoctorVisibilityUpdate(BaseModel):
    """Schema for updating doctor visibility settings."""

    patient_visibility_mode: Optional[str] = None
    can_view_other_doctors_history: Optional[bool] = None


class DoctorVisibilityResponse(BaseModel):
    """Response schema for doctor visibility."""

    doctor_id: int
    doctor_name: str
    patient_visibility_mode: str
    can_view_other_doctors_history: bool

    class Config:
        from_attributes = True


@router.get("/visibility")
def get_all_doctors_visibility(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get visibility settings for all doctors (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    doctors = (
        db.query(User)
        .filter(
            User.tenant_id == current_user.tenant_id,
            User.role == "doctor",
            User.is_active == True,
        )
        .all()
    )

    return [
        {
            "doctor_id": d.id,
            "doctor_name": d.full_name or d.username,
            "patient_visibility_mode": d.patient_visibility_mode or "all_assigned",
            "can_view_other_doctors_history": d.can_view_other_doctors_history or False,
        }
        for d in doctors
    ]


@router.put("/visibility/{doctor_id}")
def update_doctor_visibility(
    doctor_id: int,
    settings: DoctorVisibilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update visibility settings for a doctor (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Find doctor
    doctor = (
        db.query(User)
        .filter(
            User.id == doctor_id,
            User.tenant_id == current_user.tenant_id,
            User.role == "doctor",
        )
        .first()
    )

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Validate visibility mode
    if settings.patient_visibility_mode:
        valid_modes = [m.value for m in PatientVisibilityMode]
        if settings.patient_visibility_mode not in valid_modes:
            raise HTTPException(
                status_code=400, detail=f"Invalid mode. Valid: {valid_modes}"
            )
        doctor.patient_visibility_mode = settings.patient_visibility_mode

    if settings.can_view_other_doctors_history is not None:
        doctor.can_view_other_doctors_history = settings.can_view_other_doctors_history

    db.commit()
    db.refresh(doctor)

    return {
        "doctor_id": doctor.id,
        "doctor_name": doctor.full_name or doctor.username,
        "patient_visibility_mode": doctor.patient_visibility_mode,
        "can_view_other_doctors_history": doctor.can_view_other_doctors_history,
        "message": "Settings updated successfully",
    }


@router.get("/visibility-modes")
def get_visibility_modes(
    current_user: User = Depends(get_current_user),
):
    """Get available visibility modes."""
    return {
        "modes": [
            {
                "value": PatientVisibilityMode.ALL_ASSIGNED.value,
                "label": "Assigned Patients Only",
                "description": "Doctor sees only patients assigned to them",
            },
            {
                "value": PatientVisibilityMode.APPOINTMENTS_ONLY.value,
                "label": "Appointments Only",
                "description": "Doctor sees only patients with appointments",
            },
            {
                "value": PatientVisibilityMode.MIXED.value,
                "label": "Mixed (Assigned + Appointments)",
                "description": "Doctor sees both assigned patients and appointment patients",
            },
        ]
    }
