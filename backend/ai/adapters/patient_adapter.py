from typing import Dict, Any
from backend.services.patient_service import PatientService
from backend import schemas
from backend.ai.errors import AIValidationError, AINotFoundError, AIExecutionError


class PatientToolAdapter:
    """
    Adapter to bridge AI Tool Registry with PatientService.
    Converts raw tool parameters into Service calls and standardizes responses.
    Does NOT access DB directly.
    """

    def __init__(self, service: PatientService):
        self.service = service

    async def get_patient_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: get_patient_file"""
        name = params.get("patient_name", "")
        if not name:
            raise AIValidationError(
                "اسم المريض مطلوب",
                debug_info={"params": params},
                code="missing_parameter",
            )

        result = self.service.get_patient_file_details(name)

        if not result["found"]:
            raise AINotFoundError(
                result["message"], debug_info={"query": name}, code="patient_not_found"
            )

        if result.get("multiple"):
            # Technically not an error, but a "disambiguation required" state.
            # Ideally we should raise AINeedsDisambiguation, but for now we return list for UI to handle.
            # Or we can just return the data structure as success=True but with multiple items.
            return {
                "success": True,
                "message": f"تم العثور على {result['count']} مريض بهذا الاسم",
                "patients": result["patients"],
                "multiple": True,
            }

        # Success - Single Patient
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

        patients = self.service.search_patients_by_name(query)

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

        result = self.service.get_patient_summary_data(name)

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
            new_patient = self.service.create_patient(patient_data)

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
        patients = self.service.get_patients_with_balance()
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
