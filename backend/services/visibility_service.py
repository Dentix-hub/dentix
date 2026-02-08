"""
Patient Visibility Service (Multi-Doctor Support)

This service determines which patients a user can see based on:
- User role
- Patient visibility mode setting
- Doctor assignments and appointments

SECURITY: This is the ONLY place patient visibility should be determined.
All patient queries MUST use this service.
"""

from sqlalchemy.orm import Session, Query
from sqlalchemy import or_
from typing import List, Optional, Set
from backend.models import User, Patient, Appointment
from backend.core.permissions import PatientVisibilityMode
import logging

logger = logging.getLogger(__name__)


class PatientVisibilityService:
    """
    Central service for patient visibility logic.
    
    SECURITY CRITICAL:
    - Admin sees all patients
    - Doctor sees based on patient_visibility_mode
    - Other roles see all patients (receptionist, nurse, etc.)
    """
    
    def __init__(self, db: Session, user: User, tenant_id: int):
        self.db = db
        self.user = user
        self.tenant_id = tenant_id
        self._visible_ids_cache: Optional[Set[int]] = None
    
    def get_visible_patient_query(self) -> Query:
        """
        Get a filtered query for visible patients.
        
        Returns:
            SQLAlchemy Query filtered to only visible patients
        """
        base_query = self.db.query(Patient).filter(
            Patient.tenant_id == self.tenant_id,
            Patient.is_deleted == False
        )
        
        # Admin sees all
        if self.user.role == "admin":
            return base_query
        
        # Doctor visibility based on mode
        if self.user.role == "doctor":
            return self._get_doctor_filtered_query(base_query)
        
        # Default: all patients (receptionist, nurse, accountant, etc.)
        return base_query
    
    def _get_doctor_filtered_query(self, base_query: Query) -> Query:
        """Filter patients for doctor based on visibility mode."""
        mode = self.user.patient_visibility_mode or "all_assigned"
        
        if mode == PatientVisibilityMode.ALL_ASSIGNED.value:
            # Only assigned patients
            return base_query.filter(
                Patient.assigned_doctor_id == self.user.id
            )
        
        elif mode == PatientVisibilityMode.APPOINTMENTS_ONLY.value:
            # Only patients with appointments
            patient_ids = self._get_appointment_patient_ids()
            return base_query.filter(Patient.id.in_(patient_ids))
        
        elif mode == PatientVisibilityMode.MIXED.value:
            # Both assigned and appointment patients
            appointment_patient_ids = self._get_appointment_patient_ids()
            return base_query.filter(
                or_(
                    Patient.assigned_doctor_id == self.user.id,
                    Patient.id.in_(appointment_patient_ids)
                )
            )
        
        # Fallback: only assigned (safest default)
        return base_query.filter(Patient.assigned_doctor_id == self.user.id)
    
    def _get_appointment_patient_ids(self) -> List[int]:
        """Get patient IDs that have appointments with this doctor."""
        result = self.db.query(Appointment.patient_id).filter(
            Appointment.doctor_id == self.user.id
        ).distinct().all()
        
        return [r[0] for r in result]
    
    def get_visible_patient_ids(self) -> Set[int]:
        """
        Get set of visible patient IDs.
        
        Cached for performance during single request.
        """
        if self._visible_ids_cache is None:
            query = self.get_visible_patient_query()
            self._visible_ids_cache = {p.id for p in query.all()}
        
        return self._visible_ids_cache
    
    def can_view_patient(self, patient_id: int) -> bool:
        """
        Check if user can view a specific patient.
        
        Args:
            patient_id: The patient ID to check
            
        Returns:
            True if user can view this patient
        """
        return patient_id in self.get_visible_patient_ids()
    
    def filter_patients(self, patients: List[Patient]) -> List[Patient]:
        """
        Filter a list of patients to only visible ones.
        
        Args:
            patients: List of patient objects
            
        Returns:
            Filtered list containing only visible patients
        """
        visible_ids = self.get_visible_patient_ids()
        return [p for p in patients if p.id in visible_ids]


def get_visibility_service(
    db: Session,
    user: User,
    tenant_id: int
) -> PatientVisibilityService:
    """Factory function to create visibility service."""
    return PatientVisibilityService(db, user, tenant_id)
