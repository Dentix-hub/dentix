
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta, date, time
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException
import logging

from backend import models, schemas
from backend.services.patient_service import PatientService
from backend.core.permissions import has_permission, Permission

logger = logging.getLogger(__name__)

class AppointmentService:
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # ---------------------------------------------------------
    # 1. Standard CRUD (Refactored from crud/appointment.py)
    # ---------------------------------------------------------

    def get_appointments(self, skip: int = 0, limit: int = 100, 
                        date_filter: Optional[date] = None,
                        user_role: Optional[str] = None) -> List[models.Appointment]:
        """Get appointments with optional date filtering."""
        
        # Rule 7: Strict Logic Separation (Service Layer)
        # Permissions should be checked by caller or via RBAC Middleware, 
        # but specialized data access rules (e.g. Doctor sees only own?) go here if needed.
        
        query = (
            self.db.query(models.Appointment)
            .join(models.Patient)
            .filter(models.Patient.tenant_id == self.tenant_id)
            .options(joinedload(models.Appointment.patient))
        )
        
        if date_filter:
            start_of_day = datetime.combine(date_filter, time.min)
            end_of_day = datetime.combine(date_filter, time.max)
            query = query.filter(models.Appointment.date_time >= start_of_day, 
                                 models.Appointment.date_time <= end_of_day)

        return query.order_by(models.Appointment.date_time.desc()).offset(skip).limit(limit).all()

    def create_appointment(self, data: schemas.AppointmentCreate, creator_role: str) -> models.Appointment:
        """Create new appointment with validation."""
        
        # 1. RBAC Check
        if not has_permission(creator_role, Permission.APPOINTMENT_CREATE):
            raise ConnectionError(f"Role {creator_role} cannot create appointments.") # Using ConnectionError for Permission? No, ValueError or generic

        # 2. Validate Patient Belongs to Tenant
        # Delegate to PatientService or just quick check
        patient = (self.db.query(models.Patient)
                   .filter(models.Patient.id == data.patient_id, 
                           models.Patient.tenant_id == self.tenant_id)
                   .first())
                   
        if not patient:
            raise ValueError("Patient not found.")

        # 3. Conflict Check (Basic) - Could use find_available_slots logic
        # For simple manual creation, we might skip deep checks or enforce them.
        # Let's enforce basic overlap check.
        conflict = self.check_conflict(data.date_time)
        if conflict:
             raise ValueError(f"Appointment slot {data.date_time} is busy.")

        db_appointment = models.Appointment(
            patient_id=data.patient_id,
            date_time=data.date_time,
            status=data.status or "Scheduled",
            notes=data.notes
        )
        self.db.add(db_appointment)
        self.db.commit()
        self.db.refresh(db_appointment)
        return db_appointment

    def update_status(self, appointment_id: int, status: str, user_role: str) -> models.Appointment:
        """Update appointment status."""
        appt = self._get_by_id(appointment_id)
        if not appt:
            raise ValueError("Appointment not found")
            
        appt.status = status
        self.db.commit()
        self.db.refresh(appt)
        return appt

    def delete_appointment(self, appointment_id: int, user_role: str):
        if not has_permission(user_role, Permission.APPOINTMENT_DELETE):
            raise PermissionError("Ah ah ah! You didn't say the magic word.")

        appt = self._get_by_id(appointment_id)
        if appt:
            self.db.delete(appt)
            self.db.commit()

    # ---------------------------------------------------------
    # 2. Smart Logic (Ported from AI Handler)
    # ---------------------------------------------------------

    def check_conflict(self, requested_time: datetime) -> bool:
        """Check if a slot is occupied."""
        # Simple overlap check: Exact match for now. 
        # In future: duration based.
        return self.db.query(models.Appointment).join(models.Patient).filter(
            models.Patient.tenant_id == self.tenant_id,
            models.Appointment.date_time == requested_time,
            models.Appointment.status != "Cancelled"
        ).first() is not None

    def find_available_slots(self, target_date: date, period: str = "any") -> List[str]:
        """Core slot finding logic."""
        # Get existing
        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)
        
        existing = (self.db.query(models.Appointment)
                    .join(models.Patient)
                    .filter(models.Patient.tenant_id == self.tenant_id,
                            models.Appointment.date_time >= start_of_day,
                            models.Appointment.date_time <= end_of_day,
                            models.Appointment.status != "Cancelled")
                    .all())

        busy_times = {a.date_time.strftime("%H:%M") for a in existing}
        
        # Generate slots
        start_hour, end_hour = 9, 21
        if period == "morning": start_hour, end_hour = 9, 12
        elif period == "afternoon": start_hour, end_hour = 12, 17
        elif period == "evening": start_hour, end_hour = 17, 21
        
        slots = []
        for hour in range(start_hour, end_hour):
            for minute in [0, 30]:
                slot_time = f"{hour:02d}:{minute:02d}"
                if slot_time not in busy_times:
                    slots.append(slot_time)
        return slots

    def _get_by_id(self, appointment_id: int) -> Optional[models.Appointment]:
        return (self.db.query(models.Appointment)
                .join(models.Patient)
                .filter(models.Appointment.id == appointment_id,
                        models.Patient.tenant_id == self.tenant_id)
                .first())
