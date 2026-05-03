from typing import Dict
from datetime import datetime, timedelta
from ... import models
from .base import BaseHandler
from backend.services.patient_service import PatientService


class AppointmentHandler(BaseHandler):
    """Handles appointment booking and scheduling."""

    def __init__(self, db, user):
        super().__init__(db, user)
        # Initialize PatientService for lookups
        self.patient_service = PatientService(db, self.tenant_id)

    async def get_appointments(self, params: Dict) -> Dict:
        """Get appointments for a date."""
        date_str = params.get("date", "today")

        # Parse date
        if date_str == "today":
            target_date = datetime.now().date()
        elif date_str == "tomorrow":
            target_date = (datetime.now() + timedelta(days=1)).date()
        else:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = datetime.now().date()

        # Get appointments
        appointments = (
            self.db.query(models.Appointment)
            .join(models.Patient, models.Appointment.patient_id == models.Patient.id)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Appointment.date_time
                >= datetime.combine(target_date, datetime.min.time()),
                models.Appointment.date_time
                < datetime.combine(
                    target_date + timedelta(days=1), datetime.min.time()
                ),
            )
            .all()
        )

        if not appointments:
            return {"message": f"لا توجد مواعيد في {target_date}", "appointments": []}

        # Get patient names
        patient_ids = [a.patient_id for a in appointments]
        patients = {
            p.id: p.name
            for p in self.db.query(models.Patient)
            .filter(models.Patient.id.in_(patient_ids))
            .all()
        }

        return {
            "message": f"مواعيد يوم {target_date}: {len(appointments)} موعد",
            "date": str(target_date),
            "appointments": [
                {
                    "id": a.id,
                    "patient_name": patients.get(a.patient_id, "غير معروف"),
                    "time": a.date_time.strftime("%H:%M"),
                    "status": a.status,
                    "notes": a.notes,
                }
                for a in sorted(appointments, key=lambda x: x.date_time)
            ],
        }

    async def find_available_slots(self, params: Dict) -> Dict:
        """Find available appointment slots."""
        date_str = params.get("date", "today")
        period = params.get("period", "any")

        # Parse date
        if date_str == "today":
            target_date = datetime.now().date()
        elif date_str == "tomorrow":
            target_date = (datetime.now() + timedelta(days=1)).date()
        elif date_str == "next_week":
            target_date = (datetime.now() + timedelta(days=7)).date()
        else:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = datetime.now().date()

        # Get existing appointments for that day
        existing = (
            self.db.query(models.Appointment)
            .join(models.Patient)
            .filter(
                models.Patient.tenant_id == self.tenant_id,
                models.Appointment.date_time
                >= datetime.combine(target_date, datetime.min.time()),
                models.Appointment.date_time
                < datetime.combine(
                    target_date + timedelta(days=1), datetime.min.time()
                ),
            )
            .all()
        )

        busy_times = {a.date_time.strftime("%H:%M") for a in existing}

        # Generate all possible slots (9 AM to 9 PM, every 30 min)
        all_slots = []
        start_hour, end_hour = 9, 21

        if period == "morning":
            start_hour, end_hour = 9, 12
        elif period == "afternoon":
            start_hour, end_hour = 12, 17
        elif period == "evening":
            start_hour, end_hour = 17, 21

        for hour in range(start_hour, end_hour):
            for minute in [0, 30]:
                slot = f"{hour:02d}:{minute:02d}"
                if slot not in busy_times:
                    all_slots.append(slot)

        if not all_slots:
            return {
                "message": f"لا توجد مواعيد متاحة يوم {target_date}",
                "available_slots": [],
                "suggestions": ["شوف مواعيد بكره", "شوف مواعيد الأسبوع الجاي"],
            }

        return {
            "message": f"المواعيد المتاحة يوم {target_date}: {len(all_slots)} موعد",
            "date": str(target_date),
            "period": period,
            "available_slots": all_slots[:10],
            "total_available": len(all_slots),
            "suggestions": [f"احجز الساعة {all_slots[0]}" if all_slots else ""],
        }

    async def smart_book_appointment(self, params: Dict) -> Dict:
        """Smart appointment booking with conflict detection."""
        patient_name = params.get("patient_name", "")
        date_str = params.get("preferred_date", "today")
        time_str = params.get("preferred_time", "")
        procedure = params.get("procedure", "")

        if not patient_name:
            return {"error": "missing_name", "message": "اسم المريض مطلوب"}

        # Find patient using Service
        patients = self.patient_service.search_patients_by_name(patient_name)

        if not patients:
            return {
                "error": "patient_not_found",
                "message": f"لم يتم العثور على مريض باسم '{patient_name}'",
            }

        # If multiple matches, ask for clarification
        if len(patients) > 1:
            return {
                "error": "multiple_patients",
                "message": f"تم العثور على {len(patients)} مريض. يرجى تحديد الاسم بدقة:",
                "patients": [
                    {"id": p.id, "name": p.name, "phone": p.phone} for p in patients
                ],
            }

        # Single match
        patient = patients[0]

        # Parse date
        if date_str == "today":
            target_date = datetime.now().date()
        elif date_str == "tomorrow":
            target_date = (datetime.now() + timedelta(days=1)).date()
        else:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = datetime.now().date()

        # Parse preferred time or find first available
        if time_str:
            try:
                if ":" in str(time_str):
                    hour, minute = map(int, str(time_str).split(":"))
                else:
                    hour = int(time_str)
                    minute = 0
                preferred_time = datetime.combine(
                    target_date, datetime.min.time().replace(hour=hour, minute=minute)
                )
            except (ValueError, TypeError):
                preferred_time = None
        else:
            preferred_time = None

        # Check for conflicts
        if preferred_time:
            conflict = (
                self.db.query(models.Appointment)
                .join(models.Patient)
                .filter(
                    models.Patient.tenant_id == self.tenant_id,
                    models.Appointment.date_time == preferred_time,
                )
                .first()
            )

            if conflict:
                # Find alternatives
                available = await self.find_available_slots(
                    {"date": date_str, "period": "any"}
                )
                alternatives = available.get("available_slots", [])[:3]

                return {
                    "message": f"⚠️ الموعد الساعة {time_str} مشغول",
                    "conflict": True,
                    "alternatives": alternatives,
                    "suggestions": [f"احجز الساعة {alt}" for alt in alternatives],
                }
        else:
            # Find first available slot
            available = await self.find_available_slots(
                {"date": date_str, "period": "any"}
            )
            slots = available.get("available_slots", [])
            if not slots:
                return {
                    "message": f"لا توجد مواعيد متاحة يوم {target_date}",
                    "suggestions": ["شوف مواعيد بكره"],
                }
            hour, minute = map(int, slots[0].split(":"))
            preferred_time = datetime.combine(
                target_date, datetime.min.time().replace(hour=hour, minute=minute)
            )

        # Create appointment
        notes = "حجز ذكي عبر المساعد"
        if procedure:
            notes += f" - {procedure}"

        appointment = models.Appointment(
            patient_id=patient.id,
            date_time=preferred_time,
            status="Scheduled",
            notes=notes,
        )
        self.db.add(appointment)
        self.db.commit()

        return {
            "message": f"✅ تم حجز موعد لـ {patient.name} يوم {target_date} الساعة {preferred_time.strftime('%H:%M')}",
            "action": "appointment_created",
            "appointment": {
                "id": appointment.id,
                "patient_name": patient.name,
                "date": str(target_date),
                "time": preferred_time.strftime("%H:%M"),
                "procedure": procedure,
                "status": "Scheduled",
            },
            "suggestions": ["مواعيد اليوم", f"ملف {patient.name}"],
        }

    async def create_appointment(self, params: Dict) -> Dict:
        """Create a new appointment for a patient directly."""
        patient_name = params.get("patient_name", "")
        date_str = params.get("date", "today")
        time_str = params.get("time", "10:00")

        if not patient_name:
            return {"error": "missing_name", "message": "اسم المريض مطلوب"}

        # Parse date
        if date_str == "today":
            target_date = datetime.now().date()
        elif date_str == "tomorrow":
            target_date = (datetime.now() + timedelta(days=1)).date()
        elif date_str == "next_week":
            target_date = (datetime.now() + timedelta(weeks=1)).date()
        elif "بعد" in date_str and (
            "يوم" in date_str or "أيام" in date_str or "ايام" in date_str
        ):
            # Handle "after X days" in Arabic
            try:
                import re

                # Extract number
                nums = re.findall(r"\d+", date_str)
                if nums:
                    days = int(nums[0])
                elif "يومين" in date_str:
                    days = 2
                elif "ثلاث" in date_str:
                    days = 3
                elif "اربع" in date_str:
                    days = 4
                elif "خمس" in date_str:
                    days = 5
                elif "ست" in date_str:
                    days = 6
                elif "سبع" in date_str:  # سبع or اسبوع
                    days = 7
                else:
                    days = 0

                if days > 0:
                    target_date = (datetime.now() + timedelta(days=days)).date()
                else:
                    target_date = datetime.now().date()
            except Exception:
                target_date = datetime.now().date()
        else:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                # Try parsing assuming it might be a relative description the LLM failed to convert
                # But as a safe fallback, if provided date is invalid, better to ASK than Assume Today
                # For now, default to today but maybe adding a note would be better.
                # Let's check if the LLM sent "21-01-2026" (DD-MM-YYYY) instead of YYYY-MM-DD
                try:
                    target_date = datetime.strptime(date_str, "%d-%m-%Y").date()
                except ValueError:
                    target_date = datetime.now().date()

        # Parse time
        try:
            if ":" in str(time_str):
                hour, minute = map(int, str(time_str).split(":"))
            else:
                hour = int(time_str)
                minute = 0
            target_datetime = datetime.combine(
                target_date, datetime.min.time().replace(hour=hour, minute=minute)
            )
        except (ValueError, TypeError):
            target_datetime = datetime.combine(
                target_date, datetime.min.time().replace(hour=10, minute=0)
            )

        # Find patient using Service
        patients = self.patient_service.search_patients_by_name(patient_name)

        if not patients:
            return {
                "error": "patient_not_found",
                "message": f"لم يتم العثور على مريض باسم '{patient_name}'",
            }

        # If multiple matches, ask for clarification
        if len(patients) > 1:
            return {
                "error": "multiple_patients",
                "message": f"تم العثور على {len(patients)} مريض. يرجى تحديد الاسم بدقة:",
                "patients": [
                    {"id": p.id, "name": p.name, "phone": p.phone} for p in patients
                ],
            }

        # Single match
        patient = patients[0]

        # Create appointment
        appointment = models.Appointment(
            patient_id=patient.id,
            date_time=target_datetime,
            status="Scheduled",
            notes="حجز عبر المساعد الذكي",
        )
        self.db.add(appointment)
        self.db.commit()

        return {
            "message": f"✅ تم حجز موعد لـ {patient.name} يوم {target_date} الساعة {target_datetime.strftime('%H:%M')}",
            "action": "appointment_created",
            "appointment": {
                "id": appointment.id,
                "patient_name": patient.name,
                "date": str(target_date),
                "time": target_datetime.strftime("%H:%M"),
                "status": "Scheduled",
            },
            "suggestions": ["مواعيد اليوم", f"ملف {patient.name}"],
        }
