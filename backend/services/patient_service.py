import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, select, func, text
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any

from backend import models, schemas
from backend.ai.policy.execution_policy import policy_engine


class PatientService:
    """
    Encapsulates all logic related to patient management.
    Used by both API Routers and AI Tools.
    """

    def __init__(self, db: AsyncSession = None, tenant_id: int = None):
        self.db = db
        self.tenant_id = tenant_id

    async def get_patient(
        self, db: AsyncSession = None, patient_id: int = None
    ) -> Optional[models.Patient]:
        _db = db or self.db
        if not _db:
            raise ValueError("DB Session required")
        stmt = select(models.Patient).where(models.Patient.id == patient_id)
        result = await _db.execute(stmt)
        return result.scalars().first()

    async def get_patient_by_name(
        self, db: AsyncSession = None, tenant_id: int = None, name: str = None
    ) -> Optional[models.Patient]:
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")

        stmt = (
            select(models.Patient)
            .where(models.Patient.tenant_id == _tid, models.Patient.name == name)
        )
        result = await _db.execute(stmt)
        return result.scalars().first()

    async def get_patient_file_details(
        self, name: str, db: AsyncSession = None, tenant_id: int = None
    ) -> dict:
        """
        Retrieves detailed patient file including recent treatments.
        Used by get_patient_file AI tool.
        """
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")

        # Normalize name for search
        name_query = name.strip()

        # Search patients
        stmt = (
            select(models.Patient)
            .where(
                models.Patient.tenant_id == _tid,
                models.Patient.name.ilike(f"%{name_query}%"),
            )
        )
        result = await _db.execute(stmt)
        patients = result.scalars().all()

        if not patients:
            return {"found": False, "message": f"لم يتم العثور على مريض باسم '{name}'"}

        if len(patients) > 1:
            return {
                "found": True,
                "multiple": True,
                "count": len(patients),
                "patients": [{"id": p.id, "name": p.name} for p in patients],
            }

        # Single matched patient
        patient = patients[0]

        # Get recent treatments
        stmt_t = (
            select(models.Treatment)
            .where(models.Treatment.patient_id == patient.id)
            .order_by(desc(models.Treatment.date))
            .limit(5)
        )
        result_t = await _db.execute(stmt_t)
        treatments = result_t.scalars().all()

        return {
            "found": True,
            "multiple": False,
            "patient": patient,
            "treatments": treatments,
        }

    async def search_patients_by_name(
        self, query: str, db: AsyncSession = None, tenant_id: int = None
    ) -> List[models.Patient]:
        """
        Search patients by name (fuzzy match).
        """
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")

        stmt = (
            select(models.Patient)
            .where(
                models.Patient.tenant_id == _tid,
                models.Patient.name.ilike(f"%{query}%"),
            )
            .limit(20)
        )
        result = await _db.execute(stmt)
        return result.scalars().all()

    async def get_patients_with_balance(
        self, db: AsyncSession = None, tenant_id: int = None
    ) -> List[dict]:
        """
        Get patients with outstanding debt.
        Calculates balance dynamically (Cost - Paid).
        """
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")

        # Eager load treatments and payments to avoid N+1
        # FIX: Filter out deleted patients
        stmt = (
            select(models.Patient)
            .where(
                models.Patient.tenant_id == _tid,
                models.Patient.is_deleted == False,  # noqa: E712 — Exclude soft-deleted patients
            )
            .options(
                joinedload(models.Patient.treatments),
                joinedload(models.Patient.payments),
            )
        )
        result = await _db.execute(stmt)
        patients = result.scalars().unique().all()

        debtors = []
        for p in patients:
            # Calculate logic
            total_cost = sum((t.cost or 0) - (t.discount or 0) for t in p.treatments)
            total_paid = sum(pm.amount or 0 for pm in p.payments)
            balance = total_cost - total_paid

            if balance > 0:
                debtors.append(
                    {
                        "id": p.id,
                        "name": p.name,
                        "phone": p.phone.decrypt()
                        if hasattr(p.phone, "decrypt")
                        else str(p.phone),
                        "balance": balance,
                    }
                )

        # Sort by balance descending
        debtors.sort(key=lambda x: x["balance"], reverse=True)
        return debtors[:50]

    async def get_patient_summary_data(
        self, name: str, db: AsyncSession = None, tenant_id: int = None
    ) -> dict:
        """
        Get summary data for AI summarization.
        """
        _db = db or self.db

        # Reuse get_patient_file_details logic logic
        details = await self.get_patient_file_details(name, db, tenant_id)

        if not details["found"] or details.get("multiple"):
            return details

        patient = details["patient"]
        treatments = details["treatments"]

        # Eager load payments if not already loaded?
        # get_patient_file_details didn't eager load payments.
        # Let's fetch payments for this patient specifically.
        stmt_p = (
            select(models.Payment)
            .where(models.Payment.patient_id == patient.id)
        )
        result_p = await _db.execute(stmt_p)
        payments = result_p.scalars().all()

        # Refetch full history for math
        stmt_t = (
            select(models.Treatment)
            .where(models.Treatment.patient_id == patient.id)
        )
        result_t = await _db.execute(stmt_t)
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
            "history": patient.medical_history.decrypt()
            if hasattr(patient.medical_history, "decrypt")
            else str(patient.medical_history),
            "recent_procedures": [t.procedure for t in treatments],
            "last_visit": str(last_visit),
            "total_due": balance,  # Calculated
        }

        return {"found": True, "patient": patient, "summary_data": summary_data}

    async def check_duplicate(
        self,
        name: str,
        phone: Optional[str] = None,
        db: AsyncSession = None,
        tenant_id: int = None,
    ) -> Dict[str, Any]:
        """Check for duplicate or similar patients."""
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db or not _tid or not name:
            return {"exact_match": None, "similar_patients": []}

        clean_name = name.strip()
        norm_phone = re.sub(r"\D", "", phone) if phone else ""

        stmt = select(models.Patient).where(
            models.Patient.tenant_id == _tid,
            models.Patient.is_deleted.is_(False),
        )
        res = await _db.execute(stmt)
        patients = res.scalars().all()

        exact_match = None
        similar_patients = []

        for p in patients:
            p_name = (p.name or "").strip()
            p_phone = re.sub(r"\D", "", p.phone or "") if p.phone else ""
            file_num = p.file_number or p.id

            name_equal = p_name.lower() == clean_name.lower()
            phone_equal = norm_phone != "" and p_phone != "" and p_phone == norm_phone

            if name_equal and (phone_equal or norm_phone == "" or p_phone == ""):
                exact_match = {
                    "id": p.id,
                    "file_number": file_num,
                    "name": p.name,
                    "phone": p.phone,
                }
                break
            elif phone_equal and norm_phone != "":
                exact_match = {
                    "id": p.id,
                    "file_number": file_num,
                    "name": p.name,
                    "phone": p.phone,
                }
                break
            elif clean_name.lower() in p_name.lower() or p_name.lower() in clean_name.lower():
                if len(similar_patients) < 5:
                    similar_patients.append({
                        "id": p.id,
                        "file_number": file_num,
                        "name": p.name,
                        "phone": p.phone,
                    })

        return {"exact_match": exact_match, "similar_patients": similar_patients}

    async def get_field_suggestions(
        self,
        field: str,
        db: AsyncSession = None,
        tenant_id: int = None,
    ) -> List[str]:
        """Get distinct suggestions for patient fields (address, medical_history)."""
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db or not _tid:
            return []

        if field not in ("address", "medical_history", "notes"):
            return []

        stmt = select(models.Patient).where(
            models.Patient.tenant_id == _tid,
            models.Patient.is_deleted.is_(False),
        )
        res = await _db.execute(stmt)
        patients = res.scalars().all()

        from backend.core.security import get_encryption_manager
        enc_mgr = get_encryption_manager()

        suggestions = set()
        for p in patients:
            val = getattr(p, field, None)
            if val and isinstance(val, str) and val.strip():
                if val.startswith("gAAAAA"):
                    try:
                        val = enc_mgr.decrypt(val, allow_plaintext_fallback=True)
                    except Exception:
                        continue
                if not val or val.startswith("gAAAAA"):
                    continue
                items = [i.strip() for i in val.split("،") if i.strip()] if "،" in val else [val.strip()]
                for item in items:
                    if len(item) > 1 and not item.startswith("[Gender:") and not item.startswith("gAAAAA"):
                        suggestions.add(item)

        return sorted(list(suggestions))[:30]

    async def create_patient(
        self,
        patient_data: schemas.PatientCreate,
        db: AsyncSession = None,
        tenant_id: int = None,
        creator_role: str = "doctor",
    ) -> models.Patient:
        """
        Creates a new patient record.
        Enforces Policy: 'patient_registration'
        """
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db or not _tid:
            raise ValueError("DB and Tenant ID required")

        # 1. Governance Check
        if not policy_engine.check_permission("patient_registration", creator_role):
            raise PermissionError(
                f"Role '{creator_role}' is not allowed to register patients."
            )

        # 2. Duplicate Check
        dup_info = await self.check_duplicate(
            name=patient_data.name,
            phone=patient_data.phone,
            db=_db,
            tenant_id=_tid,
        )
        if dup_info["exact_match"]:
            match = dup_info["exact_match"]
            raise ValueError(
                f"Patient already exists: '{match['name']}' "
                f"(file #{match['file_number']})"
            )

        # Serialize file-number allocation per tenant on PostgreSQL. The database
        # unique constraint remains the final safety net for every caller.
        bind = _db.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            await _db.execute(
                text("SELECT pg_advisory_xact_lock(:tenant_id)"),
                {"tenant_id": int(_tid)},
            )

        # 3. Generate file_number if not provided
        file_num = patient_data.file_number
        if file_num is None:
            stmt_max = select(func.max(models.Patient.file_number)).where(
                models.Patient.tenant_id == _tid
            )
            max_val = (await _db.execute(stmt_max)).scalar() or 0
            file_num = max_val + 1

        # 4. Create Model
        new_patient = models.Patient(
            tenant_id=_tid,
            file_number=file_num,
            name=patient_data.name,
            phone=patient_data.phone or "",
            email=patient_data.email,
            age=patient_data.age if patient_data.age is not None else 0,
            address=patient_data.address,
            medical_history=patient_data.medical_history or "",
            assigned_doctor_id=patient_data.assigned_doctor_id,
            default_price_list_id=patient_data.default_price_list_id,
            notes=f"{patient_data.notes or ''} [Gender: {patient_data.gender}]"
            if patient_data.gender
            else (patient_data.notes or ""),
        )

        _db.add(new_patient)
        try:
            await _db.commit()
            await _db.refresh(new_patient)
        except IntegrityError as exc:
            await _db.rollback()
            if "uq_patients_tenant_file_number" in str(exc):
                raise ValueError(
                    f"Patient file number {file_num} is already in use"
                ) from exc
            raise
        return new_patient

    async def update_patient(
        self,
        patient_id: int,
        updates: schemas.PatientUpdate,
        db: AsyncSession = None,
        tenant_id: int = None,
        updater_role: str = "doctor",
    ) -> models.Patient:
        """
        Updates patient record.
        Enforces Policy: 'update_patient' & Field whitelist.
        """
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")

        # 1. Governance Check
        policy = policy_engine.get_policy("update_patient")
        if not policy_engine.check_permission("update_patient", updater_role):
            raise PermissionError(f"Role '{updater_role}' cannot update patients.")

        stmt = (
            select(models.Patient)
            .where(models.Patient.id == patient_id, models.Patient.tenant_id == _tid)
        )
        result = await _db.execute(stmt)
        patient = result.scalars().first()

        if not patient:
            raise ValueError("Patient not found.")

        # 2. Field Level Security
        allowed_fields = (
            policy.allowed_fields if policy and policy.allowed_fields else []
        )

        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if allowed_fields and field not in allowed_fields:
                raise PermissionError(
                    f"Field '{field}' is protected/read-only for this action."
                )

            setattr(patient, field, value)

        await _db.commit()
        await _db.refresh(patient)
        return patient


# Singleton for Router usage (stateless)
patient_service = PatientService()
