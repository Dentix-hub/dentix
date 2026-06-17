from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select
from datetime import datetime, date, time
from typing import List, Optional
import logging

from backend import models, schemas
from backend.core.permissions import has_permission, Permission

logger = logging.getLogger(__name__)


class AppointmentService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # ---------------------------------------------------------
    # 1. Standard CRUD (Refactored from crud/appointment.py)
    # ---------------------------------------------------------

    async def get_appointments(
        self,
        skip: int = 0,
        limit: int = 100,
        date_filter: Optional[date] = None,
        user_role: Optional[str] = None,
    ) -> List[models.Appointment]:
        """Get appointments with optional date filtering."""

        stmt = (
            select(models.Appointment)
            .join(models.Patient)
            .where(models.Patient.tenant_id == self.tenant_id)
            .options(joinedload(models.Appointment.patient))
        )

        if date_filter:
            start_of_day = datetime.combine(date_filter, time.min)
            end_of_day = datetime.combine(date_filter, time.max)
            stmt = stmt.where(
                models.Appointment.date_time >= start_of_day,
                models.Appointment.date_time <= end_of_day,
            )

        stmt = stmt.order_by(models.Appointment.date_time.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_appointment(
        self, data: schemas.AppointmentCreate, creator_role: str
    ) -> models.Appointment:
        """Create new appointment with validation."""

        # 1. RBAC Check
        if not has_permission(creator_role, Permission.APPOINTMENT_CREATE):
            raise ConnectionError(
                f"Role {creator_role} cannot create appointments."
            )

        # 2. Validate Patient Belongs to Tenant
        stmt_patient = select(models.Patient).where(
            models.Patient.id == data.patient_id,
            models.Patient.tenant_id == self.tenant_id,
        )
        res_patient = await self.db.execute(stmt_patient)
        patient = res_patient.scalars().first()

        if not patient:
            raise ValueError("Patient not found.")

        # 3. Conflict Check (Basic)
        conflict = await self.check_conflict(data.date_time)
        if conflict:
            raise ValueError(f"Appointment slot {data.date_time} is busy.")

        db_appointment = models.Appointment(
            patient_id=data.patient_id,
            date_time=data.date_time,
            status=data.status or "Scheduled",
            notes=data.notes,
        )
        self.db.add(db_appointment)
        await self.db.commit()
        await self.db.refresh(db_appointment)
        return db_appointment

    async def update_status(
        self, appointment_id: int, status: str, user_role: str
    ) -> models.Appointment:
        """Update appointment status."""
        appt = await self._get_by_id(appointment_id)
        if not appt:
            raise ValueError("Appointment not found")

        appt.status = status
        await self.db.commit()
        await self.db.refresh(appt)
        return appt

    async def delete_appointment(self, appointment_id: int, user_role: str):
        if not has_permission(user_role, Permission.APPOINTMENT_DELETE):
            raise PermissionError("Ah ah ah! You didn't say the magic word.")

        appt = await self._get_by_id(appointment_id)
        if appt:
            await self.db.delete(appt)
            await self.db.commit()

    # ---------------------------------------------------------
    # 2. Smart Logic (Ported from AI Handler)
    # ---------------------------------------------------------

    async def check_conflict(self, requested_time: datetime) -> bool:
        """Check if a slot is occupied."""
        stmt = (
            select(models.Appointment)
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Appointment.date_time == requested_time,
                models.Appointment.status != "Cancelled",
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def find_available_slots(self, target_date: date, period: str = "any") -> List[str]:
        """Core slot finding logic."""
        # Get existing
        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)

        stmt = (
            select(models.Appointment)
            .join(models.Patient)
            .where(
                models.Patient.tenant_id == self.tenant_id,
                models.Appointment.date_time >= start_of_day,
                models.Appointment.date_time <= end_of_day,
                models.Appointment.status != "Cancelled",
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().all()

        busy_times = {a.date_time.strftime("%H:%M") for a in existing}

        # Generate slots
        start_hour, end_hour = 9, 21
        if period == "morning":
            start_hour, end_hour = 9, 12
        elif period == "afternoon":
            start_hour, end_hour = 12, 17
        elif period == "evening":
            start_hour, end_hour = 17, 21

        slots = []
        for hour in range(start_hour, end_hour):
            for minute in [0, 30]:
                slot_time = f"{hour:02d}:{minute:02d}"
                if slot_time not in busy_times:
                    slots.append(slot_time)
        return slots

    async def _get_by_id(self, appointment_id: int) -> Optional[models.Appointment]:
        stmt = (
            select(models.Appointment)
            .join(models.Patient)
            .where(
                models.Appointment.id == appointment_id,
                models.Patient.tenant_id == self.tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
