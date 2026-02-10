from typing import Dict
from ... import models
from .base import BaseHandler

# Security
from ..tools.security import risk_level, RiskLevel

# Services
from ...services.clinical_service import ClinicalService
from ...services.scribe_service import ScribeService
from ...services.patient_service import PatientService


class ClinicalHandler(BaseHandler):
    """
    Handles treatments, lab orders, and medical notes.
    Refactored to use ClinicalService and ScribeService.
    """

    def __init__(self, db, user: models.User):
        super().__init__(db, user)
        self.clinical = ClinicalService(db, self.tenant_id, self.user.id)
        self.scribe = ScribeService()
        self.patient_service = PatientService(db, self.tenant_id)

    @risk_level(RiskLevel.SAFE)
    async def get_recent_treatments(self, params: Dict) -> Dict:
        """Get recent treatments."""
        treatments = self.clinical.get_recent_treatments()
        return {
            "message": f"آخر العلاجات: {len(treatments)} علاج",
            "treatments": treatments,
        }

    @risk_level(RiskLevel.SAFE)
    async def get_lab_orders(self, params: Dict) -> Dict:
        """Get lab orders."""
        status = params.get("status", "all")
        orders = self.clinical.get_lab_orders(status)
        return {"message": f"طلبات المعمل: {len(orders)} طلب", "orders": orders}

    @risk_level(RiskLevel.WRITE)
    async def record_medical_note(self, params: Dict) -> Dict:
        """Record note from voice."""
        patient_name = params.get("patient_name", "")
        # ... implementation ...
        spoken_note = params.get("content") or params.get("spoken_note", "")
        note_type = params.get("note_type", "general")

        if not spoken_note:
            return {"error": "missing_note", "message": "الملاحظة فارغة"}

        patient = (
            await self._find_single_patient(patient_name) if patient_name else None
        )

        if isinstance(patient, dict):  # Returned specific error or list
            return patient

        if patient:
            self.clinical.record_medical_note(patient, spoken_note, note_type)
            return {
                "message": f"✅ تم تسجيل الملاحظة لـ {patient.name}",
                "action": "note_recorded",
                "patient_name": patient.name,
            }

        return {
            "message": f"📝 ملاحظة (غير مرتبطة):\n{spoken_note}",
            "action": "note_pending",
            "requires_patient": True,
        }

    @risk_level(RiskLevel.CRITICAL)
    async def update_tooth_status(self, params: Dict) -> Dict:
        """Update tooth status."""
        patient_name = params.get("patient_name", "")
        tooth_number = params.get("tooth_number")

        if not tooth_number:
            return {"error": "missing_tooth", "message": "رقم السن مطلوب"}

        patient = await self._find_single_patient(patient_name)
        if isinstance(patient, dict):
            return patient  # Error/List
        if not patient:
            return {"error": "not_found", "message": "المريض غير موجود"}

        try:
            result = self.clinical.update_tooth_status(
                patient,
                tooth_number,
                params.get("condition", "Healthy"),
                params.get("notes", ""),
            )
            return {
                "message": f"✅ تم تحديث السن {result['fdi']} لـ {result['patient']}",
                "action": "tooth_updated",
                **result,
            }
        except ValueError as e:
            return {"error": "invalid_tooth", "message": str(e)}

    @risk_level(RiskLevel.CRITICAL)
    async def add_treatment_voice(self, params: Dict) -> Dict:
        """Add treatment from voice."""
        patient_name = params.get("patient_name", "")
        procedure = params.get("procedure", "")
        cost = float(params.get("cost", 0) or 0)

        # Handle paid amount
        paid_amount = params.get("paid_amount")
        if paid_amount:
            try:
                paid_amount = float(paid_amount)
            except (ValueError, TypeError):
                paid_amount = 0

        if not procedure:
            return {"error": "missing_procedure", "message": "الإجراء مطلوب"}

        patient = await self._find_single_patient(patient_name)
        if isinstance(patient, dict):
            return patient

        if not patient:
            # Check if it was a price check
            if cost <= 0:
                # Redirect logic (simplified)
                return {
                    "message": f"سعر {procedure}: (تحتاج لتوجيه لسجل المالية)",
                    "action": "redirect_finance",
                }

            return {
                "message": f"⚠️ لم يتم تحديد المريض للإجراء: {procedure}",
                "requires_patient": True,
            }

        # Create Treatment
        treatment = self.clinical.add_treatment(
            patient,
            procedure,
            cost,
            params.get("tooth_number"),
            params.get("diagnosis"),
            params.get("notes"),
        )

        response_msg = f"✅ تم إضافة العلاج: {procedure}"
        if treatment.cost > 0:
            response_msg += f" ({treatment.cost})"
        else:
            response_msg += " (سيتم تحديد التكلفة لاحقاً)"

        if params.get("diagnosis"):
            response_msg += f"\n🔍 التشخيص: {params.get('diagnosis')}"

        # Add Payment if provided
        if paid_amount and paid_amount > 0:
            try:
                # Use BillingService for standard payment processing
                from ...services.billing_service import BillingService
                from ...schemas.billing import PaymentCreate

                billing_service = BillingService(self.db, self.tenant_id)
                payment_data = PaymentCreate(
                    patient_id=patient.id,
                    amount=paid_amount,
                    notes=f"دفعة تلقائية مع علاج: {procedure} [AI]",
                )
                billing_service.create_payment(payment_data, doctor_id=self.user.id)
                response_msg += f"\n💰 تم تسجيل دفعة: {paid_amount}"
            except Exception as e:
                response_msg += f"\n⚠️ فشل تسجيل الدفعة: {str(e)}"

        tooth_input = params.get("tooth_number")
        if tooth_input:
            fdi = self.clinical._parse_tooth_number(tooth_input)
            tooth_display = f"FDI {fdi}" if fdi else tooth_input
            response_msg += f"\n🦷 السن: {tooth_display}"

        return {
            "message": response_msg,
            "action": "treatment_added",
            "treatment_id": treatment.id,
            "files_updated": ["treatments", "payments"]
            if paid_amount
            else ["treatments"],
        }

    @risk_level(RiskLevel.SAFE)
    async def parse_medical_dictation(self, params: Dict) -> Dict:
        """Parse dictation using Scribe."""
        text = params.get("dictation") or params.get("text", "")
        if not text:
            return {"error": "missing_text", "message": "النص فارغ"}

        try:
            procedures = self.scribe.analyze_dictation(text)

            # Contextual Patient Match
            patient_info = None
            if params.get("patient_name"):
                p = await self._find_single_patient(params["patient_name"])
                if hasattr(p, "id"):
                    patient_info = {"id": p.id, "name": p.name}

            return {
                "message": f"تم تحليل {len(procedures)} إجراءات.",
                "data": procedures,
                "patient": patient_info,
                "action": "scribe_analyzed",
            }
        except Exception as e:
            return {"error": "scribe_error", "message": str(e)}

    # Helper for searching
    async def _find_single_patient(self, name: str):
        if not name:
            return None
        patients = self.patient_service.search_patients_by_name(name)
        if not patients:
            return None

        if len(patients) == 1:
            return patients[0]

        # If multiple, check for EXACT match first
        exact_matches = [p for p in patients if p.name == name]
        if len(exact_matches) == 1:
            return exact_matches[0]

        return {
            "error": "multiple_patients",
            "message": f"وجدنا {len(patients)} مريض باسم '{name}'",
            "patients": [{"id": p.id, "name": p.name} for p in patients],
        }
