"""Finance AI handler facade using the same financial truth as Finance V2."""

from __future__ import annotations

from typing import Dict

from sqlalchemy import func, or_, select

from backend import models
from backend.schemas.billing import PaymentCreate
from backend.services.billing_service import BillingService
from backend.services.visibility_service import get_visibility_service
from backend.utils.patient_search_normalization import (
    escaped_like_pattern,
    normalize_patient_name_for_search,
)

from ..tools.security import RiskLevel, risk_level
from .finance_legacy import FinanceHandler as LegacyFinanceHandler


class FinanceHandler(LegacyFinanceHandler):
    """Keep legacy AI tools but reconcile financial reads/writes with Finance V2."""

    @risk_level(RiskLevel.SAFE)
    async def get_financial_record(self, params: Dict) -> Dict:
        name = params.get("patient_name", "")
        if not name:
            return {"error": "اسم المريض مطلوب"}

        visibility_service = get_visibility_service(self.db, self.user, self.tenant_id)
        vis_query = await visibility_service.get_visible_patient_query()
        normalized_name = normalize_patient_name_for_search(name.strip())
        pattern = escaped_like_pattern(normalized_name)
        stmt = (
            vis_query.where(
                or_(
                    models.Patient.name_search_normalized.ilike(pattern, escape="\\"),
                    (
                        models.Patient.name_search_normalized.is_(None)
                        & models.Patient.name.ilike(f"%{name.strip()}%")
                    ),
                )
            ).limit(20)
        )
        res = await self.db.execute(stmt)
        patients = res.scalars().all()

        if not patients:
            return {"message": f"لم يتم العثور على مريض باسم '{name}'"}
        if len(patients) > 1:
            return {
                "message": f"تم العثور على {len(patients)} مريض. يرجى تحديد الاسم بدقة:",
                "patients": [
                    {"id": patient.id, "name": patient.name, "phone": patient.phone}
                    for patient in patients
                ],
            }

        patient = patients[0]
        invoiced_stmt = (
            select(func.coalesce(func.sum(
                models.Treatment.cost - models.Treatment.discount
            ), 0.0))
            .join(models.Patient, models.Treatment.patient_id == models.Patient.id)
            .where(
                models.Treatment.patient_id == patient.id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
                models.Treatment.is_deleted == False,  # noqa: E712
            )
        )
        paid_stmt = (
            select(func.coalesce(func.sum(models.Payment.amount), 0.0))
            .join(models.Patient, models.Payment.patient_id == models.Patient.id)
            .where(
                models.Payment.patient_id == patient.id,
                models.Patient.tenant_id == self.tenant_id,
                models.Patient.is_deleted == False,  # noqa: E712
            )
        )
        total_invoiced = float((await self.db.execute(invoiced_stmt)).scalar() or 0.0)
        total_paid = float((await self.db.execute(paid_stmt)).scalar() or 0.0)
        remaining = max(0.0, total_invoiced - total_paid)

        return {
            "message": f"الحساب المالي: {patient.name}",
            # Keep the legacy key for tool compatibility, but its value now means
            # authoritative net invoiced (after discounts), not gross treatment cost.
            "total_cost": total_invoiced,
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "remaining": remaining,
            "status": "مسدد بالكامل"
            if remaining <= 0
            else f"متبقي {remaining:.2f} جنيه",
        }

    @risk_level(RiskLevel.WRITE)
    async def create_payment(self, params: Dict) -> Dict:
        patient_name = params.get("patient_name", "")
        amount = params.get("amount", 0)

        if not patient_name:
            return {"error": "missing_name", "message": "اسم المريض مطلوب"}
        try:
            amount = float(amount)
            if amount <= 0:
                return {
                    "error": "invalid_amount",
                    "message": "المبلغ يجب أن يكون أكبر من صفر",
                }
        except (ValueError, TypeError):
            return {"error": "invalid_amount", "message": "المبلغ غير صالح"}

        visibility_service = get_visibility_service(self.db, self.user, self.tenant_id)
        vis_query = await visibility_service.get_visible_patient_query()
        normalized_name = normalize_patient_name_for_search(patient_name.strip())
        pattern = escaped_like_pattern(normalized_name)
        stmt = (
            vis_query.where(
                or_(
                    models.Patient.name_search_normalized.ilike(pattern, escape="\\"),
                    (
                        models.Patient.name_search_normalized.is_(None)
                        & models.Patient.name.ilike(f"%{patient_name.strip()}%")
                    ),
                )
            ).limit(20)
        )
        res = await self.db.execute(stmt)
        patients = res.scalars().all()

        if not patients:
            return {
                "error": "patient_not_found",
                "message": f"لم يتم العثور على مريض باسم '{patient_name}'",
            }
        if len(patients) > 1:
            return {
                "error": "multiple_patients",
                "message": f"تم العثور على {len(patients)} مريض. يرجى تحديد الاسم بدقة:",
                "patients": [
                    {"id": patient.id, "name": patient.name, "phone": patient.phone}
                    for patient in patients
                ],
            }

        patient = patients[0]
        try:
            payment = await BillingService(self.db, self.tenant_id).create_payment(
                PaymentCreate(
                    patient_id=patient.id,
                    amount=amount,
                    notes="دفعة عبر المساعد الذكي",
                ),
                doctor_id=None,
                commit=True,
            )
        except Exception as exc:
            await self.db.rollback()
            return {
                "error": "payment_creation_failed",
                "message": f"حدث خطأ أثناء تسجيل الدفعة: {str(exc)}",
            }

        return {
            "message": f"✅ تم تسجيل دفعة {amount:.2f} جنيه للمريض {patient.name}",
            "action": "payment_created",
            "payment": {
                "id": payment.id,
                "patient_name": patient.name,
                "amount": amount,
                "date": str(payment.date),
            },
            "suggestions": [f"حساب {patient.name}", f"ملف {patient.name}"],
        }
