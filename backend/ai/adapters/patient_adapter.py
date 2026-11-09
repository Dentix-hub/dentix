from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models, schemas
from backend.core.money import as_decimal
from backend.core.permissions import Permission, has_permission
from backend.services.patient_service import PatientService
from backend.services.visibility_service import get_visibility_service, PatientVisibilityService
from backend.utils.patient_search_normalization import (
    escaped_like_pattern,
    normalize_patient_name_for_search,
)
from backend.ai.errors import AIValidationError, AINotFoundError, AIExecutionError


class PatientToolAdapter:
    """
    Adapter to bridge AI Tool Registry with PatientService.
    Converts raw tool parameters into Service calls and standardizes responses.
    Enforces canonical patient visibility when user and db session are provided.
    """

    def __init__(
        self,
        service: PatientService,
        user: Optional[models.User] = None,
        db: Optional[AsyncSession] = None,
    ):
        self.service = service
        self.user = user
        self.db = db
        self.visibility_service: Optional[PatientVisibilityService] = (
            get_visibility_service(db, user, service.tenant_id)
            if (db is not None and user is not None and service.tenant_id is not None)
            else None
        )

    async def get_patient_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: get_patient_file"""
        name = params.get("patient_name", "")
        if not name:
            raise AIValidationError(
                "اسم المريض مطلوب",
                debug_info={"params": params},
                code="missing_parameter",
            )

        if self.visibility_service and self.db:
            normalized_name = normalize_patient_name_for_search(name.strip())
            pattern = escaped_like_pattern(normalized_name)
            vis_query = await self.visibility_service.get_visible_patient_query()
            stmt = vis_query.where(
                or_(
                    models.Patient.name_search_normalized.ilike(pattern, escape="\\"),
                    (
                        models.Patient.name_search_normalized.is_(None)
                        & models.Patient.name.ilike(f"%{name.strip()}%")
                    ),
                )
            )
            result = await self.db.execute(stmt)
            patients = result.scalars().all()
            if not patients:
                raise AINotFoundError(
                    f"لم يتم العثور على مريض باسم '{name}'",
                    debug_info={"query": name},
                    code="patient_not_found",
                )
            if len(patients) > 1:
                return {
                    "success": True,
                    "message": f"تم العثور على {len(patients)} مريض بهذا الاسم",
                    "patients": [{"id": p.id, "name": p.name} for p in patients],
                    "multiple": True,
                }
            p = patients[0]
            stmt_t = (
                select(models.Treatment)
                .where(models.Treatment.patient_id == p.id)
                .order_by(desc(models.Treatment.date))
                .limit(5)
            )
            result_t = await self.db.execute(stmt_t)
            treatments = result_t.scalars().all()
        else:
            result = await self.service.get_patient_file_details(name)

            if not result["found"]:
                raise AINotFoundError(
                    result["message"], debug_info={"query": name}, code="patient_not_found"
                )

            if result.get("multiple"):
                return {
                    "success": True,
                    "message": f"تم العثور على {result['count']} مريض بهذا الاسم",
                    "patients": result["patients"],
                    "multiple": True,
                }

            p = result["patient"]
            treatments = result["treatments"]

        return {
            "success": True,
            "message": f"ملف المريض: {p.name}",
            "patient": {
                "id": p.id,
                "name": p.name,
                "phone": str(p.phone),
                "age": p.age,
                "medical_history": str(p.medical_history),
                "created_at": str(p.created_at) if p.created_at else None,
            },
            "recent_treatments": [
                {
                    "id": t.id,
                    "procedure": t.procedure,
                    "diagnosis": t.diagnosis,
                    "cost": t.cost,
                    "date": str(t.date),
                }
                for t in treatments
            ],
        }

    async def search_patients(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: search_patients"""
        query = params.get("query", "")
        if not query:
            raise AIValidationError("كلمة البحث مطلوبة", code="missing_parameter")

        if self.visibility_service and self.db:
            normalized_query = normalize_patient_name_for_search(query.strip())
            pattern = escaped_like_pattern(normalized_query)
            vis_query = await self.visibility_service.get_visible_patient_query()
            stmt = (
                vis_query.where(
                    or_(
                        models.Patient.name_search_normalized.ilike(pattern, escape="\\"),
                        (
                            models.Patient.name_search_normalized.is_(None)
                            & models.Patient.name.ilike(f"%{query.strip()}%")
                        ),
                    )
                ).limit(20)
            )
            result = await self.db.execute(stmt)
            patients = result.scalars().all()
        else:
            patients = await self.service.search_patients_by_name(query)

        return {
            "success": True,
            "message": f"نتائج البحث عن '{query}': {len(patients)} مريض",
            "patients": [
                {"id": p.id, "name": p.name, "phone": str(p.phone), "age": p.age}
                for p in patients
            ],
        }

    async def summarize_patient(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: summarize_patient"""
        name = params.get("patient_name", "")
        if not name:
            raise AIValidationError("اسم المريض مطلوب", code="missing_parameter")

        if self.visibility_service and self.db:
            normalized_name = normalize_patient_name_for_search(name.strip())
            pattern = escaped_like_pattern(normalized_name)
            vis_query = await self.visibility_service.get_visible_patient_query()
            stmt = vis_query.where(
                or_(
                    models.Patient.name_search_normalized.ilike(pattern, escape="\\"),
                    (
                        models.Patient.name_search_normalized.is_(None)
                        & models.Patient.name.ilike(f"%{name.strip()}%")
                    ),
                )
            )
            result = await self.db.execute(stmt)
            patients = result.scalars().all()
            if not patients:
                raise AINotFoundError(
                    f"لم يتم العثور على مريض باسم '{name}'", code="patient_not_found"
                )
            if len(patients) > 1:
                return {
                    "success": True,
                    "multiple": True,
                    "message": "يوجد أكثر من مريض بهذا الاسم، برجاء التحديد.",
                    "patients": [
                        {"id": p.id, "name": p.name} for p in patients
                    ],
                }

            patient = patients[0]
            stmt_t = (
                select(models.Treatment)
                .where(models.Treatment.patient_id == patient.id)
                .order_by(desc(models.Treatment.date))
                .limit(5)
            )
            res_t = await self.db.execute(stmt_t)
            recent_treatments = res_t.scalars().all()

            user_role = getattr(self.user, "role", "guest") if self.user else "guest"
            can_view_receivables = has_permission(user_role, Permission.RECEIVABLE_READ)

            def _normalize_date(val):
                if isinstance(val, datetime):
                    return val.date()
                return val

            last_visit = _normalize_date(patient.created_at)
            if recent_treatments:
                dates = [_normalize_date(t.date) for t in recent_treatments if t.date]
                if dates:
                    last_visit = max(dates)

            summary_data: Dict[str, Any] = {
                "age": patient.age,
                "history": patient.medical_history or "",
                "recent_procedures": [t.procedure for t in recent_treatments],
                "last_visit": str(last_visit),
            }

            if can_view_receivables:
                res_p = await self.db.execute(
                    select(models.Payment).where(models.Payment.patient_id == patient.id)
                )
                payments = res_p.scalars().all()

                res_all_t = await self.db.execute(
                    select(models.Treatment).where(models.Treatment.patient_id == patient.id)
                )
                all_treatments = res_all_t.scalars().all()

                true_total_cost = sum(
                    (as_decimal(t.cost) - as_decimal(t.discount) for t in all_treatments),
                    Decimal("0"),
                )
                total_paid = sum((as_decimal(pm.amount) for pm in payments), Decimal("0"))
                balance = true_total_cost - total_paid

                if all_treatments:
                    dates = [_normalize_date(t.date) for t in all_treatments if t.date]
                    if dates:
                        summary_data["last_visit"] = str(max(dates))

                summary_data["total_due"] = balance

            return {
                "success": True,
                "message": f"بيانات ملخص المريض {patient.name}",
                "summary_data": summary_data,
                "patient_name": patient.name,
            }
        else:
            user_role = getattr(self.user, "role", "guest") if self.user else "guest"
            can_view_receivables = has_permission(user_role, Permission.RECEIVABLE_READ)
            result = await self.service.get_patient_summary_data(
                name, include_financials=can_view_receivables
            )

            if not result["found"]:
                raise AINotFoundError(
                    result.get("message", "المريض غير موجود"), code="patient_not_found"
                )

            if result.get("multiple"):
                return {
                    "success": True,
                    "multiple": True,
                    "message": "يوجد أكثر من مريض بهذا الاسم، برجاء التحديد.",
                    "patients": [
                        {"id": p.id, "name": p.name} for p in result.get("patients", [])
                    ],
                }

            return {
                "success": True,
                "message": f"بيانات ملخص المريض {result['patient'].name}",
                "summary_data": result["summary_data"],
                "patient_name": result["patient"].name,
            }

    async def create_patient(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: create_patient"""
        # Convert dict to Pydantic model to avoid AttributeError in service
        try:
            # Map keys if needed or assume direct match
            # AI definitions use 'patient_name' but schema uses 'name'
            data_dict = params.copy()
            if "patient_name" in data_dict and "name" not in data_dict:
                data_dict["name"] = data_dict.pop("patient_name")

            # Map chief_complaint to notes if present
            if "chief_complaint" in data_dict:
                complaint = data_dict.pop("chief_complaint")
                current_notes = data_dict.get("notes", "")
                data_dict["notes"] = f"{current_notes}\nشكوى: {complaint}".strip()

            patient_data = schemas.PatientCreate(**data_dict)
        except Exception as e:
            raise AIValidationError(
                f"Invalid patient data: {str(e)}", code="validation_error"
            )

        try:
            creator_role = self.user.role if self.user else "doctor"
            new_patient = await self.service.create_patient(
                patient_data, creator_role=creator_role
            )

            return {
                "success": True,
                "message": f"✅ تم إنشاء ملف المريض بنجاح. رقم الملف: {new_patient.id}",
                "patient": {
                    "id": new_patient.id,
                    "name": new_patient.name,
                    "phone": str(new_patient.phone),
                    "age": new_patient.age,
                },
                "suggestions": ["احجز موعد", "أضف علاج", "سجل دفعة"],
            }
        except Exception as e:
            raise AIExecutionError(f"فشل إنشاء المريض: {str(e)}", code="create_failed")

    async def get_patients_with_balance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: get_patients_with_balance"""
        patients = await self.service.get_patients_with_balance()

        if self.visibility_service:
            visible_ids = await self.visibility_service.get_visible_patient_ids()
            patients = [p for p in patients if p["id"] in visible_ids]

        total_outstanding = sum(p["balance"] for p in patients)

        detail_msg = ""
        if patients:
            detail_msg = "\n" + "\n".join(
                [f"• {p['name']}: {p['balance']:,.0f} جنيه" for p in patients[:15]]
            )

        return {
            "success": True,
            "message": f"💳 المرضى المدينين: {len(patients)} مريض\n💰 إجمالي المستحق: {total_outstanding:,.0f} جنيه{detail_msg}",
            "total_outstanding": total_outstanding,
            "patients": patients[:20],
        }
