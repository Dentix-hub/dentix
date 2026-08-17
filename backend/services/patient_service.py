from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend import models, schemas
from backend.ai.policy.execution_policy import policy_engine
from backend.utils.patient_search_normalization import (
    escaped_like_pattern,
    normalize_patient_name_for_search,
    patient_phone_search_hash,
)


def _calculate_age(date_of_birth: date) -> int:
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


class PatientService:
    def __init__(self, db: AsyncSession = None, tenant_id: int = None):
        self.db = db
        self.tenant_id = tenant_id

    async def get_patient(self, db: AsyncSession = None, patient_id: int = None) -> Optional[models.Patient]:
        _db = db or self.db
        if not _db:
            raise ValueError("DB Session required")
        stmt = select(models.Patient).where(models.Patient.id == patient_id)
        result = await _db.execute(stmt)
        return result.scalars().first()

    async def get_patient_by_name(self, db: AsyncSession = None, tenant_id: int = None, name: str = None) -> Optional[models.Patient]:
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")
        normalized_name = normalize_patient_name_for_search(name)
        stmt = select(models.Patient).where(
            models.Patient.tenant_id == _tid,
            models.Patient.is_deleted == False,
            or_(
                models.Patient.name_search_normalized == normalized_name,
                (models.Patient.name_search_normalized.is_(None) & (models.Patient.name == name)),
            ),
        )
        result = await _db.execute(stmt)
        return result.scalars().first()

    async def get_patient_file_details(self, name: str, db: AsyncSession = None, tenant_id: int = None) -> dict:
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")
        normalized_name = normalize_patient_name_for_search(name.strip())
        pattern = escaped_like_pattern(normalized_name)
        stmt = select(models.Patient).where(
            models.Patient.tenant_id == _tid,
            models.Patient.is_deleted == False,
            or_(
                models.Patient.name_search_normalized.ilike(pattern, escape="\\"),
                (models.Patient.name_search_normalized.is_(None) & models.Patient.name.ilike(f"%{name.strip()}%")),
            ),
        )
        result = await _db.execute(stmt)
        patients = result.scalars().all()
        if not patients:
            return {"found": False, "message": f"لم يتم العثور على مريض باسم '{name}'"}
        if len(patients) > 1:
            return {
                "found": True, "multiple": True, "count": len(patients),
                "patients": [{"id": p.id, "name": p.name} for p in patients],
            }
        patient = patients[0]
        stmt_t = (
            select(models.Treatment)
            .where(models.Treatment.patient_id == patient.id)
            .order_by(desc(models.Treatment.date))
            .limit(5)
        )
        result_t = await _db.execute(stmt_t)
        return {
            "found": True, "multiple": False, "patient": patient,
            "treatments": result_t.scalars().all(),
        }

    async def search_patients_by_name(self, query: str, db: AsyncSession = None, tenant_id: int = None) -> List[models.Patient]:
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")
        normalized_query = normalize_patient_name_for_search(query)
        pattern = escaped_like_pattern(normalized_query)
        stmt = (
            select(models.Patient)
            .where(
                models.Patient.tenant_id == _tid,
                models.Patient.is_deleted == False,
                or_(
                    models.Patient.name_search_normalized.ilike(pattern, escape="\\"),
                    (models.Patient.name_search_normalized.is_(None) & models.Patient.name.ilike(f"%{query}%")),
                ),
            )
            .limit(20)
        )
        result = await _db.execute(stmt)
        return result.scalars().all()

    async def get_patients_with_balance(self, db: AsyncSession = None, tenant_id: int = None) -> List[dict]:
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")
        stmt = (
            select(models.Patient)
            .where(models.Patient.tenant_id == _tid, models.Patient.is_deleted == False)
            .options(joinedload(models.Patient.treatments), joinedload(models.Patient.payments))
        )
        result = await _db.execute(stmt)
        patients = result.scalars().unique().all()
        debtors = []
        for p in patients:
            total_cost = sum((t.cost or 0) - (t.discount or 0) for t in p.treatments)
            total_paid = sum(pm.amount or 0 for pm in p.payments)
            balance = total_cost - total_paid
            if balance > 0:
                debtors.append({"id": p.id, "name": p.name, "phone": p.phone or "", "balance": balance})
        debtors.sort(key=lambda x: x["balance"], reverse=True)
        return debtors[:50]

    async def get_patient_summary_data(self, name: str, db: AsyncSession = None, tenant_id: int = None) -> dict:
        _db = db or self.db
        details = await self.get_patient_file_details(name, db, tenant_id)
        if not details["found"] or details.get("multiple"):
            return details
        patient = details["patient"]
        treatments = details["treatments"]
        result_p = await _db.execute(select(models.Payment).where(models.Payment.patient_id == patient.id))
        payments = result_p.scalars().all()
        result_t = await _db.execute(select(models.Treatment).where(models.Treatment.patient_id == patient.id))
        all_treatments = result_t.scalars().all()
        true_total_cost = sum((t.cost or 0) - (t.discount or 0) for t in all_treatments)
        total_paid = sum(p.amount or 0 for p in payments)
        balance = true_total_cost - total_paid
        last_visit = patient.created_at
        if all_treatments:
            dates = [t.date for t in all_treatments if t.date]
            if dates:
                last_visit = max(dates)
        summary_data = {
            "age": patient.age,
            "history": patient.medical_history or "",
            "recent_procedures": [t.procedure for t in treatments],
            "last_visit": str(last_visit),
            "total_due": balance,
        }
        return {"found": True, "patient": patient, "summary_data": summary_data}

    async def create_patient(self, patient_data: schemas.PatientCreate, db: AsyncSession = None, tenant_id: int = None, creator_role: str = "doctor") -> models.Patient:
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db or not _tid:
            raise ValueError("DB and Tenant ID required")
        if not policy_engine.check_permission("patient_registration", creator_role):
            raise PermissionError(f"Role '{creator_role}' is not allowed to register patients.")

        normalized_name = normalize_patient_name_for_search(patient_data.name)
        phone_hash = patient_phone_search_hash(patient_data.phone)
        if phone_hash:
            stmt = select(models.Patient).where(
                models.Patient.tenant_id == _tid,
                models.Patient.is_deleted == False,
                models.Patient.name_search_normalized == normalized_name,
                models.Patient.phone_search_hash == phone_hash,
            )
            result = await _db.execute(stmt)
            if result.scalars().first():
                raise ValueError("A patient with the same name and phone already exists.")

        now = datetime.now(timezone.utc)
        exact_dob = patient_data.date_of_birth
        age = patient_data.age if patient_data.age is not None else 0
        dob_precision = None
        if exact_dob:
            age = _calculate_age(exact_dob)
            dob_precision = "exact"

        new_patient = models.Patient(
            tenant_id=_tid,
            name=patient_data.name,
            name_search_normalized=normalized_name,
            phone=patient_data.phone or "",
            phone_search_hash=phone_hash,
            email=patient_data.email,
            age=age,
            age_recorded_at=now if age > 0 else None,
            date_of_birth=exact_dob,
            date_of_birth_precision=dob_precision,
            address=patient_data.address,
            medical_history=patient_data.medical_history or "",
            assigned_doctor_id=patient_data.assigned_doctor_id,
            default_price_list_id=patient_data.default_price_list_id,
            notes=(
                f"{patient_data.notes or ''} [Gender: {patient_data.gender}]"
                if patient_data.gender else (patient_data.notes or "")
            ),
        )
        _db.add(new_patient)
        await _db.commit()
        await _db.refresh(new_patient)
        return new_patient

    async def update_patient(self, patient_id: int, updates: schemas.PatientUpdate, db: AsyncSession = None, tenant_id: int = None, updater_role: str = "doctor") -> models.Patient:
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")
        policy = policy_engine.get_policy("update_patient")
        if not policy_engine.check_permission("update_patient", updater_role):
            raise PermissionError(f"Role '{updater_role}' cannot update patients.")
        result = await _db.execute(
            select(models.Patient).where(
                models.Patient.id == patient_id,
                models.Patient.tenant_id == _tid,
                models.Patient.is_deleted == False,
            )
        )
        patient = result.scalars().first()
        if not patient:
            raise ValueError("Patient not found.")

        allowed_fields = policy.allowed_fields if policy and policy.allowed_fields else []
        update_data = updates.model_dump(exclude_unset=True)
        for field in update_data:
            if allowed_fields and field not in allowed_fields:
                raise PermissionError(f"Field '{field}' is protected/read-only for this action.")

        if "name" in update_data:
            patient.name_search_normalized = normalize_patient_name_for_search(update_data["name"])
        if "phone" in update_data:
            patient.phone_search_hash = patient_phone_search_hash(update_data["phone"])

        now = datetime.now(timezone.utc)
        if "date_of_birth" in update_data:
            exact_dob = update_data["date_of_birth"]
            if exact_dob:
                update_data["age"] = _calculate_age(exact_dob)
                patient.date_of_birth_precision = "exact"
                patient.age_recorded_at = now
            else:
                patient.date_of_birth_precision = None
                if "age" in update_data and update_data["age"] is not None:
                    patient.age_recorded_at = now
        elif "age" in update_data and update_data["age"] is not None:
            if patient.date_of_birth and patient.date_of_birth_precision == "exact":
                update_data["age"] = _calculate_age(patient.date_of_birth)
            else:
                patient.age_recorded_at = now

        for field, value in update_data.items():
            setattr(patient, field, value)
        await _db.commit()
        await _db.refresh(patient)
        return patient


patient_service = PatientService()
