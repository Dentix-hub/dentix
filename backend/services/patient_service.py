from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from sqlalchemy import desc

from backend import models, schemas
from backend.ai.policy.execution_policy import policy_engine


class PatientService:
    """
    Encapsulates all logic related to patient management.
    Used by both API Routers and AI Tools.
    """

    def __init__(self, db: Session = None, tenant_id: int = None):
        self.db = db
        self.tenant_id = tenant_id

    def get_patient(
        self, db: Session = None, patient_id: int = None
    ) -> Optional[models.Patient]:
        _db = db or self.db
        if not _db:
            raise ValueError("DB Session required")
        return _db.query(models.Patient).filter(models.Patient.id == patient_id).first()

    def get_patient_by_name(
        self, db: Session = None, tenant_id: int = None, name: str = None
    ) -> Optional[models.Patient]:
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")

        return (
            _db.query(models.Patient)
            .filter(models.Patient.tenant_id == _tid, models.Patient.name == name)
            .first()
        )

    def get_patient_file_details(
        self, name: str, db: Session = None, tenant_id: int = None
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
        patients = (
            _db.query(models.Patient)
            .filter(
                models.Patient.tenant_id == _tid,
                models.Patient.name.ilike(f"%{name_query}%"),
            )
            .all()
        )

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
        treatments = (
            _db.query(models.Treatment)
            .filter(models.Treatment.patient_id == patient.id)
            .order_by(desc(models.Treatment.date))
            .limit(5)
            .all()
        )

        return {
            "found": True,
            "multiple": False,
            "patient": patient,
            "treatments": treatments,
        }

    def search_patients_by_name(
        self, query: str, db: Session = None, tenant_id: int = None
    ) -> List[models.Patient]:
        """
        Search patients by name (fuzzy match).
        """
        _db = db or self.db
        _tid = tenant_id or self.tenant_id
        if not _db:
            raise ValueError("DB Session required")

        return (
            _db.query(models.Patient)
            .filter(
                models.Patient.tenant_id == _tid,
                models.Patient.name.ilike(f"%{query}%"),
            )
            .limit(20)
            .all()
        )

    def get_patients_with_balance(
        self, db: Session = None, tenant_id: int = None
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
        patients = (
            _db.query(models.Patient)
            .filter(
                models.Patient.tenant_id == _tid,
                models.Patient.is_deleted == False,  # Exclude soft-deleted patients
            )
            .options(
                joinedload(models.Patient.treatments),
                joinedload(models.Patient.payments),
            )
            .all()
        )

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

    def get_patient_summary_data(
        self, name: str, db: Session = None, tenant_id: int = None
    ) -> dict:
        """
        Get summary data for AI summarization.
        """
        _db = db or self.db

        # Reuse get_patient_file_details logic logic
        details = self.get_patient_file_details(name, db, tenant_id)

        if not details["found"] or details.get("multiple"):
            return details

        patient = details["patient"]
        treatments = details["treatments"]

        # Eager load payments if not already loaded?
        # get_patient_file_details didn't eager load payments.
        # Let's fetch payments for this patient specifically.
        payments = (
            _db.query(models.Payment)
            .filter(models.Payment.patient_id == patient.id)
            .all()
        )

        sum(
            t.cost for t in treatments
        )  # Note: this only sums *recent* treatments from details?
        # NO, details['treatments'] is limited to 5. We need FULL treatment history for balance.

        # Refetch full history for math
        all_treatments = (
            _db.query(models.Treatment)
            .filter(models.Treatment.patient_id == patient.id)
            .all()
        )
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

    def create_patient(
        self,
        patient_data: schemas.PatientCreate,
        db: Session = None,
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
        existing = (
            _db.query(models.Patient)
            .filter(
                models.Patient.tenant_id == _tid,
                models.Patient.name == patient_data.name,
                models.Patient.phone == patient_data.phone,
            )
            .first()
        )

        if existing:
            raise ValueError(
                f"Patient '{patient_data.name}' with phone '{patient_data.phone}' already exists."
            )

        # 3. Create Model
        new_patient = models.Patient(
            tenant_id=_tid,
            name=patient_data.name,
            phone=patient_data.phone,
            age=patient_data.age,
            address=patient_data.address,
            medical_history=patient_data.medical_history,
            assigned_doctor_id=patient_data.assigned_doctor_id,
            notes=f"{patient_data.notes or ''} [Gender: {patient_data.gender}]"
            if patient_data.gender
            else patient_data.notes,
        )

        _db.add(new_patient)
        _db.commit()
        _db.refresh(new_patient)
        return new_patient

    def update_patient(
        self,
        patient_id: int,
        updates: schemas.PatientUpdate,
        db: Session = None,
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

        patient = (
            _db.query(models.Patient)
            .filter(models.Patient.id == patient_id, models.Patient.tenant_id == _tid)
            .first()
        )

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

        _db.commit()
        _db.refresh(patient)
        return patient


# Singleton for Router usage (stateless)
patient_service = PatientService()
